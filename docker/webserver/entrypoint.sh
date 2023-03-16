#!/usr/bin/env bash
cd /opt/phenomedb_app/phenomedb
python setup.py install
cd
#pip install libchebipy "pymzml[full]"
python /opt/wait-for-redis.py
python /opt/wait-for-scheduler.py

airflow webserver --debug