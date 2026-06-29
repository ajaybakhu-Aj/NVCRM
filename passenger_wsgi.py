import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

try:
    import crm_erp.wsgi
    application = crm_erp.wsgi.application
except Exception as e:
    import traceback
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [traceback.format_exc().encode('utf-8')]
