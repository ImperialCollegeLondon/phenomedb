#!/usr/bin/env bash

pip install libchebipy
python /opt/wait-for-redis.py
python /opt/wait-for-scheduler.py

airflow webserver --debug