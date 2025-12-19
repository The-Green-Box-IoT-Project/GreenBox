import os
import unittest
import uuid

import requests


CATALOG_BASE_URL = os.getenv("CATALOG_BASE_URL", "http://localhost:8080").rstrip("/")


def _post_json(path: str, payload: dict, headers: dict | None = None):
    return requests.post(f"{CATALOG_BASE_URL}{path}", json=payload, headers=headers, timeout=10)


def _put(path: str, headers: dict | None = None):
    return requests.put(f"{CATALOG_BASE_URL}{path}", headers=headers, timeout=10)


def _put_json(path: str, payload: dict, headers: dict | None = None):
    return requests.put(f"{CATALOG_BASE_URL}{path}", json=payload, headers=headers, timeout=10)


def _get(path: str, headers: dict | None = None):
    return requests.get(f"{CATALOG_BASE_URL}{path}", headers=headers, timeout=10)


def _delete(path: str, headers: dict | None = None):
    return requests.delete(f"{CATALOG_BASE_URL}{path}", headers=headers, timeout=10)


class TestCatalogMongoOnly(unittest.TestCase):
    def test_happy_path_auth_greenhouse_zone_strategy(self):
        username = f"test_{uuid.uuid4().hex[:10]}"
        password = "pw"
        email = f"{username}@example.com"

        r = _post_json("/register", {"username": username, "password": password, "email": email})
        self.assertEqual(r.status_code, 200, r.text)

        r = _post_json("/login", {"username": username, "password": password})
        self.assertEqual(r.status_code, 200, r.text)
        token = r.json().get("token")
        self.assertTrue(token)
        headers = {"token": token}

        r = _get("/broker")
        self.assertEqual(r.status_code, 200, r.text)
        broker_payload = r.json()
        self.assertIn("broker_ip", broker_payload)
        self.assertIn("broker_port", broker_payload)

        r = _get("/user/info", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json().get("username"), username)

        gh_name = f"GH_{uuid.uuid4().hex[:8]}"
        r = _post_json("/greenhouses", {"name": gh_name}, headers=headers)
        self.assertEqual(r.status_code, 200, r.text)

        r = _get("/greenhouses", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        ghs = r.json()
        if isinstance(ghs, dict):
            ghs = [ghs]
        self.assertTrue(len(ghs) >= 1)
        gh_id = next((x["id"] for x in ghs if x.get("name") == gh_name), None)
        self.assertTrue(gh_id)

        r = _get(f"/greenhouses/{gh_id}/thresholds")
        self.assertEqual(r.status_code, 200, r.text)
        thresholds_payload = r.json()
        self.assertEqual(thresholds_payload.get("greenhouse_id"), gh_id)
        self.assertIsInstance(thresholds_payload.get("thresholds"), dict)

        r = _get(f"/greenhouses/{gh_id}/effects")
        self.assertEqual(r.status_code, 200, r.text)
        effects_payload = r.json()
        self.assertEqual(effects_payload.get("greenhouse_id"), gh_id)
        self.assertIsInstance(effects_payload.get("effects"), list)

        zone_id = f"Z_{uuid.uuid4().hex[:8]}"
        r = _put(f"/zones?greenhouse_id={gh_id}&zone_id={zone_id}&name=Zone%201", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)

        r = _get(f"/zones?greenhouse_id={gh_id}", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        zones = r.json()
        if isinstance(zones, dict):
            zones = [zones]
        self.assertTrue(any(z.get("id") == zone_id for z in zones))

        r = _get(f"/devices?zone_id={zone_id}", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        devices = r.json()
        if isinstance(devices, dict):
            devices = [devices]
        self.assertGreaterEqual(len(devices), 4)

        r = _put(f"/zones/validate?zone_id={zone_id}", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json() is True or r.json() == True)

        strategy = {
            "temperature": {"min": 18, "max": 26},
            "soilHumidity": {"min": 0.25, "max": 0.45},
            "airHumidity": {"min": 0.40, "max": 0.70},
        }
        r = _put_json(f"/zones/strategy?zone_id={zone_id}", strategy, headers=headers)
        self.assertEqual(r.status_code, 200, r.text)

        r = _get(f"/zones/strategy?zone_id={zone_id}", headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        payload = r.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("temperature", payload)

    def test_ownership_enforced_on_greenhouse_rename_delete(self):
        u1 = f"t1_{uuid.uuid4().hex[:8]}"
        u2 = f"t2_{uuid.uuid4().hex[:8]}"
        pw = "pw"

        self.assertEqual(_post_json("/register", {"username": u1, "password": pw, "email": f"{u1}@example.com"}).status_code, 200)
        self.assertEqual(_post_json("/register", {"username": u2, "password": pw, "email": f"{u2}@example.com"}).status_code, 200)

        t1 = _post_json("/login", {"username": u1, "password": pw}).json()["token"]
        t2 = _post_json("/login", {"username": u2, "password": pw}).json()["token"]
        h1 = {"token": t1}
        h2 = {"token": t2}

        gh_name = f"GH_{uuid.uuid4().hex[:8]}"
        self.assertEqual(_post_json("/greenhouses", {"name": gh_name}, headers=h1).status_code, 200)
        ghs = _get("/greenhouses", headers=h1).json()
        if isinstance(ghs, dict):
            ghs = [ghs]
        gh_id = next((x["id"] for x in ghs if x.get("name") == gh_name), None)
        self.assertTrue(gh_id)

        r = _put(f"/greenhouses?id={gh_id}&name=Hacked", headers=h2)
        self.assertEqual(r.status_code, 403, r.text)

        r = _delete(f"/greenhouses?id={gh_id}", headers=h2)
        self.assertEqual(r.status_code, 403, r.text)


if __name__ == "__main__":
    unittest.main()
