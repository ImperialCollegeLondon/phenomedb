Usage
=====

PhenomeDB is a database, data processing, and analysis and visualisation platform for metabolomics data. The general usage of which is outlined below, where users import data, harmonise the data, build queries to integrate and stratify the data, scale, normalise, and batch correct the data, and run analyses and reports to analyse, visualise, and interpret the data. PhenomeDB provides python APIs and web-based UIs for these steps, including a novel QueryFactory for building and executing queries, and a novel PipelineFactory for building and executing pipelines via Apache-Airflow.

.. figure:: ./_images/method-development-overview.png
  :width: 400
  :alt: PhenomeDB usage overview

  Overview of using PhenomeDB, including import, harmonisation, querying, scaling/normalisation, and analysis/visualisation.

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

Core data model and mappings
----------------------------
.. figure:: ./_images/source-to-model.png
  :width: 600
  :alt: Mappings between 3-file format at PhenomeDB

  Mappings between a 3-file format metabolomics dataset and the PhenomeDB core data model

The Apache-Airflow interface
----------------------------

To access Apache-Airflow, once the system is running, open your web browser and navigate to http://localhost:8080/. The default username and password are admin and testpass.

From here, pipelines ('DAGs' in Airflow) for individual tasks can be parameterised, executed, and monitored, and the various PhenomeDB views can be accessed.

Apache-Airflow is structured around the concepts of pipelines and pipeline runs (executions). You parameterise a pipeline run and then Airflow manages the execution. Output logs for each task in the pipeline can be inspected via the interface.

For more information regarding the usage of Apache-Airflow, please see the Apache-Airflow documentation.

.. figure:: ./_images/airflow-ui-1.png
  :width: 600
  :alt: Airflow UI home

  Airflow home page showing registered pipelines

.. figure:: ./_images/airflow-ui-2.png
  :width: 600
  :alt: Airflow Pipeline Overview

  Graphical view of the ImportPeakPantherAnnotations pipeline

.. figure:: ./_images/airflow-ui-3.png
  :width: 600
  :alt: Airflow Run Pipeline

  View for running a pipeline, with example JSON for parameterising the import task.

.. figure:: ./_images/airflow-ui-4.png
  :width: 600
  :alt: Airflow Logs example

  Example output of the TaskRun logs, viewed from within the Airflow interface


Importing analytical data and sample metadata
---------------------------------------------

Two main analytical data import sources are supported - Metabolights format, and the NPYC format, consisting of 3 separate sources of information:

A. Sample manifests: CSV files containing sample metadata subject as clinical factors, outcomes-of-interest, or covariates.
B. PeakPantheR ROI files: CSV files containing feature metadata such as annotated compound information.
C. Study data files: CSV files containing analytical features (measurements) relating to the samples and features/annotated compounds

Importing Metabolights data

Importing nPYc format data


Harmonising sample metadata
---------------------------

In order to compare, integrate, and stratify data across multiple cohorts, the sample metadata must be harmonised. To do this, it is recommended to use the CurateMetadataTask, which enables the curation of unharmonised 'raw' metadata fields and values into harmonised 'curated' metadata fields and values.

.. figure:: ./_images/curate-metadata-task.png
  :width: 600
  :alt: PhenomeDB CurateMetadata task

  The CurateMetadataTask architecture, with methods for harmonising types, names, and values

Importing compound metadata
---------------------------

PhenomeDB enables the storage of annotation metadata such as chemical references and classes, and has a data model and import processes capable of harmonising annotations to their analytical specificity.

The minimum information required for import is compound name (as annotated) and InChI (if available). If the specificity of the annotation is low, multiple compounds and InChIs can be recorded per annotation. With this minimum information, PhenomeDB can lookup and record the following external references and classes and make them queryable and reportable.

Databases: PubChem, ChEBI, ChEMBL, ChemSpider, LipidMAPS, HMDB

Classes: LipidMAPS, HMDB, ClassyFIRE

.. figure:: ./_images/compound-task-overview.png
  :width: 600
  :alt: PhenomeDB ImportCompoundTask overview

  The ImportCompoundTask overview, which looks up compound metadata and populates the database

Compound metadata can be imported from PeakPantheR region-of-interest files (ROI) files for LC-MS annotations. Recent versions for these can be found in ./data/compounds/.

To import the ROI compound data use the tasks ImportROICompounds and ImportROILipids

IVDr annotation metadata can be imported using ImportBrukerBiLISACompounds and ImportBrukerBiQuantCompounds,. The source data are available in ./data/compounds/

Once imported, compounds and compound classes can be explored using the Compound View UI.

.. figure:: ./_images/compound-list-view.png
  :width: 600
  :alt: PhenomeDB Compound List View

  The Compound List View, showing a searchable, paginated table of imported compounds

.. figure:: ./_images/compound-view-example.png
  :width: 600
  :alt: PhenomeDB Compound View

  The Compound View, showing the imported information for one compound, with links to external databases

Harmonising annotation metadata
-------------------------------

In order to integrate annotations across projects, the annotations must be harmonised. PhenomeDB will attempt to do this automatically where possible, however in some cases it is necessary to manually harmonise annotations. To do this use the 'Harmonise Annotations' view.

.. figure:: ./_images/manual-annotation-harmonisation-view.png
  :width: 600
  :alt: PhenomeDB manual annotation harmonisation

  The Harmonise Annotations View, where unharmonised annotations can be harmonised manually to enable cross-project comparisons



Creating queries
----------------

Creating queries can be done either via the Query Factory view or the QueryFactory Python API. In PhenomeDB Queries are created by chaining QueryFilter objects containing boolean operators and QueryMatches, which specifying the fields and comparison operators and values. An overview of this can be seen below. With the collection of QueryFilters and QueryMatches, the QueryFactory then calculates/transpiles the query definition into an SQLAlchemy query, and executes the query. The QueryFactory can then construct a combined-format and 3-file format dataset of the results, and store them in the Query Cache.

.. figure:: ./_images/query-filters-overview.png
  :width: 600
  :alt: PhenomeDB QueryFactory QueryFilters and QueryMatches

  The QueryFilter and QueryMatch architecture

An example of using these to construct a query is shown here:

.. code-block:: python

    query_factory = QueryFactory(query_name='Users under 40', query_description='test description')
    query_factory.add filter(model='Project', property='name', operator='eq ', value='My Project')
    filter = QueryFilter(model='HarmonisedMetadataField',property='name',operator='eq', value='Age')
    filter.add_match(model='MetadataValue',property='harmonised numeric value',operator='lt', value=40)
    query factory.add_filter(query_filter=filter)

To simplify querying MetadataFields and HarmonisedMetadataFields, the following MetadataFilter can be used

.. code-block:: python

    query factory = QueryFactory(query_name='Users under 40', query_description='test description')
    query factory.add filter(QueryFilter(model='Project',property='name',operator='eq',value='My Project') )
    query factory.add filter(MetadataFilter('Age','lt',value=40))
    #4. Save the query in the SavedQuery data model
    query factory.save_query()

.. figure:: ./_images/query-filters-overview.png
  :width: 600
  :alt: PhenomeDB QueryFactory QueryFilters and QueryMatches

  The QueryFilter and QueryMatch architecture







Running analyses
----------------

Implemented analysis functions include:

A. PCA via the RunPCA task
B. PCPR2 via the RunPCPR2 task
C. MWAS via the RunMWAS task

Tasks and Pipelines
-------------------

Major processing steps including import, harmonisation, integration, analysis are structured into repeatable and reusable 'tasks'. These tasks can then be organised into 'pipelines' using the PipelineFactory and registered to and executed and monitored by Apace-Airflow. When a task is executed it records a TaskRun object in the database with information regarding the parameters used. Task outputs are stored in the persistent cache for later use.

Pipelines can be created, registered with Airflow, and executed via the PipelineFactory. Using this approach removes the requirements for manually writing Airflow DAG files.

.. figure:: ./_images/pipeline-factory-overview.png
  :width: 500
  :alt: PhenomeB PipelineFactory Overview

  Overview of how the PipelineFactory can be used to create Apache Airflow pipelines


.. figure:: ./_images/backfill-annotations-pipeline-overview.png
  :width: 500
  :alt: PhenomeB Pipeline Example

  Example of using a task to create a Pipeline, using the PipelineFactory to chain tasks together and register it with Airflow
