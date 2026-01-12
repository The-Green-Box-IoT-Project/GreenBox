from enum import Enum, auto

class CatalogGetRequest(Enum):
    NOT_FOUND = auto()
    RETRIEVE_BROKER = auto()
    USER_INFO = auto()
    RETRIEVE_GREENHOUSES = auto()
    GREENHOUSE_THRESHOLDS = auto()
    GREENHOUSE_EFFECTS = auto()
    RETRIEVE_ZONES = auto()
    RETRIEVE_CONTROL_STRATEGY = auto()
    RETRIEVE_DEVICES = auto()
    GET_DEVICE_STATUS = auto()
    MEASURES = auto()
    LAST_MEASURES = auto()
    CONSUMPTION = auto()

class CatalogPostRequest(Enum):
    NOT_FOUND = auto()
    SIGN_UP = auto()
    LOGIN = auto()
    CREATE_GREENHOUSE = auto()

class CatalogPutRequest(Enum):
    NOT_FOUND = auto()
    RENAME_GREENHOUSE = auto()
    ADD_ZONE = auto()
    VALIDATE_ZONE = auto()
    RENAME_ZONE = auto()
    DELETE_ZONE = auto()
    MODIFY_CONTROL_STRATEGY = auto()

class CatalogDeleteRequest(Enum):
    NOT_FOUND = auto()
    DELETE_GREENHOUSE = auto()

class CatalogGetDispatcher:
    @staticmethod
    def dispatch(path, query):
        path = tuple(p for p in path if p)
        if CatalogGetDispatcher._is_broker_request(path):
            return CatalogGetRequest.RETRIEVE_BROKER
        if CatalogGetDispatcher._is_greenhouse_thresholds_request(path):
            return CatalogGetRequest.GREENHOUSE_THRESHOLDS
        if CatalogGetDispatcher._is_greenhouse_effects_request(path):
            return CatalogGetRequest.GREENHOUSE_EFFECTS
        if CatalogGetDispatcher._is_user_info_request(path):
            return CatalogGetRequest.USER_INFO
        if CatalogGetDispatcher._is_retrieve_greenhouses_request(path):
            return CatalogGetRequest.RETRIEVE_GREENHOUSES
        if CatalogGetDispatcher._is_retrieve_zones_request(path, query):
            return CatalogGetRequest.RETRIEVE_ZONES
        if CatalogGetDispatcher._is_retrieve_control_strategy_request(path, query):
            return CatalogGetRequest.RETRIEVE_CONTROL_STRATEGY
        if CatalogGetDispatcher._is_retrieve_devices_request(path, query):
            return CatalogGetRequest.RETRIEVE_DEVICES
        if CatalogGetDispatcher._is_device_status_request(path, query):
            return CatalogGetRequest.GET_DEVICE_STATUS
        if CatalogGetDispatcher._is_measures_request(path, query):
            return CatalogGetRequest.MEASURES
        if CatalogGetDispatcher._is_last_measures_request(path, query):
            return CatalogGetRequest.LAST_MEASURES
        if CatalogGetDispatcher._is_consumption_request(path, query):
            return CatalogGetRequest.CONSUMPTION
        return CatalogGetRequest.NOT_FOUND

    @staticmethod
    def _is_broker_request(path):
        return len(path) == 1 and path[0] == 'broker'

    @staticmethod
    def _is_greenhouse_thresholds_request(path):
        return len(path) == 3 and path[0] == 'greenhouses' and path[2] == 'thresholds'

    @staticmethod
    def _is_greenhouse_effects_request(path):
        return len(path) == 3 and path[0] == 'greenhouses' and path[2] == 'effects'

    @staticmethod
    def _is_user_info_request(path):
        return len(path) == 2 and path[0] == 'user' and path[1] == 'info'

    @staticmethod
    def _is_retrieve_greenhouses_request(path):
        return len(path) == 1 and path[0] == 'greenhouses'

    @staticmethod
    def _is_retrieve_zones_request(path, query):
        return len(path) == 1 and path[0] == 'zones' and 'greenhouse_id' in query

    @staticmethod
    def _is_retrieve_control_strategy_request(path, query):
        return len(path) == 2 and path[0] == 'zones' and path[1] == 'strategy' and 'zone_id' in query

    @staticmethod
    def _is_retrieve_devices_request(path, query):
        return len(path) == 1 and path[0] == 'devices' and 'zone_id' in query

    @staticmethod
    def _is_device_status_request(path, query):
        return len(path) == 2 and path[0] == 'devices' and path[1] == 'status' and 'device_id' in query

    @staticmethod
    def _is_measures_request(path, query):
        return len(path) == 1 and path[0] == 'measurements' and 'device_id' in query and 'type' in query

    @staticmethod
    def _is_last_measures_request(path, query):
        return len(path) == 2 and path[0] == 'measurements' and path[1] == 'last' and 'device_id' in query

    @staticmethod
    def _is_consumption_request(path, query):
        return len(path) == 1 and path[0] == 'consumption' and 'device_id' in query

class CatalogPostDispatcher:
    @staticmethod
    def dispatch(path, query):
        path = tuple(p for p in path if p)
        if CatalogPostDispatcher._is_sign_up_request(path):
            return CatalogPostRequest.SIGN_UP
        if CatalogPostDispatcher._is_login_request(path):
            return CatalogPostRequest.LOGIN
        if CatalogPostDispatcher._is_create_greenhouse_request(path):
            return CatalogPostRequest.CREATE_GREENHOUSE
        return CatalogPostRequest.NOT_FOUND

    @staticmethod
    def _is_sign_up_request(path):
        return len(path) == 1 and path[0] == 'register'

    @staticmethod
    def _is_login_request(path):
        return len(path) == 1 and path[0] == 'login'

    @staticmethod
    def _is_create_greenhouse_request(path):
        return len(path) == 1 and path[0] == 'greenhouses'

class CatalogPutDispatcher:
    @staticmethod
    def dispatch(path, query, body=None):
        path = tuple(p for p in path if p)
        if CatalogPutDispatcher._is_validate_zone_request(path, query, body):
            return CatalogPutRequest.VALIDATE_ZONE
        if CatalogPutDispatcher._is_rename_greenhouse_request(path, query, body):
            return CatalogPutRequest.RENAME_GREENHOUSE
        if CatalogPutDispatcher._is_modify_control_strategy_request(path, query):
            return CatalogPutRequest.MODIFY_CONTROL_STRATEGY
        # Zone operations
        if CatalogPutDispatcher._is_add_zone_request(path, query, body):
            return CatalogPutRequest.ADD_ZONE
        if CatalogPutDispatcher._is_rename_zone_request(path, query, body):
            return CatalogPutRequest.RENAME_ZONE
        if CatalogPutDispatcher._is_delete_zone_request(path, query, body):
            return CatalogPutRequest.DELETE_ZONE
        return CatalogPutRequest.NOT_FOUND

    @staticmethod
    def _is_validate_zone_request(path, query, body):
        has_zone_id = 'zone_id' in query or (body and 'zone_id' in body)
        return len(path) == 2 and path[0] == 'zones' and path[1] == 'validate' and has_zone_id

    @staticmethod
    def _is_rename_greenhouse_request(path, query, body):
        return len(path) == 1 and path[0] == 'greenhouses' and 'id' in query

    @staticmethod
    def _is_modify_control_strategy_request(path, query):
        return len(path) == 2 and path[0] == 'zones' and path[1] == 'strategy' and 'zone_id' in query

    @staticmethod
    def _is_add_zone_request(path, query, body):
        has_zone_id = 'zone_id' in query or (body and 'zone_id' in body)
        has_name = 'name' in query or (body and 'name' in body)
        return len(path) == 1 and path[0] == 'zones' and 'greenhouse_id' in query and has_zone_id and has_name

    @staticmethod
    def _is_rename_zone_request(path, query, body):
        has_name = 'name' in query or (body and 'name' in body)
        return len(path) == 1 and path[0] == 'zones' and 'zone_id' in query and has_name and 'greenhouse_id' not in query

    @staticmethod
    def _is_delete_zone_request(path, query, body):
        has_name = 'name' in query or (body and 'name' in body)
        return len(path) == 1 and path[0] == 'zones' and 'zone_id' in query and not has_name and 'greenhouse_id' not in query

class CatalogDeleteDispatcher:
    @staticmethod
    def dispatch(path, query):
        path = tuple(p for p in path if p)
        if CatalogDeleteDispatcher._is_delete_greenhouse_request(path, query):
            return CatalogDeleteRequest.DELETE_GREENHOUSE
        return CatalogDeleteRequest.NOT_FOUND

    @staticmethod
    def _is_delete_greenhouse_request(path, query):
        return len(path) == 1 and path[0] == 'greenhouses' and 'id' in query
