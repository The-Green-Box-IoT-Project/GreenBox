from enum import Enum, auto


class CatalogRequest(Enum):
    NOT_FOUND = auto(),
    RETRIEVE_BROKER = auto(),
    GENERATE_ID = auto(),
    REGISTER_ID = auto(),
    SIGN_UP = auto(),
    LOGIN = auto(),
    TOKEN_LOGIN = auto(),


class CatalogGetDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogGetDispatcher._is_broker_request(path):
            return CatalogRequest.RETRIEVE_BROKER
        if CatalogGetDispatcher._is_generate_id_request(path, query):
            return CatalogRequest.GENERATE_ID
        return CatalogRequest.NOT_FOUND

    @staticmethod
    def _is_broker_request(path):
        if len(path) == 0:
            return False
        if path[0] != 'broker':
            return False
        return True

    @staticmethod
    def _is_generate_id_request(path, query):
        if len(path) == 0:
            return False
        if path[0] != 'generate_id':
            return False
        if not {'device_type', 'token'}.issubset(query):
            return False
        return True


class CatalogPostDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogPostDispatcher._is_register_id_request(path, query):
            return CatalogRequest.REGISTER_ID
        if CatalogPostDispatcher._is_sign_up_request(path, query):
            return CatalogRequest.SIGN_UP
        if CatalogPostDispatcher._is_login_request(path, query):
            return CatalogRequest.LOGIN
        if CatalogPostDispatcher._is_token_login_request(path, query):
            return CatalogRequest.TOKEN_LOGIN
        return CatalogRequest.NOT_FOUND

    @staticmethod
    def _is_register_id_request(path, query):
        if len(path) != 1:
            return False
        if path[0] != 'register_id':
            return False
        if not {'device_id', 'token'}.issubset(query):
            return False
        return True

    @staticmethod
    def _is_sign_up_request(path, query):
        if len(path) != 1:
            return False
        if path[0] != 'signup':
            return False
        if not {'username', 'password', 'repeat_password'}.issubset(query):
            return False
        return True

    @staticmethod
    def _is_login_request(path, query):
        if len(path) != 1:
            return False
        if path[0] != 'login':
            return False
        if {'username', 'password'}.issubset(query):
            return True
        return False

    @staticmethod
    def _is_token_login_request(path, query):
        if len(path) != 1:
            return False
        if path[0] != 'login':
            return False
        if 'token' in query:
            return True
        return False


class CatalogPutDispatcher:
    @staticmethod
    def dispatch(path, query):
        pass


class CatalogDeleteDispatcher:
    @staticmethod
    def dispatch(path, query):
        pass
