import cherrypy
import os
import json
from Mongo_DB_adapter import MongoAdapter

MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:rootpassword@mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "greenbox")

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

        if path[0] == 'zones':
            if len(path) == 1:
                gh_id = params.get('greenhouse_id')
                return {"items": self.mongo.retrieve_zones(gh_id)}
            elif len(path) == 3 and path[2] == 'strategy':
                zone_id = path[1]
                return self.mongo.retrieve_zone_strategy(zone_id)

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
                return {"status": dev.get("status", False)}

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self, *path, **params):
        body = cherrypy.request.json
        
        if path[0] == 'users':
            if self.mongo.create_user(body):
                return {"status": "created"}
            raise cherrypy.HTTPError(409, "User exists")
            
        if path[0] == 'login':
            username = body.get('username')
            password = body.get('password')
            user = self.mongo.retrieve_user(username)
            if user and user.get('password') == password:
                return {"status": "ok"}
            raise cherrypy.HTTPError(401)

        if path[0] == 'greenhouses':
            if self.mongo.create_greenhouse(body):
                return {"status": "created"}
            raise cherrypy.HTTPError(409)

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def PUT(self, *path, **params):
        body = cherrypy.request.json
        
        if path[0] == 'greenhouses' and len(path) == 2:
            gh_id = path[1]
            if self.mongo.update_greenhouse(gh_id, body):
                return {"status": "updated"}
            raise cherrypy.HTTPError(400)

        if path[0] == 'zones':
            if len(path) == 1:
                if self.mongo.create_zone(body):
                    return {"status": "created"}
                raise cherrypy.HTTPError(409)
            elif len(path) == 2:
                zone_id = path[1]
                name = body.get('name')
                if self.mongo.rename_zone(zone_id, name):
                    return {"status": "updated"}
                raise cherrypy.HTTPError(400)
            elif len(path) == 3 and path[2] == 'strategy':
                zone_id = path[1]
                if self.mongo.update_zone_strategy(zone_id, body):
                    return {"status": "updated"}
                raise cherrypy.HTTPError(400)

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.json_out()
    def DELETE(self, *path, **params):
        if path[0] == 'greenhouses' and len(path) == 2:
            res = self.mongo.db.greenhouses.delete_one({"greenhouse_id": path[1]})
            if res.deleted_count: return {"status": "deleted"}
            raise cherrypy.HTTPError(404)
            
        if path[0] == 'zones' and len(path) == 2:
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
