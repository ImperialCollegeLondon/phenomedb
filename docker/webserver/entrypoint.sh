#!/usr/bin/env bash


python /opt/wait-for-redis.py
python /opt/wait-for-scheduler.py

airflow webserver --debug