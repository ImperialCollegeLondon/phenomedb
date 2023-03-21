Installation
============

The various PhenomeDB components can be installed separately, however to simplify the usage of these interacting components, they have been docker-ised.

Local/desktop Docker installation
---------------------------------

1. Install docker
2. Download the repo
3. cd into the repo directory
4. Copy the .env-example file to a file called .env, and edit the parameters as required (see settings)
5. cd into the directory and run docker-compose up

.. code-block:: console

   $ git clone git@github.com:phenomecentre/phenomedb.git
   $ cd phenomedb
   $ cp .env-example .env
   $ vim .env # or whichever text editor
   $ docker compose up

Python installatiion
--------------------

Python installation is necessary for local IDE debugging of unit tests and building the docs.

.. warning::
  Mac Mx or other ARM-based chips are not currently supported for local installation due to dependency hell. If you are running a Mac Mx chip, use one of the phenomedb-airflow containers to run the tests and build the docs

To install the phenomedb library locally:

1. Checkout the repo
2. install the pip requirements (inside a virtualenv or conda env)
3. run setup.py install
4. Either run the docker compose separately or install postgres and redis according to your OS instructions.
5. Test the installation by running the phenomedb cli.py -h command

.. code-block:: console

  $ python setup.py install # this will fail the first time, run it twice
  $ python setup.py install
  $ docker compose up -d postgres redis
  $ cd phenomedb
  $ python cli.py -h

If it the cli.py -h command shows you a list of available tasks, the installation is working.

Running the tests
-----------------

The tests can be run using pytest.

Using the local install:

.. code-block:: console

  $ docker compose up postgres redis
  $ cd tests
  $ pytest .

Using a phenomedb-airflow docker container:

.. code-block:: console

  $ docker compose up -d
  $ docker exec -it phenomedb-scheduler-1 /bin/bash
  $ cd /opt/phenomedb_app/phenomedb/
  $ pytest tests/

Building the docs
-----------------

The docs are hosted on readthedocs, but must be built locally before upload (due to the postgres and redis dependencies). The sphinx and sphinx-rtd-theme pip packages are required to build the docs. To upload them to readthedocs, simply push them to the repo.

.. code-block:: console

  $ cd docs
  $ make clean && make html
  $ cd ..
  $ git add . -A
  $ git commit -m 'updated docs'
  $ git push

Settings
========

Settings in PhenomeDB are configured in different ways depending if PhenomeDB is being run via docker compose or not.

Local Python Installation
-------------------------

When running the phenomedb python library from a local host (instead of Docker), the configuration is controlled by the ./data/config/default-config.ini file. The configuration can be overriden by either copying this file to the same directory with the name config.ini, or by copying it a location on your machine and specifying the PHENOMEDB_CONFIG environment variable.

.. code-block::bash

  $ cp ./data/config/default-config.ini ./data/config/config.ini
  $ vim ./data/config/config.ini # or whichever text editor

.. code-block::bash

  $ cp ./data/config/default-config.ini /opt/phenomedb/config.ini
  $ vim /opt/phenomedb/config.ini # or whichever text editor
  $ PHENOMEDB_CONFIG=/opt/phenomedb/config.ini

Docker installation
-------------------
When running PhenomeDB from docker compose, you can edit the user-copied (during installation) env file ./.env. This file defines the environment variables inside the docker containers, and overrides the values in config.ini and default-config.ini..

Apache Airflow settings can be configured with the following syntax:

.. code-block:: console

    AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth

PhenomeDB settings can be set in the same format:

.. code-block:: console

    PHENOMEDB__GROUP__SETTING=example

The .env-example file contains the recommended Airflow and ChemSpider settings, but they can be adjusted as required.

The config.ini file contains the following groups and settings:


To use the ImportCompoundTask compound lookup functionality the following setting must be configured to use chemspider by obtaining a chemspider api key:

PHENOMEDB__API_KEYS__CHEMSPIDER

The following settings are recommended to be changed however the defaults will work.

PHENOMEDB__REDIS__PASSWORD

PHENOMEDB__PIPELINES__PIPELINE_MANAGER_USER

PHENOMEDB__PIPELINES__PIPELINE_MANAGER_PASSWORD

POSTGRES_USER

POSTGRES_PASSWORD

AIRFLOW_ADMIN_USER

AIRFLOW_ADMIN_PASSWORD

AIRFLOW_ADMIN_EMAIL

AIRFLOW__DATABASE__SQL_ALCHEMY_CONN

AIRFLOW__CORE__FERNET_KEY



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

