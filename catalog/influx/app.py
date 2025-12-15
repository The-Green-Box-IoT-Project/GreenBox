import cherrypy
import os
from interface import InfluxInterface

class InfluxService:
    exposed = True

    def __init__(self):
        self.influx = InfluxInterface()

    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        if not path:
            return {"status": "Influx Adapter Ready"}

        if path[0] == 'measurements':
            if len(path) == 1:
                # /measurements
                device_id = params.get('device_id')
                metric = params.get('measurement_type')
                start = params.get('start_time')
                end = params.get('end_time')
                
                if not metric:
                    raise cherrypy.HTTPError(400, "Missing measurement_type")

                try:
                    df = self.influx.read(
                        metric=metric,
                        device=device_id,
                        start=start,
                        end=end,
                        limit=100
                    )
                except ValueError:
                    return []

                result = []
                if not df.empty:
                    for _, row in df.iterrows():
                        val = row.get('value')
                        t = row.get('time')
                        result.append([str(t), val])
                return result

            elif len(path) == 2 and path[1] == 'last':
                # /measurements/last
                device_id = params.get('device_id')
                metrics = ["temperature", "humidity", "soil_humidity", "light", "pH"]
                out = {}
                for m in metrics:
                    try:
                        df = self.influx.read(metric=m, device=device_id, limit=1)
                        if not df.empty:
                            out[m] = df.iloc[0]['value']
                    except ValueError:
                        pass
                return out

        if path[0] == 'consumption':
            # /consumption
            device_id = params.get('device_id')
            start = params.get('start_time')
            end = params.get('end_time')
            
            try:
                df = self.influx.read(metric="power", device=device_id, start=start, end=end)
            except ValueError:
                return []

            result = []
            if not df.empty:
                for _, row in df.iterrows():
                    val = row.get('value')
                    t = row.get('time')
                    result.append([str(t), val])
            return result

        raise cherrypy.HTTPError(404)

if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
        }
    }
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8086})
    cherrypy.quickstart(InfluxService(), '/', conf)
