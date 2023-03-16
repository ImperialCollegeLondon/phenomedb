.. _usage:

Usage
=====

PhenomeDB is a database, data processing, and analysis and visualisation platform for metabolomics data. The general usage of which is outlined below, where users import data, harmonise the data, build queries to integrate and stratify the data, scale, normalise, and batch correct the data, and run analyses and reports to analyse, visualise, and interpret the data. PhenomeDB provides python APIs and web-based UIs for these steps, including a novel QueryFactory for building and executing queries, and a novel PipelineFactory for building and executing pipelines via Apache-Airflow.

.. figure:: ./_images/method-development-overview.png
  :width: 400
  :alt: PhenomeDB usage overview

  Overview of using PhenomeDB, including import, harmonisation, querying, scaling/normalisation, and analysis/visualisation.

Tasks
-----

PhenomeDB is structured around the concept of a :ref:`phenomedb.task`. Tasks are units of work that execute a specific function, such as importing annotations, harmonising metadata, or generating datasets on the basis of defined Queries. Tasks can be executed independently, or chained together into Pipelines using the PipelineFactory python API or UI. A full list of included Tasks is shown below, and guides to implementing new tasks can be in :ref:`development`.

The inbuilt tasks for PhenomeDB are shown below. To view their parameters, follow the links to the relevant documentation page:

:func:`phenomedb.compounds.ExportCompoundsToCSV`
:func:`phenomedb.compounds.ParseKEGGtoPubchemCIDTask`
:func:`phenomedb.compounds.ParseHMDBXMLtoCSV`
:func:`phenomedb.compounds.UpdateCompoundRefs`
:func:`phenomedb.compounds.AddMissingClassyFireClasses`
:func:`phenomedb.compounds.CleanROIFile`
:func:`phenomedb.compounds.ImportROICompounds`
:func:`phenomedb.compounds.ImportBrukerBILISACompounds`
:func:`phenomedb.compounds.ImportBrukerBiQuantCompounds`
:func:`phenomedb.imports.ImportSampleManifest`
:func:`phenomedb.imports.ImportDataLocations`
:func:`phenomedb.imports.ImportBrukerIVDRAnnotations`
:func:`phenomedb.imports.ImportPeakPantherAnnotations`
:func:`phenomedb.imports.ImportTargetLynxAnnotations`
:func:`phenomedb.imports.XCMSFeatureImportTaskUnifiedCSV`
:func:`phenomedb.imports.ImportMetabolightsStudy`
:func:`phenomedb.imports.DownloadMetabolightsStudy`
:func:`phenomedb.analysis.RunXCMS`
:func:`phenomedb.imports.ImportMetadata`
:func:`phenomedb.metadata.HarmoniseMetadataField`
:func:`phenomedb.cache.CreateSavedQueryDataframeCache`
:func:`phenomedb.cache.CreateSavedQuerySummaryStatsCache`
:func:`phenomedb.analysis.RunPCA`
:func:`phenomedb.analysis.RunPCPR2`
:func:`phenomedb.analysis.RunMWAS`
:func:`phenomedb.analysis.RunNPYCReport`
:func:`phenomedb.batch_correction.RunCombatCorrection`
:func:`phenomedb.batch_correction.RunNormResidualsMM`
:func:`phenomedb.batch_correction.RunNPYCBatchCorrection`
:func:`phenomedb.batch_correction.SaveBatchCorrection`
:func:`phenomedb.pipelines.RebuildPipelinesFromDB`
:func:`phenomedb.pipelines.GenerateSingleTaskPipelines`
:func:`phenomedb.pipelines.BasicSetup`
:func:`phenomedb.pipelines.BatchCorrectionAssessmentPipelineGenerator`
:func:`phenomedb.pipelines.RunBatchCorrectionAssessmentPipeline`
:func:`phenomedb.pipelines.RunMWASMulti`
:func:`phenomedb.pipelines.ImportAllMetabolightsPipelineGenerator`
:func:`phenomedb.task.ManualSQL`
:func:`phenomedb.cache.CreateTaskViewCache`
:func:`phenomedb.cache.RemoveUntransformedDataFromCache`
:func:`phenomedb.cache.MoveTaskOutputToCache`


The Apache-Airflow interface
----------------------------

To access Apache-Airflow, once the system is running, open your web browser and navigate to http://localhost:8080/. The default username and password are admin and testpass.

From here, pipelines ('DAGs' in Airflow) for individual tasks can be parameterised, executed, and monitored, and the various PhenomeDB views can be accessed.

Apache-Airflow is structured around the concepts of pipelines and pipeline runs (executions). You parameterise a pipeline run and then Airflow manages the execution. Output logs for each task in the pipeline can be inspected via the interface.

For more information regarding the usage of Apache-Airflow, please see the Apache-Airflow documentation.

.. figure:: ./_images/airflow-ui-1.png
  :width: 600
  :alt: Airflow UI home

  Airflow home page showing registered pipelines (DAGs)

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

Tasks and Pipelines
-------------------

Pipelines can be created, registered with Airflow, and executed via the PipelineFactory. Using this approach removes the requirements for manually writing Airflow DAG files.

See the :ref:`phenomedb.pipeline_factory` for more information, including how to build and execute pipelines via the python API and the UI.

Importing analytical data and sample metadata
---------------------------------------------

Two main analytical data import sources are supported - Metabolights format, and the nPYc-toolbox 3-file format, consisting of 3 separate sources of information:

A. Sample manifests: CSV files containing sample metadata subject as clinical factors, outcomes-of-interest, or covariates.
B. Feature metadata: CSV files containing feature metadata such as RT, m/z, and other feature-specific analytical metadata.
C. Study data files: CSV files containing analytical features (measurements) relating to the samples and features/annotated compounds.



Harmonising sample metadata
---------------------------

In order to compare, integrate, and stratify data across multiple cohorts, the sample metadata must be harmonised. To do this, it is recommended to use the CurateMetadataTask, which enables the curation of unharmonised 'raw' metadata fields and values into harmonised 'curated' metadata fields and values. Please see the :ref:`metadata` module for more information.


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



Creating and executing queries
------------------------------


Scaling, normalisation, and batch correction
--------------------------------------------

In order to compare metabolite levels across different batches, projects, or assays, scaling/normalisation, transformation, and batch correction must be undertaken. The aim of these methods is to minimise inter-batch technical variation while maintaining inter-sample biological variation.

Running analyses
----------------

Implemented analysis functions include:

A. PCA via the RunPCA task
B. PCPR2 via the RunPCPR2 task
C. MWAS via the RunMWAS task
D. nPYc reports via the RunNPYCReport task

Individual analyses can be run via the AnalysisView page, where task runs can be parameterised and scheduled, and the results can be explored.

.. figure:: ./_images/analysis-view-list.png
  :width: 600
  :alt: PhenomeDB AnalysisView list

  Analyses can be executed against queries (and upstream task runs) using the AnalysisView. Parameters for the task run can be specified using the html form, including scaling and transformation steps and task-specific options. Previous task runs can be explored via a table.

The results of each analysis can be explored via a dedicated UI, with panels common to all analysis tasks with options to rerun the task, and options to download the input and output datasets.

.. figure:: ./_images/analysis-view-common.png
  :width: 600
  :alt: PhenomeDB AnalysisView common

  Each task run output view has the ability to re-run the task with new parameters, and explore and download the input and output datasets.

Each AnalysisTask also has specific charts and figures available to explore the results.

.. figure:: ./_images/pca-view.png
  :width: 650
  :alt: PhenomeDB RunPCA visualisation

  Interactive visualisation of PCA outputs, including A: Scree plot, B: control panel to control the chart options, C: 2D scores plots, D, E, F: loadings plots.

.. figure:: ./_images/pcpr2-view-1.png
  :width: 500
  :alt: PhenomeDB RunPCPr2 visualisation

  Visualisation of PCPR2 results


.. figure:: ./_images/MWAS-view-example.png
  :width: 650
  :alt: PhenomeDB RunMWAS visualisation

  Interactive visualisation of 1D MWAS outputs

.. figure:: ./_images/example-lneg-mwas-sex-comparison-consistent.png
  :width: 650
  :alt: PhenomeDB RunMWAS compare visualisation

  Interactive visualisation of MWAS comparison heatmaps, where the results of two MWAS analyses can be compared, in this case comparing the age-associated metabolites of males and females

