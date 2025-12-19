import json
from pymongo import MongoClient
from typing import List, Dict, Optional

class MongoAdapter:
    def __init__(self, db_uri: str, db_name: str):
        self.client = MongoClient(db_uri)
        self.db = self.client[db_name]

    # === USERS ===
    def retrieve_user(self, username: str) -> Dict:
        """Retrieve user by username."""
        user = self.db.users.find_one({"username": username})
        return user if user else {}

    def create_user(self, user_data: Dict) -> bool:
        """Create a new user."""
        username = user_data.get("username")
        password = user_data.get("password")
        email = user_data.get("email")
        if not username or not password or not email:
            return False
        if self.db.users.find_one({"username": username}):
            return False
        self.db.users.insert_one({
            "username": username,
            "password": password,
            "email": email,
            # Canonical: list of {greenhouse_id, name}
            "greenhouses": user_data.get("greenhouses", []),
        })
        return True

    def update_user(self, username: str, user_data: Dict) -> bool:
        """Update existing user data."""
        result = self.db.users.update_one({"username": username}, {"$set": user_data})
        return result.modified_count > 0

    # === GREENHOUSES ===
    def retrieve_greenhouse(self, greenhouse_id: str) -> Dict:
        """Retrieve greenhouse data"""
        greenhouse = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id})
        return greenhouse if greenhouse else {}

    def create_greenhouse(self, greenhouse_data: Dict) -> bool:
        """Create a new greenhouse"""
        if not greenhouse_data:
            return False
        gh_id = greenhouse_data.get("greenhouse_id")
        owner = greenhouse_data.get("owner")
        name = greenhouse_data.get("name")
        if not gh_id or not owner or not name:
            return False

        if self.db.greenhouses.find_one({"greenhouse_id": gh_id}):
            return False  # Greenhouse already exists
        # Check name uniqueness for the user
        if self.greenhouse_name_exists(name, owner):
            return False
        self.db.greenhouses.insert_one(greenhouse_data)

        # Keep user's greenhouse references in sync: add {greenhouse_id, name}
        try:
            self.db.users.update_one(
                {"username": owner},
                {"$addToSet": {"greenhouses": {"greenhouse_id": gh_id, "name": name}}},
            )
        except Exception:
            pass
        return True

    def greenhouse_name_exists(self, name: str, tenant_id: str) -> bool:
        return self.db.greenhouses.count_documents(
            {"name": name, "owner": tenant_id},
            limit=1
        ) > 0

    def update_greenhouse(self, greenhouse_id: str, greenhouse_data: Dict) -> bool:
        """Update existing greenhouse data"""
        # If name is being updated, check uniqueness
        if "name" in greenhouse_data:
            gh = self.retrieve_greenhouse(greenhouse_id)
            if not gh: return False
            if self.greenhouse_name_exists(greenhouse_data["name"], gh["owner"]):
                return False
        
        result = self.db.greenhouses.update_one({"greenhouse_id": greenhouse_id}, {"$set": greenhouse_data})
        return result.modified_count > 0

    def update_greenhouse_owned(self, greenhouse_id: str, username: str, greenhouse_data: Dict) -> bool:
        """Update greenhouse only if owned by username."""
        gh = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id, "owner": username})
        if not gh:
            return False
        if "name" in greenhouse_data and self.greenhouse_name_exists(greenhouse_data["name"], username):
            return False
        result = self.db.greenhouses.update_one(
            {"greenhouse_id": greenhouse_id, "owner": username},
            {"$set": greenhouse_data},
        )

        # If the greenhouse name changed, reflect it in user's embedded list
        if result.modified_count > 0 and "name" in (greenhouse_data or {}):
            try:
                self.db.users.update_one(
                    {"username": username},
                    {"$set": {"greenhouses.$[g].name": greenhouse_data["name"]}},
                    array_filters=[{"g.greenhouse_id": greenhouse_id}],
                )
            except Exception:
                pass
        return result.modified_count > 0

    def delete_greenhouse_owned(self, greenhouse_id: str, username: str) -> bool:
        """Delete greenhouse only if owned by username."""
        res = self.db.greenhouses.delete_one({"greenhouse_id": greenhouse_id, "owner": username})

        # Remove from user's embedded list (best-effort)
        if res.deleted_count > 0:
            try:
                self.db.users.update_one(
                    {"username": username},
                    {"$pull": {"greenhouses": {"greenhouse_id": greenhouse_id}}},
                )
            except Exception:
                pass
        return res.deleted_count > 0

    def verify_greenhouse_existence(self, greenhouse_id: str) -> bool:
        """Check if a greenhouse exists."""
        return self.db.greenhouses.count_documents({"greenhouse_id": greenhouse_id}, limit=1) > 0

    def verify_greenhouse_ownership(self, greenhouse_id: str, username: str) -> bool:
        """Check if the greenhouse is owned by (associated to) the given username."""
        return self.db.greenhouses.count_documents(
            {"greenhouse_id": greenhouse_id, "owner": username},
            limit=1
        ) > 0

    # === DEVICES ===
    def retrieve_device(self, device_id: str) -> Dict:
        """Retrieve device details by device ID"""
        device = self.db.devices.find_one({"device_id": device_id})
        return device if device else {}

    def create_device(self, device_data: Dict) -> bool:
        """Create a new device"""
        if self.db.devices.find_one({"device_id": device_data["device_id"]}):
            return False  # Device already exists
        self.db.devices.insert_one(device_data)
        return True

    def update_device(self, device_id: str, device_data: Dict) -> bool:
        """Update device data"""
        result = self.db.devices.update_one({"device_id": device_id}, {"$set": device_data})
        return result.modified_count > 0

    def verify_device_existence(self, device_id: str) -> bool:
        """Check if a device exists."""
        return self.db.devices.count_documents({"device_id": device_id}, limit=1) > 0

    def device_name_exists_in_greenhouse(self, name: str, greenhouse_id: str) -> bool:
        return self.db.devices.count_documents(
            {"greenhouse_id": greenhouse_id, "name": name},
            limit=1
        ) > 0

    def is_device_associated(self, device_id: str) -> bool:
        doc = self.db.devices.find_one({"device_id": device_id}, {"greenhouse_id": 1, "associated_greenhouse": 1})
        if not doc:
            return False
        return bool(doc.get("greenhouse_id") or doc.get("associated_greenhouse"))

    # === ASSOCIATIONS ===
    def associate_device_with_greenhouse(self, device_id: str, greenhouse_id: str, device_name: str | None = None) -> bool:
        """Associate device to greenhouse and update device document."""
        upd = {"greenhouse_id": greenhouse_id}
        if device_name:
            upd["name"] = device_name
        dev_res = self.db.devices.update_one(
            {"device_id": device_id, "greenhouse_id": {"$exists": False}},
            {"$set": upd}
        )
        if dev_res.matched_count == 0:
            return False
        gh_res = self.db.greenhouses.update_one(
            {"greenhouse_id": greenhouse_id},
            {"$addToSet": {"devices": device_id}}
        )
        return gh_res.modified_count > 0

    def retrieve_devices_in_greenhouse(self, greenhouse_id: str) -> List[Dict]:
        """Retrieve all devices associated with a greenhouse"""
        greenhouse = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id})
        return greenhouse["devices"] if greenhouse else []

    def verify_device_association(self, device_id: str, greenhouse_id: str) -> bool:
        """Verify if device is associated with a greenhouse"""
        greenhouse = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id})
        return device_id in greenhouse["devices"] if greenhouse else False

    # === GREENHOUSE CONFIG ===
    def retrieve_greenhouse_thresholds(self, greenhouse_id: str) -> Dict:
        """Return thresholds object for a greenhouse or {} if missing."""
        greenhouse = self.retrieve_greenhouse(greenhouse_id)
        return greenhouse.get("thresholds", {}) if greenhouse else {}

    def retrieve_greenhouse_effects(self, greenhouse_id: str) -> List[Dict]:
        """Return list of actuator effects for a greenhouse."""
        doc = self.db.greenhouse_effects.find_one({"greenhouse_id": greenhouse_id})
        return doc.get("effects", []) if doc else []

    # === BINDINGS ===
    def bind_actuator_to_device(self, actuator_id: str, controller_id: str) -> bool:
        """Bind an actuator to a controller/raspberry."""
        result = self.db.devices.update_one(
            {"device_id": actuator_id},
            {"$set": {"bound_device_id": controller_id, "updated_at": None}}
        )
        return result.modified_count > 0

    # === TELEMETRY ===
    def retrieve_telemetry(self, device_id: str, metric: str, time_range: str) -> Optional[List[Dict]]:
        """Retrieve telemetry points for a device/metric/range if stored in DB."""
        doc = self.db.telemetry.find_one({"device_id": device_id})
        if not doc:
            return None
        metrics = doc.get("metrics", {})
        metric_block = metrics.get(metric) or metrics.get(metric.lower())
        if not metric_block:
            return None
        return metric_block.get(time_range)

    # === ZONES ===
    def retrieve_zone(self, zone_id: str) -> Dict:
        zone = self.db.zones.find_one({"zone_id": zone_id})
        return zone if zone else {}

    def verify_zone_existence(self, zone_id: str) -> bool:
        return self.db.zones.count_documents({"zone_id": zone_id}, limit=1) > 0

    def verify_zone_ownership(self, zone_id: str, username: str) -> bool:
        zone = self.retrieve_zone(zone_id)
        if not zone:
            return False
        gh_id = zone.get("greenhouse_id")
        if not gh_id:
            return False
        return self.verify_greenhouse_ownership(gh_id, username)
    def retrieve_zones(self, greenhouse_id: str) -> List[Dict]:
        return list(self.db.zones.find({"greenhouse_id": greenhouse_id}, {"_id": 0}))

    def zone_name_exists(self, name: str, greenhouse_id: str) -> bool:
        return self.db.zones.count_documents(
            {"name": name, "greenhouse_id": greenhouse_id},
            limit=1
        ) > 0

    def create_zone(self, zone_data: Dict) -> bool:
        if not zone_data or not zone_data.get("zone_id") or not zone_data.get("greenhouse_id") or not zone_data.get("name"):
            return False

        if self.db.zones.find_one({"zone_id": zone_data["zone_id"]}):
            return False
        # Check name uniqueness in the greenhouse
        if self.zone_name_exists(zone_data["name"], zone_data["greenhouse_id"]):
            return False

        # Ensure a default strategy exists for new zones.
        # UI-friendly nested format: {metric: {min, max}}
        if not isinstance(zone_data.get("strategy"), dict) or not zone_data.get("strategy"):
            zone_data["strategy"] = {
                "temperature": {"min": 20, "max": 25},
                "light": {"min": 300, "max": 800},
                "airHumidity": {"min": 0.40, "max": 0.70},
                "soilHumidity": {"min": 0.25, "max": 0.45},
            }

        self.db.zones.insert_one(zone_data)

        # Auto-create the 4 actuators for the zone.
        zone_id = zone_data["zone_id"]
        greenhouse_id = zone_data["greenhouse_id"]
        actuator_defs = [
            ("fan", "Fan"),
            ("heater", "Heater"),
            ("irrigation", "Irrigation"),
            ("light", "Light"),
        ]
        device_ids = []
        device_docs = []
        for suffix, display_name in actuator_defs:
            device_id = f"{zone_id}_{suffix}"
            device_ids.append(device_id)
            device_docs.append(
                {
                    "device_id": device_id,
                    "greenhouse_id": greenhouse_id,
                    "zone_id": zone_id,
                    "type": "actuator",
                    "role": suffix,
                    "status": "off",
                    "name": display_name,
                }
            )

        if device_docs:
            try:
                self.db.devices.insert_many(device_docs, ordered=False)
            except Exception:
                # If some duplicates exist (shouldn't on fresh zone), ignore and continue.
                pass

        # Keep greenhouse.devices list in sync (best-effort).
        try:
            self.db.greenhouses.update_one(
                {"greenhouse_id": greenhouse_id},
                {"$addToSet": {"devices": {"$each": device_ids}}},
            )
        except Exception:
            pass
        return True

    def rename_zone(self, zone_id: str, new_name: str) -> bool:
        zone = self.db.zones.find_one({"zone_id": zone_id})
        if not zone: return False
        
        # Check name uniqueness in the greenhouse
        if self.zone_name_exists(new_name, zone["greenhouse_id"]):
            return False
            
        res = self.db.zones.update_one({"zone_id": zone_id}, {"$set": {"name": new_name}})
        return res.modified_count > 0

    def delete_zone(self, zone_id: str) -> bool:
        res = self.db.zones.delete_one({"zone_id": zone_id})
        return res.deleted_count > 0

    def update_zone_strategy(self, zone_id: str, strategy: Dict) -> bool:
        # Construct $set dictionary for partial updates using dot notation
        # This allows updating "temperature" without overwriting "humidity"
        update_fields = {f"strategy.{k}": v for k, v in strategy.items()}
        res = self.db.zones.update_one({"zone_id": zone_id}, {"$set": update_fields})
        return res.matched_count > 0

    def retrieve_zone_strategy(self, zone_id: str) -> Dict:
        zone = self.db.zones.find_one({"zone_id": zone_id})
        return zone.get("strategy", {}) if zone else {}

