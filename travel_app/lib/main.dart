import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart'; 
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:async';
import 'package:flutter/services.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await dotenv.load(
      fileName: ".env",
      isOptional: true,
    );
  } catch (e) {
    debugPrint('dotenv yüklenemedi: $e');
  }

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
  final List<dynamic>? havaDurumu; // 🌟 YENİ: Hava Durumu verisi için eklendi
  int? feedback; 
  final DateTime zaman;

  Mesaj({
    required this.metin,
    required this.kullaniciMi,
    this.ucuslar,
    this.havaDurumu, // 🌟 Eklendi
    this.feedback,
    DateTime? zaman,
  }) : zaman = zaman ?? DateTime.now();

  Map<String, dynamic> toJson() => {
    'metin': metin,
    'kullaniciMi': kullaniciMi,
    'ucuslar': ucuslar,
    'havaDurumu': havaDurumu, // 🌟 Eklendi
    'feedback': feedback,
    'zaman': zaman.toIso8601String(),
  };

  factory Mesaj.fromJson(Map<String, dynamic> json) {
    DateTime parsedZaman = DateTime.now();
    if (json['zaman'] != null && json['zaman'].isNotEmpty) {
      try { parsedZaman = DateTime.parse(json['zaman'] as String); } catch (e) {}
    }
    return Mesaj(
      metin: json['metin'] ?? '',
      kullaniciMi: json['kullaniciMi'] ?? false,
      ucuslar: json['ucuslar'] != null ? List<dynamic>.from(json['ucuslar']) : null,
      havaDurumu: json['havaDurumu'] != null ? List<dynamic>.from(json['havaDurumu']) : null, // 🌟 Eklendi
      feedback: json['feedback'],
      zaman: parsedZaman,
    );
  }
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

  late stt.SpeechToText _speech;
  bool _dinliyorMu = false;
  late FlutterTts _flutterTts;
  
  Completer<void>? _apiCancelCompleter;
  http.Client? _httpClient; // 🌟 YENİ EKLENDİ: Arka plan bağlantısını kesmek için
  // 🌟 YENİ HALİ: Artık bir şehir için birden fazla resim (Liste) tutacağız.
  final Map<String, List<String>> _sehirResimleri = {};

  @override
  void initState() {
    super.initState();
    _verileriYukle(); 

    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _flutterTts.setLanguage("tr-TR");
    _flutterTts.setSpeechRate(0.5); 
  }

  void _sesDinle() async {
    if (!_dinliyorMu) {
      bool musaitMi = await _speech.initialize(
        onStatus: (durum) => debugPrint('Ses Durumu: $durum'),
        onError: (hata) => debugPrint('Ses Hatası: $hata'),
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

  Future<void> _sesliOku(String metin) async {
    String temizMetin = metin.replaceAll(RegExp(r'[#*]'), '');
    // 🌟 DÜZELTME: Hem Uçuşları hem Hava Durumunu sesten gizle
    if (temizMetin.contains("###UCUSLAR###")) {
      temizMetin = temizMetin.split("###UCUSLAR###")[0]; 
    }
    if (temizMetin.contains("###HAVA_DURUMU###")) {
      temizMetin = temizMetin.split("###HAVA_DURUMU###")[0]; 
    }
    await _flutterTts.speak(temizMetin);
  }

  List<String> _sehirleriTespit(String metin) {
    final sehirListesi = [
      'İstanbul', 'Ankara', 'İzmir', 'Adana', 'Gaziantep', 'Bursa', 'Antalya', 'Diyarbakır',
      'Prag', 'Viyana', 'Budapeşte', 'Roma', 'Paris', 'Londra', 'Berlin', 'Barselona',
      'Madrid', 'Lizbon', 'Amsterdam', 'Venedik', 'Floransa', 'Milano', 'Atina', 'Dubai',
      'Bükreş', 'Köstence', 'Braşov'
    ];
    
    List<String> bulunanSehirler = [];
    for (var sehir in sehirListesi) {
      if (metin.toLowerCase().contains(sehir.toLowerCase()) && !bulunanSehirler.contains(sehir)) {
        bulunanSehirler.add(sehir);
      }
    }
    return bulunanSehirler;
  }

  String _zamanFormatla(DateTime zaman) {
    final bugun = DateTime.now();
    final bugundi = DateTime(bugun.year, bugun.month, bugun.day);
    final mesajGunu = DateTime(zaman.year, zaman.month, zaman.day);
    
    if (bugundi == mesajGunu) {
      return "${zaman.hour.toString().padLeft(2, '0')}:${zaman.minute.toString().padLeft(2, '0')}";
    } else if (bugundi.subtract(const Duration(days: 1)) == mesajGunu) {
      return "Dün ${zaman.hour.toString().padLeft(2, '0')}:${zaman.minute.toString().padLeft(2, '0')}";
    } else {
      return "${zaman.day}/${zaman.month}/${zaman.year} ${zaman.hour.toString().padLeft(2, '0')}:${zaman.minute.toString().padLeft(2, '0')}";
    }
  }

  // 🌟 GÜNCELLENDİ: Unsplash'ten liste halinde 5 fotoğraf çekiyor
  Future<List<String>?> _sehirFotograflariGetir(String sehirAdi) async {
    if (_sehirResimleri.containsKey(sehirAdi)) {
      return _sehirResimleri[sehirAdi];
    }

    final unsplashKey = dotenv.env['UNSPLASH_API_KEY'] ?? '';
    if (unsplashKey.isEmpty) return null;

    try {
      final url = Uri.parse(
        'https://api.unsplash.com/search/photos?query=$sehirAdi&client_id=$unsplashKey&per_page=5',
      );

      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['results'] != null && (data['results'] as List).isNotEmpty) {
          List<String> fotoListesi = [];
          for (var item in data['results']) {
            fotoListesi.add(item['urls']['regular']);
          }
          _sehirResimleri[sehirAdi] = fotoListesi;
          return fotoListesi;
        }
      }
    } catch (e) {
      debugPrint("Şehir fotosu alınırken hata: $e");
    }
    return null;
  }

  Future<void> _haritaldaAc(String lokasyon) async {
    final encoded = Uri.encodeComponent(lokasyon);
    final String googleMapsUrl = 'https://www.google.com/maps/search/?api=1&query=$encoded';
    try {
      if (await canLaunchUrl(Uri.parse(googleMapsUrl))) {
        await launchUrl(Uri.parse(googleMapsUrl), mode: LaunchMode.externalApplication);
      } else {
        debugPrint("Link açılamıyor: $googleMapsUrl");
      }
    } catch (e) {
      debugPrint("Harita açılırken hata: $e");
    }
  }

  Future<void> _panoyaKopyala(String metin) async {
    await Clipboard.setData(ClipboardData(text: metin));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mesaj panoya kopyalandı! ✓'), duration: Duration(seconds: 2)),
      );
    }
  }

  Future<void> _mesajPaylas(String metin) async {
    try {
      await Share.share(metin, subject: 'Atlas Agent Cevabı');
    } catch (e) {
      debugPrint("Paylaşım hatası: $e");
    }
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

  void _sohbetSil(SohbetOturumu oturum) {
    setState(() {
      _gecmisSohbetler.remove(oturum);
    });
    _verileriKaydet();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sohbet silindi'), duration: Duration(seconds: 2)),
      );
    }
  }

  void _sohbetYenidenAdinlandir(SohbetOturumu oturum) {
    final TextEditingController adController = TextEditingController(text: oturum.baslik);
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rota Adını Değiştir'),
        content: TextField(
          controller: adController,
          maxLines: 1,
          decoration: const InputDecoration(
            hintText: 'Yeni ad girin...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('İptal'),
          ),
          ElevatedButton(
            onPressed: () {
              String yeniAd = adController.text.trim();
              if (yeniAd.isNotEmpty) {
                setState(() {
                  oturum.baslik = yeniAd;
                });
                _verileriKaydet();
              }
              Navigator.pop(context);
            },
            child: const Text('Kaydet'),
          ),
        ],
      ),
    );
  }

  void _mesajiDuzenle(int index) {
    final mesaj = _aktifOturum.mesajlar[index];
    final TextEditingController editController = TextEditingController(text: mesaj.metin);
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Soruyu Düzenle'),
        content: TextField(
          controller: editController,
          maxLines: 5,
          minLines: 2,
          decoration: const InputDecoration(
            hintText: 'Sorunuzu düzenleyin...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('İptal'),
          ),
          ElevatedButton(
            onPressed: () {
              String yeniMesaj = editController.text.trim();
              if (yeniMesaj.isNotEmpty) {
                setState(() {
                  _aktifOturum.mesajlar[index] = Mesaj(
                    metin: yeniMesaj,
                    kullaniciMi: true,
                  );
                });
                _verileriKaydet();
                _mesajGonder();
              }
              Navigator.pop(context);
            },
            child: const Text('Yeniden Sor'),
          ),
        ],
      ),
    );
  }

  void _geribildiriumGonder(int index, int oy) {
    setState(() {
      _aktifOturum.mesajlar[index].feedback = oy;
    });
    _verileriKaydet();
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
      _yukleniyor = true; // 🔴 Butonu kırmızı "Durdur" simgesine çevirir
    });
    
    _verileriKaydet(); 
    _altaKaydir();

    int aiMesajIndex = _aktifOturum.mesajlar.length;
    setState(() {
      _aktifOturum.mesajlar.add(Mesaj(metin: "", kullaniciMi: false));
    });

    _apiCancelCompleter = Completer<void>();
    _httpClient = http.Client(); // 🌟 Bağlantıyı özel bir istemci üzerinden açıyoruz

    try {
      var request = http.Request('POST', Uri.parse('http://10.0.2.2:8000/chat'));
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode({"message": gidenMesaj});

      var response = await _httpClient!.send(request);

      // 🛑 HATA BURADAYDI: Burada _yukleniyor'u false yapıyorduk. Artık sildik!

      String toplananCevap = "";

      response.stream.transform(utf8.decoder).listen(
        (gelenParca) {
          if (!(_apiCancelCompleter?.isCompleted ?? false)) {
            toplananCevap += gelenParca;

            // 🌟 YENİ AKILLI VE GÜÇLÜ AYRIŞTIRICI (PARSER)
            String metinKismi = toplananCevap;
            List<dynamic>? ucusVerisi;
            List<dynamic>? havaVerisi;

            // 1. Ana Metni Temizle (Ekrana JSON kodlarının sızmasını engeller)
            if (metinKismi.contains("###UCUSLAR###")) {
              metinKismi = metinKismi.split("###UCUSLAR###")[0];
            }
            if (metinKismi.contains("###HAVA_DURUMU###")) {
              metinKismi = metinKismi.split("###HAVA_DURUMU###")[0];
            }

            // 2. UÇUŞ VERİSİNİ AYIKLA (Birden fazla uçuşu destekler)
            if (toplananCevap.contains("###UCUSLAR###")) {
              String ucusStr = toplananCevap.split("###UCUSLAR###")[1];
              // Eğer ucusun arkasına hava durumu yapışmışsa, sadece uçuş kısmını kesip al!
              if (ucusStr.contains("###HAVA_DURUMU###")) {
                ucusStr = ucusStr.split("###HAVA_DURUMU###")[0];
              }
              try { ucusVerisi = jsonDecode(ucusStr); } catch (e) { debugPrint("Uçuş Çözümleme Hatası: $e"); }
            }

            // 3. HAVA DURUMU VERİSİNİ AYIKLA
            if (toplananCevap.contains("###HAVA_DURUMU###")) {
              String havaStr = toplananCevap.split("###HAVA_DURUMU###")[1];
              // Eğer havanın arkasına uçuş yapışmışsa, sadece hava kısmını kesip al!
              if (havaStr.contains("###UCUSLAR###")) {
                havaStr = havaStr.split("###UCUSLAR###")[0];
              }
              try { havaVerisi = jsonDecode(havaStr); } catch (e) { debugPrint("Hava Çözümleme Hatası: $e"); }
            }

            // Ekrana Yansıt
            setState(() {
              _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(
                metin: metinKismi,
                kullaniciMi: false,
                ucuslar: ucusVerisi,
                havaDurumu: havaVerisi,
              );
            });
            _altaKaydir();
          }
        },
        onDone: () { 
          debugPrint("Akış bitti."); 
          if (mounted) {
            setState(() { _yukleniyor = false; }); // 🟢 Akış bittiğinde butonu eski haline getir
          }
          _verileriKaydet(); 
          _sesliOku(_aktifOturum.mesajlar[aiMesajIndex].metin);
        },
        onError: (hata) {
          if (mounted) {
            setState(() { 
              _yukleniyor = false; 
              _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(metin: _aktifOturum.mesajlar[aiMesajIndex].metin + "\nŞu anda yanıt verilemiyor.", kullaniciMi: false);
            });
          }
        },
        cancelOnError: true, // 🌟 Hata alırsan akışı anında kes
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _yukleniyor = false;
          _aktifOturum.mesajlar[aiMesajIndex] = Mesaj(metin: "🔌 İşlem durduruldu veya sunucu kapalı.", kullaniciMi: false);
        });
      }
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
                          trailing: PopupMenuButton(
                            color: const Color(0xFF262626),
                            icon: const Icon(Icons.more_vert, color: Colors.grey, size: 20),
                            itemBuilder: (context) => [
                              PopupMenuItem(
                                child: const Text('Yeniden Adlandır', style: TextStyle(color: Colors.white)),
                                onTap: () => _sohbetYenidenAdinlandir(oturum),
                              ),
                              PopupMenuItem(
                                child: const Text('Sil', style: TextStyle(color: Colors.red)),
                                onTap: () => _sohbetSil(oturum),
                              ),
                            ],
                          ),
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
              child: Text("Atlas inceliyor...", style: TextStyle(color: Colors.grey[500], fontSize: 13, fontStyle: FontStyle.italic)),
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

                  // 🌟 ADIM 5: Gönder/Durdur Butonu
                  Container(
                    margin: const EdgeInsets.only(bottom: 2),
                    decoration: BoxDecoration(
                      color: _yukleniyor ? Colors.redAccent : Colors.black87,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: Icon(
                        _yukleniyor ? Icons.stop : Icons.arrow_upward_rounded, // Icons.stop daha şık durur
                        color: Colors.white,
                        size: 22,
                      ),
                      onPressed: _yukleniyor ? () {
                        // 🛑 KULLANICI DURDURA BASTIĞINDA:
                        if (!(_apiCancelCompleter?.isCompleted ?? true)) {
                          _apiCancelCompleter?.complete();
                        }
                        _httpClient?.close(); // Sunucuyla olan bağlantıyı BİTİR (İnternet tasarrufu)
                        setState(() => _yukleniyor = false); // Butonu anında normale çevir
                      } : _mesajGonder,
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
    int mesajIndex = _aktifOturum.mesajlar.indexOf(mesaj);
    List<String> bulunanSehirler = isUser ? [] : _sehirleriTespit(mesaj.metin);
    
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
            child: Column(
              crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Text(
                    _zamanFormatla(mesaj.zaman),
                    style: TextStyle(color: Colors.grey[500], fontSize: 11, fontWeight: FontWeight.w500),
                  ),
                ),
                Container(
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
                            // 🌟 YENİ: Hava Durumu Kartlarını Ekrana Çizdir
                            if (mesaj.havaDurumu != null && mesaj.havaDurumu!.isNotEmpty)
                              ...mesaj.havaDurumu!.map((hava) => HavaDurumuKarti(
                                sehir: hava['sehir'] ?? 'Bilinmiyor',
                                sicaklik: hava['sicaklik'] ?? '0°C',
                                durum: hava['durum'] ?? '-',
                                tarih: hava['tarih'] ?? '',
                              )).toList(),
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
                
                // 🌟 YENİ: Harita ve Unsplash Galeri Gösterimi
                if (bulunanSehirler.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: bulunanSehirler.map((sehir) => ElevatedButton.icon(
                      onPressed: () => _haritaldaAc(sehir),
                      icon: const Icon(Icons.location_on, size: 16),
                      label: Text(sehir),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFEFF6FF),
                        foregroundColor: const Color(0xFF3B82F6),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        elevation: 0,
                      ),
                    )).toList(),
                  ),
                  const SizedBox(height: 8),
                  
                  // 🌟 YENİ: Sohbet ekranında tek resim, tıklandığında kaydırmalı galeri
                  ...bulunanSehirler.map((sehir) => FutureBuilder<List<String>?>(
                    future: _sehirFotograflariGetir(sehir),
                    builder: (context, snapshot) {
                      // Yükleniyor durumu
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 16.0),
                          child: Center(child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF3B82F6))),
                        );
                      } 
                      // 🌟 GÜNCELLEME: Sadece tek bir kapak fotoğrafı göster
                      else if (snapshot.hasData && snapshot.data != null && snapshot.data!.isNotEmpty) {
                        List<String> resimler = snapshot.data!;
                        String kapakFotografi = resimler[0]; // Sadece ilkini (en popüler) alıyoruz
                        
                        return GestureDetector(
                          onTap: () {
                            // Tıklanınca tüm fotoğrafları siyah ekranlı galeriye gönder
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => TamEkranGaleri(
                                  resimler: resimler, // Tüm listeyi gönderiyoruz ki kaydırılabilsin
                                  baslangicIndex: 0,
                                ),
                              ),
                            );
                          },
                          child: Container(
                            width: double.infinity,
                            height: 200, // Chat ekranında daha doyurucu durması için büyüttük
                            margin: const EdgeInsets.only(top: 8, bottom: 8),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(16),
                              boxShadow: [
                                BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 6, offset: const Offset(0, 3))
                              ]
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(16),
                              child: Stack(
                                fit: StackFit.expand,
                                children: [
                                  // Kapak Fotoğrafı
                                  Image.network(
                                    kapakFotografi,
                                    fit: BoxFit.cover,
                                    errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(),
                                  ),
                                  // 🌟 YENİ: Sağ üst köşeye "Albüm" ikonu ve sayısı (Instagram stili)
                                  if (resimler.length > 1)
                                    Positioned(
                                      right: 8,
                                      top: 8,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: Colors.black.withOpacity(0.6),
                                          borderRadius: BorderRadius.circular(12),
                                        ),
                                        child: Row(
                                          children: [
                                            const Icon(Icons.photo_library, color: Colors.white, size: 14),
                                            const SizedBox(width: 4),
                                            Text(
                                              "1/${resimler.length}", 
                                              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ),
                        );
                      }
                      return const SizedBox.shrink();
                    },
                  )).toList(),
                ],

                if (!isUser && !_yukleniyor) ...[
                  const SizedBox(height: 8),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.content_copy, size: 18),
                        onPressed: () => _panoyaKopyala(mesaj.metin),
                        tooltip: 'Kopyala',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: const EdgeInsets.all(4),
                      ),
                      IconButton(
                        icon: const Icon(Icons.share, size: 18),
                        onPressed: () => _mesajPaylas(mesaj.metin),
                        tooltip: 'Paylaş',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: const EdgeInsets.all(4),
                      ),
                      IconButton(
                        icon: Icon(
                          Icons.thumb_up,
                          size: 18,
                          color: mesaj.feedback == 1 ? Colors.green : Colors.grey,
                        ),
                        onPressed: () => _geribildiriumGonder(mesajIndex, mesaj.feedback == 1 ? 0 : 1),
                        tooltip: 'Beğen',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: const EdgeInsets.all(4),
                      ),
                      IconButton(
                        icon: Icon(
                          Icons.thumb_down,
                          size: 18,
                          color: mesaj.feedback == -1 ? Colors.red : Colors.grey,
                        ),
                        onPressed: () => _geribildiriumGonder(mesajIndex, mesaj.feedback == -1 ? 0 : -1),
                        tooltip: 'Beğenme',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: const EdgeInsets.all(4),
                      ),
                    ],
                  ),
                ] else ...[
                  const SizedBox(height: 8),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.edit, size: 18),
                        onPressed: () => _mesajiDuzenle(mesajIndex),
                        tooltip: 'Düzenle',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: const EdgeInsets.all(4),
                      ),
                      IconButton(
                        icon: const Icon(Icons.content_copy, size: 18),
                        onPressed: () => _panoyaKopyala(mesaj.metin),
                        tooltip: 'Kopyala',
                        constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                        padding: const EdgeInsets.all(4),
                      ),
                    ],
                  ),
                ],
              ],
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
                debugPrint("$havayolu seçildi!");
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

// 🌟 YENİ: Tam Ekran Fotoğraf Galerisi (Albüm) Sınıfı
class TamEkranGaleri extends StatefulWidget {
  final List<String> resimler;
  final int baslangicIndex;

  const TamEkranGaleri({super.key, required this.resimler, required this.baslangicIndex});

  @override
  State<TamEkranGaleri> createState() => _TamEkranGaleriState();
}

class _TamEkranGaleriState extends State<TamEkranGaleri> {
  late PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(initialPage: widget.baslangicIndex);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      extendBodyBehindAppBar: true,
      body: PageView.builder(
        controller: _pageController,
        itemCount: widget.resimler.length,
        itemBuilder: (context, index) {
          return InteractiveViewer( // Parmakla zoom (yakınlaştırma) özelliği
            minScale: 0.5,
            maxScale: 4.0,
            child: Center(
              child: Image.network(
                widget.resimler[index],
                fit: BoxFit.contain,
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return const Center(child: CircularProgressIndicator(color: Colors.white54));
                },
              ),
            ),
          );
        },
      ),
    );
  }
}
// 🌟 YENİ: Şık Hava Durumu Kartı Widget'ı
class HavaDurumuKarti extends StatelessWidget {
  final String sehir;
  final String sicaklik;
  final String durum;
  final String tarih;

  const HavaDurumuKarti({
    super.key,
    required this.sehir,
    required this.sicaklik,
    required this.durum,
    required this.tarih,
  });

  IconData _ikonBelirle(String durum) {
    String d = durum.toLowerCase();
    if (d.contains('güneş') || d.contains('açık')) return Icons.wb_sunny;
    if (d.contains('bulut')) return Icons.cloud;
    if (d.contains('yağmur') || d.contains('sağanak')) return Icons.water_drop;
    if (d.contains('kar')) return Icons.ac_unit;
    return Icons.thermostat;
  }

  Color _renkBelirle(String durum) {
    String d = durum.toLowerCase();
    if (d.contains('güneş') || d.contains('açık')) return Colors.orangeAccent;
    if (d.contains('yağmur') || d.contains('sağanak')) return Colors.blueGrey;
    return Colors.lightBlue; // Varsayılan
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [_renkBelirle(durum).withOpacity(0.8), _renkBelirle(durum)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: _renkBelirle(durum).withOpacity(0.3), blurRadius: 8, offset: const Offset(0, 4))
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(sehir, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(tarih, style: const TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w500)),
              const SizedBox(height: 12),
              Text(durum, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500)),
            ],
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Icon(_ikonBelirle(durum), color: Colors.white, size: 40),
              const SizedBox(height: 8),
              Text(sicaklik, style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900)),
            ],
          ),
        ],
      ),
    );
  }
}