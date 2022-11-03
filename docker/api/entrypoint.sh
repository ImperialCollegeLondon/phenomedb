#!/usr/bin/env bash

python /opt/wait-for-redis.py
python /opt/wait-for-scheduler.py

cd /opt/phenomedb_app/phenomedb/api

export FLASK_CONFIG="/opt/phenomedb_app/phenomedb/api/config.py"

export FLASK_APP=app/__init__.py

flask fab create-admin --username $AIRFLOW_ADMIN_USER --password $AIRFLOW_ADMIN_PASSWORD --firstname admin --lastname admin --email $AIRFLOW_ADMIN_EMAIL

gunicorn --reload --bind 0.0.0.0:5000 wsgi:app
#flask run --host=0.0.0.0

