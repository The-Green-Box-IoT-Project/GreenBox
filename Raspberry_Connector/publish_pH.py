from raspberry_connector import RaspberryConnector

rc = RaspberryConnector(conf_path="conf.json", devices_path="devices.json")
rc.publish(rc.pH_meter)
