import os
import json
import time
import copy

import cherrypy
from dotenv import load_dotenv

from . import catalog_interface
from .catalog_dispatcher import CatalogGetRequest, CatalogPostRequest, CatalogPutRequest, CatalogDeleteRequest
from .generator import generator
from pathlib import Path
from Adapters.mongo.Mongo_DB_adapter import MongoAdapter

# Instanzia l'adapter Mongo usando le variabili d'ambiente per supportare ambienti containerizzati
MONGO_URI = os.getenv("CATALOG_MONGO_URI", os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
MONGO_DB = os.getenv("CATALOG_MONGO_DB", os.getenv("MONGO_DB", "greenbox"))
mongo_adapter = MongoAdapter(MONGO_URI, MONGO_DB)

load_dotenv()
ENV_PATH = Path(__file__).parent / '.env'   # forza la .env nella cartella del catalog
admin_token = os.getenv('ADMIN_TOKEN')
SERVICE_FILE = Path(__file__).resolve().parent / 'services' / 'services.json'
ROOT_DIR = Path(__file__).resolve().parents[1]
TELEMETRY_FILE = Path(__file__).resolve().parent / 'services' / 'telemetry.json'
ALLOWED_METRICS = {"temperature", "humidity", "light", "soil_humidity", "pH", "ph"}
ALLOWED_RANGES = {"1h", "6h", "1d", "7d", "1m", "3m", "1y"}
DEFAULT_THRESHOLDS = {
    "temperature": {"lower": 18.0, "upper": 26.0, "deadband": 0.5},
    "humidity": {"lower": 60.0, "upper": 80.0, "deadband": 2.0},
    "light": {"lower": 5000, "upper": 15000, "deadband": 50},
    "soil_humidity": {"lower": 70.0, "upper": 90.0, "deadband": 2.0},
    "pH": {"lower": 5.8, "upper": 6.5, "deadband": 0.2}
}
DEFAULT_EFFECTS = [
    {"system": "ventilation_system", "level": "50%", "temperature": -0.0083, "humidity": -0.0833},
    {"system": "ventilation_system", "level": "100%", "temperature": -0.0167, "humidity": -0.1667},
    {"system": "heating_system", "level": "100%", "temperature": 0.0167, "humidity": 0.0833, "soil_humidity": -0.00333},
    {"system": "illumination_system", "level": "100%", "light": 500.0, "temperature": 0.00008}
]


def validate_authentication(headers, query=None):
    """
    Enforce token-based authentication. Looks for a token in headers,
    optionally falling back to query params.
    """
    token = (headers or {}).get('token')
    if token is None and query is not None:
        token = query.get('token')
    if token is None:
        raise cherrypy.HTTPError(status=401, message='missing_token')
    if not catalog_interface.verify_token(token):
        raise cherrypy.HTTPError(status=401, message='invalid_token')
    return token


def admin_authentication(headers):
    if 'token' not in headers:
        raise cherrypy.HTTPError(status=401)
    token = headers['token']
    is_token_valid = token == admin_token
    if not is_token_valid:
        raise cherrypy.HTTPError(status=401)


class CatalogGetResolver:
    @staticmethod
    def resolve(request: CatalogGetRequest, query, headers):
        match request:
            case CatalogGetRequest.RETRIEVE_BROKER:
                return CatalogGetResolver._retrieve_broker(query, headers)
            case CatalogGetRequest.GENERATE_ID:
                return CatalogGetResolver._generate_id(query, headers)
            case CatalogGetRequest.DEVICE_JOIN:
                return CatalogGetResolver._device_join(query, headers)
            case CatalogGetRequest.DEVICE_CONFIG:
                return CatalogGetResolver._device_config(query)
            case CatalogGetRequest.REGISTER_NEW_GREENHOUSE:
                return CatalogPostResolver._register_new_greenhouse(query, headers)
            case CatalogGetRequest.REGISTER_NEW_DEVICE:
                return CatalogPostResolver._register_new_device(query, headers)
            case CatalogGetRequest.RETRIEVE_GREENHOUSES:
                return CatalogGetResolver._retrieve_greenhouses(query, headers)
            case CatalogGetRequest.RETRIEVE_DEVICES:
                return CatalogGetResolver._retrieve_devices(query, headers)
            case CatalogGetRequest.GET_DEVICE_STATUS:
                return CatalogGetResolver._get_device_status(query)
            case CatalogGetRequest.GET_CROPS:
                return CatalogGetResolver._get_crops()
            case CatalogGetRequest.GET_DEVICES:
                return CatalogGetResolver._get_devices(query, headers)
            case CatalogGetRequest.GREENHOUSE_THRESHOLDS:
                return CatalogGetResolver._greenhouse_thresholds(query)
            case CatalogGetRequest.GREENHOUSE_EFFECTS:
                return CatalogGetResolver._greenhouse_effects(query)
            case CatalogGetRequest.USER_INFO:
                return CatalogGetResolver._user_info(query, headers)
            case CatalogGetRequest.ACTUATOR_INFO:
                return CatalogGetResolver._actuator_info(query, headers)
            case CatalogGetRequest.MEASURES:
                return CatalogGetResolver._measures(query, headers)
            case CatalogGetRequest.SERVICE_OVERVIEW:
                return CatalogGetResolver._service_overview(query, headers)
            case CatalogGetRequest.SERVICE_GH_DETAIL:
                return CatalogGetResolver._service_gh_detail(query, headers)
            case CatalogGetRequest.SERVICE_OVERVIEW:
                return CatalogGetResolver._service_overview(query, headers)
            case CatalogGetRequest.SERVICE_GH_DETAIL:
                return CatalogGetResolver._service_gh_detail(query, headers)

        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _service_overview(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        user_ghs = set(catalog_interface.retrieve_greenhouses(username))

        # carica cache
        try:
            with open(SERVICE_FILE, 'r') as f:
                state = json.load(f)
        except Exception:
            state = {}

        # filtra per greenhouses dell'utente
        out = {gh: v for gh, v in state.items() if gh in user_ghs}
        return {"greenhouses": out}

    @staticmethod
    def _service_gh_detail(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('id')
        if not gh_id:
            raise cherrypy.HTTPError(status=400, message='missing_greenhouse_id')
        if not catalog_interface.verify_greenhouse_ownership(gh_id, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')

        try:
            with open(SERVICE_FILE, 'r') as f:
                state = json.load(f)
        except Exception:
            state = {}

        return state.get(gh_id, {"devices": {}, "last_update": None})

    @staticmethod
    def _get_devices(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        


        gh_id = query['greenhouse_id']
        if (not catalog_interface.verify_greenhouse_existence(gh_id) or
                not catalog_interface.verify_greenhouse_ownership(gh_id, username)):
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')

        base = Path(__file__).parent

        # carica anagrafica
        with open(base / 'generator' / 'devices.json') as f:
            devices_all = json.load(f)

        # carica runtime
        try:
            with open(base / 'services' / 'services.json') as f:
                services_state = json.load(f)
            runtime_devices = (services_state.get(gh_id, {}) or {}).get("devices", {})
        except Exception:
            runtime_devices = {}

        # fondi le due sorgenti
        items = []
        for did, d in devices_all.items():
            if d.get("greenhouse_id") == gh_id:
                runtime_status = runtime_devices.get(did, {}).get("status")
                status = runtime_status or d.get("status", "unknown")
                items.append({
                    "device_id": did,
                    "name": d.get("name"),
                    "device_model": d.get("device_model"),
                    "device_type": d.get("device_type"),
                    "role": d.get("role"),
                    "status": status
                })
        return {"greenhouse_id": gh_id, "devices": items}

    @staticmethod
    def _get_crops():
        data = catalog_interface.list_crops()
        # restituisco chiave + label per la UI
        out = [{"id": k, "label": v.get("label", k)} for k, v in data.items()]
        return {"crops": out}

    @staticmethod
    def _get_device_status(query):
        """
        Retrieve current runtime status of a device (from services/services.json).
        path: device/status
        query: device_id
        """
        device_id = query['device_id']

        # Prova a leggere dal services catalog (runtime)
        try:
            with open(SERVICE_FILE, 'r') as f:
                state = json.load(f)
        except Exception:
            state = {}

        # cerca il device scorrendo le serre
        for gh_id, gh in state.items():
            devs = gh.get("devices", {})
            if device_id in devs:
                status = devs[device_id].get("status", "unknown")
                return {'device_id': device_id, 'status': status, 'greenhouse_id': gh_id}

        # fallback: unknown se non presente nel runtime
        return {'device_id': device_id, 'status': 'unknown'}

    @staticmethod
    def _retrieve_broker(query, headers):
        """
        Called to retrieve ip and port of the broker.
        path: broker
        query: -
        auth: -
        """
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        response = {
            'broker_ip': broker_ip,
            'broker_port': broker_port
        }
        return response

    @staticmethod
    def _generate_id(query, headers):
        """
        Called by the organization to generate a new unique id to be
        assigned to a device or a greenhouse that will be distributed.
        path: generate_id
        query: -
        auth: admin token
        """
        admin_authentication(headers)
        generated_id = generator.generate_id()
        response = {'generated_id': generated_id}
        return response

    @staticmethod
    def _device_join(query, headers):
        """
        Called by a device (Raspberry, actuator, etc...) to join
        the catalog and obtain its resource catalog (i.e. id of the
        greenhouse it is associated with). When called before the user
        has successfully registered the device, it does not return
        anything useful.
        path: device_join
        query: device_id
        auth: -
        """
        device_id = query['device_id']
        if not catalog_interface.verify_device_existence(device_id):
            raise cherrypy.HTTPError(status=404)
        if catalog_interface.is_device_available(device_id):
            raise cherrypy.HTTPError(status=404, message='device_not_associated')
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        return {
            'broker_ip': broker_ip,
            'broker_port': broker_port,
            'greenhouse_id': catalog_interface.retrieve_device_association(device_id)
        }
    @staticmethod
    def _device_config(query):
        device_id = query.get('device_id')
        if not device_id:
            raise cherrypy.HTTPError(status=400, message='missing_device_id')

        device = mongo_adapter.retrieve_device(device_id)
        if not device:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        greenhouse_id = device.get('greenhouse_id') or catalog_interface.retrieve_device_association(device_id)
        if not greenhouse_id:
            raise cherrypy.HTTPError(status=404, message='device_not_associated')

        broker_ip, broker_port = catalog_interface.retrieve_broker()
        response = {
            'device_id': device_id,
            'greenhouse_id': greenhouse_id,
            'broker_ip': broker_ip,
            'broker_port': broker_port,
            'device_type': device.get('device_type'),
            'role': device.get('role')
        }
        return response

    @staticmethod
    def _greenhouse_thresholds(query):
        greenhouse_id = query.get('greenhouse_id')
        if not greenhouse_id:
            raise cherrypy.HTTPError(status=400, message='missing_greenhouse_id')

        greenhouse = mongo_adapter.retrieve_greenhouse(greenhouse_id)
        if not greenhouse:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_found')

        thresholds = greenhouse.get('thresholds') or {}
        merged = copy.deepcopy(DEFAULT_THRESHOLDS)
        merged.update(thresholds)
        return {'greenhouse_id': greenhouse_id, 'thresholds': merged}

    @staticmethod
    def _greenhouse_effects(query):
        greenhouse_id = query.get('greenhouse_id')
        if not greenhouse_id:
            raise cherrypy.HTTPError(status=400, message='missing_greenhouse_id')

        greenhouse_exists = mongo_adapter.verify_greenhouse_existence(greenhouse_id)
        if not greenhouse_exists:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_found')

        effects = mongo_adapter.retrieve_greenhouse_effects(greenhouse_id)
        if not effects:
            effects = copy.deepcopy(DEFAULT_EFFECTS)

        return {'greenhouse_id': greenhouse_id, 'effects': effects}

    @staticmethod
    def _user_info(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)

        # prefer Mongo user profile, fallback to users.json
        user = mongo_adapter.retrieve_user(username) or {}
        if not user:
            try:
                with open(catalog_interface.USERS_FILE, 'r') as f:
                    users = json.load(f)
                user = users.get(username, {})
            except Exception:
                user = {}

        country = user.get('country') or user.get('paese')
        account_level = user.get('account_level')
        response = {
            "username": username,
            "country": country,
            "account_level": account_level
        }
        return response

    @staticmethod
    def _actuator_info(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        device_id = query.get('device_id')
        if not device_id:
            raise cherrypy.HTTPError(status=400, message='missing_device_id')

        device = mongo_adapter.retrieve_device(device_id)
        if not device:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        # ownership via greenhouse
        gh_id = device.get('greenhouse_id')
        if gh_id and not catalog_interface.verify_greenhouse_ownership(gh_id, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')

        dtype = (device.get('device_type') or '').lower()
        role = (device.get('role') or '').lower()
        is_actuator = dtype == 'actuator' or role.endswith('_system')
        if not is_actuator:
            raise cherrypy.HTTPError(status=400, message='not_actuator')

        # strategy id: usa strategia della serra se presente
        strategy_id = None
        try:
            with open(catalog_interface.STRATEGIES_FILE, 'r') as f:
                strategies = json.load(f)
            if gh_id in strategies:
                strategy_id = gh_id
        except Exception:
            strategy_id = gh_id

        info = {
            "device_id": device_id,
            "name": device.get('name'),
            "device_type": device.get('device_type'),
            "role": device.get('role'),
            "greenhouse_id": gh_id,
            "strategy_id": strategy_id,
            "bound_device_id": device.get('bound_device_id') or device.get('bound_to')
        }
        return info

    @staticmethod
    def _measures(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)

        device_id = query.get('device_id')
        metric = query.get('metric')
        time_range = query.get('range')

        if not device_id or not metric or not time_range:
            raise cherrypy.HTTPError(status=400, message='missing_fields')

        device = mongo_adapter.retrieve_device(device_id)
        if not device:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        gh_id = device.get('greenhouse_id')
        if gh_id and not catalog_interface.verify_greenhouse_ownership(gh_id, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')

        dtype = (device.get('device_type') or '').lower()
        role = (device.get('role') or '').lower()
        is_controller = dtype == 'controller' or role == 'controller' or 'raspberry' in dtype
        if not is_controller:
            raise cherrypy.HTTPError(status=400, message='not_controller_device')

        metric_norm = metric.lower()
        metric_key = 'pH' if metric.lower() in ('ph', 'pH') else metric_norm
        if metric_norm not in {m.lower() for m in ALLOWED_METRICS}:
            raise cherrypy.HTTPError(status=400, message='invalid_metric')
        if time_range not in ALLOWED_RANGES:
            raise cherrypy.HTTPError(status=400, message='invalid_range')

        # Load telemetry from Mongo (preferred) or local file fallback
        points = mongo_adapter.retrieve_telemetry(device_id, metric_key, time_range) or []
        if not points:
            try:
                with open(TELEMETRY_FILE, 'r') as f:
                    telemetry = json.load(f)
                points = telemetry.get(device_id, {}).get(metric_key, {}).get(time_range, [])
            except FileNotFoundError:
                points = []
            except Exception:
                points = []

        # Limit to 60 points as richiesto
        points = points[-60:]

        return {
            "device_id": device_id,
            "metric": metric_key,
            "range": time_range,
            "points": points
        }
    @staticmethod
    def _retrieve_greenhouses(query, headers=None):
        token = validate_authentication(headers or {}, query)
        username = catalog_interface.retrieve_username_by_token(token)
        # greenhouses = catalog_interface.retrieve_greenhouses(username)
        # Chiamata al MongoDB Adapter per recuperare le serre dell'utente
        greenhouses = catalog_interface.retrieve_greenhouses_from_mongo(username)
        
        response = {
            'greenhouses': greenhouses
        }
        return response

    @staticmethod
    def _retrieve_devices(query, headers=None):
        token = validate_authentication(headers or {}, query)
        greenhouse_id = query['greenhouse_id']
        username = catalog_interface.retrieve_username_by_token(token)
        
        # Verifica la proprietà della serra (Mongo)
        if not mongo_adapter.verify_greenhouse_ownership(greenhouse_id, username):
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')
        
        # Chiamata al MongoDB Adapter per recuperare i dispositivi
        devices = mongo_adapter.retrieve_devices_in_greenhouse(greenhouse_id)
        
        response = {'devices': devices}
        return response


class CatalogPostResolver:
    @staticmethod
    def resolve(request: CatalogPostRequest, query, body, headers):
        response = None
        match request:
            case CatalogPostRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=400)
            case CatalogPostRequest.REGISTER_NEW_GREENHOUSE:
                response = CatalogPostResolver._register_new_greenhouse(query, headers)
            case CatalogPostRequest.REGISTER_NEW_DEVICE:
                response = CatalogPostResolver._register_new_device(query, headers)
            case CatalogPostRequest.SIGN_UP:
                response = CatalogPostResolver._sign_up(body)
            case CatalogPostRequest.LOGIN:
                response = CatalogPostResolver._login(body)
            case CatalogPostRequest.TOKEN_LOGIN:
                response = CatalogPostResolver._token_login(query)
            case CatalogPostRequest.SET_CROP:
                response = CatalogPostResolver._set_crop(query, headers)
            case CatalogPostRequest.CREATE_GREENHOUSE:
                response = CatalogPostResolver._create_greenhouse(query, body, headers)
            case CatalogGetRequest.SERVICE_OVERVIEW:
                return CatalogGetResolver._service_overview(query, headers)
            case CatalogGetRequest.SERVICE_GH_DETAIL:
                return CatalogGetResolver._service_gh_detail(query, headers)

                
        return response
    

    @staticmethod
    def _set_crop(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('greenhouse_id')
        crop = query.get('crop')
        strat, err = catalog_interface.set_crop_for_greenhouse(gh_id, crop, username)
        if err:
            if err in ('greenhouse_not_available', 'crop_not_found', 'strategy_not_found'):
                raise cherrypy.HTTPError(status=404, message=err)
            raise cherrypy.HTTPError(status=400, message=err)
        return {"msg": "crop_set", "greenhouse_id": gh_id, "strategy": strat}
    
    @staticmethod
    #def _set_crop(query):
    #    """
    #    path: greenhouse/crop
    #    query: greenhouse_id, crop, token
    #    """
    #    token = query.get('token')
    #    if not catalog_interface.verify_token(token):
    #        raise cherrypy.HTTPError(status=401, message='invalid_token')
    #    username = catalog_interface.retrieve_username_by_token(token)
    #    gh_id = query.get('greenhouse_id')
    #    crop = query.get('crop')

    #    strat, err = catalog_interface.set_crop_for_greenhouse(gh_id, crop, username)
    #    if err:
    #        if err in ('greenhouse_not_available','crop_not_found','strategy_not_found'):
    #            raise cherrypy.HTTPError(status=404, message=err)
    #        raise cherrypy.HTTPError(status=400, message=err)

    #    return {"msg": "crop_set", "greenhouse_id": gh_id, "strategy": strat}

    @staticmethod
    def _token_login(query):
        """
        Called by a user that wants to log into the system using a previous
        session token. Its set of resources will be given to it.
        path: login
        query: token
        """
        token = query['token']
        is_token_valid = catalog_interface.verify_token(token)
        if is_token_valid:
            username = catalog_interface.retrieve_username_by_token(token)
            greenhouses = catalog_interface.retrieve_greenhouses(username)
        else:
            greenhouses = None
        response = {
            'token': token,
            'valid': is_token_valid,
            'greenhouses': greenhouses
        }
        return response

    @staticmethod
    def _register_new_greenhouse(query, headers):
        """
        Called by the organization to register an id associated to
        a greenhouse that will be distributed. It is supposed that the
        greenhouse is ready to be delivered.
        path: register/greenhouse
        query: greenhouse_id
        auth: admin token
        """
        admin_authentication(headers)
        greenhouse_id = query['greenhouse_id']
        generator.register_greenhouse(greenhouse_id)
        response = {'greenhouse_id': greenhouse_id}
        return response

    @staticmethod
    def _register_new_device(query, headers):
        """
        Called by the organization to register an id associated to
        a device that will be distributed. It is supposed that the
        device is ready to be delivered.
        path: register/device
        query: device_id, device_type
        auth: admin token
        """
        admin_authentication(headers)
        device_id = query['device_id']
        device_type = query['device_type']
        generator.register_device(device_id, device_type)
        response = {'device_id': device_id, 'device_type': device_type}
        return response

    @staticmethod
    def _sign_up(body):
        """
        Called by a user that wants to be registered on the system.
        path: signup
        query: -
        body: username, password
        auth: -
        """
        if not {'username', 'password'}.issubset(body):
            raise cherrypy.HTTPError(status=400, message='missing_fields')
        username = body['username']
        password = body['password']
        if not catalog_interface.signup_user(username, password):
            raise cherrypy.HTTPError(status=403, message='username_taken')
        token = catalog_interface.validate_login(username, password)
        response = {'token': token}
        return response

    @staticmethod
    def _create_greenhouse(query, body, headers):
        """
        path: greenhouses
        body: name
        auth: token
        """
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        name = (body or {}).get('name') or query.get('name')
        if not name:
            raise cherrypy.HTTPError(status=400, message='missing_name')

        # Unique name per user
        if mongo_adapter.greenhouse_name_exists(name, username):
            raise cherrypy.HTTPError(status=409, message='greenhouse_name_taken')

        greenhouse_id = query.get('greenhouse_id') or generator.generate_id()
        payload = {
            "greenhouse_id": greenhouse_id,
            "name": name,
            "tenant_id": username,
            "devices": [],
            "created_at": time.time(),
            "updated_at": time.time()
        }
        created = mongo_adapter.create_greenhouse(payload)
        if not created:
            raise cherrypy.HTTPError(status=409, message='greenhouse_id_taken')

        # Optional: update legacy users.json structure if present
        try:
            with open(catalog_interface.USERS_FILE, 'r') as f:
                users = json.load(f)
            user_entry = users.get(username)
            if user_entry is not None:
                gh_list = user_entry.get('greenhouses')
                if isinstance(gh_list, list):
                    gh_list.append(greenhouse_id)
                elif isinstance(gh_list, dict):
                    # normalize if legacy structure uses list of dicts
                    pass
                users[username] = user_entry
                with open(catalog_interface.USERS_FILE, 'w') as f:
                    json.dump(users, f, indent=2)
        except Exception:
            pass

        return {"greenhouse_id": greenhouse_id, "name": name}

    @staticmethod
    def _login(body):
        """
        Called by a user that wants to log into the system opening a new
        session. A new session (and so a new token) is initialized and
        its set of greenhouses will be given to the user.
        path: login
        query: -
        body: username, password
        auth: -
        """
        if not {'username', 'password'}.issubset(body):
            raise cherrypy.HTTPError(status=400, message='missing_fields')
        username = body['username']
        password = body['password']
        token = catalog_interface.validate_login(username, password)
        is_token_valid = catalog_interface.verify_token(token)
        if not is_token_valid:
            raise cherrypy.HTTPError(status=401, message='invalid_combination')
        response = {
            'token': token
        }
        return response


class CatalogPutResolver:
    @staticmethod
    def resolve(request: CatalogPutRequest, query, body, headers):
        response = None
        match request:
            case CatalogPutRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogPutRequest.ASSOCIATE_GREENHOUSE:
                response = CatalogPutResolver._associate_greenhouse(query, headers)
            case CatalogPutRequest.ASSOCIATE_DEVICE:
                response = CatalogPutResolver._associate_device(query, headers)
            case CatalogPutRequest.UPDATE_DEVICE_STATUS:
                response = CatalogPutResolver._update_device_status(query)
            case CatalogPutRequest.UPDATE_STRATEGY:
                response = CatalogPutResolver._update_strategy(query, headers)
            case CatalogPostRequest.SET_CROP:
                response = CatalogPostResolver._set_crop(query, headers)
            case CatalogPutRequest.ACTUATOR_BIND:
                response = CatalogPutResolver._actuator_bind(query, headers)
        return response

    @staticmethod
    def _update_device_status(query):
        """
        Update current operational status of a device (runtime).
        path: device/status
        query: device_id, status, token
        """
        token = validate_authentication({}, query)
        device_id = query['device_id']
        new_status = query['status']

        # Recupera anagrafica (greenhouse, role) da devices.json
        gh_id = catalog_interface.retrieve_device_association(device_id)
        if not gh_id:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        # Recupera i metadati del device per determinare role/kind.
        device_doc = mongo_adapter.retrieve_device(device_id) or {}

        # Fallback legacy al catalogo statico se necessario.
        if not device_doc:
            from pathlib import Path
            base = Path(__file__).parent
            try:
                with open(base / 'generator' / 'devices.json') as f:
                    devices_all = json.load(f)
                device_doc = devices_all.get(device_id, {})
            except FileNotFoundError:
                device_doc = {}

        if not device_doc:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        role = device_doc.get('role')
        dtype = (device_doc.get('device_type') or '').lower()
        if dtype == 'controller' or role == 'controller':
            kind = 'controller'
        elif dtype == 'actuator' or (role and role.endswith('_system')):
            kind = 'actuator'
        else:
            kind = 'sensor'

        # aggiorna SOLO il runtime status (services.json)
        CatalogPutResolver._update_service_catalog_status(gh_id, device_id, kind, role, new_status)

        return {'msg': 'status_updated', 'device_id': device_id, 'status': new_status, 'greenhouse_id': gh_id}

        return response

    @staticmethod
    def _update_service_catalog_status(greenhouse_id, device_id, kind, role, new_status):
        try:
            with open(SERVICE_FILE, 'r') as f:
                state = json.load(f)
        except Exception:
            state = {}

        gh = state.setdefault(greenhouse_id, {"last_update": 0, "devices": {}})
        dev = gh["devices"].setdefault(device_id, {"kind": kind, "role": role, "status": None, "last_seen": 0})
        dev["status"] = new_status
        dev["last_seen"] = time.time()
        gh["last_update"] = dev["last_seen"]

        with open(SERVICE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

    #new version update_strategy
    @staticmethod
    def _update_strategy(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('greenhouse_id')
        raw = query.get('update')
        try:
            update = json.loads(raw)
        except Exception:
            raise cherrypy.HTTPError(status=400, message='invalid_update_json')

        strat, err = catalog_interface.update_strategy(gh_id, username, update)
        if err:
            code = 404 if err in ('greenhouse_not_available', 'strategy_not_found') or err.startswith(
                'role_not_available') else 400
            raise cherrypy.HTTPError(status=code, message=err)
        return {"msg": "strategy_updated", "greenhouse_id": gh_id, "strategy": strat}

    #@staticmethod
    #def _update_strategy(query):
     #   """
      #  path: strategy
      #  query: greenhouse_id, update, token
      #  dove 'update' è una stringa JSON, es:
      #  {"targets":{"temperature":{"min":21,"max":27}},
       #  "controls":{"ventilation_system":{"hysteresis":1.2}}}
       # """
       # token = query.get('token')
       # if not catalog_interface.verify_token(token):
       #     raise cherrypy.HTTPError(status=401, message='invalid_token')
       # username = catalog_interface.retrieve_username_by_token(token)

     #   gh_id = query.get('greenhouse_id')
     #   raw = query.get('update')
     #   try:
      #      update = json.loads(raw)
      #  except Exception:
      #      raise cherrypy.HTTPError(status=400, message='invalid_update_json')

      #  strat, err = catalog_interface.update_strategy(gh_id, username, update)
     #   if err:
     #       code = 404 if err in ('greenhouse_not_available', 'strategy_not_found') or err.startswith(
     #           'role_not_available') else 400
     #       raise cherrypy.HTTPError(status=code, message=err)

      #  return {"msg": "strategy_updated", "greenhouse_id": gh_id, "strategy": strat}

    @staticmethod
    def _associate_greenhouse(query, headers):
        """
        Called by a user that wants to add a new greenhouse.
        path: associate/greenhouse
        query: greenhouse_id, greenhouse_name
        auth: token
        """
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        greenhouse_id = query['greenhouse_id']
        greenhouse_name = query['greenhouse_name']
        # Greenhouse registration verification
        is_greenhouse_registered = catalog_interface.verify_greenhouse_existence(greenhouse_id)
        if not is_greenhouse_registered:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')
        # Greenhouse ownership verification
        is_greenhouse_owned = catalog_interface.verify_greenhouse_ownership(greenhouse_id, username)
        if is_greenhouse_owned:
            raise cherrypy.HTTPError(status=403, message='greenhouse_already_associated')
        # Greenhouse availability verification
        is_greenhouse_available = catalog_interface.is_greenhouse_available(greenhouse_id)
        if not is_greenhouse_available:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')
        # Greenhouse association
        catalog_interface.associate_greenhouse(greenhouse_id, greenhouse_name, username)

    @staticmethod
    def _associate_device(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        device_id = query['device_id']
        greenhouse_id = query['greenhouse_id']
        device_name = query.get('device_name')

        # Verifica se il dispositivo esiste e se la serra è registrata
        if not mongo_adapter.verify_device_existence(device_id):
            raise cherrypy.HTTPError(status=404, message='device_not_available')
        if not mongo_adapter.verify_greenhouse_existence(greenhouse_id):
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')

        # Check ownership
        if not mongo_adapter.verify_greenhouse_ownership(greenhouse_id, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')

        # Check not already associated
        dev_doc = mongo_adapter.retrieve_device(device_id)
        if dev_doc.get('greenhouse_id') or dev_doc.get('associated_greenhouse'):
            raise cherrypy.HTTPError(status=409, message='device_already_associated')

        # Unique name in greenhouse
        if device_name and mongo_adapter.device_name_exists_in_greenhouse(device_name, greenhouse_id):
            raise cherrypy.HTTPError(status=409, message='device_name_taken')

        # Associa il dispositivo alla serra
        success = mongo_adapter.associate_device_with_greenhouse(device_id, greenhouse_id, device_name)
        if not success:
            raise cherrypy.HTTPError(status=400, message="failed_to_associate_device")
        
        return {'status': 'success', 'message': f"Device {device_id} associated to greenhouse {greenhouse_id}"}

    @staticmethod
    def _actuator_bind(query, headers):
        """
        path: actuators/{id}/bind
        query: raspberry_id
        """
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)

        actuator_id = query.get('actuator_id')
        raspberry_id = query.get('raspberry_id')
        if not actuator_id or not raspberry_id:
            raise cherrypy.HTTPError(status=400, message='missing_fields')

        actuator = mongo_adapter.retrieve_device(actuator_id)
        controller = mongo_adapter.retrieve_device(raspberry_id)
        if not actuator or not controller:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        # ownership check via greenhouse
        act_gh = actuator.get('greenhouse_id')
        ctrl_gh = controller.get('greenhouse_id')
        if act_gh and not catalog_interface.verify_greenhouse_ownership(act_gh, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if ctrl_gh and not catalog_interface.verify_greenhouse_ownership(ctrl_gh, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if act_gh and ctrl_gh and act_gh != ctrl_gh:
            raise cherrypy.HTTPError(status=400, message='greenhouse_mismatch')

        act_type = (actuator.get('device_type') or '').lower()
        act_role = (actuator.get('role') or '').lower()
        is_actuator = act_type == 'actuator' or act_role.endswith('_system')
        if not is_actuator:
            raise cherrypy.HTTPError(status=400, message='not_actuator')

        ctrl_type = (controller.get('device_type') or '').lower()
        ctrl_role = (controller.get('role') or '').lower()
        is_controller = ctrl_type == 'controller' or ctrl_role == 'controller' or 'raspberry' in ctrl_type
        if not is_controller:
            raise cherrypy.HTTPError(status=400, message='not_controller_device')

        ok = mongo_adapter.bind_actuator_to_device(actuator_id, raspberry_id)
        if not ok:
            raise cherrypy.HTTPError(status=400, message='bind_failed')

        return {"msg": "bind_ok", "actuator_id": actuator_id, "raspberry_id": raspberry_id}

class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogDeleteRequest, query, headers):
        pass
class CatalogInterface:
    def verify_device_existence(self, device_id: str) -> bool:
        device = mongo_adapter.retrieve_device(device_id)
        return bool(device)  # Restituisce True se il dispositivo esiste
def verify_greenhouse_existence(self, greenhouse_id: str) -> bool:
        greenhouse = mongo_adapter.retrieve_greenhouse(greenhouse_id)
        return bool(greenhouse)  # Restituisce True se la serra esiste
