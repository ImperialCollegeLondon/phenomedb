
from flask import Flask
from flask_appbuilder import AppBuilder, SQLA

import sys
import logging
import os

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append(  os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config

"""
 Logging configuration
"""
logger = logging.getLogger('API')

log_dir = config['LOGGING']['dir']
log_file = os.path.join(log_dir, 'api.log')

os.makedirs(log_dir, exist_ok=True)
fh = logging.FileHandler(log_file, mode="a", encoding="utf-8", delay=False)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
fh.setFormatter(formatter)

logger.setLevel(logging.DEBUG)


app = Flask(__name__)
app.config.from_envvar('FLASK_CONFIG')
db = SQLA(app)
appbuilder = AppBuilder(app, db.session)

from . import import_api  # noqa
from . import model_api
from . import saved_query_api

