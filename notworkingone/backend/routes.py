import random
import requests
import os
import base64
from datetime import datetime, timedelta
from flask import Blueprint, request, Response
from auth import create_token, verify_token, token_required, get_token_from_request, verify_password, hash_password
from models import (
    get_user_by_username, get_all_officers, create_user, delete_user, update_password, update_user_profile,
    log_detection, get_weapon_preferences, update_weapon_preferences, get_cameras_list,
    get_detection_logs, get_dashboard_data,
    create_incident, get_incidents, get_incident_by_id, update_incident, get_incident_actions, delete_incident,
    
    get_all_cameras, create_camera, update_camera, delete_camera, toggle_camera_status
)
from config import DEFAULT_WEAPONS
from stream import generate, get_latest_detection, reload_camera_config


auth_bp = Blueprint('auth', __name__)
camera_bp = Blueprint('camera', __name__)
detection_bp = Blueprint('detection', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
incident_bp = Blueprint('incident', __name__)
admin_bp = Blueprint('admin', __name__)


IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'incident_images')
os.makedirs(IMAGES_DIR, exist_ok=True)



WEAPON_TYPE_MAP = {
    
    'gun': 'pistol',
    'heavy-weapon': 'heavy_weapon',
    'heavy_weapon': 'heavy_weapon',
    'knife': 'knife',
    'pistol': 'pistol',
    
    'Gun': 'pistol',
    'Pistol': 'pistol',
    'Knife': 'knife',
    'Heavy Weapon': 'heavy_weapon',
    'Heavy-Weapon': 'heavy_weapon',
    'Heavy_Weapon': 'heavy_weapon',
    
    'GUN': 'pistol',
    'PISTOL': 'pistol',
    'KNIFE': 'knife',
    'HEAVY WEAPON': 'heavy_weapon',
    'HEAVY-WEAPON': 'heavy_weapon',
    'HEAVY_WEAPON': 'heavy_weapon',
}

def normalize_weapon_type(weapon_type: str) -> str:
    """Normalize weapon type from MQTT to database format (case-insensitive fallback)."""
    
    if weapon_type in WEAPON_TYPE_MAP:
        return WEAPON_TYPE_MAP[weapon_type]
    
    normalized = weapon_type.lower().replace(' ', '_').replace('-', '_')
    return WEAPON_TYPE_MAP.get(normalized, normalized)


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




@admin_bp.get("/admin/cameras")
@token_required
def admin_get_cameras():
    """Get all cameras including inactive ones (admin only)"""
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        cameras_list = get_all_cameras()
        return {"cameras": [dict(cam) for cam in cameras_list]}
    except Exception as e:
        print(f"Admin get cameras error: {e}")
        return {"error": "Internal server error"}, 500


@admin_bp.post("/admin/cameras")
@token_required
def admin_create_camera():
    """Create a new camera (admin only)"""
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        data = request.json
        if not data or not data.get("camera_name") or not data.get("location"):
            return {"error": "camera_name and location are required"}, 400
        
        camera_id, error = create_camera(data)
        if camera_id:
            reload_camera_config()
            return {"message": "Camera created successfully", "camera_id": camera_id}, 201
        else:
            return {"error": error or "Failed to create camera"}, 409
    except Exception as e:
        print(f"Admin create camera error: {e}")
        return {"error": "Internal server error"}, 500


@admin_bp.put("/admin/cameras/<int:camera_id>")
@token_required
def admin_update_camera(camera_id):
    """Update camera details (admin only)"""
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        data = request.json
        if not data or not data.get("camera_name") or not data.get("location"):
            return {"error": "camera_name and location are required"}, 400
        
        success, error = update_camera(camera_id, data)
        if success:
            reload_camera_config()
            return {"message": "Camera updated successfully"}
        else:
            return {"error": error or "Camera not found"}, 404
    except Exception as e:
        print(f"Admin update camera error: {e}")
        return {"error": "Internal server error"}, 500


@admin_bp.delete("/admin/cameras/<int:camera_id>")
@token_required
def admin_delete_camera(camera_id):
    """Delete a camera (admin only)"""
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        success, message = delete_camera(camera_id)
        if success:
            return {"message": message}
        else:
            return {"error": message}, 400
    except Exception as e:
        print(f"Admin delete camera error: {e}")
        return {"error": "Internal server error"}, 500


@admin_bp.patch("/admin/cameras/<int:camera_id>/toggle")
@token_required
def admin_toggle_camera(camera_id):
    """Toggle camera active/inactive status (admin only)"""
    try:
        if request.user.get('role') != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
        
        new_status = toggle_camera_status(camera_id)
        if new_status is None:
            return {"error": "Camera not found"}, 404
        
        reload_camera_config()
        return {
            "message": f"Camera {'activated' if new_status else 'deactivated'} successfully",
            "is_active": new_status
        }
    except Exception as e:
        print(f"Admin toggle camera error: {e}")
        return {"error": "Internal server error"}, 500



@camera_bp.get("/cameras")
def cameras():
    try:
        cameras_list = get_cameras_list()
        return {"cameras": [dict(cam) for cam in cameras_list]}
    except Exception as e:
        print(f"Get cameras error: {e}")
        return {"error": "Internal server error"}, 500



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



@detection_bp.post("/log-detection")
@token_required
def log_det():
    try:
        data = request.json
        if not data or not data.get('weapon_type') or not data.get('camera_id'):
            return {"error": "Missing weapon_type or camera_id"}, 400
        
        user_id = request.user.get('user_id')
        weapon_type = normalize_weapon_type(data['weapon_type'])  
        camera_id = data['camera_id']
        confidence_score = data.get('confidence_score', 0.85)
        image_data = data.get('image')
        
        from database import get_db_connection
        from datetime import datetime, timedelta
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
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
                detection_id = existing_detection['id']
                time_since = (datetime.now() - datetime.fromisoformat(existing_detection['detection_time'])).total_seconds()
                remaining = int(60 - time_since)
                
                print(f"⏳ Skipping log for {weapon_type} on camera {camera_id} - recent detection {int(time_since)}s ago (cooldown: {remaining}s remaining)")
                
                is_new_log = False
                image_path = existing_detection['image_path']
            else:
                image_path = None
                if image_data:
                    try:
                        if ',' in image_data:
                            image_data = image_data.split(',')[1]
                        
                        img_bytes = base64.b64decode(image_data)
                        
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{weapon_type}_{camera_id}_{timestamp}.jpg"
                        filepath = os.path.join(IMAGES_DIR, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_bytes)
                        
                        image_path = filename
                        print(f"📸 Saved detection image: {filepath}")
                    except Exception as e:
                        print(f"❌ Error saving image: {e}")
                        import traceback
                        traceback.print_exc()
                
                detection_id = log_detection(user_id, camera_id, weapon_type, confidence_score, image_path)
                print(f"✅ Created NEW detection log #{detection_id} for {weapon_type} on camera {camera_id}")
                
                is_new_log = True
            
            incident_id = None
            is_new_incident = False
            
            if confidence_score >= 0.80:
                cursor.execute('''
                    SELECT id, status FROM incidents 
                    WHERE camera_id = ? 
                      AND weapon_type = ? 
                      AND detected_at >= ? 
                      AND status IN ('pending', 'responding')
                    ORDER BY detected_at DESC
                    LIMIT 1
                ''', (camera_id, weapon_type, one_minute_ago))
                
                existing_incident = cursor.fetchone()
                
                if existing_incident:
                    incident_id = existing_incident['id']
                    cursor.execute('UPDATE detection_logs SET incident_id = ? WHERE id = ?', 
                                 (incident_id, detection_id))
                    conn.commit()
                    is_new_incident = False
                else:
                    cursor.execute('SELECT location FROM cameras WHERE id = ?', (camera_id,))
                    row = cursor.fetchone()
                    location = row['location'] if row else 'Unknown'
                    
                    incident_id = create_incident(
                        camera_id, weapon_type, detection_id, user_id, location,
                        f"Automatic incident created from {weapon_type} detection",
                        image_path
                    )
                    
                    print(f"🚨 Created NEW incident #{incident_id} for {weapon_type} detection")
                    is_new_incident = True
            
            if incident_id:
                return {
                    "message": f"Detection logged and {'NEW' if is_new_incident else 'existing'} incident #{incident_id} {'created' if is_new_incident else 'linked'} for {weapon_type}",
                    "incident_id": incident_id,
                    "detection_id": detection_id,
                    "is_new_log": is_new_log,
                    "is_new_incident": is_new_incident,
                    "image_path": image_path
                }
            else:
                return {
                    "message": "Detection logged successfully (confidence too low for incident)",
                    "detection_id": detection_id,
                    "is_new_log": is_new_log,
                    "image_path": image_path
                }
        
    except Exception as e:
        print(f"❌ Log detection error: {e}")
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
        
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        logs = get_detection_logs(camera_id, weapon_type, days, limit)
        
        if start_time or end_time:
            filtered_logs = []
            for log in logs:
                try:
                    log_time = datetime.fromisoformat(log['detection_time']).time()
                    
                    if start_time and end_time:
                        start = datetime.strptime(start_time, '%H:%M').time()
                        end = datetime.strptime(end_time, '%H:%M').time()
                        
                        if start <= end:
                            if start <= log_time <= end:
                                filtered_logs.append(log)
                        else:
                            if log_time >= start or log_time <= end:
                                filtered_logs.append(log)
                    elif start_time:
                        start = datetime.strptime(start_time, '%H:%M').time()
                        if log_time >= start:
                            filtered_logs.append(log)
                    elif end_time:
                        end = datetime.strptime(end_time, '%H:%M').time()
                        if log_time <= end:
                            filtered_logs.append(log)
                except Exception as e:
                    print(f"Error filtering log by time: {e}")
                    continue
            
            logs = filtered_logs
        
        return {"logs": [dict(log) for log in logs]}
    except Exception as e:
        print(f"Get detection logs error: {e}")
        return {"error": "Internal server error"}, 500



@detection_bp.get("/incident_images/<path:filename>")
def serve_incident_image(filename):
    """Serve incident images"""
    try:
        clean_filename = filename.replace('incident_images/', '')
        filepath = os.path.join(IMAGES_DIR, clean_filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                image_data = f.read()
            return Response(image_data, mimetype='image/jpeg')
        else:
            return {"error": "Image not found"}, 404
    except Exception as e:
        print(f"❌ Serve image error: {e}")
        return {"error": "Internal server error"}, 500



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



@incident_bp.get("/incidents")
@token_required
def get_incidents_route():
    try:
        status = request.args.get('status')
        assigned_to = request.args.get('assigned_to', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        user_id = request.user.get('user_id')
        user_role = request.user.get('role')
        
        if user_role == 'officer':
            incidents_list = get_incidents(status, user_id, limit, officer_view=True)
        else:
            incidents_list = get_incidents(status, assigned_to, limit, officer_view=False)
        
        if start_time or end_time:
            filtered_incidents = []
            for incident in incidents_list:
                try:
                    incident_time = datetime.fromisoformat(incident['detected_at']).time()
                    
                    if start_time and end_time:
                        start = datetime.strptime(start_time, '%H:%M').time()
                        end = datetime.strptime(end_time, '%H:%M').time()
                        
                        if start <= end:
                            if start <= incident_time <= end:
                                filtered_incidents.append(incident)
                        else:
                            if incident_time >= start or incident_time <= end:
                                filtered_incidents.append(incident)
                    elif start_time:
                        start = datetime.strptime(start_time, '%H:%M').time()
                        if incident_time >= start:
                            filtered_incidents.append(incident)
                    elif end_time:
                        end = datetime.strptime(end_time, '%H:%M').time()
                        if incident_time <= end:
                            filtered_incidents.append(incident)
                except Exception as e:
                    print(f"Error filtering incident by time: {e}")
                    continue
            
            incidents_list = filtered_incidents
        
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
        
        incident = get_incident_by_id(incident_id)
        if not incident:
            return {"error": "Incident not found"}, 404
        
        if user_role == 'officer':
            if incident['assigned_to'] is not None and incident['assigned_to'] != user_id:
                return {"error": "You can only update incidents assigned to you or unassigned incidents"}, 403
            
            if incident['assigned_to'] is None and 'status' in data:
                data['assigned_to'] = user_id
        
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
            data.get('description', ''),
            data.get('image_path')
        )
        
        return {"message": "Incident created successfully", "incident_id": incident_id}, 201
    except Exception as e:
        print(f"Create incident error: {e}")
        return {"error": "Internal server error"}, 500


@incident_bp.delete("/incidents/<int:incident_id>")
@token_required
def delete_incident_route(incident_id):
    try:
        user_role = request.user.get('role')
        if user_role != 'admin':
            return {"error": "Unauthorized - Admin only"}, 403
            
        incident = get_incident_by_id(incident_id)
        if not incident:
            return {"error": "Incident not found"}, 404
            
        if delete_incident(incident_id):
            return {"message": "Incident and associated image deleted successfully"}
        else:
            return {"error": "Failed to delete incident"}, 500
    except Exception as e:
        print(f"Delete incident error: {e}")
        return {"error": "Internal server error"}, 500



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
        Location: {data.get('location', 'Unknown')}
        Camera: {data.get('camera_name', 'Unknown')}
        Time: {data.get('detected_at', 'Unknown')}
        Incident: {incident['incident_number']}
        ===========================================
        """)
        
        return {"message": "Email notification sent"}
    except Exception as e:
        print(f"Send email error: {e}")
        return {"error": "Internal server error"}, 500



@camera_bp.get("/video")
def video_stream():
    try:
        token = request.args.get("token")
        camera_id = request.args.get("camera_id", 1, type=int)
        
        if not token or not verify_token(token):
            return {"error": "Unauthorized"}, 401

        return Response(generate(camera_id), mimetype="multipart/x-mixed-replace; boundary=frame")
    except Exception as e:
        print(f"Video proxy error: {e}")
        return {"error": "Internal server error"}, 500



@detection_bp.get("/detection-status")
def get_detection_status():
    """Get current detection status from AI service - PUBLIC endpoint"""
    try:
        return get_latest_detection()
    except Exception as e:
        print(f"Error getting detection status: {e}")
        return {
            "detected": False,
            "objects": {},
            "timestamp": None
        }
