import sqlite3
from datetime import datetime, date
from database import get_db_connection
from config import pwd_ctx, DEFAULT_WEAPONS


def dict_from_row(row):
    """Safely convert sqlite3.Row to dict with defaults for missing columns"""
    if not row:
        return None
    
    d = dict(row)
    
    if 'is_active' not in d:
        d['is_active'] = True
    
    return d


def get_user_by_username(username):
    """Get user by username"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        return dict_from_row(row) if row else None


def get_all_officers():
    """Get all officers (for admin)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, username, first_name, last_name, badge_number, 
                         department, is_active FROM users WHERE role = "officer" ORDER BY username''')
        return cursor.fetchall()


def create_user(data):
    """Create a new user (admin creates officers)"""
    password_hash = pwd_ctx.hash(data['password'])
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''INSERT INTO users 
                            (username, password_hash, email, first_name, last_name, 
                             phone, role, badge_number, department) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (data['username'], password_hash, data['email'],
                           data.get('first_name', ''), data.get('last_name', ''),
                           data.get('phone', ''), 'officer',
                           data.get('badge_number', ''), data.get('department', '')))
            user_id = cursor.lastrowid
            
            # Create default weapon preferences
            for weapon in DEFAULT_WEAPONS:
                cursor.execute('''INSERT INTO weapon_preferences 
                                (user_id, weapon_type, is_enabled) VALUES (?, ?, ?)''',
                              (user_id, weapon, True))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def delete_user(username):
    """Delete a user and all related data"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = get_user_by_username(username)
        if user:
            user_id = user['id']
            cursor.execute('DELETE FROM weapon_preferences WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM detection_logs WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM daily_summary WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM incident_actions WHERE user_id = ?', (user_id,))
            cursor.execute('UPDATE incidents SET assigned_to = NULL WHERE assigned_to = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            conn.commit()
            return cursor.rowcount > 0
        return False


def update_password(username, new_password):
    """Update user password"""
    new_password_hash = pwd_ctx.hash(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?',
                      (new_password_hash, username))
        conn.commit()
        return cursor.rowcount > 0


def update_user_profile(username, first_name, last_name, phone, badge_number, department):
    """Update user profile information"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''UPDATE users 
                         SET first_name = ?, last_name = ?, phone = ?, 
                             badge_number = ?, department = ?, updated_at = CURRENT_TIMESTAMP 
                         WHERE username = ?''',
                      (first_name, last_name, phone, badge_number, department, username))
        conn.commit()
        return cursor.rowcount > 0


def log_detection(user_id, camera_id, weapon_type, confidence_score=0.85, image_path=None):
    """Log a weapon detection with optional image path and update daily summary"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now()
        today = date.today()
        
        cursor.execute('''INSERT INTO detection_logs 
                         (user_id, camera_id, weapon_type, confidence_score, detection_time, date_only, image_path) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (user_id, camera_id, weapon_type, confidence_score, now, today, image_path))
        
        detection_id = cursor.lastrowid
        
        cursor.execute('''INSERT OR REPLACE INTO daily_summary 
                         (user_id, camera_id, detection_date, weapon_type, total_detections, 
                          avg_confidence, first_detection, last_detection)
                         SELECT ?, ?, ?, ?, 
                                COALESCE((SELECT total_detections FROM daily_summary 
                                         WHERE user_id = ? AND camera_id = ? AND detection_date = ? AND weapon_type = ?), 0) + 1,
                                (SELECT AVG(confidence_score) FROM detection_logs 
                                 WHERE user_id = ? AND camera_id = ? AND date_only = ? AND weapon_type = ?),
                                COALESCE((SELECT first_detection FROM daily_summary 
                                         WHERE user_id = ? AND camera_id = ? AND detection_date = ? AND weapon_type = ?), ?),
                                ?''',
                      (user_id, camera_id, today, weapon_type,
                       user_id, camera_id, today, weapon_type,
                       user_id, camera_id, today, weapon_type,
                       user_id, camera_id, today, weapon_type, now,
                       now))
        
        conn.commit()
        return detection_id


def create_incident(camera_id, weapon_type, detection_id, created_by, location, description='', image_path=None):
    """Create a new incident from detection with optional image"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT detection_time, image_path FROM detection_logs WHERE id = ?', (detection_id,))
        row = cursor.fetchone()
        detected_at = row['detection_time'] if row else datetime.now()
        
        if not image_path and row and row['image_path']:
            image_path = row['image_path']
        
        now = datetime.now()
        import random
        unique_suffix = now.strftime('%f')[:4]  
        incident_number = f"INC-{now.strftime('%Y%m%d-%H%M%S')}-{unique_suffix}"
        
        cursor.execute('''INSERT INTO incidents 
                         (incident_number, camera_id, weapon_type, detection_id, created_by, 
                          detected_at, location, description, status, priority, image_path) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'high', ?)''',
                      (incident_number, camera_id, weapon_type, detection_id, created_by, 
                       detected_at, location, description, image_path))
        
        incident_id = cursor.lastrowid
        
        cursor.execute('UPDATE detection_logs SET incident_id = ? WHERE id = ?', 
                      (incident_id, detection_id))
        
        cursor.execute('''INSERT INTO incident_actions 
                         (incident_id, user_id, action_type, notes) 
                         VALUES (?, ?, 'created', 'Incident created from weapon detection')''',
                      (incident_id, created_by))
        
        conn.commit()
        return incident_id


def get_incidents(status=None, assigned_to=None, limit=100, officer_view=False):
    """Get incidents with filters"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT i.*, c.camera_name, c.location as camera_location,
                   u1.username as created_by_username,
                   u2.username as assigned_to_username,
                   u3.username as resolved_by_username
            FROM incidents i
            JOIN cameras c ON i.camera_id = c.id
            JOIN users u1 ON i.created_by = u1.id
            LEFT JOIN users u2 ON i.assigned_to = u2.id
            LEFT JOIN users u3 ON i.resolved_by = u3.id
            WHERE 1=1
        '''
        
        params = []
        
        if officer_view and assigned_to:
            query += ' AND (i.assigned_to = ? OR i.assigned_to IS NULL)'
            params.append(assigned_to)
        elif not officer_view and assigned_to:
            query += ' AND i.assigned_to = ?'
            params.append(assigned_to)
        
        if status:
            query += ' AND i.status = ?'
            params.append(status)
        
        query += ' ORDER BY i.detected_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        return cursor.fetchall()


def get_incident_by_id(incident_id):
    """Get incident details"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.*, c.camera_name, c.location as camera_location,
                   u1.username as created_by_username, u1.first_name as created_by_first_name,
                   u2.username as assigned_to_username, u2.first_name as assigned_to_first_name,
                   u3.username as resolved_by_username, u3.first_name as resolved_by_first_name
            FROM incidents i
            JOIN cameras c ON i.camera_id = c.id
            JOIN users u1 ON i.created_by = u1.id
            LEFT JOIN users u2 ON i.assigned_to = u2.id
            LEFT JOIN users u3 ON i.resolved_by = u3.id
            WHERE i.id = ?
        ''', (incident_id,))
        return cursor.fetchone()


def update_incident(incident_id, user_id, updates):
    """Update incident details"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        set_parts = []
        params = []
        
        if 'status' in updates:
            set_parts.append('status = ?')
            params.append(updates['status'])
            
            if updates['status'] == 'responding':
                set_parts.append('responded_at = CURRENT_TIMESTAMP')
            elif updates['status'] == 'resolved':
                set_parts.append('resolved_at = CURRENT_TIMESTAMP')
                set_parts.append('resolved_by = ?')
                params.append(user_id)
        
        if 'priority' in updates:
            set_parts.append('priority = ?')
            params.append(updates['priority'])
        
        if 'assigned_to' in updates:
            set_parts.append('assigned_to = ?')
            params.append(updates['assigned_to'])
        
        if 'response_notes' in updates:
            set_parts.append('response_notes = ?')
            params.append(updates['response_notes'])
        
        if 'resolution_notes' in updates:
            set_parts.append('resolution_notes = ?')
            params.append(updates['resolution_notes'])
        
        set_parts.append('updated_at = CURRENT_TIMESTAMP')
        
        params.append(incident_id)
        
        query = f"UPDATE incidents SET {', '.join(set_parts)} WHERE id = ?"
        cursor.execute(query, params)
        
        action_type = updates.get('status', 'updated')
        cursor.execute('''INSERT INTO incident_actions 
                         (incident_id, user_id, action_type, notes) 
                         VALUES (?, ?, ?, ?)''',
                      (incident_id, user_id, action_type, 
                       updates.get('response_notes') or updates.get('resolution_notes') or 'Incident updated'))
        
        conn.commit()
        return cursor.rowcount > 0


def get_incident_actions(incident_id):
    """Get action history for incident"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ia.*, u.username, u.first_name, u.last_name, u.badge_number
            FROM incident_actions ia
            JOIN users u ON ia.user_id = u.id
            WHERE ia.incident_id = ?
            ORDER BY ia.created_at DESC
        ''', (incident_id,))
        return cursor.fetchall()


def delete_incident(incident_id):
    """Delete an incident, its actions, and physical image. Unlinks from detection log."""
    import os
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Get image path
        cursor.execute('SELECT image_path FROM incidents WHERE id = ?', (incident_id,))
        incident = cursor.fetchone()
        
        # 2. Delete physical image if it exists
        if incident and incident['image_path']:
            image_path = incident['image_path']
            IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'incident_images')
            filepath = os.path.join(IMAGES_DIR, image_path)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"🗑️ Deleted image file: {filepath}")
                except Exception as e:
                    print(f"⚠️ Failed to delete image file {filepath}: {e}")
                    
        # 3. Unlink from detection logs (so logs are kept, but unconnected)
        cursor.execute('UPDATE detection_logs SET incident_id = NULL WHERE incident_id = ?', (incident_id,))
        
        # 4. Delete related incident actions
        cursor.execute('DELETE FROM incident_actions WHERE incident_id = ?', (incident_id,))
        
        # 5. Delete the incident record
        cursor.execute('DELETE FROM incidents WHERE id = ?', (incident_id,))
        
        conn.commit()
        return cursor.rowcount > 0


# ========== WEAPON PREFERENCES ==========

def get_weapon_preferences(user_id):
    """Get weapon preferences for user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT weapon_type, is_enabled FROM weapon_preferences 
                         WHERE user_id = ? ORDER BY weapon_type''', (user_id,))
        prefs = cursor.fetchall()
        
        if not prefs:
            print(f"No preferences found for user {user_id}, creating defaults...")
            for weapon in DEFAULT_WEAPONS:
                cursor.execute('''INSERT INTO weapon_preferences 
                                (user_id, weapon_type, is_enabled) VALUES (?, ?, ?)''',
                              (user_id, weapon, True))
            conn.commit()
            
            cursor.execute('''SELECT weapon_type, is_enabled FROM weapon_preferences 
                             WHERE user_id = ? ORDER BY weapon_type''', (user_id,))
            prefs = cursor.fetchall()
        
        return prefs


def update_weapon_preferences(user_id, preferences):
    """Update weapon preferences"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print(f"Updating preferences for user {user_id}: {preferences}")
        
        for pref in preferences:
            weapon_type = pref.get('weapon_type')
            is_enabled = pref.get('is_enabled', True)
            
            cursor.execute('''INSERT OR REPLACE INTO weapon_preferences 
                             (user_id, weapon_type, is_enabled, updated_at) 
                             VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                          (user_id, weapon_type, is_enabled))
            
            print(f"  - {weapon_type}: {'enabled' if is_enabled else 'disabled'}")
        
        conn.commit()
        print(f"✅ Saved {len(preferences)} preferences for user {user_id}")


def get_cameras_list():
    """Get all active cameras"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, camera_name, location, description, is_active 
                         FROM cameras WHERE is_active = TRUE''')
        return cursor.fetchall()


def get_detection_logs(camera_id=None, weapon_type=None, days=7, limit=100):
    """Get detection logs with filters"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT dl.*, c.camera_name, c.location, u.username, i.incident_number, i.status as incident_status
            FROM detection_logs dl
            JOIN cameras c ON dl.camera_id = c.id
            JOIN users u ON dl.user_id = u.id
            LEFT JOIN incidents i ON dl.incident_id = i.id
            WHERE dl.date_only >= date('now', '-{} days')
        '''.format(days)
        
        params = []
        
        if camera_id:
            query += ' AND dl.camera_id = ?'
            params.append(camera_id)
        
        if weapon_type:
            query += ' AND dl.weapon_type = ?'
            params.append(weapon_type)
        
        query += ' ORDER BY dl.detection_time DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        return cursor.fetchall()


def get_dashboard_data(user_id, days=7, camera_id=None):
    """Get dashboard data"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT ds.*, c.camera_name, c.location
            FROM daily_summary ds
            JOIN cameras c ON ds.camera_id = c.id
            WHERE ds.detection_date >= date('now', '-{} days')
        '''.format(days)
        
        params = []
        
        if camera_id:
            query += ' AND ds.camera_id = ?'
            params.append(camera_id)
        
        query += ' ORDER BY ds.detection_date DESC, ds.weapon_type'
        
        cursor.execute(query, params)
        daily_data = cursor.fetchall()
        
        query2 = '''
            SELECT ds.weapon_type, SUM(ds.total_detections) as total, AVG(ds.avg_confidence) as avg_conf
            FROM daily_summary ds
            WHERE ds.detection_date >= date('now', '-{} days')
        '''.format(days)
        
        params2 = []
        
        if camera_id:
            query2 += ' AND ds.camera_id = ?'
            params2.append(camera_id)
        
        query2 += ' GROUP BY ds.weapon_type ORDER BY total DESC'
        
        cursor.execute(query2, params2)
        weapon_totals = cursor.fetchall()
        
        query3 = '''
            SELECT dl.*, c.camera_name, c.location, u.username
            FROM detection_logs dl
            JOIN cameras c ON dl.camera_id = c.id
            JOIN users u ON dl.user_id = u.id
            WHERE 1=1
        '''
        
        params3 = []
        
        if camera_id:
            query3 += ' AND dl.camera_id = ?'
            params3.append(camera_id)
        
        query3 += ' ORDER BY dl.detection_time DESC LIMIT 20'
        
        cursor.execute(query3, params3)
        recent_detections = cursor.fetchall()
        
        return {
            "daily_summary": [dict(row) for row in daily_data],
            "weapon_totals": [dict(row) for row in weapon_totals],
            "recent_detections": [dict(row) for row in recent_detections]
        }


import threading
_detection_cooldown_lock = threading.Lock()

def process_system_detection(camera_id, weapon_type, confidence_score, image_bytes=None):
    """Process an automated system detection from the backend stream."""
    from datetime import datetime, timedelta
    import os
    from config import SYSTEM_USER
    
    with _detection_cooldown_lock:
        system_user_id = 1
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (SYSTEM_USER['username'],))
            row = cursor.fetchone()
            if row:
                system_user_id = row['id']
                
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            cursor.execute('''
                SELECT id, detection_time, image_path FROM detection_logs 
                WHERE camera_id = ? 
                  AND weapon_type = ? 
                  AND detection_time >= ?
                ORDER BY detection_time DESC
                LIMIT 1
            ''', (camera_id, weapon_type, one_minute_ago))
            
            existing_detection = cursor.fetchone()
            
            if existing_detection:
                time_since = (datetime.now() - datetime.fromisoformat(existing_detection['detection_time'])).total_seconds()
                print(f"⏳ System skipping log for {weapon_type} on camera {camera_id} - recent detection {int(time_since)}s ago")
                return {"detection_id": existing_detection['id'], "incident_id": None, "image_path": existing_detection['image_path'], "is_new": False}

        image_path = None
        if image_bytes:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{weapon_type}_{camera_id}_{timestamp}.jpg"
                IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'incident_images')
                os.makedirs(IMAGES_DIR, exist_ok=True)
                filepath = os.path.join(IMAGES_DIR, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_bytes)
                image_path = filename
            except Exception as e:
                print(f"❌ Error saving system image: {e}")
                
        detection_id = log_detection(system_user_id, camera_id, weapon_type, confidence_score, image_path)
        print(f"✅ Created NEW SYSTEM detection log #{detection_id} for {weapon_type}")
        
        incident_id = None
        if confidence_score >= 0.80:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                one_minute_ago = datetime.now() - timedelta(minutes=1)

                cursor.execute('''
                    SELECT id, status FROM incidents 
                    WHERE camera_id = ? AND weapon_type = ? AND detected_at >= ? AND status IN ('pending', 'responding')
                    ORDER BY detected_at DESC LIMIT 1
                ''', (camera_id, weapon_type, one_minute_ago))
                existing_incident = cursor.fetchone()

                if existing_incident:
                    incident_id = existing_incident['id']
                    cursor.execute('UPDATE detection_logs SET incident_id = ? WHERE id = ?', (incident_id, detection_id))
                    conn.commit()
                else:
                    cursor.execute('SELECT location FROM cameras WHERE id = ?', (camera_id,))
                    row = cursor.fetchone()
                    location = row['location'] if row else 'Unknown'
                    incident_id = create_incident(camera_id, weapon_type, detection_id, system_user_id, location, f"Automatic system incident for {weapon_type}", image_path)
                    
        return {"detection_id": detection_id, "incident_id": incident_id, "image_path": image_path, "is_new": True}


# ========== CAMERA MANAGEMENT FUNCTIONS ==========

def get_all_cameras():
    """Get all cameras (active and inactive) for admin management"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, camera_name, location, description, stream_url, rtsp_url, mqtt_topic, is_active, created_at 
                         FROM cameras ORDER BY id''')
        return cursor.fetchall()


def create_camera(data):
    """Create a new camera (with rtsp_url and mqtt_topic)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        mqtt_topic = data.get('mqtt_topic', '').strip()
        if mqtt_topic:
            cursor.execute('SELECT id FROM cameras WHERE mqtt_topic = ?', (mqtt_topic,))
            if cursor.fetchone():
                return None, "MQTT topic is already in use by another camera"

        try:
            cursor.execute('''INSERT INTO cameras 
                            (camera_name, location, description, stream_url, rtsp_url, mqtt_topic, is_active) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                          (data['camera_name'], data['location'],
                           data.get('description', ''),
                           data.get('stream_url', ''),
                           data.get('rtsp_url', ''),
                           data.get('mqtt_topic', ''),
                           data.get('is_active', True)))
            conn.commit()
            return cursor.lastrowid, None
        except sqlite3.IntegrityError:
            return None, "Camera name already exists"


def update_camera(camera_id, data):
    """Update camera details (with rtsp_url and mqtt_topic)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''UPDATE cameras 
                             SET camera_name = ?, location = ?, description = ?, 
                                 stream_url = ?, rtsp_url = ?, mqtt_topic = ?, is_active = ?
                             WHERE id = ?''',
                          (data['camera_name'], data['location'],
                           data.get('description', ''),
                           data.get('stream_url', ''),
                           data.get('rtsp_url', ''),
                           data.get('mqtt_topic', ''),
                           data.get('is_active', True),
                           camera_id))
            conn.commit()
            return cursor.rowcount > 0, None
        except sqlite3.IntegrityError:
            return False, "Camera name already exists"


def delete_camera(camera_id):
    """Delete a camera (only if no detections/incidents linked)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as cnt FROM detection_logs WHERE camera_id = ?', (camera_id,))
        row = cursor.fetchone()
        if row and row['cnt'] > 0:
            return False, "Cannot delete camera with existing detection logs"

        cursor.execute('SELECT COUNT(*) as cnt FROM incidents WHERE camera_id = ?', (camera_id,))
        row = cursor.fetchone()
        if row and row['cnt'] > 0:
            return False, "Cannot delete camera with existing incidents"

        cursor.execute('DELETE FROM cameras WHERE id = ?', (camera_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Camera deleted successfully"
        return False, "Camera not found"


def toggle_camera_status(camera_id):
    """Toggle camera active/inactive status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_active FROM cameras WHERE id = ?', (camera_id,))
        row = cursor.fetchone()
        if not row:
            return None
        new_status = not bool(row['is_active'])
        cursor.execute('UPDATE cameras SET is_active = ? WHERE id = ?', (new_status, camera_id))
        conn.commit()
        return new_status