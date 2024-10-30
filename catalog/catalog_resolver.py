import cherrypy

import catalog_interface
from catalog.catalog_interface import validate_login, validate_token
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
            case CatalogRequest.LOGIN:
                response = CatalogGetResolver._login()
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
    def _login():
        if not cherrypy.sessions.has_key('token'):
            username = cherrypy.sessions['username']
            password = cherrypy.sessions['password']
            token = validate_login(username, password)
        else:
            token = cherrypy.sessions['token']
        return token, validate_token(token)


class CatalogPostResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass


class CatalogPutResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass


class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass
