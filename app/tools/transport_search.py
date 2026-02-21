import asyncio
from tools.providers.flight_amadeus import amadeus_flight_provider
from utils.flight_utils import calculate_duration_minutes, count_stops

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