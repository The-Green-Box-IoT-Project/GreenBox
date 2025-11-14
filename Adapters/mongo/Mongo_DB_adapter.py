import json
from pymongo import MongoClient
from typing import List, Dict

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

    def update_greenhouse(self, greenhouse_id: str, greenhouse_data: Dict) -> bool:
        """Update existing greenhouse data"""
        result = self.db.greenhouses.update_one({"greenhouse_id": greenhouse_id}, {"$set": greenhouse_data})
        return result.modified_count > 0

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

    # === ASSOCIATIONS ===
    def associate_device_with_greenhouse(self, device_id: str, greenhouse_id: str) -> bool:
        """Associate device to greenhouse"""
        result = self.db.greenhouses.update_one(
            {"greenhouse_id": greenhouse_id},
            {"$push": {"devices": device_id}}
        )
        return result.modified_count > 0

    def retrieve_devices_in_greenhouse(self, greenhouse_id: str) -> List[Dict]:
        """Retrieve all devices associated with a greenhouse"""
        greenhouse = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id})
        return greenhouse["devices"] if greenhouse else []

    def verify_device_association(self, device_id: str, greenhouse_id: str) -> bool:
        """Verify if device is associated with a greenhouse"""
        greenhouse = self.db.greenhouses.find_one({"greenhouse_id": greenhouse_id})
        return device_id in greenhouse["devices"] if greenhouse else False
