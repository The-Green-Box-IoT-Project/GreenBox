import json
from pathlib import Path

import cherrypy

import catalog_interface
from catalog_dispatcher import CatalogGetDispatcher, CatalogPostDispatcher, CatalogPutDispatcher, \
    CatalogDeleteDispatcher
from catalog_resolver import CatalogGetResolver, CatalogPostResolver, CatalogPutResolver, CatalogDeleteResolver

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class Catalog:
    exposed = True

    def GET(self, *path, **query):
        request = CatalogGetDispatcher.dispatch(path, query)
        response = CatalogGetResolver.resolve(request, path, query)
        return json.dumps(response)

    def POST(self, *path, **query):
        request = CatalogPostDispatcher.dispatch(path, query)
        response = CatalogPostResolver.resolve(request, path, query)
        return json.dumps(response)

    def PUT(self, *path, **query):
        request = CatalogPutDispatcher.dispatch(path, query)
        response = CatalogPutResolver.resolve(request, path, query)
        return json.dumps(response)

    def DELETE(self, *path, **query):
        request = CatalogDeleteDispatcher.dispatch(path, query)
        response = CatalogDeleteResolver.resolve(request, path, query)
        return json.dumps(response)


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
