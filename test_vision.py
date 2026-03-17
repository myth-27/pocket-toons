try:
    from google.cloud import vision
    print("Import successful")
    client = vision.ImageAnnotatorClient()
    print("Client initialization successful")
except Exception as e:
    print(f"Error: {e}")
