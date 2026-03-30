import os
from passlib.context import CryptContext

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_SECRET")
JWT_ALGO = "HS256"
JWT_EXPIRATION = 3600  # 1 hour
DATABASE = "users.db"

# Password context for hashing
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default data
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "SecureAdmin@2024!",
    "email": "admin@security.com",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin"
}

SYSTEM_USER = {
    "username": "system",
    "password": "SystemUserNoLogin123!",
    "email": "system@security.local",
    "first_name": "System",
    "last_name": "Automated",
    "role": "system"
}

DEFAULT_WEAPONS = ['knife', 'pistol', 'heavy_weapon']

# Default RTSP streams indexed by camera DB row position (1-based)
RTSP_STREAMS = {
    1: "rtsp://admin2:459OOPpr0j3ctzaCE61@161.246.5.20:554/cam/realmonitor?channel=1&subtype=1",
    2: "rtsp://fuGk55rSwiDtVigRfxPRkVlyiJPGmDZW:ZqniBPd7ILatymFgJcK9W@test.rtsp.stream/people"
}

# Default MQTT topics indexed by camera DB row position (1-based)
# "#" means subscribe to all — camera_id in the payload is used to route
DEFAULT_CAMERA_MQTT_TOPICS = {
    1: "A1G3774HC",   # Main Entrance — listens to all topics (camera_id from payload)
    2: "BG774LGG3",   # Testing Camera
    3: "",
    4: "",
}

DEFAULT_CAMERAS = [
    ('Main Entrance', 'Building A - Front Gate', 'Primary entrance monitoring'),
    ('Testing Camera', 'Lab', 'RTSP Testing Stream'),
    ('Corridor 1F', 'Building A - First Floor Corridor', 'Hallway monitoring'),
    ('Back Exit', 'Building A - Emergency Exit', 'Secondary exit monitoring')
]