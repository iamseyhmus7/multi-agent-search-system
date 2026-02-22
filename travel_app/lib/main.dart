import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_markdown/flutter_markdown.dart';

void main() {
  runApp(const SeyahatUygulamasi());
}

class SeyahatUygulamasi extends StatelessWidget {
  const SeyahatUygulamasi({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Atlas Agent',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF3B82F6)),
        useMaterial3: true,
        fontFamily: 'Roboto', 
      ),
      home: const ChatEkrani(),
    );
  }
}

// 1. MESAJ SINIFI
class Mesaj {
  final String metin;
  final bool kullaniciMi;

  Mesaj({required this.metin, required this.kullaniciMi});
}

// 2. SOHBET OTURUMU SINIFI (YENİ!)
class SohbetOturumu {
  final String id;
  String baslik;
  List<Mesaj> mesajlar;

  SohbetOturumu({required this.id, required this.baslik, required this.mesajlar});
}

class ChatEkrani extends StatefulWidget {
  const ChatEkrani({super.key});

  @override
  State<ChatEkrani> createState() => _ChatEkraniState();
}

class _ChatEkraniState extends State<ChatEkrani> {
  final TextEditingController _mesajKontrolcusu = TextEditingController();
  final ScrollController _scrollKontrolcusu = ScrollController();
  
  // 3. OTURUM YÖNETİMİ DEĞİŞKENLERİ
  List<SohbetOturumu> _gecmisSohbetler = [];
  late SohbetOturumu _aktifOturum;
  bool _yukleniyor = false;

  @override
  void initState() {
    super.initState();
    _yeniSohbetBaslat(ilkAcilis: true); // Uygulama ilk açıldığında boş bir oturum yarat
  }

  // --- YENİ SOHBET AÇMA MANTIĞI ---
  void _yeniSohbetBaslat({bool ilkAcilis = false}) {
    // Eğer mevcut sohbette mesaj varsa ve geçmiş listesinde yoksa, onu listeye ekleyerek kaydet
    if (!ilkAcilis && _aktifOturum.mesajlar.isNotEmpty && !_gecmisSohbetler.contains(_aktifOturum)) {
      _gecmisSohbetler.insert(0, _aktifOturum);
    }

    setState(() {
      _aktifOturum = SohbetOturumu(
        id: DateTime.now().millisecondsSinceEpoch.toString(), // Benzersiz ID
        baslik: "Yeni Rota",
        mesajlar: [],
      );
    });

    if (!ilkAcilis) Navigator.pop(context); // Menüden tıklandıysa menüyü kapat
  }

  // --- GEÇMİŞ SOHBETE TIKLAMA MANTIĞI ---
  void _eskiSohbeteGec(SohbetOturumu secilenOturum) {
    // Geçiş yapmadan önce açık olan oturumu (eğer mesaj varsa) kaydet
    if (_aktifOturum.mesajlar.isNotEmpty && !_gecmisSohbetler.contains(_aktifOturum)) {
      _gecmisSohbetler.insert(0, _aktifOturum);
    }

    setState(() {
      _aktifOturum = secilenOturum;
    });
    
    Navigator.pop(context); // Menüyü kapat
    _altaKaydir(); // Eski mesajları yükleyince en alta kaydır
  }

  void _altaKaydir() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollKontrolcusu.hasClients) {
        _scrollKontrolcusu.animateTo(
          _scrollKontrolcusu.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _mesajGonder() async {
    String gidenMesaj = _mesajKontrolcusu.text.trim();
    if (gidenMesaj.isEmpty) return;

    setState(() {
      // Eğer bu oturumdaki ilk mesajsa, başlığı kullanıcının mesajı yap ve sol menüye ekle!
      if (_aktifOturum.mesajlar.isEmpty) {
        _aktifOturum.baslik = gidenMesaj.length > 25 ? "${gidenMesaj.substring(0, 25)}..." : gidenMesaj;
        if (!_gecmisSohbetler.contains(_aktifOturum)) {
          _gecmisSohbetler.insert(0, _aktifOturum); // Menüde en üste ekle
        }
      }

      _aktifOturum.mesajlar.add(Mesaj(metin: gidenMesaj, kullaniciMi: true));
      _mesajKontrolcusu.clear();
      _yukleniyor = true;
    });
    _altaKaydir();

    int aiMesajIndex = _aktifOturum.mesajlar.length;
    setState(() {
      _aktifOturum.mesajlar.add(Mesaj(metin: "", kullaniciMi: false));
    });

    try {
      var request = http.Request('POST', Uri.parse('http://10.0.2.2:8000/chat'));
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode({"message": gidenMesaj});

      var response = await http.Client().send(request);

      setState(() { _yukleniyor = false; });

      response.stream.transform(utf8.decoder).listen(
        (gelenParca) {
          setState(() {
            _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(
              metin: _aktifOturum.mesajlar[aiMesajIndex].metin + gelenParca,
              kullaniciMi: false,
            );
          });
          _altaKaydir();
        },
        onDone: () { print("Akış bitti."); },
        onError: (hata) {
          setState(() {
            _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(metin: _aktifOturum.mesajlar[aiMesajIndex].metin + "\n[Bağlantı koptu]", kullaniciMi: false);
          });
        },
      );
    } catch (e) {
      setState(() {
        _yukleniyor = false;
        _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(metin: "🔌 Bağlantı Hatası: Sunucu kapalı.", kullaniciMi: false);
      });
      _altaKaydir();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      
      // --- SOL MENÜ (Geçmiş Sohbetler) ---
      drawer: Drawer(
        backgroundColor: const Color(0xFF171717),
        child: Column(
          children: [
            const SizedBox(height: 50),
            // Yeni Sohbet Butonu
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: ElevatedButton.icon(
                onPressed: () => _yeniSohbetBaslat(ilkAcilis: false),
                icon: const Icon(Icons.add, color: Colors.white),
                label: const Text("Yeni Atlas Rotası", style: TextStyle(color: Colors.white, fontSize: 16)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF262626),
                  minimumSize: const Size(double.infinity, 50),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  alignment: Alignment.centerLeft,
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Padding(
              padding: EdgeInsets.only(left: 20.0, bottom: 10),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text("Önceki Planlar", style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ),
            
            // --- DİNAMİK GEÇMİŞ SOHBETLER LİSTESİ ---
            Expanded(
              child: _gecmisSohbetler.isEmpty
                  ? const Center(child: Text("Henüz bir sohbet yok", style: TextStyle(color: Colors.white38, fontSize: 13)))
                  : ListView.builder(
                      padding: EdgeInsets.zero,
                      itemCount: _gecmisSohbetler.length,
                      itemBuilder: (context, index) {
                        final oturum = _gecmisSohbetler[index];
                        final seciliMi = oturum.id == _aktifOturum.id;

                        return ListTile(
                          leading: Icon(Icons.chat_bubble_outline, color: seciliMi ? Colors.white : Colors.grey[500], size: 20),
                          title: Text(
                            oturum.baslik, 
                            style: TextStyle(color: seciliMi ? Colors.white : Colors.white70, fontSize: 14, fontWeight: seciliMi ? FontWeight.bold : FontWeight.normal),
                            maxLines: 1, 
                            overflow: TextOverflow.ellipsis,
                          ),
                          tileColor: seciliMi ? const Color(0xFF262626) : Colors.transparent, // Seçili olanın arka planı hafif parlak
                          onTap: () => _eskiSohbeteGec(oturum),
                        );
                      },
                    ),
            ),

            const Divider(color: Colors.white24),
            ListTile(
              leading: const CircleAvatar(backgroundColor: Color(0xFF3B82F6), child: Icon(Icons.person, color: Colors.white)),
              title: const Text("Şeyhmus OK", style: TextStyle(color: Colors.white)),
              subtitle: const Text("Premium Üye", style: TextStyle(color: Colors.grey, fontSize: 12)),
              onTap: () {},
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),

      // ÜST BAR
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.white,
        iconTheme: const IconThemeData(color: Colors.black87),
        title: const Text(
          'Atlas Agent',
          style: TextStyle(color: Colors.black87, fontWeight: FontWeight.w800, letterSpacing: -0.5),
        ),
        centerTitle: true,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1.0),
          child: Container(color: Colors.grey[200], height: 1.0),
        ),
      ),

      // ANA GÖVDE
      body: Column(
        children: [
          // Aktif Oturumun Mesajlarını Göster
          Expanded(
            child: _aktifOturum.mesajlar.isEmpty
                ? _bosEkranTasarimi()
                : ListView.builder(
                    controller: _scrollKontrolcusu,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
                    itemCount: _aktifOturum.mesajlar.length,
                    itemBuilder: (context, index) {
                      return _mesajBalonuOlustur(_aktifOturum.mesajlar[index]);
                    },
                  ),
          ),
          
          if (_yukleniyor)
            Padding(
              padding: const EdgeInsets.only(bottom: 15, left: 24),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text("Atlas inceliyor...", style: TextStyle(color: Colors.grey[500], fontSize: 13, fontStyle: FontStyle.italic)),
              ),
            ),

          // MESAJ YAZMA KUTUSU
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Colors.grey.shade200)),
            ),
            child: SafeArea(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFFF4F4F5),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: TextField(
                        controller: _mesajKontrolcusu,
                        minLines: 1,
                        maxLines: 5,
                        textInputAction: TextInputAction.newline,
                        style: const TextStyle(fontSize: 15),
                        decoration: const InputDecoration(
                          hintText: 'Atlas\'a bir soru sor...',
                          hintStyle: TextStyle(color: Colors.grey),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Container(
                    margin: const EdgeInsets.only(bottom: 2),
                    decoration: const BoxDecoration(color: Colors.black87, shape: BoxShape.circle),
                    child: IconButton(
                      icon: const Icon(Icons.arrow_upward_rounded, color: Colors.white, size: 22),
                      onPressed: _mesajGonder,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bosEkranTasarimi() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(color: Color(0xFFF4F4F5), shape: BoxShape.circle),
            child: const Icon(Icons.travel_explore, size: 50, color: Colors.black87),
          ),
          const SizedBox(height: 20),
          const Text("Atlas Agent'a Hoş Geldiniz", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.black87)),
          const SizedBox(height: 10),
          const Text("Seyahat rotaları, biletler ve daha fazlası...", style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _mesajBalonuOlustur(Mesaj mesaj) {
    bool isUser = mesaj.kullaniciMi;
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 24.0),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(color: const Color(0xFF10B981), borderRadius: BorderRadius.circular(8)),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 16),
            ),
            const SizedBox(width: 12),
          ],
          
          Flexible(
            child: Container(
              padding: isUser ? const EdgeInsets.symmetric(horizontal: 18, vertical: 12) : EdgeInsets.zero,
              decoration: BoxDecoration(
                color: isUser ? const Color(0xFFF4F4F5) : Colors.transparent,
                borderRadius: BorderRadius.circular(20),
              ),
              child: isUser
                  ? Text(mesaj.metin, style: const TextStyle(color: Colors.black87, fontSize: 16))
                  : MarkdownBody(
                      data: mesaj.metin,
                      selectable: true,
                      styleSheet: MarkdownStyleSheet(
                        p: const TextStyle(color: Color(0xFF374151), fontSize: 16, height: 1.6),
                        strong: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF111827), fontSize: 16),
                        listBullet: const TextStyle(color: Color(0xFF3B82F6), fontSize: 18, fontWeight: FontWeight.bold),
                        h1: const TextStyle(color: Colors.black, fontSize: 22, fontWeight: FontWeight.w900),
                        h2: const TextStyle(color: Colors.black, fontSize: 20, fontWeight: FontWeight.bold),
                        blockquote: const TextStyle(color: Color(0xFF4B5563), fontStyle: FontStyle.italic),
                        blockquoteDecoration: BoxDecoration(
                          border: const Border(left: BorderSide(color: Color(0xFF3B82F6), width: 4)),
                          color: const Color(0xFFEFF6FF),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        code: const TextStyle(backgroundColor: Color(0xFFF3F4F6), color: Color(0xFFEF4444), fontFamily: 'monospace'),
                        codeblockDecoration: BoxDecoration(
                          color: const Color(0xFF1F2937),
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}