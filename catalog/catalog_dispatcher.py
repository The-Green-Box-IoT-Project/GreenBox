from enum import Enum, auto


class CatalogRequest(Enum):
    NOT_FOUND = auto(),
    RETRIEVE_BROKER = auto(),


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
        pass


class CatalogPutDispatcher:
    @staticmethod
    def dispatch(path, query):
        pass


class CatalogDeleteDispatcher:
    @staticmethod
    def dispatch(path, query):
        pass
