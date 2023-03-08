Installation
============

The various PhenomeDB components can be installed separately, however to simplify the usage of these interacting components, they have been docker-ised.

Local/desktop installation
------------------

1. Install docker
2. Download the repo
3. cd into the repo directory
4. Copy the ./data/config/config.ini.example to ./data/config/config.ini
5. Copy the .env-example file to a file called .env, and edit the parameters as required (see settings)
6. cd into the directory and run docker-compose up

.. code-block:: console

   $ git clone git@github.com:ghaggart/phenomedb.git
   $ cd phenomedb
   $ cp ./data/config/config.ini.example ./data/config/config.ini
   $ cp .env-example .env
   $ docker compose up

The minimum settings that need configuring are:

PHENOMEDB__REDIS__PASSWORD

PHENOMEDB__PIPELINES__PIPELINE_MANAGER_USER

PHENOMEDB__PIPELINES__PIPELINE_MANAGER_PASSWORD

PHENOMEDB__API_KEYS__CHEMSPIDER

POSTGRES_USER

POSTGRES_PASSWORD

AIRFLOW_ADMIN_USER

AIRFLOW_ADMIN_PASSWORD

AIRFLOW_ADMIN_EMAIL

AIRFLOW__DATABASE__SQL_ALCHEMY_CONN

AIRFLOW__CORE__FERNET_KEY


Settings
========

Settings in PhenomeDB are configured in different ways depending if PhenomeDB is being run via docker compose or not.

No docker -> ./data/config/config.ini

With docker -> ./.env

Apache Airflow settings can be configured with the following syntax:

.. code-block:: console

    AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth

PhenomeDB settings can be set in the same format:

.. code-block:: console

    PHENOMEDB__GROUP__SETTING=example

The .env-example file contains the recommended Airflow and ChemSpider settings, but they can be adjusted as required.

The config.ini file contains the following groups and settings:

TEST
----
.. code-block:: console

    username = admin # The user account used during unit tests

DB
--
.. code-block:: console

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
.. code-block:: console

    url = http://localhost:8080/ # The URL of the webserver

API
---
.. code-block:: console

    custom_root = custom # The url root of the custom API

REDIS
-----
.. code-block:: console

    port = 6380 # The port of the Redis server
    host = 127.0.0.1 # The host of the Redis server
    user = default # The user of the Redis server
    password = password # The password of the Redis server
    memory_expired_seconds = 86400 # The time to expire cache objects from Redis

R
-
.. code-block:: console

    exec_path = /usr/local/bin/R # The R executable path
    script_directory = /full/path/to/appdata/r_scripts/ # The R script directory

SMTP
----
.. code-block:: console

    enabled = true # Whether SMTP is configured
    host = host # SMTP host
    port = 25 # SMTP port
    user = user # SMTP user
    password = password # SMTP password
    from = Name <emailaddress> # SMTP from address

DATA
----
.. code-block:: console

    project_data_base_path = /path/to/projectdata/ # The base path to the project related data (if used)
    app_data = /full/path/to/appdata/ # The directory to store the application data
    test_data = /full/path/to/data/test/ # The directory containing the test data
    compounds = /full/path/to/data/compounds/ # The directory containing the compound data
    config = /full/path/to/data/config/ # The directory containing the configs
    cache = /full/path/to/appdata/cache/ # The cache directory

API_KEYS
--------
.. code-block:: console

    chemspider = api_key # The ChemSpider API key

LOGGING
-------
.. code-block:: console

    dir = /tmp/phenomelog/ # The logging directory

PIPELINES
---------
.. code-block:: console

    pipeline_manager = apache-airflow # Only Apache-Airflow currently supported
    pipeline_folder = /full/path/to/dags # The path to the Airflow DAGs folder
    pipeline_manager_user = admin # The Airflow user to trigger pipelines
    pipeline_manager_password = testpass # The Airflow user password for triggering pipelines
    pipeline_manager_api_host = localhost:8080 # The Airflow API host URL
    task_spec_file = /full/path/to/data/config/task_typespec.json # The task_typespec.json file
    docker = false # Whether using docker or not

