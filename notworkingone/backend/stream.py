import time
import cv2
import paho.mqtt.client as paho
from paho import mqtt
import json
import threading
from datetime import datetime

# Global variables to store latest detection data
latest_detection = {
    "detected": False,
    "objects": {},
    "timestamp": None
}
detection_lock = threading.Lock()
mqtt_client = None

# Per-camera RTSP URLs
CAMERA_RTSP_URLS = {
    "parking_lot": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
}

DEFAULT_RTSP_URL = "rtsp://admin2:459OOPpr0j3ctzaCE61@161.246.5.20:554/cam/realmonitor?channel=1&subtype=1"


def get_rtsp_url(camera_name: str) -> str:
    """Return the RTSP URL for the given camera name (normalised key)."""
    if not camera_name:
        return DEFAULT_RTSP_URL
    key = camera_name.lower().replace(" ", "_")
    return CAMERA_RTSP_URLS.get(key, DEFAULT_RTSP_URL)


def get_latest_detection():
    with detection_lock:
        return {
            "detected": latest_detection["detected"],
            "objects": latest_detection["objects"],
            "timestamp": latest_detection["timestamp"]
        }

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

def generate(camera_name: str = None):
    """Generate MJPEG frames for the given camera (uses its own RTSP URL)."""
    rtsp_url = get_rtsp_url(camera_name)
    print(f"📹 Starting stream for camera '{camera_name}' → {rtsp_url}")

    cap = None

    def open_capture():
        """Open the RTSP stream with low-latency settings."""
        c = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if c.isOpened():
            c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            c.set(cv2.CAP_PROP_FPS, 15)
            return c
        return None

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

        # Get latest detection data thread-safely
        with detection_lock:
            current_detection = latest_detection.copy()
        
        # Draw bounding boxes if detected
        if current_detection.get("detected", False):
            for weapon_type, data in current_detection["objects"].items():
                boxes = data.get("boxes", [])
                confidences = data.get("confidences", [])
                
                # Ensure we have matching confidences for boxes
                if len(confidences) < len(boxes):
                    confidences.extend([0] * (len(boxes) - len(confidences)))

                for i, box in enumerate(boxes):
                    if len(box) == 4:
                        x1, y1, x2, y2 = map(int, box)
                        conf = confidences[i]
                        
                        # Draw rectangle
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        
                        # Prepare label
                        label = f"{weapon_type}: {conf:.2f}"
                        (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        
                        # Draw label background
                        cv2.rectangle(frame, (x1, y1 - 20), (x1 + label_w, y1), (0, 0, 255), -1)
                        
                        # Draw label text
                        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Encode frame
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            continue
        
        frame_bytes = encoded.tobytes()
        yield (b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

def start_mqtt_client():
    global mqtt_client
    if mqtt_client is not None:
        return
        
    mqtt_client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
    mqtt_client.on_connect = on_connect
    mqtt_client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    mqtt_client.username_pw_set("hivemq.webclient.1757927568300", "r$i.g1>23O5TMdLAcp:H")
    
    try:
        mqtt_client.connect("fd2249eedb6c43fdbf9e9d318ab38fe4.s1.eu.hivemq.cloud", 8883)
        mqtt_client.on_message = on_message
        mqtt_client.loop_start()
        mqtt_client.subscribe("#", qos=0)
        print("MQTT client connected and listening for messages...")
        print("Subscribed to all topics (#)")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")