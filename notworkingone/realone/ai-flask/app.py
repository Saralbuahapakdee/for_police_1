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
        
        # Update latest detection with thread safety
        with detection_lock:
            latest_detection = {
                "detected": parsed.get("detected", False),
                "objects": parsed.get("objects", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        # Log detection details
        if parsed.get("detected") and parsed.get("objects"):
            print("🚨 WEAPON DETECTED!")
            for weapon_type, data in parsed.get("objects", {}).items():
                count = data.get("count", 0)
                confidences = data.get("confidences", [])
                print(f"  - {weapon_type}: {count} detected")
                print(f"    Confidences: {confidences}")
        else:
            print("✓ No threats detected")
            
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {payload_text}")
    except Exception as e:
        print(f"Error processing message: {e}")

def get_detection_overlay_text():
    """Generate text overlay for video stream based on latest detection"""
    with detection_lock:
        if not latest_detection["detected"] or not latest_detection["objects"]:
            return "Status: CLEAR | No threats detected"
        
        lines = ["⚠️ WEAPON DETECTED!"]
        for weapon_type, data in latest_detection["objects"].items():
            count = data.get("count", 0)
            confidences = data.get("confidences", [])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            
            # Format weapon name
            weapon_name = weapon_type.replace("-", " ").title()
            lines.append(f"{weapon_name}: {count} ({avg_conf*100:.1f}%)")
        
        return " | ".join(lines)

def generate():
    rtsp_url = "rtsp://admin2:admin234@161.246.5.20:554/cam/realmonitor?channel=1&subtype=1"
    cap = None

    def open_capture():
        c = cv2.VideoCapture(rtsp_url)
        return c if c.isOpened() else None

    cap = open_capture()

    while True:
        if cap is None or not cap.isOpened():
            cap = open_capture()
            if cap is None:
                time.sleep(1.0)
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

        # Get detection text
        detection_text = get_detection_overlay_text()
        
        # Determine text color based on detection status
        with detection_lock:
            is_detected = latest_detection["detected"] and latest_detection["objects"]
        
        text_color = (0, 0, 255) if is_detected else (0, 255, 0)  # Red if detected, Green if clear
        
        # Add text overlay to frame
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        
        # Add semi-transparent background for better readability
        (text_width, text_height), baseline = cv2.getTextSize(
            detection_text, font, font_scale, thickness
        )
        
        # Draw background rectangle
        cv2.rectangle(
            frame,
            (10, 10),
            (20 + text_width, 40 + text_height),
            (0, 0, 0),
            -1
        )
        
        # Draw text
        cv2.putText(
            frame,
            detection_text,
            (15, 35),
            font,
            font_scale,
            text_color,
            thickness,
            cv2.LINE_AA,
        )
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(
            frame,
            timestamp,
            (15, frame.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # Encode frame
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            continue
        
        frame_bytes = encoded.tobytes()
        yield (b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

@app.get("/stream")
def stream():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.get("/detection")
def get_detection():
    """API endpoint to get latest detection data"""
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