from flask import Flask
from flask_cors import CORS
from database import init_db
from routes import auth_bp, camera_bp, detection_bp, dashboard_bp, incident_bp, admin_bp
from stream import start_mqtt_client


app = Flask(__name__)
CORS(app)


app.register_blueprint(auth_bp)
app.register_blueprint(camera_bp)
app.register_blueprint(detection_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(incident_bp)
app.register_blueprint(admin_bp)


init_db()


start_mqtt_client()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)