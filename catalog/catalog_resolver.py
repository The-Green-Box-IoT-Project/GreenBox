import cherrypy

from catalog_dispatcher import CatalogRequest
import catalog_interface


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
            case CatalogRequest.SIGN_UP:
                response = CatalogPostResolver._register(query)
            case CatalogRequest.LOGIN:
                response = CatalogPostResolver._login(query)
            case CatalogRequest.TOKEN_LOGIN:
                response = CatalogPostResolver._token_login(query)
        return response

    @staticmethod
    def _register(query):
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
