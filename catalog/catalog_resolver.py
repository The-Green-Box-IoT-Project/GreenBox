import json
import cherrypy
from . import catalog_interface
from .catalog_dispatcher import CatalogGetRequest, CatalogPostRequest, CatalogPutRequest, CatalogDeleteRequest

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
        return items

    @staticmethod
    def _retrieve_zones(query, headers):
        validate_authentication(headers, query)
        gh_id = query.get('greenhouse_id')
        items = catalog_interface.retrieve_zones(gh_id)
        return items

    @staticmethod
    def _retrieve_control_strategy(query, headers):
        validate_authentication(headers, query)
        zone_id = query.get('zone_id')
        return catalog_interface.retrieve_control_strategy(zone_id)

    @staticmethod
    def _retrieve_devices(query, headers):
        validate_authentication(headers, query)
        zone_id = query.get('zone_id')
        items = catalog_interface.retrieve_devices(zone_id)
        return items

    @staticmethod
    def _get_device_status(query, headers):
        validate_authentication(headers, query)
        device_id = query.get('device_id')
        status = catalog_interface.retrieve_actuator_status(device_id)
        return {'device_id': device_id, 'status': status}

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
        if not username or not password:
            raise cherrypy.HTTPError(status=400, message='Missing fields')
        success = catalog_interface.signup_user(username, password)
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
            case CatalogPutRequest.RENAME_ZONE:
                return CatalogPutResolver._rename_zone(query, body, headers)
            case CatalogPutRequest.DELETE_ZONE:
                return CatalogPutResolver._delete_zone(query, headers)
            case CatalogPutRequest.MODIFY_CONTROL_STRATEGY:
                return CatalogPutResolver._modify_control_strategy(query, body, headers)
        raise cherrypy.HTTPError(status=400)

    @staticmethod
    def _rename_greenhouse(query, body, headers):
        validate_authentication(headers, query)
        gh_id = query.get('id')
        name = query.get('name') or (body or {}).get('name')
        if not catalog_interface.rename_greenhouse(gh_id, name):
            raise cherrypy.HTTPError(status=400, message='Rename failed')
        return None

    @staticmethod
    def _add_zone(query, body, headers):
        validate_authentication(headers, query)
        gh_id = query.get('greenhouse_id')
        zone_id = (body or {}).get('zone_id') or query.get('zone_id')
        name = (body or {}).get('name') or query.get('name')
        if not catalog_interface.add_zone(gh_id, zone_id, name):
            raise cherrypy.HTTPError(status=400, message='Add zone failed')
        return None

    @staticmethod
    def _rename_zone(query, body, headers):
        validate_authentication(headers, query)
        zone_id = query.get('zone_id')
        name = (body or {}).get('name') or query.get('name')
        if not catalog_interface.rename_zone(zone_id, name):
            raise cherrypy.HTTPError(status=400, message='Rename zone failed')
        return None

    @staticmethod
    def _delete_zone(query, headers):
        validate_authentication(headers, query)
        zone_id = query.get('zone_id')
        if not catalog_interface.delete_zone(zone_id):
            raise cherrypy.HTTPError(status=400, message='Delete zone failed')
        return None

    @staticmethod
    def _modify_control_strategy(query, body, headers):
        validate_authentication(headers, query)
        zone_id = query.get('zone_id')
        thresholds = body or {}
        if not catalog_interface.modify_control_strategy(zone_id, thresholds):
            raise cherrypy.HTTPError(status=400, message='Modify strategy failed')
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
        validate_authentication(headers, query)
        gh_id = query.get('id')
        if not catalog_interface.delete_greenhouse(gh_id):
            raise cherrypy.HTTPError(status=400, message='Delete greenhouse failed')
        return None
