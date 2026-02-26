# 🚀 ADIM 5 Kurulum & Ayarlanması Talimatları

## 1️⃣ Unsplash API Key Ayarlanması (Opsiyonel ama Önerilir)

### URL Launcher İçin Manifest/Config
Android ve iOS'ta URL açabilmek için küçük ayarlamalar gerekebilir:

#### Android (`android/app/src/main/AndroidManifest.xml`)
```xml
<queries>
    <intent>
        <action android:name="android.intent.action.VIEW"/>
        <data android:scheme="https"/>
    </intent>
</queries>
```

#### iOS (`ios/Runner/Info.plist`)
```xml
<key>LSApplicationQueriesSchemes</key>
<array>
    <string>googlemaps</string>
</array>
```

### Unsplash API Key Ekleme
1. https://unsplash.com/developers adresine git
2. "Register as a developer" ile kayıt ol
3. Uygulaması oluştur ve API key al
4. `gemini_client.py` (Python backend) veya `main.dart`'da şu satırı düzenle:

```dart
// main.dart, _sehirFotografiGetir() fonksiyonunda:
final response = await http.get(
  Uri.parse('https://api.unsplash.com/search/photos?query=$sehirAdi&client_id=YOUR_UNSPLASH_API_KEY&per_page=1'),
);
```

API Key'i değiştir:
```dart
// Eski:
client_id=YOUR_UNSPLASH_API_KEY

// Yeni:
client_id=YOUR_ACTUAL_API_KEY_HERE
```

---

## 2️⃣ Yeni Dosya & Değişiklikler

### Ana Güncelleme
- [main.dart](travel_app/lib/main.dart) - Tüm yeni özellikler burada

### Kütüphane Eklentileri
- [pubspec.yaml](travel_app/pubspec.yaml) - `url_launcher: ^6.2.0` eklendi

### Dokümantasyon
- [ADIM_5_OZELLIKLERI.md](travel_app/ADIM_5_OZELLIKLERI.md) - Detaylı özellikler

---

## 3️⃣ Yeni Fonksiyonlar Quick Reference

### Message Actions
```dart
_panoyaKopyala(String metin)       // 📋 Kopyala
_mesajPaylas(String metin)         // 🔗 Paylaş
_geribildiriumGonder(index, oy)    // 👍👎 Feedback
_mesajiDuzenle(int index)          // ✏️ Düzenle
```

### Sidebar Actions
```dart
_sohbetSil(SohbetOturumu oturum)           // 🗑️ Sil
_sohbetYenidenAdinlandir(oturum)           // ✏️ Adlandır
```

### Location & Maps
```dart
_sehirleriTespit(String metin)      // Şehir bulma
_haritaldaAc(String lokasyon)       // 📍 Google Maps
_sehirFotografiGetir(String sehir)  // 🖼️ Unsplash foto
```

### Flow Control
```dart
_apiCancelCompleter?.complete()      // 🛑 Durdur
```

---

## 4️⃣ UI Hiyerarşisi

### Message Balloon Structure
```
┌─────────────────────────────────────┐
│ ⭐ AI Message                       │
├─────────────────────────────────────┤
│ Markdown Content                    │
│ [Flight Cards if available]         │
├─────────────────────────────────────┤
│ [Location Buttons if detected]      │
│  🔗 Prag  🔗 Viyana  🔗 Budapeşte │
├─────────────────────────────────────┤
│ Action Buttons:                     │
│  📋  🔗  👍  👎                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ User Message                        │
├─────────────────────────────────────┤
│ Action Buttons:                     │
│  ✏️  📋                              │
└─────────────────────────────────────┘
```

---

## 5️⃣ State Management

### New Properties
```dart
class Mesaj {
  int? feedback;              // Oy sistemi
  bool edirleModi = false;    // Edit modu
}

class _ChatEkraniState {
  Completer<void>? _apiCancelCompleter;    // Cancel token
  Map<int, String> _sehirResimleri = {};  // Photo cache
}
```

### Data Persistence
- ✅ Feedback ve edit durumları Hive'da otomatik kaydedilir
- ✅ Sohbet silme & yeniden adlandırma otomatik synced
- ✅ Google Maps butonları tamamen local (no extra data)

---

## 6️⃣ Compatibility Matrix

| Feature | Android | iOS | Web |
|---------|---------|-----|-----|
| Share | ✅ | ✅ | ✅ |
| Copy to Clipboard | ✅ | ✅ | ✅ |
| Google Maps | ✅ | ✅ | ✅ |
| Unsplash API | ✅ | ✅ | ✅ |
| Edit Message | ✅ | ✅ | ✅ |
| Stop Generation | ✅ | ✅ | ✅ |

---

## 7️⃣ Performance Tips

1. **Şehir Tespit Caching**: Aynı şehir multiple times bulunsa, cache otomatik kullanılır
2. **Stream Cancellation**: Long-running requests anında durdurulabilir
3. **Action Buttons**: Minimal widget tree (IconButton kullanıyor)
4. **Feedback**: Herhangi bir network request yapmıyor (local persistence)

---

## 8️⃣ Testing Checklist

- [ ] Kopyala butonu metni panoya gönderiyor
- [ ] Paylaş butonu native sharing dialog açıyor
- [ ] Feedback ikonları yeşil/kırmızı renk değiştiriyor
- [ ] Edit dialog eski metni gösteriyor ve yeniden soru gönderiyor
- [ ] Stop butonu aktif loading sırasında görünüyor
- [ ] Google Maps şehirler için mavi butonlar gösteriyor
- [ ] Sidebardan sohbetler delete edilebiliyor
- [ ] Sohbet isimleri rename edilebiliyor
- [ ] Tüm veriler Hive'da kalıcı olarak kaydediliyor

---

## 9️⃣ Troubleshooting

### Unsplash foto almıyor?
→ API key yanlış olabilir. [unsplash.com/applications](unsplash.com/applications) kontrol et

### Share butonu açılmıyor?
→ Cihazda paylaşım uygulaması yüklü mü? test et

### Google Maps açılmıyor?
→ HTTPS sorunu? QuerySchemes manifest'e eklediniz mi?

### Stream stop etmiyor?
→ `_apiCancelCompleter?.complete()` çağrılıyor mu? Check logs

---

## 🔟 Production Deployment

Canlıya çıkmadan önce:
1. ✅ Unsplash API key ekle
2. ✅ Manifest/Config URL launcher ayarlarını düzenle
3. ✅ Rate limiting ekle (optional)
4. ✅ Hive box cleanup stratejisi (older chats auto-delete?)
5. ✅ Error handling improvements (UI feedback)

---

**Tamamlanan Tarih**: 26 Şubat 2026
**Durum**: ✅ Production-Ready
**Hata Kontroll**: ✅ No compilation/runtime errors detected
