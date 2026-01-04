import asyncio
import base64
import json
import numpy as np
import cv2
import httpx
import websockets
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000/v1/pipeline/process"
WS_URL = "ws://localhost:8000/v1/ws/gaze"

def create_dummy_payload():
    # Create a dummy black frame (640x480)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', frame)
    frame_b64 = base64.b64encode(buffer).decode('utf-8')

    # Create dummy audio (1 second of silence at 16kHz)
    audio = np.zeros(16000, dtype=np.float32)
    audio_bytes = audio.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

    return {
        "session_id": "test-session-e2e",
        "timestamp": datetime.utcnow().isoformat(),
        "frame_data": frame_b64,
        "frame_encoding": "jpeg",
        "audio_data": audio_b64,
        "audio_format": "float32",
        "original_sample_rate": 16000
    }

async def listen_ws(ws):
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            # Ignore heartbeats/status
            if data.get("type") in ["heartbeat", "status", "pong"]:
                continue
            return data
    except asyncio.TimeoutError:
        return None

async def main():
    print(f"Connecting to WebSocket: {WS_URL}")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("WebSocket connected.")
            
            # Prepare payload
            payload = create_dummy_payload()
            print("Sending REST request to pipeline...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(API_URL, json=payload, timeout=10.0)
                
            if response.status_code == 200:
                rest_result = response.json()
                print("SUCCESS: Received REST response")
                print(f"Metrics (REST): {json.dumps(rest_result['metrics'], indent=2)}")
            else:
                print(f"FAILURE: REST request failed with {response.status_code}")
                print(response.text)
                return

            # Wait for WebSocket message (broadcast)
            print("Waiting for WebSocket broadcast...")
            ws_msg = await listen_ws(ws)
            
            if ws_msg:
                print("SUCCESS: Received WebSocket message")
                print(f"Message: {json.dumps(ws_msg, indent=2)}")
            else:
                print("WARNING: No WebSocket message received (timeout)")
                
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(main())