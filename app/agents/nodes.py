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

    # 🌟 KRİTİK DÜZELTME: Yapay zekanın çökmemesi için veriyi ikiye bölüyoruz!
    # A) Yapay Zekanın Okuyacağı Kısa Özet (Sadece konuşması için)
    llm_icin_ozet = "Uçuş araması yapılmadı."
    # B) Flutter'ın Kart Çizeceği Detaylı Liste
    ucus_listesi = []
    
    if isinstance(transport_data, dict):
        # Sadece "summary" kısmını LLM'e veriyoruz, böylece anında cevap üretiyor!
        llm_icin_ozet = transport_data.get("summary", "Uçuşlar bulundu, bilet detayları kartlardadır.")
        ucus_listesi = transport_data.get("all_options", [])
    elif isinstance(transport_data, list):
        llm_icin_ozet = f"Kullanıcı için {len(transport_data)} adet uçuş seçeneği bulundu."
        ucus_listesi = transport_data

    # 2. LLM'e Sor (Sadece kısa özeti gönderiyoruz)
    sistem_verisi = f"""
    UÇUŞ ÖZETİ:
    {llm_icin_ozet}
    
    WEB ARAMA VERİLERİ (Tavily):
    {state.get('search_result', 'Web araması yapılmadı.')}
    """
    
    prompt = f"""
    Sen uzman bir seyahat asistanısın. SADECE Sistem Verilerini kullanarak cevap ver.
    ÖNEMLİ KURALLAR:
    1. Uçuş listesini detaylı metin olarak YAZMA! Ben onları görsel kartlarla göstereceğim, sen sadece genel bilgi ver (Örn: "Şu fiyattan başlayan biletler buldum, detayları aşağıda görebilirsiniz").
    2. Kullanıcıyla samimi konuş.
    
    Sistem Verileri:
    {sistem_verisi}
    
    Kullanıcı Sorusu:
    {state.get("user_input")}
    """
    
    print("⏳ LLM'e istek gönderiliyor... (Sistem burada donuyorsa API'de sorun vardır)")
    final_answer = await generate_text(prompt)
    print("✅ LLM'den cevap geldi!")
    
    clean_answer = final_answer.strip()

    # 3. ŞİFRELİ UÇUŞ KARTI MANTIĞI (Flutter için)
    if ucus_listesi:
        flutter_ucuslar_listesi = []
        for i, flight in enumerate(ucus_listesi[:5]):  
            try:
                kalkis_tam = flight.get("departure_time", "00:00")
                varis_tam = flight.get("arrival_time", "00:00")
                
                # Tarihi Güvenlice Al
                ham_tarih = kalkis_tam.split("T")[0] if "T" in kalkis_tam else ""
                if ham_tarih and "-" in ham_tarih:
                    yil, ay, gun = ham_tarih.split("-")
                    tarih_duzenli = f"{gun}.{ay}.{yil}"
                else:
                    tarih_duzenli = "Belirtilmedi"
                
                # Saati Al
                kalkis_saat = kalkis_tam.split("T")[-1][:5] if "T" in kalkis_tam else kalkis_tam
                varis_saat = varis_tam.split("T")[-1][:5] if "T" in varis_tam else varis_tam
                
                # Fiyat
                fiyat = flight.get("price", "0")
                para_birimi = flight.get("currency", "EUR")

                # Havayolu Eşleştirme
                havayolu_kodu = flight.get("airline_code", "")
                havayolu_sozlugu = {
                    "TK": "Türk Hava Yolları", "PC": "Pegasus", "A3": "Aegean Airlines",
                    "LH": "Lufthansa", "VF": "AJet", "RO": "TAROM", "XQ": "SunExpress",
                    "LO": "LOT Polish Airlines" # Senin uçuşta LO çıkmıştı!
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
            print("🚀 ŞİFRE EKLENDİ! Flutter uçuş kartlarını çizecek!")
            
    return {"final_answer": clean_answer}