import os, base64, requests

api_key = "AIzaSyDjTbMfOBG4XyDvItY2OGGKzgZBoCWAzFI"
test_image = "data/raw/panels/tower_of_god/ep_235/tower_of_god_ep235_p000.jpg"

with open(test_image, "rb") as f:
    content = base64.b64encode(f.read()).decode('utf-8')

url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
payload = {
    "requests": [{
        "image": {"content": content},
        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
    }]
}

response = requests.post(url, json=payload, timeout=20)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:3000]}")
