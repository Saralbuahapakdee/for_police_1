# Backend - Weapon Detection System

## Project Structure

```
backend/
├── app.py              # Main Flask application
├── config.py           # Configuration and constants
├── database.py         # Database connection and initialization
├── models.py           # Database models and queries
├── auth.py             # Authentication utilities
├── routes.py           # API routes (blueprints)
├── requirements.txt    # Python dependencies
├── __init__.py         # Package initialization
├── .gitignore          # Git ignore rules
└── users.db            # SQLite database (created at runtime)
```

## File Descriptions

### app.py
Main Flask application entry point. Sets up the Flask app, enables CORS, registers blueprints, and initializes the database.

### config.py
Contains all configuration settings:
- Database credentials
- JWT settings
- API endpoints
- Default data (admin user, cameras, weapons)

### database.py
Handles database operations:
- Database connection context manager
- Database initialization and schema creation
- Default data seeding

### models.py
Contains all business logic and database queries:
- User management (create, delete, update)
- Weapon preferences
- Detection logging
- Camera management
- Dashboard data

### auth.py
Authentication utilities:
- JWT token creation and verification
- Password hashing and verification
- Token extraction from requests
- Decorator for protected routes

### routes.py
API routes organized into blueprints:
- `auth_bp`: Login, register, password change, profile
- `camera_bp`: Camera list and video stream
- `detection_bp`: Weapon preferences and detection logs
- `dashboard_bp`: Dashboard analytics
- `public_bp`: Public data endpoints

## API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `POST /logout` - User logout
- `POST /change-password` - Change password (requires token)
- `DELETE /delete-account` - Delete account (requires token)

### User Profile
- `GET /user-info` - Get user info (requires token)
- `PUT /user-profile` - Update profile (requires token)

### Cameras
- `GET /cameras` - Get all cameras
- `GET /video` - Video stream proxy

### Weapon Preferences
- `GET /weapon-preferences` - Get preferences (requires token)
- `POST /weapon-preferences` - Update preferences (requires token)

### Detection
- `POST /log-detection` - Log detection (requires token)
- `GET /detection-logs` - Get detection logs

### Dashboard
- `GET /dashboard-data` - Get dashboard data (requires token)

### Public
- `GET /public/current-detections` - Current detections (public)
- `GET /public/camera-status` - Camera status (public)

## Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The app will start on `http://localhost:5000`

## Database

The app uses SQLite for data storage. Database is automatically created and initialized on first run.

Default admin user:
- Username: `admin`
- Password: `admin123`

## Security Notes

- Change `SECRET_KEY` in config.py for production
- Use environment variables for sensitive data
- Enable HTTPS in production
- Implement rate limiting