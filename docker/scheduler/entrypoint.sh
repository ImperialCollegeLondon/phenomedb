#!/usr/bin/env bash

rm -rf /opt/system/scheduler_ready
pip install libchebipy "pymzml[full]"
python /opt/wait-for-redis.py
airflow db init
airflow db upgrade
airflow users create -u $AIRFLOW_ADMIN_USER -p $AIRFLOW_ADMIN_PASSWORD -f admin -l admin -r Admin -e $AIRFLOW_ADMIN_EMAIL
python /opt/phenomedb_app/phenomedb/cli.py pipelines.GenerateSingleTaskPipelines
python /opt/phenomedb_app/phenomedb/cli.py pipelines.BasicSetup
touch /opt/system/scheduler_ready
airflow scheduler
