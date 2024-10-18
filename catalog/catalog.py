import json
from enum import Enum, auto
from pathlib import Path

import cherrypy

import catalog_interface

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class CatalogRequest(Enum):
    NOT_FOUND = auto(),
    RETRIEVE_BROKER = auto(),


class CatalogResolver:
    @staticmethod
    def get_resolve(request: CatalogRequest, path, query):
        match request:
            case CatalogRequest.NOT_FOUND:
                raise cherrypy.HTTPError(status=404)
            case CatalogRequest.RETRIEVE_BROKER:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)


class CatalogDispatcher:
    @staticmethod
    def get_dispatcher(path, query):
        if CatalogGetDispatcher.is_broker_request(path):
            return CatalogRequest.RETRIEVE_BROKER
        return CatalogRequest.NOT_FOUND

    @staticmethod
    def post_dispatcher(path, query):
        pass

    @staticmethod
    def put_dispatcher(path, query):
        pass

    @staticmethod
    def delete_dispatcher(path, query):
        pass


class CatalogGetDispatcher:
    @staticmethod
    def is_broker_request(path):
        if len(path) == 0:
            return False
        if path[0] == 'broker':
            return True
        return False


class Catalog:
    exposed = True

    def GET(self, *path, **query):
        request = CatalogDispatcher.get_dispatcher(path, query)
        return json.dumps(CatalogResolver.get_resolve(request, path, query))

    def POST(self, *path, **query):
        pass

    def PUT(self, *path, **query):
        pass


if __name__ == '__main__':
    config = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    catalog_ip, catalog_port = catalog_interface.retrieve_endpoint()
    socket_config = {
        'server.socket_host': catalog_ip,
        'server.socket_port': int(catalog_port)
    }
    cherrypy.tree.mount(Catalog(), '/', config)
    cherrypy.config.update(socket_config)
    cherrypy.engine.start()
    cherrypy.engine.block()
