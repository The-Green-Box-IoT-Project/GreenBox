import cherrypy

import catalog_interface
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
        pass


class CatalogPutResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass


class CatalogDeleteResolver:
    @staticmethod
    def resolve(request: CatalogRequest, path, query):
        pass
