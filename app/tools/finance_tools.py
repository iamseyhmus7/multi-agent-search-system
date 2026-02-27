import requests

def get_exchange_rate(amount: float, from_curr: str, to_curr: str = "TRY"):
    """Tamamen ücretsiz Frankfurter API kullanarak kur dönüşümü yapar."""
    try:
        # Örn: https://api.frankfurter.app/latest?amount=10&from=GBP&to=USD
        url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_curr.upper()}&to={to_curr.upper()}"
        response = requests.get(url)
        data = response.json()
        converted_amount = data['rates'][to_curr.upper()]
        return f"{amount} {from_curr} = {converted_amount} {to_curr}"
    except Exception as e:
        return f"Kur bilgisi alınamadı: {str(e)}"