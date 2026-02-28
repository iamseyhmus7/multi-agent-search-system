import os
import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)

# .env dosyasından anahtarı alıyoruz
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")

async def search_ticketmaster_events(city_name: str, start_date: str, end_date: str) -> list:
    """Ticketmaster API üzerinden canlı etkinlikleri (Konser, Maç, Tiyatro) çeker."""
    if not TICKETMASTER_API_KEY:
        logger.warning("⚠️ Ticketmaster API Key eksik!")
        return []

    logger.info(f"🎸 Ticketmaster Aranıyor: {city_name} | {start_date} - {end_date}")
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    
    # Ticketmaster tarihleri 'YYYY-MM-DDTHH:mm:ssZ' formatında ister
    start_dt = f"{start_date}T00:00:00Z" if start_date else ""
    end_dt = f"{end_date}T23:59:59Z" if end_date else ""

    params = {
        "apikey": TICKETMASTER_API_KEY,
        "city": city_name,
        "sort": "date,asc",
        "size": 5 # En popüler 5 etkinlik yeterli
    }
    if start_dt: params["startDateTime"] = start_dt
    if end_dt: params["endDateTime"] = end_dt

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code != 200:
                logger.error(f"❌ Ticketmaster Hatası: {resp.text}")
                return []
            
            events = resp.json().get("_embedded", {}).get("events", [])
            sonuclar = []
            
            for event in events:
                fiyat_araligi = event.get("priceRanges", [])
                fiyat_metni = "Fiyat belirtilmemiş"
                if fiyat_araligi:
                    min_fiyat = fiyat_araligi[0].get("min", "")
                    max_fiyat = fiyat_araligi[0].get("max", "")
                    kur = fiyat_araligi[0].get("currency", "")
                    fiyat_metni = f"{min_fiyat} - {max_fiyat} {kur}"
                    
                sonuclar.append({
                    "Etkinlik Adı": event.get("name"),
                    "Tarih": event.get("dates", {}).get("start", {}).get("localDate", ""),
                    "Fiyat": fiyat_metni
                })
            return sonuclar
    except Exception as e:
        logger.error(f"❌ Ticketmaster Bağlantı Hatası: {e}")
        return []

async def search_tours_and_museums(city_name: str) -> str:
    """Tavily web aramasıyla şehirdeki en iyi müzeleri ve rehberli turları bulur."""
    logger.info(f"🏛️ Müzeler ve Turlar aranıyor: {city_name}")
    try:
        from tools.web_search import search_web
        query = f"Top 3 museums, guided tours and sightseeing attractions in {city_name} with average ticket prices"
        result = await asyncio.to_thread(search_web, query) # Senkron fonksiyonu asenkron çalıştırır
        return result
    except Exception as e:
        logger.warning(f"⚠️ Müze arama hatası: {e}")
        return "Müze bilgisi alınamadı."

async def get_all_activities(city_name: str, start_date: str, end_date: str) -> dict:
    """Akıllı Alt-Yönlendirme: Konserleri ve Müzeleri PARALEL çalıştırır."""
    if not city_name:
        return {"hata": "Şehir adı belirtilmedi."}
        
    logger.info("⚡ Etkinlik ve Müzeler paralel olarak çekiliyor...")
    
    # İki API'yi aynı anda ateşliyoruz (Süreyi yarı yarıya düşürür!)
    tm_task = search_ticketmaster_events(city_name, start_date, end_date)
    tours_task = search_tours_and_museums(city_name)
    
    tm_results, tours_results = await asyncio.gather(tm_task, tours_task)
    
    return {
        "Canlı Etkinlikler (Ticketmaster)": tm_results if tm_results else "Bu tarihlerde konser veya maç bulunamadı.",
        "Müzeler ve Turlar (Web)": tours_results
    }