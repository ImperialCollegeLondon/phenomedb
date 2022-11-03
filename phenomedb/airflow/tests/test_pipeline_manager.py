import datetime
import time

import pytest
import random

import pandas as pd

import sys, os
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *
from phenomedb.query_factory import *

from phenomedb.config import config
from phenomedb.exceptions import *
from phenomedb.pipeline_factory import PipelineFactory

from deepdiff import DeepDiff

db_session = get_db_session(db_env='TEST')

class TestAirflowPipelineManager:
    """TestAirflowPipelineManager class

        Be very careful running these tests as they will hit and execute the Airflow Scheduler for the added pipeline.

        Once finished it will pause the test dag.

        This unit test expects the scheduler to be running inside a docker container (NOT localhost).
    """


    def test_a_create_save_and_run_airflow_pipeline(self,create_min_database,
                                        create_lab,
                                        create_pipeline_testing_project,
                                        create_nmr_assays,
                                        create_annotation_methods):

        pipeline_name = 'TestPipeline_%s' % str(datetime.datetime.now().timestamp()).replace(".","_")

        pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,description='Test Pipeline',db_env='TEST',tags=['TEST'])

        import_sample_manifest_task_id = pipeline_factory.add_task('phenomedb.imports', 'ImportSampleManifest')
        pipeline_factory.add_task('phenomedb.imports','ImportDataLocations',upstream_task_id=import_sample_manifest_task_id)

        assert pipeline_factory.pipeline_manager.pipeline is not None

        pipeline_factory.commit_definition()
        pipeline_file = os.path.join(config['PIPELINES']['pipeline_folder'], pipeline_name + "_TEST.py")
        assert os.path.exists(pipeline_file) is True
        assert pipeline_factory.pipeline_manager.pipeline is not None

        pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,db_env="TEST")

        sample_manifest_config = {'project_name': 'PipelineTesting',
                                                             'sample_manifest_path': '/opt/phenomedb_app/data/test/DEVSET_sampleManifest.xlsx',
                                                             'columns_to_ignore': ['Further Sample info?'],
                                                             'username': 'testuser'}
        data_locations_config = {'project_name': 'PipelineTesting',
                                 'data_locations_path': '/opt/phenomedb_app/data/test/DEVSET_datalocations_NMR.csv',
                                 'sample_matrix': 'plasma',
                                 'assay_platform': 'NMR',
                                 'assay_name': 'NOESY',
                                 'username': 'testuser'}

        run_config = {}

        for task_id,task_def in pipeline_factory.pipeline_manager.pipeline.definition.items():
            if task_def['task_class'] == 'ImportSampleManifest':
                run_config[task_id] = sample_manifest_config
            elif task_def['task_class'] == 'ImportDataLocations':
                run_config[task_id] = data_locations_config

        assert pipeline_factory.run_pipeline(run_config=run_config) is True

        pipeline = db_session.query(Pipeline).filter(Pipeline.name==pipeline_name+"_TEST").first()

        assert pipeline is not None

        time.sleep(30)
        # 1. get the task run, check it's status
        task_runs = db_session.query(TaskRun).filter(TaskRun.pipeline_id==pipeline.id).order_by(TaskRun.id).all()
        for task_run in task_runs:
            assert task_run.status == TaskRun.Status.success

        assert pipeline_factory.delete_pipeline() == True
        time.sleep(5)
        assert not os.path.exists(pipeline_factory.pipeline_manager.pipeline.pipeline_file_path)

    def test_b_create_add_and_run_tasks(self,create_min_database,
                                        create_lab,
                                        create_pipeline_testing_project,
                                        create_nmr_assays,
                                        create_annotation_methods):

        pipeline_name = 'TestPipeline_%s' % str(datetime.datetime.now().timestamp()).replace(".","_")

        pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,description='Test Pipeline',db_env='TEST',tags=['TEST'])

        sample_manifest_config = {'project_name': 'PipelineTesting',
                                  'sample_manifest_path': '/opt/phenomedb_app/data/test/DEVSET_sampleManifest.xlsx',
                                  'columns_to_ignore': ['Further Sample info?'],
                                  'username': 'testuser'}

        try:
            pipeline_factory.add_task('phenomedb.imports', 'ImportSampleManifest',task_id='1sample_manifest', run_config=sample_manifest_config)
            assert False
        except PipelineTaskIDError:
            assert True

        assert pipeline_factory.add_task('phenomedb.imports', 'ImportSampleManifest',task_id='sample_manifest',run_config=sample_manifest_config) == 'sample_manifest'

        try:
            assert pipeline_factory.add_task('phenomedb.imports', 'ImportSampleManifest',task_id='sample_manifest', run_config=sample_manifest_config)
            assert False
        except PipelineTaskIDError:
            assert True

        data_locations_config = {'project_name': 'PipelineTesting',
                                 'data_locations_path': '/opt/phenomedb_app/data/test/DEVSET_datalocations_NMR.csv',
                                 'sample_matrix': 'plasma',
                                 'assay_platform': 'NMR',
                                 'assay_name': 'NOESY',
                                 'username': 'testuser'}

        assert pipeline_factory.add_task('phenomedb.imports','ImportDataLocations',upstream_task_id='sample_manifest',task_id='data_locations',run_config=data_locations_config) == 'data_locations'

        assert pipeline_factory.pipeline_manager.pipeline is not None

        pipeline_factory.commit_definition()

        assert pipeline_factory.run_pipeline() is True

        time.sleep(120)

        # 1. get the task run, check it's status
        task_runs = db_session.query(TaskRun).filter(TaskRun.pipeline_id==pipeline_factory.pipeline_manager.pipeline.id).order_by(TaskRun.id).all()

        for task_run in task_runs:
            assert task_run.status == TaskRun.Status.success

        assert pipeline_factory.delete_pipeline() == True
        assert not os.path.exists(pipeline_factory.pipeline_manager.pipeline.pipeline_file_path)

    def test_c_creating_single_task_pipelines(self,create_min_database):

        from pipelines import GenerateSingleTaskPipelines
        task = GenerateSingleTaskPipelines(db_env='TEST')
        assert 'validation_error' not in task.run()

       # for pipeline_id,pipeline_file_path in task.pipeline_map.items():
       #     pipeline_factory = PipelineFactory(pipeline_id=pipeline_id,db_env='TEST')
       #     assert pipeline_factory.delete_pipeline() == True
       #     assert not os.path.exists(pipeline_factory.pipeline_manager.pipeline.pipeline_file_path)

    def test_d_creating_hard_coded_data_pipeline(self,create_min_database):

        pipeline_factory = PipelineFactory('test_hard_coded',db_env='TEST',hard_code_data=True)
        sample_manifest_config = {'project_name': 'PipelineTesting',
                                  'sample_manifest_path': '/opt/phenomedb_app/data/test/DEVSET_sampleManifest.xlsx',
                                  'columns_to_ignore': ['Further Sample info?'],
                                  'username': 'testuser'}
        pipeline_factory.add_task('phenomedb.imports','ImportSampleManifest',run_config=sample_manifest_config)

        data_locations_config = {'project_name': 'PipelineTesting',
                                 'data_locations_path': '/opt/phenomedb_app/data/test/DEVSET_datalocations_NMR.csv',
                                 'sample_matrix': 'plasma',
                                 'assay_platform': 'NMR',
                                 'assay_name': 'NOESY',
                                 'username': 'testuser'}
        pipeline_factory.add_task('phenomedb.imports', 'ImportDataLocations', run_config=data_locations_config)

        pipeline_factory.commit_definition()

        assert pipeline_factory.run_pipeline() is True

        time.sleep(90)

        # 1. get the task run, check it's status
        task_runs = db_session.query(TaskRun).filter(
            TaskRun.pipeline_id == pipeline_factory.pipeline_manager.pipeline.id).order_by(TaskRun.id).all()

        for task_run in task_runs:
            assert task_run.status == TaskRun.Status.success

        assert pipeline_factory.delete_pipeline() == True
        assert not os.path.exists(pipeline_factory.pipeline_manager.pipeline.pipeline_file_path)






