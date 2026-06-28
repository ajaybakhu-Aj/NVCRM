import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

def application(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return [b"Hello from Passenger! If you see this, the Python app is running."]
