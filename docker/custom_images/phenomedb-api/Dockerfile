# cd docker/custom_images/phenomedb-api
# docker build -t ghaggart/phenomedb-api .
# docker push ghaggart/phenomedb-api

# ap && cd docker/custom_images/phenomedb-api && docker build -t ghaggart/phenomedb-api . && docker push ghaggart/phenomedb-api

FROM ghaggart/phenomedb-airflow

COPY ./fab-api-manager-custom.py /home/airflow/.local/lib/python3.6/site-packages/flask_appbuilder/api/manager.py

USER root
RUN chown airflow /home/airflow/.local/lib/python3.6/site-packages/flask_appbuilder/api/manager.py
USER airflow