import sqlite3
from contextlib import contextmanager
from config import DATABASE, pwd_ctx, DEFAULT_ADMIN, SYSTEM_USER, DEFAULT_WEAPONS, DEFAULT_CAMERAS


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    conn.execute('PRAGMA cache_size=-64000;')
    conn.execute('PRAGMA temp_store=MEMORY;')
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the SQLite database and create all necessary tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'officer',
            badge_number TEXT,
            department TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_name TEXT UNIQUE NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            stream_url TEXT,
            rtsp_url TEXT,
            mqtt_topic TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weapon_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weapon_type TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, weapon_type)
        )
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            camera_id INTEGER NOT NULL,
            weapon_type TEXT NOT NULL,
            confidence_score REAL,
            detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_only DATE DEFAULT (date('now')),
            image_path TEXT,
            incident_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (camera_id) REFERENCES cameras (id),
            FOREIGN KEY (incident_id) REFERENCES incidents (id)
        )
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_number TEXT UNIQUE NOT NULL,
            camera_id INTEGER NOT NULL,
            weapon_type TEXT NOT NULL,
            detection_id INTEGER,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            assigned_to INTEGER,
            created_by INTEGER NOT NULL,
            resolved_by INTEGER,
            detected_at TIMESTAMP NOT NULL,
            responded_at TIMESTAMP,
            resolved_at TIMESTAMP,
            location TEXT,
            description TEXT,
            response_notes TEXT,
            resolution_notes TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (camera_id) REFERENCES cameras (id),
            FOREIGN KEY (detection_id) REFERENCES detection_logs (id),
            FOREIGN KEY (assigned_to) REFERENCES users (id),
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (resolved_by) REFERENCES users (id)
        )
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incident_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (incident_id) REFERENCES incidents (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            camera_id INTEGER NOT NULL,
            detection_date DATE NOT NULL,
            weapon_type TEXT NOT NULL,
            total_detections INTEGER DEFAULT 0,
            avg_confidence REAL DEFAULT 0.0,
            first_detection TIMESTAMP,
            last_detection TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (camera_id) REFERENCES cameras (id),
            UNIQUE(user_id, camera_id, detection_date, weapon_type)
        )
    ''')
    
    
    migrations = [
        ("detection_logs", "image_path",  "ALTER TABLE detection_logs ADD COLUMN image_path TEXT"),
        ("incidents",      "image_path",  "ALTER TABLE incidents ADD COLUMN image_path TEXT"),
        ("cameras",        "rtsp_url",    "ALTER TABLE cameras ADD COLUMN rtsp_url TEXT"),
        ("cameras",        "mqtt_topic",  "ALTER TABLE cameras ADD COLUMN mqtt_topic TEXT"),
    ]
    for table, column, sql in migrations:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if column not in cols:
                cursor.execute(sql)
                print(f"✅ Migration: added '{column}' to {table}")
        except Exception as e:
            print(f"Note (migration): {e}")

    
    cursor.execute('SELECT username FROM users WHERE username = ?', (DEFAULT_ADMIN['username'],))
    if not cursor.fetchone():
        admin_password_hash = pwd_ctx.hash(DEFAULT_ADMIN['password'])
        cursor.execute('''INSERT INTO users 
                         (username, password_hash, email, first_name, last_name, role, badge_number) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (DEFAULT_ADMIN['username'], admin_password_hash, DEFAULT_ADMIN['email'],
                       DEFAULT_ADMIN['first_name'], DEFAULT_ADMIN['last_name'], 'admin', 'ADMIN001'))
        admin_user_id = cursor.lastrowid
        for weapon in DEFAULT_WEAPONS:
            cursor.execute('''INSERT OR IGNORE INTO weapon_preferences 
                            (user_id, weapon_type, is_enabled) VALUES (?, ?, ?)''',
                          (admin_user_id, weapon, True))
    
    
    cursor.execute('SELECT username FROM users WHERE username = ?', (SYSTEM_USER['username'],))
    if not cursor.fetchone():
        system_password_hash = pwd_ctx.hash(SYSTEM_USER['password'])
        cursor.execute('''INSERT INTO users 
                         (username, password_hash, email, first_name, last_name, role) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (SYSTEM_USER['username'], system_password_hash, SYSTEM_USER['email'],
                       SYSTEM_USER['first_name'], SYSTEM_USER['last_name'], 'system'))
        system_user_id = cursor.lastrowid
        for weapon in DEFAULT_WEAPONS:
            cursor.execute('''INSERT OR IGNORE INTO weapon_preferences 
                            (user_id, weapon_type, is_enabled) VALUES (?, ?, ?)''',
                          (system_user_id, weapon, True))
    
    
    from config import RTSP_STREAMS, DEFAULT_CAMERA_MQTT_TOPICS
    for idx, (cam_name, location, desc) in enumerate(DEFAULT_CAMERAS, start=1):
        rtsp = RTSP_STREAMS.get(idx, '')
        mqtt_topic = DEFAULT_CAMERA_MQTT_TOPICS.get(idx, '')
        cursor.execute('''INSERT OR IGNORE INTO cameras 
                         (camera_name, location, description, stream_url, rtsp_url, mqtt_topic) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (cam_name, location, desc,
                       f'/api/video?camera={cam_name.lower().replace(" ", "_")}',
                       rtsp, mqtt_topic))
        
        
        cursor.execute('''UPDATE cameras 
                          SET rtsp_url = ?, mqtt_topic = ? 
                          WHERE camera_name = ? AND (rtsp_url IS NULL OR mqtt_topic IS NULL)''',
                      (rtsp, mqtt_topic, cam_name))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")