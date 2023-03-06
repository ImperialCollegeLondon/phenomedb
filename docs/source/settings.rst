Settings
========

Settings in PhenomeDB are configured in different ways depending if PhenomeDB is being run via docker compose or not.

No docker -> ./data/config/config.ini
With docker -> ./.env

Apache Airflow settings can be configured with the following syntax:

AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth

PhenomeDB settings can be set in the same format:

PHENOMEDB__GROUP__SETTING=example

The .env-example file contains the recommended Airflow and ChemSpider settings, but they can be adjusted as required.

The config.ini file contains the following groups and settings:

TEST
----
username = admin # The user account used during unit tests

DB
--
dir = /Library/PostgreSQL/12/data/ # The directory used for storing Postgres data

rdbms = postgresql # The RDBMS to use (only supports Postgres currently)

user = postgres # The production database username

password = testpass # The database password

host = 127.0.0.1 # The database host

name = phenomedb # The database name

test = phenomedb_test # The test database name

port = 5433 # The database port

pool_size = 10 # The database pool size (SQLAlchemy)

max_overflow = 20 # The database max overflow

create_script = ./sql/phenomedb_v0.9.5_postgres.sql # The database create script


WEBSERVER
---------
url = http://localhost:8080/ # The URL of the webserver

API
---
custom_root = custom # The url root of the custom API

REDIS
-----
port = 6380 # The port of the Redis server

host = 127.0.0.1 # The host of the Redis server

user = default # The user of the Redis server

password = password # The password of the Redis server

memory_expired_seconds = 86400 # The time to expire cache objects from Redis


R
-
exec_path = /usr/local/bin/R # The R executable path

script_directory = /full/path/to/appdata/r_scripts/ # The R script directory

SMTP
----
enabled = true # Whether SMTP is configured

host = host # SMTP host

port = 25 # SMTP port

user = user # SMTP user

password = password # SMTP password

from = Name <emailaddress> # SMTP from address


DATA
----
project_data_base_path = /path/to/projectdata/ # The base path to the project related data (if used)

app_data = /full/path/to/appdata/ # The directory to store the application data

test_data = /full/path/to/data/test/ # The directory containing the test data

compounds = /full/path/to/data/compounds/ # The directory containing the compound data

config = /full/path/to/data/config/ # The directory containing the configs

cache = /full/path/to/appdata/cache/ # The cache directory


API_KEYS
--------
chemspider = api_key # The ChemSpider API key

LOGGING
-------
dir = /tmp/phenomelog/ # The logging directory

PIPELINES
---------
pipeline_manager = apache-airflow # Only Apache-Airflow currently supported

pipeline_folder = /full/path/to/dags # The path to the Airflow DAGs folder

pipeline_manager_user = admin # The Airflow user to trigger pipelines

pipeline_manager_password = testpass # The Airflow user password for triggering pipelines

pipeline_manager_api_host = localhost:8080 # The Airflow API host URL

task_spec_file = /full/path/to/data/config/task_typespec.json # The task_typespec.json file

docker = false # Whether using docker or not
