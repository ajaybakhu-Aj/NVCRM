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

from django.utils.deprecation import MiddlewareMixin
from .models import SystemLog

class SystemLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.method == 'POST':
            user_name = request.session.get('logged_in_name', 'Unknown User')
            path = request.path
            action = request.POST.get('action', '')
            
            if 'login' in path.lower():
                action_name = "System Login"
                user_name = request.POST.get('username', 'Unknown User')
            elif 'logout' in path.lower():
                action_name = "System Logout"
            elif action:
                action_name = f"{action.replace('_', ' ').title()}"
            else:
                # Guess action from path
                action_name = f"Data Submitted to {path}"

            # Prepare details by stripping sensitive info
            post_data = request.POST.copy()
            post_data.pop('csrfmiddlewaretoken', None)
            post_data.pop('password', None)
            
            details = ", ".join([f"{k}: {v}" for k, v in post_data.items() if 'password' not in k.lower()])
            if not details:
                details = "No additional data."

            try:
                SystemLog.objects.create(
                    user_name=user_name,
                    action=action_name,
                    details=details[:1000]
                )
            except Exception:
                pass
