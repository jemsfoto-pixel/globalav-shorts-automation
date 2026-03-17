import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # Try to read from github_secrets.txt if env not set
    try:
        with open("github_secrets.txt", "r") as f:
            for line in f:
                if "GOOGLE_API_KEY" in line:
                    api_key = line.split("=")[1].strip()
                    break
    except:
        pass

if not api_key:
    # Use the one provided in earlier chat
    api_key = "AIzaSyC2F8RPT2y1X6l2nUxbm1ontttF4yDCh5A"

client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    with open("model_list.txt", "w") as f:
        for model in client.models.list():
            msg = f"- {model.name}"
            print(msg)
            f.write(msg + "\n")
    print("Done. Check model_list.txt")
except Exception as e:
    with open("model_list.txt", "w") as f:
        f.write(f"Error: {e}")
    print(f"Error listing models: {e}")
