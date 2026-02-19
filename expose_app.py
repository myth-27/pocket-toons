from pyngrok import ngrok
import time

# Open a HTTP tunnel on the default port 8501
public_url = ngrok.connect(8501).public_url
print(f" * Public URL: {public_url}")

# Keep the tunnel open
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Closing tunnel...")
    ngrok.kill()
