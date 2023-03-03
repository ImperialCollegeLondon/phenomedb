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

Apache-Airflow is structured around the concepts of pipelines and pipeline runs (executions). You parameterise a pipeline run and then Airflow manages the execution. Output logs for each task in the pipeline can be inspected via the interface.

For more information regarding the usage of Apache-Airflow, please see the Apache-Airflow documentation.

Importing data
--------------

Two main data import sources are supported - Metabolights format, and the NPYC format, consisting of 3 separate sources of information:

A. Sample manifests: CSV files containing sample metadata subject as clinical factors, outcomes-of-interest, or covariates.
B. PeakPantheR ROI files: CSV files containing feature metadata such as annotated compound information.
C. Study data files: CSV files containing analytical features (measurements) relating to the samples and features/annotated compounds

Importing Metabolights data

Importing nPYc format data

Harmonising sample metadata
---------------------------

In order to compare, integrate, and stratify data across multiple cohorts, the sample metadata must be harmonised. To do this, it is recommended to use the curate_metadata task.

Harmonising annotation metadata
-------------------------------

In order to integrate annotations across projects, the annotations must be harmonised. PhenomeDB will attempt to do this automatically where possible, however in some cases it is necessary to manually harmonise annotations. To do this use the 'Harmonise Annotations' view.

Creating queries
----------------

Creating queries can be done either via the Query Factory view or the QueryFactory() class.

Running analyses
----------------

Implemented analysis functions include:

A. PCA via the RunPCA task
B. PCPR2 via the RunPCPR2 task
C. MWAS via the RunMWAS task


