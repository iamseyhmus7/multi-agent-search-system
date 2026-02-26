import json
from datetime import datetime
from core.gemini_client import generate_text
from tools.web_search import search_web
from tools.transport_search import search_transport
from agents.state import AgentState

async def supervisor_agent(state: AgentState) -> dict:
    bugunun_tarihi = datetime.now().strftime("%Y-%m-%d")
    mevcut_yil = datetime.now().year

    prompt = f"""
    Sen bir Karar Verici ajansın. Kullanıcının girdisini analiz et.
    Tarih bağlamı: Bugün {bugunun_tarihi}. Yıl belirtilmezse tarihi {mevcut_yil} veya sonrasına göre hesapla. Geçmiş tarih oluşturma.

    Kullanıcı Girdisi: "{state['user_input']}"

    GÖREVLER:
    Eğer kullanıcı hem uçuş hem de bilgi istiyorsa (Örn: "Bileti al ve gezilecek yerleri bul"), İKİSİNİ BİRDEN listeye ekle.

    1. Uçak bileti veya uçuş isteniyorsa: Listeye "transport" ekle ve 'origin' (IATA), 'destination' (IATA), 'date' (YYYY-MM-DD) çıkar.
    2. Güncel bilgi, hava durumu veya rehber isteniyorsa: Listeye "search" ekle ve 'search_query' oluştur.
    3. Sadece basit bir sohbetse: Listeye sadece "responder" ekle.

    Sadece geçerli JSON döndür:
    {{
        "next_nodes": ["transport", "search"], 
        "origin": "IST", 
        "destination": "OTP", 
        "date": "2026-02-23", 
        "search_query": "Romanya'da gezilecek yerler"
    }}
    """
    
    response = await generate_text(prompt)
    
    try:
        cleaned = response.strip().strip("```json").strip("```")
        analysis = json.loads(cleaned)
        
        print(f"🎯 Supervisor Kararı: {analysis.get('next_nodes')}")
        print(f"🔍 Çıkarılan Veriler: {analysis}")
        
        return {
            "next_nodes": analysis.get("next_nodes", ["responder"]),
            "origin": analysis.get("origin", ""),
            "destination": analysis.get("destination", ""),
            "date": analysis.get("date", ""),
            "search_query": analysis.get("search_query", "")
        }
        
    except Exception as e:
        print(f"⚠️ Supervisor Hatası: {e}")
        return {"next_nodes": ["responder"]}

def search_agent(state: AgentState) -> dict:
    query = state.get("search_query", "") 
    print(f"🔎 Tavily Arama Yapıyor: '{query}'")
    
    if not query:
        print("⚠️ Hata: Arama sorgusu boş geldi!")
        return {"search_result": {"error": "Sorgu boş."}}
        
    try:
        result = search_web(query)
        print("📦 Tavily Sonucu Alındı!")
        return {"search_result": result}
    except Exception as e:
        print(f"❌ Tavily API Hatası: {e}")
        return {"search_result": {"error": str(e)}}

async def transport_agent(state: AgentState) -> dict:
    print(f"✈️ Amadeus Aranıyor: {state.get('origin')} -> {state.get('destination')} | {state.get('date')}")
    result = await search_transport(
        "flight", state.get("origin"), state.get("destination"), state.get("date")
    )
    print(f"📦 Amadeus Sonucu Alındı!")
    return {"transport_result": result}

import json

async def responder_agent(state: AgentState) -> dict:
    print("💬 Yanıtlayıcı Cevabı Hazırlıyor...")
    
    # 1. Verileri Al
    transport_data = state.get("transport_result", {})
    if isinstance(transport_data, str):
        try: transport_data = json.loads(transport_data)
        except: pass

    llm_icin_ozet = "Uçuş araması YAPILMADI."
    ucus_listesi = []
    
    if isinstance(transport_data, dict) and transport_data: # Veri boş değilse
        llm_icin_ozet = transport_data.get("summary", "Uçuşlar bulundu, bilet detayları kartlardadır.")
        ucus_listesi = transport_data.get("all_options", [])
    elif isinstance(transport_data, list) and transport_data:
        llm_icin_ozet = f"Kullanıcı için {len(transport_data)} adet uçuş seçeneği bulundu."
        ucus_listesi = transport_data

    # 🌟 KRİTİK DÜZELTME: DİNAMİK KURAL MANTIĞI
    # LLM'in kafasının karışmaması için kuralları duruma göre veriyoruz.
    ucus_kurali = ""
    if ucus_listesi:
        ucus_kurali = "1. Uçuş listesini detaylı metin olarak YAZMA! Ben onları görsel kartlarla göstereceğim, sen sadece genel bilgi ver (Örn: 'Şu fiyattan başlayan biletler buldum, detayları aşağıda görebilirsiniz')."
    else:
        ucus_kurali = "1. DİKKAT: Kullanıcı uçuş veya bilet İSTEMEDİ. Bu yüzden KESİNLİKLE uçuşlardan, biletlerden, görsel kartlardan veya seyahat hazırlığından BAHSETME! Sadece sorulan soruya odaklan."

    sistem_verisi = f"""
    UÇUŞ ÖZETİ:
    {llm_icin_ozet}
    
    WEB ARAMA VERİLERİ (Tavily):
    {state.get('search_result', 'Web araması yapılmadı.')}
    """
    
    prompt = f"""
    Sen akıllı ve yardımsever bir asistansın. SADECE Sistem Verilerini kullanarak cevap ver. Hayal gücünü kullanma.
    
    ÖNEMLİ KURALLAR:
    {ucus_kurali}
    2. Kullanıcıyla doğal ve samimi konuş.
    3. EĞER Sistem Verilerinde Hava Durumu bilgisi varsa veya kullanıcı bunu sorduysa, cevabının EN SONUNA şu formatta mutlaka gizli bir JSON şifresi ekle (boşluk bırakmadan):
    ###HAVA_DURUMU###[{{"sehir": "Adana", "sicaklik": "22°C", "durum": "Güneşli", "tarih": "26 Şubat 2026"}}]
    
    Sistem Verileri:
    {sistem_verisi}
    
    Kullanıcı Sorusu:
    {state.get("user_input")}
    """
    
    print("⏳ LLM'e istek gönderiliyor...")
    final_answer = await generate_text(prompt)
    print("✅ LLM'den cevap geldi!")
    
    clean_answer = final_answer.strip()

    # 3. UÇUŞ KARTI MANTIĞI (Sadece uçuş varsa çalışır)
    if ucus_listesi:
        flutter_ucuslar_listesi = []
        for i, flight in enumerate(ucus_listesi[:5]):  
            try:
                kalkis_tam = flight.get("departure_time", "00:00")
                varis_tam = flight.get("arrival_time", "00:00")
                
                ham_tarih = kalkis_tam.split("T")[0] if "T" in kalkis_tam else ""
                if ham_tarih and "-" in ham_tarih:
                    yil, ay, gun = ham_tarih.split("-")
                    tarih_duzenli = f"{gun}.{ay}.{yil}"
                else:
                    tarih_duzenli = "Belirtilmedi"
                
                kalkis_saat = kalkis_tam.split("T")[-1][:5] if "T" in kalkis_tam else kalkis_tam
                varis_saat = varis_tam.split("T")[-1][:5] if "T" in varis_tam else varis_tam
                
                fiyat = flight.get("price", "0")
                para_birimi = flight.get("currency", "EUR")

                havayolu_kodu = flight.get("airline_code", "")
                havayolu_sozlugu = {
                    "TK": "Türk Hava Yolları", "PC": "Pegasus", "A3": "Aegean Airlines",
                    "LH": "Lufthansa", "VF": "AJet", "RO": "TAROM", "XQ": "SunExpress",
                    "LO": "LOT Polish Airlines" 
                }
                havayolu_adi = havayolu_sozlugu.get(havayolu_kodu, f"{havayolu_kodu} Airlines") if havayolu_kodu else "Havayolu"

                flutter_ucuslar_listesi.append({
                    "havayolu": havayolu_adi,
                    "kalkisSaat": kalkis_saat,
                    "varisSaat": varis_saat,
                    "kalkisKod": state.get("origin", "N/A"),
                    "varisKod": state.get("destination", "N/A"),
                    "fiyat": f"{fiyat} {para_birimi}",
                    "tarih": tarih_duzenli
                })
            except Exception as e:
                print(f"⚠️ {i}. Uçuş parse hatası: {e}")
                
        if flutter_ucuslar_listesi:
            json_str = json.dumps(flutter_ucuslar_listesi)
            clean_answer += f"###UCUSLAR###{json_str}"
            print("🚀 UÇUŞ ŞİFRESİ EKLENDİ!")
            
    return {"final_answer": clean_answer}