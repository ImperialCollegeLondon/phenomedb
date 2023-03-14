import datetime

import pytest
import random

import pandas as pd

import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *
from phenomedb.query_factory import *

from phenomedb.config import config
from phenomedb.pipeline_factory import PipelineFactory
from phenomedb.pipelines import *
from phenomedb.analysis import *
from deepdiff import DeepDiff

class TestPipelineFactory:
    """TestPipelineFactory class
    """
    def test_get_arg_spec(self):
        import inspect
        signature = inspect.signature(RunMWAS)
        arglist = list(signature.parameters.keys())
        pass

    def test_save_multi_task_pipeline_factory(self,create_min_database,
                                        create_lab,
                                        create_pipeline_testing_project,
                                        create_nmr_assays,
                                        create_annotation_methods):

        pipeline_folder = config["DATA"]['test_data'] + "tmp/"

        pipeline_name = 'TestPipeline_%s' % str(datetime.datetime.now().timestamp()).replace(".","_")
        pipeline_file = os.path.join(pipeline_folder,pipeline_name + ".py")

        if os.path.exists(pipeline_file):
            os.remove(pipeline_file)

        db_session = get_db_session(db_env='TEST')

        pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,description='Test Pipeline',db_env='TEST',tags=['TEST'],pipeline_folder=pipeline_folder)

        import_sample_manifest_task_id = pipeline_factory.add_task('phenomedb.imports', 'ImportSampleManifest', 'import_sample_manifest')
        pipeline_factory.add_task('phenomedb.imports','ImportDataLocations','import_nmr_datalocations',upstream_task_id=import_sample_manifest_task_id)

        assert pipeline_factory.pipeline_manager.pipeline is not None

        pipeline_factory.commit_definition()

        assert os.path.exists(pipeline_file) is True
        assert pipeline_factory.pipeline_manager.pipeline is not None

        pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,db_env="TEST")
        assert pipeline_factory.pipeline_manager.pipeline is not None

        if os.path.exists(pipeline_file):
            os.remove(pipeline_file)

    def test_generate_single_task_pipelines(self,create_min_database):

        #task = GenerateSingleTaskPipelines(db_env='TEST')
        task = GenerateSingleTaskPipelines()
        task.run()

    def test_rerun_batch_correction_assessment_pipeline(self):
        db_session = db.get_db_session()
        cache = Cache()
        task_run = db_session.query(TaskRun).filter(TaskRun.id==5212).first()
        #task_run_output = task_run.get_task_output(cache)
        if task_run.id not in task_run.args.keys():
            task_run.args['task_run_id'] = task_run.id
        task = RunBatchCorrectionAssessmentPipeline(**task_run.args)
        task.run()
        pass

    def test_run_pipeline(self):

        pipeline_factory = PipelineFactory(pipeline_name='RunMWAS')
        db_session = db.get_db_session()
        task_run = db_session.query(TaskRun).filter(TaskRun.id==4276).first()
        args = dict(task_run.args)
        del(args['task_run_id'])
        run_config = {'runmwas':task_run.args}
        pipeline_factory.run_pipeline(run_config=run_config)
        pass


