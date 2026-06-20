from django.shortcuts import redirect

class AuthRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exempt_urls = ['/login/', '/admin/', '/static/', '/media/']
        if not any(request.path.startswith(url) for url in exempt_urls):
            if not request.session.get('logged_in_uid'):
                return redirect('login')
        response = self.get_response(request)
        return response
