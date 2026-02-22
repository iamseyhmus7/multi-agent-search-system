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

async def responder_agent(state: AgentState) -> dict:
    print("💬 Yanıtlayıcı Cevabı Hazırlıyor...")
    
    # İki farklı kaynaktan gelen verileri birleştiriyoruz
    sistem_verisi = f"""
    UÇUŞ VERİLERİ (Amadeus):
    {state.get('transport_result', 'Uçuş araması yapılmadı.')}
    
    WEB ARAMA VERİLERİ (Tavily):
    {state.get('search_result', 'Web araması yapılmadı.')}
    """
    
    prompt = f"""
    Sen uzman bir seyahat asistanısın. SADECE aşağıdaki Sistem Verilerini kullanarak cevap ver. Kendi hafızandan bilgi uydurma.
    Veriler "error" içeriyorsa veya "yapılmadı" diyorsa durumu kullanıcıya açıkla.
    
    ÖNEMLİ KURALLAR:
    1. Cevabı her zaman Türkçe ver.
    2. Kullanıcıyla samimi ama profesyonel bir tonda konuş.
    3. KRİTİK BİLGİLERİ VURGULA: Üniversite isimleri, şehir adları, para miktarları veya önemli tarihleri mutlaka Markdown kullanarak kalınlaştır (Örn: **Bükreş Üniversitesi**, **150€**).
    4. Listeleri düzenli madde işaretleri (-) ile alt alta sun.
    
    Sistem Verileri:
    {sistem_verisi}
    
    Kullanıcı Sorusu:
    {state.get("user_input")}
    """
    
    final_answer = await generate_text(prompt)
    
    # DİKKAT: replace("**", "") ve replace("\n", " ") kısımlarını tamamen KALDIRDIK!
    # Sadece baştaki ve sondaki gereksiz boşlukları temizliyoruz.
    clean_answer = final_answer.strip()
    
    return {"final_answer": clean_answer}