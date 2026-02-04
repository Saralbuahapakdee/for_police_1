# notworkingone/ai-flask/app.py - UPDATED: NO TEXT OVERLAY, JUST RAW STREAM

from flask import Flask, Response
import time
import cv2
import paho.mqtt.client as paho
from paho import mqtt
import json
import threading
from datetime import datetime

app = Flask(__name__)

# Global variables to store latest detection data
latest_detection = {
    "detected": False,
    "objects": {},
    "timestamp": None
}
detection_lock = threading.Lock()

def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def on_message(client, userdata, msg):
    global latest_detection
    
    try:
        payload_text = msg.payload.decode('utf-8')
        parsed = json.loads(payload_text)
        
        print(f"\n{'='*50}")
        print(f"Received message on topic: {msg.topic}")
        print(f"QoS: {msg.qos}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Payload: {json.dumps(parsed, indent=2)}")
        print(f"{'='*50}\n")
        
        # Process and normalize the detection data
        processed_objects = {}
        
        if parsed.get("objects"):
            for weapon_type, data in parsed.get("objects", {}).items():
                # Normalize confidences to always be a list
                confidences = data.get("confidences", [])
                if not isinstance(confidences, list):
                    confidences = [confidences]
                
                # Get boxes (default to empty list if not provided)
                boxes = data.get("boxes", [])
                
                # Count number of detections
                count = len(confidences) if confidences else 0
                
                processed_objects[weapon_type] = {
                    "count": count,
                    "confidences": confidences,
                    "boxes": boxes  # [[x1, y1, x2, y2], ...]
                }
        
        # Update latest detection with thread safety
        with detection_lock:
            latest_detection = {
                "detected": parsed.get("detected", False),
                "objects": processed_objects,
                "timestamp": datetime.now().isoformat()
            }
            
        # Log detection details
        if parsed.get("detected") and processed_objects:
            print("🚨 WEAPON DETECTED!")
            for weapon_type, data in processed_objects.items():
                count = data.get("count", 0)
                confidences = data.get("confidences", [])
                boxes = data.get("boxes", [])
                print(f"  - {weapon_type}: {count} detected")
                print(f"    Confidences: {confidences}")
                print(f"    Boxes: {boxes}")
        else:
            print("✓ No threats detected")
            
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {payload_text}")
    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()

def generate():
    rtsp_url = "rtsp://admin2:459OOPpr0j3ctzaCE61@161.246.5.20:554/cam/realmonitor?channel=1&subtype=1"
    cap = None

    def open_capture():
        """Open the RTSP stream with low-latency settings."""
        c = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        c.set(cv2.CAP_PROP_FPS, 15)
        return c if c.isOpened() else None

    while True:
        if cap is None or not cap.isOpened():
            cap = open_capture()
            if cap is None:
                time.sleep(0.2)
                continue

        ok, frame = cap.read()
        if not ok or frame is None:
            try:
                cap.release()
            except Exception:
                pass
            cap = None
            time.sleep(0.2)
            continue

        # NO TEXT OVERLAY - Just pass through the raw stream
        
        # Encode frame
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            continue
        
        frame_bytes = encoded.tobytes()
        yield (b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

@app.get("/stream")
def stream():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.get("/detection")
def get_detection():
    """API endpoint to get latest detection data including bounding boxes"""
    with detection_lock:
        return {
            "detected": latest_detection["detected"],
            "objects": latest_detection["objects"],
            "timestamp": latest_detection["timestamp"]
        }

# Initialize MQTT client
client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
client.username_pw_set("hivemq.webclient.1757927568300", "r$i.g1>23O5TMdLAcp:H")
client.connect("fd2249eedb6c43fdbf9e9d318ab38fe4.s1.eu.hivemq.cloud", 8883)

client.on_message = on_message
client.loop_start()
client.subscribe("#", qos=1)

print("MQTT client connected and listening for messages...")
print("Subscribed to all topics (#)")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)