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
        # Dispatch
        request = CatalogGetDispatcher.dispatch(path=path,
                                                query=query)
        headers = cherrypy.request.headers
        # Resolve
        response = CatalogGetResolver.resolve(request=request,
                                              query=query,
                                              headers=headers)
        return json.dumps(response)

    @cherrypy.tools.json_out()
    def POST(self, *path, **query):
        body = cherrypy.request.body.read().decode("utf-8")
        body = json.loads(body)
        # Dispatch
        request = CatalogPostDispatcher.dispatch(path=path,
                                                 query=query)
        headers = cherrypy.request.headers
        # Resolve
        response = CatalogPostResolver.resolve(request=request,
                                               query=query,
                                               body=body,
                                               headers=headers)
        return json.dumps(response)

    def PUT(self, *path, **query):
        body = json.loads(cherrypy.request.body.read().decode("utf-8"))
        # Dispatch
        request = CatalogPutDispatcher.dispatch(path=path,
                                                query=query)
        headers = cherrypy.request.headers
        # Resolve
        response = CatalogPutResolver.resolve(request=request,
                                              query=query,
                                              body=body,
                                              headers=headers)
        return json.dumps(response)

    def DELETE(self, *path, **query):
        # Dispatch
        request = CatalogDeleteDispatcher.dispatch(path=path,
                                                   query=query)
        headers = cherrypy.request.headers
        # Resolve
        response = CatalogDeleteResolver.resolve(request=request,
                                                 query=query,
                                                 headers=headers)
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
        'server.socket_port': int(catalog_port),
        'tools.response_headers.on': True,
        'tools.response_headers.headers': [('Access-Control-Allow-Origin', '*')],
    }
    cherrypy.tree.mount(Catalog(), '/', config)
    cherrypy.config.update(socket_config)
    cherrypy.engine.start()
    cherrypy.engine.block()
