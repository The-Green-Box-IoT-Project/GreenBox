from enum import Enum, auto


class CatalogGetRequest(Enum):
    NOT_FOUND = auto(),
    RETRIEVE_BROKER = auto(),
    GENERATE_ID = auto(),
    RETRIEVE_GREENHOUSES = auto(),
    RETRIEVE_DEVICES = auto(),
    DEVICE_JOIN = auto(),


class CatalogPostRequest(Enum):
    NOT_FOUND = auto(),
    REGISTER_NEW_GREENHOUSE = auto(),
    REGISTER_NEW_DEVICE = auto(),
    SIGN_UP = auto(),
    LOGIN = auto(),


class CatalogPutRequest(Enum):
    NOT_FOUND = auto(),
    ASSOCIATE_GREENHOUSE = auto(),
    ASSOCIATE_DEVICE = auto(),


class CatalogDeleteRequest(Enum):
    NOT_FOUND = auto(),


class CatalogGetDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogGetDispatcher._is_broker_request(path):
            return CatalogGetRequest.RETRIEVE_BROKER
        if CatalogGetDispatcher._is_generate_id_request(path, query):
            return CatalogGetRequest.GENERATE_ID
        if CatalogGetDispatcher._is_device_join_request(path, query):
            return CatalogGetRequest.DEVICE_JOIN
        if CatalogGetDispatcher._is_retrieve_greenhouses_request(path, query):
            return CatalogGetRequest.RETRIEVE_GREENHOUSES
        if CatalogGetDispatcher._is_retrieve_devices_request(path, query):
            return CatalogGetRequest.RETRIEVE_DEVICES
        return CatalogGetRequest.NOT_FOUND

    @staticmethod
    def _is_broker_request(path):
        """
        Called to retrieve ip and port of the broker.
        path: broker
        query: -
        auth: -
        """
        if len(path) != 1:
            return False
        if path[0] != 'broker':
            return False
        return True

    @staticmethod
    def _is_generate_id_request(path, query):
        """
        Called by the organization to generate a new unique id to be
        assigned to a device or a greenhouse that will be distributed.
        path: generate_id
        query: -
        auth: admin token
        """
        if len(path) != 1:
            return False
        if path[0] != 'generate_id':
            return False
        return True

    @staticmethod
    def _is_device_join_request(path, query):
        """
        Called by a device (Raspberry, actuator, etc...) to join
        the catalog and obtain its resource catalog (i.e. id of the
        greenhouse it is associated with). When called before the user
        has successfully registered the device, it does not return
        anything useful.
        path: device_join
        query: device_id
        auth: -
        """
        if len(path) != 1:
            return False
        if path[0] != 'device_join':
            return False
        if not 'device_id' in query:
            return False
        return True

    @staticmethod
    def _is_retrieve_greenhouses_request(path, query):
        """
        Called by a user that wants to retrieve its set of greenhouses.
        path: retrieve/greenhouses
        query: -
        auth: token
        """
        if len(path) != 2:
            return False
        if path[0] != 'retrieve':
            return False
        if path[1] != 'greenhouses':
            return False
        return True

    @staticmethod
    def _is_retrieve_devices_request(path, query):
        """
        Called by a user that wants to retrieve the devices associated
        with a greenhouse.
        path: retrieve/devices
        query: greenhouse_id
        auth: token
        """
        if len(path) != 2:
            return False
        if path[0] != 'retrieve':
            return False
        if path[1] != 'devices':
            return False
        if 'greenhouse_id' not in query:
            return False
        return True


class CatalogPostDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogPostDispatcher._is_register_new_greenhouse_request(path, query):
            return CatalogPostRequest.REGISTER_NEW_GREENHOUSE
        if CatalogPostDispatcher._is_register_new_device_request(path, query):
            return CatalogPostRequest.REGISTER_NEW_DEVICE
        if CatalogPostDispatcher._is_sign_up_request(path, query):
            return CatalogPostRequest.SIGN_UP
        if CatalogPostDispatcher._is_login_request(path, query):
            return CatalogPostRequest.LOGIN
        return CatalogPostRequest.NOT_FOUND

    @staticmethod
    def _is_register_new_greenhouse_request(path, query):
        """
        Called by the organization to register an id associated to
        a greenhouse that will be distributed. It is supposed that the
        greenhouse is ready to be delivered.
        path: register/greenhouse
        query: greenhouse_id
        auth: admin token
        """
        if len(path) != 2:
            return False
        if path[0] != 'register':
            return False
        if path[1] != 'greenhouse':
            return False
        if 'greenhouse_id' not in query:
            return False
        return True

    @staticmethod
    def _is_register_new_device_request(path, query):
        """
        Called by the organization to register an id associated to
        a device that will be distributed. It is supposed that the
        device is ready to be delivered.
        path: register/device
        query: device_id, device_type
        auth: admin token
        """
        if len(path) != 2:
            return False
        if path[0] != 'register':
            return False
        if path[1] != 'device':
            return False
        if not {'device_id', 'device_type'}.issubset(query):
            return False
        return True

    @staticmethod
    def _is_sign_up_request(path, query):
        """
        Called by a user that wants to be registered on the system.
        path: signup
        query: username, password, repeat_password
        auth: -
        """
        if len(path) != 1:
            return False
        if path[0] != 'signup':
            return False
        if not {'username', 'password', 'repeat_password'}.issubset(query):
            return False
        return True

    @staticmethod
    def _is_login_request(path, query):
        """
        Called by a user that wants to log into the system opening a new
        session. A new session (and so a new token) is initialized and
        its set of greenhouses will be given to the user.
        path: login
        query: username, password
        auth: -
        """
        if len(path) != 1:
            return False
        if path[0] != 'login':
            return False
        if not {'username', 'password'}.issubset(query):
            return False
        return True


class CatalogPutDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogPutDispatcher._is_associate_device_request(path, query):
            return CatalogPutRequest.ASSOCIATE_DEVICE
        if CatalogPutDispatcher._is_associate_greenhouse_request(path, query):
            return CatalogPutRequest.ASSOCIATE_GREENHOUSE
        return CatalogPutRequest.NOT_FOUND

    @staticmethod
    def _is_associate_greenhouse_request(path, query):
        """
        Called by a user that wants to add a new greenhouse.
        path: associate/greenhouse
        query: greenhouse_id, greenhouse_name
        auth: token
        """
        if len(path) != 2:
            return False
        if path[0] != 'associate':
            return False
        if path[1] != 'greenhouse':
            return False
        if not {'greenhouse_id', 'greenhouse_name'}.issubset(query):
            return False
        return True

    @staticmethod
    def _is_associate_device_request(path, query):
        """
        Called by a user that wants to associate a new device to its
        greenhouse.
        path: associate/device
        query: device_id, device_name, greenhouse_id
        auth: token
        """
        if len(path) != 2:
            return False
        if path[0] != 'associate':
            return False
        if path[1] != 'device':
            return False
        if not {'device_id', 'greenhouse_id', 'device_name'}.issubset(query):
            return False
        return True


class CatalogDeleteDispatcher:
    @staticmethod
    def dispatch(path, query):
        pass
