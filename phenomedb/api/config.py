
import os,sys
from flask_appbuilder.security.manager import AUTH_DB

AUTH_TYPE = AUTH_DB

basedir = os.path.abspath(os.path.dirname(__file__))

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

if 'PHENOMEDB__API__ROOT' in os.environ:
    APPLICATION_ROOT = os.environ['PHENOMEDB__API__ROOT']
else:
    APPLICATION_ROOT = "/"

#SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://' + os.environ['POSTGRES_USER'] + ':' + os.environ['POSTGRES_PASSWORD'] + '@postgres:5432/phenomedb'

FAB_API_SWAGGER_UI=True

SECRET_KEY = 'supersecretkey'

CSRF_ENABLED = True