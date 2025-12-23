import random
import requests
from flask import Blueprint, request, Response
from datetime import datetime, timedelta
from auth import create_token, verify_token, token_required, get_token_from_request, verify_password, hash_password
from models import (
    get_user_by_username, get_all_officers, create_user, delete_user, update_password, update_user_profile,
    log_detection, get_weapon_preferences, update_weapon_preferences, get_cameras_list,
    get_detection_logs, get_dashboard_data,
    create_incident, get_incidents, get_incident_by_id, update_incident, get_incident_actions
)
from config import AI_STREAM_URL, DEFAULT_WEAPONS

# Create blueprints
auth_bp = Blueprint('auth', __name__)
camera_bp = Blueprint('camera', __name__)
detection_bp = Blueprint('detection', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
incident_bp = Blueprint('incident', __name__)
admin_bp = Blueprint('admin', __name__)

# Weapon type mapping from MQTT to database format
WEAPON_TYPE_MAP = {
    'gun': 'pistol',
    'heavy-weapon': 'heavy_weapon',
    'knife': 'knife',
    'pistol': 'pistol',
    'heavy_weapon': 'heavy_weapon'
}

def normalize_weapon_type(weapon_type):
    """Normalize weapon type from MQTT to database format"""
    return WEAPON_TYPE_MAP.get(weapon_type.lower(), weapon_type.lower())

# ========== AUTH ROUTES ==========
@auth_bp.post("/login")
def login():
    try:
        data = request.json
        if not data or not data.get("username") or not data.get("password"):
            return {"error": "Missing credentials"}, 400

        user = get_user_by_username(data["username"])
        if not user:
            return {"error": "Invalid credentials"}, 401
        
        if not verify_password(data["password"], user["password_hash"]):
            return {"error": "Invalid credentials"}, 401
        
        if not user.get("is_active", True):
            return {"error": "Account is deactivated"}, 403

        token = create_token(data["username"], user["id"], user["role"])
        
        return {
            "access_token": token,
            "username": data["username"],
            "user_id": user["id"],
            "role": user["role"],
            "full_name": f"{user['first_name']} {user['last_name']}"
        }
    except Exception as e:
        print(f"Login error: {e}")
        return {"error": "Internal server error"}, 500


@auth_bp.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


@auth_bp.post("/change-password")
@token_required
def change_password():
    try:
        data = request.json
        if not data or not data.get("current_password") or not data.get("new_password"):
            return {"error": "Missing current_password or new_password"}, 400
        
        if len(data["new_password"]) < 6:
            return {"error": "New password must be at least 6 characters long"}, 400
        
        username = request.user.get('sub')
        user = get_user_by_username(username)
        
        if not user:
            return {"error": "User not found"}, 404
        
        if not verify_password(data["current_password"], user["password_hash"]):
            return {"error": "Current password is incorrect"}, 400
        
        if update_password(username, data["new_password"]):
            return {"message": "Password changed successfully"}
        else:
            return {"error": "Failed to update password"}, 500
    except Exception as e:
        print(f"Change password error: {e}")
        return {"error": "Internal server error"}, 500


@auth_bp.get("/user-info")
@token_required
def user_info():
    try:
        user = get_user_by_username(request.user.get('sub'))
        if user:
            return {
                "username": user["username"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "phone": user["phone"],
                "role": user["role"],
                "badge_number": user.get("badge_number", ""),
                "department": user["department"],
                "created_at": user["created_at"]
            }
        else:
            return {"error": "User not found"}, 404
    except Exception as e:
        print(f"User info error: {e}")
        return {"error": "Internal server error"}, 500


@auth_bp.put("/user-profile")
@token_required
def update_profile():
    try:
        data = request.json
        username = request.user.get('sub')
        
        if update_user_profile(username, data.get('first_name'), data.get('last_name'),
                              data.get('phone'), data.get('badge_number', ''), data.get('department')):
            return {"message": "Profile updated successfully"}
        else:
            return {"error": "Failed to update profile"}, 500
    except Exception as e:
        print(f"Update profile error: {e}")
        return {"error": "Internal server error"}, 500


# ========== ADMIN ROUTES ==========
@admin_bp.get("/officers")
@token_required
def get_officers():
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        officers_list = get_all_officers()
        return {"officers": [dict(o) for o in officers_list]}
    except Exception as e:
        print(f"Get officers error: {e}")
        return {"error": "Internal server error"}, 500


@admin_bp.post("/create-officer")
@token_required
def create_officer():
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        data = request.json
        if not data or not data.get("username") or not data.get("password") or not data.get("email"):
            return {"error": "Missing required fields"}, 400
        
        if len(data["username"]) < 3:
            return {"error": "Username must be at least 3 characters long"}, 400
        
        if len(data["password"]) < 6:
            return {"error": "Password must be at least 6 characters long"}, 400
        
        if '@' not in data["email"]:
            return {"error": "Invalid email address"}, 400
        
        if create_user(data):
            return {"message": "Officer account created successfully"}, 201
        else:
            return {"error": "Username or email already exists"}, 409
    except Exception as e:
        print(f"Create officer error: {e}")
        return {"error": "Internal server error"}, 500


@admin_bp.delete("/delete-officer/<username>")
@token_required
def delete_officer(username):
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        if username == request.user.get('sub'):
            return {"error": "Cannot delete your own account"}, 400
        
        if delete_user(username):
            return {"message": "Officer account deleted successfully"}
        else:
            return {"error": "Officer not found"}, 404
    except Exception as e:
        print(f"Delete officer error: {e}")
        return {"error": "Internal server error"}, 500


# ========== CAMERA ROUTES ==========
@camera_bp.get("/cameras")
def cameras():
    try:
        cameras_list = get_cameras_list()
        return {"cameras": [dict(cam) for cam in cameras_list]}
    except Exception as e:
        print(f"Get cameras error: {e}")
        return {"error": "Internal server error"}, 500


# ========== WEAPON PREFERENCES ROUTES ==========
@detection_bp.get("/weapon-preferences")
@token_required
def get_prefs():
    try:
        user_id = request.user.get('user_id')
        prefs = get_weapon_preferences(user_id)
        
        if not prefs:
            from database import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for weapon in DEFAULT_WEAPONS:
                    cursor.execute('''INSERT INTO weapon_preferences 
                                    (user_id, weapon_type, is_enabled) VALUES (?, ?, ?)''',
                                  (user_id, weapon, True))
                conn.commit()
            prefs = get_weapon_preferences(user_id)
        
        return {"preferences": [dict(pref) for pref in prefs]}
    except Exception as e:
        print(f"Get weapon preferences error: {e}")
        return {"error": "Internal server error"}, 500


@detection_bp.post("/weapon-preferences")
@token_required
def set_prefs():
    try:
        data = request.json
        if not data or 'preferences' not in data:
            return {"error": "Missing preferences data"}, 400
        
        user_id = request.user.get('user_id')
        update_weapon_preferences(user_id, data['preferences'])
        
        return {"message": "Preferences updated successfully"}
    except Exception as e:
        print(f"Update weapon preferences error: {e}")
        return {"error": "Internal server error"}, 500


# ========== DETECTION ROUTES ==========
@detection_bp.post("/log-detection")
@token_required
def log_det():
    """
    FIXED: Separates detection log cooldown from incident creation cooldown
    - Detection logs: 5-minute cooldown per weapon+camera
    - Incidents: Independent check - creates if no recent incident exists
    """
    try:
        data = request.json
        if not data or not data.get('weapon_type') or not data.get('camera_id'):
            return {"error": "Missing weapon_type or camera_id"}, 400
        
        user_id = request.user.get('user_id')
        weapon_type = data['weapon_type']
        camera_id = data['camera_id']
        confidence_score = data.get('confidence_score', 0.85)
        
        from database import get_db_connection
        from datetime import datetime, timedelta
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            
            # ===== STEP 1: Check/Create Detection Log (5-min cooldown) =====
            cursor.execute('''
                SELECT id, detection_time FROM detection_logs 
                WHERE camera_id = ? 
                  AND weapon_type = ? 
                  AND detection_time >= ?
                ORDER BY detection_time DESC
                LIMIT 1
            ''', (camera_id, weapon_type, five_minutes_ago))
            
            existing_detection = cursor.fetchone()
            
            if existing_detection:
                # Detection log exists - skip creating new one
                detection_id = existing_detection['id']
                time_since = (datetime.now() - datetime.fromisoformat(existing_detection['detection_time'])).total_seconds()
                remaining = int(300 - time_since)
                
                print(f"⏳ Skipping log for {weapon_type} on camera {camera_id} - recent detection {int(time_since)}s ago (cooldown: {remaining}s remaining)")
                
                is_new_log = False
            else:
                # No recent detection - CREATE new log
                detection_id = log_detection(user_id, camera_id, weapon_type, confidence_score)
                
                print(f"✅ Created NEW detection log #{detection_id} for {weapon_type} on camera {camera_id} (confidence: {confidence_score:.2%})")
                
                is_new_log = True
            
            # ===== STEP 2: Check/Create Incident (INDEPENDENT check) =====
            incident_id = None
            is_new_incident = False
            
            if confidence_score >= 0.80:
                # Check for existing recent incident (within last 5 minutes)
                cursor.execute('''
                    SELECT id, status FROM incidents 
                    WHERE camera_id = ? 
                      AND weapon_type = ? 
                      AND detected_at >= ? 
                      AND status IN ('pending', 'responding')
                    ORDER BY detected_at DESC
                    LIMIT 1
                ''', (camera_id, weapon_type, five_minutes_ago))
                
                existing_incident = cursor.fetchone()
                
                if existing_incident:
                    # Incident exists - just link detection to it
                    incident_id = existing_incident['id']
                    print(f"✓ Using existing incident #{incident_id} for {weapon_type} (status: {existing_incident['status']})")
                    
                    # Link the detection to this incident
                    cursor.execute('UPDATE detection_logs SET incident_id = ? WHERE id = ?', 
                                 (incident_id, detection_id))
                    conn.commit()
                    
                    is_new_incident = False
                else:
                    # No recent incident - CREATE new one
                    cursor.execute('SELECT location FROM cameras WHERE id = ?', (camera_id,))
                    row = cursor.fetchone()
                    location = row['location'] if row else 'Unknown'
                    
                    incident_id = create_incident(
                        camera_id, 
                        weapon_type,
                        detection_id, 
                        user_id, 
                        location,
                        f"Automatic incident created from {weapon_type} detection"
                    )
                    
                    print(f"🚨 Created NEW incident #{incident_id} for {weapon_type} detection (confidence: {confidence_score:.2%})")
                    
                    is_new_incident = True
            
            # ===== STEP 3: Return Response =====
            if incident_id:
                return {
                    "message": f"Detection logged and {'NEW' if is_new_incident else 'existing'} incident #{incident_id} {'created' if is_new_incident else 'linked'} for {weapon_type}",
                    "incident_id": incident_id,
                    "detection_id": detection_id,
                    "is_new_log": is_new_log,
                    "is_new_incident": is_new_incident
                }
            else:
                return {
                    "message": "Detection logged successfully (confidence too low for incident)",
                    "detection_id": detection_id,
                    "is_new_log": is_new_log
                }
        
    except Exception as e:
        print(f"Log detection error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "Internal server error"}, 500


@detection_bp.get("/detection-logs")
@token_required
def get_logs():
    try:
        camera_id = request.args.get('camera_id', type=int)
        weapon_type = request.args.get('weapon_type')
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        logs = get_detection_logs(camera_id, weapon_type, days, limit)
        return {"logs": [dict(log) for log in logs]}
    except Exception as e:
        print(f"Get detection logs error: {e}")
        return {"error": "Internal server error"}, 500


# ========== DASHBOARD ROUTES ==========
@dashboard_bp.get("/dashboard-data")
@token_required
def dashboard():
    try:
        user_id = request.user.get('user_id')
        days = request.args.get('days', 7, type=int)
        camera_id = request.args.get('camera_id', type=int)
        
        data = get_dashboard_data(user_id, days, camera_id)
        return data
    except Exception as e:
        print(f"Dashboard data error: {e}")
        return {"error": "Internal server error"}, 500


# ========== INCIDENT ROUTES ==========
@incident_bp.get("/incidents")
@token_required
def get_incidents_route():
    try:
        status = request.args.get('status')
        assigned_to = request.args.get('assigned_to', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        user_id = request.user.get('user_id')
        user_role = request.user.get('role')
        
        # For officers: only show incidents assigned to them or unassigned
        # For admins: show all incidents (or filtered by assigned_to if specified)
        if user_role == 'officer':
            # Officers can only see their own assignments or unassigned incidents
            incidents_list = get_incidents(status, user_id, limit, officer_view=True)
        else:
            # Admins can see all incidents
            incidents_list = get_incidents(status, assigned_to, limit, officer_view=False)
        
        return {"incidents": [dict(inc) for inc in incidents_list]}
    except Exception as e:
        print(f"Get incidents error: {e}")
        return {"error": "Internal server error"}, 500


@incident_bp.get("/incidents/<int:incident_id>")
@token_required
def get_incident_detail(incident_id):
    try:
        incident = get_incident_by_id(incident_id)
        if incident:
            actions = get_incident_actions(incident_id)
            return {
                "incident": dict(incident),
                "actions": [dict(a) for a in actions]
            }
        else:
            return {"error": "Incident not found"}, 404
    except Exception as e:
        print(f"Get incident detail error: {e}")
        return {"error": "Internal server error"}, 500


@incident_bp.put("/incidents/<int:incident_id>")
@token_required
def update_incident_route(incident_id):
    try:
        data = request.json
        if not data:
            return {"error": "Missing update data"}, 400
        
        user_id = request.user.get('user_id')
        user_role = request.user.get('role')
        
        # Get the incident to check permissions
        incident = get_incident_by_id(incident_id)
        if not incident:
            return {"error": "Incident not found"}, 404
        
        # Permission check for officers
        if user_role == 'officer':
            # Officers can only update incidents assigned to them or unassigned incidents
            if incident['assigned_to'] is not None and incident['assigned_to'] != user_id:
                return {"error": "You can only update incidents assigned to you or unassigned incidents"}, 403
            
            # When officer takes action on unassigned incident, auto-assign to them
            if incident['assigned_to'] is None and 'status' in data:
                data['assigned_to'] = user_id
        
        # Update the incident
        if update_incident(incident_id, user_id, data):
            return {"message": "Incident updated successfully"}
        else:
            return {"error": "Failed to update incident"}, 500
    except Exception as e:
        print(f"Update incident error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "Internal server error"}, 500


@incident_bp.post("/incidents/create")
@token_required
def create_incident_route():
    try:
        data = request.json
        if not data or not data.get('camera_id') or not data.get('weapon_type') or not data.get('detection_id'):
            return {"error": "Missing required fields"}, 400
        
        user_id = request.user.get('user_id')
        
        incident_id = create_incident(
            data['camera_id'],
            data['weapon_type'],
            data['detection_id'],
            user_id,
            data.get('location', ''),
            data.get('description', '')
        )
        
        return {"message": "Incident created successfully", "incident_id": incident_id}, 201
    except Exception as e:
        print(f"Create incident error: {e}")
        return {"error": "Internal server error"}, 500


# ========== EMAIL NOTIFICATION ROUTE ==========
@incident_bp.post("/send-alert-email")
@token_required
def send_alert_email():
    try:
        data = request.json
        if not data or not data.get('incident_id'):
            return {"error": "Missing incident_id"}, 400
        
        incident = get_incident_by_id(data['incident_id'])
        if not incident:
            return {"error": "Incident not found"}, 404
        
        user = get_user_by_username(request.user.get('sub'))
        if not user:
            return {"error": "User not found"}, 404
        
        print(f"""
        ===========================================
        🚨 EMAIL ALERT 🚨
        ===========================================
        To: {user['email']}
        Subject: URGENT: Weapon Detected - {incident['incident_number']}
        
        A {data.get('weapon_type', 'weapon')} has been detected!
        
        Location: {data.get('location', 'Unknown')}
        Camera: {data.get('camera_name', 'Unknown')}
        Time: {data.get('detected_at', 'Unknown')}
        Incident: {incident['incident_number']}
        
        Please respond immediately.
        
        View incident: http://localhost:5173/
        ===========================================
        """)
        
        return {"message": "Email notification sent"}
    except Exception as e:
        print(f"Send email error: {e}")
        return {"error": "Internal server error"}, 500


# ========== VIDEO STREAM ROUTE - PROXY ONLY, NO AUTO-LOGGING ==========
@camera_bp.get("/video")
def video_stream():
    try:
        token = request.args.get("token")
        camera_id = request.args.get("camera_id", 1, type=int)
        
        if not token or not verify_token(token):
            return {"error": "Unauthorized"}, 401

        # Just proxy the video stream - detection logging is handled by frontend polling
        r = requests.get(AI_STREAM_URL, stream=True)
        return Response(r.iter_content(chunk_size=1024),
                        content_type=r.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=frame"))
    except Exception as e:
        print(f"Video proxy error: {e}")
        return {"error": "Internal server error"}, 500


# ========== NEW DETECTION STATUS ENDPOINT ==========
@detection_bp.get("/detection-status")
def get_detection_status():
    """Get current detection status from AI service - PUBLIC endpoint for frontend polling"""
    try:
        # Get detection data from AI service
        detection_response = requests.get(f"{AI_STREAM_URL.replace('/stream', '/detection')}", timeout=2)
        
        if detection_response.ok:
            detection_data = detection_response.json()
            return {
                "detected": detection_data.get('detected', False),
                "objects": detection_data.get('objects', {}),
                "timestamp": detection_data.get('timestamp')
            }
        else:
            return {
                "detected": False,
                "objects": {},
                "timestamp": None
            }
    except Exception as e:
        print(f"Error getting detection status: {e}")
        return {
            "detected": False,
            "objects": {},
            "timestamp": None
        }