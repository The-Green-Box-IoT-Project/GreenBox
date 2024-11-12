import json
from pathlib import Path

import cherrypy

import catalog_interface
from catalog_dispatcher import CatalogGetDispatcher, CatalogPostDispatcher, CatalogPutDispatcher, \
    CatalogDeleteDispatcher
from catalog_resolver import CatalogGetResolver, CatalogPostResolver, CatalogPutResolver, CatalogDeleteResolver

catalog_interface.init()

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


def retrieve_endpoint():
    """
    Used to retrieve ip and port of the catalog, inside the catalog itself
    """
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        catalog_ip = data['catalog_ip']
        catalog_port = data['catalog_port']
    return catalog_ip, catalog_port


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
    catalog_ip, catalog_port = retrieve_endpoint()
    socket_config = {
        'server.socket_host': catalog_ip,
        'server.socket_port': int(catalog_port)
    }
    cherrypy.tree.mount(Catalog(), '/', config)
    cherrypy.config.update(socket_config)
    cherrypy.engine.start()
    cherrypy.engine.block()
