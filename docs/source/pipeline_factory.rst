phenomedb.pipeline_factory
==========================

Pipelines can be created, registered with Airflow, and executed via the :class:`phenomedb.modules.PipelineFactory`. Using this approach removes the requirements for manually writing Airflow DAG files.

Overview
--------

The :class:`phenomedb.modules.PipelineFactory` is the interface between the user and the PipelineManager (the default of which is the AirflowPipelineManager). The PipelineFactory provides a standardised interface to creating Pipelines. Pipelines are created by add Tasks to a pipeline, and then committing them and then executing them.

.. figure:: ./_images/pipeline-factory-overview.png
  :width: 500
  :alt: PhenomeB `phenomedb.modules.PipelineFactory` Overview

  Overview of how the :class:`phenomedb.modules.PipelineFactory` can be used to create Apache Airflow pipelines

User Interface
--------------

The PipelineFactory UI can be used to created parameterised, hard-coded Pipelines/DAGs made of many tasks (executed sequentially).

.. figure:: ./_images/pipeline-factory-ui-example.png
  :width: 650
  :alt: PhenomeB PipelineFactory UI Example

  Example of using a the `phenomedb.modules.PipelineFactory` UI to create a parameterised pipeline

Python API
----------

The :class:`phenomedb.modules.PipelineFactory` Python API has more flexibility in creating a :class:`phenomedb.models.Pipeline`, as it can be used to create two kinds of :class:`phenomedb.models.Pipeline`, dynamic, or hard-coded.

* Hard coded: The pipeline parameters are injected into the DAG file, so each instance of a Pipeline will be specific to one project, for example. These are the kinds of Pipelines the UI builds.
* Dynamic: The pipeline is created with no parameters, to be executed with a run_config (of the same JSON structure as running pipelines through the Airflow UI)

These options are specified using the hard_coded parameter of the :class:`phenomedb.modules.PipelineFactory`

.. code-block:: python

    pipeline_factory = PipelineFactory(pipeline_name='Example hard-coded Pipeline',
                                       description='An Example hard-coded Pipeline',
                                       hard_coded=True)

    # Import a Sample Manifest (could use ImportMetadata instead for CSV files)
    pipeline_factory.add_task('phenomedb.imports', # module
                              'ImportSampleManifest', # class
                               task_id='importsamplemanifest', # unique per pipeline
                               run_config={
                                    "project": "PipelineTesting",
                                    "sample_manifest_path":config['DATA']['test_data'] + 'DEVSET_sampleManifest.xlsx',
                                    "columns_to_ignore": ['Further Sample info?'],
                                    "username": "admin"}
                               )
    # Import Bruker IVDr annotations
    pipeline_factory.add_task('phenomedb.imports',
                              'ImportBrukerIVDrAnnotations',
                              task_id='importbrukerivdrannotations',
                              upstream_task_id='importsamplemanifest',
                              run_config={
                                    "project": "PipelineTesting",
                                    "sample_matrix": "plasma",
                                    "annotation_method": "Bi-LISA",
                                    "unified_csv_path": config['DATA']['test_data'] + 'DEVSET_P_BILISA_combinedData.csv',
                                    "username": "admin" }
                               )

    # Import Bruker IVDr Bi-LISA annotation metadata
    pipeline_factory.add_task('phenomedb.compounds',
                              'ImportBrukerBiLISACompounds',
                              task_id='importbilisacompounds',
                              upstream_task_id='importbrukerivdrannotations',
                              run_config={
                                    "bilisa_file": config['DATA']['test_data'] + 'ivdr-bilisa-all.csv',
                                    "username": "admin"}
                              )

    # Harmonise the metadata (just one field in this example, add one HarmoniseMetadata task per field to be harmonised)
    pipeline_factory.add_task('phenomedb.metadata',
                              'HarmoniseMetadata',
                              task_id='harmoniseage',
                              upstream_task_id='importbilisacompounds',
                              run_config={
                                    "project": "PipelineTesting",
                                    "metadata_field_name": "age",
                                    "harmonised_metadata_field_name":"Age",
                                    "inbuilt_transform_name":"simple_assignment",
                                    "allowed_decimal_places":0,
                                    "username": "admin" }
                               )

    pipeline_factory.add_task('phenomedb.metadata',
                              'HarmoniseMetadata',
                              task_id='harmonisesex',
                              upstream_task_id='harmoniseage',
                              run_config={
                                    "project": "PipelineTesting",
                                    "metadata_field_name": "gender",
                                    "harmonised_metadata_field_name":"Sex",
                                    "lambda_function_string":"lambda x: 'Male' if x.lower().strip() == 'm' else ('Female' if x.lower().strip() == 'f' else 'Unknown' )",
                                    "username": "admin" }
                               )

    # Create a SavedQuery that will target the data (in this case those individuals under 40).
    # Note: When importing annotations, a SavedQuery will be created targeting the imported FeatureDataset

    query_factory = QueryFactory(query_name='PipelineTesting IVDr under 40', query_description='test description')
    query_factory.add_filter(model='Project', property='name', operator='eq', value='PipelineTesting')
    query_factory.add_filter(model='Sample', property='matrix', operator='eq', value='plasma')
    query_factory.add_filter(model='Assay', property='name', operator='eq', value='NOESY')
    query_factory.add_filter(model='AnnotationMethod', property='name', operator='eq', value='Bi-LISA')
    query_factory.add_filter(MetadataFilter('Age','lt',value=40)))
    saved_query = query_factory.save_query()

    # Add a task to create the SavedQuery dataframe cache for the query
    # As this it IVDr, we use the raw values (correction_type=None)
    # If we were targeting LC-MS PeakPantheR data, we would use the SR-corrected data (correction_type='SR')
    # By default it will harmonise the intensities to mmol/L
    pipeline_factory.add_task('phenomedb.cache',
                              'CreateSavedQueryDataframeCache',
                              task_id='createquerycache',
                              upstream_task_id='harmonisesex',
                              run_config={
                                    "saved_query_id": saved_query.id,
                                    "username": "admin" }
                              )

    # Run a PCA with default params
    pipeline_factory.add_task('phenomedb.analysis',
                              'RunPCA',
                              task_id='runpca',
                              upstream_task_id='createquerycache',
                               run_config={
                                    "saved_query_id": saved_query.id,
                                    "username": "admin" }
                               )

    # Run an Bonferroni-corrected linear-regression MWAS where harmonised Age is the outcome-of-interest and harmonised Sex is a covariate
    pipeline_factory.add_task('phenomedb.analysis',
                              'RunMWAS',
                              task_id='runmwas',
                              upstream_task_id='runpca',
                               run_config={
                                    "saved_query_id": saved_query.id,
                                    "model_Y_variable": "h_metadata::Age",
                                    "model_X_variables": ["h_metadata::Sex"],
                                    "method": "linear",
                                    "correction_method": "bonferroni",
                                    "username": "admin" }
                               )

    # Write out the hard coded DAG and register with Airflow
    pipeline_factory.commit_definition()

    # Run the Pipeline (may block while waiting for Airflow to register the Pipeline)
    pipeline_factory.run_pipeline()


The equivalent Pipeline could also be dynamically executed using the following approach

.. code-block:: python

    pipeline_factory = PipelineFactory(pipeline_name='Example dynamic Pipeline',
                                       description='An Example dynamic Pipeline',
                                       hard_coded=False)

    # Import a Sample Manifest (could use ImportMetadata instead for CSV files)
    pipeline_factory.add_task('phenomedb.imports',
                              'ImportSampleManifest',
                               task_id='importsamplemanifest')

    pipeline_factory.add_task('phenomedb.imports',
                              'ImportBrukerIVDrAnnotations',
                              task_id='importbrukerivdrannotations',
                              upstream_task_id='importsamplemanifest')

    # Import Bruker IVDr Bi-LISA annotation metadata
    pipeline_factory.add_task('phenomedb.compounds',
                              'ImportBrukerBiLISACompounds',
                              task_id='importbilisacompounds',
                              upstream_task_id='importbrukerivdrannotations')

    # Harmonise the metadata (just one field in this example, add one HarmoniseMetadata task per field to be harmonised)
    pipeline_factory.add_task('phenomedb.metadata',
                              'HarmoniseMetadata',
                              task_id='harmoniseage',
                              upstream_task_id='importbilisacompounds')

    pipeline_factory.add_task('phenomedb.metadata',
                              'HarmoniseMetadata',
                              task_id='harmonisesex',
                              upstream_task_id='harmoniseage')

    # Create a SavedQuery that will target the data (in this case those individuals under 40).
    # Note: When importing annotations, a SavedQuery will be created targeting the imported FeatureDataset

    query_factory = QueryFactory(query_name='PipelineTesting IVDr under 40', query_description='test description')
    query_factory.add_filter(model='Project', property='name', operator='eq', value='PipelineTesting')
    query_factory.add_filter(model='Sample', property='matrix', operator='eq', value='plasma')
    query_factory.add_filter(model='Assay', property='name', operator='eq', value='NOESY')
    query_factory.add_filter(model='AnnotationMethod', property='name', operator='eq', value='Bi-LISA')
    query_factory.add_filter(MetadataFilter('Age','lt',value=40)))
    saved_query = query_factory.save_query()

    # Add a task to create the SavedQuery dataframe cache for the query
    # As this it IVDr, we use the raw values (correction_type=None)
    # If we were targeting LC-MS PeakPantheR data, we would use the SR-corrected data (correction_type='SR')
    # By default it will harmonise the intensities to mmol/L
    pipeline_factory.add_task('phenomedb.cache',
                              'CreateSavedQueryDataframeCache',
                              task_id='createquerycache',
                              upstream_task_id='harmonisesex',
                              )

    # Run a PCA with default params
    pipeline_factory.add_task('phenomedb.analysis',
                              'RunPCA',
                              task_id='runpca',
                              upstream_task_id='createquerycache'
                               )

    # Run an Bonferroni-corrected linear-regression MWAS where harmonised Age is the outcome-of-interest and harmonised Sex is a covariate
    pipeline_factory.add_task('phenomedb.analysis',
                              'RunMWAS',
                              task_id='runmwas',
                              upstream_task_id='runpca')

    # Write out the hard coded DAG and register with Airflow
    pipeline_factory.commit_definition()

    # Build the dynamically parameterised run_config dictionary
    run_config={
                "importsamplemanifest":{
                        "project": "PipelineTesting",
                        "sample_manifest_path":config['DATA']['test_data'] + 'DEVSET_sampleManifest.xlsx',
                        "columns_to_ignore": ['Further Sample info?'],
                        "username": "admin"
                        },
                "importbrukerivdrannotations":{
                            "project": "PipelineTesting",
                            "sample_matrix": "plasma",
                            "annotation_method": "Bi-LISA",
                            "unified_csv_path": config['DATA']['test_data'] + 'DEVSET_P_BILISA_combinedData.csv',
                            "username": "admin" }

                            "bilisa_file": config['DATA']['test_data'] + 'ivdr-bilisa-all.csv',
                            "username": "admin"
                        },
                 "harmoniseage":{
                            "project": "PipelineTesting",
                            "metadata_field_name": "age",
                            "harmonised_metadata_field_name":"Age",
                            "inbuilt_transform_name":"simple_assignment",
                            "allowed_decimal_places":0,
                            "username": "admin"
                         },
                 "harmonisesex":{
                            "project": "PipelineTesting",
                            "metadata_field_name": "gender",
                            "harmonised_metadata_field_name":"Sex",
                            "lambda_function_string":"lambda x: 'Male' if x.lower().strip() == 'm' else ('Female' if x.lower().strip() == 'f' else 'Unknown' )",
                            "username": "admin"
                         },
                "createquerycache":{
                            "saved_query_id": saved_query.id,
                            "username": "admin"
                         },
                "runpca":{
                            "saved_query_id": saved_query.id,
                            "username": "admin"
                         },
                "runmwas":{
                            "saved_query_id": saved_query.id,
                            "model_Y_variable": "h_metadata::Age",
                            "model_X_variables": ["h_metadata::Sex"],
                            "method": "linear",
                            "correction_method": "bonferroni",
                            "username": "admin" }
                }

    # Run the Pipeline (may block while waiting for Airflow to register the Pipeline)
    pipeline_factory.run_pipeline(run_config=run_config)

The dynamically parameterised run_config is the same format taken by the Apache-Airflow DAG config, so can be used to execute Dynamic pipelines from the interface

.. automodule:: phenomedb.pipeline_factory
   :members:
