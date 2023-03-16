.. _development:

Development
===========

PhenomeDB is designed to be highly extensible to new methods.

Core platform architecture
--------------------------
PhenomeDB is a relatively complex application consisting of the following sub-systems:

A. Postgres database
B. Python library with modules for importing, harmonising, querying, normalising, and analysing the data. The code in these modules is organised into 'tasks' that can be chained together into pipelines using the PipelineFactory.
C. Redis cache (with a file-system backend extension) for storing query sets and analysis results
D. Apache-Airflow for running pipelines
E. Flask plugins for exploring the data, building queries, running analyses, and visualising results

.. figure:: ./_images/phenomedb-software-main-components.png
  :width: 500
  :alt: PhenomeDB core architecture

  PhenomeDB core architectural components (note that important components Redis and the file-system are not shown here)


Adding tasks
------------

Tasks are added to the CLI and UI via the ./data/config/task_spec.json file.

To add new task...
