import random
import requests
from flask import Blueprint, request, Response
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
    try:
        data = request.json
        if not data or not data.get('weapon_type') or not data.get('camera_id'):
            return {"error": "Missing weapon_type or camera_id"}, 400
        
        user_id = request.user.get('user_id')
        detection_id = log_detection(user_id, data['camera_id'], data['weapon_type'], 
                                     data.get('confidence_score', 0.85))
        
        # Auto-create incident for high-confidence detections
        if data.get('confidence_score', 0.85) >= 0.80:
            from database import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT location FROM cameras WHERE id = ?', (data['camera_id'],))
                row = cursor.fetchone()
                location = row['location'] if row else 'Unknown'
            
            incident_id = create_incident(
                data['camera_id'], 
                data['weapon_type'], 
                detection_id, 
                user_id, 
                location,
                f"Automatic incident created from {data['weapon_type']} detection"
            )
            
            return {"message": "Detection logged and incident created", "incident_id": incident_id}
        
        return {"message": "Detection logged successfully"}
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
        
        incidents_list = get_incidents(status, assigned_to, limit)
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
        
        if update_incident(incident_id, user_id, data):
            return {"message": "Incident updated successfully"}
        else:
            return {"error": "Failed to update incident"}, 500
    except Exception as e:
        print(f"Update incident error: {e}")
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
        
        # Get incident details
        incident = get_incident_by_id(data['incident_id'])
        if not incident:
            return {"error": "Incident not found"}, 404
        
        # Get user email
        user = get_user_by_username(request.user.get('sub'))
        if not user:
            return {"error": "User not found"}, 404
        
        # TODO: Implement email sending
        # For now, just log it
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


# ========== VIDEO STREAM ROUTE ==========
@camera_bp.get("/video")
def video_stream():
    try:
        token = request.args.get("token")
        camera_id = request.args.get("camera_id", 1, type=int)
        
        if not token or not verify_token(token):
            return {"error": "Unauthorized"}, 401

        user_data = verify_token(token)
        
        # Random detection simulation (10% chance)
        if user_data and random.random() < 0.1:
            weapons = DEFAULT_WEAPONS
            weapon = random.choice(weapons)
            confidence = random.uniform(0.7, 0.95)
            detection_id = log_detection(user_data.get('user_id'), camera_id, weapon, confidence)
            
            # Auto-create incident for high-confidence detections
            if confidence >= 0.80:
                from database import get_db_connection
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT location FROM cameras WHERE id = ?', (camera_id,))
                    row = cursor.fetchone()
                    location = row['location'] if row else 'Unknown'
                
                create_incident(camera_id, weapon, detection_id, user_data.get('user_id'), 
                              location, f"Automatic incident from {weapon} detection")

        r = requests.get(AI_STREAM_URL, stream=True)
        return Response(r.iter_content(chunk_size=1024),
                        content_type=r.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=frame"))
    except Exception as e:
        print(f"Video proxy error: {e}")
        return {"error": "Internal server error"}, 500