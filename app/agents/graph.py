from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes import supervisor_agent, transport_agent, search_agent, responder_agent

# Supervisor'ın listesine göre sıradaki düğümü belirleyen fonksiyon
def route_next_steps(state: AgentState):
    nodes = state.get("next_nodes", [])
    
    # Liste boşsa veya responder varsa direkt bitir
    if not nodes or "responder" in nodes:
        return "responder"
        
    # Eğer ikisi de varsa, önce transport'a git, o bitince search'e geçeceğiz
    if "transport" in nodes:
        # Gidilen node'u listeden çıkaralım ki sonsuz döngü olmasın
        state["next_nodes"].remove("transport")
        return "transport"
        
    if "search" in nodes:
        state["next_nodes"].remove("search")
        return "search"
        
    return "responder"

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("transport", transport_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("responder", responder_agent)

    workflow.set_entry_point("supervisor")

    # Supervisor'dan çıkışta dinamik yönlendirme
    workflow.add_conditional_edges("supervisor", route_next_steps)
    
    # Alt ajanlar işini bitirince TEKRAR yönlendirme kontrolüne girer 
    # (Böylece transport bitince search'e, search bitince responder'a gider)
    workflow.add_conditional_edges("transport", route_next_steps)
    workflow.add_conditional_edges("search", route_next_steps)

    workflow.add_edge("responder", END)

    return workflow.compile()