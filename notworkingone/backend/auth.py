import time
import jwt
from functools import wraps
from flask import request
from config import SECRET_KEY, JWT_ALGO, JWT_EXPIRATION, pwd_ctx


def create_token(username, user_id, role):
    
    current_time = int(time.time())
    return jwt.encode({
        "sub": username,
        "user_id": user_id,
        "role": role,
        "iat": current_time,
        "exp": current_time + JWT_EXPIRATION
    }, SECRET_KEY, algorithm=JWT_ALGO)


def verify_token(token: str):
    
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except Exception as e:
        print(f"Token verification error: {e}")
        return None


def get_token_from_request():
    
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return None
    return token[7:]


def verify_password(plain_password, hashed_password):
    
    try:
        return pwd_ctx.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False



def token_required(f):
    
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return {"error": "Missing or invalid authorization header"}, 401
        
        user_data = verify_token(token)
        if not user_data:
            return {"error": "Invalid token"}, 401
        
        request.user = user_data
        return f(*args, **kwargs)
    
    return decorated