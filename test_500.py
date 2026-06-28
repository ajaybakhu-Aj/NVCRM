import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_erp.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from core.views import ProjectTaskBoardView
from core.models import SystemUserProfile
import traceback

try:
    factory = RequestFactory()
    request = factory.get('/task_board/')
    
    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    
    # Add messages
    msg_middleware = MessageMiddleware(lambda r: None)
    msg_middleware.process_request(request)
    
    user = SystemUserProfile.objects.first()
    if user:
        request.session['logged_in_uid'] = user.uid
        request.session['logged_in_name'] = user.full_name
        request.session['active_role'] = user.position
    
    from core.views import ProjectTaskBoardView
    view = ProjectTaskBoardView.as_view()
    response = view(request)
    
    if hasattr(response, 'render'):
        response.render()
        print("Render successful. Status:", response.status_code)
    else:
        print("Response returned:", response.status_code, getattr(response, 'url', ''))
except Exception:
    traceback.print_exc()
