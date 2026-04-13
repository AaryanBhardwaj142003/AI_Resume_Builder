from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime, timedelta

class ResumeDB:
    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._client = MongoClient(MONGO_URI)
            self._db = self._client['resume_builder']
            self._collection = self._db['resumes']
            # Create index on user_id for faster lookups (changed from email)
            # We use sparse=True because existing documents might not have a user_id yet
            self._collection.create_index("user_id", unique=True, sparse=True)
            # Create index on email as well since we still use it for profile info
            self._collection.create_index("email", unique=True)
        return self._collection

    def get_or_create_user(self, user_info):
        """
        Handle OAuth login. If user doesn't exist, create them with 'free' role.
        Update email and picture just in case they changed.
        user_info should have: 'user_id', 'email', 'name', 'picture'
        """
        user_id = user_info.get("user_id")
        
        # Check if user already exists
        existing_user = self.collection.find_one({"user_id": user_id})
        
        if not existing_user:
            # Create a brand new user document
            new_user = {
                "user_id": user_id,
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "role": "free",  # default role
                "original_resume": None,
                "tailored_versions": []
            }
            self.collection.insert_one(new_user)
            return new_user
        else:
            # Optionally update info
            self.collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                }}
            )
            return existing_user

    def check_quota(self, user_id):
        """
        Check if the user is allowed to generate a new resume.
        - Paid users: Unlimited
        - Free users: 1 tailored resume every 7 days
        Returns (True, None) if allowed, or (False, "reason string") if denied.
        """
        user = self.collection.find_one({"user_id": user_id})
        if not user:
            return False, "User not found"

        # Paid users bypass quota
        if user.get("role") == "paid":
            return True, None

        # Free user logic: check tailored_versions
        versions = user.get("tailored_versions", [])
        if not versions:
            return True, None  # Has never generated one before

        # Find the most recent generation timestamp
        # Assuming created_at is ISO format string
        if len(versions)>=2:
            return False, "Free users can only generate 2 tailored resume. Please try again later."

        return True, None

    # 1. Save or Update the ORIGINAL resume
    def save_original_resume(self, user_id, resume_data):
        self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {"original_resume": resume_data},
            },
            upsert=False # We assume user is created upon login
        )
        return True

    # 2. Add a NEW tailored version to the user's history
    def add_tailored_version(self, user_id, jd, optimized_resume):
        version_entry = {
            "jd_used": jd,
            "optimized_resume": optimized_resume,
            "created_at": datetime.now().isoformat()
        }

        # $push adds the object to the 'tailored_versions' array
        self.collection.update_one(
            {"user_id": user_id},
            {"$push": {"tailored_versions": version_entry}}
        )
        return True

    # 3. Get the original resume by user_id
    def get_original_resume(self, user_id):
        user_doc = self.collection.find_one({"user_id": user_id})
        return user_doc['original_resume'] if user_doc and 'original_resume' in user_doc else None

    # 4. Get the optimization history
    def get_optimization_history(self, user_id):
        user_doc = self.collection.find_one({"user_id": user_id}, {"tailored_versions": 1, "email": 1})
        if not user_doc:
            return None
        return user_doc
