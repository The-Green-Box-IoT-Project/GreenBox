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
        return response

    @staticmethod
    def _retrieve_broker():
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        response = {
            'broker_ip': broker_ip,
            'broker_port': broker_port
        }
        return response

    @staticmethod
    def _generate_id(query):
        token = query['token']
        if token != admin_token:
            raise cherrypy.HTTPError(status=403)
        device_type = query['device_type']
        device_id = generator.generate_id(device_type)
        response = {
            'device_id': device_id,
            'device_type': device_type
        }
        return response


class CatalogPostResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        response = None
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.REGISTER_ID:
                response = CatalogPostResolver._register_id(query)
            case CatalogRequest.SIGN_UP:
                response = CatalogPostResolver._sign_up(query)
            case CatalogRequest.LOGIN:
                response = CatalogPostResolver._login(query)
            case CatalogRequest.TOKEN_LOGIN:
                response = CatalogPostResolver._token_login(query)
        return response

    @staticmethod
    def _register_id(query):
        token = query['token']
        if token != admin_token:
            raise cherrypy.HTTPError(status=403)
        device_id = query['device_id']
        generator.register_device(device_id)
        response = {'device_id': device_id}
        return response

    @staticmethod
    def _sign_up(query):
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
            'valid': catalog_interface.validate_token(token),
            'resources': []
        }
        return response

    @staticmethod
    def _login(query):
        username = query['username']
        password = query['password']
        token = catalog_interface.validate_login(username, password)
        response = {
            'token': token,
            'valid': catalog_interface.validate_token(token),
            'resources': catalog_interface.retrieve_resources(token)
        }
        return response

    @staticmethod
    def _token_login(query):
        token = query['token']
        response = {
            'token': token,
            'valid': catalog_interface.validate_token(token),
            'resources': catalog_interface.retrieve_resources(token)
        }
        return response


class CatalogPutResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass


class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass
