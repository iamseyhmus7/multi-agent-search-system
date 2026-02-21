from typing import TypedDict, Optional , Dict, Any
class AgentState(TypedDict, total = False):
    user_input : str 
    # Supervisor Kararı 
    next_node:Optional[str]
    # Ulaşım(Sadece Uçuş)
    origin: Optional[str]
    destination: Optional[str]
    date: Optional[str]

    # Genel Arama 
    search_query: Optional[str]
    # Araç Sonuçları ve Nihai Sonuçları
    tool_result:Optional[Dict[str, Any]]
    final_answer: Optional[str]
    