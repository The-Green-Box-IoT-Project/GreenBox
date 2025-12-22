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
    def GET(self, username, *args, **kwargs):
        # Recupera 'id' dai query params (kwargs)
        id_param = kwargs.get("id")
        
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        if resource == "greenhouses" and id_param is None and action is None:
            return self.db.retrieve_greenhouses(username)

        if resource == "greenhouses" and id_param and action is None:
            return self.db.retrieve_greenhouse(username, id_param)

        if resource == "zones" and id_param and action is None:
            return self.db.retrieve_zone(username, id_param)

        if resource == "strategy" and id_param and action is None:
            return self.db.get_control_strategy(username, id_param)

        if resource == "devices" and id_param and action is None:
            return self.db.retrieve_devices(username, id_param)

        raise cherrypy.HTTPError(404)

    # POST /users/<username>/greenhouses
    @cherrypy.tools.json_in()
    @handle_adapter_errors
    def POST(self, username, *args, **kwargs):
        body = cherrypy.request.json
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
    def PUT(self, username, *args, **kwargs):
        # 1. Log di Debug (guarda il terminale di docker dopo la richiesta)
        print(f"DEBUG PUT -> Username: {username} | Args: {args} | Kwargs: {kwargs}", flush=True)

        body = cherrypy.request.json
        # Recupera 'id' dai query params se presente (es. ?id=GH_001)
        id_param = kwargs.get("id")

        # Parsing sicuro del path
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        # --- LOGICA ACTIONS (es. /zones/associate) ---
        if resource == "zones" and action == "associate":
            # Verifica che il body abbia i campi necessari
            if not all(k in body for k in ("greenhouse_id", "zone_id", "name")):
                raise cherrypy.HTTPError(400, "Missing required fields in body")
            
            self.db.associate_zone(username, body["greenhouse_id"], body["zone_id"], body["name"])
            return ""

        if resource == "zones" and action == "disassociate":
            self.db.disassociate_zone(username, body["zone_id"])
            return ""

        # --- LOGICA GENERICI (con ?id=...) ---
        # Nota: usiamo id_param estratto da kwargs
        if resource == "greenhouses" and id_param and action is None:
            self.db.rename_greenhouse(username, id_param, body["name"])
            return ""

        if resource == "zones" and id_param and action is None:
            self.db.rename_zone(username, id_param, body["name"])
            return ""

        if resource == "strategy" and id_param and action is None:
            self.db.update_control_strategy(username, id_param, body)
            return ""

        # Se arriviamo qui, nessuna condizione è stata soddisfatta
        print(f"DEBUG 404 -> Resource: {resource}, Action: {action}, ID: {id_param}")
        raise cherrypy.HTTPError(404, "Nothing matches the given URI")

    # DELETE /users/<username>/greenhouses?id=...
    @handle_adapter_errors
    def DELETE(self, username, *args, **kwargs):
        id_param = kwargs.get("id")
        resource = args[0] if len(args) > 0 else None
        action = args[1] if len(args) > 1 else None

        if resource == "greenhouses" and id_param and action is None:
            self.db.delete_greenhouse(username, id_param)
            return ""

        raise cherrypy.HTTPError(404)


if __name__ == "__main__":
    cherrypy.config.update({
        "server.socket_host": "0.0.0.0",
        "server.socket_port": 8080,
        "tools.response_headers.on": True,
        "tools.response_headers.headers": [("Content-Type", "application/json")],
    })

    cherrypy.tree.mount(
        MongoService(),
        "/users",
        {"/": {"request.dispatch": cherrypy.dispatch.MethodDispatcher()}}
    )

    cherrypy.engine.start()
    cherrypy.engine.block()