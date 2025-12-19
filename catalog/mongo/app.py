import cherrypy
import os
import json
from Mongo_DB_adapter import MongoAdapter

MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:rootpassword@mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "greenbox")


def _normalize_strategy_payload(payload: dict) -> dict:
    """Normalize different strategy shapes to {metric: {min, max}}.

    Accepts either:
      - nested: {"temperature": {"min": 18, "max": 26}, ...}
      - flat legacy: {"min_temperature": 18, "max_temperature": 26, ...}
      - scalar legacy (kept as-is): {"temperature": 10, ...}
    """
    if not isinstance(payload, dict):
        return {}

    nested_like = True
    for _, v in payload.items():
        if isinstance(v, dict):
            continue
        nested_like = False
        break
    if nested_like and payload:
        return payload

    normalized: dict = {}
    for k, v in payload.items():
        if not isinstance(k, str):
            continue
        if k.startswith('min_'):
            metric = k[4:]
            normalized.setdefault(metric, {})['min'] = v
        elif k.startswith('max_'):
            metric = k[4:]
            normalized.setdefault(metric, {})['max'] = v
        else:
            normalized[k] = v
    return normalized

class MongoService:
    exposed = True

    def __init__(self):
        self.mongo = MongoAdapter(MONGO_URI, DB_NAME)

    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        if not path:
            return {"status": "Mongo Adapter Ready"}
        
        if path[0] == 'verify-device':
            device_id = params.get('device_id')
            return {"exists": self.mongo.verify_device_existence(device_id)}
        
        if path[0] == 'greenhouses':
            if len(path) == 1:
                username = params.get('username')
                query = {"owner": username} if username else {}
                items = list(self.mongo.db.greenhouses.find(query, {"_id": 0}))
                return {"items": items}
            elif len(path) == 2:
                gh_id = path[1]
                gh = self.mongo.retrieve_greenhouse(gh_id)
                if not gh: raise cherrypy.HTTPError(404)
                gh.pop("_id", None)
                return gh
            elif len(path) == 3 and path[2] == 'thresholds':
                gh_id = path[1]
                thresholds = self.mongo.retrieve_greenhouse_thresholds(gh_id)
                return {
                    "greenhouse_id": gh_id,
                    "thresholds": thresholds or {}
                }
            elif len(path) == 3 and path[2] == 'effects':
                gh_id = path[1]
                effects = self.mongo.retrieve_greenhouse_effects(gh_id)
                return {
                    "greenhouse_id": gh_id,
                    "effects": effects or []
                }

        if path[0] == 'zones':
            if len(path) == 1:
                gh_id = params.get('greenhouse_id')
                return {"items": self.mongo.retrieve_zones(gh_id)}
            elif len(path) == 2:
                zone_id = path[1]
                zone = self.mongo.retrieve_zone(zone_id)
                if not zone:
                    raise cherrypy.HTTPError(404)
                zone.pop("_id", None)
                return zone
            elif len(path) == 3 and path[2] == 'strategy':
                zone_id = path[1]
                strategy = self.mongo.retrieve_zone_strategy(zone_id)
                return _normalize_strategy_payload(strategy or {})

        if path[0] == 'devices':
            if len(path) == 1:
                zone_id = params.get('zone_id')
                items = list(self.mongo.db.devices.find({"zone_id": zone_id}, {"_id": 0}))
                return {"items": items}
            elif len(path) == 2:
                dev_id = path[1]
                dev = self.mongo.retrieve_device(dev_id)
                if not dev: raise cherrypy.HTTPError(404)
                dev.pop("_id", None)
                return dev
            elif len(path) == 3 and path[2] == 'status':
                dev_id = path[1]
                dev = self.mongo.retrieve_device(dev_id)
                if not dev:
                    raise cherrypy.HTTPError(404)
                if dev.get("type") != "actuator":
                    raise cherrypy.HTTPError(400, "not_an_actuator")
                return {"status": dev.get("status", False)}

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *path, **params):
        body = cherrypy.request.json
        
        if path[0] == 'users':
            username = body.get('username')
            password = body.get('password')
            email = body.get('email')
            if not username or not password or not email:
                raise cherrypy.HTTPError(400, 'missing_fields')
            if self.mongo.create_user({"username": username, "password": password, "email": email, "greenhouses": []}):
                cherrypy.response.status = 201
                return {"status": "created"}
            raise cherrypy.HTTPError(409, "user_exists")
            
        if path[0] == 'login':
            username = body.get('username')
            password = body.get('password')
            user = self.mongo.retrieve_user(username)
            if user and user.get('password') == password:
                return {"status": "ok"}
            raise cherrypy.HTTPError(401)

        if path[0] == 'greenhouses':
            if self.mongo.create_greenhouse(body):
                cherrypy.response.status = 201
                return {"status": "created"}
            raise cherrypy.HTTPError(409)

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, *path, **params):
        body = cherrypy.request.json
        
        if path[0] == 'greenhouses' and len(path) == 2:
            gh_id = path[1]
            username = params.get('username')
            if not username:
                raise cherrypy.HTTPError(400, 'missing_username')
            if self.mongo.update_greenhouse_owned(gh_id, username, body):
                return {"status": "updated"}
            raise cherrypy.HTTPError(404)

        if path[0] == 'zones':
            if len(path) == 1:
                username = params.get('username')
                if not username:
                    raise cherrypy.HTTPError(400, 'missing_username')
                gh_id = body.get('greenhouse_id')
                if not gh_id or not self.mongo.verify_greenhouse_ownership(gh_id, username):
                    raise cherrypy.HTTPError(403)
                if self.mongo.create_zone(body):
                    return {"status": "created"}
                raise cherrypy.HTTPError(409)
            elif len(path) == 2:
                zone_id = path[1]
                name = body.get('name')
                username = params.get('username')
                if not username:
                    raise cherrypy.HTTPError(400, 'missing_username')
                if not self.mongo.verify_zone_ownership(zone_id, username):
                    raise cherrypy.HTTPError(403)
                if self.mongo.rename_zone(zone_id, name):
                    return {"status": "updated"}
                raise cherrypy.HTTPError(404)
            elif len(path) == 3 and path[2] == 'strategy':
                zone_id = path[1]
                username = params.get('username')
                if not username:
                    raise cherrypy.HTTPError(400, 'missing_username')
                if not self.mongo.verify_zone_ownership(zone_id, username):
                    raise cherrypy.HTTPError(403)
                strategy = _normalize_strategy_payload(body or {})
                if self.mongo.update_zone_strategy(zone_id, strategy):
                    return {"status": "updated"}
                raise cherrypy.HTTPError(404)

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.json_out()
    def DELETE(self, *path, **params):
        if path[0] == 'greenhouses' and len(path) == 2:
            username = params.get('username')
            if not username:
                raise cherrypy.HTTPError(400, 'missing_username')
            if self.mongo.delete_greenhouse_owned(path[1], username):
                return {"status": "deleted"}
            raise cherrypy.HTTPError(404)
            
        if path[0] == 'zones' and len(path) == 2:
            username = params.get('username')
            if not username:
                raise cherrypy.HTTPError(400, 'missing_username')
            if not self.mongo.verify_zone_ownership(path[1], username):
                raise cherrypy.HTTPError(403)
            if self.mongo.delete_zone(path[1]):
                return {"status": "deleted"}
            raise cherrypy.HTTPError(404)

        raise cherrypy.HTTPError(404)

if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
        }
    }
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8082})
    cherrypy.quickstart(MongoService(), '/', conf)
