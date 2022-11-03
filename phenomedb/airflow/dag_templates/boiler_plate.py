#################################################
#
#     PhenomeDB PipelineFactory Airflow Pipeline
#
#     Pipeline ID: {{ pipeline.id }}
#     Pipeline name: {{ pipeline.name }}
#     Description: {{ pipeline.description }}
#     Created by: {{ pipeline.user_created }}
#     Date created: {{ pipeline.date_created }}
#
#################################################

import sys,os
from airflow import DAG
from airflow.decorators import task
from airflow import AirflowException
from airflow.operators.python import get_current_context
from pathlib import Path
import math
import datetime

if os.environ['PHENOMEDB_PATH'] not in sys.path:
   sys.path.append(  os.environ['PHENOMEDB_PATH'])

with DAG(
    "{{ pipeline.name }}",
    start_date=datetime.datetime.fromtimestamp({{ start_timestamp }}),
    default_args={{ pipeline.default_args }},
    description="{{ pipeline.description }}",
    max_active_runs={{ pipeline.max_active_runs }},
    concurrency={{ pipeline.concurrency }},
    tags={{ pipeline.tags }},
    {% if pipeline.schedule_interval == 'None' %}schedule_interval={{ pipeline.schedule_interval }},{% else %}schedule_interval="{{ pipeline.schedule_interval }}",{% endif %}
) as dag:

