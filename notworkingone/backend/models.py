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


def log_detection(user_id, camera_id, weapon_type, confidence_score=0.85):
    """Log a weapon detection and update daily summary"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now()
        today = date.today()
        
        # Insert detection log
        cursor.execute('''INSERT INTO detection_logs 
                         (user_id, camera_id, weapon_type, confidence_score, detection_time, date_only) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (user_id, camera_id, weapon_type, confidence_score, now, today))
        
        detection_id = cursor.lastrowid
        
        # Update daily summary
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


# ========== INCIDENT MANAGEMENT FUNCTIONS ==========

def create_incident(camera_id, weapon_type, detection_id, created_by, location, description=''):
    """Create a new incident from detection"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get detection time
        cursor.execute('SELECT detection_time FROM detection_logs WHERE id = ?', (detection_id,))
        row = cursor.fetchone()
        detected_at = row['detection_time'] if row else datetime.now()
        
        # Generate incident number
        now = datetime.now()
        incident_number = f"INC-{now.strftime('%Y%m%d-%H%M%S')}"
        
        cursor.execute('''INSERT INTO incidents 
                         (incident_number, camera_id, weapon_type, detection_id, created_by, 
                          detected_at, location, description, status, priority) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'high')''',
                      (incident_number, camera_id, weapon_type, detection_id, created_by, 
                       detected_at, location, description))
        
        incident_id = cursor.lastrowid
        
        # Update detection log
        cursor.execute('UPDATE detection_logs SET incident_id = ? WHERE id = ?', 
                      (incident_id, detection_id))
        
        # Log action
        cursor.execute('''INSERT INTO incident_actions 
                         (incident_id, user_id, action_type, notes) 
                         VALUES (?, ?, 'created', 'Incident created from weapon detection')''',
                      (incident_id, created_by))
        
        conn.commit()
        return incident_id


def get_incidents(status=None, assigned_to=None, limit=100):
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
        
        if status:
            query += ' AND i.status = ?'
            params.append(status)
        
        if assigned_to:
            query += ' AND i.assigned_to = ?'
            params.append(assigned_to)
        
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
        
        # Log action
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


# ========== EXISTING FUNCTIONS ==========

def get_weapon_preferences(user_id):
    """Get weapon preferences for user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT weapon_type, is_enabled FROM weapon_preferences 
                         WHERE user_id = ? ORDER BY weapon_type''', (user_id,))
        return cursor.fetchall()


def update_weapon_preferences(user_id, preferences):
    """Update weapon preferences"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for pref in preferences:
            weapon_type = pref.get('weapon_type')
            is_enabled = pref.get('is_enabled', True)
            
            cursor.execute('''UPDATE weapon_preferences 
                             SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP 
                             WHERE user_id = ? AND weapon_type = ?''',
                          (is_enabled, user_id, weapon_type))
        conn.commit()


def get_cameras_list():
    """Get all active cameras"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT id, camera_name, location, description, is_active 
                         FROM cameras WHERE is_active = TRUE ORDER BY camera_name''')
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
    """Get dashboard data - show all detections regardless of user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get daily summary - ALL USERS
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
        
        # Get weapon totals - ALL USERS
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
        
        # Get recent detections - ALL USERS
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