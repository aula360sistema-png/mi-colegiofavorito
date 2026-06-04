from threading import local

_request_storage = local()


def get_current_request():
    return getattr(_request_storage, 'request', None)


class AuditoriaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Guardamos request globalmente
        _request_storage.request = request

        response = self.get_response(request)

        return response