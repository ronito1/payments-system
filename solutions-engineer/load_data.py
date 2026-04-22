import requests
import json

URL = "http://127.0.0.1:8000/events/bulk"

with open("sample_events.json") as f:
    data = json.load(f)

# 🔥 LIMIT DATASET (SMALL + FAST)
data = data[:1000]

chunk_size = 200

total_batches = len(data) // chunk_size + 1

for i in range(0, len(data), chunk_size):
    chunk = data[i:i+chunk_size]
    batch_num = i // chunk_size + 1

    print(f"\nProcessing Batch {batch_num}/{total_batches}")

    res = requests.post(URL, json=chunk)

    try:
        print(res.json())
    except:
        print("❌ Non-JSON response")
        print("Status:", res.status_code)
        print("Response:", res.text)
        break

print("\n✅ All batches processed successfully")