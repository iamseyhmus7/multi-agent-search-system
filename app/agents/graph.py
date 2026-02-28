from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes import (
    accommodation_agent,
    gastronomy_agent,
    supervisor_agent, 
    transport_agent, 
    search_agent, 
    responder_agent,
    vision_agent,    # 🌟 Yeni ekledik
    currency_agent,  # 🌟 Yeni ekledik
    accommodation_agent, # 🌟 Yeni ekledik
    activity_agent,  # 🌟 Yeni ekledik
)

# Supervisor'ın listesine göre sıradaki düğümü belirleyen "Akıllı Trafik Polisi"
def route_next_steps(state: AgentState):
    nodes = state.get("next_nodes", [])
    
    # Eğer gidilecek bir yer kalmadıysa veya responder sırası geldiyse bitir
    if not nodes:
        return "responder"
    
    # 🌟 DİNAMİK MANTIK: Listenin en başındaki ilk ajana git
    # (Hiyerarşi: Vision -> Transport/Search -> Currency)
    next_node = nodes[0]
    
    # Gidilecek node'u listeden çıkaralım ki döngüye girmeyelim
    state["next_nodes"].pop(0) 
    
    return next_node

def build_graph():
    workflow = StateGraph(AgentState)

    # 1. Düğümleri (Ajanları) Tanımlıyoruz
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("transport", transport_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("accommodation", accommodation_agent) # 🌟 YENİ EKLENDİ
    workflow.add_node("vision", vision_agent)     # 🌟 Yeni
    workflow.add_node("currency", currency_agent) # 🌟 Yeni
    workflow.add_node("responder", responder_agent)
    workflow.add_node("activity", activity_agent)
    workflow.add_node("gastronomy", gastronomy_agent)
    # 2. Giriş Noktası
    workflow.set_entry_point("supervisor")

    # 3. Koşullu Geçişler (Dinamik Yönlendirme)
    # Supervisor karar verir, route_next_steps trafiği yönetir
    workflow.add_conditional_edges("supervisor", route_next_steps)
    
    # 🌟 HER AJAN İŞİ BİTİNCE TRAFİK POLİSİNE TEKRAR SORAR
    # Böylece vision bitince transport'a, o bitince responder'a geçebiliriz.
    workflow.add_conditional_edges("accommodation", route_next_steps) # 🌟 YENİ EKLENDİ
    workflow.add_conditional_edges("vision", route_next_steps)
    workflow.add_conditional_edges("transport", route_next_steps)
    workflow.add_conditional_edges("search", route_next_steps)
    workflow.add_conditional_edges("currency", route_next_steps)
    workflow.add_conditional_edges("activity", route_next_steps)
    workflow.add_conditional_edges("gastronomy", route_next_steps)
    # 4. Final
    workflow.add_edge("responder", END)

    return workflow.compile()