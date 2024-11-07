from enum import Enum, auto


class CatalogRequest(Enum):
    NOT_FOUND = auto(),
    RETRIEVE_BROKER = auto(),
    SIGN_UP = auto(),
    LOGIN = auto(),
    TOKEN_LOGIN = auto(),


class CatalogGetDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogGetDispatcher._is_broker_request(path):
            return CatalogRequest.RETRIEVE_BROKER
        return CatalogRequest.NOT_FOUND

    @staticmethod
    def _is_broker_request(path):
        if len(path) == 0:
            return False
        if path[0] == 'broker':
            return True
        return False


class CatalogPostDispatcher:
    @staticmethod
    def dispatch(path, query):
        if CatalogPostDispatcher._is_sign_up_request(path, query):
            return CatalogRequest.SIGN_UP
        if CatalogPostDispatcher._is_login_request(path, query):
            return CatalogRequest.LOGIN
        if CatalogPostDispatcher._is_token_login_request(path, query):
            return CatalogRequest.TOKEN_LOGIN
        return CatalogRequest.NOT_FOUND

    @staticmethod
    def _is_sign_up_request(path, query):
        if len(path) != 1:
            return False
        if path[0] != 'signup':
            return False
        if {'username', 'password', 'repeat_password'}.issubset(query):
            return True
        return False

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
