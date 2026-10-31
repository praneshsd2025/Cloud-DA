"""
GazeboExpress Menu Migration and Seeding Script
Idempotently cleans up obsolete categories (Starters, Spicy Arrabbiata Pasta)
and updates all menu items with correct categories, descriptions, images,
and ensures exactly one bestseller per category.
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise ValueError("MONGODB_URI not found in environment")

client = MongoClient(mongo_uri)
db = client["gazeboexpress"]
menu_collection = db["menu"]

MENU_ITEMS = [
    # ==========================================
    # SNACKS (6 items, 1 bestseller)
    # ==========================================
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

    # ==========================================
    # BURGERS (6 items, 1 bestseller)
    # ==========================================
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

    # ==========================================
    # SANDWICHES (6 items, 1 bestseller)
    # ==========================================
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

    # ==========================================
    # PASTA (2 items, 1 bestseller)
    # ==========================================
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

    # ==========================================
    # BEVERAGES (6 items, 1 bestseller)
    # ==========================================
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

    # ==========================================
    # DESSERTS (4 items, 1 bestseller)
    # ==========================================
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


def run_migration():
    print("Starting GazeboExpress menu migration...")

    # 1. Remove obsolete items and old categories
    obsolete_filter = {
        "$or": [
            {"category": "Starters"},
            {"name": {"$in": ["Spicy Arrabbiata Pasta", "Creamy Alfredo Penne Pasta", "Fresh Mint Lime Mojito"]}}
        ]
    }
    del_res = menu_collection.delete_many(obsolete_filter)
    print(f"Removed {del_res.deleted_count} obsolete item(s).")

    # 2. Upsert each canonical item
    upserted_count = 0
    for item in MENU_ITEMS:
        res = menu_collection.update_one(
            {"name": item["name"]},
            {"$set": item},
            upsert=True
        )
        upserted_count += 1
    print(f"Upserted {upserted_count} canonical menu items.")

    # 3. Validation
    expected_categories = ["Snacks", "Burgers", "Sandwiches", "Pasta", "Beverages", "Desserts"]
    print("\n--- Menu Validation ---")
    total_bestsellers = 0
    for cat in expected_categories:
        items = list(menu_collection.find({"category": cat}))
        bestsellers = [i["name"] for i in items if i.get("bestseller")]
        total_bestsellers += len(bestsellers)
        print(f"Category: {cat:12} | Count: {len(items):2} | Bestseller: {bestsellers}")
        assert len(bestsellers) == 1, f"Expected exactly 1 bestseller in {cat}, got {bestsellers}"

    starters_count = menu_collection.count_documents({"category": "Starters"})
    assert starters_count == 0, f"Expected 0 items in Starters, got {starters_count}"

    arrabbiata_count = menu_collection.count_documents({"name": "Spicy Arrabbiata Pasta"})
    assert arrabbiata_count == 0, "Spicy Arrabbiata Pasta should not exist"

    print("\nMigration and validation completed successfully!")


if __name__ == "__main__":
    run_migration()
