import os

import cherrypy
from dotenv import load_dotenv

import catalog_interface
from catalog_dispatcher import CatalogRequest
from generator import generator

load_dotenv()
admin_token = os.getenv('ADMIN_TOKEN')


class CatalogGetResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        response = None
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.RETRIEVE_BROKER:
                response = CatalogGetResolver._retrieve_broker()
            case CatalogRequest.GENERATE_ID:
                response = CatalogGetResolver._generate_id(query)
            case CatalogRequest.DEVICE_JOIN:
                response = CatalogGetResolver._device_join(query)
        return response

    @staticmethod
    def _retrieve_broker():
        """
        Called to retrieve ip and port of the broker.
        path: broker
        query: -
        """
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        response = {
            'broker_ip': broker_ip,
            'broker_port': broker_port
        }
        return response

    @staticmethod
    def _generate_id(query):
        """
        Called by the organization to generate a new unique id to be
        assigned to a device or a greenhouse that will be distributed.
        path: generate_id
        query: token
        """
        token = query['token']
        if token != admin_token:
            raise cherrypy.HTTPError(status=403)
        generated_id = generator.generate_id()
        response = {'generated_id': generated_id}
        return response

    @staticmethod
    def _device_join(query):
        """
        Called by a device (Raspberry, actuator, etc...) to join
        the catalog and obtain its resource catalog (i.e. id of the
        greenhouse it is associated with). When called before the user
        has successfully registered the device, it does not return
        anything useful.
        path: device_join
        query: device_id
        """
        device_id = query['device_id']
        if not catalog_interface.verify_device_existence(device_id):
            raise cherrypy.HTTPError(status=404)
        if catalog_interface.is_device_available(device_id):
            return {'msg': 'device_not_associated'}
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        return {
            'broker_ip': broker_ip,
            'broker_port': broker_port,
            'greenhouse_id': catalog_interface.retrieve_device_association(device_id)
        }


class CatalogPostResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        response = None
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.REGISTER_NEW_GREENHOUSE:
                response = CatalogPostResolver._register_new_greenhouse(query)
            case CatalogRequest.REGISTER_NEW_DEVICE:
                response = CatalogPostResolver._register_new_device(query)
            case CatalogRequest.SIGN_UP:
                response = CatalogPostResolver._sign_up(query)
            case CatalogRequest.LOGIN:
                response = CatalogPostResolver._login(query)
            case CatalogRequest.TOKEN_LOGIN:
                response = CatalogPostResolver._token_login(query)
        return response

    @staticmethod
    def _register_new_greenhouse(query):
        """
        Called by the organization to register an id associated to
        a greenhouse that will be distributed. It is supposed that the
        greenhouse is ready to be delivered.
        path: register/greenhouse
        query: greenhouse_id, token
        """
        if 'token' not in query:
            raise cherrypy.HTTPError(status=401)
        token = query['token']
        if token != admin_token:
            raise cherrypy.HTTPError(status=403)
        greenhouse_id = query['greenhouse_id']
        generator.register_greenhouse(greenhouse_id)
        response = {'greenhouse_id': greenhouse_id}
        return response

    @staticmethod
    def _register_new_device(query):
        """
        Called by the organization to register an id associated to
        a device that will be distributed. It is supposed that the
        device is ready to be delivered.
        path: register/device
        query: device_id, device_type, token
        """
        if 'token' not in query:
            raise cherrypy.HTTPError(status=401)
        token = query['token']
        if token != admin_token:
            raise cherrypy.HTTPError(status=403)
        device_id = query['device_id']
        device_type = query['device_type']
        generator.register_device(device_id, device_type)
        response = {'device_id': device_id, 'device_type': device_type}
        return response

    @staticmethod
    def _sign_up(query):
        """
        Called by a user that wants to be registered on the system.
        path: signup
        query: username, password, repeat_password
        """
        token = None
        msg = None
        username = query['username']
        password = query['password']
        repeat_password = query['repeat_password']
        if password != repeat_password:
            msg = 'password_mismatch'
        elif not catalog_interface.signup_user(username, password):
            msg = 'user_existing'
        else:
            token = catalog_interface.validate_login(username, password)
        response = {
            'msg': msg,
            'token': token,
            'valid': catalog_interface.verify_token(token)
        }
        return response

    @staticmethod
    def _login(query):
        """
        Called by a user that wants to log into the system opening a new
        session. A new session (and so a new token) is initialized and
        its set of resources will be given to the user.
        path: login
        query: username, password
        """
        username = query['username']
        password = query['password']
        token = catalog_interface.validate_login(username, password)
        is_token_valid = catalog_interface.verify_token(token)
        if is_token_valid:
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


class CatalogPutResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        response = None
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.ASSOCIATE_GREENHOUSE:
                response = CatalogPutResolver._associate_greenhouse(query)
            case CatalogRequest.ASSOCIATE_DEVICE:
                response = CatalogPutResolver._associate_device(query)
        return response

    @staticmethod
    def _associate_greenhouse(query):
        """
        Called by a user that wants to add a new greenhouse.
        path: associate/greenhouse
        query: greenhouse_id, greenhouse_name, token
        """
        if 'token' not in query:
            raise cherrypy.HTTPError(status=401)
        token = query['token']
        greenhouse_id = query['greenhouse_id']
        greenhouse_name = query['greenhouse_name']
        # Token validity verification
        is_token_valid = catalog_interface.verify_token(token)
        if not is_token_valid:
            return {
                'msg': 'invalid_token',
                'success': False
            }
        username = catalog_interface.retrieve_username_by_token(token)
        # Greenhouse registration verification
        is_greenhouse_registered = catalog_interface.verify_greenhouse_existence(greenhouse_id)
        if not is_greenhouse_registered:
            return {
                'msg': 'greenhouse_not_available',
                'success': False
            }
        # Greenhouse ownership verification
        is_greenhouse_owned = catalog_interface.verify_greenhouse_ownership(greenhouse_id, username)
        if is_greenhouse_owned:
            return {
                'msg': 'greenhouse_already_associated',
                'success': False
            }
        # Greenhouse availability verification
        is_greenhouse_available = catalog_interface.is_greenhouse_available(greenhouse_id)
        if not is_greenhouse_available:
            return {
                'msg': 'greenhouse_not_available',
                'success': False
            }
        # Greenhouse association
        catalog_interface.associate_greenhouse(greenhouse_id, greenhouse_name, username)
        return {
            'msg': None,
            'success': True
        }

    @staticmethod
    def _associate_device(query):
        """
        Called by a user that wants to associate a new device to its
        greenhouse.
        path: associate/device
        query: device_id, device_name, greenhouse_id, token
        """
        if 'token' not in query:
            raise cherrypy.HTTPError(status=401)
        token = query['token']
        device_id = query['device_id']
        device_name = query['device_name']
        greenhouse_id = query['greenhouse_id']

        # Token validity verification
        is_token_valid = catalog_interface.verify_token(token)
        if not is_token_valid:
            return {
                'msg': 'invalid_token',
                'success': False
            }
        username = catalog_interface.retrieve_username_by_token(token)
        # Device registration verification
        is_device_registered = catalog_interface.verify_device_existence(device_id)
        if not is_device_registered:
            return {
                'msg': 'device_not_available',
                'success': False
            }
        # Device ownership verification
        is_device_owned = catalog_interface.verify_device_ownership(device_id, username)
        if is_device_owned:
            return {
                'msg': 'device_already_associated',
                'additional': catalog_interface.retrieve_device_association(device_id),
                'success': False
            }
        # Device availability verification
        is_device_available = catalog_interface.is_device_available(device_id)
        if not is_device_available:
            return {
                'msg': 'device_not_available',
                'success': False
            }
        # Greenhouse registration verification
        is_greenhouse_registered = catalog_interface.verify_greenhouse_existence(greenhouse_id)
        if not is_greenhouse_registered:
            return {
                'msg': 'greenhouse_not_available',
                'success': False
            }
        # Greenhouse ownership verification
        is_greenhouse_owned = catalog_interface.verify_greenhouse_ownership(greenhouse_id, username)
        if not is_greenhouse_owned:
            return {
                'msg': 'greenhouse_not_available',
                'success': False
            }
        # Device association
        catalog_interface.associate_device(device_id, greenhouse_id, device_name, username)
        return {
            'msg': None,
            'success': True
        }


class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass
