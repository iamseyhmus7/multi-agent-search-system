from typing import TypedDict, Optional, Dict, Any, List

class AgentState(TypedDict, total=False):
    user_input: str 
    
    # Supervisor Kararı Artık Bir LİSTE (Örn: ["transport", "search"])
    next_nodes: Optional[List[str]]
    
    # Ulaşım (Sadece Uçuş)
    origin: Optional[str]
    destination: Optional[str]
    date: Optional[str]

    # Genel Arama 
    search_query: Optional[str]
    
    # --- YENİ DEĞİŞİKLİK: Her Aracın Kendi Hafıza Kutusu ---
    transport_result: Optional[Dict[str, Any]]
    search_result: Optional[Dict[str, Any]]
    
    final_answer: Optional[str]