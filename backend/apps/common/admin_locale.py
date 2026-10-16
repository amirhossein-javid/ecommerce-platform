from django.utils import translation


class AdminPersianLocaleMiddleware:
    """Activate Persian only for Django Admin without changing API responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/admin" or request.path.startswith("/admin/"):
            with translation.override("fa"):
                return self.get_response(request)
        return self.get_response(request)
