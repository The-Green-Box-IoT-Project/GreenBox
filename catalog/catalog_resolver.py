import cherrypy

import catalog_interface
from catalog_interface import validate_login, validate_token
from catalog_dispatcher import CatalogRequest


class CatalogGetResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        response = None
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.RETRIEVE_BROKER:
                response = CatalogGetResolver._retrieve_broker()
        return response

    @staticmethod
    def _retrieve_broker():
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        response = {
            'broker_ip': broker_ip,
            'broker_port': broker_port
        }
        return response


class CatalogPostResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        response = None
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.LOGIN:
                response = CatalogPostResolver._login(query)
        return response

    @staticmethod
    def _login(query):
        if 'token' not in query:
            username = query['username']
            password = query['password']
            token = validate_login(username, password)
        else:
            token = query['token']
        response = {
            'token': token,
            'valid': validate_token(token)
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
