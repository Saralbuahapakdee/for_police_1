import time
import cv2
import paho.mqtt.client as paho
from paho import mqtt
import json
import threading
from datetime import datetime
from config import RTSP_STREAMS

# Global variables to store latest detection data per camera
latest_detections = {}
detection_lock = threading.Lock()
mqtt_client = None

# Global variables for continuous stream capture per camera
latest_raw_frames = {}
frame_locks = {}
capture_threads = {}

def get_latest_detection(camera_id=1):
    with detection_lock:
        det = latest_detections.get(camera_id, {
            "detected": False,
            "objects": {},
            "timestamp": None,
            "latest_incident_id": None
        })
        return {
            "detected": det.get("detected"),
            "objects": det.get("objects"),
            "timestamp": det.get("timestamp"),
            "latest_incident_id": det.get("latest_incident_id")
        }

def capture_loop(camera_id, rtsp_url):
    """Background thread to constantly read RTSP and hold latest raw frame"""
    cap = None

    def open_capture():
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
            
        with frame_locks[camera_id]:
            latest_raw_frames[camera_id] = frame.copy()

def start_capture_threads():
    for camera_id, rtsp_url in RTSP_STREAMS.items():
        if camera_id not in capture_threads:
            # Initialize locks and vars for this camera if not present
            if camera_id not in frame_locks:
                frame_locks[camera_id] = threading.Lock()
            if camera_id not in latest_raw_frames:
                latest_raw_frames[camera_id] = None
            
            # Start thread
            t = threading.Thread(target=capture_loop, args=(camera_id, rtsp_url), daemon=True)
            t.start()
            capture_threads[camera_id] = t
            print(f"🎥 Background video capture thread started for camera {camera_id}")

def draw_boxes_on_frame(frame, detection_objects):
    """Draw bounding boxes based on detection objects"""
    for weapon_type, data in detection_objects.items():
        boxes = data.get("boxes", [])
        confidences = data.get("confidences", [])
        
        if len(confidences) < len(boxes):
            confidences.extend([0] * (len(boxes) - len(confidences)))

        for i, box in enumerate(boxes):
            if len(box) == 4:
                x1, y1, x2, y2 = map(int, box)
                conf = confidences[i]
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
                label = f"{weapon_type}: {conf:.2f}"
                (label_w, label_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + label_w, y1), (0, 0, 255), -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return frame

def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def on_message(client, userdata, msg):
    global latest_detections, latest_raw_frames
    from models import process_system_detection
    
    try:
        payload_text = msg.payload.decode('utf-8')
        parsed = json.loads(payload_text)
        
        print(f"\n{'='*50}")
        print(f"Received message on topic: {msg.topic}")
        print(f"QoS: {msg.qos}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Payload: {json.dumps(parsed, indent=2)}")
        print(f"{'='*50}\n")
        
        # Determine camera_id from MQTT if provided, otherwise default to 1
        camera_id = parsed.get("camera_id", 1)
        
        # Process and normalize the detection data
        processed_objects = {}
        
        if parsed.get("objects"):
            for weapon_type, data in parsed.get("objects", {}).items():
                confidences = data.get("confidences", [])
                if not isinstance(confidences, list):
                    confidences = [confidences]
                
                boxes = data.get("boxes", [])
                count = len(confidences) if confidences else 0
                
                processed_objects[weapon_type] = {
                    "count": count,
                    "confidences": confidences,
                    "boxes": boxes
                }
        
        # Update latest detection for this camera with thread safety
        with detection_lock:
            if camera_id not in latest_detections:
                latest_detections[camera_id] = {}
                
            latest_detections[camera_id]["detected"] = parsed.get("detected", False)
            latest_detections[camera_id]["objects"] = processed_objects
            latest_detections[camera_id]["timestamp"] = datetime.now().isoformat()
            
        # Log detection details and process system detection
        if parsed.get("detected") and processed_objects:
            print(f"🚨 WEAPON DETECTED on camera {camera_id}!")
            
            # Grab latest frame for automated image logging
            current_frame = None
            if camera_id in frame_locks and camera_id in latest_raw_frames:
                with frame_locks[camera_id]:
                    if latest_raw_frames[camera_id] is not None:
                        current_frame = latest_raw_frames[camera_id].copy()
            
            # Log all detected weapons
            for weapon_type, data in processed_objects.items():
                count = data.get("count", 0)
                confidences = data.get("confidences", [])
                boxes = data.get("boxes", [])
                
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85
                print(f"  - {weapon_type}: {count} detected (Avg Conf: {avg_confidence:.2f})")
                
                # Check if we should log image (only if we have a frame)
                image_bytes = None
                if current_frame is not None:
                    # Create a copy specifically for this weapon type to draw boxes
                    frame_for_log = current_frame.copy()
                    
                    # Ensure we only draw boxes for THIS weapon type being logged
                    single_weapon_obj = {weapon_type: data}
                    drawn_frame = draw_boxes_on_frame(frame_for_log, single_weapon_obj)
                    
                    ok, encoded = cv2.imencode(".jpg", drawn_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    if ok:
                        image_bytes = encoded.tobytes()
                
                # Automatically process backend logging and incident creation
                result = process_system_detection(camera_id, weapon_type, avg_confidence, image_bytes)
                if result.get("is_new"):
                    print(f"  -> Successfully logged {weapon_type} detection #{result.get('detection_id')} in background.")
                    if result.get("incident_id"):
                        with detection_lock:
                            if camera_id not in latest_detections:
                                latest_detections[camera_id] = {}
                            latest_detections[camera_id]["latest_incident_id"] = result.get("incident_id")
        else:
            print("✓ No threats detected")
            
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {payload_text}")
    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()

def generate(camera_id=1):
    """Video stream generator for frontend clients"""
    
    # Ensure background threads are running
    start_capture_threads()
    
    while True:
        frame_copy = None
        if camera_id in frame_locks and camera_id in latest_raw_frames:
            with frame_locks[camera_id]:
                if latest_raw_frames[camera_id] is not None:
                    frame_copy = latest_raw_frames[camera_id].copy()
                
        if frame_copy is None:
            time.sleep(0.1)
            continue
            
        # Get latest detection data thread-safely
        with detection_lock:
            current_detection = latest_detections.get(camera_id, {}).copy()
        
        # Draw bounding boxes if detected
        if current_detection.get("detected", False):
            frame_copy = draw_boxes_on_frame(frame_copy, current_detection.get("objects", {}))
        
        # Encode frame
        ok, encoded = cv2.imencode(".jpg", frame_copy, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            continue
        
        frame_bytes = encoded.tobytes()
        yield (b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        
        # Avoid blasting the CPU
        time.sleep(0.06)  # ~15 fps max

def start_mqtt_client():
    global mqtt_client
    
    # Start the continuous capture threads here as well to assure they're always running 
    # even before a frontend connects
    start_capture_threads()
    
    if mqtt_client is not None:
        return
        
    mqtt_client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
    mqtt_client.on_connect = on_connect
    mqtt_client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    mqtt_client.username_pw_set("mqtt_user1", "user1_mqtt")
    
    try:
        mqtt_client.connect("nafbb59e.ala.asia-southeast1.emqxsl.com", 8883)
        mqtt_client.on_message = on_message
        mqtt_client.loop_start()
        mqtt_client.subscribe("test/", qos=0)
        print("MQTT client connected and listening for messages...")
        print("Subscribed to all topics (#)")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
