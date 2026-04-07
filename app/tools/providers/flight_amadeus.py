import traceback
import sys
from tools.amadeus_client import search_flights

async def amadeus_flight_provider(origin, destination, date):
    try:
        raw_data = await search_flights(origin, destination, date)
        # 🚨 İŞTE BURASI! AMADEUS BİZE NE DİYOR GÖRELİM:
        # print(f"🚨 AMADEUS HAM CEVAP: {raw_data}") 
        
    except Exception as e:
        print(f"❌ Amadeus Bağlantı Hatası! Tür: {type(e).__name__} | Mesaj: {e}")
        traceback.print_exc()
        return []

    # Eğer cevapta 'errors' diye bir şey varsa API key veya tarih hatasıdır
    if "errors" in raw_data:
        print(f"❌ Amadeus API Hatası: {raw_data['errors']}")
        return []

    if "data" not in raw_data or not raw_data["data"]:
        print("⚠️ Amadeus 'data' bulamadı veya boş döndü.")
        return []

    results = []

    for offer in raw_data["data"]:
        try:
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]

            results.append({
                "provider": "Amadeus",
                "airline_code": segments[0]["carrierCode"], # 🌟 YENİ: Havayolu kodunu cebe koyduk!
                "price": float(offer["price"]["total"]),
                "currency": offer["price"]["currency"],
                "departure_time": segments[0]["departure"]["at"],
                "arrival_time": segments[-1]["arrival"]["at"],
                "raw_duration": itinerary["duration"],
                "segments_count": len(segments)
            })
        except Exception as e:
            print(f"⚠️ Amadeus veri işleme hatası: {e}")
            continue
    return results