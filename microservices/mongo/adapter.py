# adapter.py
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from pymongo import MongoClient, ReturnDocument


# -------------------------
# Errori (dominio) -> mappati a HTTP nella service
# -------------------------
class AdapterError(Exception):
    pass


class NotFound(AdapterError):
    pass


class Forbidden(AdapterError):
    pass


class Conflict(AdapterError):
    pass


# -------------------------
# Helpers
# -------------------------
def _with_auth_source_admin(uri: str) -> str:
    p = urlparse(uri)
    q = dict(parse_qsl(p.query))
    q["authSource"] = "admin"
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))


# -------------------------
# MongoDB Adapter
# -------------------------
@dataclass(frozen=True)
class MongoDBAdapter:
    def __post_init__(self) -> None:
        # SOLO env (niente fallback)
        uri = os.environ["MONGO_URI"]
        db_name = os.environ["MONGO_DB"]
        uri = _with_auth_source_admin(uri)

        client = MongoClient(uri)
        db = client[db_name]

        object.__setattr__(self, "_client", client)
        object.__setattr__(self, "_db", db)
        object.__setattr__(self, "_users", db["users"])
        object.__setattr__(self, "_greenhouses", db["greenhouses"])
        object.__setattr__(self, "_zones", db["zones"])
        object.__setattr__(self, "_devices", db["devices"])
        object.__setattr__(self, "_counters", db["counters"])

    # -------------------------
    # Helpers privati
    # -------------------------
    def _get_user(self, username: str) -> Dict[str, Any]:
        u = self._users.find_one({"username": username})
        if not u:
            raise NotFound("user_not_found")
        if u.get("greenhouses") is None:
            u["greenhouses"] = []
        return u

    def _user_greenhouse_ids(self, username: str) -> List[str]:
        return list(self._get_user(username).get("greenhouses", []))

    def _ensure_greenhouse_owned(self, username: str, greenhouse_id: str) -> None:
        if greenhouse_id not in self._user_greenhouse_ids(username):
            raise Forbidden("greenhouse_not_owned")

    def _get_greenhouse_owned(self, username: str, greenhouse_id: str) -> Dict[str, Any]:
        self._ensure_greenhouse_owned(username, greenhouse_id)
        gh = self._greenhouses.find_one({"greenhouse_id": greenhouse_id})
        if not gh:
            raise NotFound("greenhouse_not_found")
        if gh.get("zones") is None:
            gh["zones"] = []
        return gh

    def _zone_doc(self, zone_id: str) -> Dict[str, Any]:
        z = self._zones.find_one({"zone_id": zone_id})
        if not z:
            raise NotFound("zone_not_found")
        if z.get("devices") is None:
            z["devices"] = []
        if z.get("strategy") is None:
            z["strategy"] = {}
        return z

    def _find_user_greenhouse_containing_zone(self, username: str, zone_id: str) -> Optional[str]:
        for gh_id in self._user_greenhouse_ids(username):
            gh = self._greenhouses.find_one({"greenhouse_id": gh_id}, {"zones": 1})
            if gh and zone_id in (gh.get("zones") or []):
                return gh_id
        return None

    def _ensure_zone_owned(self, username: str, zone_id: str) -> None:
        if not self._find_user_greenhouse_containing_zone(username, zone_id):
            raise Forbidden("zone_not_owned")

    def _is_zone_assigned_anywhere(self, zone_id: str) -> bool:
        return self._greenhouses.count_documents({"zones": zone_id}, limit=1) > 0

    def _greenhouse_name_taken_for_user(self, username: str, name: str, *, exclude_id: Optional[str] = None) -> bool:
        ids = self._user_greenhouse_ids(username)
        if exclude_id:
            ids = [x for x in ids if x != exclude_id]
        if not ids:
            return False
        return self._greenhouses.count_documents(
            {"greenhouse_id": {"$in": ids}, "name": name},
            limit=1
        ) > 0

    def _zone_name_taken_for_user(self, username: str, name: str, *, exclude_zone_id: Optional[str] = None) -> bool:
        zone_ids: List[str] = []
        for gh_id in self._user_greenhouse_ids(username):
            gh = self._greenhouses.find_one({"greenhouse_id": gh_id}, {"zones": 1})
            if gh:
                zone_ids.extend(list(gh.get("zones") or []))

        if exclude_zone_id:
            zone_ids = [zid for zid in zone_ids if zid != exclude_zone_id]

        if not zone_ids:
            return False

        return self._zones.count_documents(
            {"zone_id": {"$in": zone_ids}, "name": name},
            limit=1
        ) > 0

    def _next_greenhouse_id(self) -> str:
        doc = self._counters.find_one_and_update(
            {"_id": "greenhouse_seq"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        n = int(doc.get("seq", 1))
        return f"GH_{n:03d}"

    def _next_device_id(self, prefix: str) -> str:
        """
        Genera ID univoci (es. VENT_001).
        Include un controllo di sicurezza (loop) per evitare collisioni con dati esistenti.
        """
        while True:
            # 1. Incrementa il contatore
            seq_name = f"{prefix.lower()}_seq"
            doc = self._counters.find_one_and_update(
                {"_id": seq_name},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            n = int(doc.get("seq", 1))
            candidate_id = f"{prefix}_{n:03d}"

            # 2. Verifica collisione su 'devices'
            if self._devices.count_documents({"device_id": candidate_id}, limit=1) == 0:
                return candidate_id

    # -------------------------
    # Greenhouses
    # -------------------------
    def retrieve_greenhouses(self, username: str) -> List[str]:
        return self._user_greenhouse_ids(username)

    def retrieve_greenhouse(self, username: str, greenhouse_id: str) -> Dict[str, Any]:
        gh = self._get_greenhouse_owned(username, greenhouse_id)
        return {"name": gh.get("name"), "zones": list(gh.get("zones") or [])}

    def add_greenhouse(self, username: str, name: str) -> None:
        if self._greenhouse_name_taken_for_user(username, name):
            raise Conflict("greenhouse_name_taken")

        greenhouse_id = self._next_greenhouse_id()

        try:
            self._greenhouses.insert_one({
                "greenhouse_id": greenhouse_id,
                "name": name,
                "zones": []
            })
        except Exception as e:
            if "E11000" in str(e):
                greenhouse_id = self._next_greenhouse_id()
                self._greenhouses.insert_one({
                    "greenhouse_id": greenhouse_id,
                    "name": name,
                    "zones": []
                })
            else:
                raise

        self._users.update_one({"username": username}, {"$addToSet": {"greenhouses": greenhouse_id}})

    def rename_greenhouse(self, username: str, greenhouse_id: str, new_name: str) -> None:
        self._get_greenhouse_owned(username, greenhouse_id)

        if self._greenhouse_name_taken_for_user(username, new_name, exclude_id=greenhouse_id):
            raise Conflict("greenhouse_name_taken")

        res = self._greenhouses.update_one(
            {"greenhouse_id": greenhouse_id},
            {"$set": {"name": new_name}}
        )
        if res.matched_count == 0:
            raise NotFound("greenhouse_not_found")

    def delete_greenhouse(self, username: str, greenhouse_id: str) -> None:
        self._ensure_greenhouse_owned(username, greenhouse_id)

        self._users.update_one({"username": username}, {"$pull": {"greenhouses": greenhouse_id}})
        res = self._greenhouses.delete_one({"greenhouse_id": greenhouse_id})
        if res.deleted_count == 0:
            raise NotFound("greenhouse_not_found")

    # -------------------------
    # Zone
    # -------------------------
    def get_info_from_device(self, greenhouse_id: str, device_id: str) -> Optional[Dict[str, str]]:
        """
        Dato un greenhouse_id e un device_id, risale al proprietario (username)
        e alla zona specifica.
        """
        # 1. Trova l'utente
        user_doc = self._users.find_one({"greenhouses": greenhouse_id}, {"username": 1})
        if not user_doc:
            return None

        # 2. Trova la zona
        zone_doc = self._zones.find_one({"devices": device_id}, {"zone_id": 1})
        if not zone_doc:
            return None
        
        found_zone_id = zone_doc["zone_id"]

        # 3. Cross-check di sicurezza (la zona deve essere in quella serra)
        gh_check = self._greenhouses.find_one({
            "greenhouse_id": greenhouse_id,
            "zones": found_zone_id
        })
        
        if not gh_check:
            return None

        return {
            "username": user_doc["username"],
            "zone_id": found_zone_id
        }
    
    def retrieve_zones(self, username: str, greenhouse_id: str) -> List[Dict[str, str]]:
        gh = self._get_greenhouse_owned(username, greenhouse_id)
        zone_ids = list(gh.get("zones") or [])
        if not zone_ids:
            return []

        cursor = self._zones.find({"zone_id": {"$in": zone_ids}}, {"_id": 0, "zone_id": 1, "name": 1})
        by_id = {d["zone_id"]: d for d in cursor}

        out: List[Dict[str, str]] = []
        for zid in zone_ids:
            z = by_id.get(zid)
            if z:
                out.append({"id": z["zone_id"], "name": z.get("name", "")})
        return out

    def check_zone_validity(self, zone_id: str) -> bool:
        return self._zones.count_documents({"zone_id": zone_id}, limit=1) > 0

    def retrieve_zone(self, username: str, zone_id: str) -> Dict[str, Any]:
        self._ensure_zone_owned(username, zone_id)
        z = self._zone_doc(zone_id)
        return {"name": z.get("name"), "devices": list(z.get("devices") or [])}

    def associate_zone(self, username: str, greenhouse_id: str, zone_id: str, zone_name: str) -> None:
        self._get_greenhouse_owned(username, greenhouse_id)
        
        # Cerchiamo se la zona esiste
        existing_zone = self._zones.find_one({"zone_id": zone_id})

        if existing_zone:
            if self._is_zone_assigned_anywhere(zone_id):
                raise Conflict("zone_already_assigned")
        else:
            # --- 1. PROVISIONING DEVICE ---
            device_templates = [
                {"prefix": "RB",    "type": "raspberry"},
                {"prefix": "VENT",  "type": "ventilation_system"},
                {"prefix": "HEAT",  "type": "heating_system"},
                {"prefix": "LIGHT", "type": "illumination_system"},
                {"prefix": "IRRIG", "type": "irrigation_system"},
                {"prefix": "HUM",   "type": "humidification_system"}
            ]

            new_device_ids = []
            new_device_docs = []

            for t in device_templates:
                d_id = self._next_device_id(t["prefix"])
                new_device_ids.append(d_id)
                new_device_docs.append({
                    "device_id": d_id,
                    "type": t["type"],
                    "parent_zone": zone_id 
                })

            if new_device_docs:
                self._devices.insert_many(new_device_docs)

            # --- 2. PROVISIONING STRATEGY (NUOVO) ---
            default_strategy = {
                "temperature": {
                    "min": 20,
                    "max": 25
                },
                "light": {
                    "enabled": "false",
                    "start": 10,
                    "end": 15
                },
                "humidity": {
                    "min": 0.4,
                    "max": 0.7
                },
                "soil_humidity": {
                    "min": 0.25,
                    "max": 0.45
                }
            }

            # --- 3. CREAZIONE ZONA ---
            self._zones.insert_one({
                "zone_id": zone_id,
                "name": zone_name,
                "devices": new_device_ids,
                "strategy": default_strategy  # Qui inseriamo la strategia di default
            })

        if self._zone_name_taken_for_user(username, zone_name, exclude_zone_id=zone_id):
            raise Conflict("zone_name_taken")

        # Associazione alla Greenhouse
        res = self._greenhouses.update_one(
            {"greenhouse_id": greenhouse_id},
            {"$addToSet": {"zones": zone_id}}
        )
        if res.matched_count == 0:
            raise NotFound("greenhouse_not_found")

        self._zones.update_one({"zone_id": zone_id}, {"$set": {"name": zone_name}})

    def rename_zone(self, username: str, zone_id: str, new_name: str) -> None:
        self._ensure_zone_owned(username, zone_id)
        self._zone_doc(zone_id)

        if self._zone_name_taken_for_user(username, new_name, exclude_zone_id=zone_id):
            raise Conflict("zone_name_taken")

        res = self._zones.update_one({"zone_id": zone_id}, {"$set": {"name": new_name}})
        if res.matched_count == 0:
            raise NotFound("zone_not_found")

    def disassociate_zone(self, username: str, zone_id: str) -> None:
        self._zone_doc(zone_id)

        gh_id = self._find_user_greenhouse_containing_zone(username, zone_id)
        if not gh_id:
            raise Forbidden("zone_not_owned")

        res = self._greenhouses.update_one(
            {"greenhouse_id": gh_id},
            {"$pull": {"zones": zone_id}}
        )
        if res.matched_count == 0:
            raise NotFound("greenhouse_not_found")

    # -------------------------
    # Control Strategy
    # -------------------------
    def get_control_strategy(self, username: str, zone_id: str) -> Dict[str, Any]:
        self._ensure_zone_owned(username, zone_id)
        z = self._zone_doc(zone_id)
        return dict(z.get("strategy") or {})

    def update_control_strategy(self, username: str, zone_id: str, strategy: Dict[str, Any]) -> None:
        self._ensure_zone_owned(username, zone_id)
        self._zone_doc(zone_id)

        res = self._zones.update_one({"zone_id": zone_id}, {"$set": {"strategy": strategy}})
        if res.matched_count == 0:
            raise NotFound("zone_not_found")

    # -------------------------
    # Devices
    # -------------------------
    def retrieve_devices(self, username: str, zone_id: str) -> List[Dict[str, str]]:
        self._ensure_zone_owned(username, zone_id)
        z = self._zone_doc(zone_id)
        dev_ids = list(z.get("devices") or [])
        if not dev_ids:
            return []

        cursor = self._devices.find({"device_id": {"$in": dev_ids}}, {"_id": 0, "device_id": 1, "type": 1})
        by_id = {d["device_id"]: d for d in cursor}

        out: List[Dict[str, str]] = []
        for did in dev_ids:
            d = by_id.get(did)
            if d:
                out.append({"id": d["device_id"], "type": d.get("type", "")})
        return out

    # -------------------------
    # Statistics
    # -------------------------
    def get_all_statistics_zones(self):
        """
        System-wide: returns all (greenhouse_id, zone_id, raspberry_id) found in DB.
        No username / ownership checks (intended for internal services like Statistics).
        """
        out = []

        # iterate all greenhouses
        cursor = self._greenhouses.find({}, {"_id": 0, "greenhouse_id": 1, "zones": 1})
        for gh in cursor:
            gh_id = gh.get("greenhouse_id")
            for zone_id in (gh.get("zones") or []):
                z = self._zones.find_one({"zone_id": zone_id}, {"_id": 0, "devices": 1})
                if not z:
                    continue

                dev_ids = list(z.get("devices") or [])
                if not dev_ids:
                    continue

                # fastest/common: RB_* is in devices list
                rb_id = next((d for d in dev_ids if isinstance(d, str) and d.startswith("RB_")), None)

                # fallback: use devices collection type=raspberry among those ids
                if not rb_id:
                    d = self._devices.find_one(
                        {"device_id": {"$in": dev_ids}, "type": "raspberry"},
                        {"_id": 0, "device_id": 1}
                    )
                    rb_id = d.get("device_id") if d else None

                if rb_id:
                    out.append({
                        "greenhouse_id": gh_id,
                        "zone_id": zone_id,
                        "raspberry_id": rb_id
                    })

        return out

    def get_all_measurements(self) -> List[str]:
        """
        Returns the list of measurements (metric names) used by raspberries.
        Since they are the same for all, we derive them from zone.strategy keys.
        """
        z = self._zones.find_one({}, {"_id": 0, "strategy": 1})
        if not z:
            return []
        strategy = z.get("strategy") or {}
        return list(strategy.keys())
