import json
from pymongo import MongoClient
from typing import List, Dict, Optional

class MongoAdapter:
    def __init__(self, db_uri: str, db_name: str):
        self.client = MongoClient(db_uri)
        self.db = self.client[db_name]

    # === USERS ===
    def retrieve_user(self, username: str) -> Dict:
        """Retrieve user by username"""
        user = self.db.users.find_one({"user_id": username})
        return user if user else {}

    def create_user(self, user_data: Dict) -> bool:
        """Create a new user"""
        if self.db.users.find_one({"user_id": user_data["user_id"]}):
            return False  # User already exists
        self.db.users.insert_one(user_data)
        return True

    def update_user(self, username: str, user_data: Dict) -> bool:
        """Update existing user data"""
        result = self.db.users.update_one({"user_id": username}, {"$set": user_data})
        return result.modified_count > 0

    # === GREENHOUSES ===
    def retrieve_greenhouse(self, greenhouse_id: str) -> Dict:
        """Retrieve greenhouse data"""
        greenhouse = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id})
        return greenhouse if greenhouse else {}

    def create_greenhouse(self, greenhouse_data: Dict) -> bool:
        """Create a new greenhouse"""
        if self.db.greenhouses.find_one({"greenhouse_id": greenhouse_data["greenhouse_id"]}):
            return False  # Greenhouse already exists
        self.db.greenhouses.insert_one(greenhouse_data)
        return True

    def greenhouse_name_exists(self, name: str, tenant_id: str) -> bool:
        return self.db.greenhouses.count_documents(
            {"name": name, "tenant_id": tenant_id},
            limit=1
        ) > 0

    def update_greenhouse(self, greenhouse_id: str, greenhouse_data: Dict) -> bool:
        """Update existing greenhouse data"""
        result = self.db.greenhouses.update_one({"greenhouse_id": greenhouse_id}, {"$set": greenhouse_data})
        return result.modified_count > 0

    def verify_greenhouse_existence(self, greenhouse_id: str) -> bool:
        """Check if a greenhouse exists."""
        return self.db.greenhouses.count_documents({"greenhouse_id": greenhouse_id}, limit=1) > 0

    def verify_greenhouse_ownership(self, greenhouse_id: str, username: str) -> bool:
        """Check if the greenhouse is owned by (associated to) the given username."""
        return self.db.greenhouses.count_documents(
            {"greenhouse_id": greenhouse_id, "tenant_id": username},
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
