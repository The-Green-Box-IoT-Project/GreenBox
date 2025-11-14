from enum import Enum, auto


class CatalogGetRequest(Enum):
    NOT_FOUND = auto(),
    RETRIEVE_BROKER = auto(),
    GENERATE_ID = auto(),
    RETRIEVE_GREENHOUSES = auto(),
    RETRIEVE_DEVICES = auto(),
    DEVICE_JOIN = auto(),
    GET_DEVICE_STATUS = auto(),
    GET_CROPS = auto(),
    SET_CROP = auto(),
    GET_DEVICES = auto(),
    SERVICE_OVERVIEW = auto(),
    SERVICE_GH_DETAIL = auto(),


class CatalogPostRequest(Enum):
    NOT_FOUND = auto(),
    REGISTER_NEW_GREENHOUSE = auto(),
    REGISTER_NEW_DEVICE = auto(),
    SIGN_UP = auto(),
    LOGIN = auto(),
    TOKEN_LOGIN = auto()
    SET_CROP = auto()


class CatalogPutRequest(Enum):
    NOT_FOUND = auto(),
    ASSOCIATE_GREENHOUSE = auto(),
    ASSOCIATE_DEVICE = auto(),
    UPDATE_DEVICE_STATUS = auto()
    UPDATE_STRATEGY = auto()


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
        if CatalogGetDispatcher._is_device_status_request(path, query):
            return CatalogGetRequest.GET_DEVICE_STATUS
        if CatalogGetDispatcher._is_get_crops_request(path, query):
            return CatalogGetRequest.GET_CROPS
        if CatalogGetDispatcher._is_get_devices_request(path, query):
            return CatalogGetRequest.GET_DEVICES
        if len(path) == 2 and path[0] == 'services' and path[1] == 'overview':
            return CatalogGetRequest.SERVICE_OVERVIEW
        if len(path) == 2 and path[0] == 'services' and path[1] == 'gh':
            return CatalogGetRequest.SERVICE_GH_DETAIL
        return CatalogGetRequest.NOT_FOUND

    @staticmethod
    def _is_get_devices_request(path, query):
        #tolto 'token' dai campi obbligatori
        return len(path) == 1 and path[0] == 'devices' and {'greenhouse_id'}.issubset(query)

    @staticmethod
    #def _is_get_crops_request(path, query):
    #    """
    #    path: crops
    #    query: (opzionale) token per UI autenticata
    #    """
    #    return len(path) == 1 and path[0] == 'crops'
    def _is_set_crop_request(path, query):
        if len(path) != 2 or path[0] != 'greenhouse' or path[1] != 'crop':
          return False
        return {'greenhouse_id', 'crop'}.issubset(query)


    @staticmethod
    def _is_device_status_request(path, query):
        """
        Retrieve current status of a device.
        path: device/status
        query: device_id
        """
        if len(path) != 2:
            return False
        if path[0] != 'device' or path[1] != 'status':
            return False
        if 'device_id' not in query:
            return False
        return True

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
        if CatalogPostDispatcher._is_set_crop_request(path, query):    # <-- NEW
            return CatalogPostRequest.SET_CROP
        return CatalogPostRequest.NOT_FOUND


    @staticmethod
    def _is_set_crop_request(path, query):
        """
        path: greenhouse/crop
        query: greenhouse_id, crop, token
        """
        if len(path) != 2 or path[0] != 'greenhouse' or path[1] != 'crop':
            return False
        return {'greenhouse_id','crop','token'}.issubset(query)

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
        query: -
        body: username, password
        auth: -
        """
        if len(path) != 1:
            return False
        if path[0] != 'signup':
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
        return True


class CatalogPutDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogPutDispatcher._is_associate_device_request(path, query):
            return CatalogPutRequest.ASSOCIATE_DEVICE
        if CatalogPutDispatcher._is_associate_greenhouse_request(path, query):
            return CatalogPutRequest.ASSOCIATE_GREENHOUSE
        if CatalogPutDispatcher._is_update_device_status_request(path, query):
            return CatalogPutRequest.UPDATE_DEVICE_STATUS
        if CatalogPutDispatcher._is_update_strategy_request(path, query):  # <-- NEW
            return CatalogPutRequest.UPDATE_STRATEGY
        return CatalogPutRequest.NOT_FOUND

    @staticmethod
    def _is_update_device_status_request(path, query):
        """
        Update current operational status of a device.
        path: device/status
        query: device_id, status, token
        """
        if len(path) != 2:
            return False
        if path[0] != 'device' or path[1] != 'status':
            return False
        if not {'device_id', 'status', 'token'}.issubset(query):
            return False
        return True

    @staticmethod
    def _is_update_strategy_request(path, query):
        """
        path: strategy
        query: greenhouse_id, update, token
        dove 'update' è una stringa JSON con i campi da modificare
        (es: {"targets":{"temperature":{"min":21,"max":27}}})
        """
        if len(path) != 1 or path[0] != 'strategy':
            return False
        #tolto 'token' dai campi obbligatori
        return {'greenhouse_id','update'}.issubset(query)

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
