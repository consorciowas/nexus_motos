import requests

ACCESS_TOKEN = "APP_USR-6236678389226473-081611-e2798395abebeb194d8a5b2868ee292c-2633352678"  # tu token real de vendedor

url = "https://api.mercadopago.com/users/test_user"
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}
body = {
    "site_id": "MPE"  # País: MLA (Argentina), MLM (México), MPE (Perú), etc.
}

response = requests.post(url, headers=headers, json=body)
print(response.json())
