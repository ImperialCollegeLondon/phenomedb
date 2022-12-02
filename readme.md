# Welcome to PhenomeDB - the platform for harmonisation and integration of metabolomics data

PhenomeDB is a platform for integrative storage and analysis of metabolomics data, with tools for creating and running data processing pipelines, harmonisation of metadata, querying/generating integrated cohorts, and analysing and visualising those cohorts using commonly used statistical analyses, including PCA, PCPR2, and MWAS.

## Getting started
The easiest way to get started is to use Docker - simply checkout/download this repo, configure the .env variables, and run 'docker compose up', and use your browser to navigate to 'http://localhost:8000'.

## Using PhenomeDB

### Importing data
Data can be loaded from Metabolights, peak-picked/extracted with XCMS, and imported to the backend database ready to harmonisation and integration. To do so, use the ImportMetabolightsStudyXCMS pipeline.

### Harmonising data
Important phenotypes should be harmonised prior to their usage in integrative cohorts. To do so, use the CurateMetadata task.

### Generating queries/cohorts
Once imported and harmonised, data can be queried by creating 'SavedQueries', either via the Python QueryFactory API, or the user interface. Once a query is generated, the cached dataframes for that query should be generated prior to analysis. 

### Analysing data
Once a cohort is created and the cache built, analyses can be executed against that generated dataset. The RunPCA, RunPCPR2, and RunMWAS methods can be used to analyse the data, either via the Python API or the user interface to schedule execution. Analysis results can be explored via dedicated web pages for each task.

### Batch correction/scaling/transformation
Generated cohorts can be be batch corrected using dedicated functions, RunNPYCBatchCorrection for LOWESS correction, RunComBat for ComBat correction, or unit-variance, pareto, or median scaling, and log10 and sqrt transformation.

### Tasks and Pipelines
Everything in PhenomeDB is structured around asynchronous tasks and pipelines, meaning all tasks can chained together in any order into pipelines. Pipelines can be built using the Python API or the web interface (TBD).


