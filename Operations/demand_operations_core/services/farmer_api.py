import requests

BASE_URL = "http://demand.bharatintelligence.ai"
TOKEN = "e8fa8310c9af344ca22ec6bd23960d609b09c704"  # TODO: move to settings/env later

def get_farmer_details(farmer_id: str):
    url = f"{BASE_URL}/fir/api/get_farmer_details/{farmer_id}/"
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json()
