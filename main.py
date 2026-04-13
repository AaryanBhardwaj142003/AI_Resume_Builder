import json
import jwt
from functools import wraps
from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta

from engine import ResumeOptimizer
from database import ResumeDB  # Import the DB class we created
from config import JWT_SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, FRONTEND_URL
from schema import JD_FORMAT

app = Flask(__name__)
# Enable CORS for all routes (important for React frontend to talk to Flask)
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:5173"],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# Required by Authlib for sessions
app.secret_key = JWT_SECRET_KEY 

# Initialize the engine and database once when the app starts
optimizer = ResumeOptimizer()
db = ResumeDB()

# --- OAuth 2.0 Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# --- JWT Middleware ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Extract Bearer token from 'Authorization' header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            print("Token missing in headers")
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
            print(f"Token validated for user: {current_user_id}")
        except jwt.ExpiredSignatureError:
            print("Token expired")
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {e}")
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorated

# --- Auth Routes ---
@app.route('/login/google')
def login_google():
    """Redirect to Google for login."""
    redirect_uri = url_for('auth_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback/google')
def auth_google():
    """Handle Google OAuth callback, create/fetch user, and return JWT."""
    token = google.authorize_access_token()
    # Authlib automatically parses the ID token into 'userinfo'
    user_info = token.get('userinfo')
    
    if not user_info:
        # Fallback to manual fetch if userinfo is missing from token
        resp = google.get('userinfo')
        user_info = resp.json()
    
    # Extract needed info
    extracted_info = {
        "user_id": user_info.get('sub') or user_info.get('id'),  # Google's unique ID
        "email": user_info.get('email'),
        "name": user_info.get('name'),
        "picture": user_info.get('picture')
    }  
    # Save to MongoDB
    user = db.get_or_create_user(extracted_info)
    
    # Generate JWT
    jwt_token = jwt.encode(
        {
            'user_id': user['user_id'],
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(days=7) # Token expires in 7 days
        }, 
        JWT_SECRET_KEY, 
        algorithm="HS256"
    )
    
    # Redirect back to frontend with the token
    # On the React side, you'll grab this token from the URL and save it to localStorage
    return redirect(f"{FRONTEND_URL}/login/success?token={jwt_token}")

# --- Core App Routes ---
@app.post("/save")
@token_required
def save_resume(current_user_id):
    """
    Endpoint to save the user's original resume.
    Expected JSON: { "resume": { ... } }
    """
    data = request.get_json()
    resume_json = data.get("resume")

    if not resume_json:
        return jsonify({"error": "Please provide resume data"}), 400

    # Save the original resume to MongoDB using user_id
    success = db.save_original_resume(current_user_id, resume_json)

    if success:
        return jsonify({"message": f"Original resume saved successfully!"}), 200
    else:
        return jsonify({"error": "Failed to save resume to database"}), 500


@app.post("/optimize")
@token_required
def optimize_resume(current_user_id):
    """
    Endpoint to optimize a resume based on a Job Description.
    Expected JSON: { "jd": { ... } }
    """
    data = request.get_json()
    jd_json = data.get("jd")

    # --- 1. Check user Quota before proceeding ---
    allowed, message = db.check_quota(current_user_id)
    if not allowed:
        return jsonify({"error": message}), 403 # Return 403 Forbidden for quota limit

    # --- 2. Fetch the original resume from MongoDB ---
    original_resume = db.get_original_resume(current_user_id)

    if not original_resume:
        return jsonify({"error": "No original resume found for this user. Please call /save first."}), 404

    print(f"Starting Resume Optimization for User {current_user_id}...")

    # --- 3. Process the resume using the LLM engine ---
    try:
        print(f"Calling openai API...")
        updated_resume = optimizer.optimize_resume(original_resume, jd_json , provider="openai")
        print(f"OpenAI API returned.")
    except Exception as e:
        print(f"LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "LLM request timed out or failed. Please try again."}), 504

    if updated_resume:
        # --- 4. Save this tailored version to the user's history ---
        db.add_tailored_version(current_user_id, jd_json, updated_resume)

        print("Optimization Complete and saved to history!")
        return jsonify(updated_resume), 200
    else:
        print("Failed to optimize resume.")
        return jsonify({"error": "LLM failed to generate an optimized resume"}), 500


@app.get("/resume")
@token_required
def get_saved_resume(current_user_id):
    """Fetch the user's saved original resume."""
    original_resume = db.get_original_resume(current_user_id)
    return jsonify({"resume": original_resume}), 200


@app.get("/history")
@token_required
def get_optimization_history(current_user_id):
    """Fetch all optimized versions for a user's resume."""
    # We moved this query logic to database.py for better abstraction!
    user_doc = db.get_optimization_history(current_user_id)

    if not user_doc:
        return jsonify({"error": "No history found for this user."}), 404

    return jsonify({
        "email": user_doc.get("email"),
        "history": user_doc.get("tailored_versions", [])
    }), 200

if __name__ == "__main__":
    print("Starting Resume Optimizer API with Auth...")
    app.run(debug=True, port=5000)
