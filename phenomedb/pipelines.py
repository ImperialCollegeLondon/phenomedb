# Add your custom PipelineTasks here

import math
from pathlib import Path
import numpy as np
from nPYc.enumerations import *
import requests
import re
import pandas as pd
import os
import json
from phenomedb.models import *
from phenomedb.config import config
from phenomedb.task import Task
from phenomedb.pipeline_factory import PipelineFactory
from phenomedb.analysis import *
from phenomedb.query_factory import *
from phenomedb.exceptions import *
from phenomedb.compounds import *

class PipelineGeneratorTask(Task):

    pipeline_id = None
    pipeline_map = {}

    def __init__(self,**kwargs):

        if 'pipeline_id' in kwargs:
            self.pipeline_id = kwargs['pipeline_id']

        super().__init__(**kwargs)

    def get_pipeline_factory(self,pipeline_name,description=None):
        if not description:
            description = pipeline_name
        return PipelineFactory(pipeline_name,pipeline_id=self.pipeline_id,description=description,db_env=self.db_env)

    def generate_report(self):
        pass

class RebuildPipelinesFromDB(Task):

    def __init__(self,db_env=None,type='all',username=None,db_session=None,task_run_id=None,pipeline_run_id=None,execution_date=None):
        super().__init__(db_env=db_env,username=username,db_session=db_session,task_run_id=task_run_id,pipeline_run_id=pipeline_run_id,execution_date=execution_date)

        self.type = type
        self.get_class_name(self)
        self.args['type'] = type

    def process(self):

        if self.type == 'all':
            pipelines = self.db_session.query(Pipeline).all()
        elif self.type == 'dynamic':
            pipelines = self.db_session.query(Pipeline).filter(Pipeline.hard_code_data==False).all()
        else:
            raise Exception("Unimplemented type %s must be one of all or dynamic" % self.type)

        for pipeline in pipelines:
            pipeline_factory = PipelineFactory(pipeline_name=pipeline.name,db_session=self.db_session,db_env=self.db_env)
            pipeline_factory.commit_definition()


class GenerateSingleTaskPipelines(Task):
    """ This pipeline is used for generating the single task pipelines. These are typically used for API methods or administrative methods such as generating the caches or running reports.
    """

    def process(self):

        self.tasks = PipelineFactory.get_tasks_from_json()
        for task_class_module, task in self.tasks.items():
            self.logger.info(task_class_module)
            if isinstance(task,dict):
                pipeline_factory = PipelineFactory(pipeline_name=task['task'],description=task['task'],db_env=self.db_env,db_session=self.db_session)
                if utils.clean_task_id(task['task']) not in pipeline_factory.pipeline_manager.pipeline.definition.keys():
                    pipeline_factory.add_task(task['module'],task['task'],task_id=utils.clean_task_id(task['task']))
                    pipeline_factory.commit_definition()
                self.tasks[task_class_module]['pipeline_file'] = pipeline_factory.pipeline_manager.pipeline.pipeline_file_path

    def task_validation(self):
        for task_module_class,task in self.tasks.items():
            if isinstance(task,dict):
                if 'pipeline_file' not in task.keys():
                    raise ValidationError("Pipeline File does not exist for task: %s" % (task_module_class))
                else:
                    if not os.path.exists(task['pipeline_file']):
                        raise ValidationError("Pipeline File does not exist: %s" % (task['pipeline_file']))

class BasicSetup(Task):

    pipeline_map = {}
    
    def __init__(self,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,add_pipelines=True,pipeline_run_id=None):
        
        self.add_pipelines = add_pipelines
        
        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)

        self.get_class_name(self)

    def add_pipeline(self,pipeline_name,task_class):

        pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,
                                           db_env=self.db_env)
        if pipeline_name not in pipeline_factory.pipeline_manager.pipeline.definition.keys():
            pipeline_factory.add_task('phenomedb.pipelines', task_class,
                                      task_id=pipeline_name)
        if not os.path.exists(pipeline_factory.pipeline_manager.pipeline.pipeline_file_path):
            pipeline_factory.commit_definition()

        self.pipeline_map[
            pipeline_factory.pipeline_manager.pipeline.id] = pipeline_factory.pipeline_manager.pipeline.pipeline_file_path

    def process(self):

        data_config_file = config['DATA']['config'] + "basic-setup.json"
        if not os.path.exists(data_config_file):
            raise Exception("Setup file missing %s" % data_config_file)

        with open(data_config_file) as json_file:
            data_config = json.load(json_file)

        lab = self.get_or_add_laboratory(data_config['lab'][0],data_config['lab'][1])

        for assay in data_config['assays']:
            self.get_or_add_assay(assay[0],assay[1],assay[2],assay[3],assay[4],assay[5],assay[6])

        for annotation_method in data_config['annotation_methods']:
            self.get_or_add_annotation_method(annotation_method[0],annotation_method[1])

        for unit in data_config['units']:
            self.get_or_add_unit(unit[0], unit[1])

        for harmonised_metadata_field in data_config['harmonised_metadata_fields']:
            unit = self.db_session.query(Unit).filter(Unit.name==harmonised_metadata_field[1]).first()
            if not unit:
                raise Exception("Unit not recognised %s" % harmonised_metadata_field[1])

            self.get_or_add_harmonised_field(harmonised_metadata_field[0],unit,harmonised_metadata_field[2])

        for project in data_config['projects']:
            self.get_or_add_project(project[0],project_folder_name=project[1],laboratory_id=lab.id)

        for compound_external_db in data_config["compound_external_dbs"]:
            self.get_or_add_compound_external_db(compound_external_db[0],compound_external_db[1])

    def task_validation(self):
        for pipeline_id, pipeline_file in self.pipeline_map.items():
            if not os.path.exists(pipeline_file):
                raise ValidationError("Pipeline File does not exist: %s" % (pipeline_file))

    def get_or_add_compound_external_db(self,name,url):

        external_db = self.db_session.query(ExternalDB).filter(ExternalDB.name==name).first()

        if not external_db:
            external_db = ExternalDB(name=name,
                                     url=url)
            self.db_session.add(external_db)
            self.db_session.flush()

        return external_db

class DynamicPipelineTask(Task):

    def __init__(self,pipeline_name=None,username=None,pipeline_run_id=None,task_run_id=None,db_env=None,db_session=None,debug=False,execution_date=None,upstream_task_run_id=None):

        super().__init__(username=username, task_run_id=task_run_id, db_env=db_env, db_session=db_session,
                         execution_date=execution_date,debug=debug,pipeline_run_id=pipeline_run_id,
                         validate=False, upstream_task_run_id=upstream_task_run_id)

        self.pipeline_factory = PipelineFactory(pipeline_name=pipeline_name,db_env=self.db_env)

    def get_task_run_id(self,label):

        task_run = self.db_session.query(TaskRun).filter(#TaskRun.pipeline_id == self.pipeline_id,
                                                    TaskRun.task_id == label,
                                                    TaskRun.id.in_(self.task_run_output['task_run_ids'])).first()
        if task_run:
            return task_run.id
        else:
            return None


class RunBatchCorrectionAssessmentPipeline(DynamicPipelineTask):

    def __init__(self,saved_query_id=None,correction_type=None,run_combat_and_norm_mixedresiduals=False,variable_of_interest=None,
                 metadata_covariates=None,reload_cache=False,task_run_id=None,username=None,upstream_task_run_id=None,model_Y_ci=None,model_Y_min=None,model_Y_max=None,
                 execution_date=None,db_session=None,db_env=None,wait_for_completion=False,debug=False,pipeline_run_id=None):

        self.task_ids = {}

        super().__init__(pipeline_name='batch_correction_assessment_pipeline',task_run_id=task_run_id, username=username,debug=debug,pipeline_run_id=pipeline_run_id,
                         execution_date=execution_date, upstream_task_run_id=upstream_task_run_id,db_env=db_env,db_session=db_session)

        self.saved_query_id = saved_query_id
        self.reload_cache = reload_cache
        self.correction_type = correction_type
        self.run_combat_and_norm_mixedresiduals = run_combat_and_norm_mixedresiduals
        self.variable_of_interest = variable_of_interest
        if metadata_covariates is None:
            self.metadata_covariates = []
        elif isinstance(metadata_covariates,list):
            self.metadata_covariates = metadata_covariates

        self.wait_for_completion = wait_for_completion
        self.args['wait_for_completion'] = wait_for_completion
        self.args['run_combat_and_norm_mixedresiduals'] = run_combat_and_norm_mixedresiduals
        self.args['variable_of_interest'] = variable_of_interest
        self.args['metadata_covariates'] = metadata_covariates
        self.args['saved_query_id'] = saved_query_id
        self.args['reload_cache'] = reload_cache
        self.args['correction_type'] = correction_type
        self.model_Y_ci = model_Y_ci
        self.args['model_Y_ci'] = model_Y_ci
        self.model_Y_min = model_Y_min
        self.args['model_Y_min'] = model_Y_min
        self.model_Y_max = model_Y_max
        self.args['model_Y_max'] = model_Y_max

        self.get_class_name(self)

        self.scaling_types = [None, 'uv', 'med', 'mc', 'pa']
        self.transform_types = [None, 'log', 'sqrt']

    def process(self):

        # 1. load_dataframes - raw, SR, LTR
        saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(float(self.saved_query_id))).first()

        query_factory = QueryFactory(saved_query_id=self.saved_query_id,db_session=self.db_session,db_env=self.db_env)
        self.combined = query_factory.load_dataframe(type='combined',output_model='AnnotatedFeature',harmonise_annotations=True,
                                                     correction_type=self.correction_type,reload_cache=self.reload_cache)
        self.feature_metadata = query_factory.load_dataframe(type='feature_metadata', output_model='AnnotatedFeature',
                                                     correction_type=self.correction_type,harmonise_annotations=True,
                                                     reload_cache=self.reload_cache)

        #types = ['single','single-sample-matrix','single-assay','multi','multi-sample-matrix','multi-assay']
        self.metadata_types = []

        p = 0
        while p < self.combined.shape[1]:
            if re.search('h_metadata::',self.combined.columns[p]):
                if self.combined.columns[p] not in self.metadata_types:
                    self.metadata_types.append(self.combined.columns[p])
            p = p + 1

        self.logger.info("metadata types: %s" % self.metadata_types)

        self.run_config = {}

        # Run only uv-scaling if there are relative and absolute assays in the dataset
        self.measurement_types = []
        for assay_name in self.feature_metadata['assay'].unique():
            assay = self.db_session.query(Assay).filter(Assay.name==assay_name).first()
            if assay.quantification_type not in self.measurement_types:
                self.measurement_types.append(assay.quantification_type)

        if len(self.measurement_types) == 1:
            # Only absolute OR relative - all permutations
            for scaling in self.scaling_types:
                for transform in self.transform_types:
                    self.add_permutation(scaling=scaling,transform=transform)
            if self.run_combat_and_norm_mixedresiduals and len(self.feature_metadata['assay'].unique()) == 1:
                self.add_permutation(scaling=None, transform='log', run_combat=True)
                self.add_permutation(scaling=None, transform='log', run_norm_mixed_residuals=True)
                self.add_permutation(scaling='uv', transform='log', run_combat=True)
                self.add_permutation(scaling='uv', transform='log', run_norm_mixed_residuals=True)
        else:
            # Both absolute AND relative - only no-scaling and unit-variance
            for transform in self.transform_types:
                self.add_permutation(scaling=None,transform=transform)
                self.add_permutation(scaling='uv',transform=transform)
            if self.run_combat_and_norm_mixedresiduals and len(self.feature_metadata['assay'].unique() == 1):
                self.add_permutation(scaling=None, transform='log',run_combat=True)
                self.add_permutation(scaling=None, transform='log', run_norm_mixed_residuals=True)
                self.add_permutation(scaling='uv', transform='log',run_combat=True)
                self.add_permutation(scaling='uv', transform='log', run_norm_mixed_residuals=True)

        # the task is being re-run
        if self.task_run_id and self.cache.exists(self.task_run.get_task_output_cache_key()):
            self.task_run_output = self.task_run.get_task_output(self.cache)
            if 'task_run_ids' in self.task_run_output.keys():
                for task_id in self.run_config.keys():
                    self.run_config[task_id]['task_run_id'] = self.get_task_run_id(task_id)

        self.pipeline_factory.run_pipeline(run_config=self.run_config,debug=self.debug)

        self.mwas_tasks = []
        for task_run_id, task_run in self.pipeline_factory.pipeline_manager.task_runs.items():
            self.logger.info("Task: %s %s %s" % (task_run.task_id,task_run.id,task_run.get_url()))
            if task_run.class_name == 'RunMWAS':
                self.mwas_tasks.append(str(task_run.id))

        if self.wait_for_completion:
            time.sleep(30)
            self.check_batch_correction_status()
            self.logger.info("Batch correction assessment pipelines finished")

        self.saved_output['task_run_ids'] = list(self.pipeline_factory.pipeline_manager.task_runs.keys())
        
        mwas_compare_url = "%s/analysisview/analysisresult/%s?compare=%s" % (config['WEBSERVER']['url'],self.mwas_tasks.pop(0),",".join(self.mwas_tasks))

        self.logger.info("Mwas compare: %s" % mwas_compare_url)

    def check_batch_correction_status(self):

        if self.db_session.query(TaskRun).filter(
                TaskRun.id.in_(self.pipeline_factory.pipeline_manager.task_runs.keys())) \
                .filter(TaskRun.status != TaskRun.Status.success).count() > 0:
            time.sleep(30)
            self.check_batch_correction_status()

    def add_permutation(self,scaling=None,transform=None,run_combat=False,run_norm_mixed_residuals=False):

        upstream_task_id = None

        self.logger.info("Adding permutation %s %s" % (scaling, transform))

        if not scaling:
            label = 'unscaled'
        else:
            label = "%s" % scaling
        if not transform:
            label = '%s_untransformed' % label
        else:
            label = '%s_%s' % (label, transform)

        if run_combat is not False and transform == 'log' and len(self.combined['Unique Batch'].unique()) > 1:
            label = '%s_runcombatcorrection' % label.lower()

            # Is only run when there are more than 1 batch!
            combat_args = {'saved_query_id': self.saved_query_id, 'correction_type': self.correction_type,
                           'exclude_features_not_in_all_projects': True, 'scaling': scaling}
            # TODO: If batch-study-group is balanced, then allow for batch correction covariates
            combat_args['batch_variable'] = 'Unique Batch'

            self.run_config['%s_batch_correction' % label.lower()] = combat_args
            upstream_task_id = '%s_batch_correction' % label.lower()

        elif run_norm_mixed_residuals is not False and transform == 'log':
            label = '%s_runnormresidualsmm' % label.lower()

            norm_residuals_args = {'saved_query_id': self.saved_query_id, 'correction_type': self.correction_type,
                                   'exclude_features_not_in_all_projects': True,'scaling':scaling}
            columns = []
            if len(self.combined['Unique Batch'].unique()) > 1:
                columns.append('Unique Batch')
            if len(self.combined['Project'].unique()) > 1:
                columns.append('Project')
            self.logger.info(self.feature_metadata.columns)
            if len(self.feature_metadata['assay'].unique()) > 1:
                columns.append('Assay')
            norm_residuals_args['columns_random_to_correct'] = columns
            norm_residuals_args['heteroscedastic_columns'] = columns

            self.run_config['%s_batch_correction' % label.lower()] = norm_residuals_args
            upstream_task_id = '%s_batch_correction' % label.lower()

        pca_args = {'scaling': scaling, 'transform': transform, 'saved_query_id': self.saved_query_id,
                'correction_type': self.correction_type, 'exclude_features_not_in_all_projects':True}
        if upstream_task_id:
            pca_args['upstream_task_id'] = upstream_task_id
        self.run_config['%s_pca' % label] = pca_args

        # if there are is more than 1 batch and exactly 1 assay, use unique batch
        if len(self.combined['Unique Batch'].unique()) > 1 and len(self.feature_metadata['assay'].unique()) == 1:
            pcpr2_batch_args = {'scaling': scaling, 'transform': transform, 'saved_query_id': self.saved_query_id,
                    'correction_type': self.correction_type, 'exclude_features_not_in_all_projects':True}
            pcpr2_batch_args['columns_to_include'] = ['Unique Batch']
            if "Unique Batch" not in self.metadata_types:
                self.metadata_types.append('Unique Batch')
            if upstream_task_id:
                pcpr2_batch_args['upstream_task_id'] = upstream_task_id
            self.run_config['%s_pcpr2_batch' % label] = pcpr2_batch_args

        if len(self.combined['Project'].unique()) > 1:
            pcpr2_project_args = {'scaling': scaling, 'transform': transform, 'saved_query_id': self.saved_query_id,
                    'correction_type': self.correction_type, 'exclude_features_not_in_all_projects':True}
            pcpr2_project_args['columns_to_include'] = ['Project']
            if "Project" not in self.metadata_types:
                self.metadata_types.append('Project')
            if upstream_task_id:
                pcpr2_project_args['upstream_task_id'] = upstream_task_id
            self.run_config['%s_pcpr2_project' % label] = pcpr2_project_args

        if len(self.combined['Sample Matrix'].unique()) > 1:
            pcpr2_sample_args = {'scaling': scaling, 'transform': transform, 'saved_query_id': self.saved_query_id,
                    'correction_type': self.correction_type, 'exclude_features_not_in_all_projects':True}
            pcpr2_sample_args['columns_to_include'] = ['Sample Matrix']
            if "Sample Matrix" not in self.metadata_types:
                self.metadata_types.append('Sample Matrix')
            if upstream_task_id:
                pcpr2_sample_args['upstream_task_id'] = upstream_task_id
            self.run_config['%s_pcpr2_sample_matrix' % label] = pcpr2_sample_args

        #if len(self.feature_metadata['assay'].unique()) > 1:
        #    assay_args = {'scaling': scaling, 'transform': transform, 'saved_query_id': self.saved_query_id,
        #            'correction_type': self.correction_type, 'exclude_features_not_in_all_projects':True}
        #    assay_args['columns_to_include'] = ['Assay']
        #    #if "Assay" not in self.metadata_types:
        #    #    self.metadata_types.append('Assay')
        #    if upstream_task_id:
        #        assay_args['upstream_task_id'] = upstream_task_id
        #    self.run_config['%s_pcpr2_assay' % label] = assay_args

        mwas_args = {'scaling': scaling, 'transform': transform, 'saved_query_id': self.saved_query_id,
                'correction_type': self.correction_type, 'exclude_features_not_in_all_projects':True}
        mwas_args['model_Y_variable'] = self.variable_of_interest
        mwas_args['model_X_variables'] = self.metadata_types
        mwas_args['multiple_correction'] = 'bonferroni'
        if self.model_Y_ci:
            mwas_args['model_Y_ci'] = self.model_Y_ci
        if self.model_Y_min:
            mwas_args['model_Y_min'] = self.model_Y_min
        if self.model_Y_max:
            mwas_args['model_Y_max'] = self.model_Y_max
        if upstream_task_id:
            mwas_args['upstream_task_id'] = upstream_task_id

        self.run_config['%s_mwas' % label] = mwas_args

class BatchCorrectionAssessmentPipelineGenerator(PipelineGeneratorTask):

    # The pipeline this creates is to be triggered per SavedQuery and per Intensity type to be assesses (ie, raw, SR, LTR).
    # Permutates the scaling, transform, and batch correction (COMBAT and RunNormResidualsMM) methods.
    # Runs PCA, PCPR2, and MWAS on scaled, transformed, and batch corrected data

    def process(self):
        self.db_session.query(Pipeline).filter(Pipeline.name == 'batch_correction_assessment_pipeline').delete()
        self.db_session.commit()

        self.pipeline_factory = PipelineFactory(pipeline_name='batch_correction_assessment_pipeline',
                                                max_active_runs=1, db_env=self.db_env)

        scaling_types = [None,'uv','med','mc','pa']
        transform_types = [None,'log','sqrt']
        batch_correction_methods = ['RunCombatCorrection','RunNormResidualsMM']

        self.upstream_task_id = None
        for scaling in scaling_types:
            for transform in transform_types:
                self.add_permutation(scaling=scaling,transform=transform)
        # All batch correction methods expect log transformed data
        for batch_correction_method in batch_correction_methods:
            self.add_permutation(scaling=None, transform='log', batch_correction_method=batch_correction_method)
            # Need UV/log for multi-measurement (ie LC-MS+NMR)
            self.add_permutation(scaling='uv',transform='log',batch_correction_method=batch_correction_method)

        self.pipeline_factory.commit_definition()

    def add_permutation(self,scaling=None,transform=None,batch_correction_method=None):

        self.logger.info("Adding permutation %s %s %s" % (scaling,transform,batch_correction_method))

        if not scaling:
            label = 'unscaled'
        else:
            label = "%s" % scaling
        if not transform:
            label = '%s_untransformed' % label
        else:
            label = '%s_%s' % (label, transform)

        if batch_correction_method is not None:
            label = '%s_%s' % (label, batch_correction_method.lower())
            task_id = '%s_batch_correction' % label
            if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
                self.pipeline_factory.add_task('phenomedb.batch_correction', batch_correction_method, task_id=task_id,upstream_task_id=self.upstream_task_id)
            self.upstream_task_id = task_id

        task_id = '%s_pca' % (label)
        if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
            self.pipeline_factory.add_task('phenomedb.analysis', 'RunPCA', task_id=task_id,upstream_task_id=self.upstream_task_id)
        self.upstream_task_id = task_id

        task_id = '%s_pcpr2_batch' % (label)
        if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
            self.pipeline_factory.add_task('phenomedb.analysis', 'RunPCPR2', task_id=task_id,
                                           upstream_task_id=self.upstream_task_id)
        self.upstream_task_id = task_id

        task_id = '%s_pcpr2_project' % (label)
        if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
            self.pipeline_factory.add_task('phenomedb.analysis', 'RunPCPR2', task_id=task_id,
                                           upstream_task_id=self.upstream_task_id)
        self.upstream_task_id = task_id

        task_id = '%s_pcpr2_sample_matrix' % (label)
        if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
            self.pipeline_factory.add_task('phenomedb.analysis', 'RunPCPR2', task_id=task_id,
                                           upstream_task_id=self.upstream_task_id)
        self.upstream_task_id = task_id

        task_id = '%s_pcpr2_assay' % (label)
        if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
            self.pipeline_factory.add_task('phenomedb.analysis', 'RunPCPR2', task_id=task_id,
                                           upstream_task_id=self.upstream_task_id)
        self.upstream_task_id = task_id

        task_id = '%s_mwas' % (label)
        if task_id not in self.pipeline_factory.pipeline_manager.pipeline.definition.keys():
            self.pipeline_factory.add_task('phenomedb.analysis', 'RunMWAS', task_id=task_id,
                                           upstream_task_id=self.upstream_task_id)
        self.upstream_task_id = task_id

class RunMWASMulti(Task):

    def __init__(self,saved_query_ids=None,method='pearson',correction_type=None,variable_of_interest=None,reload_cache=False,task_run_id=None,username=None,
                 upstream_task_run_id=None,model_Y_ci=None,model_Y_min=None,model_Y_max=None,multiple_correction=None,scaling=None,transform=None,
                 execution_date=None,db_session=None,db_env=None,debug=False,pipeline_run_id=None):

        self.task_ids = {}

        super().__init__(task_run_id=task_run_id, username=username,debug=debug,pipeline_run_id=pipeline_run_id,
                         execution_date=execution_date, upstream_task_run_id=upstream_task_run_id,db_env=db_env,db_session=db_session)

        if not saved_query_ids or not isinstance(saved_query_ids,list):
            raise Exception('saved_query_ids must be a list')

        self.saved_query_ids = saved_query_ids
        self.reload_cache = reload_cache

        self.scaling = scaling
        self.args['scaling'] = scaling
        self.transform = transform
        self.args['transform'] = transform
        self.correction_type = correction_type
        self.args['correction_type'] = correction_type
        self.method = method
        self.args['method'] = method
        self.variable_of_interest = variable_of_interest
        self.args['variable_of_interest'] = variable_of_interest
        self.args['saved_query_ids'] = saved_query_ids
        self.args['reload_cache'] = reload_cache
        self.model_Y_ci = model_Y_ci
        self.args['model_Y_ci'] = model_Y_ci
        self.model_Y_min = model_Y_min
        self.args['model_Y_min'] = model_Y_min
        self.model_Y_max = model_Y_max
        self.args['model_Y_max'] = model_Y_max
        self.multiple_correction = multiple_correction
        self.args['multiple_correction'] = multiple_correction

        self.get_class_name(self)

    def process(self):

        pipeline_factory = PipelineFactory(pipeline_name='RunMWAS')

        args = {'method': self.method,
                'correction_type': self.correction_type,
                'model_Y_ci': self.model_Y_ci,
                'model_Y_min': self.model_Y_min,
                'model_Y_max': self.model_Y_max,
                'model_Y_variable': self.variable_of_interest,
                'multiple_correction': self.multiple_correction,
                }

        saved_querys = self.db_session.query(SavedQuery).filter(SavedQuery.id.in_(self.saved_query_ids)).all()

        for saved_query in saved_querys:
            run_args = dict(args)
            run_args['saved_query_id'] = saved_query.id
            run_config = {'runmwas':run_args}
            pipeline_factory.run_pipeline(run_config=run_config)

        for task_run_id,task_run in pipeline_factory.pipeline_manager.task_runs.items():
            self.logger.info('SavedQuery: %s TaskRun: %s' % (task_run.saved_query_id,task_run_id))

class ImportAllMetabolightsPipelineGenerator(Task):

    def __init__(self,task_run_id=None,username=None,upstream_task_run_id=None,execution_date=None,db_session=None,
                 db_env=None,debug=False,pipeline_run_id=None):

        super().__init__(task_run_id=task_run_id, username=username, debug=debug, pipeline_run_id=pipeline_run_id,
                         execution_date=execution_date, upstream_task_run_id=upstream_task_run_id, db_env=db_env,
                         db_session=db_session)

        self.get_class_name(self)

    def process(self):

        self.pipeline_factory = PipelineFactory(pipeline_name="ImportAllMetabolights",hard_code_data=True)

        from ftplib import FTP
        self.ebi_ftp = FTP('ftp.ebi.ac.uk')  # connect to host, default port
        self.ebi_ftp.login()
        self.ebi_ftp.cwd('pub/databases/metabolights/studies/public/')
        filenames = self.ebi_ftp.nlst()
        study_ids = []
        for filename in filenames:
            if re.search(r'^MTBL', filename):
                study_ids.append(filename)
        try:
            self.ebi_ftp.quit()
        except Exception as err:
            self.ebi_ftp.close()
        for study_id in study_ids:
            self.pipeline_factory.add_task('phenomedb.imports','ImportMetabolightsStudy',task_id=study_id,run_config={'study_id':study_id})
            self.logger.info("%s added to import pipeline" % study_id)

        self.pipeline_factory.commit_definition()