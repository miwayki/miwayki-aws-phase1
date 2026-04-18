import asyncio
import json
import httpx
from datetime import datetime

async def main():
    flow_id = "fc6a4595-8529-4e32-8655-fa54920e7b8a"
    api_key = "sk-9bKz2vXMJzNpW3We66kay6AAOBh4ZZ-xFmSajQfNKJE"
    
    url = f"http://127.0.0.1:7860/api/v1/run/{flow_id}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    body = {
        "input_value": "Por favor cotízame el tour Machu Picchu Full Day para 2 adultos y 1 adolescente para la fecha 15 de julio de 2026",
        "input_type": "chat",
        "output_type": "chat",
        "session_id": f"test-{datetime.now().timestamp()}",
        "tweaks": {}
    }
    
    print(f"Calling endpoint {url}...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(url, json=body, headers=headers)
        
    print(f"Status: {res.status_code}")
    print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
