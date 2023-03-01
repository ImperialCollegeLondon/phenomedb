Usage
=====

PhenomeDB is a relatively complex application consisting of the following sub-systems:

A. Postgres database
B. Python library with modules for importing, harmonising, querying, normalising, and analysing the data. The code in these modules is organised into 'tasks' that can be chained together into pipelines using the PipelineFactory.
C. Redis cache (with a file-system backend extension) for storing query sets and analysis results
D. Apache-Airflow for running pipelines
E. Flask plugins for exploring the data, building queries, running analyses, and visualising results

These subsystems can be installed separately, however to simplify the usage of these interacting components, they have been docker-ised.

Installation
------------

To use PhenomeDB locally, install docker, download the repo, copy the .env-example file to a file called .env, edit the parameters as required, and then run

.. code-block:: console

   $ git clone git@github.com:ghaggart/phenomedb.git
   $ cd phenomedb
   $ cp .env-example .env
   $ docker compose up

The Apache-Airflow interface
----------------------------

To access Apache-Airflow, once the system is running, open your web browser and navigate to http://localhost:8080/. The default username and password are admin and testpass.

From here, pipelines for individual tasks can be parameterised, executed, and monitored, and the various PhenomeDB views can be accessed.

Importing data
--------------

Two main data import sources are supported - Metabolights, and the NPYC format, consisting of  
