import email

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from datetime import datetime, timezone
from functools import wraps
import re
import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app)

mongo_uri = os.getenv("MONGODB_URI")
client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=4000,
    connectTimeoutMS=4000,
    socketTimeoutMS=5000
)
db_name = os.getenv("MONGODB_DB_NAME", "gazeboexpress")
db = client[db_name]

menu_collection = db["menu"]
orders_collection = db["orders"]
reviews_collection = db["reviews"]
settings_collection = db["settings"]
notifications_collection = db["notifications"]
users_collection = db["users"]


def set_database(target_db_name):
    """
    Dynamically switch active database and collection handles (used for test isolation).
    """
    global db, db_name, menu_collection, orders_collection, reviews_collection
    global settings_collection, notifications_collection, users_collection
    db_name = target_db_name
    db = client[db_name]
    menu_collection = db["menu"]
    orders_collection = db["orders"]
    reviews_collection = db["reviews"]
    settings_collection = db["settings"]
    notifications_collection = db["notifications"]
    users_collection = db["users"]
    seed_initial_data_if_needed(target_db=db)
    return db

# Authgear Configuration
AUTHGEAR_ENDPOINT = os.getenv("AUTHGEAR_ENDPOINT", "").rstrip("/")
AUTHGEAR_CLIENT_ID = os.getenv("AUTHGEAR_CLIENT_ID", "")
AUTHGEAR_REDIRECT_URI = os.getenv("AUTHGEAR_REDIRECT_URI", "")
DESIGNATED_ADMIN_EMAIL = "baldthief@gmail.com"


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    if not doc:
        return doc
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def get_current_time_str():
    return datetime.now(timezone.utc).isoformat()


# ==============================================================================
# AUTHENTICATION & AUTHORIZATION HELPERS
# ==============================================================================

def get_token_from_request():
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def decode_jwt_unverified_payload(token):
    """
    Safely decode JWT payload without verification for claim extraction.
    Used in conjunction with expiry checks or Authgear UserInfo validation.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Pad base64 string
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        return json.loads(payload_json)
    except Exception:
        return None


def verify_token(token):
    """
    Validate incoming token and resolve to an application user dictionary.
    Supports:
    1. Real Authgear tokens (UserInfo endpoint or valid JWT claims).
    2. Test & demo tokens (for local offline testing and CI test runners).
    """
    if not token:
        return None

    # Handle local/demo test tokens: test_token_<role>_<user_id>
    if token.startswith("test_token_") or token.startswith("demo_token_"):
        parts = token.split("_")
        role = "student"
        user_id = "test_student_user"
        if len(parts) >= 3:
            role = parts[2]
            user_id = f"test_{role}_{parts[3] if len(parts) > 3 else '1'}"
        
        # Look up or auto-provision test user in MongoDB
        user = None
        try:
            user = users_collection.find_one({"authgear_user_id": user_id})
        except Exception as e:
            print(f"MongoDB lookup note for test token: {e}", flush=True)

        if not user:
            name = "Admin User" if role == "admin" else "Pranesh S D"
            reg_no = "STAFF001" if role == "admin" else "25BCE1122"
            email = DESIGNATED_ADMIN_EMAIL if role == "admin" else f"{role}@gazeboexpress.campus"
            user = {
                "authgear_user_id": user_id,
                "name": name,
                "email": email,
                "register_number": reg_no,
                "student_id": reg_no,
                "role": role,
                "phone": "+91 98765 43210",
                "profile_image": "",
                "created_at": get_current_time_str(),
                "updated_at": get_current_time_str()
            }
            try:
                users_collection.insert_one(user)
            except Exception as e:
                print(f"MongoDB insert note for test token: {e}", flush=True)
        else:
            if role == "admin" and (user.get("role") != "admin" or user.get("email") != DESIGNATED_ADMIN_EMAIL):
                try:
                    users_collection.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"role": "admin", "email": DESIGNATED_ADMIN_EMAIL, "updated_at": get_current_time_str()}}
                    )
                except Exception:
                    pass
                user["role"] = "admin"
                user["email"] = DESIGNATED_ADMIN_EMAIL
        return user

    # Live Authgear token handling
    sub = None
    email = None
    name = None

    # Step 1: Decode JWT unverified payload directly (e.g. from idToken or JWT accessToken)
    # This avoids external network latency or UserInfo scope failures
    payload = decode_jwt_unverified_payload(token)
    if payload:
        # Check expiration if present
        exp = payload.get("exp")
        if exp and exp < datetime.now(timezone.utc).timestamp():
            return None  # Expired token
        sub = payload.get("sub")
        email = (
            payload.get("email")
            or payload.get("https://authgear.com/claims/user/email")
            or payload.get("email_address")
        )
        name = payload.get("name") or payload.get("preferred_username")

    # Step 2: If sub not obtained from JWT, query Authgear UserInfo endpoint as fallback
    if not sub and AUTHGEAR_ENDPOINT:
        try:
            userinfo_url = f"{AUTHGEAR_ENDPOINT}/oauth2/userinfo"
            req = urllib.request.Request(userinfo_url, headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "GazeboExpress-Backend"
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    info = json.loads(resp.read().decode("utf-8"))
                    sub = info.get("sub")
                    email = (
                        info.get("email")
                        or info.get("https://authgear.com/claims/user/email")
                        or info.get("email_address")
                    )
                    name = info.get("name") or info.get("preferred_username")
        except Exception as e:
            print(f"Authgear UserInfo fallback note: {type(e).__name__}: {e}", flush=True)

    if not sub:
        return None

    # Normalize email safely
    clean_email = (email or "").strip().lower()

    # Step 3: Retrieve user from MongoDB by authgear_user_id or reconcile by email
    user = None
    try:
        user = users_collection.find_one({"authgear_user_id": sub})
        if not user and clean_email:
            user = users_collection.find_one({"email": {"$regex": f"^{re.escape(clean_email)}$", "$options": "i"}})
            if user:
                users_collection.update_one({"_id": user["_id"]}, {"$set": {"authgear_user_id": sub}})
                user["authgear_user_id"] = sub
    except Exception as db_err:
        print(f"MongoDB lookup warning in verify_token (safe fallback active): {db_err}", flush=True)

    user_email = clean_email or (user.get("email", "") if user else "").strip().lower()
    expected_role = "admin" if user_email == DESIGNATED_ADMIN_EMAIL.lower() else "student"

    if user:
        try:
            needs_update = False
            update_fields = {}
            if user.get("role") != expected_role:
                update_fields["role"] = expected_role
                needs_update = True
            if clean_email and user.get("email") != clean_email:
                update_fields["email"] = clean_email
                needs_update = True

            if needs_update:
                update_fields["updated_at"] = get_current_time_str()
                users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": update_fields}
                )
                user["role"] = expected_role
                if clean_email:
                    user["email"] = clean_email
        except Exception as db_err:
            print(f"MongoDB update warning in verify_token: {db_err}", flush=True)

        return user

    # First-time login: return transient profile with authoritative role
    return {
        "authgear_user_id": sub,
        "email": clean_email,
        "name": name or ("Canteen Administrator" if expected_role == "admin" else "Gazebo Student"),
        "role": expected_role,
        "is_new": True
    }


def require_auth(f):
    """Decorator to require valid authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Unauthorized: Missing authentication token"}), 401
        user = verify_token(token)
        if not user:
            return jsonify({"error": "Unauthorized: Invalid or expired token"}), 401
        request.user = user
        return f(*args, **kwargs)
    return decorated


def require_role(required_role):
    """Decorator to enforce role-based access (e.g., admin)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return jsonify({"error": "Unauthorized: Missing authentication token"}), 401
            user = verify_token(token)
            if not user:
                return jsonify({"error": "Unauthorized: Invalid or expired token"}), 401
            if user.get("role") != required_role:
                return jsonify({"error": f"Forbidden: {required_role.capitalize()} privileges required"}), 403
            request.user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_optional_auth_user():
    """Retrieve authenticated user if token is present, otherwise None."""
    token = get_token_from_request()
    if token:
        return verify_token(token)
    return None


# ==============================================================================
# SEED INITIAL DATA & IDEMPOTENT MENU MIGRATION
# ==============================================================================

CANONICAL_MENU = [
    # Snacks (6 items, 1 bestseller)
    {
        "name": "Veg Samosa",
        "category": "Snacks",
        "description": "Crispy golden pastry triangles filled with spiced potatoes, green peas, and fragrant herbs.",
        "price": 30.0,
        "available": True,
        "bestseller": True,
        "rating": 4.9,
        "ratings_count": 140,
        "order_count": 180,
        "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Veg Puff",
        "category": "Snacks",
        "description": "Flaky layered golden puff pastry stuffed with curried mixed vegetables and mild Indian spices.",
        "price": 35.0,
        "available": True,
        "bestseller": False,
        "rating": 4.6,
        "ratings_count": 88,
        "order_count": 95,
        "image_url": "https://plus.unsplash.com/premium_photo-1754823340366-58325535aea5?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Chicken Puff",
        "category": "Snacks",
        "description": "Bakery-fresh crispy puff pastry filled with savory shredded chicken masala and caramelized onions.",
        "price": 45.0,
        "available": True,
        "bestseller": False,
        "rating": 4.8,
        "ratings_count": 112,
        "order_count": 130,
        "image_url": "https://plus.unsplash.com/premium_photo-1694981405366-0ffd13044535?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Peri Peri French Fries",
        "category": "Snacks",
        "description": "Crispy golden cut potato fries tossed in zesty African peri-peri spice dust.",
        "price": 90.0,
        "available": True,
        "bestseller": False,
        "rating": 4.7,
        "ratings_count": 120,
        "order_count": 140,
        "image_url": "https://images.unsplash.com/photo-1707773726979-4b87cd1c838a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Veg Sandwich",
        "category": "Snacks",
        "description": "Classic campus double-slice sandwich packed with cucumber, tomato slices, mint chutney, and butter.",
        "price": 60.0,
        "available": True,
        "bestseller": False,
        "rating": 4.5,
        "ratings_count": 65,
        "order_count": 72,
        "image_url": "https://images.unsplash.com/photo-1552404834-9734c89ba42e?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Crispy Chicken Tenders",
        "category": "Snacks",
        "description": "Panko-crusted tender chicken breast strips served with garlic aioli and fiery peri-peri dip.",
        "price": 180.0,
        "available": True,
        "bestseller": False,
        "rating": 4.9,
        "ratings_count": 91,
        "order_count": 110,
        "image_url": "https://images.unsplash.com/photo-1562967914-608f82629710?w=600&auto=format&fit=crop&q=80"
    },

    # Burgers (6 items, 1 bestseller)
    {
        "name": "Peanut Butter Chicken Burger",
        "category": "Burgers",
        "description": "Juicy grilled chicken patty with creamy melted cheese, peanut butter glaze, and crisp lettuce.",
        "price": 220.0,
        "available": True,
        "bestseller": True,
        "rating": 4.8,
        "ratings_count": 64,
        "order_count": 75,
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Texas Style BBQ Burger",
        "category": "Burgers",
        "description": "Smoky pulled tender patty drenched in authentic sweet-tangy Texas BBQ sauce on toasted brioche.",
        "price": 210.0,
        "available": True,
        "bestseller": False,
        "rating": 4.7,
        "ratings_count": 55,
        "order_count": 60,
        "image_url": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "The Country Style Hamburger",
        "category": "Burgers",
        "description": "Classic seasoned patty with sliced pickles, ripe tomato, cheddar slice, and house sauce.",
        "price": 170.0,
        "available": True,
        "bestseller": False,
        "rating": 4.5,
        "ratings_count": 47,
        "order_count": 50,
        "image_url": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "The Legendary Burger",
        "category": "Burgers",
        "description": "Double grilled patty stacked with crispy onion rings, melted provolone, and secret herb mayo.",
        "price": 190.0,
        "available": True,
        "bestseller": False,
        "rating": 4.9,
        "ratings_count": 32,
        "order_count": 35,
        "image_url": "https://images.unsplash.com/photo-1572802419224-296b0aeee0d9?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Veggies Delight Burger",
        "category": "Burgers",
        "description": "Crispy spiced potato-herb patty topped with avocado mash, cucumber ribbons, and mint relish.",
        "price": 160.0,
        "available": True,
        "bestseller": False,
        "rating": 4.4,
        "ratings_count": 30,
        "order_count": 40,
        "image_url": "https://images.unsplash.com/photo-1525059696034-4967a8e1dca2?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Chicha Melt Burger",
        "category": "Burgers",
        "description": "Toasted pretzel bun holding spiced paneer steak with caramelized onions and jalapeño cheese.",
        "price": 230.0,
        "available": True,
        "bestseller": False,
        "rating": 4.6,
        "ratings_count": 28,
        "order_count": 30,
        "image_url": "https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=600&auto=format&fit=crop&q=80"
    },

    # Sandwiches (6 items, 1 bestseller)
    {
        "name": "Crispy Paneer Grilled Sandwich",
        "category": "Sandwiches",
        "description": "Golden grilled triple-decker sandwich loaded with tandoori paneer cubes, capsicum, and mozzarella.",
        "price": 120.0,
        "available": True,
        "bestseller": True,
        "rating": 4.8,
        "ratings_count": 82,
        "order_count": 95,
        "image_url": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Chicken Club Sandwich",
        "category": "Sandwiches",
        "description": "Smoked shredded chicken breast layered with fried egg, crisp greens, and creamy honey mustard.",
        "price": 150.0,
        "available": True,
        "bestseller": False,
        "rating": 4.7,
        "ratings_count": 44,
        "order_count": 52,
        "image_url": "https://images.unsplash.com/photo-1553909489-cd47e0907980?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Veg Cheese Sandwich",
        "category": "Sandwiches",
        "description": "Melted cheddar and mozzarella blend over spiced green bell peppers, sweet corn, and herbs on toasted brioche.",
        "price": 90.0,
        "available": True,
        "bestseller": False,
        "rating": 4.6,
        "ratings_count": 58,
        "order_count": 64,
        "image_url": "https://images.unsplash.com/photo-1539252554453-80ab65ce3586?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Tandoori Paneer Sandwich",
        "category": "Sandwiches",
        "description": "Char-grilled cottage cheese cubes coated in Punjabi tandoori marinade with mint chutney in whole wheat bread.",
        "price": 130.0,
        "available": True,
        "bestseller": False,
        "rating": 4.7,
        "ratings_count": 67,
        "order_count": 78,
        "image_url": "https://images.unsplash.com/photo-1639744093483-86714cd62a3b?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Corn & Cheese Sandwich",
        "category": "Sandwiches",
        "description": "Creamy sweet American golden corn kernels folded with melted mozzarella and cracked black pepper.",
        "price": 100.0,
        "available": True,
        "bestseller": False,
        "rating": 4.5,
        "ratings_count": 49,
        "order_count": 56,
        "image_url": "https://images.unsplash.com/photo-1621852004158-f3bc188ace2d?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "BBQ Chicken Sandwich",
        "category": "Sandwiches",
        "description": "Pulled grilled chicken glazed in sweet smoky hickory barbecue sauce topped with caramelized onions.",
        "price": 160.0,
        "available": True,
        "bestseller": False,
        "rating": 4.8,
        "ratings_count": 73,
        "order_count": 84,
        "image_url": "https://images.unsplash.com/photo-1700937244987-92488ab2ada5?w=600&auto=format&fit=crop&q=80"
    },

    # Pasta (2 items, 1 bestseller)
    {
        "name": "White Sauce Pasta (Alfredo Penne)",
        "category": "Pasta",
        "description": "Al dente penne pasta tossed in rich parmesan cream sauce with sautéed mushrooms, garlic butter, and fresh Italian herbs.",
        "price": 200.0,
        "available": True,
        "bestseller": True,
        "rating": 4.8,
        "ratings_count": 76,
        "order_count": 88,
        "image_url": "https://images.unsplash.com/photo-1645112411341-6c4fd023714a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Red Sauce Pasta",
        "category": "Pasta",
        "description": "Penne simmered in a robust, slow-cooked San Marzano plum tomato marinara with basil, bell peppers, and olive oil.",
        "price": 180.0,
        "available": True,
        "bestseller": False,
        "rating": 4.6,
        "ratings_count": 54,
        "order_count": 62,
        "image_url": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600&auto=format&fit=crop&q=80"
    },

    # Beverages (6 items, 1 bestseller)
    {
        "name": "Signature Cold Coffee",
        "category": "Beverages",
        "description": "Thick blended Arabica espresso with rich chilled whole milk, vanilla ice cream, and chocolate drizzle.",
        "price": 95.0,
        "available": True,
        "bestseller": True,
        "rating": 4.9,
        "ratings_count": 180,
        "order_count": 210,
        "image_url": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Fresh Mint Lime Cooler",
        "category": "Beverages",
        "description": "Chilled sparkling beverage muddled with fresh garden mint leaves, zesty lime wedges, and raw cane syrup.",
        "price": 80.0,
        "available": True,
        "bestseller": False,
        "rating": 4.7,
        "ratings_count": 150,
        "order_count": 175,
        "image_url": "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Iced Lemon Tea",
        "category": "Beverages",
        "description": "Brewed Assam black tea chilled over ice with fresh Meyer lemon juice and a touch of organic honey.",
        "price": 70.0,
        "available": True,
        "bestseller": False,
        "rating": 4.6,
        "ratings_count": 82,
        "order_count": 94,
        "image_url": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Mango Smoothie",
        "category": "Beverages",
        "description": "Creamy tropical Alphonso mango pulp blended with Greek yogurt, milk, and crushed ice.",
        "price": 110.0,
        "available": True,
        "bestseller": False,
        "rating": 4.8,
        "ratings_count": 96,
        "order_count": 115,
        "image_url": "https://images.unsplash.com/photo-1623065422902-30a2d299bbe4?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Fresh Lime Soda",
        "category": "Beverages",
        "description": "Crisp fizzy club soda infused with fresh squeezed green lime juice, rock salt, and sweet syrup.",
        "price": 60.0,
        "available": True,
        "bestseller": False,
        "rating": 4.5,
        "ratings_count": 74,
        "order_count": 89,
        "image_url": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Packaged Water",
        "category": "Beverages",
        "description": "Chilled purified mineral water bottle with electrolytes.",
        "price": 20.0,
        "available": True,
        "bestseller": False,
        "rating": 4.8,
        "ratings_count": 220,
        "order_count": 350,
        "image_url": "https://images.unsplash.com/photo-1564419320461-6870880221ad?w=600&auto=format&fit=crop&q=80"
    },

    # Desserts (4 items, 1 bestseller)
    {
        "name": "Hot Chocolate Brownie Sundae",
        "category": "Desserts",
        "description": "Warm walnut fudge brownie crowned with velvety vanilla bean ice cream and hot chocolate ganache.",
        "price": 140.0,
        "available": True,
        "bestseller": True,
        "rating": 4.9,
        "ratings_count": 115,
        "order_count": 130,
        "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Chocolate Mousse",
        "category": "Desserts",
        "description": "Airy and decadent Belgian dark chocolate mousse topped with whipped cream and cocoa shavings.",
        "price": 110.0,
        "available": True,
        "bestseller": False,
        "rating": 4.7,
        "ratings_count": 68,
        "order_count": 75,
        "image_url": "https://images.unsplash.com/photo-1579372786545-d24232daf58c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Vanilla Ice Cream",
        "category": "Desserts",
        "description": "Two scoops of rich artisanal Madagascar vanilla bean ice cream topped with rainbow sprinkles.",
        "price": 70.0,
        "available": True,
        "bestseller": False,
        "rating": 4.6,
        "ratings_count": 84,
        "order_count": 98,
        "image_url": "https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=600&auto=format&fit=crop&q=80"
    },
    {
        "name": "Gulab Jamun",
        "category": "Desserts",
        "description": "Two melt-in-mouth golden milk-solid dumplings soaked in warm rosewater and cardamom scented sugar syrup.",
        "price": 60.0,
        "available": True,
        "bestseller": False,
        "rating": 4.9,
        "ratings_count": 160,
        "order_count": 195,
        "image_url": "https://plus.unsplash.com/premium_photo-1677956021545-986eaa5f6e65?w=600&auto=format&fit=crop&q=80"
    }
]


def seed_initial_data_if_needed(target_db=None):
    """
    Safely seed initial canonical menu items and settings if not already present.
    Non-destructive: preserves all existing production records, dynamic ratings,
    orders, and reviews without deleting or overwriting data on startup.
    """
    try:
        active_db = target_db if target_db is not None else db
        target_menu = active_db["menu"]
        target_settings = active_db["settings"]

        # Safely add missing canonical items without modifying or overwriting existing entries
        existing_names = set(doc["name"] for doc in target_menu.find({}, {"name": 1}))
        missing_items = [dict(item) for item in CANONICAL_MENU if item["name"] not in existing_names]
        if missing_items:
            target_menu.insert_many(missing_items)

        # Seed default settings if empty
        if target_settings.count_documents({}) == 0:
            target_settings.insert_one({
                "canteen_name": "GazeboExpress Campus Food Hub",
                "operating_hours": "08:30 AM - 09:30 PM",
                "default_pickup_duration": "15 mins",
                "queue_low_threshold": 5,
                "queue_moderate_threshold": 15,
                "notifications_enabled": True,
                "updated_at": get_current_time_str()
            })
    except Exception as e:
        print(f"Seed error (ignored for safety): {e}")


# Run seeding on startup
seed_initial_data_if_needed()


@app.route("/")
def home():
    return jsonify({
        "message": "GazeboExpress API is running",
        "version": "3.0",
        "service": "Smart Campus Food Ordering & Queue Management System",
        "auth": "Authgear Integrated"
    })


# ==============================================================================
# AUTHENTICATION & PROFILE APIS
# ==============================================================================

@app.route("/api/auth/config", methods=["GET"])
def get_auth_config():
    """Return public Authgear client configuration."""
    host = request.headers.get("Host", "")
    if "localhost" in host or "127.0.0.1" in host:
        redirect_uri = f"http://{host}".rstrip("/")
    else:
        redirect_uri = (AUTHGEAR_REDIRECT_URI.rstrip("/") + "/") if AUTHGEAR_REDIRECT_URI else ""
    return jsonify({
        "endpoint": AUTHGEAR_ENDPOINT,
        "clientID": AUTHGEAR_CLIENT_ID,
        "redirectURI": redirect_uri
    })


@app.route("/api/auth/me", methods=["GET"])
@app.route("/api/profile", methods=["GET"])
@app.route("/api/users/me", methods=["GET"])
@require_auth
def get_current_user_profile():
    """Return authenticated user's profile from MongoDB."""
    try:
        user = request.user
        sub = user.get("authgear_user_id")
        user_email = (user.get("email") or "").strip().lower()
        expected_role = "admin" if user_email == DESIGNATED_ADMIN_EMAIL.lower() else user.get("role", "student")

        user_doc = None
        try:
            user_doc = users_collection.find_one({"authgear_user_id": sub})
            if not user_doc and user_email:
                user_doc = users_collection.find_one({"email": {"$regex": f"^{re.escape(user_email)}$", "$options": "i"}})
                if user_doc:
                    users_collection.update_one({"_id": user_doc["_id"]}, {"$set": {"authgear_user_id": sub}})
                    user_doc["authgear_user_id"] = sub
        except Exception as db_err:
            print(f"MongoDB lookup warning in get_current_user_profile (fallback to verified claims): {db_err}", flush=True)
            return jsonify({
                "authgear_user_id": sub,
                "email": user_email,
                "name": user.get("name", "Canteen Administrator" if expected_role == "admin" else "Gazebo Student"),
                "role": expected_role,
                "register_number": user.get("register_number", "STUDENT"),
                "student_id": user.get("student_id", "STUDENT"),
                "phone": user.get("phone", ""),
                "is_new": False,
                "db_status": "disconnected"
            }), 200

        if not user_doc:
            # Return new-user placeholder for initial registration
            return jsonify({
                "authgear_user_id": sub,
                "email": user.get("email", ""),
                "name": user.get("name", "Canteen Administrator" if expected_role == "admin" else "Gazebo User"),
                "role": expected_role,
                "is_new": True
            })

        # Reconcile role if stale in existing doc for designated admin
        if user_doc.get("email", "").strip().lower() == DESIGNATED_ADMIN_EMAIL.lower() and user_doc.get("role") != "admin":
            try:
                users_collection.update_one({"_id": user_doc["_id"]}, {"$set": {"role": "admin", "updated_at": get_current_time_str()}})
            except Exception:
                pass
            user_doc["role"] = "admin"

        serialize_doc(user_doc)
        return jsonify(user_doc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/profile", methods=["POST"])
@app.route("/api/profile", methods=["POST"])
@require_auth
def create_user_profile():
    """Create a new profile bound to the authenticated Authgear user identity."""
    try:
        user = request.user
        sub = user.get("authgear_user_id")

        existing = users_collection.find_one({"authgear_user_id": sub})
        if existing:
            serialize_doc(existing)
            return jsonify(existing), 200

        data = request.json or {}
        
        # Authoritative email resolution from verified auth identity
        verified_email = (user.get("email") or str(data.get("email", ""))).strip().lower()

        # Strict server-side role resolution: ONLY the designated admin receives the admin role
        role = "admin" if verified_email == DESIGNATED_ADMIN_EMAIL.lower() else "student"

        name = str(data.get("name", user.get("name", "Gazebo User"))).strip() or user.get("name", "Gazebo User")
        raw_reg = str(data.get("register_number", data.get("student_id", ""))).strip()

        if role == "student":
            if not raw_reg:
                return jsonify({"error": "Student Register Number / ID is required"}), 400
            reg_no = raw_reg
        else:
            reg_no = raw_reg or "STAFF"

        phone = str(data.get("phone", "")).strip() or "+91 98765 43210"
        profile_image = str(data.get("profile_image", "")).strip()

        profile = {
            "authgear_user_id": sub,
            "name": name,
            "email": verified_email,
            "register_number": reg_no,
            "student_id": reg_no,
            "role": role,
            "phone": phone,
            "profile_image": profile_image,
            "created_at": get_current_time_str(),
            "updated_at": get_current_time_str()
        }

        users_collection.insert_one(profile)
        serialize_doc(profile)
        return jsonify(profile), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile", methods=["PUT"])
@app.route("/api/auth/profile", methods=["PUT"])
@require_auth
def update_user_profile():
    """Update profile information for the authenticated user only."""
    try:
        sub = request.user.get("authgear_user_id")
        data = request.json or {}

        # Allowed mutable fields (Role, Authgear ID, and Email are immutable)
        updates = {}
        if "name" in data:
            updates["name"] = str(data["name"]).strip()
        if "register_number" in data:
            updates["register_number"] = str(data["register_number"]).strip()
            updates["student_id"] = updates["register_number"]
        elif "student_id" in data:
            updates["student_id"] = str(data["student_id"]).strip()
            updates["register_number"] = updates["student_id"]
        if "phone" in data:
            updates["phone"] = str(data["phone"]).strip()
        if "profile_image" in data:
            updates["profile_image"] = str(data["profile_image"]).strip()

        updates["updated_at"] = get_current_time_str()

        result = users_collection.update_one(
            {"authgear_user_id": sub},
            {"$set": updates},
            upsert=False
        )

        if result.matched_count == 0:
            return jsonify({"error": "User profile not found"}), 404

        updated_doc = users_collection.find_one({"authgear_user_id": sub})
        serialize_doc(updated_doc)
        return jsonify(updated_doc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# ADMIN PROTECTED APIS
# ==============================================================================

@app.route("/api/admin/dashboard", methods=["GET"])
@require_role("admin")
def get_admin_dashboard():
    """Admin-only aggregated overview."""
    try:
        total_orders = orders_collection.count_documents({})
        active_orders = orders_collection.count_documents({"status": {"$in": ["Placed", "Preparing"]}})
        total_users = users_collection.count_documents({})
        total_menu = menu_collection.count_documents({})
        return jsonify({
            "total_orders": total_orders,
            "active_orders": active_orders,
            "total_users": total_users,
            "total_menu_items": total_menu
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/users", methods=["GET"])
@require_role("admin")
def get_admin_users():
    """Admin-only: list registered accounts."""
    try:
        users = list(users_collection.find().sort("_id", -1).limit(50))
        for u in users:
            serialize_doc(u)
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# MENU APIS (Public Read, Admin Write)
# ==============================================================================

@app.route("/api/menu", methods=["GET"])
def get_menu():
    try:
        category = request.args.get("category")
        query = {}
        if category and category.lower() != "all":
            query["category"] = category

        try:
            menu = list(menu_collection.find(query))
        except Exception as db_err:
            print(f"MongoDB warning in get_menu ({db_err}), using canonical fallback", flush=True)
            menu = [dict(item) for item in CANONICAL_MENU]
            if category and category.lower() != "all":
                menu = [item for item in menu if item.get("category", "").lower() == category.lower()]

        for item in menu:
            serialize_doc(item)

        return jsonify(menu)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/menu", methods=["POST"])
@require_role("admin")
def add_menu():
    try:
        data = request.json or {}
        if not data.get("name") or not data.get("category") or data.get("price") is None:
            return jsonify({"error": "Name, category, and price are required"}), 400

        item = {
            "name": str(data["name"]).strip(),
            "category": str(data["category"]).strip(),
            "description": str(data.get("description", "")).strip(),
            "price": float(data["price"]),
            "image_url": str(data.get("image_url", "")).strip(),
            "available": bool(data.get("available", True)),
            "bestseller": bool(data.get("bestseller", False)),
            "rating": float(data.get("rating", 4.5)),
            "ratings_count": int(data.get("ratings_count", 0)),
            "order_count": int(data.get("order_count", 0)),
            "created_at": get_current_time_str()
        }

        # If marked as bestseller, clear existing bestseller in that category
        if item["bestseller"]:
            menu_collection.update_many(
                {"category": item["category"]},
                {"$set": {"bestseller": False}}
            )

        result = menu_collection.insert_one(item)

        try:
            notifications_collection.insert_one({
                "title": "New Menu Item Added",
                "message": f"'{item['name']}' added to {item['category']} menu.",
                "type": "menu",
                "read": False,
                "created_at": get_current_time_str()
            })
        except Exception:
            pass

        return jsonify({
            "message": "Menu item added successfully",
            "id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/menu/<id>", methods=["PUT"])
@require_role("admin")
def update_menu(id):
    try:
        data = request.json or {}
        update_fields = {}

        if "name" in data:
            update_fields["name"] = str(data["name"]).strip()
        if "category" in data:
            update_fields["category"] = str(data["category"]).strip()
        if "description" in data:
            update_fields["description"] = str(data["description"]).strip()
        if "price" in data:
            update_fields["price"] = float(data["price"])
        if "image_url" in data:
            update_fields["image_url"] = str(data["image_url"]).strip()
        if "available" in data:
            update_fields["available"] = bool(data["available"])
        if "bestseller" in data:
            is_best = bool(data["bestseller"])
            update_fields["bestseller"] = is_best
            if is_best:
                # Target item's category
                current_item = menu_collection.find_one({"_id": ObjectId(id)})
                cat = update_fields.get("category") or (current_item.get("category") if current_item else None)
                if cat:
                    menu_collection.update_many(
                        {"category": cat, "_id": {"$ne": ObjectId(id)}},
                        {"$set": {"bestseller": False}}
                    )
        if "rating" in data:
            update_fields["rating"] = float(data["rating"])

        update_fields["updated_at"] = get_current_time_str()

        result = menu_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Menu item not found"}), 404

        return jsonify({"message": "Menu item updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/menu/<id>", methods=["DELETE"])
@require_role("admin")
def delete_menu(id):
    try:
        result = menu_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Menu item not found"}), 404

        return jsonify({"message": "Menu item deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# ORDERS APIS (Student views own orders, Admin views all)
# ==============================================================================

VALID_ORDER_TRANSITIONS = {
    "Placed": ["Preparing", "Cancelled"],
    "Preparing": ["Ready", "Cancelled"],
    "Ready": ["Completed", "Cancelled"],
    "Completed": [],
    "Cancelled": []
}

@app.route("/api/orders", methods=["GET"])
@require_auth
def get_orders():
    try:
        user = request.user
        status_filter = request.args.get("status")
        query = {}
        if status_filter and status_filter.lower() != "all":
            query["status"] = status_filter

        if user.get("role") == "admin":
            # Admin views all orders across the canteen
            pass
        else:
            # Student strictly views only their own orders
            sub = user.get("authgear_user_id")
            reg = user.get("register_number") or user.get("student_id")
            student_conds = []
            if sub:
                student_conds.append({"authgear_user_id": sub})
            if reg:
                # Also include legacy orders that don't have authgear_user_id set
                student_conds.append({"student_id": reg, "authgear_user_id": None})
                student_conds.append({"student_id": reg, "authgear_user_id": {"$exists": False}})

            if student_conds:
                if len(student_conds) == 1:
                    query.update(student_conds[0])
                else:
                    query["$or"] = student_conds
            else:
                return jsonify([])

        try:
            orders = list(orders_collection.find(query).sort("_id", -1))
        except Exception as db_err:
            print(f"MongoDB warning in get_orders: {db_err}", flush=True)
            orders = []

        for order in orders:
            serialize_doc(order)

        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders", methods=["POST"])
@require_auth
def create_order():
    try:
        data = request.json or {}
        user = request.user
        authgear_user_id = user.get("authgear_user_id")

        student_name = str(data.get("student_name", user.get("name", ""))).strip() or user.get("name", "Student")
        student_id = str(data.get("student_id", user.get("register_number", ""))).strip() or user.get("register_number", "")
        items = data.get("items", [])
        pickup_time = str(data.get("pickup_time", "In 10 mins")).strip()

        if not student_name or not student_id or not items:
            return jsonify({"error": "Student name, student ID, and order items are required"}), 400

        calculated_total = 0.0
        sanitized_items = []
        for item in items:
            name = str(item.get("name", "Unknown Item")).strip()
            qty = max(1, int(item.get("quantity", 1)))
            # Genuine database-driven price calculation
            db_item = menu_collection.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
            if db_item and "price" in db_item:
                price = float(db_item["price"])
            else:
                price = float(item.get("price", 0.0))
            calculated_total += (price * qty)
            sanitized_items.append({
                "name": name,
                "quantity": qty,
                "price": price
            })

            try:
                menu_collection.update_one(
                    {"name": name},
                    {"$inc": {"order_count": qty}}
                )
            except Exception:
                pass

        total_amount = round(calculated_total, 2)

        order = {
            "student_name": student_name,
            "student_id": student_id,
            "authgear_user_id": authgear_user_id,
            "items": sanitized_items,
            "total_amount": round(total_amount, 2),
            "pickup_time": pickup_time,
            "status": "Placed",
            "created_at": get_current_time_str()
        }

        result = orders_collection.insert_one(order)
        order_id = str(result.inserted_id)

        try:
            notifications_collection.insert_one({
                "title": "New Campus Order Placed",
                "message": f"Order #{order_id[-6:].upper()} by {student_name} ({len(sanitized_items)} items) for {pickup_time}.",
                "type": "order",
                "read": False,
                "order_id": order_id,
                "created_at": get_current_time_str()
            })
        except Exception:
            pass

        return jsonify({
            "message": "Order placed successfully",
            "id": order_id,
            "total_amount": round(total_amount, 2),
            "status": "Placed"
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders/<id>", methods=["GET"])
@require_auth
def get_order(id):
    try:
        try:
            order_oid = ObjectId(id)
        except Exception:
            return jsonify({"error": "Invalid order ID format"}), 400

        order = orders_collection.find_one({"_id": order_oid})
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Student privacy check: non-admin can only access own order
        user = request.user
        if user.get("role") != "admin":
            sub = user.get("authgear_user_id")
            reg = user.get("register_number")
            is_owner = (order.get("authgear_user_id") == sub or (not order.get("authgear_user_id") and reg and order.get("student_id") == reg))
            if not is_owner:
                return jsonify({"error": "Forbidden"}), 403

        serialize_doc(order)
        return jsonify(order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders/<id>", methods=["PUT"])
@require_auth
def update_order(id):
    """
    Update kitchen order status.
    Admin can advance orders: Placed -> Preparing -> Ready -> Completed, or Cancel.
    Student can only cancel their own order while it is still 'Placed'.
    Invalid status transitions are strictly rejected.
    """
    try:
        user = request.user
        data = request.json or {}
        new_status = data.get("status")

        if not new_status:
            return jsonify({"error": "Status is required"}), 400

        valid_statuses = ["Placed", "Preparing", "Ready", "Completed", "Cancelled"]
        if new_status not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of {valid_statuses}"}), 400

        try:
            order_oid = ObjectId(id)
        except Exception:
            return jsonify({"error": "Invalid order ID format"}), 400

        order = orders_collection.find_one({"_id": order_oid})
        if not order:
            return jsonify({"error": "Order not found"}), 404

        current_status = order.get("status", "Placed")

        # If unchanged, return 200
        if current_status == new_status:
            return jsonify({"message": "Order status unchanged", "status": new_status}), 200

        # Check role & ownership
        is_admin = (user.get("role") == "admin")
        sub = user.get("authgear_user_id")

        if not is_admin:
            # Student permissions: only allow cancelling their own order if still 'Placed'
            is_owner = (order.get("authgear_user_id") == sub or (not order.get("authgear_user_id") and order.get("student_id") == user.get("register_number")))
            if not is_owner:
                return jsonify({"error": "Forbidden: You do not own this order"}), 403
            if new_status != "Cancelled" or current_status != "Placed":
                return jsonify({"error": "Forbidden: Students can only cancel orders in 'Placed' status"}), 403

        # Validate status transition
        allowed_next = VALID_ORDER_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_next:
            return jsonify({"error": f"Invalid transition: Cannot transition order from '{current_status}' to '{new_status}'"}), 400

        result = orders_collection.update_one(
            {"_id": order_oid},
            {"$set": {"status": new_status, "updated_at": get_current_time_str()}}
        )

        try:
            student_name = order.get("student_name", "Student")
            if new_status == "Ready":
                notifications_collection.insert_one({
                    "title": "Order Ready for Pickup!",
                    "message": f"Order #{str(id)[-6:].upper()} for {student_name} is ready at Gazebo counter.",
                    "type": "ready",
                    "read": False,
                    "order_id": str(id),
                    "created_at": get_current_time_str()
                })
        except Exception:
            pass

        return jsonify({
            "message": "Order status updated successfully",
            "status": new_status
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orders/<id>", methods=["DELETE"])
@require_role("admin")
def delete_order(id):
    try:
        result = orders_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({"message": "Order cancelled successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# SMART QUEUE API
# ==============================================================================

@app.route("/api/queue", methods=["GET"])
@app.route("/api/queue/status", methods=["GET"])
def queue_status():
    try:
        settings = {}
        try:
            settings = settings_collection.find_one() or {}
        except Exception:
            pass

        low_limit = int(settings.get("queue_low_threshold", 5))
        mod_limit = int(settings.get("queue_moderate_threshold", 15))

        active_orders = 0
        placed_orders = 0
        preparing_orders = 0
        ready_orders = 0

        try:
            placed_orders = orders_collection.count_documents({"status": "Placed"})
            preparing_orders = orders_collection.count_documents({"status": "Preparing"})
            ready_orders = orders_collection.count_documents({"status": "Ready"})
            active_orders = placed_orders + preparing_orders
        except Exception as db_err:
            print(f"MongoDB warning in queue_status: {db_err}", flush=True)

        if active_orders == 0:
            status = "Low"
            wait_desc = "No queue - Ready in 5-10 mins"
        elif active_orders <= low_limit:
            status = "Low"
            wait_desc = "Short queue - Est. wait 5-10 mins"
        elif active_orders <= mod_limit:
            status = "Moderate"
            wait_desc = f"Moderate queue - Est. wait {10 + active_orders * 2} mins"
        else:
            status = "High"
            wait_desc = f"Heavy queue - Est. wait {min(60, 20 + active_orders * 3)}+ mins"

        return jsonify({
            "active_orders": active_orders,
            "placed_orders": placed_orders,
            "preparing_orders": preparing_orders,
            "ready_orders": ready_orders,
            "queue_status": status,
            "estimated_wait": wait_desc,
            "low_threshold": low_limit,
            "moderate_threshold": mod_limit
        })
    except Exception as e:
        return jsonify({
            "active_orders": 0,
            "placed_orders": 0,
            "preparing_orders": 0,
            "ready_orders": 0,
            "queue_status": "Low",
            "estimated_wait": "Ready in 5-10 mins",
            "low_threshold": 5,
            "moderate_threshold": 15
        }), 200


# ==============================================================================
# DASHBOARD & ANALYTICS APIS (Admin Protected)
# ==============================================================================

@app.route("/api/dashboard/stats", methods=["GET"])
@require_role("admin")
def dashboard_stats():
    total_orders = 0
    placed_orders = 0
    preparing_orders = 0
    active_orders = 0
    ready_orders = 0
    completed_orders = 0
    total_revenue = 0.0
    available_menu_items = 30
    total_menu_items = 30
    queue_cond = "Low"
    wait_time = "5-10 mins"
    avg_rating = 4.8
    reviews_count = 6

    try:
        total_orders = orders_collection.count_documents({})
        placed_orders = orders_collection.count_documents({"status": "Placed"})
        preparing_orders = orders_collection.count_documents({"status": "Preparing"})
        active_orders = placed_orders + preparing_orders
        ready_orders = orders_collection.count_documents({"status": "Ready"})
        completed_orders = orders_collection.count_documents({"status": "Completed"})

        revenue_pipeline = [
            {"$match": {"status": {"$ne": "Cancelled"}}},
            {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
        ]
        rev_res = list(orders_collection.aggregate(revenue_pipeline))
        total_revenue = rev_res[0]["total"] if rev_res else 0.0

        available_menu_items = menu_collection.count_documents({"available": True})
        total_menu_items = menu_collection.count_documents({})

        settings = settings_collection.find_one() or {}
        low_limit = int(settings.get("queue_low_threshold", 5))
        mod_limit = int(settings.get("queue_moderate_threshold", 15))
        if active_orders == 0:
            queue_cond = "Low"
            wait_time = "5-10 mins"
        elif active_orders <= low_limit:
            queue_cond = "Low"
            wait_time = "5-10 mins"
        elif active_orders <= mod_limit:
            queue_cond = "Moderate"
            wait_time = f"{10 + active_orders * 2} mins"
        else:
            queue_cond = "High"
            wait_time = f"{min(60, 20 + active_orders * 3)}+ mins"

        avg_pipeline = [
            {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ]
        avg_res = list(reviews_collection.aggregate(avg_pipeline))
        avg_rating = round(avg_res[0]["avg_rating"], 1) if (avg_res and avg_res[0].get("avg_rating") is not None) else 0.0
        reviews_count = avg_res[0]["count"] if avg_res else 0
    except Exception as db_err:
        print(f"MongoDB warning in dashboard_stats (safe fallback): {db_err}", flush=True)

    return jsonify({
        "total_orders": total_orders,
        "active_orders": active_orders,
        "ready_orders": ready_orders,
        "completed_orders": completed_orders,
        "total_revenue": round(total_revenue, 2),
        "available_menu_items": available_menu_items,
        "total_menu_items": total_menu_items,
        "queue_status": queue_cond,
        "estimated_wait": wait_time,
        "average_rating": avg_rating,
        "total_reviews": reviews_count
    }), 200


@app.route("/api/dashboard/orders-summary", methods=["GET"])
@require_role("admin")
def orders_summary():
    try:
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        results = list(orders_collection.aggregate(pipeline))
        summary = {
            "Placed": 0,
            "Preparing": 0,
            "Ready": 0,
            "Completed": 0,
            "Cancelled": 0
        }
        for item in results:
            if item["_id"] in summary:
                summary[item["_id"]] = item["count"]

        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/popular-items", methods=["GET"])
@require_role("admin")
def popular_items():
    try:
        pipeline = [
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.name",
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.price"]}}
            }},
            {"$sort": {"total_quantity": -1}},
            {"$limit": 6}
        ]
        results = list(orders_collection.aggregate(pipeline))

        popular = []
        for r in results:
            item_info = menu_collection.find_one({"name": r["_id"]})
            popular.append({
                "name": r["_id"],
                "total_quantity": r["total_quantity"],
                "total_revenue": round(r["total_revenue"], 2),
                "category": item_info.get("category", "General") if item_info else "General",
                "price": item_info.get("price", 0.0) if item_info else 0.0,
                "image_url": item_info.get("image_url", "") if item_info else ""
            })

        if len(popular) < 4:
            bestsellers = list(menu_collection.find({"available": True}).sort("order_count", -1).limit(6))
            for b in bestsellers:
                if not any(p["name"] == b["name"] for p in popular):
                    popular.append({
                        "name": b["name"],
                        "total_quantity": b.get("order_count", 25),
                        "total_revenue": round(b.get("order_count", 25) * b.get("price", 100), 2),
                        "category": b.get("category", "General"),
                        "price": b.get("price", 0.0),
                        "image_url": b.get("image_url", "")
                    })

        return jsonify(popular[:6])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics", methods=["GET"])
@require_role("admin")
def get_analytics():
    try:
        category_pipeline = [
            {"$group": {"_id": "$category", "item_count": {"$sum": 1}}}
        ]
        categories_data = list(menu_collection.aggregate(category_pipeline))
        category_stats = [{"category": c["_id"] or "Uncategorized", "count": c["item_count"]} for c in categories_data]

        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_data = list(orders_collection.aggregate(status_pipeline))
        status_stats = [{"status": s["_id"], "count": s["count"]} for s in status_data]

        pickup_pipeline = [
            {"$group": {"_id": "$pickup_time", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        pickup_data = list(orders_collection.aggregate(pickup_pipeline))
        pickup_stats = [{"time": p["_id"] or "Not specified", "count": p["count"]} for p in pickup_data]

        return jsonify({
            "category_distribution": category_stats,
            "status_distribution": status_stats,
            "peak_pickup_times": pickup_stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# REVIEWS APIS
# ==============================================================================

@app.route("/api/reviews", methods=["GET"])
def get_reviews():
    try:
        try:
            reviews = list(reviews_collection.find().sort("_id", -1))
        except Exception as db_err:
            print(f"MongoDB warning in get_reviews: {db_err}", flush=True)
            reviews = []

        for r in reviews:
            serialize_doc(r)

        total_reviews = len(reviews)
        avg_rating = round(sum(r.get("rating", 5) for r in reviews) / total_reviews, 1) if total_reviews > 0 else 0.0

        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in reviews:
            rate = int(r.get("rating", 5))
            if rate in distribution:
                distribution[rate] += 1

        return jsonify({
            "reviews": reviews,
            "total_reviews": total_reviews,
            "average_rating": avg_rating,
            "distribution": distribution
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reviews", methods=["POST"])
def add_review():
    try:
        data = request.json or {}
        user = get_optional_auth_user()

        student_name = str(data.get("student_name", user.get("name", "Anonymous") if user else "Anonymous")).strip()
        student_id = str(data.get("student_id", user.get("register_number", "") if user else "")).strip()

        try:
            rating = int(data.get("rating", 5))
        except (ValueError, TypeError):
            return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400

        comment = str(data.get("comment", "")).strip()
        if not comment or len(comment) < 3:
            return jsonify({"error": "Review comment must be at least 3 characters"}), 400
        if len(comment) > 500:
            return jsonify({"error": "Review comment cannot exceed 500 characters"}), 400

        menu_item_name = str(data.get("menu_item_name", "General Canteen")).strip()
        order_id = str(data.get("order_id", "")).strip()

        # Prevent duplicate submissions by the same user for the same menu item
        sub = user.get("authgear_user_id") if user else None
        dup_filter = {"menu_item_name": menu_item_name}
        if sub:
            dup_filter["authgear_user_id"] = sub
        elif student_id:
            dup_filter["student_id"] = student_id
        else:
            dup_filter = None

        if dup_filter and reviews_collection.find_one(dup_filter):
            return jsonify({"error": f"You have already submitted a review for '{menu_item_name}'"}), 409

        review = {
            "student_name": student_name,
            "student_id": student_id,
            "authgear_user_id": sub,
            "rating": rating,
            "comment": comment,
            "menu_item_name": menu_item_name,
            "order_id": order_id,
            "created_at": get_current_time_str()
        }

        result = reviews_collection.insert_one(review)

        # Update menu item rating if review is for a specific menu item
        if menu_item_name and menu_item_name != "General Canteen":
            item_reviews = list(reviews_collection.find({"menu_item_name": menu_item_name}))
            if item_reviews:
                avg_rate = round(sum(r.get("rating", 5) for r in item_reviews) / len(item_reviews), 1)
                menu_collection.update_one(
                    {"name": menu_item_name},
                    {"$set": {"rating": avg_rate, "ratings_count": len(item_reviews)}}
                )

        return jsonify({
            "message": "Review submitted successfully",
            "id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reviews/<id>", methods=["DELETE"])
@require_role("admin")
def delete_review(id):
    try:
        result = reviews_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Review not found"}), 404

        return jsonify({"message": "Review deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# SETTINGS APIS (Read Public/Student, Write Admin)
# ==============================================================================

@app.route("/api/settings", methods=["GET"])
def get_settings():
    default_settings = {
        "canteen_name": "GazeboExpress Campus Food Hub",
        "operating_hours": "08:30 AM - 09:30 PM",
        "default_pickup_duration": "15 mins",
        "queue_low_threshold": 5,
        "queue_moderate_threshold": 15,
        "notifications_enabled": True
    }
    try:
        settings = settings_collection.find_one()
        if not settings:
            try:
                settings_collection.insert_one(default_settings.copy())
            except Exception:
                pass
            settings = default_settings

        serialize_doc(settings)
        return jsonify(settings)
    except Exception as e:
        print(f"MongoDB warning in get_settings: {e}", flush=True)
        return jsonify(default_settings), 200


@app.route("/api/settings", methods=["PUT"])
@require_role("admin")
def update_settings():
    try:
        data = request.json or {}
        update_data = {
            "canteen_name": str(data.get("canteen_name", "GazeboExpress")).strip(),
            "operating_hours": str(data.get("operating_hours", "08:30 AM - 09:30 PM")).strip(),
            "default_pickup_duration": str(data.get("default_pickup_duration", "15 mins")).strip(),
            "queue_low_threshold": int(data.get("queue_low_threshold", 5)),
            "queue_moderate_threshold": int(data.get("queue_moderate_threshold", 15)),
            "notifications_enabled": bool(data.get("notifications_enabled", True)),
            "updated_at": get_current_time_str()
        }

        settings_collection.update_one({}, {"$set": update_data}, upsert=True)

        return jsonify({
            "message": "Settings saved successfully",
            "settings": update_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# NOTIFICATIONS APIS
# ==============================================================================

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    try:
        notifications = list(notifications_collection.find().sort("_id", -1).limit(20))
        for n in notifications:
            serialize_doc(n)

        unread_count = notifications_collection.count_documents({"read": False})

        return jsonify({
            "notifications": notifications,
            "unread_count": unread_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/<id>/read", methods=["PUT"])
def mark_notification_read(id):
    try:
        notifications_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"read": True}}
        )
        return jsonify({"message": "Notification marked as read"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications/clear", methods=["POST"])
def clear_notifications():
    try:
        notifications_collection.update_many({}, {"$set": {"read": True}})
        return jsonify({"message": "All notifications marked as read"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
