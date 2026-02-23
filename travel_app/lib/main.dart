import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:hive_flutter/hive_flutter.dart';
// 🌟 YENİ: Ses paketleri eklendi
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  await Hive.openBox('atlas_box'); 

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

class Mesaj {
  final String metin;
  final bool kullaniciMi;
  final List<dynamic>? ucuslar; 

  Mesaj({required this.metin, required this.kullaniciMi, this.ucuslar});

  Map<String, dynamic> toJson() => {
    'metin': metin,
    'kullaniciMi': kullaniciMi,
    'ucuslar': ucuslar,
  };

  factory Mesaj.fromJson(Map<String, dynamic> json) => Mesaj(
    metin: json['metin'] ?? '',
    kullaniciMi: json['kullaniciMi'] ?? false,
    ucuslar: json['ucuslar'] != null ? List<dynamic>.from(json['ucuslar']) : null,
  );
}

class SohbetOturumu {
  final String id;
  String baslik;
  List<Mesaj> mesajlar;

  SohbetOturumu({required this.id, required this.baslik, required this.mesajlar});

  Map<String, dynamic> toJson() => {
    'id': id,
    'baslik': baslik,
    'mesajlar': mesajlar.map((m) => m.toJson()).toList(),
  };

  factory SohbetOturumu.fromJson(Map<String, dynamic> json) => SohbetOturumu(
    id: json['id'] ?? '',
    baslik: json['baslik'] ?? 'Yeni Rota',
    mesajlar: json['mesajlar'] != null 
        ? (json['mesajlar'] as List).map((m) => Mesaj.fromJson(Map<String, dynamic>.from(m))).toList()
        : [],
  );
}

class ChatEkrani extends StatefulWidget {
  const ChatEkrani({super.key});

  @override
  State<ChatEkrani> createState() => _ChatEkraniState();
}

class _ChatEkraniState extends State<ChatEkrani> {
  final TextEditingController _mesajKontrolcusu = TextEditingController();
  final ScrollController _scrollKontrolcusu = ScrollController();
  
  List<SohbetOturumu> _gecmisSohbetler = [];
  late SohbetOturumu _aktifOturum;
  bool _yukleniyor = false;
  
  final _box = Hive.box('atlas_box');

  // 🌟 YENİ: Ses Asistanı Değişkenleri
  late stt.SpeechToText _speech;
  bool _dinliyorMu = false;
  late FlutterTts _flutterTts;

  @override
  void initState() {
    super.initState();
    _verileriYukle(); 

    // 🌟 YENİ: Ses Motorlarını Başlatıyoruz
    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _flutterTts.setLanguage("tr-TR"); // Türkçe
    _flutterTts.setSpeechRate(0.3); // Doğal konuşma hızı
  }

  // 🌟 YENİ: Sesi Metne Çevir (Kullanıcı Konuştuğunda)
  void _sesDinle() async {
    if (!_dinliyorMu) {
      bool musaitMi = await _speech.initialize(
        onStatus: (durum) => print('Ses Durumu: $durum'),
        onError: (hata) => print('Ses Hatası: $hata'),
      );

      if (musaitMi) {
        setState(() => _dinliyorMu = true);
        _speech.listen(
          onResult: (sonuc) {
            setState(() {
              _mesajKontrolcusu.text = sonuc.recognizedWords;
            });
          },
          localeId: "tr_TR",
        );
      }
    } else {
      setState(() => _dinliyorMu = false);
      _speech.stop();
    }
  }

  // 🌟 YENİ: Metni Sese Çevir (Yapay Zeka Cevap Verdiğinde)
  Future<void> _sesliOku(String metin) async {
    // Markdown işaretlerini (*, #) okumaması için temizliyoruz
    String temizMetin = metin.replaceAll(RegExp(r'[#*]'), '');
    if (temizMetin.contains("###UCUSLAR###")) {
      temizMetin = temizMetin.split("###UCUSLAR###")[0]; // Uçuş JSON'ını okumasına engel oluyoruz
    }
    await _flutterTts.speak(temizMetin);
  }

  void _verileriKaydet() {
    var gecmisJson = _gecmisSohbetler.map((oturum) => oturum.toJson()).toList();
    var aktifJson = _aktifOturum.toJson();

    _box.put('gecmisSohbetler', gecmisJson);
    _box.put('aktifOturum', aktifJson);
  }

  void _verileriYukle() {
    var kayitliGecmis = _box.get('gecmisSohbetler');
    var kayitliAktif = _box.get('aktifOturum');

    setState(() {
      if (kayitliGecmis != null) {
        _gecmisSohbetler = (kayitliGecmis as List)
            .map((e) => SohbetOturumu.fromJson(Map<String, dynamic>.from(e)))
            .toList();
      }

      if (kayitliAktif != null) {
        _aktifOturum = SohbetOturumu.fromJson(Map<String, dynamic>.from(kayitliAktif));
      } else {
        _aktifOturum = SohbetOturumu(
          id: DateTime.now().millisecondsSinceEpoch.toString(),
          baslik: "Yeni Rota",
          mesajlar: [],
        );
      }
    });
    _altaKaydir();
  }

  void _yeniSohbetBaslat({bool ilkAcilis = false}) {
    if (!ilkAcilis && _aktifOturum.mesajlar.isNotEmpty && !_gecmisSohbetler.contains(_aktifOturum)) {
      _gecmisSohbetler.insert(0, _aktifOturum);
    }

    setState(() {
      _aktifOturum = SohbetOturumu(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        baslik: "Yeni Rota",
        mesajlar: [],
      );
    });
    
    _verileriKaydet(); 
    if (!ilkAcilis) Navigator.pop(context);
  }

  void _eskiSohbeteGec(SohbetOturumu secilenOturum) {
    if (_aktifOturum.mesajlar.isNotEmpty && !_gecmisSohbetler.contains(_aktifOturum)) {
      _gecmisSohbetler.insert(0, _aktifOturum);
    }

    setState(() {
      _aktifOturum = secilenOturum;
    });
    
    Navigator.pop(context);
    _verileriKaydet(); 
    _altaKaydir();
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
      if (_aktifOturum.mesajlar.isEmpty) {
        _aktifOturum.baslik = gidenMesaj.length > 25 ? "${gidenMesaj.substring(0, 25)}..." : gidenMesaj;
        if (!_gecmisSohbetler.contains(_aktifOturum)) {
          _gecmisSohbetler.insert(0, _aktifOturum);
        }
      }

      _aktifOturum.mesajlar.add(Mesaj(metin: gidenMesaj, kullaniciMi: true));
      _mesajKontrolcusu.clear();
      _yukleniyor = true;
    });
    
    _verileriKaydet(); 
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

      String toplananCevap = "";

      response.stream.transform(utf8.decoder).listen(
        (gelenParca) {
          toplananCevap += gelenParca;

          if (toplananCevap.contains("###UCUSLAR###")) {
            var parcalar = toplananCevap.split("###UCUSLAR###");
            String metinKismi = parcalar[0];
            String jsonKismi = parcalar.length > 1 ? parcalar[1] : "";
            
            try {
              List<dynamic> ucusListesi = jsonDecode(jsonKismi);
              setState(() {
                _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(
                  metin: metinKismi,
                  kullaniciMi: false,
                  ucuslar: ucusListesi, 
                );
              });
            } catch (e) {
              setState(() {
                _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(metin: metinKismi, kullaniciMi: false);
              });
            }
          } else {
            setState(() {
              _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(
                metin: toplananCevap,
                kullaniciMi: false,
              );
            });
          }
          _altaKaydir();
        },
        onDone: () { 
          print("Akış bitti."); 
          _verileriKaydet(); 
          // 🌟 YENİ: Yapay zeka yazmayı bitirince, cevabı sesli olarak oku!
          _sesliOku(_aktifOturum.mesajlar[aiMesajIndex].metin);
        },
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
      
      drawer: Drawer(
        backgroundColor: const Color(0xFF171717),
        child: Column(
          children: [
            const SizedBox(height: 50),
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
                          tileColor: seciliMi ? const Color(0xFF262626) : Colors.transparent, 
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

      body: Column(
        children: [
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
                  
                  // 🌟 YENİ: Mikrofon Butonu
                  Container(
                    margin: const EdgeInsets.only(bottom: 2, right: 8),
                    decoration: BoxDecoration(
                      color: _dinliyorMu ? Colors.redAccent : const Color(0xFFF4F4F5), 
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.grey.shade300),
                    ),
                    child: IconButton(
                      icon: Icon(_dinliyorMu ? Icons.mic : Icons.mic_none, 
                            color: _dinliyorMu ? Colors.white : Colors.black87, size: 22),
                      onPressed: _sesDinle,
                    ),
                  ),

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
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        MarkdownBody(
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
                        if (mesaj.ucuslar != null && mesaj.ucuslar!.isNotEmpty)
                          ...mesaj.ucuslar!.map((ucus) => UcusKarti(
                                havayolu: ucus['havayolu'] ?? 'Bilinmiyor',
                                kalkisSaat: ucus['kalkisSaat'] ?? '00:00',
                                varisSaat: ucus['varisSaat'] ?? '00:00',
                                kalkisKod: ucus['kalkisKod'] ?? 'N/A',
                                varisKod: ucus['varisKod'] ?? 'N/A',
                                fiyat: ucus['fiyat'] ?? '₺0',
                                tarih: ucus['tarih'] ?? '', 
                              )).toList(),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class UcusKarti extends StatelessWidget {
  final String havayolu;
  final String kalkisSaat;
  final String varisSaat;
  final String kalkisKod;
  final String varisKod;
  final String fiyat;
  final String tarih; 

  const UcusKarti({
    super.key,
    required this.havayolu,
    required this.kalkisSaat,
    required this.varisSaat,
    required this.kalkisKod,
    required this.varisKod,
    required this.fiyat,
    required this.tarih, 
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade200),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.airlines, color: Color(0xFF3B82F6), size: 20),
                      const SizedBox(width: 8),
                      Text(havayolu, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black87)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(tarih, style: const TextStyle(color: Colors.grey, fontSize: 13, fontWeight: FontWeight.w500)), 
                ],
              ),
              Text(fiyat, style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF10B981), fontSize: 18)),
            ],
          ),
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Divider(height: 1),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(kalkisSaat, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  Text(kalkisKod, style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w500)),
                ],
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      const Expanded(child: Divider(color: Colors.grey, thickness: 1.5)),
                      Transform.rotate(
                        angle: 1.57, 
                        child: const Icon(Icons.flight, color: Color(0xFF3B82F6), size: 24),
                      ),
                      const Expanded(child: Divider(color: Colors.grey, thickness: 1.5)),
                    ],
                  ),
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(varisSaat, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  Text(varisKod, style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w500)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                print("$havayolu seçildi!");
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFEFF6FF),
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: const Text("Bileti Seç", style: TextStyle(color: Color(0xFF3B82F6), fontWeight: FontWeight.bold)),
            ),
          )
        ],
      ),
    );
  }
}