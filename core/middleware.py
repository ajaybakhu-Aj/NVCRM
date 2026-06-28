from django.shortcuts import redirect
from django.contrib import messages

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
from .models import SystemLog, SystemUserProfile

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

class PageAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Mapping route prefixes to permission fields. Order matters for overlapping paths.
        access_map = [
            ('/attendance/payroll/', 'can_access_staff_payroll'),
            ('/attendance/', 'can_access_time_attendance'),
            ('/notice_board/', 'can_access_notice_board'),
            ('/leave/', 'can_access_leave'),
            ('/users/', 'can_access_profiles'),
            ('/leads/', 'can_access_lead_pipeline'),
            ('/inventory/', 'can_access_inventory'),
            ('/accounts/', 'can_access_accounts_receivable'),
            ('/pos/', 'can_access_pos'),
            ('/procurement/', 'can_access_procurement'),
            ('/task_board/', 'can_access_task_board'),
            ('/system_log/', 'can_access_system_log'),
            ('/dashboard/', 'can_access_dashboard'),
        ]
        
        logged_in_uid = request.session.get('logged_in_uid')
        if logged_in_uid and not any(path.startswith(url) for url in ['/login/', '/logout/', '/admin/', '/static/', '/media/']):
            user = SystemUserProfile.objects.filter(uid=logged_in_uid).first()
            if user:
                for route, perm_field in access_map:
                    if path.startswith(route):
                        has_access = getattr(user, perm_field, False)
                        if not has_access:
                            messages.error(request, 'Access Denied: You do not have permission to view this page.')
                            if path == '/dashboard/':
                                return redirect('login')
                            return redirect('dashboard')
                        break
                        
        response = self.get_response(request)
        return response
