import sys,os

class PrefixMiddleware(object):
    """Custom prefix middleware to handle url prefixes

    :param object: Flask App
    :type object: `Flask.App`
    """    

    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):

        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]

from app import app
app.wsgi_app = PrefixMiddleware(app.wsgi_app, app.config['APPLICATION_ROOT'])

if __name__ == "__main__":
    app.run()