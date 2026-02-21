import json
from core.gemini_client import generate_text
from tools.web_search import search_web
from tools.transport_search import search_transport
from agents.state import AgentState

async def supervisor_agent(state: AgentState) -> AgentState: # Dönüş tipi AgentState oldu
    prompt = f"""
    Sen bir Karar Verici (Router) ajansın. Kullanıcının girdisini analiz et ve eylemi seç.

    Kullanıcı Girdisi: "{state['user_input']}"

    KESİN KURALLAR:
    1. "transport": Kullanıcı uçak bileti veya uçuş arıyorsa. 'origin' (IATA kodu), 'destination' (IATA kodu) ve 'date' (YYYY-MM-DD) çıkar.
    2. "search": Kullanıcı hava durumu, haberler veya web'den bilgi soruyorsa. Mantıklı bir 'search_query' oluştur.
    3. "responder": Kullanıcı sadece selam veriyorsa veya sistemde toplanmış bir veri varsa.

    Sadece geçerli JSON döndür:
    {{
        "next_node": "transport" | "search" | "responder",
        "origin": "IST", 
        "destination": "ESB", 
        "date": "2026-03-21",
        "search_query": "İstanbul hava durumu"
    }}
    """
    
    response = await generate_text(prompt)
    
    try:
        cleaned = response.strip().strip("```json").strip("```")
        analysis = json.loads(cleaned)
        
        print(f"🎯 Supervisor Kararı: {analysis.get('next_node', 'responder').upper()}")
        print(f"🔍 Çıkarılan Veriler: {analysis}")
        
        # GARANTİ YÖNTEM: State'i doğrudan güncelle ve onu döndür
        state["next_node"] = analysis.get("next_node", "responder")
        state["origin"] = analysis.get("origin")
        state["destination"] = analysis.get("destination")
        state["date"] = analysis.get("date")
        state["search_query"] = analysis.get("search_query", "")
        
        return state
        
    except Exception as e:
        print(f"⚠️ Supervisor JSON Hatası: {e}")
        state["next_node"] = "responder"
        return state

def search_agent(state: AgentState) -> AgentState: # Dönüş tipi AgentState oldu
    query = state.get("search_query", "") 
    print(f"🔎 Tavily Arama Yapıyor: '{query}'")
    
    if not query:
        print("⚠️ Hata: Arama sorgusu boş geldi!")
        state["tool_result"] = {"error": "Arama sorgusu boş."}
        return state
        
    try:
        result = search_web(query)
        print("📦 Tavily Sonucu Başarıyla Alındı!")
        state["tool_result"] = result
        return state
    except Exception as e:
        print(f"❌ Tavily API Hatası: {e}")
        state["tool_result"] = {"error": f"Tavily API Hatası: {e}"}
        return state

async def transport_agent(state: AgentState) -> AgentState:
    print(f"✈️ Amadeus Aranıyor: {state.get('origin')} -> {state.get('destination')} | {state.get('date')}")
    result = await search_transport(
        "flight",
        state.get("origin"),
        state.get("destination"),
        state.get("date")
    )
    print(f"📦 Amadeus Sonucu: {result}")
    state["tool_result"] = result
    return state

async def responder_agent(state: AgentState) -> AgentState:
    print("💬 Yanıtlayıcı Cevabı Hazırlıyor...")
    tool_data = state.get("tool_result", "")
    
    prompt = f"""
    Sen uygulamanın son yanıtlayıcı ajanısın.
    
    Sistem Verisi:
    {tool_data}
    
    Kullanıcı Sorusu:
    {state.get("user_input")}
    
    Lütfen Sistem Verisi'ni kullanarak kullanıcıya samimi ve düzenli bir cevap ver. Veri "error" içeriyorsa durumu açıkla.
    """
    
    final_answer = await generate_text(prompt)
    # \n karakterlerini ve ** gibi Markdown sembollerini temizle
    clean_answer = final_answer.replace("\n", " ").replace("**", "")
    state["final_answer"] = clean_answer
    return state