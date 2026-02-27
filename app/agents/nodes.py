import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from tools.finance_tools import get_exchange_rate
from core.gemini_client import generate_text
from tools.web_search import search_web
from tools.transport_search import search_hotels, search_transport
from tools.wikipedia import search_wikipedia
from agents.state import AgentState

# 🌟 Logging Konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def supervisor_agent(state: AgentState) -> dict:
    bugunun_tarihi = datetime.now().strftime("%Y-%m-%d")
    mevcut_yil = datetime.now().year
    image_exists = "EVET" if state.get("image_input") else "HAYIR"
    user_input = state.get("user_input", "")
    # 🌟 YENİ: Geçmiş sohbeti state'den alıyoruz
    chat_history = state.get("chat_history", "Geçmiş sohbet yok.")
    prompt = f"""
    Sen dünyanın en gelişmiş Asistan ve Seyahat Orkestra Şefisin (Travel Orchestrator). 
    Görevin: Kullanıcı girdisini analiz etmek, SADECE GEREKLİ uzman ajanları sıraya koymak ve parametreleri HATASIZ çıkarmaktır.

    [BAĞLAM BİLGİLERİ]
    - Bugünün Tarihi: {bugunun_tarihi}
    - Sistemde Görsel Var mı?: {image_exists}
    - Kullanıcı Mesajı: "{user_input}"

    [GEÇMİŞ SOHBET HAFIZASI]
    {chat_history}

    [AJAN SEÇİM KURALLARI]
    1. vision: Eğer görsel ('EVET') varsa, mutlaka İLK SIRAYA "vision" ekle.
    2. transport: Kullanıcı uçuş, bilet veya "nasıl giderim" diyorsa ekle.
    3. search: Hava durumu, gezilecek yerler, güncel bilgi veya rehberlik gerekiyorsa ekle.
    4. currency: Döviz, kur, para birimi çevirme veya "kaç TL" gibi sorularda ekle.
    5. responder: Her zaman listenin EN SONUNDA olmalı veya sohbetse tek başına seçilmeli.
    6. accommodation: Kullanıcı otel, konaklama, nerede kalınır, airbnb gibi yer arayışındaysa ekle.
    [VERİ ÇIKARMA KURALLARI - ÇOK KRİTİK]
    [VERİ ÇIKARMA KURALLARI - ÇOK KRİTİK]
    - DÖVİZ (currency): Kullanıcının mesajındaki MİKTARI bul ve 'amount' alanına yaz (Örn: "75 Pound" -> 75.0). 
      ⚠️ PARA BİRİMİ KURALI: Kullanıcı ne derse desin (Pound, Sterlin, Dolar, Yen, Ruble vs.), sen bu kelimeyi KESİNLİKLE dünyaca geçerli 3 HARFLİ ISO KODUNA çevirip 'from_currency' alanına yazacaksın. (Örn: Pound -> GBP, Japon Yeni -> JPY, Euro -> EUR). Asla kelimenin kendisini yazma!
    - IATA KODLARI (transport): 'origin' ve 'destination' her zaman 3 HARFLİ IATA KODU olmalıdır (Örn: IST, FCO). Asla tam isim yazma!
    - TARİH: "Gelecek hafta", "Yarın" gibi ifadeleri bugüne ({bugunun_tarihi}) göre YYYY-MM-DD formatında kesin tarihe çevir.

    [ÇIKTI FORMATI]
    Aşağıdaki JSON şablonunu KULLANICI MESAJINA GÖRE DİNAMİK OLARAK DOLDUR. Şablondaki değerleri uydurma!
    Sadece geçerli bir JSON objesi döndür:
    {{
        "next_nodes": ["gerekli_ajanlar", "responder"],
        "origin": "",
        "destination": "",
        "date": "",
        "search_query": "",
        "amount": 0.0,
        "from_currency": ""
    }}
    """

    try:
        logger.info("🧠 Supervisor: Kullanıcı mesajı analiz ediliyor...")
        response = await generate_text(prompt)
        
        # JSON temizliği (Markdown taglerini uçur)
        cleaned = response.strip().replace("```json", "").replace("```", "").strip()
        analysis = json.loads(cleaned)
        
        nodes = analysis.get("next_nodes", ["responder"])
        
        # 🛡️ Manuel Güvenlik Kilidi: Görsel varken model unutursa zorla başa ekle
        if state.get("image_input") and "vision" not in nodes:
            nodes.insert(0, "vision")
            
        logger.info(f"🎯 Supervisor Kararı: {nodes}")
        
        # 🛡️ Güvenli Tip Dönüşümleri (LLM boş veya null gönderirse çökmemesi için)
        try:
            amount_val = float(analysis.get("amount") or 1.0)
            if amount_val == 0.0: amount_val = 1.0 # Eğer model 0.0 bıraktıysa 1 kabul et
        except (ValueError, TypeError):
            amount_val = 1.0

        return {
            "next_nodes": nodes,
            "origin": str(analysis.get("origin") or "").upper().strip(),
            "destination": str(analysis.get("destination") or "").upper().strip(),
            "date": str(analysis.get("date") or "").strip(),
            "search_query": str(analysis.get("search_query") or "").strip(),
            "amount": amount_val,
            "from_currency": str(analysis.get("from_currency") or "EUR").upper().strip()
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"⚠️ Supervisor JSON Parse Hatası: {e} | Gelen Yanıt: {response}")
        return {"next_nodes": ["responder"]}
    except Exception as e:
        logger.error(f"⚠️ Supervisor Genel Hatası: {e}")
        return {"next_nodes": ["responder"]}
    
def search_agent(state: AgentState) -> dict:
    """Web arama ve encyclopeadic bilgi kaynakları (Tavily + Wikipedia)"""
    query = state.get("search_query", "") 
    logger.info(f"🔎 Tavily Arama Yapıyor: '{query}'")
    
    if not query:
        logger.warning("⚠️ Hata: Arama sorgusu boş geldi!")
        return {"search_result": {"error": "Sorgu boş.", "source": "none"}}
        
    try:
        # 🌐 PLAN A: Tavily Web Search ile güncel sonuçlar
        result = search_web(query)
        logger.info("📆 Tavily Sonucu Alındı!")
        return {"search_result": {**result, "source": "tavily"}}
        
    except Exception as e:
        logger.warning(f"⚠️ Tavily Hatası: {e}. Wikipedia'ya dönülüyor...")
        
        try:
            # 🌐 PLAN B: Wikipedia'dan tarihi/genel bilgi
            wiki_result = search_wikipedia(query)
            logger.info("📋 Wikipedia Sonucu Alındı!")
            return {"search_result": {"summary": wiki_result, "source": "wikipedia"}}
            
        except Exception as wiki_error:
            logger.error(f"❌ Her iki kaynak da başarısız: {wiki_error}")
            return {"search_result": {"error": f"Arama başarısız: {str(wiki_error)}", "source": "none"}}

async def transport_agent(state: AgentState) -> dict:
    origin = state.get("origin", "").upper().strip()
    destination = state.get("destination", "").upper().strip()
    date = state.get("date", "").strip()

    # 🛡️ GÜVENLİK DUVARI VE PROAKTİF SORU
    if not origin or not destination or not date:
        eksikler = []
        if not origin: eksikler.append("nereden uçacağı (kalkış şehri)")
        if not destination: eksikler.append("nereye gideceği (varış şehri)")
        if not date: eksikler.append("hangi tarihte gideceği")
        
        eksik_metni = " ve ".join(eksikler)
        logger.warning(f"⚠️ Uçuş için eksik bilgiler var: {eksik_metni}")
        
        # 🌟 DİNAMİK TALİMAT: LLM'i yönlendiriyoruz
        return {
            "transport_result": {
                "gizli_talimat": f"Kullanıcı seyahat etmek istiyor ancak {eksik_metni} eksik. Ona kibar ve samimi bir dille eksik olan bu bilgileri sor.",
                "all_options": []
            }
        }

    logger.info(f"✈️ Amadeus Aranıyor: {origin} -> {destination} | {date}")
    
    try:
        result = await search_transport("flight", origin, destination, date)
        logger.info(f"📦 Amadeus Uçuş Sonucu Alındı!")
        return {"transport_result": result}
    except Exception as e:
        logger.error(f"❌ Amadeus Hatası: {e}")
        return {"transport_result": {"error": f"Uçuş bulunamadı: {str(e)}", "all_options": []}}

async def accommodation_agent(state: AgentState) -> dict:
    """Gidilecek şehirdeki gerçek konaklama (otel) seçeneklerini bulur."""
    logger.info("🏨 Accommodation Agent: Otel araması başlatılıyor...")
    
    destination = state.get("destination", "").upper().strip()
    
    # 🛡️ EKSİK BİLGİ KONTROLÜ: Şehir yoksa LLM'e sor dedirt!
    if len(destination) != 3:
        logger.warning(f"⚠️ Otel araması için hedef şehir eksik: '{destination}'")
        return {"accommodation_result": "GİZLİ_TALİMAT: Kullanıcıya otel bulabilmem için HANGİ ŞEHRE gideceğini doğal bir dille sor."}
        
    logger.info(f"🏨 Aranıyor: {destination} şehrindeki oteller...")
    
    try:
        # Gerçek Amadeus Otel API'sini çağırıyoruz
        result = await search_hotels(destination)
        
        if not result:
            return {"accommodation_result": f"{destination} şehrinde şu an Amadeus sisteminde uygun otel bulunamadı."}
            
        logger.info("✅ Gerçek oteller başarıyla state'e aktarıldı!")
        return {"accommodation_result": result}
        
    except Exception as e:
        logger.error(f"❌ Otel Arama Hatası: {e}")
        return {"accommodation_result": "Oteller aranırken sistemsel bir sorun oluştu."}
    
async def vision_agent(state: AgentState) -> dict:
    """Gemini Vision: Görseli analiz edip yeri/nesneyi tanıyıp otomatik arama sorgusu oluştur"""
    logger.info("👁️ Vision Agent: Görsel analiz ediliyor...")
    
    image_data = state.get("image_input")
    if not image_data:
        logger.warning("⚠️ Görsel verisi eksik.")
        return {"vision_result": "Görsel verisi eksik."}
    
    prompt = """
    Bu fotoğraftaki turistik yer, tarihi eser veya şehür neresidir? 
    İsmini net belirt ve kısa cümlelerle bilgi ver. 
    Eğer bir şehür ise, o şehönü ziyaret etmek için ne tavsiye edersin?
    """
    
    try:
        # 🌟 GERÇEK ÇAĞRI: Multi-modal desteği ile görseli gönderiyoruz
        analysis_result = await generate_text(prompt, image_b64=image_data)
        logger.info("✅ Görsel Analiz Tamamlandı")
        
        return {
            "vision_result": analysis_result,
            "search_query": f"{analysis_result} seyahat rehberi ve gezilecek yerler"
        }
        
    except Exception as e:
        logger.error(f"❌ Görsel Analiz Hatası: {e}")
        return {
            "vision_result": f"Görsel analiz başarısız: {str(e)}",
            "search_query": ""
        }

async def currency_agent(state: AgentState) -> dict:
    logger.info("💰 Currency Agent: Kur hesaplaması yapılıyor...")
    
    amount = float(state.get("amount", 1.0))
    raw_currency = state.get("from_currency")
    
    if not raw_currency:
        logger.warning("⚠️ Supervisor para birimini state'e aktaramadı!")
        return {"currency_result": "Hangi para birimini çevirmek istediğini anlayamadım."}
        
    # Supervisor'dan gelen veriyi temizle ve 3 harfe zorla
    from_curr = str(raw_currency).upper().strip()

    # 🛡️ DİNAMİK KONTROL: Eğer Supervisor inatla 3 harfli kod göndermediyse işlemi durdur
    if len(from_curr) != 3:
        logger.error(f"❌ Supervisor hatalı format gönderdi: {from_curr}")
        return {"currency_result": f"Sistemsel bir hata: Para birimi kodu geçersiz ({from_curr})."}

    if amount <= 0:
        return {"currency_result": "Geçersiz miktar. Pozitif bir değer girin."}
    
    logger.info(f"💰 Kur dönüştürme: {amount} {from_curr} -> TRY")
    
    try:
        result = get_exchange_rate(amount, from_curr, "TRY")
        logger.info(f"✅ Kur Dönüşümü: {result}")
        return {"currency_result": result}
    except Exception as e:
        logger.error(f"❌ Kur Hesaplama Hatası: {e}")
        return {"currency_result": f"Kur bilgisi alınamadı. Detay: {str(e)}"}
    

async def responder_agent(state: AgentState) -> dict:
    """Son aş: Tüm ajanlardan gelen veriyi birleştirir, final yanıt oluştur"""
    logger.info("📃 Responder: Final cevap hazırlanıyor...")
    
    # 1. Tüm Verileri Havuzda Topla (Güvenli Parse)
    transport_data = state.get("transport_result", {})
    if isinstance(transport_data, str):
        try: 
            transport_data = json.loads(transport_data)
        except json.JSONDecodeError:
            logger.warning("⚠️ Transport data JSON parse hatası")
            transport_data = {}

    vision_data = state.get("vision_result") or "Analiz edilecek bir görsel gönderilmedi."
    currency_data = state.get("currency_result") or "Döviz sorgusu yapılmadı."
    search_data = state.get("search_result") or {}
    
    # 🌟 YENİ EKLEME: Otel Verisini Çek
    accommodation_data = state.get("accommodation_result") or "Otel araması yapılmadı."
    
    # Search result'ı güvenle string'e çevir
    if isinstance(search_data, dict):
        search_str = json.dumps(search_data, ensure_ascii=False)
    else:
        search_str = str(search_data)

    llm_icin_ozet = "Uçuş araması yapılmadı."
    ucus_listesi = []
    
    if isinstance(transport_data, dict) and transport_data and "error" not in transport_data:
        llm_icin_ozet = transport_data.get("summary", "Uçuşlar bulundu, bilet detayları kartlardadır.")
        ucus_listesi = transport_data.get("all_options", [])
    elif isinstance(transport_data, list) and transport_data:
        llm_icin_ozet = f"Kullanıcı için {len(transport_data)} adet uçuş seçeneği bulundu."
        ucus_listesi = transport_data

    # 🌟 YENİ EKLEME: GİZLİ TALİMATLARI (SORULARI) YAKALA
    gizli_talimatlar = []
    
    if isinstance(transport_data, dict) and transport_data.get("gizli_talimat"):
        gizli_talimatlar.append(transport_data.get("gizli_talimat"))
        
    if isinstance(accommodation_data, str) and "GİZLİ_TALİMAT" in accommodation_data:
        gizli_talimatlar.append(accommodation_data.replace("GİZLİ_TALİMAT:", "").strip())

    talimat_metni = ""
    if gizli_talimatlar:
        talimat_metni = "\n🚨 DİKKAT GİZLİ GÖREV: Aşağıdaki eksik bilgileri kullanıcıya DOĞAL, SOHBET EDER GİBİ SOR:\n- " + "\n- ".join(gizli_talimatlar) + "\n(Asla 'sistem verilerimde yok' deme, doğrudan bir insan gibi soruyu yönelt!)"

    # 🌟 DİNAMİK KURAL MANTIĞI (Senin eski kodun, aynen duruyor)
    ucus_kurali = ""
    if ucus_listesi:
        ucus_kurali = "1. Uçuş listesini detaylı metin olarak YAZMA! Ben kartlarla göstereceğim. Sen sadece: 'En uygun biletleri aşağıda görebilirsiniz' gibi kısaca söyle."
    else:
        ucus_kurali = "1. DİKKAT: Uçuş araması yapılmadı. KESİNLİKLE uçuş veya biletlerden BAHSETME!"

    # 2. Sistem Verisi Havuzu (Otel eklendi)
    sistem_verisi = f"""
    GÖRSEL ANALİZ: {vision_data}
    DÖVİZ BİLGİSİ: {currency_data}
    OTEL BİLGİLERİ: {accommodation_data if not gizli_talimatlar else 'Eksik bilgi nedeniyle aranamadı.'}
    UÇUŞ ÖZETİ: {llm_icin_ozet}
    WEB/REHBER BİLGİLERİ: {search_str}
    """
    chat_history = state.get("chat_history", "")
    prompt = f"""
    Sen uzman ve yardımsever bir seyahat asistanısın. SADECE Sistem Verilerini kullanarak cevap ver.
    
    ÖNEMLİ KURALLAR:
    {ucus_kurali}
    2. GÖRSEL varsa: 'Gönderdiğin fotoğraftaki yer... neresidir' diye açıkla.
    3. DÖVİZ varsa: Kuru mutlaka belirt.
    4. Doğal ve samimi bir dille konuş.
    5. EĞER harita/konum bilgisi verdiysen, sonuna bu formatta ekle:
    ###HAVA_DURUMU###[{{"sehir": "Şehir", "sicaklik": "22°C", "durum": "Güneşli"}}]
    {talimat_metni} 
    
    Sistem Verileri:
    {sistem_verisi}
    
    [GEÇMİŞ SOHBET]
    {chat_history}
    
    Kullanıcı Sorusu:
    {state.get("user_input", "")}
    """
    
    try:
        logger.info("⏳ LLM'e final isteği gönderiliyor...")
        final_answer = await generate_text(prompt)
        clean_answer = final_answer.strip() if final_answer else ""
        logger.info("✅ Final cevap oluşturuldu!")
        
    except Exception as e:
        logger.error(f"❌ LLM Hatası: {e}")
        clean_answer = "Maalesef cevap oluşturulamadı. Lütfen daha sonra tekrar deneyin."

    # 3. UÇUŞ KARTI MANTIĞI (Senin eserin, bir noktasına bile dokunulmadı!)
    if ucus_listesi:
        flutter_ucuslar_listesi = []
        
        for i, flight in enumerate(ucus_listesi[:10]):  # max 10 uçuş
            try:
                # Tarih-Saat Parse
                kalkis_tam = flight.get("departure_time") or flight.get("departure") or "00:00"
                varis_tam = flight.get("arrival_time") or flight.get("arrival") or "00:00"
                
                # ISO format'ı işleyin (YYYY-MM-DDTHH:MM:SS)
                ham_tarih = kalkis_tam.split("T")[0] if "T" in str(kalkis_tam) else ""
                if ham_tarih and "-" in ham_tarih:
                    try:
                        yil, ay, gun = ham_tarih.split("-")
                        tarih_duzenli = f"{gun}.{ay}.{yil}"
                    except:
                        tarih_duzenli = ham_tarih
                else:
                    tarih_duzenli = "Tarih N/A"
                
                kalkis_saat = str(kalkis_tam).split("T")[-1][:5] if "T" in str(kalkis_tam) else str(kalkis_tam)[:5]
                varis_saat = str(varis_tam).split("T")[-1][:5] if "T" in str(varis_tam) else str(varis_tam)[:5]
                
                fiyat = str(flight.get("price") or "0")
                para_birimi = flight.get("currency", "EUR").upper()
                fiyat_degeri = int(float(fiyat))
                havayolu_kodu = flight.get("airline_code") or flight.get("airline") or ""
                
                # Havayolu Sözlüğü
                havayolu_sozlugu = {
                    "TK": "Türk Hava Yolları", "PC": "Pegasus", "A3": "Aegean Airlines",
                    "LH": "Lufthansa", "VF": "AJet", "RO": "TAROM", "XQ": "SunExpress",
                    "LO": "LOT Polish Airlines", "IB": "İberia", "AF": "Air France"
                }
                havayolu_adi = havayolu_sozlugu.get(havayolu_kodu.upper(), f"{havayolu_kodu} Airlines") if havayolu_kodu else "Havayolu"

                flutter_ucuslar_listesi.append({
                    "havayolu": havayolu_adi,
                    "kalkisSaat": kalkis_saat,
                    "varisSaat": varis_saat,
                    "kalkisKod": state.get("origin", "N/A").upper(),
                    "varisKod": state.get("destination", "N/A").upper(),
                    "fiyat": f"{fiyat_degeri} {para_birimi}",
                    "tarih": tarih_duzenli
                })
                
            except Exception as e:
                logger.warning(f"⚠️ {i}. Uçuş parse hatası: {e}")
                continue
                
        if flutter_ucuslar_listesi:
            json_str = json.dumps(flutter_ucuslar_listesi, ensure_ascii=False)
            clean_answer += f"###UCUSLAR###{json_str}"
            logger.info("🚀 UÇUŞ KARTLARI ŞİFRESİ EKLENDİ!")
            
    return {"final_answer": clean_answer}