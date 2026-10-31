import os
import sys
import unittest
import json

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure tests run strictly in an isolated test database, never touching production
os.environ["MONGODB_DB_NAME"] = "gazeboexpress_test"

from app import (
    app,
    db,
    menu_collection,
    users_collection,
    orders_collection,
    set_database,
    seed_initial_data_if_needed
)


REQUIRED_TEST_DB = "gazeboexpress_test"


class GazeboExpressBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        # 1. Explicitly select and switch to isolated test database
        set_database(REQUIRED_TEST_DB)

        # 2. Enforce strict isolation guard: Require exact database name 'gazeboexpress_test'
        if app_module.db.name != REQUIRED_TEST_DB:
            raise RuntimeError(
                f"CRITICAL SAFETY ERROR: Test suite requires exact database '{REQUIRED_TEST_DB}', but found '{app_module.db.name}'! Rejecting all other database names."
            )

        seed_initial_data_if_needed(target_db=app_module.db)

        cls.client = app.test_client()
        cls.student_token = "test_token_student_pranesh"
        cls.admin_token = "test_token_admin_supermanager"

        # 3. Clean any existing leftover test documents in isolated test database
        cls._cleanup_isolated_test_data()

    @classmethod
    def _cleanup_isolated_test_data(cls):
        import app as app_module
        # Guard: Require exact database name 'gazeboexpress_test' before any destructive test operation
        if app_module.db.name != REQUIRED_TEST_DB:
            raise RuntimeError(
                f"CRITICAL SAFETY ERROR: Destructive test cleanup rejected! Exact database '{REQUIRED_TEST_DB}' required, but found '{app_module.db.name}'."
            )
        app_module.orders_collection.delete_many({})
        app_module.reviews_collection.delete_many({})
        app_module.notifications_collection.delete_many({})
        app_module.users_collection.delete_many({})

    def setUp(self):
        import app as app_module
        # Guard: Require exact database name 'gazeboexpress_test' before test setup cleanup
        if app_module.db.name != REQUIRED_TEST_DB:
            raise RuntimeError(
                f"CRITICAL SAFETY ERROR: Test setup rejected! Exact database '{REQUIRED_TEST_DB}' required, but found '{app_module.db.name}'."
            )

        # Clean state for test cases sensitive to prior test submissions
        app_module.orders_collection.delete_many({"authgear_user_id": "test_student_newfreshman"})
        app_module.reviews_collection.delete_many({"student_id": "reviewer99"})
        app_module.reviews_collection.delete_many({"student_name": {"$in": ["reviewer99", "Student Reviewer99"]}})
        app_module.reviews_collection.delete_many({"authgear_user_id": {"$regex": "reviewer99"}})

    def tearDown(self):
        import app as app_module
        # Guard: Require exact database name 'gazeboexpress_test' before test teardown cleanup
        if app_module.db.name != REQUIRED_TEST_DB:
            raise RuntimeError(
                f"CRITICAL SAFETY ERROR: Test teardown rejected! Exact database '{REQUIRED_TEST_DB}' required, but found '{app_module.db.name}'."
            )
        # Clean transient test orders and reviews after test execution so each test remains isolated
        app_module.orders_collection.delete_many({"authgear_user_id": "test_student_newfreshman"})
        app_module.reviews_collection.delete_many({"student_id": "reviewer99"})
        app_module.reviews_collection.delete_many({"student_name": {"$in": ["reviewer99", "Student Reviewer99"]}})
        app_module.reviews_collection.delete_many({"authgear_user_id": {"$regex": "reviewer99"}})

    @classmethod
    def tearDownClass(cls):
        # Final cleanup strictly within the isolated test database
        cls._cleanup_isolated_test_data()

    def test_01_auth_config(self):
        res = self.client.get("/api/auth/config")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("endpoint", data)
        self.assertIn("clientID", data)
        self.assertIn("redirectURI", data)

    def test_02_get_profile_authenticated(self):
        # Student profile
        res = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.student_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data.get("role"), "student")
        self.assertIn("name", data)

        # Admin profile
        res_admin = self.client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res_admin.status_code, 200)
        admin_data = json.loads(res_admin.data)
        self.assertEqual(admin_data.get("role"), "admin")

    def test_03_profile_update(self):
        # Update student profile
        res = self.client.put(
            "/api/profile",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={"phone": "+91 99999 88888", "name": "Pranesh S D"}
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data.get("phone"), "+91 99999 88888")

    def test_04_role_authorization_student(self):
        # Student attempting to add a menu item (Admin only) -> must return 403
        res = self.client.post(
            "/api/menu",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={
                "name": "Unauthorized Hack Item",
                "category": "Snacks",
                "price": 10.0
            }
        )
        self.assertEqual(res.status_code, 403)

        # Student attempting to view admin analytics -> must return 403
        res_analytics = self.client.get(
            "/api/analytics",
            headers={"Authorization": f"Bearer {self.student_token}"}
        )
        self.assertEqual(res_analytics.status_code, 403)

    def test_05_role_authorization_admin(self):
        # Admin can access analytics
        res = self.client.get(
            "/api/analytics",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("category_distribution", data)

        # Admin can access dashboard stats
        res_dash = self.client.get(
            "/api/dashboard/stats",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res_dash.status_code, 200)

    def test_06_menu_categories_and_bestsellers(self):
        res = self.client.get("/api/menu")
        self.assertEqual(res.status_code, 200)
        items = json.loads(res.data)
        self.assertGreater(len(items), 20)

        # Validate no Starters
        starter_items = [i for i in items if i.get("category") == "Starters"]
        self.assertEqual(len(starter_items), 0)

        # Validate no Spicy Arrabbiata Pasta
        arrabbiata = [i for i in items if i.get("name") == "Spicy Arrabbiata Pasta"]
        self.assertEqual(len(arrabbiata), 0)

        # Validate exactly 2 pasta items
        pasta_items = [i for i in items if i.get("category") == "Pasta"]
        self.assertEqual(len(pasta_items), 2)

        # Validate exactly 1 bestseller per category
        categories = ["Snacks", "Burgers", "Sandwiches", "Pasta", "Beverages", "Desserts"]
        for cat in categories:
            cat_items = [i for i in items if i.get("category") == cat]
            bestsellers = [i for i in cat_items if i.get("bestseller")]
            self.assertEqual(len(bestsellers), 1, f"Failed for category {cat}: {bestsellers}")

    def test_07_orders_and_queue(self):
        # Student creates an order
        res = self.client.post(
            "/api/orders",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={
                "items": [{"name": "Veg Samosa", "price": 30.0, "quantity": 2}],
                "pickup_time": "In 10 mins"
            }
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn("id", data)

        # Queue status
        res_q = self.client.get("/api/queue")
        self.assertEqual(res_q.status_code, 200)
        q_data = json.loads(res_q.data)
        self.assertIn("queue_status", q_data)

    def test_08_designated_admin_role_security(self):
        # 1. Admin token has baldthief@gmail.com and admin role
        res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assertEqual(res.status_code, 200)
        admin_user = json.loads(res.data)
        self.assertEqual(admin_user.get("role"), "admin")
        self.assertEqual(admin_user.get("email").lower(), "baldthief@gmail.com")

        # 2. Student cannot elevate role via profile update
        res_hack = self.client.put(
            "/api/profile",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={"role": "admin", "name": "Hacked Student"}
        )
        self.assertEqual(res_hack.status_code, 200)
        updated = json.loads(res_hack.data)
        self.assertEqual(updated.get("role"), "student")

    def test_09_student_order_privacy_and_empty_state(self):
        # A new student with zero orders starts with empty list
        new_token = "test_token_student_newfreshman"
        res = self.client.get("/api/orders", headers={"Authorization": f"Bearer {new_token}"})
        self.assertEqual(res.status_code, 200)
        orders = json.loads(res.data)
        self.assertEqual(len(orders), 0)

        # Placing an order as new student
        res_order = self.client.post(
            "/api/orders",
            headers={"Authorization": f"Bearer {new_token}"},
            json={
                "items": [{"name": "Veg Samosa", "price": 30.0, "quantity": 1}],
                "pickup_time": "In 5 mins"
            }
        )
        self.assertEqual(res_order.status_code, 201)
        order_data = json.loads(res_order.data)
        order_id = order_data["id"]

        # Order appears for this student
        res_orders_after = self.client.get("/api/orders", headers={"Authorization": f"Bearer {new_token}"})
        self.assertEqual(res_orders_after.status_code, 200)
        student_orders = json.loads(res_orders_after.data)
        self.assertEqual(len(student_orders), 1)
        self.assertEqual(student_orders[0]["_id"], order_id)

        # But another student (self.student_token) does NOT see this new order
        res_other = self.client.get("/api/orders", headers={"Authorization": f"Bearer {self.student_token}"})
        self.assertEqual(res_other.status_code, 200)
        other_orders = json.loads(res_other.data)
        self.assertFalse(any(o["_id"] == order_id for o in other_orders))

    def test_10_order_status_transitions_and_role_protection(self):
        # Admin places an order
        res_place = self.client.post(
            "/api/orders",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={
                "items": [{"name": "Signature Cold Coffee", "price": 95.0, "quantity": 1}],
                "pickup_time": "In 10 mins"
            }
        )
        self.assertEqual(res_place.status_code, 201)
        order_id = json.loads(res_place.data)["id"]

        # Student cannot change order status to 'Preparing' (Forbidden)
        res_forbidden = self.client.put(
            f"/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={"status": "Preparing"}
        )
        self.assertEqual(res_forbidden.status_code, 403)

        # Admin advances order: Placed -> Preparing
        res_prep = self.client.put(
            f"/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"status": "Preparing"}
        )
        self.assertEqual(res_prep.status_code, 200)

        # Admin advances order: Preparing -> Ready
        res_ready = self.client.put(
            f"/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"status": "Ready"}
        )
        self.assertEqual(res_ready.status_code, 200)

        # Admin advances order: Ready -> Completed
        res_comp = self.client.put(
            f"/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"status": "Completed"}
        )
        self.assertEqual(res_comp.status_code, 200)

        # Invalid transition: Completed -> Placed (Rejected)
        res_invalid = self.client.put(
            f"/api/orders/{order_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"status": "Placed"}
        )
        self.assertEqual(res_invalid.status_code, 400)

    def test_11_reviews_validation_and_duplicate_prevention(self):
        unique_student = "test_token_student_reviewer99"

        # Invalid review (empty comment)
        res_invalid = self.client.post(
            "/api/reviews",
            headers={"Authorization": f"Bearer {unique_student}"},
            json={"menu_item_name": "Signature Cold Coffee", "rating": 5, "comment": ""}
        )
        self.assertEqual(res_invalid.status_code, 400)

        # Valid review
        res_valid = self.client.post(
            "/api/reviews",
            headers={"Authorization": f"Bearer {unique_student}"},
            json={
                "menu_item_name": "Signature Cold Coffee",
                "rating": 5,
                "comment": "Incredible brew, absolute campus lifesaver!"
            }
        )
        self.assertEqual(res_valid.status_code, 201)

        # Duplicate review for same item by same student is rejected with 409
        res_dup = self.client.post(
            "/api/reviews",
            headers={"Authorization": f"Bearer {unique_student}"},
            json={
                "menu_item_name": "Signature Cold Coffee",
                "rating": 4,
                "comment": "Second review should be rejected"
            }
        )
        self.assertEqual(res_dup.status_code, 409)

    def test_12_menu_image_mappings(self):
        res = self.client.get("/api/menu")
        self.assertEqual(res.status_code, 200)
        items = json.loads(res.data)
        menu_by_name = {i["name"]: i for i in items}

        # Gulab Jamun must not have the fish image
        gj = menu_by_name["Gulab Jamun"]
        self.assertNotIn("1599488615731", gj["image_url"])
        self.assertIn("premium_photo-1677956021545", gj["image_url"])

        # Veg Puff must not have chicken leg image
        vp = menu_by_name["Veg Puff"]
        self.assertNotIn("1626082927389", vp["image_url"])
        self.assertIn("premium_photo-1754823340366", vp["image_url"])

        # Chicken Puff must not have raw bread image
        cp = menu_by_name["Chicken Puff"]
        self.assertNotIn("1509440159596", cp["image_url"])
        self.assertIn("premium_photo-1694981405366", cp["image_url"])

        # Peri Peri French Fries must not have plain fries image
        pf = menu_by_name["Peri Peri French Fries"]
        self.assertNotIn("1630384060421", pf["image_url"])

        # Veg Sandwich and Crispy Paneer Grilled Sandwich must have distinct images
        vs = menu_by_name["Veg Sandwich"]
        cp_sand = menu_by_name["Crispy Paneer Grilled Sandwich"]
        self.assertNotEqual(vs["image_url"], cp_sand["image_url"])

    def test_13_server_side_order_pricing_tamper_proof(self):
        # Even if client tries to send tampered price = 1.0, backend looks up real DB price (Veg Samosa = 30)
        res = self.client.post(
            "/api/orders",
            headers={"Authorization": f"Bearer {self.student_token}"},
            json={
                "items": [{"name": "Veg Samosa", "price": 1.0, "quantity": 2}],
                "total_amount": 2.0,
                "pickup_time": "In 15 mins"
            }
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data["total_amount"], 60.0)

    def test_14_auth_config_no_trailing_slash_and_local_handling(self):
        # Authgear requires exact redirect URI without trailing slash
        res = self.client.get("/api/auth/config", headers={"Host": "localhost:8080"})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["redirectURI"], "http://localhost:8080")
        self.assertFalse(data["redirectURI"].endswith("/"))


if __name__ == "__main__":
    unittest.main()
