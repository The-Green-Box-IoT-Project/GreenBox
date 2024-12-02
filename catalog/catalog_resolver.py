import os

import cherrypy
from dotenv import load_dotenv

import catalog_interface
from catalog_dispatcher import CatalogGetRequest, CatalogPostRequest, CatalogPutRequest, CatalogDeleteRequest
from generator import generator

load_dotenv()
admin_token = os.getenv('ADMIN_TOKEN')


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
        raise cherrypy.HTTPError(status=400)

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
    def _retrieve_greenhouses(headers):
        """
        Called by a user that wants to retrieve its set of greenhouses.
        path: retrieve/greenhouses
        query: -
        auth: token
        """
        token = validate_authentication(headers)
        username = catalog_interface.retrieve_username_by_token(token)
        greenhouses = catalog_interface.retrieve_greenhouses(username)
        response = {
            'greenhouses': greenhouses,
            'username': username
        }
        return response

    @staticmethod
    def _retrieve_devices(query, headers):
        """
        Called by a user that wants to retrieve the devices associated
        with a greenhouse.
        path: retrieve/devices
        query: greenhouse_id
        auth: token
        """
        token = validate_authentication(headers)
        greenhouse_id = query['greenhouse_id']
        username = catalog_interface.retrieve_username_by_token(token)
        # Greenhouse ownership verification
        is_greenhouse_owned = catalog_interface.verify_greenhouse_ownership(greenhouse_id, username)
        if not is_greenhouse_owned:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')
        devices = catalog_interface.retrieve_devices(greenhouse_id)
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
        body: username, password, repeat_password
        auth: -
        """
        if not {'username', 'password', 'repeat_password'}.issubset(body):
            raise cherrypy.HTTPError(status=400, message='missing_fields')
        username = body['username']
        password = body['password']
        repeat_password = body['repeat_password']
        if password != repeat_password:
            raise cherrypy.HTTPError(status=403, message='passwords_dont_match')
        elif not catalog_interface.signup_user(username, password):
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
        greenhouses = catalog_interface.retrieve_greenhouses(username)
        response = {
            'token': token,
            'greenhouses': greenhouses
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
        return response

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
        """
        Called by a user that wants to associate a new device to its
        greenhouse.
        path: associate/device
        query: device_id, device_name, greenhouse_id
        auth: token
        """
        token = validate_authentication(headers)
        username = catalog_interface.retrieve_username_by_token(token)
        device_id = query['device_id']
        device_name = query['device_name']
        greenhouse_id = query['greenhouse_id']
        # Device registration verification
        is_device_registered = catalog_interface.verify_device_existence(device_id)
        if not is_device_registered:
            raise cherrypy.HTTPError(status=404, message='device_not_available')
        # Device ownership verification
        is_device_owned = catalog_interface.verify_device_ownership(device_id, username)
        if is_device_owned:
            raise cherrypy.HTTPError(status=403, message='device_already_associated')
        # Device availability verification
        is_device_available = catalog_interface.is_device_available(device_id)
        if not is_device_available:
            raise cherrypy.HTTPError(status=404, message='device_not_available')
        # Greenhouse registration verification
        is_greenhouse_registered = catalog_interface.verify_greenhouse_existence(greenhouse_id)
        if not is_greenhouse_registered:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')
        # Greenhouse ownership verification
        is_greenhouse_owned = catalog_interface.verify_greenhouse_ownership(greenhouse_id, username)
        if not is_greenhouse_owned:
            raise cherrypy.HTTPError(status=404, message='greenhouse_not_available')
        # Device association
        catalog_interface.associate_device(device_id, greenhouse_id, device_name, username)


class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogDeleteRequest, query, headers):
        pass
