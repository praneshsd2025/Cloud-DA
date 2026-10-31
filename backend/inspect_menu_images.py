import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

uri = os.getenv("MONGODB_URI")
if not uri:
    raise RuntimeError("MONGODB_URI is not configured.")

client = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = client[os.getenv("MONGODB_DB_NAME", "gazeboexpress")]

names = [
    "Veg Puff",
    "Chicken Puff",
    "Peri Peri French Fries",
    "Veg Sandwich",
    "Crispy Paneer Grilled Sandwich",
    "Chicken Club Sandwich",
    "Veg Cheese Sandwich",
    "Tandoori Paneer Sandwich",
    "Corn & Cheese Sandwich",
    "BBQ Chicken Sandwich",
    "Gulab Jamun",
]

try:
    client.admin.command("ping")
    print("Database:", db.name)
    print("\nAffected menu records (read-only):")

    for item in db["menu"].find(
        {"name": {"$in": names}},
        {"name": 1, "image_url": 1, "category": 1}
    ).sort("name", 1):
        print(f"\nName: {item.get('name')}")
        print(f"Category: {item.get('category')}")
        print(f"Image URL: {item.get('image_url', '(missing)')}")

finally:
    client.close()
