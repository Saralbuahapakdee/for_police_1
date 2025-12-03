import os
from passlib.context import CryptContext

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_SECRET")
JWT_ALGO = "HS256"
JWT_EXPIRATION = 3600  # 1 hour
DATABASE = "users.db"
AI_STREAM_URL = "http://ai-flask:6000/stream"

# Password context for hashing
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default data
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "email": "admin@security.com",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin"
}

DEFAULT_WEAPONS = ['knife', 'pistol', 'heavy_weapon']

DEFAULT_CAMERAS = [
    ('Main Entrance', 'Building A - Front Gate', 'Primary entrance monitoring'),
    ('Parking Lot', 'Building A - Parking Level 1', 'Vehicle and pedestrian monitoring'),
    ('Lobby', 'Building A - Main Lobby', 'Reception area surveillance'),
    ('Corridor 1F', 'Building A - First Floor Corridor', 'Hallway monitoring'),
    ('Back Exit', 'Building A - Emergency Exit', 'Secondary exit monitoring')
]