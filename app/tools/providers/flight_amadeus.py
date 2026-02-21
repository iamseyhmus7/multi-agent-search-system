from tools.amadeus_client import search_flights


async def amadeus_flight_provider(origin, destination, date):

    try:
        raw_data = await search_flights(origin, destination, date)
    except Exception as e:
        return []

    if "data" not in raw_data:
        return []

    results = []

    for offer in raw_data["data"]:
        try:
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]

            results.append({
                "provider": "Amadeus",
                "price": float(offer["price"]["total"]),
                "currency": offer["price"]["currency"],
                "departure_time": segments[0]["departure"]["at"],
                "arrival_time": segments[-1]["arrival"]["at"],
                "raw_duration": itinerary["duration"],
                "segments_count": len(segments)
            })
        except:
            continue

    return results