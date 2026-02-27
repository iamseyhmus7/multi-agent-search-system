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


# 🏨 YENİ VE GERÇEK: AMADEUS OTEL ARAMA FONKSİYONU
async def search_hotels(city_code: str) -> list:
    """Amadeus API üzerinden belirli bir şehirdeki otelleri getirir."""
    logger.info(f"🏨 Amadeus API'den {city_code} için otel aranıyor...")

    try:
        # 1. amadeus_client'dan taze token al
        token = await get_access_token()
        
        # 2. Amadeus Endpoint ve Parametreleri (Daha güvenli params kullanımı)
        url = f"{BASE_URL}/v1/reference-data/locations/hotels/by-city"
        params = {
            "cityCode": city_code,
            "radius": 5,
            "radiusUnit": "KM"
        }
        headers = {"Authorization": f"Bearer {token}"}

        # 3. İstek At
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)

            if response.status_code != 200:
                logger.error(f"❌ Amadeus Otel API Hatası ({response.status_code}): {response.text}")
                return []

            data = response.json()
            oteller = []

            # İlk 5 oteli temizleyip listeye ekle
            for item in data.get("data", [])[:5]:
                oteller.append({
                    "isim": item.get("name", "Bilinmeyen Otel"),
                    "otel_kodu": item.get("hotelId", ""),
                    "mesafe": f"{item.get('distance', {}).get('value', 'Bilinmiyor')} KM"
                })

            logger.info(f"✅ {len(oteller)} adet gerçek otel başarıyla çekildi.")
            return oteller

    except Exception as e:
        logger.error(f"❌ Amadeus Otel Bağlantı Hatası: {e}")
        return []