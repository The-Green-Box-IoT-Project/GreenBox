import json
from pathlib import Path

import cherrypy
from cherrypy import response

from catalog_dispatcher import CatalogRequest
import catalog_interface


# P = Path(__file__).parent.absolute()
# CONFIG_FILE = P / 'config.json'


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
        catalog_ip, catalog_port = catalog_interface.retrieve_endpoint()
        broker_ip, broker_port = catalog_interface.retrieve_broker()
        response = {
            'broker_ip': 'http://%s/%s' % (catalog_ip, broker_ip),
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
