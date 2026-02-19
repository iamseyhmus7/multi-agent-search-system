from core.gemini_client import generate_text
from tools.web_search import search_web
from agents.state import AgentState


import json
from core.gemini_client import generate_text
from agents.state import AgentState

def intent_detection(state: AgentState) -> AgentState:
    prompt = f"""
    Sen akıllı bir sorgu analizatörüsün. Kullanıcının girdisini analiz et ve aşağıdaki JSON formatında yanıt ver.
    
    Görevlerin:
    1. 'intent': Bu girdi bir bilgi arayışı mı ('search') yoksa genel bir sohbet mi ('general')?
    2. 'search_query': Eğer intent 'search' ise, arama motorundan en iyi sonucu almak için bu sorguyu yeniden yaz. 
       - Arama motorlarının anlayacağı net anahtar kelimeler kullan.
    
    Kullanıcı Girdisi: "{state['user_input']}"
    
    Sadece aşağıdaki formatta geçerli bir JSON dön, başka hiçbir açıklama yapma:
    {{
        "intent": "search",
        "search_query": "Galatasaray last match results"
    }}
    """
    
    response = generate_text(prompt)
    
    try:
        # LLM'den gelen JSON'ı parse et (Eğer model başında/sonunda markdown ```json kullanırsa temizlemek gerekebilir)
        cleaned_response = response.strip().strip('```json').strip('```')
        analysis = json.loads(cleaned_response)
        
        state["intent"] = analysis.get("intent", "general").lower()
        state["search_query"] = analysis.get("search_query", state["user_input"])
        
    except json.JSONDecodeError:
        # JSON parse hatası olursa varsayılan (fallback) davranış
        state["intent"] = "search" if "search" in response.lower() else "general"
        state["search_query"] = state["user_input"]
        
    return state

def tool_execution(state:AgentState) -> AgentState:
    # Kullanıcının ham metnini değil, LLM'in düzelttiği (örn: Galatasaray içeren) sorguyu ara
    query_to_search = state.get("search_query", state["user_input"])
    result = search_web(query_to_search)
    state["tool_result"] = result
    return state

def final_response(state: AgentState) -> AgentState:
    if state["intent"] == "search":
        results = state["tool_result"]["results"]
        formatted_context = ""
        for r in results:
            formatted_context += f"Title: {r['title']}\n"
            formatted_context += f"Content: {r['content']}\n\n"
        prompt = f"""
You are a factual AI assistant.

ONLY use the information provided below.
DO NOT use your own knowledge.
If the answer is not in the search results, say you don't know.

SEARCH RESULTS:
{formatted_context}
USER QUESTION:
{state["user_input"]}
Provide a clear and concise answer.
"""
    else:
        prompt = state["user_input"]
    
    state["final_answer"] = generate_text(prompt)
    return state