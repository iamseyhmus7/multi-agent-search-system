import httpx
import os
from dotenv import load_dotenv

# .env dosyasını zorla okutuyoruz
load_dotenv()

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

BASE_URL = "https://test.api.amadeus.com"

async def get_access_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": AMADEUS_API_KEY,
                "client_secret": AMADEUS_API_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return response.json()["access_token"]


async def search_flights(origin, destination, date):
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/v2/shopping/flight-offers",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": date,
                "adults": 1,
                "max": 5
            },
        )

        return response.json()