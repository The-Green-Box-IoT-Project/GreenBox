import json
import cherrypy
from . import catalog_interface
from .catalog_dispatcher import CatalogGetRequest, CatalogPostRequest, CatalogPutRequest, CatalogDeleteRequest


def _normalize_strategy_payload(payload: dict) -> dict:
    """Normalize different strategy shapes to {metric: {min, max}}.

    Accepts either:
      - nested: {"temperature": {"min": 18, "max": 26}, ...}
      - flat legacy: {"min_temperature": 18, "max_temperature": 26, ...}
      - scalar legacy (kept as-is): {"temperature": 10, ...}
    """
    if not isinstance(payload, dict):
        return {}

    # If it already looks nested, keep it.
    nested_like = True
    for _, v in payload.items():
        if isinstance(v, dict):
            continue
        nested_like = False
        break
    if nested_like and payload:
        return payload

    # Convert flat min_*/max_* keys.
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
            # Scalar legacy: store as-is.
            normalized[k] = v
    return normalized

def validate_authentication(headers, query=None):
    token = (headers or {}).get('token')
    if token is None and query is not None:
        token = query.get('token')
    if token is None:
        raise cherrypy.HTTPError(status=401, message='missing_token')
    if not catalog_interface.verify_token(token):
        raise cherrypy.HTTPError(status=401, message='invalid_token')
    return token

class CatalogGetResolver:
    @staticmethod
    def resolve(request: CatalogGetRequest, query, headers):
        match request:
            case CatalogGetRequest.RETRIEVE_BROKER:
                return CatalogGetResolver._retrieve_broker()
            case CatalogGetRequest.USER_INFO:
                return CatalogGetResolver._user_info(query, headers)
            case CatalogGetRequest.RETRIEVE_GREENHOUSES:
                return CatalogGetResolver._retrieve_greenhouses(query, headers)
            case CatalogGetRequest.RETRIEVE_ZONES:
                return CatalogGetResolver._retrieve_zones(query, headers)
            case CatalogGetRequest.RETRIEVE_CONTROL_STRATEGY:
                return CatalogGetResolver._retrieve_control_strategy(query, headers)
            case CatalogGetRequest.RETRIEVE_DEVICES:
                return CatalogGetResolver._retrieve_devices(query, headers)
            case CatalogGetRequest.GET_DEVICE_STATUS:
                return CatalogGetResolver._get_device_status(query, headers)
            case CatalogGetRequest.MEASURES:
                return CatalogGetResolver._measures(query, headers)
            case CatalogGetRequest.LAST_MEASURES:
                return CatalogGetResolver._last_measures(query, headers)
            case CatalogGetRequest.CONSUMPTION:
                return CatalogGetResolver._consumption(query, headers)
        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _retrieve_broker():
        ip, port = catalog_interface.retrieve_broker()
        return {'broker_ip': ip, 'broker_port': port}

    @staticmethod
    def _user_info(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        return {'username': username}

    @staticmethod
    def _retrieve_greenhouses(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        items = catalog_interface.retrieve_greenhouses(username)
        # Spec: list of {id, name}
        return [{"id": it.get("greenhouse_id"), "name": it.get("name")} for it in (items or [])]

    @staticmethod
    def _retrieve_zones(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('greenhouse_id')
        gh = catalog_interface.retrieve_greenhouse(gh_id)
        if not gh:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_found')
        if gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        items = catalog_interface.retrieve_zones(gh_id)
        return [{"id": it.get("zone_id"), "name": it.get("name")} for it in (items or [])]

    @staticmethod
    def _retrieve_control_strategy(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        zone_id = query.get('zone_id')
        zone = catalog_interface.retrieve_zone(zone_id)
        if not zone:
            raise cherrypy.HTTPError(status=404, message='zone_not_found')
        gh = catalog_interface.retrieve_greenhouse(zone.get('greenhouse_id'))
        if not gh or gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        strategy = catalog_interface.retrieve_control_strategy(zone_id)
        return _normalize_strategy_payload(strategy or {})

    @staticmethod
    def _retrieve_devices(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        zone_id = query.get('zone_id')
        if not zone_id:
            raise cherrypy.HTTPError(status=400, message='missing_zone_id')
        zone = catalog_interface.retrieve_zone(zone_id)
        if not zone:
            raise cherrypy.HTTPError(status=404, message='zone_not_found')
        gh = catalog_interface.retrieve_greenhouse(zone.get('greenhouse_id'))
        if not gh or gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        items = catalog_interface.retrieve_devices(zone_id)
        # Spec: list of {id, type}
        return [{"id": it.get("device_id"), "type": it.get("type")} for it in (items or [])]

    @staticmethod
    def _get_device_status(query, headers):
        validate_authentication(headers, query)
        device_id = query.get('device_id')
        dev = catalog_interface.retrieve_device(device_id)
        if not dev:
            raise cherrypy.HTTPError(status=404, message='device_not_found')
        if dev.get('type') != 'actuator':
            raise cherrypy.HTTPError(status=400, message='not_an_actuator')
        # Convert on/off-like values to boolean
        status = catalog_interface.retrieve_actuator_status(device_id)
        if isinstance(status, str):
            status_bool = status.lower() in {'on', 'true', '1', 'online'}
        else:
            status_bool = bool(status)
        return {'device_id': device_id, 'status': status_bool}

    @staticmethod
    def _measures(query, headers):
        validate_authentication(headers, query)
        device_id = query.get('device_id')
        m_type = query.get('type')
        start = query.get('start')
        end = query.get('end')
        return catalog_interface.retrieve_measurements(device_id, m_type, start, end)

    @staticmethod
    def _last_measures(query, headers):
        validate_authentication(headers, query)
        device_id = query.get('device_id')
        return catalog_interface.retrieve_last_measurements(device_id)

    @staticmethod
    def _consumption(query, headers):
        validate_authentication(headers, query)
        device_id = query.get('device_id')
        start = query.get('start')
        end = query.get('end')
        return catalog_interface.retrieve_actuator_consumption(device_id, start, end)

class CatalogPostResolver:
    @staticmethod
    def resolve(request: CatalogPostRequest, query, body, headers):
        match request:
            case CatalogPostRequest.SIGN_UP:
                return CatalogPostResolver._sign_up(body)
            case CatalogPostRequest.LOGIN:
                return CatalogPostResolver._login(body)
            case CatalogPostRequest.CREATE_GREENHOUSE:
                return CatalogPostResolver._create_greenhouse(query, body, headers)
        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _sign_up(body):
        username = body.get('username')
        password = body.get('password')
        email = body.get('email')
        if not username or not password or not email:
            raise cherrypy.HTTPError(status=400, message='Missing fields')
        success = catalog_interface.signup_user(username, password, email)
        if not success:
            raise cherrypy.HTTPError(status=409, message='Username taken')
        return None

    @staticmethod
    def _login(body):
        username = body.get('username')
        password = body.get('password')
        token = catalog_interface.validate_login(username, password)
        if not token:
            raise cherrypy.HTTPError(status=401, message='Invalid credentials')
        return {'token': token}

    @staticmethod
    def _create_greenhouse(query, body, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        name = (body or {}).get('name') or query.get('name')
        if not name:
            raise cherrypy.HTTPError(status=400, message='Missing name')
        success = catalog_interface.add_greenhouse(name, username)
        if not success:
            raise cherrypy.HTTPError(status=409, message='Creation failed')
        return None

class CatalogPutResolver:
    @staticmethod
    def resolve(request: CatalogPutRequest, query, body, headers):
        match request:
            case CatalogPutRequest.RENAME_GREENHOUSE:
                return CatalogPutResolver._rename_greenhouse(query, body, headers)
            case CatalogPutRequest.ADD_ZONE:
                return CatalogPutResolver._add_zone(query, body, headers)
            case CatalogPutRequest.VALIDATE_ZONE:
                return CatalogPutResolver._validate_zone(query, body, headers)
            case CatalogPutRequest.RENAME_ZONE:
                return CatalogPutResolver._rename_zone(query, body, headers)
            case CatalogPutRequest.DELETE_ZONE:
                return CatalogPutResolver._delete_zone(query, headers)
            case CatalogPutRequest.MODIFY_CONTROL_STRATEGY:
                return CatalogPutResolver._modify_control_strategy(query, body, headers)
        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _rename_greenhouse(query, body, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('id')
        name = query.get('name') or (body or {}).get('name')
        gh = catalog_interface.retrieve_greenhouse(gh_id)
        if not gh:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_found')
        if gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if not catalog_interface.rename_greenhouse(gh_id, name, username):
            raise cherrypy.HTTPError(status=409, message='name_taken')
        return None

    @staticmethod
    def _add_zone(query, body, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('greenhouse_id')
        zone_id = (body or {}).get('zone_id') or query.get('zone_id')
        name = (body or {}).get('name') or query.get('name')
        gh = catalog_interface.retrieve_greenhouse(gh_id)
        if not gh:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_found')
        if gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if not catalog_interface.add_zone(gh_id, zone_id, name, username):
            raise cherrypy.HTTPError(status=409, message='zone_conflict')
        return None

    @staticmethod
    def _validate_zone(query, body, headers):
        validate_authentication(headers, query)
        zone_id = query.get('zone_id') or (body or {}).get('zone_id')
        return bool(catalog_interface.retrieve_zone(zone_id))

    @staticmethod
    def _rename_zone(query, body, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        zone_id = query.get('zone_id')
        name = (body or {}).get('name') or query.get('name')
        zone = catalog_interface.retrieve_zone(zone_id)
        if not zone:
            raise cherrypy.HTTPError(status=404, message='zone_not_found')
        gh = catalog_interface.retrieve_greenhouse(zone.get('greenhouse_id'))
        if not gh or gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if not catalog_interface.rename_zone(zone_id, name, username):
            raise cherrypy.HTTPError(status=409, message='name_taken')
        return None

    @staticmethod
    def _delete_zone(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        zone_id = query.get('zone_id')
        zone = catalog_interface.retrieve_zone(zone_id)
        if not zone:
            raise cherrypy.HTTPError(status=404, message='zone_not_found')
        gh = catalog_interface.retrieve_greenhouse(zone.get('greenhouse_id'))
        if not gh or gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if not catalog_interface.delete_zone(zone_id, username):
            raise cherrypy.HTTPError(status=400, message='delete_failed')
        return None

    @staticmethod
    def _modify_control_strategy(query, body, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        zone_id = query.get('zone_id')
        thresholds = _normalize_strategy_payload(body or {})
        zone = catalog_interface.retrieve_zone(zone_id)
        if not zone:
            raise cherrypy.HTTPError(status=404, message='zone_not_found')
        gh = catalog_interface.retrieve_greenhouse(zone.get('greenhouse_id'))
        if not gh or gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if not catalog_interface.modify_control_strategy(zone_id, thresholds, username):
            raise cherrypy.HTTPError(status=400, message='modify_failed')
        return None

class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogDeleteRequest, query, headers):
        match request:
            case CatalogDeleteRequest.DELETE_GREENHOUSE:
                return CatalogDeleteResolver._delete_greenhouse(query, headers)
        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _delete_greenhouse(query, headers):
        token = validate_authentication(headers, query)
        username = catalog_interface.retrieve_username_by_token(token)
        gh_id = query.get('id')
        gh = catalog_interface.retrieve_greenhouse(gh_id)
        if not gh:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_found')
        if gh.get('owner') != username:
            raise cherrypy.HTTPError(status=403, message='forbidden')
        if not catalog_interface.delete_greenhouse(gh_id, username):
            raise cherrypy.HTTPError(status=400, message='delete_failed')
        return None
