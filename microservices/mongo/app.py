# app.py
import cherrypy
from adapter import MongoDBAdapter, NotFound, Forbidden, Conflict

def handle_adapter_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFound as e:
            raise cherrypy.HTTPError(404, str(e))
        except Forbidden as e:
            raise cherrypy.HTTPError(403, str(e))
        except Conflict as e:
            raise cherrypy.HTTPError(409, str(e))
        except KeyError as e:
            # Cattura errori di chiavi mancanti nel JSON body
            raise cherrypy.HTTPError(400, f"Missing parameter: {str(e)}")
    return wrapper

class MongoService:
    exposed = True

    def __init__(self):
        self.db = MongoDBAdapter()

    # GET /users/<username>/...
    @cherrypy.tools.json_out()
    @handle_adapter_errors
    def GET(self, username=None, *args, **kwargs):
        if not username:
            raise cherrypy.HTTPError(404)
        # Recupera 'id' dai query params (kwargs)
        id_param = kwargs.get("id")
        greenhouse_id = kwargs.get("greenhouse_id")
        
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        if resource == "greenhouses" and id_param is None and action is None:
            return self.db.retrieve_greenhouses(username)

        if resource == "greenhouses" and id_param and action is None:
            return self.db.retrieve_greenhouse(username, id_param)

        if resource == "zones" and greenhouse_id and action is None:
            return self.db.retrieve_zones(username, greenhouse_id)

        if resource == "zones" and id_param and action is None:
            return self.db.retrieve_zone(username, id_param)

        if resource == "strategy" and id_param and action is None:
            return self.db.get_control_strategy(username, id_param)

        if resource == "devices" and id_param and action is None:
            return self.db.retrieve_devices(username, id_param)
        
        # NOTA: Ho rimosso "lookup" da qui perché MongoService richiede {username} nell'URL.
        # La logica è stata spostata in StrategyService.

        raise cherrypy.HTTPError(404)

    # POST /users/<username>/greenhouses
    @cherrypy.tools.json_in()
    @handle_adapter_errors
    def POST(self, username=None, *args, **kwargs):
        body = cherrypy.request.json
        if not username:
            if not all(k in body for k in ("username", "password", "email")):
                raise cherrypy.HTTPError(400, "Missing required fields in body")
            self.db.create_user(body["username"], body["password"], body["email"])
            cherrypy.response.status = 201
            return ""
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        if resource == "greenhouses" and action is None:
            self.db.add_greenhouse(username, body["name"])
            cherrypy.response.status = 201
            return ""

        raise cherrypy.HTTPError(404)

    # PUT /users/<username>/...
    @cherrypy.tools.json_in()
    @handle_adapter_errors
    def PUT(self, username=None, *args, **kwargs):
        if not username:
            raise cherrypy.HTTPError(404)
        # 1. Log di Debug
        print(f"DEBUG PUT -> Username: {username} | Args: {args} | Kwargs: {kwargs}", flush=True)

        body = cherrypy.request.json
        id_param = kwargs.get("id")
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        # --- LOGICA ACTIONS ---
        if resource == "zones" and action == "associate":
            if not all(k in body for k in ("greenhouse_id", "zone_id", "name")):
                raise cherrypy.HTTPError(400, "Missing required fields in body")
            
            self.db.associate_zone(username, body["greenhouse_id"], body["zone_id"], body["name"])
            return ""

        if resource == "zones" and action == "disassociate":
            self.db.disassociate_zone(username, body["zone_id"])
            return ""

        # --- LOGICA GENERICI ---
        if resource == "greenhouses" and id_param and action is None:
            self.db.rename_greenhouse(username, id_param, body["name"])
            return ""

        if resource == "zones" and id_param and action is None:
            self.db.rename_zone(username, id_param, body["name"])
            return ""

        if resource == "strategy" and id_param and action is None:
            self.db.update_control_strategy(username, id_param, body)
            return ""

        print(f"DEBUG 404 -> Resource: {resource}, Action: {action}, ID: {id_param}")
        raise cherrypy.HTTPError(404, "Nothing matches the given URI")

    # DELETE /users/<username>/greenhouses?id=...
    @handle_adapter_errors
    def DELETE(self, username=None, *args, **kwargs):
        if not username:
            raise cherrypy.HTTPError(404)
        id_param = kwargs.get("id")
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        if resource == "greenhouses" and id_param and action is None:
            self.db.delete_greenhouse(username, id_param)
            return ""

        raise cherrypy.HTTPError(404)
    

class LoginService:
    exposed = True

    def __init__(self):
        self.db = MongoDBAdapter()

    @cherrypy.tools.json_in()
    def POST(self, *args, **kwargs):
        body = cherrypy.request.json
        username = body.get("username")
        password = body.get("password")
        if not username or not password:
            raise cherrypy.HTTPError(400, "Missing required fields in body")
        if not self.db.verify_user(username, password):
            raise cherrypy.HTTPError(401, "Invalid credentials")
        return ""


class StatisticsService:
    exposed = True

    def __init__(self):
        self.db = MongoDBAdapter()

    @cherrypy.tools.json_out()
    @handle_adapter_errors
    def GET(self, *args, **kwargs):
        resource = args[0] if len(args) > 0 else None

        if resource == "zones":
            print("STAT GET args=", args, "kwargs=", kwargs, flush=True)
            return self.db.get_all_statistics_zones()

        if resource == "measurements":
            return self.db.get_all_measurements()

        raise cherrypy.HTTPError(404)


class ZoneLookupService:
    exposed = True

    def __init__(self):
        self.db = MongoDBAdapter()

    @cherrypy.tools.json_out()
    def GET(self, *args, **kwargs):
        resource = args[0] if len(args) > 0 else None
        if resource == "validate":
            zone_id = kwargs.get("zone_id")
            if not zone_id:
                raise cherrypy.HTTPError(400, "Missing zone_id")
            return {"valid": self.db.check_zone_validity(zone_id)}
        raise cherrypy.HTTPError(404)


class DeviceService:
    exposed = True

    def __init__(self):
        self.db = MongoDBAdapter()

    @cherrypy.tools.json_out()
    @handle_adapter_errors
    def GET(self, device_id, *args, **kwargs):
        resource = args[0] if len(args) > 0 else None
        if resource == "status":
            return {"status": self.db.retrieve_device_status(device_id)}
        return self.db.retrieve_device(device_id)


class StrategyService:
    exposed = True

    def __init__(self):
        self.db = MongoDBAdapter()

    @cherrypy.tools.json_out()
    @handle_adapter_errors
    def GET(self, *args, **kwargs):
        resource = args[0] if len(args) > 0 else None

        # Endpoint: GET /strategies/lookup?greenhouse_id=...&device_id=...
        if resource == "lookup":
            gh_id = kwargs.get("greenhouse_id")
            dev_id = kwargs.get("device_id")

            if not gh_id or not dev_id:
                raise cherrypy.HTTPError(400, "Missing greenhouse_id or device_id params")

            # Chiama il metodo dell'adapter
            result = self.db.get_info_from_device(gh_id, dev_id)

            if not result:
                raise cherrypy.HTTPError(404, "Device association not found")

            return result

        raise cherrypy.HTTPError(404)


if __name__ == "__main__":
    cherrypy.config.update({
        "server.socket_host": "0.0.0.0",
        "server.socket_port": 8082,
        "tools.response_headers.on": True,
        "tools.response_headers.headers": [("Content-Type", "application/json")],
    })

    cherrypy.tree.mount(
        MongoService(),
        "/users",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )

    cherrypy.tree.mount(
        ZoneLookupService(),
        "/zones",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )

    cherrypy.tree.mount(
        DeviceService(),
        "/devices",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )

    cherrypy.tree.mount(
        StatisticsService(),
        "/statistics",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )

    # Ora la classe StrategyService esiste ed è definita sopra
    cherrypy.tree.mount(
        StrategyService(),
        "/strategies",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )
    cherrypy.tree.mount(
        LoginService(),
        "/login",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )

    cherrypy.engine.start()
    cherrypy.engine.block()
