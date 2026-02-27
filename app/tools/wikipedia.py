
import requests

def search_wikipedia(query: str):
    """Wikipedia'dan kısa özet bilgi çeker."""
    try:
        url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        response = requests.get(url)
        data = response.json()
        return data.get("extract", "Bilgi bulunamadı.")
    except:
        return "Wikipedia araması başarısız."