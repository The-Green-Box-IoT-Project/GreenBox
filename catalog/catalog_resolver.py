import os
import json
import time

import cherrypy
from dotenv import load_dotenv

import catalog_interface
from catalog_dispatcher import CatalogGetRequest, CatalogPostRequest, CatalogPutRequest, CatalogDeleteRequest
from generator import generator
from pathlib import Path
from mongo_adapter import MongoAdapter

# Instanziare l'adapter Mongo (in production, passa l'URI dal config)
mongo_adapter = MongoAdapter("mongodb://localhost:27017", "greenbox")

load_dotenv()
ENV_PATH = Path(__file__).parent / '.env'   # forza la .env nella cartella del catalog
admin_token = os.getenv('ADMIN_TOKEN')
SERVICE_FILE = Path(__file__).resolve().parent / 'services' / 'services.json'


def validate_authentication(headers):
    if 'token' not in headers:
        raise cherrypy.HTTPError(status=401)
    token = headers['token']
    is_token_valid = catalog_interface.verify_token(token)
    if not is_token_valid:
        raise cherrypy.HTTPError(status=401)
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
            case CatalogGetRequest.RETRIEVE_GREENHOUSES:
                return CatalogGetResolver._retrieve_greenhouses(headers)
            case CatalogGetRequest.RETRIEVE_DEVICES:
                return CatalogGetResolver._retrieve_devices(query, headers)
            case CatalogGetRequest.GET_DEVICE_STATUS:
                return CatalogGetResolver._get_device_status(query)
            case CatalogGetRequest.GET_CROPS:
                return CatalogGetResolver._get_crops()
            case CatalogGetRequest.GET_DEVICES:
                return CatalogGetResolver._get_devices(query)
            case CatalogGetRequest.SERVICE_OVERVIEW:
                return CatalogGetResolver._service_overview(query)
            case CatalogGetRequest.SERVICE_GH_DETAIL:
                return CatalogGetResolver._service_gh_detail(query)
        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _service_overview(query):
        token = query.get('token')
        if not catalog_interface.verify_token(token):
            raise cherrypy.HTTPError(status=401, message='invalid_token')
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
    def _service_gh_detail(query):
        token = query.get('token')
        gh_id = query.get('id')
        if not gh_id:
            raise cherrypy.HTTPError(status=400, message='missing_greenhouse_id')

        if not catalog_interface.verify_token(token):
            raise cherrypy.HTTPError(status=401, message='invalid_token')
        username = catalog_interface.retrieve_username_by_token(token)
        if not catalog_interface.verify_greenhouse_ownership(gh_id, username):
            raise cherrypy.HTTPError(status=403, message='forbidden')

        try:
            with open(SERVICE_FILE, 'r') as f:
                state = json.load(f)
        except Exception:
            state = {}

        return state.get(gh_id, {"devices": {}, "last_update": None})

    @staticmethod
    def _get_devices(query):
        token = query['token']
        if not catalog_interface.verify_token(token):
            raise cherrypy.HTTPError(status=401, message='invalid_token')
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
    def _retrieve_greenhouses(query):
        token = query['token']
        username = catalog_interface.retrieve_username_by_token(token)
        
        # Chiamata al MongoDB Adapter per recuperare le serre dell'utente
        greenhouses = mongo_adapter.retrieve_greenhouses(username)
        
        response = {
            'greenhouses': greenhouses
        }
        return response

    @staticmethod
    def _retrieve_devices(query):
        token = query['token']
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
                response = CatalogPostResolver._set_crop(query)
        return response

    @staticmethod
    def _set_crop(query):
        """
        path: greenhouse/crop
        query: greenhouse_id, crop, token
        """
        token = query.get('token')
        if not catalog_interface.verify_token(token):
            raise cherrypy.HTTPError(status=401, message='invalid_token')
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('greenhouse_id')
        crop = query.get('crop')

        strat, err = catalog_interface.set_crop_for_greenhouse(gh_id, crop, username)
        if err:
            if err in ('greenhouse_not_available','crop_not_found','strategy_not_found'):
                raise cherrypy.HTTPError(status=404, message=err)
            raise cherrypy.HTTPError(status=400, message=err)

        return {"msg": "crop_set", "greenhouse_id": gh_id, "strategy": strat}

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
                response = CatalogPutResolver._update_strategy(query)

    @staticmethod
    def _update_device_status(query):
        """
        Update current operational status of a device (runtime).
        path: device/status
        query: device_id, status, token
        """
        token = query['token']
        device_id = query['device_id']
        new_status = query['status']

        if not catalog_interface.verify_token(token):
            raise cherrypy.HTTPError(status=401, message='invalid_token')

        # Recupera anagrafica (greenhouse, role) da devices.json
        gh_id = catalog_interface.retrieve_device_association(device_id)
        if not gh_id:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        # serve anche il "kind": inferiamolo dal device_type
        # (sensor / actuator / controller). Se non hai una mappa,
        # puoi dedurlo da role o device_type:
        from pathlib import Path
        base = Path(__file__).parent
        with open(base / 'generator' / 'devices.json') as f:
            devices_all = json.load(f)
        d = devices_all.get(device_id)
        if not d:
            raise cherrypy.HTTPError(status=404, message='device_not_found')

        role = d.get('role')
        dtype = (d.get('device_type') or '').lower()  # 'controller' | 'sensor' | 'actuator'
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


    @staticmethod
    def _update_strategy(query):
        """
        path: strategy
        query: greenhouse_id, update, token
        dove 'update' è una stringa JSON, es:
        {"targets":{"temperature":{"min":21,"max":27}},
         "controls":{"ventilation_system":{"hysteresis":1.2}}}
        """
        token = query.get('token')
        if not catalog_interface.verify_token(token):
            raise cherrypy.HTTPError(status=401, message='invalid_token')
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


    @staticmethod
    def _associate_greenhouse(query, headers):
        """
        Called by a user that wants to add a new greenhouse.
        path: associate/greenhouse
        query: greenhouse_id, greenhouse_name
        auth: token
        """
        token = validate_authentication(headers)
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
        token = validate_authentication(headers)
        username = catalog_interface.retrieve_username_by_token(token)
        device_id = query['device_id']
        greenhouse_id = query['greenhouse_id']

        # Verifica se il dispositivo esiste e se la serra è registrata
        if not mongo_adapter.verify_device_existence(device_id):
            raise cherrypy.HTTPError(status=404, message='device_not_available')
        if not mongo_adapter.verify_greenhouse_existence(greenhouse_id):
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')

        # Associa il dispositivo alla serra
        success = mongo_adapter.associate_device_with_greenhouse(device_id, greenhouse_id)
        if not success:
            raise cherrypy.HTTPError(status=400, message="failed_to_associate_device")
        
        return {'status': 'success', 'message': f"Device {device_id} associated to greenhouse {greenhouse_id}"}

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