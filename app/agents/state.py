from typing import TypedDict, Optional, Dict, Any, List

class AgentState(TypedDict, total=False):
    # --- Kullanıcı Girdileri ---
    user_input: str 
    image_input: Optional[str]  # 🌟 YENİ: Base64 formatında görsel veya dosya yolu
    
    # --- Akış Kontrolü ---
    # Supervisor Kararı (Örn: ["vision", "transport", "search"])
    next_nodes: Optional[List[str]]
    
    # --- Ulaşım Parametreleri (Amadeus) ---
    origin: Optional[str]
    destination: Optional[str]
    date: Optional[str]

    # Finans Parametreleri (Frankfurter)
    amount: Optional[float]
    from_currency: Optional[str]
    
    # YENİ: Otel arama sonuçları
    accommodation_result: Optional[Any]  
    # --- Otel Parametreleri ---
    check_in_date: Optional[str]
    check_out_date: Optional[str]
    adults: Optional[int]
    
    # --- Arama Parametreleri (Tavily / Wikipedia) ---
    search_query: Optional[str]

    # Activity Agent için eklenen parametreler
    # 🏙️ Ticketmaster için şehrin tam adı (Örn: Paris)
    city_name: Optional[str]
    # 🎢 Etkinlik, müze ve konser sonuçları        
    activity_result: Optional[Any]  

    # 🌟 YENİ: Gastronomi Agent parametresi
    gastronomy_result: Optional[Any]  # 🍝 Restoran önerileri ve yerel mutfak bilgileri

    # 🧠 YENİ: Geçmiş sohbet hafızası
    chat_history: Optional[str]
    
    # --- 📦 Ajan Hafıza Kutuları (Sonuçlar) ---
    transport_result: Optional[Dict[str, Any]]
    search_result: Optional[Dict[str, Any]]
    currency_result: Optional[Any]  # 🌟 YENİ: Döviz/Kur bilgisi saklama alanı
    vision_result: Optional[str]    # 🌟 YENİ: Görsel analizden gelen metin açıklaması
    hava_durumu: Optional[List[Dict[str, Any]]]  # 🌜 YENİ: Hava durumu kardları
    
    # --- Nihai Yanıt ---
    final_answer: Optional[str]