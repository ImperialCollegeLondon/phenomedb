# docker build -t phenomedb/phenomedb-api .
# docker push phenomedb/phenomedb-api

# both arm64 and x86
# docker buildx build --platform linux/amd64,linux/arm64 -t phenomedb/phenomedb-api:latest --push ./docker/custom_images/phenomedb-api/

FROM phenomedb/phenomedb-airflow

COPY ./fab-api-manager-custom.py /home/airflow/.local/lib/python3.9/site-packages/flask_appbuilder/api/manager.py

USER root
RUN chown airflow /home/airflow/.local/lib/python3.9/site-packages/flask_appbuilder/api/manager.py
USER airflow