import asyncio
import httpx
import logging
from tools.providers.flight_amadeus import amadeus_flight_provider
from utils.flight_utils import calculate_duration_minutes, count_stops

# 🌟 AMADEUS CLIENT IMPORTU
# Eğer amadeus_client.py dosyan 'tools' klasöründeyse böyle kalabilir. 
# Farklı bir yerdeyse (örn: core) burayı kendi yapına göre güncelle: 'from core.amadeus_client import ...'
from tools.amadeus_client import get_access_token, BASE_URL

logger = logging.getLogger(__name__)

def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 0
    return (value - min_val) / (max_val - min_val)

def score_option(option, all_results):
    prices = [x["price"] for x in all_results]
    durations = [calculate_duration_minutes(x) for x in all_results]
    stops_list = [count_stops(x) for x in all_results]

    price_norm = normalize(option["price"], min(prices), max(prices))
    duration_norm = normalize(
        calculate_duration_minutes(option),
        min(durations),
        max(durations)
    )
    stops_norm = normalize(
        count_stops(option),
        min(stops_list),
        max(stops_list)
    )

    return 0.5 * price_norm + 0.3 * duration_norm + 0.2 * stops_norm

async def search_transport(transport_type, origin, destination, date):
    if transport_type == "flight":
        providers = [amadeus_flight_provider]
    elif transport_type == "train":
        return {"error": "Train provider not implemented yet"}
    elif transport_type == "bus":
        return {"error": "Bus provider not implemented yet"}
    
    tasks = [provider(origin, destination, date) for provider in providers]
    results_nested = await asyncio.gather(*tasks)

    all_results = [item for sublist in results_nested for item in sublist]

    if not all_results:
        return {"error": "No flights found"}

    cheapest = min(all_results, key=lambda x: x["price"])
    fastest = min(all_results, key=lambda x: calculate_duration_minutes(x))
    least_stops = min(all_results, key=lambda x: count_stops(x))
    best_overall = min(all_results, key=lambda x: score_option(x, all_results))

    return {
        "transport_type": "flight",
        "summary": {
            "cheapest": cheapest,
            "fastest": fastest,
            "least_stops": least_stops,
            "best_overall": best_overall
        },
        "all_options": all_results
    }


# 🏨 V3 YÜKSELTMESİ: GERÇEK FİYATLI VE ÇOK SEÇENEKLİ AMADEUS OTEL ARAMASI
async def search_hotels(city_code: str, check_in: str, check_out: str, adults: int = 1) -> list:
    """Amadeus API üzerinden otellerin En Ucuz, Orta ve Premium oda fiyatlarını getirir."""
    logger.info(f"🏨 Amadeus'tan {city_code} için çoklu oda seçenekli otel aranıyor...")

    try:
        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 1. AŞAMA: Şehirdeki Otel ID'lerini Bul
        url_ids = f"{BASE_URL}/v1/reference-data/locations/hotels/by-city"
        params_ids = {"cityCode": city_code, "radius": 5, "radiusUnit": "KM"}
        
        async with httpx.AsyncClient() as client:
            resp_ids = await client.get(url_ids, headers=headers, params=params_ids, timeout=10.0)
            if resp_ids.status_code != 200:
                logger.error(f"❌ Otel ID Hatası: {resp_ids.text}")
                return []
            
            # İlk 5 otelin ID'sini al
            hotel_data = resp_ids.json().get("data", [])[:5]
            hotel_ids = ",".join([h.get("hotelId") for h in hotel_data if h.get("hotelId")])
            
            if not hotel_ids:
                return []

            # 2. AŞAMA: Bu ID'ler için Gerçek Fiyatları Çek (V3 API)
            url_offers = f"{BASE_URL}/v3/shopping/hotel-offers"
            params_offers = {
                "hotelIds": hotel_ids,
                "adults": adults,
                "checkInDate": check_in,
                "checkOutDate": check_out
                # 🌟 KURAL İPTALİ: "bestRateOnly": "true" satırını SİLDİK. Artık tüm odalar gelecek!
            }

            resp_offers = await client.get(url_offers, headers=headers, params=params_offers, timeout=15.0)
            if resp_offers.status_code != 200:
                logger.error(f"❌ Otel Fiyat Hatası: {resp_offers.text}")
                return []

            offers_data = resp_offers.json().get("data", [])
            oteller = []

            # 🌟 KURAL: En fazla 5 otel için döngüye gir
            for hotel in offers_data[:5]:
                h_info = hotel.get("hotel", {})
                h_isim = h_info.get("name", "Bilinmeyen Otel")
                
                teklifler = hotel.get("offers", [])
                if not teklifler:
                    continue

                # Teklifleri fiyata göre sırala (Küçükten büyüğe)
                try:
                    teklifler = sorted(teklifler, key=lambda x: float(x.get("price", {}).get("total", 0)))
                except: pass

                # 1. En Ucuz Oda (Kesin var)
                en_ucuz = teklifler[0]
                en_ucuz_fiyat = f"{en_ucuz.get('price', {}).get('total')} {en_ucuz.get('price', {}).get('currency')}"
                en_ucuz_oda = en_ucuz.get('room', {}).get('typeEstimated', {}).get('category', 'Standart Oda')

                otel_ozeti = {
                    "Otel Adı": h_isim,
                    "En Uygun Seçenek": f"{en_ucuz_oda} - {en_ucuz_fiyat}"
                }

                # 2. Premium / Lüks Oda (Eğer birden fazla teklif varsa en sondakini al)
                if len(teklifler) > 1:
                    en_pahali = teklifler[-1]
                    if en_pahali.get("id") != en_ucuz.get("id"):
                        en_pahali_fiyat = f"{en_pahali.get('price', {}).get('total')} {en_pahali.get('price', {}).get('currency')}"
                        en_pahali_oda = en_pahali.get('room', {}).get('typeEstimated', {}).get('category', 'Premium Oda')
                        otel_ozeti["Premium Seçenek"] = f"{en_pahali_oda} - {en_pahali_fiyat}"

                # 3. Ortanca Oda (Eğer 3 veya daha fazla seçenek varsa aradan bir tane al)
                if len(teklifler) > 2:
                    ortanca = teklifler[len(teklifler) // 2]
                    ortanca_fiyat = f"{ortanca.get('price', {}).get('total')} {ortanca.get('price', {}).get('currency')}"
                    ortanca_oda = ortanca.get('room', {}).get('typeEstimated', {}).get('category', 'Gelişmiş Standart Oda')
                    otel_ozeti["Orta Seçenek"] = f"{ortanca_oda} - {ortanca_fiyat}"

                oteller.append(otel_ozeti)

            logger.info(f"✅ {len(oteller)} adet çok seçenekli otel başarıyla çekildi.")
            return oteller

    except Exception as e:
        logger.error(f"❌ Amadeus Otel V3 Hatası: {e}")
        return []