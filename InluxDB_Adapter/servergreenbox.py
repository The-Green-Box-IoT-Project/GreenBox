import os
import cherrypy
import json
from db_reader import InfluxDBReader
from dotenv import load_dotenv
import datetime

load_dotenv()

token = os.getenv("INFLUX_TOKEN")
bucket = os.getenv('INFLUXDB_BUCKET')
org = os.getenv('INFLUXDB_ORG')
url = os.getenv('INFLUXDB_URL')


class ServerGreenBox:
    exposed = True

    def __init__(self, influxdb):
        self.influxdb: InfluxDBReader = influxdb

    def GET(self, *path, **query):
        # print(path, '\t', query)
        self.influxdb.token = query['token']
        self.influxdb.token = token
        self.influxdb.connect_client()
        variables_dict = {
            "measurement_name": "mqtt_consumer",
            "field_name": "temperature",
            "host_name": "SteurendoPPC",
            "topic_name": "sensor/data",
            "window_period": "1m",
            "yield_name": "mean"
        }
        start_time = datetime.datetime(2024, 4, 24, 17, 27, 0)
        end_time = datetime.datetime(2024, 4, 30, 17, 36, 0)
        self.influxdb.compose_query_timestamps(start_time, end_time, **variables_dict)
        self.influxdb.execute_query()
        result = self.influxdb.get_result()
        return json.dumps(result, indent=4)


if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.tree.mount(ServerGreenBox(InfluxDBReader(bucket, org, token, url)), '/', conf)

    cherrypy.config.update({'server.socket_host': '0.0.0.0'})

    cherrypy.engine.start()
    cherrypy.engine.block()
