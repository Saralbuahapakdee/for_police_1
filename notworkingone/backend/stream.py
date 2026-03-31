"""
stream.py  –  RTSP capture + MQTT listener

Key change: RTSP streams and MQTT-topic→camera_id mappings are loaded
from the cameras table in the DB (so admin changes take effect on restart
or via reload_camera_config()).
"""

import time
import cv2
import paho.mqtt.client as paho
from paho import mqtt
import json
import threading
from datetime import datetime

# ── In-memory state ──────────────────────────────────────────────────────────
latest_detections = {}          # camera_id → detection dict
detection_lock    = threading.Lock()
mqtt_client       = None

latest_raw_frames = {}          # camera_id → numpy frame
frame_locks       = {}          # camera_id → threading.Lock
capture_threads   = {}          # camera_id → Thread

# topic → camera_id  (built from DB)
_topic_to_camera  = {}
_config_lock      = threading.Lock()


# ── DB helpers ────────────────────────────────────────────────────────────────

def _load_camera_config():
    """Read rtsp_url and mqtt_topic for every active camera from the DB."""
    try:
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, rtsp_url, mqtt_topic FROM cameras WHERE is_active = 1"
            )
            rows = cursor.fetchall()
        return rows
    except Exception as e:
        print(f"⚠️  Could not load camera config from DB: {e}")
        return []


def reload_camera_config():
    """Re-read DB and rebuild topic→camera map + start any new capture threads."""
    global _topic_to_camera

    rows = _load_camera_config()

    new_topic_map  = {}
    rtsp_map       = {}           # camera_id → rtsp_url

    for row in rows:
        cam_id    = row["id"]
        rtsp_url  = (row["rtsp_url"] or "").strip()
        topic     = (row["mqtt_topic"] or "").strip()

        if rtsp_url:
            rtsp_map[cam_id] = rtsp_url

        if topic:
            new_topic_map[topic] = cam_id

    with _config_lock:
        _topic_to_camera  = new_topic_map

    # Start capture threads for cameras that have an RTSP URL
    for cam_id, rtsp_url in rtsp_map.items():
        if cam_id not in capture_threads or not capture_threads[cam_id].is_alive():
            _start_one_capture_thread(cam_id, rtsp_url)

    print(f"📡 Camera config loaded: {len(rows)} cameras | "
          f"topics={list(new_topic_map.keys())}")


def _resolve_camera_id(mqtt_topic: str):
    """
    Decide which camera_id an MQTT message belongs to.
    Strictly match the topic from the configuration map.
    """
    with _config_lock:
        if mqtt_topic in _topic_to_camera:
            return _topic_to_camera[mqtt_topic]

    return None


# ── RTSP capture threads ──────────────────────────────────────────────────────

def _start_one_capture_thread(camera_id, rtsp_url):
    if camera_id not in frame_locks:
        frame_locks[camera_id]       = threading.Lock()
        latest_raw_frames[camera_id] = None

    t = threading.Thread(
        target=capture_loop, args=(camera_id, rtsp_url), daemon=True
    )
    t.start()
    capture_threads[camera_id] = t
    print(f"🎥 Capture thread started for camera {camera_id}  ({rtsp_url[:40]}...)")


def capture_loop(camera_id, rtsp_url):
    cap = None

    def open_cap():
        c = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if c.isOpened():
            c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            c.set(cv2.CAP_PROP_FPS, 10)
            return c
        return None

    while True:
        if cap is None or not cap.isOpened():
            cap = open_cap()
            if cap is None:
                time.sleep(0.5)
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
            latest_raw_frames[camera_id] = frame


def start_capture_threads():
    """Called on startup – loads config from DB and starts threads."""
    reload_camera_config()


# ── Drawing helpers ───────────────────────────────────────────────────────────

def draw_boxes_on_frame(frame, detection_objects):
    for weapon_type, data in detection_objects.items():
        boxes       = data.get("boxes", [])
        confidences = data.get("confidences", [])

        if len(confidences) < len(boxes):
            confidences.extend([0] * (len(boxes) - len(confidences)))

        for i, box in enumerate(boxes):
            if len(box) == 4:
                x1, y1, x2, y2 = map(int, box)
                conf = confidences[i]

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

                label = f"{weapon_type}: {conf:.2f}"
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + lw, y1), (0, 0, 255), -1)
                cv2.putText(frame, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return frame


# ── MQTT callbacks ────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"MQTT CONNACK rc={rc}")


def on_message(client, userdata, msg):
    from models import process_system_detection

    try:
        parsed       = json.loads(msg.payload.decode("utf-8"))
        camera_id    = _resolve_camera_id(msg.topic)

        if camera_id is None:
            print(f"⚠️  Ignoring message on topic '{msg.topic}' - no configured camera match.")
            return

        print(f"\n{'='*50}")
        print(f"MQTT  topic={msg.topic}  →  camera_id={camera_id}")
        print(f"Payload: {json.dumps(parsed, indent=2)}")
        print(f"{'='*50}\n")

        # Normalise detection objects
        processed_objects = {}
        for weapon_type, data in parsed.get("objects", {}).items():
            confs = data.get("confidences", [])
            if not isinstance(confs, list):
                confs = [confs]
            processed_objects[weapon_type] = {
                "count":       len(confs),
                "confidences": confs,
                "boxes":       data.get("boxes", []),
            }

        # Update latest detection (thread-safe)
        with detection_lock:
            if camera_id not in latest_detections:
                latest_detections[camera_id] = {}
            latest_detections[camera_id]["detected"]  = parsed.get("detected", False)
            latest_detections[camera_id]["objects"]   = processed_objects
            latest_detections[camera_id]["timestamp"] = datetime.now().isoformat()

        # Log detections to DB
        if parsed.get("detected") and processed_objects:
            print(f"🚨 WEAPON DETECTED on camera {camera_id}!")

            # Grab latest frame
            current_frame = None
            if camera_id in frame_locks:
                with frame_locks[camera_id]:
                    if latest_raw_frames.get(camera_id) is not None:
                        current_frame = latest_raw_frames[camera_id].copy()

            def process_and_log():
                for weapon_type, data in processed_objects.items():
                    confs          = data.get("confidences", [])
                    avg_confidence = sum(confs) / len(confs) if confs else 0.85

                    image_bytes = None
                    if current_frame is not None:
                        drawn = draw_boxes_on_frame(
                            current_frame.copy(), {weapon_type: data}
                        )
                        ok, enc = cv2.imencode(
                            ".jpg", drawn, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                        )
                        if ok:
                            image_bytes = enc.tobytes()

                    result = process_system_detection(
                        camera_id, weapon_type, avg_confidence, image_bytes
                    )
                    if result.get("is_new"):
                        print(f"  → Logged detection #{result['detection_id']}")
                        if result.get("incident_id"):
                            with detection_lock:
                                latest_detections.setdefault(camera_id, {})[
                                    "latest_incident_id"
                                ] = result["incident_id"]
                                
            # Offload disk IO/DB insertions to avoid blocking MQTT thread/stream delay 
            threading.Thread(target=process_and_log, daemon=True).start()
        else:
            print("✓ No threats detected")

    except json.JSONDecodeError as e:
        print(f"Bad JSON: {e}")
    except Exception as e:
        print(f"Error in on_message: {e}")
        import traceback
        traceback.print_exc()


# ── Video stream generator ────────────────────────────────────────────────────

def get_latest_detection(camera_id=None):
    with detection_lock:
        if not latest_detections:
            return {
                "detected": False, "objects": {}, "timestamp": None, "latest_incident_id": None
            }

        if camera_id is not None:
            det = latest_detections.get(camera_id, {})
            return {
                "detected":          det.get("detected", False),
                "objects":           det.get("objects", {}),
                "timestamp":         det.get("timestamp"),
                "latest_incident_id": det.get("latest_incident_id"),
            }
        else:
            # Find the globally most recent detection
            valid_dets = [d for d in latest_detections.values() if d.get("timestamp")]
            if valid_dets:
                newest = max(valid_dets, key=lambda x: x["timestamp"])
                return {
                    "detected":          newest.get("detected", False),
                    "objects":           newest.get("objects", {}),
                    "timestamp":         newest.get("timestamp"),
                    "latest_incident_id": newest.get("latest_incident_id"),
                }
            
            return {
                "detected": False, "objects": {}, "timestamp": None, "latest_incident_id": None
            }


def generate(camera_id=1):
    """MJPEG stream generator for frontend."""
    start_capture_threads()   # ensure threads are running

    while True:
        frame_copy = None
        if camera_id in frame_locks:
            with frame_locks[camera_id]:
                if latest_raw_frames.get(camera_id) is not None:
                    frame_copy = latest_raw_frames[camera_id].copy()

        if frame_copy is None:
            time.sleep(0.1)
            continue

        with detection_lock:
            det = latest_detections.get(camera_id, {}).copy()

        if det.get("detected", False):
            frame_copy = draw_boxes_on_frame(frame_copy, det.get("objects", {}))

        ok, encoded = cv2.imencode(
            ".jpg", frame_copy, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        )
        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + encoded.tobytes()
            + b"\r\n"
        )
        time.sleep(0.06)   # ~15 fps


# ── MQTT client startup ───────────────────────────────────────────────────────

def start_mqtt_client():
    global mqtt_client

    # Always load camera config (starts RTSP threads too)
    start_capture_threads()

    if mqtt_client is not None:
        return

    mqtt_client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    mqtt_client.username_pw_set(
        "hivemq.webclient.1757927568300", "r$i.g1>23O5TMdLAcp:H"
    )

    try:
        mqtt_client.connect(
            "fd2249eedb6c43fdbf9e9d318ab38fe4.s1.eu.hivemq.cloud", 8883
        )
        mqtt_client.loop_start()
        mqtt_client.subscribe("#", qos=0)
        print("✅ MQTT client connected — subscribed to all topics (#)")
    except Exception as e:
        print(f"❌ MQTT connect failed: {e}")