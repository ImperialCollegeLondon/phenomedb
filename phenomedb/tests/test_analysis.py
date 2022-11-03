import pytest
import random

import pandas as pd

import sys, os
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *
from phenomedb.query_factory import *
from phenomedb.analysis import *
from phenomedb.batch_correction import *
from phenomedb.tests.conftest import *

from phenomedb.config import config

test_db_session = get_db_session(db_env='TEST')
prod_db_session = get_db_session()

class TestAnalysisTasks:    
    """TestAnalysisTasks class. Tests the AnalysisTasks
    """

    def test_a_run_pca_saved_query(self):

        task = RunPCA(saved_query_id=1,username='testuser',reload_cache=True)
        output = task.run()

        assert isinstance(output,dict)
        assert 'ncomps' in output.keys()
        assert 'scores' in output.keys()
        assert 'loadings' in output.keys()

    def test_a_run_pca_multi_project(self):
        task = RunPCA(saved_query_id=89,exclude_features_not_in_all_projects=True,
                      scaling='uv',transform='log',correction_type='SR',
                      harmonise_annotations=True,sample_types=["StudySample"])
        output = task.run()

        assert isinstance(output, dict)
        assert 'ncomps' in output.keys()
        assert 'scores' in output.keys()
        assert 'loadings' in output.keys()

    def test_a_run_pca_compare_scaling(self):

        task = RunPCA(saved_query_id=58,username='testuser',scaling='log')
        output = task.run()
        print('Log transform: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=58, username='testuser', scaling='uv')
        output = task.run()
        print('UV transform: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

    def test_a_run_pcpr2(self):

      #  task = RunPCPR2(saved_query_id=58,correction_type='SR',include_harmonised_metadata=True)
      #  output = task.run()
      #  print('PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCPR2(saved_query_id=1, correction_type='SR',columns_to_include=['Project'])
        output = task.run()
        print('PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCPR2(saved_query_id=1, correction_type='SR', include_harmonised_metadata=False)
        output = task.run()
        print('PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

      # assert isinstance(output,dict)
      #  assert 'ncomps' in output.keys()
      #  assert 'scores' in output.keys()
      #  assert 'loadings' in output.keys()

    def test_load_task_data(self):
        db_session = db.get_db_session()
        cache = Cache()
        id = 977
        # id = 976
        task_run = db_session.query(TaskRun).filter(TaskRun.id == id).first()

        task_data = None

        if cache.exists(task_run.get_task_data_cache_key()):
            task_data = cache.get(task_run.get_task_data_cache_key())
        else:
            task = task_run.get_task_class_object()
            if hasattr(task, 'load_data'):
                task.load_data()

        if task_data:
            # self.logger.debug("Task.data %s" % task_data)
            pass


  #  def test_a_pca_output(self):

  #      task_run = prod_db_session.query(TaskRun).filter(TaskRun.id==579).first()
  #      task_run.output

    def test_a_run_pca_bilisa(self,create_min_database,
                       create_pipeline_testing_project,
                       create_lab,
                       create_nmr_assays,
                       create_annotation_methods,
                       import_devset_sample_manifest,
                       import_devset_ivdr_bilisa_annotations,
                       create_age_sex_harmonised_fields,
                        dummy_harmonise_annotations,
                       create_saved_queries):

        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name=='test_query_bilisa').first()

        task = RunPCA(saved_query_id=saved_query.id,username='testuser',db_env='TEST',reload_cache=True)
        output = task.run()

        assert isinstance(output, dict)
        assert 'ncomps' in output.keys()
        assert 'scores' in output.keys()
        assert 'loadings' in output.keys()


    def test_multi_pcpr2(self):

        args = {'columns_to_include': ['Project', 'Sample Matrix'],
                 'correction_type': 'SR',
                 'db_env': 'PROD',
                 'exclude_features_not_in_all_projects': True,
                 'harmonise_annotations': True,
                 'reload_cache': False,
                 'saved_query_id': 76,
                 'saved_query_model': 'AnnotatedFeature',
                 'task_run_id': 1526}
        task = RunPCPR2(**args)
        task.run()
        pass

    def test_b_run_pcpr2(self,create_min_database,
                       create_pipeline_testing_project,
                       create_lab,
                       create_nmr_assays,
                       create_annotation_methods,
                       import_devset_sample_manifest,
                       import_devset_ivdr_bilisa_annotations,
                       create_age_sex_harmonised_fields,
                        dummy_harmonise_annotations,
                       create_saved_queries):

        create_project('PipelineTesting2')
        import_devset_project_sample_manifest('PipelineTesting2')
        #import_devset_project_datalocations_nmr('PipelineTesting2')
        import_devset_project_ivdr_bilisa_annotations('PipelineTesting2')

        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name=='test_query_bilisa_2_projects').first()

        columns_to_include = ["metadata::Age","metadata::Gender","Project"]
        columnns_to_exclude = ['Unique Run Order','Run Order','Acquired Time']

        task = RunPCPR2(saved_query_id=saved_query.id,username='testuser',db_env='TEST',#reload_cache=True,
                        columns_to_include=columns_to_include,columns_to_exclude=columnns_to_exclude)

        task.run()

        #assert output == "R script failed: %s %s %s" % (task.r_script_path,task.err,task.r_output)
        assert task.results is not None

    def test_a_reports(self,create_min_database,
                         create_pipeline_testing_project,
                         create_lab,
                         create_nmr_assays,
                         create_annotation_methods,
                         import_devset_sample_manifest,
                         import_devset_ivdr_bilisa_annotations,
                         create_age_sex_harmonised_fields,
                         dummy_harmonise_annotations,
                         create_saved_queries):
        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_bilisa').first()
        task = RunNPYCReport(report_name='multivariate_report',saved_query_id=saved_query.id,
                             username='testuser',db_env='TEST',reload_cache=True)
        output = task.run()
        assert os.path.exists(task.report_folder)

    def test_analysis_view_load_data(self):

        db_session = db.get_db_session()

        cache = Cache()

        id = 190

        task_run = db_session.query(TaskRun).filter(TaskRun.id == id).first()

        task_data = None

        #if cache.exists(task_run.get_task_data_cache_key()):
        #    task_data = cache.get(task_run.get_task_data_cache_key())
        #else:
        task = task_run.get_task_class_object()
        if hasattr(task, 'load_data'):
            task.load_data()
        pass
        #if hasattr(task, 'data'):#
#
#            cache.set(task_run.get_task_data_cache_key(), task.data, ex=60 * 60 * 24)
#            task_data = task.data

    def test_combined_generator(self):

        query_factory = QueryFactory(saved_query_id=1)
        query_factory.build_intensity_data_sample_metadata_and_feature_metadata()
        combined = utils.build_combined_dataframe_from_seperate(
            query_factory.dataframes['intensity_data::AnnotatedFeature'],
            query_factory.dataframes['sample_metadata::AnnotatedFeature'],
            query_factory.dataframes['feature_metadata::AnnotatedFeature'])

        assert isinstance(combined,pd.DataFrame) == True
        assert combined.shape == (query_factory.dataframes['sample_metadata::AnnotatedFeature'].shape[0],query_factory.dataframes['sample_metadata::AnnotatedFeature'].shape[1] + query_factory.dataframes['feature_metadata::AnnotatedFeature'].shape[0])

    def test_combined_generator_from_task_run(self):

        db_session = db.get_db_session()
        cache = Cache()
        task_run = db_session.query(TaskRun).filter(TaskRun.id == 1172).first()
        data_dict = cache.get(task_run.get_task_data_cache_key())

        intensity_data = np.matrix(data_dict['intensity_data'])
        sample_metadata = pd.DataFrame.from_dict(data_dict['sample_metadata'])
        feature_metadata = pd.DataFrame.from_dict(data_dict['feature_metadata'])
        # query_factory.build_intensity_data_sample_metadata_and_feature_metadata()
        combined = utils.build_combined_dataframe_from_seperate(
            intensity_data,
            sample_metadata,
            feature_metadata)

        assert isinstance(combined, pd.DataFrame) == True
        assert combined.shape == (sample_metadata.shape[0],
                                  sample_metadata.shape[1] +
                                  feature_metadata.shape[0])

    def test_mwas_tools(self):

        task = RunMWAS(saved_query_id=65,correction_type='SR',scaling='uv',transform='log',reload_cache=False,model_Y_ci=0.8,
                       model_Y_variable='h_metadata::Age',model_X_variables=['h_metadata::Sex','h_metadata::BMI'])
        task.run()
        print("task: %s" % task.task_run.id)

        task2 = RunMWAS(saved_query_id=65, correction_type='SR', scaling='uv', transform='log',model_Y_min=25,model_Y_max=60,
                       model_Y_variable='h_metadata::Age', model_X_variables=['h_metadata::Sex','h_metadata::BMI'],features_to_exclude=[8])
        task2.run()
        print("task: %s" % task2.task_run.id)

    def test_mwas_2_projects(self):

        task = RunMWAS(saved_query_id=76,correction_type='SR',scaling='uv',transform='log',reload_cache=False,model_Y_ci=0.9,
                       model_Y_variable='h_metadata::Age',model_X_variables=['h_metadata::Sex','h_metadata::BMI',"Project","Sample Matrix"])
        task.run()
        print("task: %s" % task.task_run.id)

        #task = RunMWAS(saved_query_id=75, correction_type='SR', scaling='uv', transform='log',
        #               model_Y_variable='h_metadata::Age', model_X_variables=['h_metadata::Sex','h_metadata::BMI'])
        #task.run()
        #print("task: %s" % task.task_run.id)

    def test_mwas_tools_models_and_bootstrap(self):

        task = RunMWAS(saved_query_id=66,correction_type='SR',scaling='uv',transform='log',bootstrap=False,
                       save_models=False,
                       model_Y_variable='h_metadata::Age',model_X_variables=['h_metadata::Sex','h_metadata::BMI'])
        task.run()
        print("task: %s" % task.task_run.id)

        #task = RunMWAS(saved_query_id=66, correction_type='SR', scaling='uv', transform='log', bootstrap=False,
        #               save_models=True,model_Y_variable='h_metadata::Age',
        #               model_X_variables=['h_metadata::Sex', 'h_metadata::BMI'])
        #task.run()
        #print("task: %s" % task.task_run.id)

        task = RunMWAS(saved_query_id=66, correction_type='SR', scaling='uv', transform='log', bootstrap=True,
                       save_models=False,
                       model_Y_variable='h_metadata::Age', model_X_variables=['h_metadata::Sex', 'h_metadata::BMI'])
        task.run()
        print("task: %s" % task.task_run.id)

    def test_mwas_sort(self):

        #from flask import url_for

        task = RunMWAS(saved_query_id=31, correction_type='SR',  # ,reload_cache=True,
                       model_Y_variable='h_metadata::Age', model_X_variables=['h_metadata::Sex'])
        task.run()
        task_run_1_id = task.task_run.id

        task = RunMWAS(saved_query_id=31, correction_type='SR',  # ,reload_cache=True,
                       model_Y_variable='h_metadata::Age', model_X_variables=['h_metadata::Sex'])
        task.run()
        task_run_2_id = task.task_run.id

        task_run_1 = prod_db_session.query(TaskRun).filter(TaskRun.id == task_run_1_id).first()
        task_run_2 = prod_db_session.query(TaskRun).filter(TaskRun.id == task_run_2_id).first()
        task_run_1_dataframe = pd.DataFrame.from_dict(task_run_1.output['mwas_results'])
        task_run_2_dataframe = pd.DataFrame.from_dict(task_run_2.output['mwas_results'])
        task_run_1_dataframe = task_run_1_dataframe.sort_values('adjusted_pvalues')

        task_run_1_dataframe["harmonised_annotation_id"] = None
        task_run_1_dataframe["assay"] = None
        task_run_1_dataframe["annotation_method"] = None
        task_run_1_dataframe["cpd_id"] = None
        task_run_1_dataframe["cpd_name"] = None
        task_run_1_dataframe["annotation_url"] = None
        harmonised_annotation_ids = []
        i = 0
        while i < task_run_1_dataframe.shape[0]:
            harmonised_annotation = prod_db_session.query(HarmonisedAnnotation).filter(
                HarmonisedAnnotation.id == int(float(task_run_1_dataframe.loc[i, "_row"].replace('X', "")))).first()
            task_run_1_dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
            task_run_1_dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
            task_run_1_dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
            task_run_1_dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
            task_run_1_dataframe.loc[i, "annotation_method"] = "%s" % (harmonised_annotation.annotation_method.name)
            #task_run_1_dataframe.loc[i, "annotation_url"] = url_for('CompoundView.harmonised_annotation',id=harmonised_annotation.id)
            i = i + 1

        task_run_1_dataframe['sign'] = np.sign(task_run_1_dataframe["estimates"])
        task_run_1_dataframe.loc[:, "signed_log_adjusted_pvalues"] = -1 * task_run_1_dataframe.loc[:, 'sign'] * np.log10(task_run_1_dataframe.loc[:, 'adjusted_pvalues'])
        task_run_1_dataframe.loc[:, "log_adjusted_pvalues"] = np.log10(task_run_1_dataframe.loc[:, 'adjusted_pvalues'])
        task_run_1_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_1_dataframe.loc[:, "log_adjusted_pvalues"].replace(np.inf, 17)
        task_run_1_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_1_dataframe.loc[:, "log_adjusted_pvalues"].replace(-np.inf, -17)

        task_run_2_dataframe["harmonised_annotation_id"] = None
        task_run_2_dataframe["assay"] = None
        task_run_2_dataframe["annotation_method"] = None
        task_run_2_dataframe["cpd_id"] = None
        task_run_2_dataframe["cpd_name"] = None
        task_run_2_dataframe["annotation_url"] = None
        harmonised_annotation_ids = []
        i = 0
        while i < task_run_2_dataframe.shape[0]:
            harmonised_annotation = prod_db_session.query(HarmonisedAnnotation).filter(
                HarmonisedAnnotation.id == int(float(task_run_2_dataframe.loc[i, "_row"].replace('X', "")))).first()
            task_run_2_dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
            task_run_2_dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
            task_run_2_dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
            task_run_2_dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
            task_run_2_dataframe.loc[i, "annotation_method"] = "%s" % (harmonised_annotation.annotation_method.name)
            # task_run_1_dataframe.loc[i, "annotation_url"] = url_for('CompoundView.harmonised_annotation',id=harmonised_annotation.id)
            i = i + 1

        task_run_2_dataframe['sign'] = np.sign(task_run_2_dataframe["estimates"])
        task_run_2_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_2_dataframe.loc[:, 'sign'] * np.log10(task_run_2_dataframe.loc[:, 'adjusted_pvalues'])
        task_run_2_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_2_dataframe.loc[:,"log_adjusted_pvalues"].replace(np.inf, 17)
        task_run_2_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_2_dataframe.loc[:,"log_adjusted_pvalues"].replace(-np.inf, -17)

        task_run_2_dataframe = task_run_2_dataframe.set_index('cpd_id')
        task_run_2_dataframe = task_run_2_dataframe.reindex(index=task_run_1_dataframe['cpd_id'])
        task_run_2_dataframe = task_run_2_dataframe.reset_index()
        task_run_1_dataframe = task_run_1_dataframe.reset_index()
        task_run_1_dataframe = task_run_1_dataframe.drop('index', axis=1)
        task_run_1_dataframe = task_run_1_dataframe.drop('_row', axis=1)
        task_run_2_dataframe = task_run_2_dataframe.drop('_row', axis=1)

        coefficients = pd.DataFrame(columns=['task_run_1', 'task_run_2'])
        coefficients['task_run_1'] = task_run_1_dataframe['estimates']
        coefficients['task_run_2'] = task_run_2_dataframe['estimates']
        correlation = coefficients.corr(method='pearson')
        correlation = correlation.iloc[0,0]

        assert correlation == 1.0

        mwas_table = task_run_1_dataframe.transpose().to_dict()

        pass

    def test_multiple_mwas(self):

        cache = Cache()

        task_run_ids = [5289,5559,5760]
        task_runs = prod_db_session.query(TaskRun).filter(TaskRun.id.in_(task_run_ids)).all()
        mwas_tables = {}
        adjusted_pvalues = pd.DataFrame(columns=['harmonised_annotation_id'])
        for task_run in task_runs:

            task_data = cache.get(task_run.get_task_data_cache_key())
            task_output = task_run.get_task_output(cache)
            sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])

            task_run_dataframe = pd.DataFrame.from_dict(task_output['mwas_results'])
            task_run_dataframe["harmonised_annotation_id"] = None
            task_run_dataframe["assay"] = None
            task_run_dataframe["annotation_method"] = None
            task_run_dataframe["cpd_id"] = None
            task_run_dataframe["cpd_name"] = None
            i = 0
            while i < task_run_dataframe.shape[0]:
                harmonised_annotation = prod_db_session.query(HarmonisedAnnotation).filter(
                    HarmonisedAnnotation.id == int(float(task_run_dataframe.loc[i, "_row"].replace('X', "")))).first()
                task_run_dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
                task_run_dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
                task_run_dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
                task_run_dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
                task_run_dataframe.loc[i, "annotation_method"] = "%s" % (harmonised_annotation.annotation_method.name)

                # find the corresponding row in the adjusted p-value table
                try:
                    row_index = adjusted_pvalues.loc[adjusted_pvalues['harmonised_annotation_id'] == harmonised_annotation.id].index[0]
                except:
                    row_index = len(adjusted_pvalues)
                    adjusted_pvalues.loc[row_index,'harmonised_annotation_id'] = harmonised_annotation.id

                adjusted_pvalues.loc[row_index, task_run.id] = task_run_dataframe.loc[i, 'adjusted_pvalues']

                i = i + 1
            task_run_dataframe = task_run_dataframe.set_index('harmonised_annotation_id')

            task_run_dataframe['sign'] = np.sign(task_run_dataframe["estimates"])
            task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:, 'sign'] * np.log10(
                task_run_dataframe.loc[:, 'adjusted_pvalues'])
            task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:,
                                                                  "log_adjusted_pvalues"].replace(np.inf, 17)
            task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:,
                                                                  "log_adjusted_pvalues"].replace(-np.inf, -17)

            mwas_tables[task_run.id] = task_run_dataframe

        adjusted_pvalues = adjusted_pvalues.set_index('harmonised_annotation_id')

        unfiltered_table = pd.DataFrame(
            columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
        all_indices = adjusted_pvalues.index.to_list()
        i = 0
        while i < len(all_indices):
            harmonised_annotation_id = str(all_indices[i])

            for task_run_id, task_run_dataframe in mwas_tables.items():
                task_run_label = 'tr_%s' % task_run_id
                if harmonised_annotation_id in task_run_dataframe.index:
                    mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                    if harmonised_annotation_id not in unfiltered_table.index:
                        row = {}
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = mwas_row['assay']
                        row['annotation_method'] = mwas_row['annotation_method']
                        row['cpd_id'] = mwas_row['cpd_id']
                        row['cpd_name'] = mwas_row['cpd_name']
                        unfiltered_table = unfiltered_table.append(pd.Series(row, name=harmonised_annotation_id))
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_estimates"] = utils.precision_round(
                        mwas_row['estimates'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_estimates_str"] = utils.precision_round(
                        mwas_row['estimates'], type='str')
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = utils.precision_round(
                        mwas_row['pvalues'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_pvalues_str"] = utils.precision_round(
                        mwas_row['pvalues'], type='str')
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = utils.precision_round(
                        mwas_row[
                            'adjusted_pvalues'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = utils.precision_round(
                        mwas_row['adjusted_pvalues'], type='str')
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = utils.precision_round(
                        mwas_row[
                            'log_adjusted_pvalues'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = utils.precision_round(
                        mwas_row['log_adjusted_pvalues'], type='str')

                else:
                    if harmonised_annotation_id not in unfiltered_table.index:
                        row = {}
                        harmonised_annotation = prod_db_session.query(HarmonisedAnnotation).filter(
                            HarmonisedAnnotation.id == int(float(harmonised_annotation_id))).first()
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = harmonised_annotation.assay.name
                        row['annotation_method'] = harmonised_annotation.annotation_method.name
                        row['cpd_id'] = harmonised_annotation.cpd_id
                        row['cpd_name'] = harmonised_annotation.cpd_name
                        unfiltered_table = unfiltered_table.append(pd.Series(row, name=harmonised_annotation_id))
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates_str"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues_str"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = None

            i = i + 1

        unfiltered_table = unfiltered_table.where(pd.notNone(unfiltered_table), None)

        # significant in all!
        consistently_significant = adjusted_pvalues[(adjusted_pvalues[adjusted_pvalues.columns] < 0.05).all(axis=1)]
        filtered_table = pd.DataFrame(columns=['harmonised_annotation_id','assay','annotation_method','cpd_id','cpd_name'])

        index_list = consistently_significant.index.to_list()
        i = 0
        while i < len(index_list):
            harmonised_annotation_id = str(index_list[i])

            for task_run_id,task_run_dataframe in mwas_tables.items():
                task_run_label = 'tr_%s' % task_run_id
                mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                if harmonised_annotation_id not in filtered_table.index:
                    row = {}
                    row['harmonised_annotation_id'] = harmonised_annotation_id
                    row['assay'] = mwas_row['assay']
                    row['annotation_method'] = mwas_row['annotation_method']
                    row['cpd_id'] = mwas_row['cpd_id']
                    row['cpd_name'] = mwas_row['cpd_name']
                    filtered_table = filtered_table.append(pd.Series(row,name=harmonised_annotation_id))

                filtered_table.loc[harmonised_annotation_id,task_run_label + "_estimates"] = mwas_row['estimates']
                filtered_table.loc[harmonised_annotation_id,task_run_label + "_pvalues"] = mwas_row['pvalues']
                filtered_table.loc[harmonised_annotation_id,task_run_label + "_adjusted_pvalues"] = mwas_row['adjusted_pvalues']
                filtered_table.loc[harmonised_annotation_id,task_run_label + "_log_adjusted_pvalues"] = mwas_row['log_adjusted_pvalues']

            i = i + 1

        significant_in_some = adjusted_pvalues[(adjusted_pvalues[adjusted_pvalues.columns] < 0.05).any(axis=1)]
        significant_in_some_and_not_all = significant_in_some[(np.isnan(significant_in_some[adjusted_pvalues.columns])).any(axis=1)]

        significant_in_some_and_not_all_dict = {}
        p = 0
        while p < significant_in_some_and_not_all.shape[1]:
            task_run_id = significant_in_some_and_not_all.columns[p]
            significant_rows = significant_in_some_and_not_all.loc[~np.isnan(significant_in_some_and_not_all[task_run_id]),task_run_id]
            index_list = significant_rows.index.to_list()

            if len(index_list) > 0:

                significant_in_some_table = pd.DataFrame(columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
                i = 0
                while i < len(index_list):
                    harmonised_annotation_id = str(index_list[i])



                    task_run_dataframe = mwas_tables[task_run_id]
                    mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                    if harmonised_annotation_id not in significant_in_some_table.index:
                        row = {}
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = mwas_row['assay']
                        row['annotation_method'] = mwas_row['annotation_method']
                        row['cpd_id'] = mwas_row['cpd_id']
                        row['cpd_name'] = mwas_row['cpd_name']
                        significant_in_some_table = significant_in_some_table.append(pd.Series(row, name=harmonised_annotation_id))

                    significant_in_some_table.loc[harmonised_annotation_id, "estimates"] = mwas_row['estimates']
                    significant_in_some_table.loc[harmonised_annotation_id, "pvalues"] = mwas_row['pvalues']
                    significant_in_some_table.loc[harmonised_annotation_id, "adjusted_pvalues"] = mwas_row['adjusted_pvalues']
                    significant_in_some_table.loc[harmonised_annotation_id, "log_adjusted_pvalues"] = mwas_row['log_adjusted_pvalues']

                    i = i + 1

                significant_in_some_and_not_all_dict[task_run_id] = significant_in_some_table.to_dict()

            p = p + 1

        significant_in_only_one_dict = {}
        for task_run_id in task_run_ids:
            significant_in_only_one_dict[task_run_id] = None
        i = 0
        while i < significant_in_some_and_not_all.shape[0]:
            if significant_in_some_and_not_all.iloc[i, :].isNone().sum() == 1:
                task_run_id = significant_in_some.iloc[i, :].notNone().index[0]
                harmonised_annotation_id = str(significant_in_some_and_not_all.index[i])
                if significant_in_only_one_dict[task_run_id] is None:
                    significant_in_only_one_dict[task_run_id] = pd.DataFrame()
                task_run_label = 'tr_%s' % task_run_id
                if harmonised_annotation_id not in significant_in_only_one_dict[task_run_id].index:
                    row = {}
                    row['harmonised_annotation_id'] = harmonised_annotation_id
                    row['assay'] = unfiltered_table.loc[harmonised_annotation_id, 'assay']
                    row['annotation_method'] = unfiltered_table.loc[harmonised_annotation_id, 'annotation_method']
                    row['cpd_id'] = unfiltered_table.loc[harmonised_annotation_id, 'cpd_id']
                    row['cpd_name'] = unfiltered_table.loc[harmonised_annotation_id, 'cpd_name']
                    significant_in_only_one_dict[task_run_id] = significant_in_only_one_dict[task_run_id].append(
                        pd.Series(row, name=harmonised_annotation_id))
                significant_in_only_one_dict[task_run_id].loc[harmonised_annotation_id, "estimates"] = \
                    significant_in_some_and_not_all.loc[harmonised_annotation_id, task_run_label + '_estimates']
                significant_in_only_one_dict[task_run_id].loc[harmonised_annotation_id, "pvalues"] = \
                    significant_in_some_and_not_all.loc[harmonised_annotation_id, task_run_label + '_pvalues']
                significant_in_only_one_dict[task_run_id].loc[harmonised_annotation_id, "adjusted_pvalues"] = \
                    significant_in_some_and_not_all.loc[harmonised_annotation_id, task_run_label + '_adjusted_pvalues']
                significant_in_only_one_dict[task_run_id].loc[harmonised_annotation_id, "log_adjusted_pvalues"] = \
                    significant_in_some_and_not_all.loc[
                        harmonised_annotation_id, task_run_label + '_log_adjusted_pvalues']
            i = i + 1
        print(significant_in_only_one_dict)
        #self.logger.info('significant_in_only_one_dict')
        #self.logger.info(significant_in_only_one_dict)
        #for task_run_id, table in significant_in_only_one_dict.items():
        #    print("%s %s %s" % (task_run_id,table.shape[0],table))

        pass

    def test_mwas_double(self):
        task_run_1_id = 1258
        task_run_2_id = 1262
        task_run_1 = prod_db_session.query(TaskRun).filter(TaskRun.id == task_run_1_id).first()
        task_run_2 = prod_db_session.query(TaskRun).filter(TaskRun.id == task_run_2_id).first()

        task_run_1_dataframe = pd.DataFrame.from_dict(task_run_1.output['mwas_results'])
        task_run_2_dataframe = pd.DataFrame.from_dict(task_run_2.output['mwas_results'])

        task_run_1_dataframe = self.build_mwas_table(task_run_1_dataframe)
        task_run_1_dataframe = task_run_1_dataframe.sort_values('log_adjusted_pvalues', ascending=True)
        task_run_2_dataframe = self.build_mwas_table(task_run_2_dataframe)
        task_run_2_dataframe = task_run_2_dataframe.sort_values('log_adjusted_pvalues', ascending=True)

        filtered_coefficients = pd.DataFrame(columns=[task_run_1_id, task_run_2_id])

        i = 0
        while i < task_run_1_dataframe.shape[0]:
            # find the corresponding row in the adjusted p-value table
            try:
                #adjusted_pvalues.loc[adjusted_pvalues['harmonised_annotation_id'] == harmonised_annotation.id].index[0]
                row_index = task_run_2_dataframe.loc[task_run_2_dataframe.loc[:,'cpd_id'] == task_run_1_dataframe.loc[i,'cpd_id']].index[0]
                filtered_coefficients.loc[i, task_run_1_id] = task_run_1_dataframe.loc[i, 'log_adjusted_pvalues']
                filtered_coefficients.loc[i, task_run_2_id] = task_run_2_dataframe.loc[row_index, 'log_adjusted_pvalues']
            except:
                pass

            i = i + 1

        correlation = filtered_coefficients.astype(float).corr(method='spearman')
        correlation = correlation.iloc[0, 1]
        filtered_coefficients.loc[:,'harmonised_annotation_id'] = task_run_1_dataframe.loc[:,'harmonised_annotation_id']

        test = json.dumps([task_run_1_dataframe.to_dict(),task_run_2_dataframe.to_dict(),filtered_coefficients.to_dict()])
        pass

    def build_mwas_table(self,dataframe):

        dataframe["harmonised_annotation_id"] = None
        dataframe["assay"] = None
        dataframe["annotation_method"] = None
        dataframe["cpd_id"] = None
        dataframe["cpd_name"] = None
        dataframe['sign'] = np.sign(dataframe["estimates"])
        dataframe['opposite_sign'] = None
        i = 0
        while i < dataframe.shape[0]:
            harmonised_annotation = prod_db_session.query(HarmonisedAnnotation).filter(
                HarmonisedAnnotation.id == int(float(dataframe.loc[i, "_row"].replace('X', "")))).first()
            dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
            dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
            dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
            dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
            dataframe.loc[i, "annotation_method"] = "%s" % (harmonised_annotation.annotation_method.name)

            if dataframe.loc[i,'sign'] < 0:
                dataframe.loc[i,'opposite_sign'] = 1
            else:
                dataframe.loc[i, 'opposite_sign'] = -1
            i = i + 1

        dataframe.loc[:,"log_adjusted_pvalues"] = dataframe.loc[:,'opposite_sign'] * np.log10(dataframe.loc[:,'adjusted_pvalues'])
        dataframe.loc[:,"log_adjusted_pvalues"] = dataframe.loc[:,"log_adjusted_pvalues"].replace(np.inf, 40)
        dataframe.loc[:,"log_adjusted_pvalues"] = dataframe.loc[:,"log_adjusted_pvalues"].replace(-np.inf, -40)

        return dataframe

    def test_load_features_and_output_var(self):
        cache = Cache()
        harmonised_annotation_id = '273'
        task_run_id = '2095'
        data = {}
        hardcoded_bmi_classes = ['(18.5, 25.0]','(25.0, 30.0]']
        harmonised_annotation = prod_db_session.query(HarmonisedAnnotation).filter(
            HarmonisedAnnotation.id == int(float(harmonised_annotation_id))).first()
        task_run = prod_db_session.query(TaskRun).filter(TaskRun.id == int(float(task_run_id))).first()
        task_data = cache.get(task_run.get_task_data_cache_key())
        feature_metadata = pd.DataFrame.from_dict(task_data['feature_metadata'])
        sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])
        model_y_variable = task_run.args['model_Y_variable']
        feature_row = int(feature_metadata.loc[feature_metadata.loc[:, 'harmonised_annotation_id'] == int(
            harmonised_annotation_id)].index[0])
        data['feature_estimates'] = task_run.output['mwas_estimates'][("X%s" % harmonised_annotation_id)]
        data['feature_summary'] = task_run.output['mwas_summaries'][("X%s" % harmonised_annotation_id)]
        intensity_data = np.matrix(task_data['intensity_data'])
        output_dataframe = pd.DataFrame(columns=['Y', 'feature intensity'])
        #output_dataframe = output_dataframe.where(pd.notNone(output_dataframe), None)
        data['cpd_id'] = harmonised_annotation.cpd_id
        data['task_run_id'] = str(task_run.id)
        data['cpd_name'] = harmonised_annotation.cpd_name
        data['Y_label'] = model_y_variable
        data['X_labels'] = task_run.args['model_X_variables']
        output_dataframe.loc[:, 'Y'] = sample_metadata.loc[:, model_y_variable].astype(float)
        output_dataframe.loc[:, 'project'] = sample_metadata.loc[:, 'Project']
        output_dataframe.loc[:, 'feature intensity'] = intensity_data[:, feature_row]
        output_dataframe = output_dataframe.where(pd.notNone(output_dataframe), None)
        #output_dataframe = output_dataframe.sort_values("Y")
        # main plot (no separation)
        data['std'] = output_dataframe.groupby("Y").apply(np.std).transpose().to_dict()
        #data['median'] = output_dataframe.groupby("Y").apply(np.median).transpose().to_dict()
        data['mean'] = output_dataframe.groupby("Y").apply(np.mean).transpose().to_dict()
        data['Y_intensity'] = output_dataframe.sort_values('Y').transpose().to_dict()
        model_x_variables = list(task_run.args['model_X_variables'])
        grouped_data = {}
        harmonised_metadata_fields = {}
        # Individual plots (seperated by 1 metadata field)
        X_variables_to_plot = []
        for model_x_variable in model_x_variables:
            if re.search('h_metadata::',model_x_variable):
                X_variables_to_plot.append(model_x_variable)
        for model_x_variable in X_variables_to_plot:

            grouped_data[model_x_variable] = {}
            output_dataframe.loc[:, model_x_variable] = sample_metadata.loc[:, model_x_variable]
            harmonised_metadata_fields[model_x_variable] = prod_db_session.query(HarmonisedMetadataField).filter(
                HarmonisedMetadataField.name == model_x_variable.replace("h_metadata::", "")).first()
            if harmonised_metadata_fields[model_x_variable].datatype in [
                HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric,
                HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric.value]:
                class_column = model_x_variable + "_class"
                output_dataframe[class_column] = pd.cut(output_dataframe.loc[:, model_x_variable],
                                                        [float("-inf")] + harmonised_metadata_fields[model_x_variable].classes + [
                                                            float("inf")],
                                                        include_lowest=True).astype('str')
            else:
                class_column = model_x_variable
            for group in output_dataframe[class_column].unique():
                if group != 'nan' and group is not None:
                    if((model_x_variable != 'h_metadata::BMI') or (group in hardcoded_bmi_classes)):
                        grouped_data[model_x_variable][group] = {}
                        filtered_dataframe = output_dataframe[output_dataframe[class_column] == group].dropna(
                            axis=0)
                        # filtered_dataframe['Y'] = filtered_dataframe['Y'].astype(float)
                        grouped_data[model_x_variable][group]['std'] = filtered_dataframe.groupby("Y").apply(
                            np.std).transpose().to_dict()
                        grouped_data[model_x_variable][group]['mean'] = filtered_dataframe.groupby("Y").apply(
                            np.mean).transpose().to_dict()
                        # grouped_data[model_x_variable][group]['median'] = filtered_dataframe.groupby("Y").apply(
                        #    np.median).transpose().to_dict()
                        grouped_data[model_x_variable][group][
                            'Y_intensities'] = filtered_dataframe.transpose().to_dict()

        # Seperate plots (seperated by 2 metadata fields)
        if len(X_variables_to_plot) > 1:
            i = 0
            while i < len(X_variables_to_plot):

                var_one = X_variables_to_plot[i]
                var_two = X_variables_to_plot[i + 1]
                combined_key = var_one + ":" + var_two
                grouped_data[combined_key] = {}
                if harmonised_metadata_fields[var_one].datatype in [
                    HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric,
                    HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric.value]:
                    var_one_class_column = var_one + "_class"
                else:
                    var_one_class_column = var_one
                if harmonised_metadata_fields[var_two].datatype in [
                    HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric,
                    HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric.value]:
                    var_two_class_column = var_two + "_class"
                else:
                    var_two_class_column = var_two
                var_one_groups = output_dataframe[var_one_class_column].unique()
                var_two_groups = output_dataframe[var_two_class_column].unique()
                for var_one_group in var_one_groups:
                    if var_one_group != 'nan' and var_one_group is not None:
                        if ((var_one != 'h_metadata::BMI') or (var_one_group in hardcoded_bmi_classes)):
                            for var_two_group in var_two_groups:
                                if var_two_group != 'nan' and var_two_group is not None:
                                    if ((var_two != 'h_metadata::BMI') or (var_two_group in hardcoded_bmi_classes)):
                                        group_key = var_one_group + ":" + var_two_group
                                        grouped_data[combined_key][group_key] = {}
                                        filtered_dataframe = output_dataframe[
                                            (output_dataframe[var_one_class_column] == var_one_group) & (
                                                        output_dataframe[var_two_class_column] == var_two_group)].dropna(axis=0)
                                        grouped_data[combined_key][group_key]['std'] = filtered_dataframe.groupby("Y").apply(
                                            np.std).transpose().to_dict()
                                        grouped_data[combined_key][group_key]['mean'] = filtered_dataframe.groupby("Y").apply(
                                            np.mean).transpose().to_dict()
                                        grouped_data[combined_key][group_key][
                                            'Y_intensities'] = filtered_dataframe.transpose().to_dict()

                i = i + 2


        data['grouped_data'] = grouped_data

        dumped = json.dumps(utils.convert_to_json_safe(data))
        
        pass

    def test_task_run_stores_transformed(self):
        cache = Cache()
        task_run_id = 1282
        task_run = prod_db_session.query(TaskRun).filter(TaskRun.id==task_run_id).first()
        task_data = cache.get(task_run.get_task_data_cache_key())
        actual_feature_metadata = pd.DataFrame.from_dict(task_data['feature_metadata'])
        actual_sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])
        actual_intensity_data = np.matrix(task_data['intensity_data'])
        args = task_run.args
        args['saved_query_id'] = task_run.saved_query_id
        task = RunMWAS(**args)
        output = task.run()
        expected_feature_metadata = pd.DataFrame.from_dict(task.data['feature_metadata'])
        expected_sample_metadata = pd.DataFrame.from_dict(task.data['sample_metadata'])
        expected_intensity_data = np.matrix(task.data['intensity_data'])

        assert actual_sample_metadata == expected_sample_metadata
        assert actual_intensity_data == expected_intensity_data
        assert actual_feature_metadata == expected_feature_metadata

    def test_precision_round(self):

        rounded = utils.precision_round(8.087999999999999e-58)

        rounded = utils.precision_round(2.1430000000000005e-34)

        pass

    def test_integrated_analysis_view(self):
        db_session = db.get_db_session()
        task_run_id = 7098
        task_run = db_session.query(TaskRun).filter(TaskRun.id==task_run_id).first()
        task_run_table = pd.DataFrame.from_dict(task_run.output['task_run_table'])

        data = {}
        data['saved_query_names'] = task_run_table.loc[:, 'query_name'].to_dict()
        data['saved_query_mwas_compare'] = {}
        all_mwas = []
        i = 0
        while i < task_run_table.shape[0]:
            mwas_tasks = []
            p = 0
            while p < task_run_table.shape[1]:
                if re.search('mwas', task_run_table.columns[p]):
                    mwas_tasks.append(str(task_run_table.iloc[i,p]))
                p = p + 1

            mwas_compare_url = "%s/analysisview/analysisresult/%s?compare=%s" % (config['WEBSERVER']['url'], mwas_tasks.pop(0), ",".join(mwas_tasks))
            all_mwas = all_mwas + mwas_tasks
            data['saved_query_mwas_compare'][task_run_table.iloc[:,i].index.values[0]] = mwas_compare_url
            i = i + 1

        data['all_mwas_compare'] = "%s/analysisview/analysisresult/%s?compare=%s" % (config['WEBSERVER']['url'], all_mwas.pop(0), ",".join(all_mwas))

    pass

    def test_cohort_spec(self):

        db_session = db.get_db_session()

        task_run = db_session.query(TaskRun).filter(TaskRun.id == 1282).first()

        task = task_run.get_task_class_object()

            #task.load_data()

    def test_get_analysis_results(self):
        cache = Cache()
        db_session = db.get_db_session()
        task_runs = db_session.query(TaskRun).filter(TaskRun.status==TaskRun.Status.success).all()
        for task_run in task_runs:
            key = 'analysis_view_table_row_%s' % task_run.id
            if cache.exists(key):
                try:
                    row = cache.get(key)
                except Exception as err:
                    pass

        pass

    def test_task_run_nan(self):
        db_session = db.get_db_session()
        upstream_task_run = db_session.query(TaskRun).filter(TaskRun.id==8557).all()
        task_run = db_session.query(TaskRun).filter(TaskRun.id == 8558).all()
        task = RunPCA(upstream_task_run_id=8557)
        task.run()
        pass


    def test_mwas_view(self):

        db_session = db.get_db_session()
        cache = Cache()

        task_runs = db_session.query(TaskRun).filter(TaskRun.id.in_([8687,8683])).all()
        mwas_summary = {}
        mwas_tables = {}
        task_run_dict = {}
        adjusted_pvalues = pd.DataFrame(columns=['harmonised_annotation_id'])
        for task_run in task_runs:

            task_run_dict[task_run.id] = task_run
            task_run_dataframe = pd.DataFrame.from_dict(task_run.output['mwas_results'])
            task_run_dataframe["harmonised_annotation_id"] = None
            task_run_dataframe["assay"] = None
            task_run_dataframe["annotation_method"] = None
            task_run_dataframe["cpd_id"] = None
            task_run_dataframe["cpd_name"] = None
            task_run_dataframe["aic"] = None
            i = 0
            while i < task_run_dataframe.shape[0]:
                harmonised_annotation = db_session.query(HarmonisedAnnotation).filter(
                    HarmonisedAnnotation.id == int(
                        float(task_run_dataframe.loc[i, "_row"].replace('X', "")))).first()
                task_run_dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
                task_run_dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
                task_run_dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
                task_run_dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
                task_run_dataframe.loc[i, "annotation_method"] = "%s" % (
                    harmonised_annotation.annotation_method.name)
                task_run_dataframe.loc[i, "aic"] = \
                task_run.output['mwas_summaries'][task_run_dataframe.loc[i, "_row"]]['aic'][0]
                # find the corresponding row in the adjusted p-value table
                try:
                    row_index = adjusted_pvalues.loc[
                        adjusted_pvalues['harmonised_annotation_id'] == harmonised_annotation.id].index[0]
                except:
                    row_index = len(adjusted_pvalues)
                    adjusted_pvalues.loc[row_index, 'harmonised_annotation_id'] = harmonised_annotation.id

                adjusted_pvalues.loc[row_index, task_run.id] = task_run_dataframe.loc[i, 'adjusted_pvalues']

                i = i + 1
            task_run_dataframe = task_run_dataframe.set_index('harmonised_annotation_id')

            task_run_dataframe['sign'] = np.sign(task_run_dataframe["estimates"])
            task_run_dataframe.loc[:, "log_adjusted_pvalues"] = -1 * task_run_dataframe.loc[:, 'sign'] * np.log10(
                task_run_dataframe.loc[:, 'adjusted_pvalues'])
            # task_run_dataframe.loc[:, "log_adjusted_pvalues"] = np.log10( task_run_dataframe.loc[:, 'adjusted_pvalues'])
            task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:,
                                                                "log_adjusted_pvalues"].replace(np.inf, 17)
            task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:,
                                                                "log_adjusted_pvalues"].replace(-np.inf, -17)

            mwas_tables[task_run.id] = task_run_dataframe

            # mwas_summary[task_run.id] =
            summary = {}
            summary['n_significant_features'] = len(task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)])
            mean_values = task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)].mean()
            summary['mean_significant_pvalue'] = utils.precision_round(mean_values['adjusted_pvalues'])
            min_values = task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)].min()
            summary['min_significant_pvalue'] = utils.precision_round(min_values['adjusted_pvalues'])
            max_values = task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)].max()
            summary['max_significant_pvalue'] = utils.precision_round(max_values['adjusted_pvalues'])
            task_data = cache.get(task_run.get_task_data_cache_key())
            sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])
            summary['n_samples'] = sample_metadata.shape[0]
            model_Y_variable = task_run.args['model_Y_variable']
            summary['min_y'] = sample_metadata[model_Y_variable].min()
            summary['max_y'] = sample_metadata[model_Y_variable].max()
            summary['n_features'] = pd.DataFrame.from_dict(task_data['feature_metadata']).shape[0]
            mwas_summary[task_run.id] = summary

        adjusted_pvalues = adjusted_pvalues.set_index('harmonised_annotation_id')

        unfiltered_table = pd.DataFrame(
            columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
        all_indices = adjusted_pvalues.index.to_list()
        i = 0
        while i < len(all_indices):
            harmonised_annotation_id = str(all_indices[i])

            for task_run_id, task_run_dataframe in mwas_tables.items():
                task_run_label = 'tr_%s' % task_run_id
                if harmonised_annotation_id in task_run_dataframe.index:
                    mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                    if harmonised_annotation_id not in unfiltered_table.index:
                        row = {}
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = mwas_row['assay']
                        row['annotation_method'] = mwas_row['annotation_method']
                        row['cpd_id'] = mwas_row['cpd_id']
                        row['cpd_name'] = mwas_row['cpd_name']
                        unfiltered_table = unfiltered_table.append(pd.Series(row, name=harmonised_annotation_id))
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_estimates"] = utils.precision_round(
                        mwas_row['estimates'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_estimates_str"] = utils.precision_round(
                        mwas_row['estimates'], type='str')
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = utils.precision_round(
                        mwas_row['pvalues'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_pvalues_str"] = utils.precision_round(
                        mwas_row['pvalues'], type='str')
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = utils.precision_round(
                        mwas_row[
                            'adjusted_pvalues'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = utils.precision_round(
                        mwas_row['adjusted_pvalues'], type='str')
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = utils.precision_round(
                        mwas_row[
                            'log_adjusted_pvalues'])
                    unfiltered_table.loc[
                        harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = utils.precision_round(
                        mwas_row['log_adjusted_pvalues'], type='str')
                    if methods[task_run_id] == 'linear':
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_aic"] = utils.precision_round(
                            mwas_row['aic'])
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_aic_str"] = utils.precision_round(
                            mwas_row['aic'], type='str')
                else:
                    if harmonised_annotation_id not in unfiltered_table.index:
                        row = {}
                        harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
                            HarmonisedAnnotation.id == int(float(harmonised_annotation_id))).first()
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = harmonised_annotation.assay.name
                        row['annotation_method'] = harmonised_annotation.annotation_method.name
                        row['cpd_id'] = harmonised_annotation.cpd_id
                        row['cpd_name'] = harmonised_annotation.cpd_name
                        unfiltered_table = unfiltered_table.append(pd.Series(row, name=harmonised_annotation_id))
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates_str"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues_str"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = None
                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = None
                    if methods[task_run_id] == 'linear':
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_aic"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_aic_str"] = None
            i = i + 1

        unfiltered_table = unfiltered_table.where(pd.notNone(unfiltered_table), None)

        filtered_pvalues = adjusted_pvalues[(adjusted_pvalues[adjusted_pvalues.columns] < 0.05).all(axis=1)]
        filtered_table = pd.DataFrame(
            columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
        index_list = filtered_pvalues.index.to_list()
        i = 0

        while i < len(index_list):
            harmonised_annotation_id = str(index_list[i])

            for task_run_id, task_run_dataframe in mwas_tables.items():
                task_run_label = 'tr_%s' % task_run_id
                mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                if harmonised_annotation_id not in filtered_table.index:
                    row = {}
                    row['harmonised_annotation_id'] = harmonised_annotation_id
                    row['assay'] = mwas_row['assay']
                    row['annotation_method'] = mwas_row['annotation_method']
                    row['cpd_id'] = mwas_row['cpd_id']
                    row['cpd_name'] = mwas_row['cpd_name']
                    filtered_table = filtered_table.append(pd.Series(row, name=harmonised_annotation_id))

                filtered_table.loc[harmonised_annotation_id, task_run_label + "_estimates"] = utils.precision_round(
                    mwas_row['estimates'])
                filtered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = utils.precision_round(
                    mwas_row['pvalues'])
                filtered_table.loc[
                    harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = utils.precision_round(mwas_row[
                                                                                                                'adjusted_pvalues'])
                filtered_table.loc[
                    harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = utils.precision_round(
                    mwas_row[
                        'log_adjusted_pvalues'])
                filtered_table.loc[harmonised_annotation_id, task_run_label + "_aic"] = utils.precision_round(
                    mwas_row['aic'])

            i = i + 1

        significant_in_some = adjusted_pvalues[(adjusted_pvalues[adjusted_pvalues.columns] < 0.05).any(axis=1)]
        significant_in_some_and_not_all = significant_in_some[
            (np.isnan(significant_in_some[adjusted_pvalues.columns])).any(axis=1)]

        significant_in_some_and_not_all_dict = {}
        p = 0
        while p < significant_in_some_and_not_all.shape[1]:
            task_run_id = significant_in_some_and_not_all.columns[p]
            significant_rows = significant_in_some_and_not_all.loc[
                ~np.isnan(significant_in_some_and_not_all[task_run_id])]
            # ~np.isnan(significant_in_some_and_not_all[task_run_id] & (significant_in_some_and_not_all[task_run_id] < 0.05))), task_run_id]
            index_list = significant_rows.index.to_list()

            if len(index_list) > 0:

                significant_in_some_table = pd.DataFrame(
                    columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
                i = 0
                while i < len(index_list):
                    harmonised_annotation_id = str(index_list[i])

                    task_run_dataframe = mwas_tables[task_run_id]
                    mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                    if harmonised_annotation_id not in significant_in_some_table.index:
                        row = {}
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = mwas_row['assay']
                        row['annotation_method'] = mwas_row['annotation_method']
                        row['cpd_id'] = mwas_row['cpd_id']
                        row['cpd_name'] = mwas_row['cpd_name']
                        significant_in_some_table = significant_in_some_table.append(
                            pd.Series(row, name=harmonised_annotation_id))


                    significant_in_some_table.loc[harmonised_annotation_id, "estimates"] = utils.precision_round(
                        mwas_row['estimates'])
                    significant_in_some_table.loc[harmonised_annotation_id, "pvalues"] = utils.precision_round(
                        mwas_row['pvalues'])
                    significant_in_some_table.loc[harmonised_annotation_id, "adjusted_pvalues"] = utils.precision_round(
                        mwas_row[
                            'adjusted_pvalues'])
                    significant_in_some_table.loc[
                        harmonised_annotation_id, "log_adjusted_pvalues"] = utils.precision_round(mwas_row[
                                                                                                      'log_adjusted_pvalues'])
                    significant_in_some_table.loc[harmonised_annotation_id, "aic"] = utils.precision_round(mwas_row['aic'])

                    i = i + 1

                significant_in_some_and_not_all_dict[task_run_id] = significant_in_some_table.sort_values(
                    'log_adjusted_pvalues').transpose().to_dict()

            p = p + 1

        data = {}
        data['mwas_summary'] = mwas_summary
        #sort_column = 'tr_%s_log_adjusted_pvalues' % request_data['task_run_ids'][0]
        # self.logger.debug(filtered_table.sort_values(sort_column).transpose().to_dict())
        #data['filtered_table'] = filtered_table.sort_values(sort_column).transpose().to_dict()
        #data['task_run_ids'] = request_data['task_run_ids']
        # template_data = {'mwas_table': data['filtered_table']}

        #data['mwas_consistent_table'] = self.render_template('analysis/mwas_table_multi.html', data=data)
        #data['mwas_significant_in_some_but_not_all_tables'] = []
        #for task_run_id, mwas_dict in significant_in_some_and_not_all_dict.items():
            #template_data = {'mwas_table': mwas_dict, 'task_run': task_run_dict[task_run_id]}
        #    data['mwas_significant_in_some_but_not_all_tables'].append()
        #        self.render_template('analysis/mwas_table.html', data=template_data))

        #data['success'] = True

    def test_upstream_task(self):

        args = {'batch_variable': 'Unique Batch',
         'correction_type': 'SR',
         'db_env': 'PROD',
         'exclude_features_not_in_all_projects': True,
         'saved_query_id': '135',
         'scaling': 'uv'}

        task = RunCombatCorrection(**args)
        task.run()

        args = {'correction_type': 'SR',
                 'db_env': 'PROD',
                 'exclude_features_not_in_all_projects': True,
                 'saved_query_id': '135',
                 'scaling': 'uv',
                 'transform': 'log',
                 'upstream_task_run_id': task.task_run.id}

        task2 = RunPCA(**args)
        task2.run()

    def test_mean_centring(self):

        args = {'correction_type': 'SR',
                'db_env': 'PROD',
                'exclude_features_not_in_all_projects': True,
                'saved_query_id': '135',
                'scaling': 'mc',
                'transform': 'log'}

        task2 = RunPCA(**args)
        task2.run()

    def test_task_label_split(self):

        task_labels = {"6389 AIRWAVE-AIRWAVE2-FINGER-MASALA plasma LPOS PPR ALL runmwas Pearson":"6389 AIRWAVE-AIRWAVE2-FINGER-MASALA<br/> plasma LPOS PPR ALL runmwas Pearson",
                       "6389 AIRWAVE-AIRWAVE2 plasma LPOS PPR ALL runmwas Pearson":"6389 AIRWAVE-AIRWAVE2 plasma LPOS PPR<br/> ALL runmwas Pearson",}
        for task_label, expected_output in task_labels.items():
            if len(task_label) > 30:
                substrings = task_label.split(' ')
                task_label_rebuilt = ""
                current_position = 0
                unbroken_position = 0
                for substring in substrings:
                    if current_position == 0:
                        task_label_rebuilt = substring
                    else:
                        task_label_rebuilt = task_label_rebuilt + " " + substring
                    reset_broken_position = False
                    if unbroken_position + len(substring) > 30:
                        task_label_rebuilt = task_label_rebuilt + "<br/>"
                        reset_broken_position = True
                    current_position = current_position + len(substring)
                    if reset_broken_position:
                        unbroken_position = 0
                    else:
                        unbroken_position = unbroken_position + len(substring)
            else:
                task_label_rebuilt = expected_output
            assert task_label_rebuilt == expected_output

    def test_order_by(self):

        data = {"5": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0110", "cpd_name": "LPC(22:6/0:0)",
                      "harmonised_annotation_id": "5", "tr_5289_adjusted_pvalues": 2.502e-21,
                      "tr_5289_adjusted_pvalues_str": "2.502e-21", "tr_5289_aic": -180800,
                      "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -3.472e-14,
                      "tr_5289_estimates_str": "-3.472e-14", "tr_5289_log_adjusted_pvalues": -20.6,
                      "tr_5289_log_adjusted_pvalues_str": "-20.6", "tr_5289_pvalues": 4.337e-24,
                      "tr_5289_pvalues_str": "4.337e-24", "tr_5760_adjusted_pvalues": 7.593e-27,
                      "tr_5760_adjusted_pvalues_str": "7.593e-27", "tr_5760_aic": -246000,
                      "tr_5760_aic_str": "-246000.0", "tr_5760_estimates": 1.921e-14,
                      "tr_5760_estimates_str": "1.921e-14", "tr_5760_log_adjusted_pvalues": 26.12,
                      "tr_5760_log_adjusted_pvalues_str": "26.12", "tr_5760_pvalues": 1.316e-29,
                      "tr_5760_pvalues_str": "1.316e-29"},
                "10": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0020", "cpd_name": "CAR(18:0-DC)",
                       "harmonised_annotation_id": "10", "tr_5289_adjusted_pvalues": 305.7,
                       "tr_5289_adjusted_pvalues_str": "305.7", "tr_5289_aic": -178400, "tr_5289_aic_str": "-178400.0",
                       "tr_5289_estimates": 3.287e-15, "tr_5289_estimates_str": "3.287e-15",
                       "tr_5289_log_adjusted_pvalues": -2.485, "tr_5289_log_adjusted_pvalues_str": "-2.485",
                       "tr_5289_pvalues": 0.5298, "tr_5289_pvalues_str": "0.5298", "tr_5760_adjusted_pvalues": 208.2,
                       "tr_5760_adjusted_pvalues_str": "208.2", "tr_5760_aic": -234000, "tr_5760_aic_str": "-234000.0",
                       "tr_5760_estimates": 7.079e-15, "tr_5760_estimates_str": "7.079e-15",
                       "tr_5760_log_adjusted_pvalues": -2.319, "tr_5760_log_adjusted_pvalues_str": "-2.319",
                       "tr_5760_pvalues": 0.3609, "tr_5760_pvalues_str": "0.3609"},
                "12": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0255", "cpd_name": "LPE(0:0/18:2)",
                       "harmonised_annotation_id": "12", "tr_5289_adjusted_pvalues": 133.9,
                       "tr_5289_adjusted_pvalues_str": "133.9", "tr_5289_aic": -176700, "tr_5289_aic_str": "-176700.0",
                       "tr_5289_estimates": 8.026e-15, "tr_5289_estimates_str": "8.026e-15",
                       "tr_5289_log_adjusted_pvalues": -2.127, "tr_5289_log_adjusted_pvalues_str": "-2.127",
                       "tr_5289_pvalues": 0.232, "tr_5289_pvalues_str": "0.232", "tr_5760_adjusted_pvalues": 480.5,
                       "tr_5760_adjusted_pvalues_str": "480.5", "tr_5760_aic": -236500, "tr_5760_aic_str": "-236500.0",
                       "tr_5760_estimates": -1.164e-15, "tr_5760_estimates_str": "-1.164e-15",
                       "tr_5760_log_adjusted_pvalues": 2.682, "tr_5760_log_adjusted_pvalues_str": "2.682",
                       "tr_5760_pvalues": 0.8328, "tr_5760_pvalues_str": "0.8328"},
                "15": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0087", "cpd_name": "LPC(0:0/22:6)",
                       "harmonised_annotation_id": "15", "tr_5289_adjusted_pvalues": 1.551e-17,
                       "tr_5289_adjusted_pvalues_str": "1.551e-17", "tr_5289_aic": -175300,
                       "tr_5289_aic_str": "-175300.0", "tr_5289_estimates": -8.121e-14,
                       "tr_5289_estimates_str": "-8.121e-14", "tr_5289_log_adjusted_pvalues": -16.81,
                       "tr_5289_log_adjusted_pvalues_str": "-16.81", "tr_5289_pvalues": 2.687e-20,
                       "tr_5289_pvalues_str": "2.687e-20", "tr_5760_adjusted_pvalues": 1.399e-21,
                       "tr_5760_adjusted_pvalues_str": "1.399e-21", "tr_5760_aic": -234900,
                       "tr_5760_aic_str": "-234900.0", "tr_5760_estimates": 7.071e-14,
                       "tr_5760_estimates_str": "7.071e-14", "tr_5760_log_adjusted_pvalues": 20.85,
                       "tr_5760_log_adjusted_pvalues_str": "20.85", "tr_5760_pvalues": 2.425e-24,
                       "tr_5760_pvalues_str": "2.425e-24"},
                "16": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0283",
                       "cpd_name": "PC(O-24:1/22:4) and/or PC(P-24:0/22:4)", "harmonised_annotation_id": "16",
                       "tr_5289_adjusted_pvalues": 1.348e-38, "tr_5289_adjusted_pvalues_str": "1.348e-38",
                       "tr_5289_aic": -181700, "tr_5289_aic_str": "-181700.0", "tr_5289_estimates": 4.313e-14,
                       "tr_5289_estimates_str": "4.313e-14", "tr_5289_log_adjusted_pvalues": 37.87,
                       "tr_5289_log_adjusted_pvalues_str": "37.87", "tr_5289_pvalues": 2.336e-41,
                       "tr_5289_pvalues_str": "2.336e-41", "tr_5760_adjusted_pvalues": 1.48e-36,
                       "tr_5760_adjusted_pvalues_str": "1.48e-36", "tr_5760_aic": -241300,
                       "tr_5760_aic_str": "-241300.0", "tr_5760_estimates": -4.276e-14,
                       "tr_5760_estimates_str": "-4.276e-14", "tr_5760_log_adjusted_pvalues": -35.83,
                       "tr_5760_log_adjusted_pvalues_str": "-35.83", "tr_5760_pvalues": 2.565e-39,
                       "tr_5760_pvalues_str": "2.565e-39"},
                "18": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0232", "cpd_name": "CAR(18:3)_2",
                       "harmonised_annotation_id": "18", "tr_5289_adjusted_pvalues": 213.1,
                       "tr_5289_adjusted_pvalues_str": "213.1", "tr_5289_aic": -178000, "tr_5289_aic_str": "-178000.0",
                       "tr_5289_estimates": 5.174e-15, "tr_5289_estimates_str": "5.174e-15",
                       "tr_5289_log_adjusted_pvalues": -2.329, "tr_5289_log_adjusted_pvalues_str": "-2.329",
                       "tr_5289_pvalues": 0.3693, "tr_5289_pvalues_str": "0.3693", "tr_5760_adjusted_pvalues": 71.78,
                       "tr_5760_adjusted_pvalues_str": "71.78", "tr_5760_aic": -238200, "tr_5760_aic_str": "-238200.0",
                       "tr_5760_estimates": -7.319e-15, "tr_5760_estimates_str": "-7.319e-15",
                       "tr_5760_log_adjusted_pvalues": 1.856, "tr_5760_log_adjusted_pvalues_str": "1.856",
                       "tr_5760_pvalues": 0.1244, "tr_5760_pvalues_str": "0.1244"},
                "19": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0070",
                       "cpd_name": "HexCer(d18:1/24:0)", "harmonised_annotation_id": "19",
                       "tr_5289_adjusted_pvalues": 125.1, "tr_5289_adjusted_pvalues_str": "125.1",
                       "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -1.06e-15,
                       "tr_5289_estimates_str": "-1.06e-15", "tr_5289_log_adjusted_pvalues": 2.097,
                       "tr_5289_log_adjusted_pvalues_str": "2.097", "tr_5289_pvalues": 0.2168,
                       "tr_5289_pvalues_str": "0.2168", "tr_5760_adjusted_pvalues": 19.81,
                       "tr_5760_adjusted_pvalues_str": "19.81", "tr_5760_aic": -243800, "tr_5760_aic_str": "-243800.0",
                       "tr_5760_estimates": -4.708e-15, "tr_5760_estimates_str": "-4.708e-15",
                       "tr_5760_log_adjusted_pvalues": 1.297, "tr_5760_log_adjusted_pvalues_str": "1.297",
                       "tr_5760_pvalues": 0.03433, "tr_5760_pvalues_str": "0.03433"},
                "22": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0234", "cpd_name": "CAR(24:1)",
                       "harmonised_annotation_id": "22", "tr_5289_adjusted_pvalues": 1.307e-10,
                       "tr_5289_adjusted_pvalues_str": "1.307e-10", "tr_5289_aic": -177500,
                       "tr_5289_aic_str": "-177500.0", "tr_5289_estimates": 4.485e-14,
                       "tr_5289_estimates_str": "4.485e-14", "tr_5289_log_adjusted_pvalues": 9.884,
                       "tr_5289_log_adjusted_pvalues_str": "9.884", "tr_5289_pvalues": 2.265e-13,
                       "tr_5289_pvalues_str": "2.265e-13", "tr_5760_adjusted_pvalues": 7.746e-15,
                       "tr_5760_adjusted_pvalues_str": "7.746e-15", "tr_5760_aic": -242300,
                       "tr_5760_aic_str": "-242300.0", "tr_5760_estimates": 2.367e-14,
                       "tr_5760_estimates_str": "2.367e-14", "tr_5760_log_adjusted_pvalues": 14.11,
                       "tr_5760_log_adjusted_pvalues_str": "14.11", "tr_5760_pvalues": 1.342e-17,
                       "tr_5760_pvalues_str": "1.342e-17"},
                "23": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0071",
                       "cpd_name": "LacCer(d18:1/16:0)", "harmonised_annotation_id": "23",
                       "tr_5289_adjusted_pvalues": 0.009248, "tr_5289_adjusted_pvalues_str": "0.009248",
                       "tr_5289_aic": -178800, "tr_5289_aic_str": "-178800.0", "tr_5289_estimates": 2.113e-14,
                       "tr_5289_estimates_str": "2.113e-14", "tr_5289_log_adjusted_pvalues": 2.034,
                       "tr_5289_log_adjusted_pvalues_str": "2.034", "tr_5289_pvalues": 0.00001603,
                       "tr_5289_pvalues_str": "1.603e-05", "tr_5760_adjusted_pvalues": 0.8306,
                       "tr_5760_adjusted_pvalues_str": "0.8306", "tr_5760_aic": -249200, "tr_5760_aic_str": "-249200.0",
                       "tr_5760_estimates": -3.604e-15, "tr_5760_estimates_str": "-3.604e-15",
                       "tr_5760_log_adjusted_pvalues": -0.08059, "tr_5760_log_adjusted_pvalues_str": "-0.08059",
                       "tr_5760_pvalues": 0.00144, "tr_5760_pvalues_str": "0.00144"},
                "26": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0333", "cpd_name": "TG(55:3)",
                       "harmonised_annotation_id": "26", "tr_5289_adjusted_pvalues": 0.0531,
                       "tr_5289_adjusted_pvalues_str": "0.0531", "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0",
                       "tr_5289_estimates": -1.54e-14, "tr_5289_estimates_str": "-1.54e-14",
                       "tr_5289_log_adjusted_pvalues": -1.275, "tr_5289_log_adjusted_pvalues_str": "-1.275",
                       "tr_5289_pvalues": 0.00009204, "tr_5289_pvalues_str": "9.204e-05",
                       "tr_5760_adjusted_pvalues": 0.01106, "tr_5760_adjusted_pvalues_str": "0.01106",
                       "tr_5760_aic": -245900, "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": -7.453e-15,
                       "tr_5760_estimates_str": "-7.453e-15", "tr_5760_log_adjusted_pvalues": -1.956,
                       "tr_5760_log_adjusted_pvalues_str": "-1.956", "tr_5760_pvalues": 0.00001917,
                       "tr_5760_pvalues_str": "1.917e-05"},
                "28": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0357", "cpd_name": "TG(58:7)_1",
                       "harmonised_annotation_id": "28", "tr_5289_adjusted_pvalues": 72.89,
                       "tr_5289_adjusted_pvalues_str": "72.89", "tr_5289_aic": -193200, "tr_5289_aic_str": "-193200.0",
                       "tr_5289_estimates": -6.506e-16, "tr_5289_estimates_str": "-6.506e-16",
                       "tr_5289_log_adjusted_pvalues": 1.863, "tr_5289_log_adjusted_pvalues_str": "1.863",
                       "tr_5289_pvalues": 0.1263, "tr_5289_pvalues_str": "0.1263", "tr_5760_adjusted_pvalues": None,
                       "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                       "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                       "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "33": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0048",
                       "cpd_name": "Cer(d18:1/26:1)", "harmonised_annotation_id": "33",
                       "tr_5289_adjusted_pvalues": 5.96e-51, "tr_5289_adjusted_pvalues_str": "5.96e-51",
                       "tr_5289_aic": -178000, "tr_5289_aic_str": "-178000.0", "tr_5289_estimates": -8.969e-14,
                       "tr_5289_estimates_str": "-8.969e-14", "tr_5289_log_adjusted_pvalues": -50.22,
                       "tr_5289_log_adjusted_pvalues_str": "-50.22", "tr_5289_pvalues": 1.033e-53,
                       "tr_5289_pvalues_str": "1.033e-53", "tr_5760_adjusted_pvalues": 2.43e-67,
                       "tr_5760_adjusted_pvalues_str": "2.43e-67", "tr_5760_aic": -240000,
                       "tr_5760_aic_str": "-240000.0", "tr_5760_estimates": 6.645e-14,
                       "tr_5760_estimates_str": "6.645e-14", "tr_5760_log_adjusted_pvalues": 66.61,
                       "tr_5760_log_adjusted_pvalues_str": "66.61", "tr_5760_pvalues": 4.212e-70,
                       "tr_5760_pvalues_str": "4.212e-70"},
                "34": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0026", "cpd_name": "CAR(20:2)",
                       "harmonised_annotation_id": "34", "tr_5289_adjusted_pvalues": 272.1,
                       "tr_5289_adjusted_pvalues_str": "272.1", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                       "tr_5289_estimates": 6.294e-16, "tr_5289_estimates_str": "6.294e-16",
                       "tr_5289_log_adjusted_pvalues": -2.435, "tr_5289_log_adjusted_pvalues_str": "-2.435",
                       "tr_5289_pvalues": 0.4716, "tr_5289_pvalues_str": "0.4716", "tr_5760_adjusted_pvalues": None,
                       "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                       "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                       "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "36": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0181", "cpd_name": "SM(d18:1/18:0)",
                       "harmonised_annotation_id": "36", "tr_5289_adjusted_pvalues": None,
                       "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                       "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                       "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                       "tr_5760_adjusted_pvalues": 5.371e-25, "tr_5760_adjusted_pvalues_str": "5.371e-25",
                       "tr_5760_aic": -234700, "tr_5760_aic_str": "-234700.0", "tr_5760_estimates": 7.727e-14,
                       "tr_5760_estimates_str": "7.727e-14", "tr_5760_log_adjusted_pvalues": 24.27,
                       "tr_5760_log_adjusted_pvalues_str": "24.27", "tr_5760_pvalues": 9.309e-28,
                       "tr_5760_pvalues_str": "9.309e-28"},
                "37": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0167", "cpd_name": "PE(16:0/20:4)",
                       "harmonised_annotation_id": "37", "tr_5289_adjusted_pvalues": 213.1,
                       "tr_5289_adjusted_pvalues_str": "213.1", "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0",
                       "tr_5289_estimates": -1.443e-15, "tr_5289_estimates_str": "-1.443e-15",
                       "tr_5289_log_adjusted_pvalues": 2.329, "tr_5289_log_adjusted_pvalues_str": "2.329",
                       "tr_5289_pvalues": 0.3693, "tr_5289_pvalues_str": "0.3693", "tr_5760_adjusted_pvalues": 42.7,
                       "tr_5760_adjusted_pvalues_str": "42.7", "tr_5760_aic": -235800, "tr_5760_aic_str": "-235800.0",
                       "tr_5760_estimates": 1.126e-14, "tr_5760_estimates_str": "1.126e-14",
                       "tr_5760_log_adjusted_pvalues": -1.63, "tr_5760_log_adjusted_pvalues_str": "-1.63",
                       "tr_5760_pvalues": 0.07401, "tr_5760_pvalues_str": "0.07401"},
                "55": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0231", "cpd_name": "CAR(18:3)_1",
                       "harmonised_annotation_id": "55", "tr_5289_adjusted_pvalues": 126.9,
                       "tr_5289_adjusted_pvalues_str": "126.9", "tr_5289_aic": -175900, "tr_5289_aic_str": "-175900.0",
                       "tr_5289_estimates": -9.88e-15, "tr_5289_estimates_str": "-9.88e-15",
                       "tr_5289_log_adjusted_pvalues": 2.103, "tr_5289_log_adjusted_pvalues_str": "2.103",
                       "tr_5289_pvalues": 0.2199, "tr_5289_pvalues_str": "0.2199", "tr_5760_adjusted_pvalues": 147.7,
                       "tr_5760_adjusted_pvalues_str": "147.7", "tr_5760_aic": -233100, "tr_5760_aic_str": "-233100.0",
                       "tr_5760_estimates": -1.011e-14, "tr_5760_estimates_str": "-1.011e-14",
                       "tr_5760_log_adjusted_pvalues": 2.169, "tr_5760_log_adjusted_pvalues_str": "2.169",
                       "tr_5760_pvalues": 0.2559, "tr_5760_pvalues_str": "0.2559"},
                "56": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0084", "cpd_name": "LPC(0:0/20:3)",
                       "harmonised_annotation_id": "56", "tr_5289_adjusted_pvalues": 339.4,
                       "tr_5289_adjusted_pvalues_str": "339.4", "tr_5289_aic": -185400, "tr_5289_aic_str": "-185400.0",
                       "tr_5289_estimates": 8.363e-16, "tr_5289_estimates_str": "8.363e-16",
                       "tr_5289_log_adjusted_pvalues": -2.531, "tr_5289_log_adjusted_pvalues_str": "-2.531",
                       "tr_5289_pvalues": 0.5883, "tr_5289_pvalues_str": "0.5883", "tr_5760_adjusted_pvalues": 105.1,
                       "tr_5760_adjusted_pvalues_str": "105.1", "tr_5760_aic": -234800, "tr_5760_aic_str": "-234800.0",
                       "tr_5760_estimates": -9.094e-15, "tr_5760_estimates_str": "-9.094e-15",
                       "tr_5760_log_adjusted_pvalues": 2.022, "tr_5760_log_adjusted_pvalues_str": "2.022",
                       "tr_5760_pvalues": 0.1821, "tr_5760_pvalues_str": "0.1821"},
                "59": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0076", "cpd_name": "LPC(0:0/14:0)",
                       "harmonised_annotation_id": "59", "tr_5289_adjusted_pvalues": 0.000007184,
                       "tr_5289_adjusted_pvalues_str": "7.184e-06", "tr_5289_aic": -181500,
                       "tr_5289_aic_str": "-181500.0", "tr_5289_estimates": 1.703e-14,
                       "tr_5289_estimates_str": "1.703e-14", "tr_5289_log_adjusted_pvalues": 5.144,
                       "tr_5289_log_adjusted_pvalues_str": "5.144", "tr_5289_pvalues": 1.245e-8,
                       "tr_5289_pvalues_str": "1.245e-08", "tr_5760_adjusted_pvalues": None,
                       "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                       "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                       "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "61": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0165",
                       "cpd_name": "PC(O-18:1/18:1) and/or PC(P-18:0/18:1)", "harmonised_annotation_id": "61",
                       "tr_5289_adjusted_pvalues": 178.1, "tr_5289_adjusted_pvalues_str": "178.1",
                       "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0", "tr_5289_estimates": 3.478e-15,
                       "tr_5289_estimates_str": "3.478e-15", "tr_5289_log_adjusted_pvalues": -2.251,
                       "tr_5289_log_adjusted_pvalues_str": "-2.251", "tr_5289_pvalues": 0.3087,
                       "tr_5289_pvalues_str": "0.3087", "tr_5760_adjusted_pvalues": 283.9,
                       "tr_5760_adjusted_pvalues_str": "283.9", "tr_5760_aic": -237800, "tr_5760_aic_str": "-237800.0",
                       "tr_5760_estimates": -3.613e-15, "tr_5760_estimates_str": "-3.613e-15",
                       "tr_5760_log_adjusted_pvalues": 2.453, "tr_5760_log_adjusted_pvalues_str": "2.453",
                       "tr_5760_pvalues": 0.492, "tr_5760_pvalues_str": "0.492"},
                "63": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0168", "cpd_name": "PE(18:0/20:4)",
                       "harmonised_annotation_id": "63", "tr_5289_adjusted_pvalues": 0.214,
                       "tr_5289_adjusted_pvalues_str": "0.214", "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0",
                       "tr_5289_estimates": 5.409e-15, "tr_5289_estimates_str": "5.409e-15",
                       "tr_5289_log_adjusted_pvalues": 0.6697, "tr_5289_log_adjusted_pvalues_str": "0.6697",
                       "tr_5289_pvalues": 0.0003708, "tr_5289_pvalues_str": "0.0003708",
                       "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf",
                       "tr_5760_aic_str": "inf", "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0",
                       "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                       "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "65": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0306", "cpd_name": "TG(50:5)",
                       "harmonised_annotation_id": "65", "tr_5289_adjusted_pvalues": 0.00002662,
                       "tr_5289_adjusted_pvalues_str": "2.662e-05", "tr_5289_aic": -175600,
                       "tr_5289_aic_str": "-175600.0", "tr_5289_estimates": 4.606e-14,
                       "tr_5289_estimates_str": "4.606e-14", "tr_5289_log_adjusted_pvalues": 4.575,
                       "tr_5289_log_adjusted_pvalues_str": "4.575", "tr_5289_pvalues": 4.614e-8,
                       "tr_5289_pvalues_str": "4.614e-08", "tr_5760_adjusted_pvalues": 0.0003858,
                       "tr_5760_adjusted_pvalues_str": "0.0003858", "tr_5760_aic": -235200,
                       "tr_5760_aic_str": "-235200.0", "tr_5760_estimates": 3.383e-14,
                       "tr_5760_estimates_str": "3.383e-14", "tr_5760_log_adjusted_pvalues": 3.414,
                       "tr_5760_log_adjusted_pvalues_str": "3.414", "tr_5760_pvalues": 6.687e-7,
                       "tr_5760_pvalues_str": "6.687e-07"},
                "73": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0193", "cpd_name": "SM(d18:2/22:0)",
                       "harmonised_annotation_id": "73", "tr_5289_adjusted_pvalues": 5.46e-8,
                       "tr_5289_adjusted_pvalues_str": "5.46e-08", "tr_5289_aic": -180000,
                       "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": -2.426e-14,
                       "tr_5289_estimates_str": "-2.426e-14", "tr_5289_log_adjusted_pvalues": -7.263,
                       "tr_5289_log_adjusted_pvalues_str": "-7.263", "tr_5289_pvalues": 9.463e-11,
                       "tr_5289_pvalues_str": "9.463e-11", "tr_5760_adjusted_pvalues": 3.039e-11,
                       "tr_5760_adjusted_pvalues_str": "3.039e-11", "tr_5760_aic": -241200,
                       "tr_5760_aic_str": "-241200.0", "tr_5760_estimates": 2.258e-14,
                       "tr_5760_estimates_str": "2.258e-14", "tr_5760_log_adjusted_pvalues": 10.52,
                       "tr_5760_log_adjusted_pvalues_str": "10.52", "tr_5760_pvalues": 5.266e-14,
                       "tr_5760_pvalues_str": "5.266e-14"},
                "76": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0278",
                       "cpd_name": "PC(O-24:0/18:2)", "harmonised_annotation_id": "76",
                       "tr_5289_adjusted_pvalues": 105.4, "tr_5289_adjusted_pvalues_str": "105.4",
                       "tr_5289_aic": -176600, "tr_5289_aic_str": "-176600.0", "tr_5289_estimates": -9.189e-15,
                       "tr_5289_estimates_str": "-9.189e-15", "tr_5289_log_adjusted_pvalues": 2.023,
                       "tr_5289_log_adjusted_pvalues_str": "2.023", "tr_5289_pvalues": 0.1826,
                       "tr_5289_pvalues_str": "0.1826", "tr_5760_adjusted_pvalues": 59.64,
                       "tr_5760_adjusted_pvalues_str": "59.64", "tr_5760_aic": -241600, "tr_5760_aic_str": "-241600.0",
                       "tr_5760_estimates": -4.756e-15, "tr_5760_estimates_str": "-4.756e-15",
                       "tr_5760_log_adjusted_pvalues": 1.776, "tr_5760_log_adjusted_pvalues_str": "1.776",
                       "tr_5760_pvalues": 0.1034, "tr_5760_pvalues_str": "0.1034"},
                "78": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0117",
                       "cpd_name": "LPC(P-16:0/0:0)", "harmonised_annotation_id": "78",
                       "tr_5289_adjusted_pvalues": 537.3, "tr_5289_adjusted_pvalues_str": "537.3",
                       "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": -1.419e-16,
                       "tr_5289_estimates_str": "-1.419e-16", "tr_5289_log_adjusted_pvalues": 2.73,
                       "tr_5289_log_adjusted_pvalues_str": "2.73", "tr_5289_pvalues": 0.9312,
                       "tr_5289_pvalues_str": "0.9312", "tr_5760_adjusted_pvalues": 441.7,
                       "tr_5760_adjusted_pvalues_str": "441.7", "tr_5760_aic": -242600, "tr_5760_aic_str": "-242600.0",
                       "tr_5760_estimates": 7.684e-16, "tr_5760_estimates_str": "7.684e-16",
                       "tr_5760_log_adjusted_pvalues": -2.645, "tr_5760_log_adjusted_pvalues_str": "-2.645",
                       "tr_5760_pvalues": 0.7654, "tr_5760_pvalues_str": "0.7654"},
                "79": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0261", "cpd_name": "PC(18:1/22:6)",
                       "harmonised_annotation_id": "79", "tr_5289_adjusted_pvalues": 7.521e-23,
                       "tr_5289_adjusted_pvalues_str": "7.521e-23", "tr_5289_aic": -175700,
                       "tr_5289_aic_str": "-175700.0", "tr_5289_estimates": -8.694e-14,
                       "tr_5289_estimates_str": "-8.694e-14", "tr_5289_log_adjusted_pvalues": -22.12,
                       "tr_5289_log_adjusted_pvalues_str": "-22.12", "tr_5289_pvalues": 1.304e-25,
                       "tr_5289_pvalues_str": "1.304e-25", "tr_5760_adjusted_pvalues": 1.035e-29,
                       "tr_5760_adjusted_pvalues_str": "1.035e-29", "tr_5760_aic": -240300,
                       "tr_5760_aic_str": "-240300.0", "tr_5760_estimates": 4.183e-14,
                       "tr_5760_estimates_str": "4.183e-14", "tr_5760_log_adjusted_pvalues": 28.98,
                       "tr_5760_log_adjusted_pvalues_str": "28.98", "tr_5760_pvalues": 1.794e-32,
                       "tr_5760_pvalues_str": "1.794e-32"},
                "82": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0006",
                       "cpd_name": "Tetradecanoylcarnitine CAR(14:0)", "harmonised_annotation_id": "82",
                       "tr_5289_adjusted_pvalues": 31.05, "tr_5289_adjusted_pvalues_str": "31.05",
                       "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0", "tr_5289_estimates": -6.283e-15,
                       "tr_5289_estimates_str": "-6.283e-15", "tr_5289_log_adjusted_pvalues": 1.492,
                       "tr_5289_log_adjusted_pvalues_str": "1.492", "tr_5289_pvalues": 0.05382,
                       "tr_5289_pvalues_str": "0.05382", "tr_5760_adjusted_pvalues": 0.372,
                       "tr_5760_adjusted_pvalues_str": "0.372", "tr_5760_aic": -241700, "tr_5760_aic_str": "-241700.0",
                       "tr_5760_estimates": -1.091e-14, "tr_5760_estimates_str": "-1.091e-14",
                       "tr_5760_log_adjusted_pvalues": -0.4295, "tr_5760_log_adjusted_pvalues_str": "-0.4295",
                       "tr_5760_pvalues": 0.0006447, "tr_5760_pvalues_str": "0.0006447"},
                "83": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0062", "cpd_name": "DG(34:2)",
                       "harmonised_annotation_id": "83", "tr_5289_adjusted_pvalues": 11.87,
                       "tr_5289_adjusted_pvalues_str": "11.87", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                       "tr_5289_estimates": -2.2e-15, "tr_5289_estimates_str": "-2.2e-15",
                       "tr_5289_log_adjusted_pvalues": 1.074, "tr_5289_log_adjusted_pvalues_str": "1.074",
                       "tr_5289_pvalues": 0.02057, "tr_5289_pvalues_str": "0.02057",
                       "tr_5760_adjusted_pvalues": 0.000006489, "tr_5760_adjusted_pvalues_str": "6.489e-06",
                       "tr_5760_aic": -241900, "tr_5760_aic_str": "-241900.0", "tr_5760_estimates": -1.804e-14,
                       "tr_5760_estimates_str": "-1.804e-14", "tr_5760_log_adjusted_pvalues": -5.188,
                       "tr_5760_log_adjusted_pvalues_str": "-5.188", "tr_5760_pvalues": 1.125e-8,
                       "tr_5760_pvalues_str": "1.125e-08"},
                "85": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0279",
                       "cpd_name": "PC(O-24:0/20:4)", "harmonised_annotation_id": "85",
                       "tr_5289_adjusted_pvalues": 7.06, "tr_5289_adjusted_pvalues_str": "7.06", "tr_5289_aic": -185500,
                       "tr_5289_aic_str": "-185500.0", "tr_5289_estimates": 3.891e-15,
                       "tr_5289_estimates_str": "3.891e-15", "tr_5289_log_adjusted_pvalues": -0.8488,
                       "tr_5289_log_adjusted_pvalues_str": "-0.8488", "tr_5289_pvalues": 0.01223,
                       "tr_5289_pvalues_str": "0.01223", "tr_5760_adjusted_pvalues": 0.02904,
                       "tr_5760_adjusted_pvalues_str": "0.02904", "tr_5760_aic": -242000,
                       "tr_5760_aic_str": "-242000.0", "tr_5760_estimates": -1.129e-14,
                       "tr_5760_estimates_str": "-1.129e-14", "tr_5760_log_adjusted_pvalues": -1.537,
                       "tr_5760_log_adjusted_pvalues_str": "-1.537", "tr_5760_pvalues": 0.00005032,
                       "tr_5760_pvalues_str": "5.032e-05"},
                "91": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0068",
                       "cpd_name": "HexCer(d18:1/16:0)", "harmonised_annotation_id": "91",
                       "tr_5289_adjusted_pvalues": 0.4696, "tr_5289_adjusted_pvalues_str": "0.4696",
                       "tr_5289_aic": -178700, "tr_5289_aic_str": "-178700.0", "tr_5289_estimates": 1.586e-14,
                       "tr_5289_estimates_str": "1.586e-14", "tr_5289_log_adjusted_pvalues": 0.3283,
                       "tr_5289_log_adjusted_pvalues_str": "0.3283", "tr_5289_pvalues": 0.0008138,
                       "tr_5289_pvalues_str": "0.0008138", "tr_5760_adjusted_pvalues": 66.78,
                       "tr_5760_adjusted_pvalues_str": "66.78", "tr_5760_aic": -248000, "tr_5760_aic_str": "-248000.0",
                       "tr_5760_estimates": -1.984e-15, "tr_5760_estimates_str": "-1.984e-15",
                       "tr_5760_log_adjusted_pvalues": 1.825, "tr_5760_log_adjusted_pvalues_str": "1.825",
                       "tr_5760_pvalues": 0.1157, "tr_5760_pvalues_str": "0.1157"},
                "93": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0363", "cpd_name": "TG(60:3)",
                       "harmonised_annotation_id": "93", "tr_5289_adjusted_pvalues": 2.588,
                       "tr_5289_adjusted_pvalues_str": "2.588", "tr_5289_aic": -176200, "tr_5289_aic_str": "-176200.0",
                       "tr_5289_estimates": 2.598e-14, "tr_5289_estimates_str": "2.598e-14",
                       "tr_5289_log_adjusted_pvalues": -0.413, "tr_5289_log_adjusted_pvalues_str": "-0.413",
                       "tr_5289_pvalues": 0.004486, "tr_5289_pvalues_str": "0.004486",
                       "tr_5760_adjusted_pvalues": 9.195, "tr_5760_adjusted_pvalues_str": "9.195",
                       "tr_5760_aic": -240400, "tr_5760_aic_str": "-240400.0", "tr_5760_estimates": -9.754e-15,
                       "tr_5760_estimates_str": "-9.754e-15", "tr_5760_log_adjusted_pvalues": 0.9635,
                       "tr_5760_log_adjusted_pvalues_str": "0.9635", "tr_5760_pvalues": 0.01594,
                       "tr_5760_pvalues_str": "0.01594"},
                "94": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0015", "cpd_name": "CAR(14:2)",
                       "harmonised_annotation_id": "94", "tr_5289_adjusted_pvalues": 455.5,
                       "tr_5289_adjusted_pvalues_str": "455.5", "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0",
                       "tr_5289_estimates": -4.518e-16, "tr_5289_estimates_str": "-4.518e-16",
                       "tr_5289_log_adjusted_pvalues": 2.659, "tr_5289_log_adjusted_pvalues_str": "2.659",
                       "tr_5289_pvalues": 0.7895, "tr_5289_pvalues_str": "0.7895", "tr_5760_adjusted_pvalues": 233.7,
                       "tr_5760_adjusted_pvalues_str": "233.7", "tr_5760_aic": -236900, "tr_5760_aic_str": "-236900.0",
                       "tr_5760_estimates": -4.631e-15, "tr_5760_estimates_str": "-4.631e-15",
                       "tr_5760_log_adjusted_pvalues": 2.369, "tr_5760_log_adjusted_pvalues_str": "2.369",
                       "tr_5760_pvalues": 0.4051, "tr_5760_pvalues_str": "0.4051"},
                "96": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0104",
                       "cpd_name": "LPC(20:3/0:0)_1", "harmonised_annotation_id": "96",
                       "tr_5289_adjusted_pvalues": 291.8, "tr_5289_adjusted_pvalues_str": "291.8",
                       "tr_5289_aic": -175800, "tr_5289_aic_str": "-175800.0", "tr_5289_estimates": 5.205e-15,
                       "tr_5289_estimates_str": "5.205e-15", "tr_5289_log_adjusted_pvalues": -2.465,
                       "tr_5289_log_adjusted_pvalues_str": "-2.465", "tr_5289_pvalues": 0.5057,
                       "tr_5289_pvalues_str": "0.5057", "tr_5760_adjusted_pvalues": 244.9,
                       "tr_5760_adjusted_pvalues_str": "244.9", "tr_5760_aic": -238900, "tr_5760_aic_str": "-238900.0",
                       "tr_5760_estimates": -3.255e-15, "tr_5760_estimates_str": "-3.255e-15",
                       "tr_5760_log_adjusted_pvalues": 2.389, "tr_5760_log_adjusted_pvalues_str": "2.389",
                       "tr_5760_pvalues": 0.4244, "tr_5760_pvalues_str": "0.4244"},
                "97": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0122",
                       "cpd_name": "LPE(P-18:0/0:0)", "harmonised_annotation_id": "97",
                       "tr_5289_adjusted_pvalues": 1.117, "tr_5289_adjusted_pvalues_str": "1.117",
                       "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -2.66e-15,
                       "tr_5289_estimates_str": "-2.66e-15", "tr_5289_log_adjusted_pvalues": 0.04798,
                       "tr_5289_log_adjusted_pvalues_str": "0.04798", "tr_5289_pvalues": 0.001936,
                       "tr_5289_pvalues_str": "0.001936", "tr_5760_adjusted_pvalues": 0.002375,
                       "tr_5760_adjusted_pvalues_str": "0.002375", "tr_5760_aic": -236700,
                       "tr_5760_aic_str": "-236700.0", "tr_5760_estimates": 2.507e-14,
                       "tr_5760_estimates_str": "2.507e-14", "tr_5760_log_adjusted_pvalues": 2.624,
                       "tr_5760_log_adjusted_pvalues_str": "2.624", "tr_5760_pvalues": 0.000004117,
                       "tr_5760_pvalues_str": "4.117e-06"},
                "100": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0105",
                        "cpd_name": "LPC(20:3/0:0)_2", "harmonised_annotation_id": "100",
                        "tr_5289_adjusted_pvalues": 0.2342, "tr_5289_adjusted_pvalues_str": "0.2342",
                        "tr_5289_aic": -175200, "tr_5289_aic_str": "-175200.0", "tr_5289_estimates": 3.145e-14,
                        "tr_5289_estimates_str": "3.145e-14", "tr_5289_log_adjusted_pvalues": 0.6304,
                        "tr_5289_log_adjusted_pvalues_str": "0.6304", "tr_5289_pvalues": 0.0004059,
                        "tr_5289_pvalues_str": "0.0004059", "tr_5760_adjusted_pvalues": 0.1888,
                        "tr_5760_adjusted_pvalues_str": "0.1888", "tr_5760_aic": -243600,
                        "tr_5760_aic_str": "-243600.0", "tr_5760_estimates": 8.204e-15,
                        "tr_5760_estimates_str": "8.204e-15", "tr_5760_log_adjusted_pvalues": 0.7239,
                        "tr_5760_log_adjusted_pvalues_str": "0.7239", "tr_5760_pvalues": 0.0003273,
                        "tr_5760_pvalues_str": "0.0003273"},
                "101": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0109", "cpd_name": "LPC(22:4/0:0)",
                        "harmonised_annotation_id": "101", "tr_5289_adjusted_pvalues": 49.8,
                        "tr_5289_adjusted_pvalues_str": "49.8", "tr_5289_aic": -183300, "tr_5289_aic_str": "-183300.0",
                        "tr_5289_estimates": 3.931e-15, "tr_5289_estimates_str": "3.931e-15",
                        "tr_5289_log_adjusted_pvalues": -1.697, "tr_5289_log_adjusted_pvalues_str": "-1.697",
                        "tr_5289_pvalues": 0.08631, "tr_5289_pvalues_str": "0.08631", "tr_5760_adjusted_pvalues": 24.85,
                        "tr_5760_adjusted_pvalues_str": "24.85", "tr_5760_aic": -238200, "tr_5760_aic_str": "-238200.0",
                        "tr_5760_estimates": -9.361e-15, "tr_5760_estimates_str": "-9.361e-15",
                        "tr_5760_log_adjusted_pvalues": 1.395, "tr_5760_log_adjusted_pvalues_str": "1.395",
                        "tr_5760_pvalues": 0.04306, "tr_5760_pvalues_str": "0.04306"},
                "106": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0324", "cpd_name": "TG(54:5)",
                        "harmonised_annotation_id": "106", "tr_5289_adjusted_pvalues": 252.3,
                        "tr_5289_adjusted_pvalues_str": "252.3", "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0",
                        "tr_5289_estimates": 1.249e-15, "tr_5289_estimates_str": "1.249e-15",
                        "tr_5289_log_adjusted_pvalues": -2.402, "tr_5289_log_adjusted_pvalues_str": "-2.402",
                        "tr_5289_pvalues": 0.4373, "tr_5289_pvalues_str": "0.4373", "tr_5760_adjusted_pvalues": 187.4,
                        "tr_5760_adjusted_pvalues_str": "187.4", "tr_5760_aic": -249200, "tr_5760_aic_str": "-249200.0",
                        "tr_5760_estimates": -1.158e-15, "tr_5760_estimates_str": "-1.158e-15",
                        "tr_5760_log_adjusted_pvalues": 2.273, "tr_5760_log_adjusted_pvalues_str": "2.273",
                        "tr_5760_pvalues": 0.3248, "tr_5760_pvalues_str": "0.3248"},
                "111": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0127", "cpd_name": "PC(14:0/20:4)",
                        "harmonised_annotation_id": "111", "tr_5289_adjusted_pvalues": 0.0001089,
                        "tr_5289_adjusted_pvalues_str": "0.0001089", "tr_5289_aic": -180000,
                        "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": 2.001e-14,
                        "tr_5289_estimates_str": "2.001e-14", "tr_5289_log_adjusted_pvalues": 3.963,
                        "tr_5289_log_adjusted_pvalues_str": "3.963", "tr_5289_pvalues": 1.887e-7,
                        "tr_5289_pvalues_str": "1.887e-07", "tr_5760_adjusted_pvalues": 0.0007889,
                        "tr_5760_adjusted_pvalues_str": "0.0007889", "tr_5760_aic": -248000,
                        "tr_5760_aic_str": "-248000.0", "tr_5760_estimates": -6.255e-15,
                        "tr_5760_estimates_str": "-6.255e-15", "tr_5760_log_adjusted_pvalues": -3.103,
                        "tr_5760_log_adjusted_pvalues_str": "-3.103", "tr_5760_pvalues": 0.000001367,
                        "tr_5760_pvalues_str": "1.367e-06"},
                "117": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0021", "cpd_name": "CAR(18:1)",
                        "harmonised_annotation_id": "117", "tr_5289_adjusted_pvalues": 10.48,
                        "tr_5289_adjusted_pvalues_str": "10.48", "tr_5289_aic": -175800, "tr_5289_aic_str": "-175800.0",
                        "tr_5289_estimates": -1.909e-14, "tr_5289_estimates_str": "-1.909e-14",
                        "tr_5289_log_adjusted_pvalues": 1.02, "tr_5289_log_adjusted_pvalues_str": "1.02",
                        "tr_5289_pvalues": 0.01816, "tr_5289_pvalues_str": "0.01816",
                        "tr_5760_adjusted_pvalues": 0.1137, "tr_5760_adjusted_pvalues_str": "0.1137",
                        "tr_5760_aic": -242700, "tr_5760_aic_str": "-242700.0", "tr_5760_estimates": -9.766e-15,
                        "tr_5760_estimates_str": "-9.766e-15", "tr_5760_log_adjusted_pvalues": -0.9441,
                        "tr_5760_log_adjusted_pvalues_str": "-0.9441", "tr_5760_pvalues": 0.0001971,
                        "tr_5760_pvalues_str": "0.0001971"},
                "118": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0312", "cpd_name": "TG(52:5)_1",
                        "harmonised_annotation_id": "118", "tr_5289_adjusted_pvalues": 0.1758,
                        "tr_5289_adjusted_pvalues_str": "0.1758", "tr_5289_aic": -174700,
                        "tr_5289_aic_str": "-174700.0", "tr_5289_estimates": 3.572e-14,
                        "tr_5289_estimates_str": "3.572e-14", "tr_5289_log_adjusted_pvalues": 0.7551,
                        "tr_5289_log_adjusted_pvalues_str": "0.7551", "tr_5289_pvalues": 0.0003046,
                        "tr_5289_pvalues_str": "0.0003046", "tr_5760_adjusted_pvalues": 0.0373,
                        "tr_5760_adjusted_pvalues_str": "0.0373", "tr_5760_aic": -238900,
                        "tr_5760_aic_str": "-238900.0", "tr_5760_estimates": -1.716e-14,
                        "tr_5760_estimates_str": "-1.716e-14", "tr_5760_log_adjusted_pvalues": -1.428,
                        "tr_5760_log_adjusted_pvalues_str": "-1.428", "tr_5760_pvalues": 0.00006465,
                        "tr_5760_pvalues_str": "6.465e-05"},
                "119": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0079", "cpd_name": "LPC(0:0/16:1)",
                        "harmonised_annotation_id": "119", "tr_5289_adjusted_pvalues": 0.000001668,
                        "tr_5289_adjusted_pvalues_str": "1.668e-06", "tr_5289_aic": -183600,
                        "tr_5289_aic_str": "-183600.0", "tr_5289_estimates": 1.296e-14,
                        "tr_5289_estimates_str": "1.296e-14", "tr_5289_log_adjusted_pvalues": 5.778,
                        "tr_5289_log_adjusted_pvalues_str": "5.778", "tr_5289_pvalues": 2.89e-9,
                        "tr_5289_pvalues_str": "2.89e-09", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "121": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0364", "cpd_name": "TG(60:4)_1",
                        "harmonised_annotation_id": "121", "tr_5289_adjusted_pvalues": 0.005886,
                        "tr_5289_adjusted_pvalues_str": "0.005886", "tr_5289_aic": -176000,
                        "tr_5289_aic_str": "-176000.0", "tr_5289_estimates": 3.899e-14,
                        "tr_5289_estimates_str": "3.899e-14", "tr_5289_log_adjusted_pvalues": 2.23,
                        "tr_5289_log_adjusted_pvalues_str": "2.23", "tr_5289_pvalues": 0.0000102,
                        "tr_5289_pvalues_str": "1.02e-05", "tr_5760_adjusted_pvalues": 0.006871,
                        "tr_5760_adjusted_pvalues_str": "0.006871", "tr_5760_aic": -242700,
                        "tr_5760_aic_str": "-242700.0", "tr_5760_estimates": -1.263e-14,
                        "tr_5760_estimates_str": "-1.263e-14", "tr_5760_log_adjusted_pvalues": -2.163,
                        "tr_5760_log_adjusted_pvalues_str": "-2.163", "tr_5760_pvalues": 0.00001191,
                        "tr_5760_pvalues_str": "1.191e-05"},
                "124": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0043",
                        "cpd_name": "Cer(d18:1/20:0)", "harmonised_annotation_id": "124",
                        "tr_5289_adjusted_pvalues": 0.000001268, "tr_5289_adjusted_pvalues_str": "1.268e-06",
                        "tr_5289_aic": -188100, "tr_5289_aic_str": "-188100.0", "tr_5289_estimates": 6.083e-15,
                        "tr_5289_estimates_str": "6.083e-15", "tr_5289_log_adjusted_pvalues": 5.897,
                        "tr_5289_log_adjusted_pvalues_str": "5.897", "tr_5289_pvalues": 2.198e-9,
                        "tr_5289_pvalues_str": "2.198e-09", "tr_5760_adjusted_pvalues": 6.887e-28,
                        "tr_5760_adjusted_pvalues_str": "6.887e-28", "tr_5760_aic": -239800,
                        "tr_5760_aic_str": "-239800.0", "tr_5760_estimates": -4.345e-14,
                        "tr_5760_estimates_str": "-4.345e-14", "tr_5760_log_adjusted_pvalues": -27.16,
                        "tr_5760_log_adjusted_pvalues_str": "-27.16", "tr_5760_pvalues": 1.194e-30,
                        "tr_5760_pvalues_str": "1.194e-30"},
                "128": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0012", "cpd_name": "CAR(14:0)",
                        "harmonised_annotation_id": "128", "tr_5289_adjusted_pvalues": 1.521e-15,
                        "tr_5289_adjusted_pvalues_str": "1.521e-15", "tr_5289_aic": -182300,
                        "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": 2.41e-14,
                        "tr_5289_estimates_str": "2.41e-14", "tr_5289_log_adjusted_pvalues": 14.82,
                        "tr_5289_log_adjusted_pvalues_str": "14.82", "tr_5289_pvalues": 2.636e-18,
                        "tr_5289_pvalues_str": "2.636e-18", "tr_5760_adjusted_pvalues": 9.075e-23,
                        "tr_5760_adjusted_pvalues_str": "9.075e-23", "tr_5760_aic": -245900,
                        "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": 1.917e-14,
                        "tr_5760_estimates_str": "1.917e-14", "tr_5760_log_adjusted_pvalues": 22.04,
                        "tr_5760_log_adjusted_pvalues_str": "22.04", "tr_5760_pvalues": 1.573e-25,
                        "tr_5760_pvalues_str": "1.573e-25"},
                "137": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0267",
                        "cpd_name": "PC(O-16:0/15:0)", "harmonised_annotation_id": "137",
                        "tr_5289_adjusted_pvalues": 150.9, "tr_5289_adjusted_pvalues_str": "150.9",
                        "tr_5289_aic": -183600, "tr_5289_aic_str": "-183600.0", "tr_5289_estimates": -2.448e-15,
                        "tr_5289_estimates_str": "-2.448e-15", "tr_5289_log_adjusted_pvalues": 2.179,
                        "tr_5289_log_adjusted_pvalues_str": "2.179", "tr_5289_pvalues": 0.2616,
                        "tr_5289_pvalues_str": "0.2616", "tr_5760_adjusted_pvalues": 339.3,
                        "tr_5760_adjusted_pvalues_str": "339.3", "tr_5760_aic": -234600, "tr_5760_aic_str": "-234600.0",
                        "tr_5760_estimates": -3.921e-15, "tr_5760_estimates_str": "-3.921e-15",
                        "tr_5760_log_adjusted_pvalues": 2.531, "tr_5760_log_adjusted_pvalues_str": "2.531",
                        "tr_5760_pvalues": 0.588, "tr_5760_pvalues_str": "0.588"},
                "138": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0286",
                        "cpd_name": "PC(O-24:2/20:4) and/or PC(P-24:1/20:4)", "harmonised_annotation_id": "138",
                        "tr_5289_adjusted_pvalues": 2.01e-12, "tr_5289_adjusted_pvalues_str": "2.01e-12",
                        "tr_5289_aic": -183700, "tr_5289_aic_str": "-183700.0", "tr_5289_estimates": 1.724e-14,
                        "tr_5289_estimates_str": "1.724e-14", "tr_5289_log_adjusted_pvalues": 11.7,
                        "tr_5289_log_adjusted_pvalues_str": "11.7", "tr_5289_pvalues": 3.483e-15,
                        "tr_5289_pvalues_str": "3.483e-15", "tr_5760_adjusted_pvalues": 7.753e-17,
                        "tr_5760_adjusted_pvalues_str": "7.753e-17", "tr_5760_aic": -240300,
                        "tr_5760_aic_str": "-240300.0", "tr_5760_estimates": -3.299e-14,
                        "tr_5760_estimates_str": "-3.299e-14", "tr_5760_log_adjusted_pvalues": -16.11,
                        "tr_5760_log_adjusted_pvalues_str": "-16.11", "tr_5760_pvalues": 1.344e-19,
                        "tr_5760_pvalues_str": "1.344e-19"},
                "145": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0377",
                        "cpd_name": "LacCer(d18:1/24:0)", "harmonised_annotation_id": "145",
                        "tr_5289_adjusted_pvalues": 155.6, "tr_5289_adjusted_pvalues_str": "155.6",
                        "tr_5289_aic": -177800, "tr_5289_aic_str": "-177800.0", "tr_5289_estimates": 5.747e-15,
                        "tr_5289_estimates_str": "5.747e-15", "tr_5289_log_adjusted_pvalues": -2.192,
                        "tr_5289_log_adjusted_pvalues_str": "-2.192", "tr_5289_pvalues": 0.2697,
                        "tr_5289_pvalues_str": "0.2697", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "155": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0292",
                        "cpd_name": "SM(d19:1/24:1)", "harmonised_annotation_id": "155",
                        "tr_5289_adjusted_pvalues": 8.485e-7, "tr_5289_adjusted_pvalues_str": "8.485e-07",
                        "tr_5289_aic": -180500, "tr_5289_aic_str": "-180500.0", "tr_5289_estimates": 2.13e-14,
                        "tr_5289_estimates_str": "2.13e-14", "tr_5289_log_adjusted_pvalues": 6.071,
                        "tr_5289_log_adjusted_pvalues_str": "6.071", "tr_5289_pvalues": 1.471e-9,
                        "tr_5289_pvalues_str": "1.471e-09", "tr_5760_adjusted_pvalues": 3.562e-10,
                        "tr_5760_adjusted_pvalues_str": "3.562e-10", "tr_5760_aic": -242800,
                        "tr_5760_aic_str": "-242800.0", "tr_5760_estimates": -1.773e-14,
                        "tr_5760_estimates_str": "-1.773e-14", "tr_5760_log_adjusted_pvalues": -9.448,
                        "tr_5760_log_adjusted_pvalues_str": "-9.448", "tr_5760_pvalues": 6.173e-13,
                        "tr_5760_pvalues_str": "6.173e-13"},
                "158": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0273",
                        "cpd_name": "PC(O-18:1/22:6) and/or PC(P-18:0/22:6)", "harmonised_annotation_id": "158",
                        "tr_5289_adjusted_pvalues": 0.00009501, "tr_5289_adjusted_pvalues_str": "9.501e-05",
                        "tr_5289_aic": -178200, "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": -2.801e-14,
                        "tr_5289_estimates_str": "-2.801e-14", "tr_5289_log_adjusted_pvalues": -4.022,
                        "tr_5289_log_adjusted_pvalues_str": "-4.022", "tr_5289_pvalues": 1.647e-7,
                        "tr_5289_pvalues_str": "1.647e-07", "tr_5760_adjusted_pvalues": 2.394e-7,
                        "tr_5760_adjusted_pvalues_str": "2.394e-07", "tr_5760_aic": -236700,
                        "tr_5760_aic_str": "-236700.0", "tr_5760_estimates": -3.42e-14,
                        "tr_5760_estimates_str": "-3.42e-14", "tr_5760_log_adjusted_pvalues": -6.621,
                        "tr_5760_log_adjusted_pvalues_str": "-6.621", "tr_5760_pvalues": 4.15e-10,
                        "tr_5760_pvalues_str": "4.15e-10"},
                "159": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0210", "cpd_name": "TG(48:4)",
                        "harmonised_annotation_id": "159", "tr_5289_adjusted_pvalues": 1.865,
                        "tr_5289_adjusted_pvalues_str": "1.865", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                        "tr_5289_estimates": 2.809e-15, "tr_5289_estimates_str": "2.809e-15",
                        "tr_5289_log_adjusted_pvalues": -0.2707, "tr_5289_log_adjusted_pvalues_str": "-0.2707",
                        "tr_5289_pvalues": 0.003232, "tr_5289_pvalues_str": "0.003232",
                        "tr_5760_adjusted_pvalues": 0.0004801, "tr_5760_adjusted_pvalues_str": "0.0004801",
                        "tr_5760_aic": -237500, "tr_5760_aic_str": "-237500.0", "tr_5760_estimates": -2.654e-14,
                        "tr_5760_estimates_str": "-2.654e-14", "tr_5760_log_adjusted_pvalues": -3.319,
                        "tr_5760_log_adjusted_pvalues_str": "-3.319", "tr_5760_pvalues": 8.321e-7,
                        "tr_5760_pvalues_str": "8.321e-07"},
                "161": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0077", "cpd_name": "LPC(0:0/15:0)",
                        "harmonised_annotation_id": "161", "tr_5289_adjusted_pvalues": 3.614,
                        "tr_5289_adjusted_pvalues_str": "3.614", "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0",
                        "tr_5289_estimates": -8.509e-15, "tr_5289_estimates_str": "-8.509e-15",
                        "tr_5289_log_adjusted_pvalues": 0.558, "tr_5289_log_adjusted_pvalues_str": "0.558",
                        "tr_5289_pvalues": 0.006264, "tr_5289_pvalues_str": "0.006264",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "162": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0369",
                        "cpd_name": "Anhydrolutein I", "harmonised_annotation_id": "162",
                        "tr_5289_adjusted_pvalues": 0.005042, "tr_5289_adjusted_pvalues_str": "0.005042",
                        "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": -7.937e-15,
                        "tr_5289_estimates_str": "-7.937e-15", "tr_5289_log_adjusted_pvalues": -2.297,
                        "tr_5289_log_adjusted_pvalues_str": "-2.297", "tr_5289_pvalues": 0.000008739,
                        "tr_5289_pvalues_str": "8.739e-06", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "172": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0158",
                        "cpd_name": "PC(32:1); PC(14:0/18:1) AND PC(16:0/16:1)", "harmonised_annotation_id": "172",
                        "tr_5289_adjusted_pvalues": 0.01838, "tr_5289_adjusted_pvalues_str": "0.01838",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": 3.667e-15,
                        "tr_5289_estimates_str": "3.667e-15", "tr_5289_log_adjusted_pvalues": 1.736,
                        "tr_5289_log_adjusted_pvalues_str": "1.736", "tr_5289_pvalues": 0.00003185,
                        "tr_5289_pvalues_str": "3.185e-05", "tr_5760_adjusted_pvalues": 1.836e-13,
                        "tr_5760_adjusted_pvalues_str": "1.836e-13", "tr_5760_aic": -233200,
                        "tr_5760_aic_str": "-233200.0", "tr_5760_estimates": -7.084e-14,
                        "tr_5760_estimates_str": "-7.084e-14", "tr_5760_log_adjusted_pvalues": -12.74,
                        "tr_5760_log_adjusted_pvalues_str": "-12.74", "tr_5760_pvalues": 3.183e-16,
                        "tr_5760_pvalues_str": "3.183e-16"},
                "173": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0014", "cpd_name": "CAR(14:1)",
                        "harmonised_annotation_id": "173", "tr_5289_adjusted_pvalues": 396.3,
                        "tr_5289_adjusted_pvalues_str": "396.3", "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0",
                        "tr_5289_estimates": -1.623e-15, "tr_5289_estimates_str": "-1.623e-15",
                        "tr_5289_log_adjusted_pvalues": 2.598, "tr_5289_log_adjusted_pvalues_str": "2.598",
                        "tr_5289_pvalues": 0.6869, "tr_5289_pvalues_str": "0.6869", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "174": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0040",
                        "cpd_name": "Cer(d16:1/24:1)", "harmonised_annotation_id": "174",
                        "tr_5289_adjusted_pvalues": 5.275e-22, "tr_5289_adjusted_pvalues_str": "5.275e-22",
                        "tr_5289_aic": -179800, "tr_5289_aic_str": "-179800.0", "tr_5289_estimates": 4.282e-14,
                        "tr_5289_estimates_str": "4.282e-14", "tr_5289_log_adjusted_pvalues": 21.28,
                        "tr_5289_log_adjusted_pvalues_str": "21.28", "tr_5289_pvalues": 9.143e-25,
                        "tr_5289_pvalues_str": "9.143e-25", "tr_5760_adjusted_pvalues": 1.051e-29,
                        "tr_5760_adjusted_pvalues_str": "1.051e-29", "tr_5760_aic": -247900,
                        "tr_5760_aic_str": "-247900.0", "tr_5760_estimates": 1.606e-14,
                        "tr_5760_estimates_str": "1.606e-14", "tr_5760_log_adjusted_pvalues": 28.98,
                        "tr_5760_log_adjusted_pvalues_str": "28.98", "tr_5760_pvalues": 1.822e-32,
                        "tr_5760_pvalues_str": "1.822e-32"},
                "175": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0265", "cpd_name": "PC(40:3)",
                        "harmonised_annotation_id": "175", "tr_5289_adjusted_pvalues": 456.4,
                        "tr_5289_adjusted_pvalues_str": "456.4", "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0",
                        "tr_5289_estimates": -4.279e-16, "tr_5289_estimates_str": "-4.279e-16",
                        "tr_5289_log_adjusted_pvalues": 2.659, "tr_5289_log_adjusted_pvalues_str": "2.659",
                        "tr_5289_pvalues": 0.7911, "tr_5289_pvalues_str": "0.7911", "tr_5760_adjusted_pvalues": 141.6,
                        "tr_5760_adjusted_pvalues_str": "141.6", "tr_5760_aic": -248000, "tr_5760_aic_str": "-248000.0",
                        "tr_5760_estimates": -1.481e-15, "tr_5760_estimates_str": "-1.481e-15",
                        "tr_5760_log_adjusted_pvalues": 2.151, "tr_5760_log_adjusted_pvalues_str": "2.151",
                        "tr_5760_pvalues": 0.2455, "tr_5760_pvalues_str": "0.2455"},
                "178": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0025", "cpd_name": "CAR(20:1)",
                        "harmonised_annotation_id": "178", "tr_5289_adjusted_pvalues": 2.235e-10,
                        "tr_5289_adjusted_pvalues_str": "2.235e-10", "tr_5289_aic": -180000,
                        "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": -2.869e-14,
                        "tr_5289_estimates_str": "-2.869e-14", "tr_5289_log_adjusted_pvalues": -9.651,
                        "tr_5289_log_adjusted_pvalues_str": "-9.651", "tr_5289_pvalues": 3.874e-13,
                        "tr_5289_pvalues_str": "3.874e-13", "tr_5760_adjusted_pvalues": 1.434e-17,
                        "tr_5760_adjusted_pvalues_str": "1.434e-17", "tr_5760_aic": -237600,
                        "tr_5760_aic_str": "-237600.0", "tr_5760_estimates": 4.601e-14,
                        "tr_5760_estimates_str": "4.601e-14", "tr_5760_log_adjusted_pvalues": 16.84,
                        "tr_5760_log_adjusted_pvalues_str": "16.84", "tr_5760_pvalues": 2.486e-20,
                        "tr_5760_pvalues_str": "2.486e-20"},
                "181": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0203", "cpd_name": "TG(46:0)",
                        "harmonised_annotation_id": "181", "tr_5289_adjusted_pvalues": 4.907e-12,
                        "tr_5289_adjusted_pvalues_str": "4.907e-12", "tr_5289_aic": -180500,
                        "tr_5289_aic_str": "-180500.0", "tr_5289_estimates": 2.898e-14,
                        "tr_5289_estimates_str": "2.898e-14", "tr_5289_log_adjusted_pvalues": 11.31,
                        "tr_5289_log_adjusted_pvalues_str": "11.31", "tr_5289_pvalues": 8.505e-15,
                        "tr_5289_pvalues_str": "8.505e-15", "tr_5760_adjusted_pvalues": 1.144e-10,
                        "tr_5760_adjusted_pvalues_str": "1.144e-10", "tr_5760_aic": -247900,
                        "tr_5760_aic_str": "-247900.0", "tr_5760_estimates": 1.003e-14,
                        "tr_5760_estimates_str": "1.003e-14", "tr_5760_log_adjusted_pvalues": 9.941,
                        "tr_5760_log_adjusted_pvalues_str": "9.941", "tr_5760_pvalues": 1.983e-13,
                        "tr_5760_pvalues_str": "1.983e-13"},
                "185": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0069",
                        "cpd_name": "HexCer(d18:1/20:0)", "harmonised_annotation_id": "185",
                        "tr_5289_adjusted_pvalues": 236.1, "tr_5289_adjusted_pvalues_str": "236.1",
                        "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0", "tr_5289_estimates": 1.26e-15,
                        "tr_5289_estimates_str": "1.26e-15", "tr_5289_log_adjusted_pvalues": -2.373,
                        "tr_5289_log_adjusted_pvalues_str": "-2.373", "tr_5289_pvalues": 0.4093,
                        "tr_5289_pvalues_str": "0.4093", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "186": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0251",
                        "cpd_name": "LPC(O-24:1/0:0)", "harmonised_annotation_id": "186",
                        "tr_5289_adjusted_pvalues": 10.98, "tr_5289_adjusted_pvalues_str": "10.98",
                        "tr_5289_aic": -180800, "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": 7.845e-15,
                        "tr_5289_estimates_str": "7.845e-15", "tr_5289_log_adjusted_pvalues": -1.041,
                        "tr_5289_log_adjusted_pvalues_str": "-1.041", "tr_5289_pvalues": 0.01903,
                        "tr_5289_pvalues_str": "0.01903", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "188": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0022", "cpd_name": "CAR(18:1-DC)",
                        "harmonised_annotation_id": "188", "tr_5289_adjusted_pvalues": 36.45,
                        "tr_5289_adjusted_pvalues_str": "36.45", "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0",
                        "tr_5289_estimates": 2.821e-15, "tr_5289_estimates_str": "2.821e-15",
                        "tr_5289_log_adjusted_pvalues": -1.562, "tr_5289_log_adjusted_pvalues_str": "-1.562",
                        "tr_5289_pvalues": 0.06317, "tr_5289_pvalues_str": "0.06317", "tr_5760_adjusted_pvalues": 3.393,
                        "tr_5760_adjusted_pvalues_str": "3.393", "tr_5760_aic": -235700, "tr_5760_aic_str": "-235700.0",
                        "tr_5760_estimates": -1.718e-14, "tr_5760_estimates_str": "-1.718e-14",
                        "tr_5760_log_adjusted_pvalues": 0.5306, "tr_5760_log_adjusted_pvalues_str": "0.5306",
                        "tr_5760_pvalues": 0.005881, "tr_5760_pvalues_str": "0.005881"},
                "189": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0063",
                        "cpd_name": "DG(36:2); DG(18:1/18:1) | DG(18:0/18:2)", "harmonised_annotation_id": "189",
                        "tr_5289_adjusted_pvalues": 0.003787, "tr_5289_adjusted_pvalues_str": "0.003787",
                        "tr_5289_aic": -180800, "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -1.713e-14,
                        "tr_5289_estimates_str": "-1.713e-14", "tr_5289_log_adjusted_pvalues": -2.422,
                        "tr_5289_log_adjusted_pvalues_str": "-2.422", "tr_5289_pvalues": 0.000006563,
                        "tr_5289_pvalues_str": "6.563e-06", "tr_5760_adjusted_pvalues": 0.1921,
                        "tr_5760_adjusted_pvalues_str": "0.1921", "tr_5760_aic": -249200,
                        "tr_5760_aic_str": "-249200.0", "tr_5760_estimates": -4.519e-15,
                        "tr_5760_estimates_str": "-4.519e-15", "tr_5760_log_adjusted_pvalues": -0.7164,
                        "tr_5760_log_adjusted_pvalues_str": "-0.7164", "tr_5760_pvalues": 0.000333,
                        "tr_5760_pvalues_str": "0.000333"},
                "191": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0208", "cpd_name": "TG(48:2)",
                        "harmonised_annotation_id": "191", "tr_5289_adjusted_pvalues": 6.666e-12,
                        "tr_5289_adjusted_pvalues_str": "6.666e-12", "tr_5289_aic": -181300,
                        "tr_5289_aic_str": "-181300.0", "tr_5289_estimates": 2.564e-14,
                        "tr_5289_estimates_str": "2.564e-14", "tr_5289_log_adjusted_pvalues": 11.18,
                        "tr_5289_log_adjusted_pvalues_str": "11.18", "tr_5289_pvalues": 1.155e-14,
                        "tr_5289_pvalues_str": "1.155e-14", "tr_5760_adjusted_pvalues": 3.559e-14,
                        "tr_5760_adjusted_pvalues_str": "3.559e-14", "tr_5760_aic": -238600,
                        "tr_5760_aic_str": "-238600.0", "tr_5760_estimates": 3.791e-14,
                        "tr_5760_estimates_str": "3.791e-14", "tr_5760_log_adjusted_pvalues": 13.45,
                        "tr_5760_log_adjusted_pvalues_str": "13.45", "tr_5760_pvalues": 6.168e-17,
                        "tr_5760_pvalues_str": "6.168e-17"},
                "192": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0378",
                        "cpd_name": "LacCer(d18:1/24:1)", "harmonised_annotation_id": "192",
                        "tr_5289_adjusted_pvalues": 2.051e-8, "tr_5289_adjusted_pvalues_str": "2.051e-08",
                        "tr_5289_aic": -188100, "tr_5289_aic_str": "-188100.0", "tr_5289_estimates": -6.618e-15,
                        "tr_5289_estimates_str": "-6.618e-15", "tr_5289_log_adjusted_pvalues": -7.688,
                        "tr_5289_log_adjusted_pvalues_str": "-7.688", "tr_5289_pvalues": 3.555e-11,
                        "tr_5289_pvalues_str": "3.555e-11", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "193": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0216", "cpd_name": "TG(50:4)",
                        "harmonised_annotation_id": "193", "tr_5289_adjusted_pvalues": 3.57e-7,
                        "tr_5289_adjusted_pvalues_str": "3.57e-07", "tr_5289_aic": -185100,
                        "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": -1.086e-14,
                        "tr_5289_estimates_str": "-1.086e-14", "tr_5289_log_adjusted_pvalues": -6.447,
                        "tr_5289_log_adjusted_pvalues_str": "-6.447", "tr_5289_pvalues": 6.187e-10,
                        "tr_5289_pvalues_str": "6.187e-10", "tr_5760_adjusted_pvalues": 5.698e-9,
                        "tr_5760_adjusted_pvalues_str": "5.698e-09", "tr_5760_aic": -229400,
                        "tr_5760_aic_str": "-229400.0", "tr_5760_estimates": 9.903e-14,
                        "tr_5760_estimates_str": "9.903e-14", "tr_5760_log_adjusted_pvalues": 8.244,
                        "tr_5760_log_adjusted_pvalues_str": "8.244", "tr_5760_pvalues": 9.875e-12,
                        "tr_5760_pvalues_str": "9.875e-12"},
                "194": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0047",
                        "cpd_name": "Cer(d18:1/25:0)", "harmonised_annotation_id": "194",
                        "tr_5289_adjusted_pvalues": 3.243e-10, "tr_5289_adjusted_pvalues_str": "3.243e-10",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -6.338e-15,
                        "tr_5289_estimates_str": "-6.338e-15", "tr_5289_log_adjusted_pvalues": -9.489,
                        "tr_5289_log_adjusted_pvalues_str": "-9.489", "tr_5289_pvalues": 5.621e-13,
                        "tr_5289_pvalues_str": "5.621e-13", "tr_5760_adjusted_pvalues": 3.019e-63,
                        "tr_5760_adjusted_pvalues_str": "3.019e-63", "tr_5760_aic": -233800,
                        "tr_5760_aic_str": "-233800.0", "tr_5760_estimates": -1.382e-13,
                        "tr_5760_estimates_str": "-1.382e-13", "tr_5760_log_adjusted_pvalues": -62.52,
                        "tr_5760_log_adjusted_pvalues_str": "-62.52", "tr_5760_pvalues": 5.233e-66,
                        "tr_5760_pvalues_str": "5.233e-66"},
                "195": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0316", "cpd_name": "TG(52:6)_2",
                        "harmonised_annotation_id": "195", "tr_5289_adjusted_pvalues": 1.934e-9,
                        "tr_5289_adjusted_pvalues_str": "1.934e-09", "tr_5289_aic": -181500,
                        "tr_5289_aic_str": "-181500.0", "tr_5289_estimates": 2.254e-14,
                        "tr_5289_estimates_str": "2.254e-14", "tr_5289_log_adjusted_pvalues": 8.714,
                        "tr_5289_log_adjusted_pvalues_str": "8.714", "tr_5289_pvalues": 3.351e-12,
                        "tr_5289_pvalues_str": "3.351e-12", "tr_5760_adjusted_pvalues": 1.186e-10,
                        "tr_5760_adjusted_pvalues_str": "1.186e-10", "tr_5760_aic": -242800,
                        "tr_5760_aic_str": "-242800.0", "tr_5760_estimates": -1.976e-14,
                        "tr_5760_estimates_str": "-1.976e-14", "tr_5760_log_adjusted_pvalues": -9.926,
                        "tr_5760_log_adjusted_pvalues_str": "-9.926", "tr_5760_pvalues": 2.055e-13,
                        "tr_5760_pvalues_str": "2.055e-13"},
                "196": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0083", "cpd_name": "LPC(0:0/18:3)",
                        "harmonised_annotation_id": "196", "tr_5289_adjusted_pvalues": 34.08,
                        "tr_5289_adjusted_pvalues_str": "34.08", "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0",
                        "tr_5289_estimates": 5.866e-15, "tr_5289_estimates_str": "5.866e-15",
                        "tr_5289_log_adjusted_pvalues": -1.533, "tr_5289_log_adjusted_pvalues_str": "-1.533",
                        "tr_5289_pvalues": 0.05907, "tr_5289_pvalues_str": "0.05907", "tr_5760_adjusted_pvalues": 88.09,
                        "tr_5760_adjusted_pvalues_str": "88.09", "tr_5760_aic": -242600, "tr_5760_aic_str": "-242600.0",
                        "tr_5760_estimates": -3.74e-15, "tr_5760_estimates_str": "-3.74e-15",
                        "tr_5760_log_adjusted_pvalues": 1.945, "tr_5760_log_adjusted_pvalues_str": "1.945",
                        "tr_5760_pvalues": 0.1527, "tr_5760_pvalues_str": "0.1527"},
                "199": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0385", "cpd_name": "zeta-carotene",
                        "harmonised_annotation_id": "199", "tr_5289_adjusted_pvalues": 0.129,
                        "tr_5289_adjusted_pvalues_str": "0.129", "tr_5289_aic": -178200, "tr_5289_aic_str": "-178200.0",
                        "tr_5289_estimates": -1.96e-14, "tr_5289_estimates_str": "-1.96e-14",
                        "tr_5289_log_adjusted_pvalues": -0.8894, "tr_5289_log_adjusted_pvalues_str": "-0.8894",
                        "tr_5289_pvalues": 0.0002236, "tr_5289_pvalues_str": "0.0002236",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "201": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0061", "cpd_name": "DG(32:1)",
                        "harmonised_annotation_id": "201", "tr_5289_adjusted_pvalues": 7.21e-11,
                        "tr_5289_adjusted_pvalues_str": "7.21e-11", "tr_5289_aic": -177700,
                        "tr_5289_aic_str": "-177700.0", "tr_5289_estimates": -4.708e-14,
                        "tr_5289_estimates_str": "-4.708e-14", "tr_5289_log_adjusted_pvalues": -10.14,
                        "tr_5289_log_adjusted_pvalues_str": "-10.14", "tr_5289_pvalues": 1.25e-13,
                        "tr_5289_pvalues_str": "1.25e-13", "tr_5760_adjusted_pvalues": 7.31e-11,
                        "tr_5760_adjusted_pvalues_str": "7.31e-11", "tr_5760_aic": -241200,
                        "tr_5760_aic_str": "-241200.0", "tr_5760_estimates": 2.532e-14,
                        "tr_5760_estimates_str": "2.532e-14", "tr_5760_log_adjusted_pvalues": 10.14,
                        "tr_5760_log_adjusted_pvalues_str": "10.14", "tr_5760_pvalues": 1.267e-13,
                        "tr_5760_pvalues_str": "1.267e-13"},
                "202": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0367", "cpd_name": "TG(60:9)",
                        "harmonised_annotation_id": "202", "tr_5289_adjusted_pvalues": 0.007363,
                        "tr_5289_adjusted_pvalues_str": "0.007363", "tr_5289_aic": -184600,
                        "tr_5289_aic_str": "-184600.0", "tr_5289_estimates": 7.997e-15,
                        "tr_5289_estimates_str": "7.997e-15", "tr_5289_log_adjusted_pvalues": 2.133,
                        "tr_5289_log_adjusted_pvalues_str": "2.133", "tr_5289_pvalues": 0.00001276,
                        "tr_5289_pvalues_str": "1.276e-05", "tr_5760_adjusted_pvalues": 4.2e-7,
                        "tr_5760_adjusted_pvalues_str": "4.2e-07", "tr_5760_aic": -238100,
                        "tr_5760_aic_str": "-238100.0", "tr_5760_estimates": -2.862e-14,
                        "tr_5760_estimates_str": "-2.862e-14", "tr_5760_log_adjusted_pvalues": -6.377,
                        "tr_5760_log_adjusted_pvalues_str": "-6.377", "tr_5760_pvalues": 7.279e-10,
                        "tr_5760_pvalues_str": "7.279e-10"},
                "204": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0271",
                        "cpd_name": "PC(O-18:0/20:4)", "harmonised_annotation_id": "204",
                        "tr_5289_adjusted_pvalues": 6.565e-9, "tr_5289_adjusted_pvalues_str": "6.565e-09",
                        "tr_5289_aic": -179700, "tr_5289_aic_str": "-179700.0", "tr_5289_estimates": -2.73e-14,
                        "tr_5289_estimates_str": "-2.73e-14", "tr_5289_log_adjusted_pvalues": -8.183,
                        "tr_5289_log_adjusted_pvalues_str": "-8.183", "tr_5289_pvalues": 1.138e-11,
                        "tr_5289_pvalues_str": "1.138e-11", "tr_5760_adjusted_pvalues": 0.02973,
                        "tr_5760_adjusted_pvalues_str": "0.02973", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": -2.921e-15,
                        "tr_5760_estimates_str": "-2.921e-15", "tr_5760_log_adjusted_pvalues": -1.527,
                        "tr_5760_log_adjusted_pvalues_str": "-1.527", "tr_5760_pvalues": 0.00005152,
                        "tr_5760_pvalues_str": "5.152e-05"},
                "206": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0185",
                        "cpd_name": "SM(d18:1/22:0)", "harmonised_annotation_id": "206",
                        "tr_5289_adjusted_pvalues": 3.223e-9, "tr_5289_adjusted_pvalues_str": "3.223e-09",
                        "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": -1.127e-14,
                        "tr_5289_estimates_str": "-1.127e-14", "tr_5289_log_adjusted_pvalues": -8.492,
                        "tr_5289_log_adjusted_pvalues_str": "-8.492", "tr_5289_pvalues": 5.586e-12,
                        "tr_5289_pvalues_str": "5.586e-12", "tr_5760_adjusted_pvalues": 3.194e-13,
                        "tr_5760_adjusted_pvalues_str": "3.194e-13", "tr_5760_aic": -242800,
                        "tr_5760_aic_str": "-242800.0", "tr_5760_estimates": -1.995e-14,
                        "tr_5760_estimates_str": "-1.995e-14", "tr_5760_log_adjusted_pvalues": -12.5,
                        "tr_5760_log_adjusted_pvalues_str": "-12.5", "tr_5760_pvalues": 5.536e-16,
                        "tr_5760_pvalues_str": "5.536e-16"},
                "208": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0337", "cpd_name": "TG(56:3)",
                        "harmonised_annotation_id": "208", "tr_5289_adjusted_pvalues": 10.03,
                        "tr_5289_adjusted_pvalues_str": "10.03", "tr_5289_aic": -182500, "tr_5289_aic_str": "-182500.0",
                        "tr_5289_estimates": 6.568e-15, "tr_5289_estimates_str": "6.568e-15",
                        "tr_5289_log_adjusted_pvalues": -1.001, "tr_5289_log_adjusted_pvalues_str": "-1.001",
                        "tr_5289_pvalues": 0.01738, "tr_5289_pvalues_str": "0.01738", "tr_5760_adjusted_pvalues": 5.618,
                        "tr_5760_adjusted_pvalues_str": "5.618", "tr_5760_aic": -235900, "tr_5760_aic_str": "-235900.0",
                        "tr_5760_estimates": 1.704e-14, "tr_5760_estimates_str": "1.704e-14",
                        "tr_5760_log_adjusted_pvalues": -0.7496, "tr_5760_log_adjusted_pvalues_str": "-0.7496",
                        "tr_5760_pvalues": 0.009736, "tr_5760_pvalues_str": "0.009736"},
                "209": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0013", "cpd_name": "CAR(14:0-OH)",
                        "harmonised_annotation_id": "209", "tr_5289_adjusted_pvalues": 0.0009477,
                        "tr_5289_adjusted_pvalues_str": "0.0009477", "tr_5289_aic": -185700,
                        "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": 7.593e-15,
                        "tr_5289_estimates_str": "7.593e-15", "tr_5289_log_adjusted_pvalues": 3.023,
                        "tr_5289_log_adjusted_pvalues_str": "3.023", "tr_5289_pvalues": 0.000001642,
                        "tr_5289_pvalues_str": "1.642e-06", "tr_5760_adjusted_pvalues": 2.795e-15,
                        "tr_5760_adjusted_pvalues_str": "2.795e-15", "tr_5760_aic": -230200,
                        "tr_5760_aic_str": "-230200.0", "tr_5760_estimates": 1.127e-13,
                        "tr_5760_estimates_str": "1.127e-13", "tr_5760_log_adjusted_pvalues": 14.55,
                        "tr_5760_log_adjusted_pvalues_str": "14.55", "tr_5760_pvalues": 4.844e-18,
                        "tr_5760_pvalues_str": "4.844e-18"},
                "212": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0139",
                        "cpd_name": "PC(16:0/20:4)_3", "harmonised_annotation_id": "212",
                        "tr_5289_adjusted_pvalues": 6.814, "tr_5289_adjusted_pvalues_str": "6.814",
                        "tr_5289_aic": -176200, "tr_5289_aic_str": "-176200.0", "tr_5289_estimates": -1.797e-14,
                        "tr_5289_estimates_str": "-1.797e-14", "tr_5289_log_adjusted_pvalues": 0.8334,
                        "tr_5289_log_adjusted_pvalues_str": "0.8334", "tr_5289_pvalues": 0.01181,
                        "tr_5289_pvalues_str": "0.01181", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "213": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0036", "cpd_name": "CE(22:6)",
                        "harmonised_annotation_id": "213", "tr_5289_adjusted_pvalues": 65.72,
                        "tr_5289_adjusted_pvalues_str": "65.72", "tr_5289_aic": -177200, "tr_5289_aic_str": "-177200.0",
                        "tr_5289_estimates": -1.022e-14, "tr_5289_estimates_str": "-1.022e-14",
                        "tr_5289_log_adjusted_pvalues": 1.818, "tr_5289_log_adjusted_pvalues_str": "1.818",
                        "tr_5289_pvalues": 0.1139, "tr_5289_pvalues_str": "0.1139", "tr_5760_adjusted_pvalues": 0.01976,
                        "tr_5760_adjusted_pvalues_str": "0.01976", "tr_5760_aic": -241100,
                        "tr_5760_aic_str": "-241100.0", "tr_5760_estimates": 1.316e-14,
                        "tr_5760_estimates_str": "1.316e-14", "tr_5760_log_adjusted_pvalues": 1.704,
                        "tr_5760_log_adjusted_pvalues_str": "1.704", "tr_5760_pvalues": 0.00003424,
                        "tr_5760_pvalues_str": "3.424e-05"},
                "214": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0289",
                        "cpd_name": "PE(O-20:1/20:4) and/or PE(P-20:0/20:4)", "harmonised_annotation_id": "214",
                        "tr_5289_adjusted_pvalues": 0.001195, "tr_5289_adjusted_pvalues_str": "0.001195",
                        "tr_5289_aic": -175900, "tr_5289_aic_str": "-175900.0", "tr_5289_estimates": 3.828e-14,
                        "tr_5289_estimates_str": "3.828e-14", "tr_5289_log_adjusted_pvalues": 2.923,
                        "tr_5289_log_adjusted_pvalues_str": "2.923", "tr_5289_pvalues": 0.000002071,
                        "tr_5289_pvalues_str": "2.071e-06", "tr_5760_adjusted_pvalues": 0.0008236,
                        "tr_5760_adjusted_pvalues_str": "0.0008236", "tr_5760_aic": -233300,
                        "tr_5760_aic_str": "-233300.0", "tr_5760_estimates": 4.16e-14,
                        "tr_5760_estimates_str": "4.16e-14", "tr_5760_log_adjusted_pvalues": 3.084,
                        "tr_5760_log_adjusted_pvalues_str": "3.084", "tr_5760_pvalues": 0.000001427,
                        "tr_5760_pvalues_str": "1.427e-06"},
                "217": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0330", "cpd_name": "TG(54:8)_1",
                        "harmonised_annotation_id": "217", "tr_5289_adjusted_pvalues": 0.001808,
                        "tr_5289_adjusted_pvalues_str": "0.001808", "tr_5289_aic": -175800,
                        "tr_5289_aic_str": "-175800.0", "tr_5289_estimates": 3.841e-14,
                        "tr_5289_estimates_str": "3.841e-14", "tr_5289_log_adjusted_pvalues": 2.743,
                        "tr_5289_log_adjusted_pvalues_str": "2.743", "tr_5289_pvalues": 0.000003133,
                        "tr_5289_pvalues_str": "3.133e-06", "tr_5760_adjusted_pvalues": 1.174e-8,
                        "tr_5760_adjusted_pvalues_str": "1.174e-08", "tr_5760_aic": -236300,
                        "tr_5760_aic_str": "-236300.0", "tr_5760_estimates": -3.993e-14,
                        "tr_5760_estimates_str": "-3.993e-14", "tr_5760_log_adjusted_pvalues": -7.93,
                        "tr_5760_log_adjusted_pvalues_str": "-7.93", "tr_5760_pvalues": 2.035e-11,
                        "tr_5760_pvalues_str": "2.035e-11"},
                "218": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0179",
                        "cpd_name": "SM(d18:0/16:0)", "harmonised_annotation_id": "218",
                        "tr_5289_adjusted_pvalues": 1.279e-17, "tr_5289_adjusted_pvalues_str": "1.279e-17",
                        "tr_5289_aic": -180800, "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -3.135e-14,
                        "tr_5289_estimates_str": "-3.135e-14", "tr_5289_log_adjusted_pvalues": -16.89,
                        "tr_5289_log_adjusted_pvalues_str": "-16.89", "tr_5289_pvalues": 2.217e-20,
                        "tr_5289_pvalues_str": "2.217e-20", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "219": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0151", "cpd_name": "PC(18:0/22:5)",
                        "harmonised_annotation_id": "219", "tr_5289_adjusted_pvalues": 197.6,
                        "tr_5289_adjusted_pvalues_str": "197.6", "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0",
                        "tr_5289_estimates": -1.482e-15, "tr_5289_estimates_str": "-1.482e-15",
                        "tr_5289_log_adjusted_pvalues": 2.296, "tr_5289_log_adjusted_pvalues_str": "2.296",
                        "tr_5289_pvalues": 0.3424, "tr_5289_pvalues_str": "0.3424", "tr_5760_adjusted_pvalues": 61.08,
                        "tr_5760_adjusted_pvalues_str": "61.08", "tr_5760_aic": -230100, "tr_5760_aic_str": "-230100.0",
                        "tr_5760_estimates": -2.046e-14, "tr_5760_estimates_str": "-2.046e-14",
                        "tr_5760_log_adjusted_pvalues": 1.786, "tr_5760_log_adjusted_pvalues_str": "1.786",
                        "tr_5760_pvalues": 0.1059, "tr_5760_pvalues_str": "0.1059"},
                "224": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0189",
                        "cpd_name": "SM(d18:2/14:0)", "harmonised_annotation_id": "224",
                        "tr_5289_adjusted_pvalues": 1.449e-57, "tr_5289_adjusted_pvalues_str": "1.449e-57",
                        "tr_5289_aic": -181000, "tr_5289_aic_str": "-181000.0", "tr_5289_estimates": -6.513e-14,
                        "tr_5289_estimates_str": "-6.513e-14", "tr_5289_log_adjusted_pvalues": -56.84,
                        "tr_5289_log_adjusted_pvalues_str": "-56.84", "tr_5289_pvalues": 2.512e-60,
                        "tr_5289_pvalues_str": "2.512e-60", "tr_5760_adjusted_pvalues": 6.147e-65,
                        "tr_5760_adjusted_pvalues_str": "6.147e-65", "tr_5760_aic": -243100,
                        "tr_5760_aic_str": "-243100.0", "tr_5760_estimates": 5.09e-14,
                        "tr_5760_estimates_str": "5.09e-14", "tr_5760_log_adjusted_pvalues": 64.21,
                        "tr_5760_log_adjusted_pvalues_str": "64.21", "tr_5760_pvalues": 1.065e-67,
                        "tr_5760_pvalues_str": "1.065e-67"},
                "226": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0356", "cpd_name": "TG(58:6)",
                        "harmonised_annotation_id": "226", "tr_5289_adjusted_pvalues": 262.4,
                        "tr_5289_adjusted_pvalues_str": "262.4", "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0",
                        "tr_5289_estimates": -1.296e-15, "tr_5289_estimates_str": "-1.296e-15",
                        "tr_5289_log_adjusted_pvalues": 2.419, "tr_5289_log_adjusted_pvalues_str": "2.419",
                        "tr_5289_pvalues": 0.4548, "tr_5289_pvalues_str": "0.4548", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "227": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0107", "cpd_name": "LPC(20:5/0:0)",
                        "harmonised_annotation_id": "227", "tr_5289_adjusted_pvalues": 3.376e-28,
                        "tr_5289_adjusted_pvalues_str": "3.376e-28", "tr_5289_aic": -183800,
                        "tr_5289_aic_str": "-183800.0", "tr_5289_estimates": 2.573e-14,
                        "tr_5289_estimates_str": "2.573e-14", "tr_5289_log_adjusted_pvalues": 27.47,
                        "tr_5289_log_adjusted_pvalues_str": "27.47", "tr_5289_pvalues": 5.851e-31,
                        "tr_5289_pvalues_str": "5.851e-31", "tr_5760_adjusted_pvalues": 1.238e-40,
                        "tr_5760_adjusted_pvalues_str": "1.238e-40", "tr_5760_aic": -231900,
                        "tr_5760_aic_str": "-231900.0", "tr_5760_estimates": 1.462e-13,
                        "tr_5760_estimates_str": "1.462e-13", "tr_5760_log_adjusted_pvalues": 39.91,
                        "tr_5760_log_adjusted_pvalues_str": "39.91", "tr_5760_pvalues": 2.145e-43,
                        "tr_5760_pvalues_str": "2.145e-43"},
                "229": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0382",
                        "cpd_name": "PC(O-16:1/22:6) and/or PC(P-16:0/22:6)", "harmonised_annotation_id": "229",
                        "tr_5289_adjusted_pvalues": 9.579e-9, "tr_5289_adjusted_pvalues_str": "9.579e-09",
                        "tr_5289_aic": -188000, "tr_5289_aic_str": "-188000.0", "tr_5289_estimates": 6.833e-15,
                        "tr_5289_estimates_str": "6.833e-15", "tr_5289_log_adjusted_pvalues": 8.019,
                        "tr_5289_log_adjusted_pvalues_str": "8.019", "tr_5289_pvalues": 1.66e-11,
                        "tr_5289_pvalues_str": "1.66e-11", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "232": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0088", "cpd_name": "LPC(14:0/0:0)",
                        "harmonised_annotation_id": "232", "tr_5289_adjusted_pvalues": 0.2996,
                        "tr_5289_adjusted_pvalues_str": "0.2996", "tr_5289_aic": -184600,
                        "tr_5289_aic_str": "-184600.0", "tr_5289_estimates": 7.579e-15,
                        "tr_5289_estimates_str": "7.579e-15", "tr_5289_log_adjusted_pvalues": 0.5234,
                        "tr_5289_log_adjusted_pvalues_str": "0.5234", "tr_5289_pvalues": 0.0005193,
                        "tr_5289_pvalues_str": "0.0005193", "tr_5760_adjusted_pvalues": 0.06213,
                        "tr_5760_adjusted_pvalues_str": "0.06213", "tr_5760_aic": -238200,
                        "tr_5760_aic_str": "-238200.0", "tr_5760_estimates": -1.979e-14,
                        "tr_5760_estimates_str": "-1.979e-14", "tr_5760_log_adjusted_pvalues": -1.207,
                        "tr_5760_log_adjusted_pvalues_str": "-1.207", "tr_5760_pvalues": 0.0001077,
                        "tr_5760_pvalues_str": "0.0001077"},
                "236": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0217", "cpd_name": "TG(52:1)",
                        "harmonised_annotation_id": "236", "tr_5289_adjusted_pvalues": 9.483e-16,
                        "tr_5289_adjusted_pvalues_str": "9.483e-16", "tr_5289_aic": -177800,
                        "tr_5289_aic_str": "-177800.0", "tr_5289_estimates": -5.486e-14,
                        "tr_5289_estimates_str": "-5.486e-14", "tr_5289_log_adjusted_pvalues": -15.02,
                        "tr_5289_log_adjusted_pvalues_str": "-15.02", "tr_5289_pvalues": 1.644e-18,
                        "tr_5289_pvalues_str": "1.644e-18", "tr_5760_adjusted_pvalues": 3.958e-16,
                        "tr_5760_adjusted_pvalues_str": "3.958e-16", "tr_5760_aic": -236300,
                        "tr_5760_aic_str": "-236300.0", "tr_5760_estimates": 5.549e-14,
                        "tr_5760_estimates_str": "5.549e-14", "tr_5760_log_adjusted_pvalues": 15.4,
                        "tr_5760_log_adjusted_pvalues_str": "15.4", "tr_5760_pvalues": 6.859e-19,
                        "tr_5760_pvalues_str": "6.859e-19"},
                "237": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0176",
                        "cpd_name": "SM(d16:1/24:1)", "harmonised_annotation_id": "237",
                        "tr_5289_adjusted_pvalues": 7.82e-9, "tr_5289_adjusted_pvalues_str": "7.82e-09",
                        "tr_5289_aic": -175200, "tr_5289_aic_str": "-175200.0", "tr_5289_estimates": -5.894e-14,
                        "tr_5289_estimates_str": "-5.894e-14", "tr_5289_log_adjusted_pvalues": -8.107,
                        "tr_5289_log_adjusted_pvalues_str": "-8.107", "tr_5289_pvalues": 1.355e-11,
                        "tr_5289_pvalues_str": "1.355e-11", "tr_5760_adjusted_pvalues": 0.003818,
                        "tr_5760_adjusted_pvalues_str": "0.003818", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": -3.277e-15,
                        "tr_5760_estimates_str": "-3.277e-15", "tr_5760_log_adjusted_pvalues": -2.418,
                        "tr_5760_log_adjusted_pvalues_str": "-2.418", "tr_5760_pvalues": 0.000006617,
                        "tr_5760_pvalues_str": "6.617e-06"},
                "246": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0384", "cpd_name": "zeaxanthin",
                        "harmonised_annotation_id": "246", "tr_5289_adjusted_pvalues": 4.34,
                        "tr_5289_adjusted_pvalues_str": "4.34", "tr_5289_aic": -184700, "tr_5289_aic_str": "-184700.0",
                        "tr_5289_estimates": -4.845e-15, "tr_5289_estimates_str": "-4.845e-15",
                        "tr_5289_log_adjusted_pvalues": 0.6375, "tr_5289_log_adjusted_pvalues_str": "0.6375",
                        "tr_5289_pvalues": 0.007522, "tr_5289_pvalues_str": "0.007522",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "247": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0227", "cpd_name": "TG(54:6)_1",
                        "harmonised_annotation_id": "247", "tr_5289_adjusted_pvalues": 5.945,
                        "tr_5289_adjusted_pvalues_str": "5.945", "tr_5289_aic": -177800, "tr_5289_aic_str": "-177800.0",
                        "tr_5289_estimates": 1.511e-14, "tr_5289_estimates_str": "1.511e-14",
                        "tr_5289_log_adjusted_pvalues": -0.7741, "tr_5289_log_adjusted_pvalues_str": "-0.7741",
                        "tr_5289_pvalues": 0.0103, "tr_5289_pvalues_str": "0.0103", "tr_5760_adjusted_pvalues": 192.9,
                        "tr_5760_adjusted_pvalues_str": "192.9", "tr_5760_aic": -252500, "tr_5760_aic_str": "-252500.0",
                        "tr_5760_estimates": -7.489e-16, "tr_5760_estimates_str": "-7.489e-16",
                        "tr_5760_log_adjusted_pvalues": 2.285, "tr_5760_log_adjusted_pvalues_str": "2.285",
                        "tr_5760_pvalues": 0.3343, "tr_5760_pvalues_str": "0.3343"},
                "248": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0215", "cpd_name": "TG(50:3)",
                        "harmonised_annotation_id": "248", "tr_5289_adjusted_pvalues": 7.488e-11,
                        "tr_5289_adjusted_pvalues_str": "7.488e-11", "tr_5289_aic": -177400,
                        "tr_5289_aic_str": "-177400.0", "tr_5289_estimates": 4.745e-14,
                        "tr_5289_estimates_str": "4.745e-14", "tr_5289_log_adjusted_pvalues": 10.13,
                        "tr_5289_log_adjusted_pvalues_str": "10.13", "tr_5289_pvalues": 1.298e-13,
                        "tr_5289_pvalues_str": "1.298e-13", "tr_5760_adjusted_pvalues": 4.017e-11,
                        "tr_5760_adjusted_pvalues_str": "4.017e-11", "tr_5760_aic": -237500,
                        "tr_5760_aic_str": "-237500.0", "tr_5760_estimates": 3.906e-14,
                        "tr_5760_estimates_str": "3.906e-14", "tr_5760_log_adjusted_pvalues": 10.4,
                        "tr_5760_log_adjusted_pvalues_str": "10.4", "tr_5760_pvalues": 6.962e-14,
                        "tr_5760_pvalues_str": "6.962e-14"},
                "250": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0259", "cpd_name": "PC(16:0/15:0)",
                        "harmonised_annotation_id": "250", "tr_5289_adjusted_pvalues": 0.02379,
                        "tr_5289_adjusted_pvalues_str": "0.02379", "tr_5289_aic": -189000,
                        "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -3.55e-15,
                        "tr_5289_estimates_str": "-3.55e-15", "tr_5289_log_adjusted_pvalues": -1.624,
                        "tr_5289_log_adjusted_pvalues_str": "-1.624", "tr_5289_pvalues": 0.00004124,
                        "tr_5289_pvalues_str": "4.124e-05", "tr_5760_adjusted_pvalues": 0.01645,
                        "tr_5760_adjusted_pvalues_str": "0.01645", "tr_5760_aic": -252600,
                        "tr_5760_aic_str": "-252600.0", "tr_5760_estimates": -3.098e-15,
                        "tr_5760_estimates_str": "-3.098e-15", "tr_5760_log_adjusted_pvalues": -1.784,
                        "tr_5760_log_adjusted_pvalues_str": "-1.784", "tr_5760_pvalues": 0.00002851,
                        "tr_5760_pvalues_str": "2.851e-05"},
                "253": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0195",
                        "cpd_name": "SM(d18:2/24:0)", "harmonised_annotation_id": "253",
                        "tr_5289_adjusted_pvalues": 5.885e-10, "tr_5289_adjusted_pvalues_str": "5.885e-10",
                        "tr_5289_aic": -175300, "tr_5289_aic_str": "-175300.0", "tr_5289_estimates": -6.012e-14,
                        "tr_5289_estimates_str": "-6.012e-14", "tr_5289_log_adjusted_pvalues": -9.23,
                        "tr_5289_log_adjusted_pvalues_str": "-9.23", "tr_5289_pvalues": 1.02e-12,
                        "tr_5289_pvalues_str": "1.02e-12", "tr_5760_adjusted_pvalues": 4.808e-17,
                        "tr_5760_adjusted_pvalues_str": "4.808e-17", "tr_5760_aic": -248000,
                        "tr_5760_aic_str": "-248000.0", "tr_5760_estimates": -1.165e-14,
                        "tr_5760_estimates_str": "-1.165e-14", "tr_5760_log_adjusted_pvalues": -16.32,
                        "tr_5760_log_adjusted_pvalues_str": "-16.32", "tr_5760_pvalues": 8.332e-20,
                        "tr_5760_pvalues_str": "8.332e-20"},
                "254": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0240",
                        "cpd_name": "Cer(d42:3); Cer(d18:2/24:1)| Cer(d18:1/24:2)", "harmonised_annotation_id": "254",
                        "tr_5289_adjusted_pvalues": 5.525e-15, "tr_5289_adjusted_pvalues_str": "5.525e-15",
                        "tr_5289_aic": -174700, "tr_5289_aic_str": "-174700.0", "tr_5289_estimates": 8.161e-14,
                        "tr_5289_estimates_str": "8.161e-14", "tr_5289_log_adjusted_pvalues": 14.26,
                        "tr_5289_log_adjusted_pvalues_str": "14.26", "tr_5289_pvalues": 9.575e-18,
                        "tr_5289_pvalues_str": "9.575e-18", "tr_5760_adjusted_pvalues": 1.186e-16,
                        "tr_5760_adjusted_pvalues_str": "1.186e-16", "tr_5760_aic": -242300,
                        "tr_5760_aic_str": "-242300.0", "tr_5760_estimates": 2.424e-14,
                        "tr_5760_estimates_str": "2.424e-14", "tr_5760_log_adjusted_pvalues": 15.93,
                        "tr_5760_log_adjusted_pvalues_str": "15.93", "tr_5760_pvalues": 2.055e-19,
                        "tr_5760_pvalues_str": "2.055e-19"},
                "257": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0149", "cpd_name": "PC(18:0/20:4)",
                        "harmonised_annotation_id": "257", "tr_5289_adjusted_pvalues": 0.0323,
                        "tr_5289_adjusted_pvalues_str": "0.0323", "tr_5289_aic": -182400,
                        "tr_5289_aic_str": "-182400.0", "tr_5289_estimates": -1.015e-14,
                        "tr_5289_estimates_str": "-1.015e-14", "tr_5289_log_adjusted_pvalues": -1.491,
                        "tr_5289_log_adjusted_pvalues_str": "-1.491", "tr_5289_pvalues": 0.00005597,
                        "tr_5289_pvalues_str": "5.597e-05", "tr_5760_adjusted_pvalues": 0.005089,
                        "tr_5760_adjusted_pvalues_str": "0.005089", "tr_5760_aic": -245900,
                        "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": -7.417e-15,
                        "tr_5760_estimates_str": "-7.417e-15", "tr_5760_log_adjusted_pvalues": -2.293,
                        "tr_5760_log_adjusted_pvalues_str": "-2.293", "tr_5760_pvalues": 0.00000882,
                        "tr_5760_pvalues_str": "8.82e-06"},
                "263": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0147", "cpd_name": "PC(18:0/18:2)",
                        "harmonised_annotation_id": "263", "tr_5289_adjusted_pvalues": 29.37,
                        "tr_5289_adjusted_pvalues_str": "29.37", "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0",
                        "tr_5289_estimates": -2.875e-15, "tr_5289_estimates_str": "-2.875e-15",
                        "tr_5289_log_adjusted_pvalues": 1.468, "tr_5289_log_adjusted_pvalues_str": "1.468",
                        "tr_5289_pvalues": 0.05089, "tr_5289_pvalues_str": "0.05089",
                        "tr_5760_adjusted_pvalues": 0.6539, "tr_5760_adjusted_pvalues_str": "0.6539",
                        "tr_5760_aic": -242000, "tr_5760_aic_str": "-242000.0", "tr_5760_estimates": 8.599e-15,
                        "tr_5760_estimates_str": "8.599e-15", "tr_5760_log_adjusted_pvalues": 0.1845,
                        "tr_5760_log_adjusted_pvalues_str": "0.1845", "tr_5760_pvalues": 0.001133,
                        "tr_5760_pvalues_str": "0.001133"},
                "268": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0004", "cpd_name": "CAR(10:1)",
                        "harmonised_annotation_id": "268", "tr_5289_adjusted_pvalues": 8.143,
                        "tr_5289_adjusted_pvalues_str": "8.143", "tr_5289_aic": -180800, "tr_5289_aic_str": "-180800.0",
                        "tr_5289_estimates": -8.882e-15, "tr_5289_estimates_str": "-8.882e-15",
                        "tr_5289_log_adjusted_pvalues": 0.9108, "tr_5289_log_adjusted_pvalues_str": "0.9108",
                        "tr_5289_pvalues": 0.01411, "tr_5289_pvalues_str": "0.01411", "tr_5760_adjusted_pvalues": 0.716,
                        "tr_5760_adjusted_pvalues_str": "0.716", "tr_5760_aic": -242000, "tr_5760_aic_str": "-242000.0",
                        "tr_5760_estimates": 9.54e-15, "tr_5760_estimates_str": "9.54e-15",
                        "tr_5760_log_adjusted_pvalues": 0.1451, "tr_5760_log_adjusted_pvalues_str": "0.1451",
                        "tr_5760_pvalues": 0.001241, "tr_5760_pvalues_str": "0.001241"},
                "269": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0146", "cpd_name": "PC(18:0/18:1)",
                        "harmonised_annotation_id": "269", "tr_5289_adjusted_pvalues": 0.0001764,
                        "tr_5289_adjusted_pvalues_str": "0.0001764", "tr_5289_aic": -188200,
                        "tr_5289_aic_str": "-188200.0", "tr_5289_estimates": 4.919e-15,
                        "tr_5289_estimates_str": "4.919e-15", "tr_5289_log_adjusted_pvalues": 3.754,
                        "tr_5289_log_adjusted_pvalues_str": "3.754", "tr_5289_pvalues": 3.057e-7,
                        "tr_5289_pvalues_str": "3.057e-07", "tr_5760_adjusted_pvalues": 1.457e-8,
                        "tr_5760_adjusted_pvalues_str": "1.457e-08", "tr_5760_aic": -248000,
                        "tr_5760_aic_str": "-248000.0", "tr_5760_estimates": 8.582e-15,
                        "tr_5760_estimates_str": "8.582e-15", "tr_5760_log_adjusted_pvalues": 7.836,
                        "tr_5760_log_adjusted_pvalues_str": "7.836", "tr_5760_pvalues": 2.525e-11,
                        "tr_5760_pvalues_str": "2.525e-11"},
                "275": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0186",
                        "cpd_name": "SM(d18:1/23:0)", "harmonised_annotation_id": "275",
                        "tr_5289_adjusted_pvalues": 1.069e-8, "tr_5289_adjusted_pvalues_str": "1.069e-08",
                        "tr_5289_aic": -185900, "tr_5289_aic_str": "-185900.0", "tr_5289_estimates": 9.52e-15,
                        "tr_5289_estimates_str": "9.52e-15", "tr_5289_log_adjusted_pvalues": 7.971,
                        "tr_5289_log_adjusted_pvalues_str": "7.971", "tr_5289_pvalues": 1.853e-11,
                        "tr_5289_pvalues_str": "1.853e-11", "tr_5760_adjusted_pvalues": 2.931e-33,
                        "tr_5760_adjusted_pvalues_str": "2.931e-33", "tr_5760_aic": -231800,
                        "tr_5760_aic_str": "-231800.0", "tr_5760_estimates": -1.245e-13,
                        "tr_5760_estimates_str": "-1.245e-13", "tr_5760_log_adjusted_pvalues": -32.53,
                        "tr_5760_log_adjusted_pvalues_str": "-32.53", "tr_5760_pvalues": 5.079e-36,
                        "tr_5760_pvalues_str": "5.079e-36"},
                "280": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0142", "cpd_name": "PC(16:0/22:6)",
                        "harmonised_annotation_id": "280", "tr_5289_adjusted_pvalues": 2.297e-15,
                        "tr_5289_adjusted_pvalues_str": "2.297e-15", "tr_5289_aic": -182300,
                        "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": -2.303e-14,
                        "tr_5289_estimates_str": "-2.303e-14", "tr_5289_log_adjusted_pvalues": -14.64,
                        "tr_5289_log_adjusted_pvalues_str": "-14.64", "tr_5289_pvalues": 3.981e-18,
                        "tr_5289_pvalues_str": "3.981e-18", "tr_5760_adjusted_pvalues": 5.915e-21,
                        "tr_5760_adjusted_pvalues_str": "5.915e-21", "tr_5760_aic": -248000,
                        "tr_5760_aic_str": "-248000.0", "tr_5760_estimates": 1.31e-14,
                        "tr_5760_estimates_str": "1.31e-14", "tr_5760_log_adjusted_pvalues": 20.23,
                        "tr_5760_log_adjusted_pvalues_str": "20.23", "tr_5760_pvalues": 1.025e-23,
                        "tr_5760_pvalues_str": "1.025e-23"},
                "281": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0204", "cpd_name": "TG(46:1)",
                        "harmonised_annotation_id": "281", "tr_5289_adjusted_pvalues": 1.626e-10,
                        "tr_5289_adjusted_pvalues_str": "1.626e-10", "tr_5289_aic": -182300,
                        "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": -2.073e-14,
                        "tr_5289_estimates_str": "-2.073e-14", "tr_5289_log_adjusted_pvalues": -9.789,
                        "tr_5289_log_adjusted_pvalues_str": "-9.789", "tr_5289_pvalues": 2.818e-13,
                        "tr_5289_pvalues_str": "2.818e-13", "tr_5760_adjusted_pvalues": 1.189e-7,
                        "tr_5760_adjusted_pvalues_str": "1.189e-07", "tr_5760_aic": -243900,
                        "tr_5760_aic_str": "-243900.0", "tr_5760_estimates": -1.497e-14,
                        "tr_5760_estimates_str": "-1.497e-14", "tr_5760_log_adjusted_pvalues": -6.925,
                        "tr_5760_log_adjusted_pvalues_str": "-6.925", "tr_5760_pvalues": 2.06e-10,
                        "tr_5760_pvalues_str": "2.06e-10"},
                "282": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0268",
                        "cpd_name": "PC(O-16:0/20:3)", "harmonised_annotation_id": "282",
                        "tr_5289_adjusted_pvalues": 0.003033, "tr_5289_adjusted_pvalues_str": "0.003033",
                        "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": -6.69e-15,
                        "tr_5289_estimates_str": "-6.69e-15", "tr_5289_log_adjusted_pvalues": -2.518,
                        "tr_5289_log_adjusted_pvalues_str": "-2.518", "tr_5289_pvalues": 0.000005257,
                        "tr_5289_pvalues_str": "5.257e-06", "tr_5760_adjusted_pvalues": 3.148e-10,
                        "tr_5760_adjusted_pvalues_str": "3.148e-10", "tr_5760_aic": -234000,
                        "tr_5760_aic_str": "-234000.0", "tr_5760_estimates": 5.402e-14,
                        "tr_5760_estimates_str": "5.402e-14", "tr_5760_log_adjusted_pvalues": 9.502,
                        "tr_5760_log_adjusted_pvalues_str": "9.502", "tr_5760_pvalues": 5.455e-13,
                        "tr_5760_pvalues_str": "5.455e-13"},
                "283": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0188",
                        "cpd_name": "SM(d18:1/24:1)", "harmonised_annotation_id": "283",
                        "tr_5289_adjusted_pvalues": 0.9956, "tr_5289_adjusted_pvalues_str": "0.9956",
                        "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0", "tr_5289_estimates": 9.288e-15,
                        "tr_5289_estimates_str": "9.288e-15", "tr_5289_log_adjusted_pvalues": 0.001933,
                        "tr_5289_log_adjusted_pvalues_str": "0.001933", "tr_5289_pvalues": 0.001725,
                        "tr_5289_pvalues_str": "0.001725", "tr_5760_adjusted_pvalues": 0.00002134,
                        "tr_5760_adjusted_pvalues_str": "2.134e-05", "tr_5760_aic": -233300,
                        "tr_5760_aic_str": "-233300.0", "tr_5760_estimates": 4.445e-14,
                        "tr_5760_estimates_str": "4.445e-14", "tr_5760_log_adjusted_pvalues": 4.671,
                        "tr_5760_log_adjusted_pvalues_str": "4.671", "tr_5760_pvalues": 3.698e-8,
                        "tr_5760_pvalues_str": "3.698e-08"},
                "288": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0381",
                        "cpd_name": "PC(O-16:1/18:2) and/or PC(P-16:0/18:2)", "harmonised_annotation_id": "288",
                        "tr_5289_adjusted_pvalues": 2.8, "tr_5289_adjusted_pvalues_str": "2.8", "tr_5289_aic": -189000,
                        "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": 2.542e-15,
                        "tr_5289_estimates_str": "2.542e-15", "tr_5289_log_adjusted_pvalues": -0.4472,
                        "tr_5289_log_adjusted_pvalues_str": "-0.4472", "tr_5289_pvalues": 0.004853,
                        "tr_5289_pvalues_str": "0.004853", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "289": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0001",
                        "cpd_name": "Octanoylcarnitine CAR(8:0)", "harmonised_annotation_id": "289",
                        "tr_5289_adjusted_pvalues": 22.19, "tr_5289_adjusted_pvalues_str": "22.19",
                        "tr_5289_aic": -178000, "tr_5289_aic_str": "-178000.0", "tr_5289_estimates": 1.491e-14,
                        "tr_5289_estimates_str": "1.491e-14", "tr_5289_log_adjusted_pvalues": -1.346,
                        "tr_5289_log_adjusted_pvalues_str": "-1.346", "tr_5289_pvalues": 0.03846,
                        "tr_5289_pvalues_str": "0.03846", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "290": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0205", "cpd_name": "TG(46:2)",
                        "harmonised_annotation_id": "290", "tr_5289_adjusted_pvalues": 3.696e-10,
                        "tr_5289_adjusted_pvalues_str": "3.696e-10", "tr_5289_aic": -178200,
                        "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": -4.078e-14,
                        "tr_5289_estimates_str": "-4.078e-14", "tr_5289_log_adjusted_pvalues": -9.432,
                        "tr_5289_log_adjusted_pvalues_str": "-9.432", "tr_5289_pvalues": 6.405e-13,
                        "tr_5289_pvalues_str": "6.405e-13", "tr_5760_adjusted_pvalues": 3.586e-9,
                        "tr_5760_adjusted_pvalues_str": "3.586e-09", "tr_5760_aic": -234100,
                        "tr_5760_aic_str": "-234100.0", "tr_5760_estimates": 5.522e-14,
                        "tr_5760_estimates_str": "5.522e-14", "tr_5760_log_adjusted_pvalues": 8.445,
                        "tr_5760_log_adjusted_pvalues_str": "8.445", "tr_5760_pvalues": 6.216e-12,
                        "tr_5760_pvalues_str": "6.216e-12"},
                "291": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0219", "cpd_name": "TG(52:3)",
                        "harmonised_annotation_id": "291", "tr_5289_adjusted_pvalues": 0.006641,
                        "tr_5289_adjusted_pvalues_str": "0.006641", "tr_5289_aic": -177100,
                        "tr_5289_aic_str": "-177100.0", "tr_5289_estimates": 2.879e-14,
                        "tr_5289_estimates_str": "2.879e-14", "tr_5289_log_adjusted_pvalues": 2.178,
                        "tr_5289_log_adjusted_pvalues_str": "2.178", "tr_5289_pvalues": 0.00001151,
                        "tr_5289_pvalues_str": "1.151e-05", "tr_5760_adjusted_pvalues": 0.0001219,
                        "tr_5760_adjusted_pvalues_str": "0.0001219", "tr_5760_aic": -238800,
                        "tr_5760_aic_str": "-238800.0", "tr_5760_estimates": -2.254e-14,
                        "tr_5760_estimates_str": "-2.254e-14", "tr_5760_log_adjusted_pvalues": -3.914,
                        "tr_5760_log_adjusted_pvalues_str": "-3.914", "tr_5760_pvalues": 2.112e-7,
                        "tr_5760_pvalues_str": "2.112e-07"},
                "293": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0362", "cpd_name": "TG(60:2)",
                        "harmonised_annotation_id": "293", "tr_5289_adjusted_pvalues": 1.404,
                        "tr_5289_adjusted_pvalues_str": "1.404", "tr_5289_aic": -178800, "tr_5289_aic_str": "-178800.0",
                        "tr_5289_estimates": 1.7e-14, "tr_5289_estimates_str": "1.7e-14",
                        "tr_5289_log_adjusted_pvalues": -0.1473, "tr_5289_log_adjusted_pvalues_str": "-0.1473",
                        "tr_5289_pvalues": 0.002433, "tr_5289_pvalues_str": "0.002433",
                        "tr_5760_adjusted_pvalues": 0.549, "tr_5760_adjusted_pvalues_str": "0.549",
                        "tr_5760_aic": -238200, "tr_5760_aic_str": "-238200.0", "tr_5760_estimates": -1.724e-14,
                        "tr_5760_estimates_str": "-1.724e-14", "tr_5760_log_adjusted_pvalues": -0.2604,
                        "tr_5760_log_adjusted_pvalues_str": "-0.2604", "tr_5760_pvalues": 0.0009515,
                        "tr_5760_pvalues_str": "0.0009515"},
                "294": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0091", "cpd_name": "LPC(16:1/0:0)",
                        "harmonised_annotation_id": "294", "tr_5289_adjusted_pvalues": 0.000003184,
                        "tr_5289_adjusted_pvalues_str": "3.184e-06", "tr_5289_aic": -180800,
                        "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -2.028e-14,
                        "tr_5289_estimates_str": "-2.028e-14", "tr_5289_log_adjusted_pvalues": -5.497,
                        "tr_5289_log_adjusted_pvalues_str": "-5.497", "tr_5289_pvalues": 5.519e-9,
                        "tr_5289_pvalues_str": "5.519e-09", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "295": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0241",
                        "cpd_name": "Cer(t18:0/24:1)", "harmonised_annotation_id": "295",
                        "tr_5289_adjusted_pvalues": 1.865e-36, "tr_5289_adjusted_pvalues_str": "1.865e-36",
                        "tr_5289_aic": -172800, "tr_5289_aic_str": "-172800.0", "tr_5289_estimates": -1.858e-13,
                        "tr_5289_estimates_str": "-1.858e-13", "tr_5289_log_adjusted_pvalues": -35.73,
                        "tr_5289_log_adjusted_pvalues_str": "-35.73", "tr_5289_pvalues": 3.232e-39,
                        "tr_5289_pvalues_str": "3.232e-39", "tr_5760_adjusted_pvalues": 4.145e-32,
                        "tr_5760_adjusted_pvalues_str": "4.145e-32", "tr_5760_aic": -248100,
                        "tr_5760_aic_str": "-248100.0", "tr_5760_estimates": 1.709e-14,
                        "tr_5760_estimates_str": "1.709e-14", "tr_5760_log_adjusted_pvalues": 31.38,
                        "tr_5760_log_adjusted_pvalues_str": "31.38", "tr_5760_pvalues": 7.184e-35,
                        "tr_5760_pvalues_str": "7.184e-35"},
                "301": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0177",
                        "cpd_name": "SM(d17:1/16:0)", "harmonised_annotation_id": "301",
                        "tr_5289_adjusted_pvalues": 1.769e-25, "tr_5289_adjusted_pvalues_str": "1.769e-25",
                        "tr_5289_aic": -176800, "tr_5289_aic_str": "-176800.0", "tr_5289_estimates": -7.576e-14,
                        "tr_5289_estimates_str": "-7.576e-14", "tr_5289_log_adjusted_pvalues": -24.75,
                        "tr_5289_log_adjusted_pvalues_str": "-24.75", "tr_5289_pvalues": 3.065e-28,
                        "tr_5289_pvalues_str": "3.065e-28", "tr_5760_adjusted_pvalues": 6.218e-14,
                        "tr_5760_adjusted_pvalues_str": "6.218e-14", "tr_5760_aic": -249200,
                        "tr_5760_aic_str": "-249200.0", "tr_5760_estimates": 9.539e-15,
                        "tr_5760_estimates_str": "9.539e-15", "tr_5760_log_adjusted_pvalues": 13.21,
                        "tr_5760_log_adjusted_pvalues_str": "13.21", "tr_5760_pvalues": 1.078e-16,
                        "tr_5760_pvalues_str": "1.078e-16"},
                "302": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0028", "cpd_name": "CAR(20:4)",
                        "harmonised_annotation_id": "302", "tr_5289_adjusted_pvalues": 564.6,
                        "tr_5289_adjusted_pvalues_str": "564.6", "tr_5289_aic": -176700, "tr_5289_aic_str": "-176700.0",
                        "tr_5289_estimates": -2.051e-16, "tr_5289_estimates_str": "-2.051e-16",
                        "tr_5289_log_adjusted_pvalues": 2.752, "tr_5289_log_adjusted_pvalues_str": "2.752",
                        "tr_5289_pvalues": 0.9784, "tr_5289_pvalues_str": "0.9784", "tr_5760_adjusted_pvalues": 503.3,
                        "tr_5760_adjusted_pvalues_str": "503.3", "tr_5760_aic": -243500, "tr_5760_aic_str": "-243500.0",
                        "tr_5760_estimates": 4.12e-16, "tr_5760_estimates_str": "4.12e-16",
                        "tr_5760_log_adjusted_pvalues": -2.702, "tr_5760_log_adjusted_pvalues_str": "-2.702",
                        "tr_5760_pvalues": 0.8722, "tr_5760_pvalues_str": "0.8722"},
                "303": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0029",
                        "cpd_name": "Tetracosanoylcarnitine CAR(24:0)", "harmonised_annotation_id": "303",
                        "tr_5289_adjusted_pvalues": 3.074e-8, "tr_5289_adjusted_pvalues_str": "3.074e-08",
                        "tr_5289_aic": -178800, "tr_5289_aic_str": "-178800.0", "tr_5289_estimates": -3.355e-14,
                        "tr_5289_estimates_str": "-3.355e-14", "tr_5289_log_adjusted_pvalues": -7.512,
                        "tr_5289_log_adjusted_pvalues_str": "-7.512", "tr_5289_pvalues": 5.328e-11,
                        "tr_5289_pvalues_str": "5.328e-11", "tr_5760_adjusted_pvalues": 2.958,
                        "tr_5760_adjusted_pvalues_str": "2.958", "tr_5760_aic": -252500, "tr_5760_aic_str": "-252500.0",
                        "tr_5760_estimates": -2.179e-15, "tr_5760_estimates_str": "-2.179e-15",
                        "tr_5760_log_adjusted_pvalues": 0.4709, "tr_5760_log_adjusted_pvalues_str": "0.4709",
                        "tr_5760_pvalues": 0.005126, "tr_5760_pvalues_str": "0.005126"},
                "304": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0347", "cpd_name": "TG(56:9)",
                        "harmonised_annotation_id": "304", "tr_5289_adjusted_pvalues": 1.002e-16,
                        "tr_5289_adjusted_pvalues_str": "1.002e-16", "tr_5289_aic": -178900,
                        "tr_5289_aic_str": "-178900.0", "tr_5289_estimates": -4.448e-14,
                        "tr_5289_estimates_str": "-4.448e-14", "tr_5289_log_adjusted_pvalues": -16,
                        "tr_5289_log_adjusted_pvalues_str": "-16.0", "tr_5289_pvalues": 1.736e-19,
                        "tr_5289_pvalues_str": "1.736e-19", "tr_5760_adjusted_pvalues": 1.821e-18,
                        "tr_5760_adjusted_pvalues_str": "1.821e-18", "tr_5760_aic": -240400,
                        "tr_5760_aic_str": "-240400.0", "tr_5760_estimates": 3.373e-14,
                        "tr_5760_estimates_str": "3.373e-14", "tr_5760_log_adjusted_pvalues": 17.74,
                        "tr_5760_log_adjusted_pvalues_str": "17.74", "tr_5760_pvalues": 3.155e-21,
                        "tr_5760_pvalues_str": "3.155e-21"},
                "305": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0334", "cpd_name": "TG(55:4)",
                        "harmonised_annotation_id": "305", "tr_5289_adjusted_pvalues": 0.01052,
                        "tr_5289_adjusted_pvalues_str": "0.01052", "tr_5289_aic": -180800,
                        "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -1.535e-14,
                        "tr_5289_estimates_str": "-1.535e-14", "tr_5289_log_adjusted_pvalues": -1.978,
                        "tr_5289_log_adjusted_pvalues_str": "-1.978", "tr_5289_pvalues": 0.00001823,
                        "tr_5289_pvalues_str": "1.823e-05", "tr_5760_adjusted_pvalues": 0.01869,
                        "tr_5760_adjusted_pvalues_str": "0.01869", "tr_5760_aic": -237500,
                        "tr_5760_aic_str": "-237500.0", "tr_5760_estimates": -2.139e-14,
                        "tr_5760_estimates_str": "-2.139e-14", "tr_5760_log_adjusted_pvalues": -1.728,
                        "tr_5760_log_adjusted_pvalues_str": "-1.728", "tr_5760_pvalues": 0.00003239,
                        "tr_5760_pvalues_str": "3.239e-05"},
                "309": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0266",
                        "cpd_name": "PC(O-16:0/14:0)", "harmonised_annotation_id": "309",
                        "tr_5289_adjusted_pvalues": 297.3, "tr_5289_adjusted_pvalues_str": "297.3",
                        "tr_5289_aic": -179700, "tr_5289_aic_str": "-179700.0", "tr_5289_estimates": -2.66e-15,
                        "tr_5289_estimates_str": "-2.66e-15", "tr_5289_log_adjusted_pvalues": 2.473,
                        "tr_5289_log_adjusted_pvalues_str": "2.473", "tr_5289_pvalues": 0.5153,
                        "tr_5289_pvalues_str": "0.5153", "tr_5760_adjusted_pvalues": 519.7,
                        "tr_5760_adjusted_pvalues_str": "519.7", "tr_5760_aic": -246200, "tr_5760_aic_str": "-246200.0",
                        "tr_5760_estimates": -2.026e-16, "tr_5760_estimates_str": "-2.026e-16",
                        "tr_5760_log_adjusted_pvalues": 2.716, "tr_5760_log_adjusted_pvalues_str": "2.716",
                        "tr_5760_pvalues": 0.9008, "tr_5760_pvalues_str": "0.9008"},
                "310": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0143", "cpd_name": "PC(16:1/18:2)",
                        "harmonised_annotation_id": "310", "tr_5289_adjusted_pvalues": None,
                        "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                        "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                        "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "311": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0044",
                        "cpd_name": "Cer(d18:1/22:0)", "harmonised_annotation_id": "311",
                        "tr_5289_adjusted_pvalues": 2.712e-30, "tr_5289_adjusted_pvalues_str": "2.712e-30",
                        "tr_5289_aic": -174200, "tr_5289_aic_str": "-174200.0", "tr_5289_estimates": 1.305e-13,
                        "tr_5289_estimates_str": "1.305e-13", "tr_5289_log_adjusted_pvalues": 29.57,
                        "tr_5289_log_adjusted_pvalues_str": "29.57", "tr_5289_pvalues": 4.7e-33,
                        "tr_5289_pvalues_str": "4.7e-33", "tr_5760_adjusted_pvalues": 5.375e-28,
                        "tr_5760_adjusted_pvalues_str": "5.375e-28", "tr_5760_aic": -244000,
                        "tr_5760_aic_str": "-244000.0", "tr_5760_estimates": 2.581e-14,
                        "tr_5760_estimates_str": "2.581e-14", "tr_5760_log_adjusted_pvalues": 27.27,
                        "tr_5760_log_adjusted_pvalues_str": "27.27", "tr_5760_pvalues": 9.315e-31,
                        "tr_5760_pvalues_str": "9.315e-31"},
                "314": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0031", "cpd_name": "CAR(26:1)",
                        "harmonised_annotation_id": "314", "tr_5289_adjusted_pvalues": 2.019e-14,
                        "tr_5289_adjusted_pvalues_str": "2.019e-14", "tr_5289_aic": -179000,
                        "tr_5289_aic_str": "-179000.0", "tr_5289_estimates": 4.239e-14,
                        "tr_5289_estimates_str": "4.239e-14", "tr_5289_log_adjusted_pvalues": 13.69,
                        "tr_5289_log_adjusted_pvalues_str": "13.69", "tr_5289_pvalues": 3.5e-17,
                        "tr_5289_pvalues_str": "3.5e-17", "tr_5760_adjusted_pvalues": 9.609e-24,
                        "tr_5760_adjusted_pvalues_str": "9.609e-24", "tr_5760_aic": -238700,
                        "tr_5760_aic_str": "-238700.0", "tr_5760_estimates": 4.928e-14,
                        "tr_5760_estimates_str": "4.928e-14", "tr_5760_log_adjusted_pvalues": 23.02,
                        "tr_5760_log_adjusted_pvalues_str": "23.02", "tr_5760_pvalues": 1.665e-26,
                        "tr_5760_pvalues_str": "1.665e-26"},
                "317": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0111", "cpd_name": "LPC(24:0/0:0)",
                        "harmonised_annotation_id": "317", "tr_5289_adjusted_pvalues": 7.487e-9,
                        "tr_5289_adjusted_pvalues_str": "7.487e-09", "tr_5289_aic": -182300,
                        "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": -1.843e-14,
                        "tr_5289_estimates_str": "-1.843e-14", "tr_5289_log_adjusted_pvalues": -8.126,
                        "tr_5289_log_adjusted_pvalues_str": "-8.126", "tr_5289_pvalues": 1.298e-11,
                        "tr_5289_pvalues_str": "1.298e-11", "tr_5760_adjusted_pvalues": 0.2929,
                        "tr_5760_adjusted_pvalues_str": "0.2929", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": 2.629e-15,
                        "tr_5760_estimates_str": "2.629e-15", "tr_5760_log_adjusted_pvalues": 0.5333,
                        "tr_5760_log_adjusted_pvalues_str": "0.5333", "tr_5760_pvalues": 0.0005076,
                        "tr_5760_pvalues_str": "0.0005076"},
                "319": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0293",
                        "cpd_name": "SM(d30:1); SM(d16:1/14:0) | SM(d18:1/12:0)", "harmonised_annotation_id": "319",
                        "tr_5289_adjusted_pvalues": 1.274e-24, "tr_5289_adjusted_pvalues_str": "1.274e-24",
                        "tr_5289_aic": -185900, "tr_5289_aic_str": "-185900.0", "tr_5289_estimates": 1.668e-14,
                        "tr_5289_estimates_str": "1.668e-14", "tr_5289_log_adjusted_pvalues": 23.89,
                        "tr_5289_log_adjusted_pvalues_str": "23.89", "tr_5289_pvalues": 2.208e-27,
                        "tr_5289_pvalues_str": "2.208e-27", "tr_5760_adjusted_pvalues": 1.655e-41,
                        "tr_5760_adjusted_pvalues_str": "1.655e-41", "tr_5760_aic": -244100,
                        "tr_5760_aic_str": "-244100.0", "tr_5760_estimates": 3.173e-14,
                        "tr_5760_estimates_str": "3.173e-14", "tr_5760_log_adjusted_pvalues": 40.78,
                        "tr_5760_log_adjusted_pvalues_str": "40.78", "tr_5760_pvalues": 2.868e-44,
                        "tr_5760_pvalues_str": "2.868e-44"},
                "320": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0060", "cpd_name": "DG(18:2/18:1)",
                        "harmonised_annotation_id": "320", "tr_5289_adjusted_pvalues": 3.225,
                        "tr_5289_adjusted_pvalues_str": "3.225", "tr_5289_aic": -174300, "tr_5289_aic_str": "-174300.0",
                        "tr_5289_estimates": -3.089e-14, "tr_5289_estimates_str": "-3.089e-14",
                        "tr_5289_log_adjusted_pvalues": 0.5085, "tr_5289_log_adjusted_pvalues_str": "0.5085",
                        "tr_5289_pvalues": 0.005589, "tr_5289_pvalues_str": "0.005589",
                        "tr_5760_adjusted_pvalues": 1.064, "tr_5760_adjusted_pvalues_str": "1.064",
                        "tr_5760_aic": -238900, "tr_5760_aic_str": "-238900.0", "tr_5760_estimates": -1.413e-14,
                        "tr_5760_estimates_str": "-1.413e-14", "tr_5760_log_adjusted_pvalues": 0.02674,
                        "tr_5760_log_adjusted_pvalues_str": "0.02674", "tr_5760_pvalues": 0.001843,
                        "tr_5760_pvalues_str": "0.001843"},
                "321": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0007", "cpd_name": "CAR(12:0-OH)",
                        "harmonised_annotation_id": "321", "tr_5289_adjusted_pvalues": 2.832,
                        "tr_5289_adjusted_pvalues_str": "2.832", "tr_5289_aic": -173800, "tr_5289_aic_str": "-173800.0",
                        "tr_5289_estimates": 3.198e-14, "tr_5289_estimates_str": "3.198e-14",
                        "tr_5289_log_adjusted_pvalues": -0.4521, "tr_5289_log_adjusted_pvalues_str": "-0.4521",
                        "tr_5289_pvalues": 0.004909, "tr_5289_pvalues_str": "0.004909",
                        "tr_5760_adjusted_pvalues": 0.003466, "tr_5760_adjusted_pvalues_str": "0.003466",
                        "tr_5760_aic": -234100, "tr_5760_aic_str": "-234100.0", "tr_5760_estimates": 3.499e-14,
                        "tr_5760_estimates_str": "3.499e-14", "tr_5760_log_adjusted_pvalues": 2.46,
                        "tr_5760_log_adjusted_pvalues_str": "2.46", "tr_5760_pvalues": 0.000006007,
                        "tr_5760_pvalues_str": "6.007e-06"},
                "322": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0046",
                        "cpd_name": "Cer(d18:1/24:1)", "harmonised_annotation_id": "322",
                        "tr_5289_adjusted_pvalues": 1.841e-18, "tr_5289_adjusted_pvalues_str": "1.841e-18",
                        "tr_5289_aic": -182300, "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": -2.489e-14,
                        "tr_5289_estimates_str": "-2.489e-14", "tr_5289_log_adjusted_pvalues": -17.74,
                        "tr_5289_log_adjusted_pvalues_str": "-17.74", "tr_5289_pvalues": 3.19e-21,
                        "tr_5289_pvalues_str": "3.19e-21", "tr_5760_adjusted_pvalues": 1.381e-25,
                        "tr_5760_adjusted_pvalues_str": "1.381e-25", "tr_5760_aic": -245900,
                        "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": 1.863e-14,
                        "tr_5760_estimates_str": "1.863e-14", "tr_5760_log_adjusted_pvalues": 24.86,
                        "tr_5760_log_adjusted_pvalues_str": "24.86", "tr_5760_pvalues": 2.394e-28,
                        "tr_5760_pvalues_str": "2.394e-28"},
                "323": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0112",
                        "cpd_name": "LPC(O-16:0/0:0)", "harmonised_annotation_id": "323",
                        "tr_5289_adjusted_pvalues": 0.2896, "tr_5289_adjusted_pvalues_str": "0.2896",
                        "tr_5289_aic": -184700, "tr_5289_aic_str": "-184700.0", "tr_5289_estimates": -6.046e-15,
                        "tr_5289_estimates_str": "-6.046e-15", "tr_5289_log_adjusted_pvalues": -0.5381,
                        "tr_5289_log_adjusted_pvalues_str": "-0.5381", "tr_5289_pvalues": 0.000502,
                        "tr_5289_pvalues_str": "0.000502", "tr_5760_adjusted_pvalues": 0.005134,
                        "tr_5760_adjusted_pvalues_str": "0.005134", "tr_5760_aic": -230800,
                        "tr_5760_aic_str": "-230800.0", "tr_5760_estimates": 4.996e-14,
                        "tr_5760_estimates_str": "4.996e-14", "tr_5760_log_adjusted_pvalues": 2.29,
                        "tr_5760_log_adjusted_pvalues_str": "2.29", "tr_5760_pvalues": 0.000008898,
                        "tr_5760_pvalues_str": "8.898e-06"},
                "326": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0288",
                        "cpd_name": "PE(O-20:1/18:2) and/or PE(P-20:0/18:2)", "harmonised_annotation_id": "326",
                        "tr_5289_adjusted_pvalues": 321.6, "tr_5289_adjusted_pvalues_str": "321.6",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": 5.059e-16,
                        "tr_5289_estimates_str": "5.059e-16", "tr_5289_log_adjusted_pvalues": -2.507,
                        "tr_5289_log_adjusted_pvalues_str": "-2.507", "tr_5289_pvalues": 0.5573,
                        "tr_5289_pvalues_str": "0.5573", "tr_5760_adjusted_pvalues": 50.09,
                        "tr_5760_adjusted_pvalues_str": "50.09", "tr_5760_aic": -235600, "tr_5760_aic_str": "-235600.0",
                        "tr_5760_estimates": 1.078e-14, "tr_5760_estimates_str": "1.078e-14",
                        "tr_5760_log_adjusted_pvalues": -1.7, "tr_5760_log_adjusted_pvalues_str": "-1.7",
                        "tr_5760_pvalues": 0.08681, "tr_5760_pvalues_str": "0.08681"},
                "328": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0171",
                        "cpd_name": "PE(O-18:1/20:4) and/or PE(P-18:0/20:4)", "harmonised_annotation_id": "328",
                        "tr_5289_adjusted_pvalues": 363.1, "tr_5289_adjusted_pvalues_str": "363.1",
                        "tr_5289_aic": -178400, "tr_5289_aic_str": "-178400.0", "tr_5289_estimates": 2.499e-15,
                        "tr_5289_estimates_str": "2.499e-15", "tr_5289_log_adjusted_pvalues": -2.56,
                        "tr_5289_log_adjusted_pvalues_str": "-2.56", "tr_5289_pvalues": 0.6293,
                        "tr_5289_pvalues_str": "0.6293", "tr_5760_adjusted_pvalues": 242.3,
                        "tr_5760_adjusted_pvalues_str": "242.3", "tr_5760_aic": -231300, "tr_5760_aic_str": "-231300.0",
                        "tr_5760_estimates": -8.65e-15, "tr_5760_estimates_str": "-8.65e-15",
                        "tr_5760_log_adjusted_pvalues": 2.384, "tr_5760_log_adjusted_pvalues_str": "2.384",
                        "tr_5760_pvalues": 0.4199, "tr_5760_pvalues_str": "0.4199"},
                "329": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0248",
                        "cpd_name": "LPC(22:5/0:0)_1", "harmonised_annotation_id": "329",
                        "tr_5289_adjusted_pvalues": 0.000003412, "tr_5289_adjusted_pvalues_str": "3.412e-06",
                        "tr_5289_aic": -193100, "tr_5289_aic_str": "-193100.0", "tr_5289_estimates": 2.603e-15,
                        "tr_5289_estimates_str": "2.603e-15", "tr_5289_log_adjusted_pvalues": 5.467,
                        "tr_5289_log_adjusted_pvalues_str": "5.467", "tr_5289_pvalues": 5.913e-9,
                        "tr_5289_pvalues_str": "5.913e-09", "tr_5760_adjusted_pvalues": 3.285e-16,
                        "tr_5760_adjusted_pvalues_str": "3.285e-16", "tr_5760_aic": -239400,
                        "tr_5760_aic_str": "-239400.0", "tr_5760_estimates": 3.611e-14,
                        "tr_5760_estimates_str": "3.611e-14", "tr_5760_log_adjusted_pvalues": 15.48,
                        "tr_5760_log_adjusted_pvalues_str": "15.48", "tr_5760_pvalues": 5.694e-19,
                        "tr_5760_pvalues_str": "5.694e-19"},
                "332": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0383", "cpd_name": "retinol",
                        "harmonised_annotation_id": "332", "tr_5289_adjusted_pvalues": 4.551,
                        "tr_5289_adjusted_pvalues_str": "4.551", "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0",
                        "tr_5289_estimates": -1.001e-14, "tr_5289_estimates_str": "-1.001e-14",
                        "tr_5289_log_adjusted_pvalues": 0.6581, "tr_5289_log_adjusted_pvalues_str": "0.6581",
                        "tr_5289_pvalues": 0.007888, "tr_5289_pvalues_str": "0.007888",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "333": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0184",
                        "cpd_name": "SM(d18:1/20:1)", "harmonised_annotation_id": "333",
                        "tr_5289_adjusted_pvalues": 0.00000219, "tr_5289_adjusted_pvalues_str": "2.19e-06",
                        "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": -2.304e-14,
                        "tr_5289_estimates_str": "-2.304e-14", "tr_5289_log_adjusted_pvalues": -5.659,
                        "tr_5289_log_adjusted_pvalues_str": "-5.659", "tr_5289_pvalues": 3.796e-9,
                        "tr_5289_pvalues_str": "3.796e-09", "tr_5760_adjusted_pvalues": 5.12e-11,
                        "tr_5760_adjusted_pvalues_str": "5.12e-11", "tr_5760_aic": -235600,
                        "tr_5760_aic_str": "-235600.0", "tr_5760_estimates": -4.693e-14,
                        "tr_5760_estimates_str": "-4.693e-14", "tr_5760_log_adjusted_pvalues": -10.29,
                        "tr_5760_log_adjusted_pvalues_str": "-10.29", "tr_5760_pvalues": 8.873e-14,
                        "tr_5760_pvalues_str": "8.873e-14"},
                "334": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0323", "cpd_name": "TG(53:5)",
                        "harmonised_annotation_id": "334", "tr_5289_adjusted_pvalues": 0.0002546,
                        "tr_5289_adjusted_pvalues_str": "0.0002546", "tr_5289_aic": -182400,
                        "tr_5289_aic_str": "-182400.0", "tr_5289_estimates": 1.377e-14,
                        "tr_5289_estimates_str": "1.377e-14", "tr_5289_log_adjusted_pvalues": 3.594,
                        "tr_5289_log_adjusted_pvalues_str": "3.594", "tr_5289_pvalues": 4.413e-7,
                        "tr_5289_pvalues_str": "4.413e-07", "tr_5760_adjusted_pvalues": 0.003321,
                        "tr_5760_adjusted_pvalues_str": "0.003321", "tr_5760_aic": -242100,
                        "tr_5760_aic_str": "-242100.0", "tr_5760_estimates": 1.297e-14,
                        "tr_5760_estimates_str": "1.297e-14", "tr_5760_log_adjusted_pvalues": 2.479,
                        "tr_5760_log_adjusted_pvalues_str": "2.479", "tr_5760_pvalues": 0.000005755,
                        "tr_5760_pvalues_str": "5.755e-06"},
                "335": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0214", "cpd_name": "TG(50:2)",
                        "harmonised_annotation_id": "335", "tr_5289_adjusted_pvalues": 1.685e-11,
                        "tr_5289_adjusted_pvalues_str": "1.685e-11", "tr_5289_aic": -183600,
                        "tr_5289_aic_str": "-183600.0", "tr_5289_estimates": -1.702e-14,
                        "tr_5289_estimates_str": "-1.702e-14", "tr_5289_log_adjusted_pvalues": -10.77,
                        "tr_5289_log_adjusted_pvalues_str": "-10.77", "tr_5289_pvalues": 2.921e-14,
                        "tr_5289_pvalues_str": "2.921e-14", "tr_5760_adjusted_pvalues": 9.003e-15,
                        "tr_5760_adjusted_pvalues_str": "9.003e-15", "tr_5760_aic": -240800,
                        "tr_5760_aic_str": "-240800.0", "tr_5760_estimates": -2.952e-14,
                        "tr_5760_estimates_str": "-2.952e-14", "tr_5760_log_adjusted_pvalues": -14.05,
                        "tr_5760_log_adjusted_pvalues_str": "-14.05", "tr_5760_pvalues": 1.56e-17,
                        "tr_5760_pvalues_str": "1.56e-17"},
                "336": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0340", "cpd_name": "TG(56:5)",
                        "harmonised_annotation_id": "336", "tr_5289_adjusted_pvalues": 180.2,
                        "tr_5289_adjusted_pvalues_str": "180.2", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                        "tr_5289_estimates": -8.324e-16, "tr_5289_estimates_str": "-8.324e-16",
                        "tr_5289_log_adjusted_pvalues": 2.256, "tr_5289_log_adjusted_pvalues_str": "2.256",
                        "tr_5289_pvalues": 0.3123, "tr_5289_pvalues_str": "0.3123", "tr_5760_adjusted_pvalues": 0.5548,
                        "tr_5760_adjusted_pvalues_str": "0.5548", "tr_5760_aic": -233300,
                        "tr_5760_aic_str": "-233300.0", "tr_5760_estimates": 2.681e-14,
                        "tr_5760_estimates_str": "2.681e-14", "tr_5760_log_adjusted_pvalues": 0.2558,
                        "tr_5760_log_adjusted_pvalues_str": "0.2558", "tr_5760_pvalues": 0.0009616,
                        "tr_5760_pvalues_str": "0.0009616"},
                "341": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0250",
                        "cpd_name": "LPC(O-24:0/0:0)", "harmonised_annotation_id": "341",
                        "tr_5289_adjusted_pvalues": 0.02172, "tr_5289_adjusted_pvalues_str": "0.02172",
                        "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": -6.138e-15,
                        "tr_5289_estimates_str": "-6.138e-15", "tr_5289_log_adjusted_pvalues": -1.663,
                        "tr_5289_log_adjusted_pvalues_str": "-1.663", "tr_5289_pvalues": 0.00003764,
                        "tr_5289_pvalues_str": "3.764e-05", "tr_5760_adjusted_pvalues": 0.1621,
                        "tr_5760_adjusted_pvalues_str": "0.1621", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": 2.655e-15,
                        "tr_5760_estimates_str": "2.655e-15", "tr_5760_log_adjusted_pvalues": 0.7901,
                        "tr_5760_log_adjusted_pvalues_str": "0.7901", "tr_5760_pvalues": 0.000281,
                        "tr_5760_pvalues_str": "0.000281"},
                "342": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0016",
                        "cpd_name": "Palmitoylcarnitine CAR(16:0)", "harmonised_annotation_id": "342",
                        "tr_5289_adjusted_pvalues": 1.697, "tr_5289_adjusted_pvalues_str": "1.697",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -2.699e-15,
                        "tr_5289_estimates_str": "-2.699e-15", "tr_5289_log_adjusted_pvalues": 0.2297,
                        "tr_5289_log_adjusted_pvalues_str": "0.2297", "tr_5289_pvalues": 0.002941,
                        "tr_5289_pvalues_str": "0.002941", "tr_5760_adjusted_pvalues": 6.959e-15,
                        "tr_5760_adjusted_pvalues_str": "6.959e-15", "tr_5760_aic": -233300,
                        "tr_5760_aic_str": "-233300.0", "tr_5760_estimates": 7.609e-14,
                        "tr_5760_estimates_str": "7.609e-14", "tr_5760_log_adjusted_pvalues": 14.16,
                        "tr_5760_log_adjusted_pvalues_str": "14.16", "tr_5760_pvalues": 1.206e-17,
                        "tr_5760_pvalues_str": "1.206e-17"},
                "345": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0169",
                        "cpd_name": "PE(36:1); PE(18:0/18:1) | PE(18:1/18:0)", "harmonised_annotation_id": "345",
                        "tr_5289_adjusted_pvalues": 2.031, "tr_5289_adjusted_pvalues_str": "2.031",
                        "tr_5289_aic": -177200, "tr_5289_aic_str": "-177200.0", "tr_5289_estimates": 1.862e-14,
                        "tr_5289_estimates_str": "1.862e-14", "tr_5289_log_adjusted_pvalues": -0.3077,
                        "tr_5289_log_adjusted_pvalues_str": "-0.3077", "tr_5289_pvalues": 0.00352,
                        "tr_5289_pvalues_str": "0.00352", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "346": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0099",
                        "cpd_name": "LPC(18:3/0:0)_2", "harmonised_annotation_id": "346",
                        "tr_5289_adjusted_pvalues": 172.3, "tr_5289_adjusted_pvalues_str": "172.3",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": 9.196e-16,
                        "tr_5289_estimates_str": "9.196e-16", "tr_5289_log_adjusted_pvalues": -2.236,
                        "tr_5289_log_adjusted_pvalues_str": "-2.236", "tr_5289_pvalues": 0.2987,
                        "tr_5289_pvalues_str": "0.2987", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "347": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0114",
                        "cpd_name": "LPC(O-18:1/0:0)", "harmonised_annotation_id": "347",
                        "tr_5289_adjusted_pvalues": 0.05783, "tr_5289_adjusted_pvalues_str": "0.05783",
                        "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": 6.274e-15,
                        "tr_5289_estimates_str": "6.274e-15", "tr_5289_log_adjusted_pvalues": 1.238,
                        "tr_5289_log_adjusted_pvalues_str": "1.238", "tr_5289_pvalues": 0.0001002,
                        "tr_5289_pvalues_str": "0.0001002", "tr_5760_adjusted_pvalues": 0.028,
                        "tr_5760_adjusted_pvalues_str": "0.028", "tr_5760_aic": -236200, "tr_5760_aic_str": "-236200.0",
                        "tr_5760_estimates": 2.276e-14, "tr_5760_estimates_str": "2.276e-14",
                        "tr_5760_log_adjusted_pvalues": 1.553, "tr_5760_log_adjusted_pvalues_str": "1.553",
                        "tr_5760_pvalues": 0.00004852, "tr_5760_pvalues_str": "4.852e-05"},
                "351": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0220", "cpd_name": "TG(52:4)_1",
                        "harmonised_annotation_id": "351", "tr_5289_adjusted_pvalues": 0.01337,
                        "tr_5289_adjusted_pvalues_str": "0.01337", "tr_5289_aic": -175600,
                        "tr_5289_aic_str": "-175600.0", "tr_5289_estimates": -3.661e-14,
                        "tr_5289_estimates_str": "-3.661e-14", "tr_5289_log_adjusted_pvalues": -1.874,
                        "tr_5289_log_adjusted_pvalues_str": "-1.874", "tr_5289_pvalues": 0.00002318,
                        "tr_5289_pvalues_str": "2.318e-05", "tr_5760_adjusted_pvalues": 0.003915,
                        "tr_5760_adjusted_pvalues_str": "0.003915", "tr_5760_aic": -245900,
                        "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": -8.151e-15,
                        "tr_5760_estimates_str": "-8.151e-15", "tr_5760_log_adjusted_pvalues": -2.407,
                        "tr_5760_log_adjusted_pvalues_str": "-2.407", "tr_5760_pvalues": 0.000006786,
                        "tr_5760_pvalues_str": "6.786e-06"},
                "352": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0064",
                        "cpd_name": "DG(36:4); DG(18:2/18:2) | DG(18:1/18:3)", "harmonised_annotation_id": "352",
                        "tr_5289_adjusted_pvalues": 6.121, "tr_5289_adjusted_pvalues_str": "6.121",
                        "tr_5289_aic": -193200, "tr_5289_aic_str": "-193200.0", "tr_5289_estimates": 1.166e-15,
                        "tr_5289_estimates_str": "1.166e-15", "tr_5289_log_adjusted_pvalues": -0.7868,
                        "tr_5289_log_adjusted_pvalues_str": "-0.7868", "tr_5289_pvalues": 0.01061,
                        "tr_5289_pvalues_str": "0.01061", "tr_5760_adjusted_pvalues": 0.8467,
                        "tr_5760_adjusted_pvalues_str": "0.8467", "tr_5760_aic": -236800,
                        "tr_5760_aic_str": "-236800.0", "tr_5760_estimates": -1.848e-14,
                        "tr_5760_estimates_str": "-1.848e-14", "tr_5760_log_adjusted_pvalues": -0.07226,
                        "tr_5760_log_adjusted_pvalues_str": "-0.07226", "tr_5760_pvalues": 0.001467,
                        "tr_5760_pvalues_str": "0.001467"},
                "353": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0372",
                        "cpd_name": "beta carotene_3", "harmonised_annotation_id": "353",
                        "tr_5289_adjusted_pvalues": 0.000002919, "tr_5289_adjusted_pvalues_str": "2.919e-06",
                        "tr_5289_aic": -181500, "tr_5289_aic_str": "-181500.0", "tr_5289_estimates": -1.836e-14,
                        "tr_5289_estimates_str": "-1.836e-14", "tr_5289_log_adjusted_pvalues": -5.535,
                        "tr_5289_log_adjusted_pvalues_str": "-5.535", "tr_5289_pvalues": 5.058e-9,
                        "tr_5289_pvalues_str": "5.058e-09", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "354": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0050",
                        "cpd_name": "Cer(d18:2/24:0)", "harmonised_annotation_id": "354",
                        "tr_5289_adjusted_pvalues": 4.682e-32, "tr_5289_adjusted_pvalues_str": "4.682e-32",
                        "tr_5289_aic": -180900, "tr_5289_aic_str": "-180900.0", "tr_5289_estimates": 4.221e-14,
                        "tr_5289_estimates_str": "4.221e-14", "tr_5289_log_adjusted_pvalues": 31.33,
                        "tr_5289_log_adjusted_pvalues_str": "31.33", "tr_5289_pvalues": 8.115e-35,
                        "tr_5289_pvalues_str": "8.115e-35", "tr_5760_adjusted_pvalues": 7.814e-43,
                        "tr_5760_adjusted_pvalues_str": "7.814e-43", "tr_5760_aic": -243900,
                        "tr_5760_aic_str": "-243900.0", "tr_5760_estimates": 3.154e-14,
                        "tr_5760_estimates_str": "3.154e-14", "tr_5760_log_adjusted_pvalues": 42.11,
                        "tr_5760_log_adjusted_pvalues_str": "42.11", "tr_5760_pvalues": 1.354e-45,
                        "tr_5760_pvalues_str": "1.354e-45"},
                "355": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0244",
                        "cpd_name": "LPC(0:0/22:5)_1", "harmonised_annotation_id": "355",
                        "tr_5289_adjusted_pvalues": 6.923e-28, "tr_5289_adjusted_pvalues_str": "6.923e-28",
                        "tr_5289_aic": -176800, "tr_5289_aic_str": "-176800.0", "tr_5289_estimates": -7.929e-14,
                        "tr_5289_estimates_str": "-7.929e-14", "tr_5289_log_adjusted_pvalues": -27.16,
                        "tr_5289_log_adjusted_pvalues_str": "-27.16", "tr_5289_pvalues": 1.2e-30,
                        "tr_5289_pvalues_str": "1.2e-30", "tr_5760_adjusted_pvalues": 4.318e-30,
                        "tr_5760_adjusted_pvalues_str": "4.318e-30", "tr_5760_aic": -246000,
                        "tr_5760_aic_str": "-246000.0", "tr_5760_estimates": 2.072e-14,
                        "tr_5760_estimates_str": "2.072e-14", "tr_5760_log_adjusted_pvalues": 29.36,
                        "tr_5760_log_adjusted_pvalues_str": "29.36", "tr_5760_pvalues": 7.483e-33,
                        "tr_5760_pvalues_str": "7.483e-33"},
                "357": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0264",
                        "cpd_name": "PC(33:1); PC(15:0/18:1) | PC(16:0/17:1)", "harmonised_annotation_id": "357",
                        "tr_5289_adjusted_pvalues": 0.0001238, "tr_5289_adjusted_pvalues_str": "0.0001238",
                        "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": 7.752e-15,
                        "tr_5289_estimates_str": "7.752e-15", "tr_5289_log_adjusted_pvalues": 3.907,
                        "tr_5289_log_adjusted_pvalues_str": "3.907", "tr_5289_pvalues": 2.145e-7,
                        "tr_5289_pvalues_str": "2.145e-07", "tr_5760_adjusted_pvalues": 5.948e-12,
                        "tr_5760_adjusted_pvalues_str": "5.948e-12", "tr_5760_aic": -233500,
                        "tr_5760_aic_str": "-233500.0", "tr_5760_estimates": -6.225e-14,
                        "tr_5760_estimates_str": "-6.225e-14", "tr_5760_log_adjusted_pvalues": -11.23,
                        "tr_5760_log_adjusted_pvalues_str": "-11.23", "tr_5760_pvalues": 1.031e-14,
                        "tr_5760_pvalues_str": "1.031e-14"},
                "358": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0299", "cpd_name": "TG(46:3)",
                        "harmonised_annotation_id": "358", "tr_5289_adjusted_pvalues": 4.176e-9,
                        "tr_5289_adjusted_pvalues_str": "4.176e-09", "tr_5289_aic": -179400,
                        "tr_5289_aic_str": "-179400.0", "tr_5289_estimates": -3.096e-14,
                        "tr_5289_estimates_str": "-3.096e-14", "tr_5289_log_adjusted_pvalues": -8.379,
                        "tr_5289_log_adjusted_pvalues_str": "-8.379", "tr_5289_pvalues": 7.238e-12,
                        "tr_5289_pvalues_str": "7.238e-12", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "360": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0348", "cpd_name": "TG(58:1)",
                        "harmonised_annotation_id": "360", "tr_5289_adjusted_pvalues": 0.6714,
                        "tr_5289_adjusted_pvalues_str": "0.6714", "tr_5289_aic": -185100,
                        "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": 6.072e-15,
                        "tr_5289_estimates_str": "6.072e-15", "tr_5289_log_adjusted_pvalues": 0.173,
                        "tr_5289_log_adjusted_pvalues_str": "0.173", "tr_5289_pvalues": 0.001164,
                        "tr_5289_pvalues_str": "0.001164", "tr_5760_adjusted_pvalues": 0.02561,
                        "tr_5760_adjusted_pvalues_str": "0.02561", "tr_5760_aic": -241800,
                        "tr_5760_aic_str": "-241800.0", "tr_5760_estimates": -1.31e-14,
                        "tr_5760_estimates_str": "-1.31e-14", "tr_5760_log_adjusted_pvalues": -1.592,
                        "tr_5760_log_adjusted_pvalues_str": "-1.592", "tr_5760_pvalues": 0.00004438,
                        "tr_5760_pvalues_str": "4.438e-05"},
                "365": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0108", "cpd_name": "LPC(22:0/0:0)",
                        "harmonised_annotation_id": "365", "tr_5289_adjusted_pvalues": 7.467,
                        "tr_5289_adjusted_pvalues_str": "7.467", "tr_5289_aic": -193100, "tr_5289_aic_str": "-193100.0",
                        "tr_5289_estimates": 1.095e-15, "tr_5289_estimates_str": "1.095e-15",
                        "tr_5289_log_adjusted_pvalues": -0.8732, "tr_5289_log_adjusted_pvalues_str": "-0.8732",
                        "tr_5289_pvalues": 0.01294, "tr_5289_pvalues_str": "0.01294",
                        "tr_5760_adjusted_pvalues": 0.6673, "tr_5760_adjusted_pvalues_str": "0.6673",
                        "tr_5760_aic": -246200, "tr_5760_aic_str": "-246200.0", "tr_5760_estimates": 5.483e-15,
                        "tr_5760_estimates_str": "5.483e-15", "tr_5760_log_adjusted_pvalues": 0.1757,
                        "tr_5760_log_adjusted_pvalues_str": "0.1757", "tr_5760_pvalues": 0.001157,
                        "tr_5760_pvalues_str": "0.001157"},
                "366": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0230", "cpd_name": "CAR(16:2)",
                        "harmonised_annotation_id": "366", "tr_5289_adjusted_pvalues": 0.3173,
                        "tr_5289_adjusted_pvalues_str": "0.3173", "tr_5289_aic": -175800,
                        "tr_5289_aic_str": "-175800.0", "tr_5289_estimates": 2.87e-14,
                        "tr_5289_estimates_str": "2.87e-14", "tr_5289_log_adjusted_pvalues": 0.4986,
                        "tr_5289_log_adjusted_pvalues_str": "0.4986", "tr_5289_pvalues": 0.0005499,
                        "tr_5289_pvalues_str": "0.0005499", "tr_5760_adjusted_pvalues": 0.0005463,
                        "tr_5760_adjusted_pvalues_str": "0.0005463", "tr_5760_aic": -230600,
                        "tr_5760_aic_str": "-230600.0", "tr_5760_estimates": 6.396e-14,
                        "tr_5760_estimates_str": "6.396e-14", "tr_5760_log_adjusted_pvalues": 3.263,
                        "tr_5760_log_adjusted_pvalues_str": "3.263", "tr_5760_pvalues": 9.467e-7,
                        "tr_5760_pvalues_str": "9.467e-07"},
                "367": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0314", "cpd_name": "TG(52:5)_3",
                        "harmonised_annotation_id": "367", "tr_5289_adjusted_pvalues": 5.938e-19,
                        "tr_5289_adjusted_pvalues_str": "5.938e-19", "tr_5289_aic": -175500,
                        "tr_5289_aic_str": "-175500.0", "tr_5289_estimates": 8.771e-14,
                        "tr_5289_estimates_str": "8.771e-14", "tr_5289_log_adjusted_pvalues": 18.23,
                        "tr_5289_log_adjusted_pvalues_str": "18.23", "tr_5289_pvalues": 1.029e-21,
                        "tr_5289_pvalues_str": "1.029e-21", "tr_5760_adjusted_pvalues": 2.522e-20,
                        "tr_5760_adjusted_pvalues_str": "2.522e-20", "tr_5760_aic": -242400,
                        "tr_5760_aic_str": "-242400.0", "tr_5760_estimates": 2.906e-14,
                        "tr_5760_estimates_str": "2.906e-14", "tr_5760_log_adjusted_pvalues": 19.6,
                        "tr_5760_log_adjusted_pvalues_str": "19.6", "tr_5760_pvalues": 4.37e-23,
                        "tr_5760_pvalues_str": "4.37e-23"},
                "368": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0291",
                        "cpd_name": "SM(d19:1/18:0)", "harmonised_annotation_id": "368",
                        "tr_5289_adjusted_pvalues": 4.47e-12, "tr_5289_adjusted_pvalues_str": "4.47e-12",
                        "tr_5289_aic": -193000, "tr_5289_aic_str": "-193000.0", "tr_5289_estimates": 3.485e-15,
                        "tr_5289_estimates_str": "3.485e-15", "tr_5289_log_adjusted_pvalues": 11.35,
                        "tr_5289_log_adjusted_pvalues_str": "11.35", "tr_5289_pvalues": 7.747e-15,
                        "tr_5289_pvalues_str": "7.747e-15", "tr_5760_adjusted_pvalues": 2.508e-24,
                        "tr_5760_adjusted_pvalues_str": "2.508e-24", "tr_5760_aic": -242400,
                        "tr_5760_aic_str": "-242400.0", "tr_5760_estimates": 2.953e-14,
                        "tr_5760_estimates_str": "2.953e-14", "tr_5760_log_adjusted_pvalues": 23.6,
                        "tr_5760_log_adjusted_pvalues_str": "23.6", "tr_5760_pvalues": 4.347e-27,
                        "tr_5760_pvalues_str": "4.347e-27"},
                "371": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0228", "cpd_name": "TG(54:6)_2",
                        "harmonised_annotation_id": "371", "tr_5289_adjusted_pvalues": 7.125e-26,
                        "tr_5289_adjusted_pvalues_str": "7.125e-26", "tr_5289_aic": -172000,
                        "tr_5289_aic_str": "-172000.0", "tr_5289_estimates": -1.842e-13,
                        "tr_5289_estimates_str": "-1.842e-13", "tr_5289_log_adjusted_pvalues": -25.15,
                        "tr_5289_log_adjusted_pvalues_str": "-25.15", "tr_5289_pvalues": 1.235e-28,
                        "tr_5289_pvalues_str": "1.235e-28", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "373": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0218", "cpd_name": "TG(52:2)",
                        "harmonised_annotation_id": "373", "tr_5289_adjusted_pvalues": 0.00000328,
                        "tr_5289_adjusted_pvalues_str": "3.28e-06", "tr_5289_aic": -177700,
                        "tr_5289_aic_str": "-177700.0", "tr_5289_estimates": -3.436e-14,
                        "tr_5289_estimates_str": "-3.436e-14", "tr_5289_log_adjusted_pvalues": -5.484,
                        "tr_5289_log_adjusted_pvalues_str": "-5.484", "tr_5289_pvalues": 5.684e-9,
                        "tr_5289_pvalues_str": "5.684e-09", "tr_5760_adjusted_pvalues": 2.017e-9,
                        "tr_5760_adjusted_pvalues_str": "2.017e-09", "tr_5760_aic": -233000,
                        "tr_5760_aic_str": "-233000.0", "tr_5760_estimates": 6.316e-14,
                        "tr_5760_estimates_str": "6.316e-14", "tr_5760_log_adjusted_pvalues": 8.695,
                        "tr_5760_log_adjusted_pvalues_str": "8.695", "tr_5760_pvalues": 3.495e-12,
                        "tr_5760_pvalues_str": "3.495e-12"},
                "375": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0253", "cpd_name": "LPE(0:0/16:0)",
                        "harmonised_annotation_id": "375", "tr_5289_adjusted_pvalues": 0.007507,
                        "tr_5289_adjusted_pvalues_str": "0.007507", "tr_5289_aic": -178000,
                        "tr_5289_aic_str": "-178000.0", "tr_5289_estimates": 2.405e-14,
                        "tr_5289_estimates_str": "2.405e-14", "tr_5289_log_adjusted_pvalues": 2.125,
                        "tr_5289_log_adjusted_pvalues_str": "2.125", "tr_5289_pvalues": 0.00001301,
                        "tr_5289_pvalues_str": "1.301e-05", "tr_5760_adjusted_pvalues": 0.01034,
                        "tr_5760_adjusted_pvalues_str": "0.01034", "tr_5760_aic": -243800,
                        "tr_5760_aic_str": "-243800.0", "tr_5760_estimates": -9.451e-15,
                        "tr_5760_estimates_str": "-9.451e-15", "tr_5760_log_adjusted_pvalues": -1.986,
                        "tr_5760_log_adjusted_pvalues_str": "-1.986", "tr_5760_pvalues": 0.00001792,
                        "tr_5760_pvalues_str": "1.792e-05"},
                "376": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0067",
                        "cpd_name": "HexCer(d18:1/22:0)", "harmonised_annotation_id": "376",
                        "tr_5289_adjusted_pvalues": 210.1, "tr_5289_adjusted_pvalues_str": "210.1",
                        "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": -1.363e-15,
                        "tr_5289_estimates_str": "-1.363e-15", "tr_5289_log_adjusted_pvalues": 2.322,
                        "tr_5289_log_adjusted_pvalues_str": "2.322", "tr_5289_pvalues": 0.3641,
                        "tr_5289_pvalues_str": "0.3641", "tr_5760_adjusted_pvalues": 529.3,
                        "tr_5760_adjusted_pvalues_str": "529.3", "tr_5760_aic": -252500, "tr_5760_aic_str": "-252500.0",
                        "tr_5760_estimates": 7.587e-17, "tr_5760_estimates_str": "7.587e-17",
                        "tr_5760_log_adjusted_pvalues": -2.724, "tr_5760_log_adjusted_pvalues_str": "-2.724",
                        "tr_5760_pvalues": 0.9173, "tr_5760_pvalues_str": "0.9173"},
                "380": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0005", "cpd_name": "CAR(10:2)",
                        "harmonised_annotation_id": "380", "tr_5289_adjusted_pvalues": 0.774,
                        "tr_5289_adjusted_pvalues_str": "0.774", "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0",
                        "tr_5289_estimates": 1.017e-14, "tr_5289_estimates_str": "1.017e-14",
                        "tr_5289_log_adjusted_pvalues": 0.1113, "tr_5289_log_adjusted_pvalues_str": "0.1113",
                        "tr_5289_pvalues": 0.001341, "tr_5289_pvalues_str": "0.001341",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "383": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0257", "cpd_name": "PC(14:0/22:6)",
                        "harmonised_annotation_id": "383", "tr_5289_adjusted_pvalues": None,
                        "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                        "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                        "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                        "tr_5760_adjusted_pvalues": 4.456e-21, "tr_5760_adjusted_pvalues_str": "4.456e-21",
                        "tr_5760_aic": -232300, "tr_5760_aic_str": "-232300.0", "tr_5760_estimates": 9.745e-14,
                        "tr_5760_estimates_str": "9.745e-14", "tr_5760_log_adjusted_pvalues": 20.35,
                        "tr_5760_log_adjusted_pvalues_str": "20.35", "tr_5760_pvalues": 7.723e-24,
                        "tr_5760_pvalues_str": "7.723e-24"},
                "384": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0089", "cpd_name": "LPC(15:0/0:0)",
                        "harmonised_annotation_id": "384", "tr_5289_adjusted_pvalues": 242.6,
                        "tr_5289_adjusted_pvalues_str": "242.6", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                        "tr_5289_estimates": -7.665e-16, "tr_5289_estimates_str": "-7.665e-16",
                        "tr_5289_log_adjusted_pvalues": 2.385, "tr_5289_log_adjusted_pvalues_str": "2.385",
                        "tr_5289_pvalues": 0.4204, "tr_5289_pvalues_str": "0.4204", "tr_5760_adjusted_pvalues": 343.2,
                        "tr_5760_adjusted_pvalues_str": "343.2", "tr_5760_aic": -242600, "tr_5760_aic_str": "-242600.0",
                        "tr_5760_estimates": -1.478e-15, "tr_5760_estimates_str": "-1.478e-15",
                        "tr_5760_log_adjusted_pvalues": 2.536, "tr_5760_log_adjusted_pvalues_str": "2.536",
                        "tr_5760_pvalues": 0.5948, "tr_5760_pvalues_str": "0.5948"},
                "389": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0039",
                        "cpd_name": "Cer(d16:1/24:0)", "harmonised_annotation_id": "389",
                        "tr_5289_adjusted_pvalues": 2.081e-22, "tr_5289_adjusted_pvalues_str": "2.081e-22",
                        "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": -1.812e-14,
                        "tr_5289_estimates_str": "-1.812e-14", "tr_5289_log_adjusted_pvalues": -21.68,
                        "tr_5289_log_adjusted_pvalues_str": "-21.68", "tr_5289_pvalues": 3.607e-25,
                        "tr_5289_pvalues_str": "3.607e-25", "tr_5760_adjusted_pvalues": 8.554e-39,
                        "tr_5760_adjusted_pvalues_str": "8.554e-39", "tr_5760_aic": -236400,
                        "tr_5760_aic_str": "-236400.0", "tr_5760_estimates": -7.982e-14,
                        "tr_5760_estimates_str": "-7.982e-14", "tr_5760_log_adjusted_pvalues": -38.07,
                        "tr_5760_log_adjusted_pvalues_str": "-38.07", "tr_5760_pvalues": 1.483e-41,
                        "tr_5760_pvalues_str": "1.483e-41"},
                "390": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0172",
                        "cpd_name": "PE(O-18:1/22:6) and/or PE(P-18:0/22:6)", "harmonised_annotation_id": "390",
                        "tr_5289_adjusted_pvalues": 2.436e-11, "tr_5289_adjusted_pvalues_str": "2.436e-11",
                        "tr_5289_aic": -175900, "tr_5289_aic_str": "-175900.0", "tr_5289_estimates": 5.978e-14,
                        "tr_5289_estimates_str": "5.978e-14", "tr_5289_log_adjusted_pvalues": 10.61,
                        "tr_5289_log_adjusted_pvalues_str": "10.61", "tr_5289_pvalues": 4.222e-14,
                        "tr_5289_pvalues_str": "4.222e-14", "tr_5760_adjusted_pvalues": 4.008e-11,
                        "tr_5760_adjusted_pvalues_str": "4.008e-11", "tr_5760_aic": -241900,
                        "tr_5760_aic_str": "-241900.0", "tr_5760_estimates": -2.148e-14,
                        "tr_5760_estimates_str": "-2.148e-14", "tr_5760_log_adjusted_pvalues": -10.4,
                        "tr_5760_log_adjusted_pvalues_str": "-10.4", "tr_5760_pvalues": 6.946e-14,
                        "tr_5760_pvalues_str": "6.946e-14"},
                "392": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0331", "cpd_name": "TG(54:8)_2",
                        "harmonised_annotation_id": "392", "tr_5289_adjusted_pvalues": 1.492e-23,
                        "tr_5289_adjusted_pvalues_str": "1.492e-23", "tr_5289_aic": -179500,
                        "tr_5289_aic_str": "-179500.0", "tr_5289_estimates": -4.693e-14,
                        "tr_5289_estimates_str": "-4.693e-14", "tr_5289_log_adjusted_pvalues": -22.83,
                        "tr_5289_log_adjusted_pvalues_str": "-22.83", "tr_5289_pvalues": 2.586e-26,
                        "tr_5289_pvalues_str": "2.586e-26", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "404": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0136", "cpd_name": "PC(16:0/20:3)",
                        "harmonised_annotation_id": "404", "tr_5289_adjusted_pvalues": None,
                        "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                        "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                        "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "414": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0051",
                        "cpd_name": "Cer(d19:1/22:0)", "harmonised_annotation_id": "414",
                        "tr_5289_adjusted_pvalues": 3.135e-15, "tr_5289_adjusted_pvalues_str": "3.135e-15",
                        "tr_5289_aic": -187900, "tr_5289_aic_str": "-187900.0", "tr_5289_estimates": 9.199e-15,
                        "tr_5289_estimates_str": "9.199e-15", "tr_5289_log_adjusted_pvalues": 14.5,
                        "tr_5289_log_adjusted_pvalues_str": "14.5", "tr_5289_pvalues": 5.433e-18,
                        "tr_5289_pvalues_str": "5.433e-18", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "420": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0140", "cpd_name": "PC(16:0/20:5)",
                        "harmonised_annotation_id": "420", "tr_5289_adjusted_pvalues": 1.98e-30,
                        "tr_5289_adjusted_pvalues_str": "1.98e-30", "tr_5289_aic": -187800,
                        "tr_5289_aic_str": "-187800.0", "tr_5289_estimates": 1.333e-14,
                        "tr_5289_estimates_str": "1.333e-14", "tr_5289_log_adjusted_pvalues": 29.7,
                        "tr_5289_log_adjusted_pvalues_str": "29.7", "tr_5289_pvalues": 3.432e-33,
                        "tr_5289_pvalues_str": "3.432e-33", "tr_5760_adjusted_pvalues": 6.667e-70,
                        "tr_5760_adjusted_pvalues_str": "6.667e-70", "tr_5760_aic": -238100,
                        "tr_5760_aic_str": "-238100.0", "tr_5760_estimates": 8.691e-14,
                        "tr_5760_estimates_str": "8.691e-14", "tr_5760_log_adjusted_pvalues": 69.18,
                        "tr_5760_log_adjusted_pvalues_str": "69.18", "tr_5760_pvalues": 1.155e-72,
                        "tr_5760_pvalues_str": "1.155e-72"},
                "422": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0055", "cpd_name": "Cholesterol",
                        "harmonised_annotation_id": "422", "tr_5289_adjusted_pvalues": 1.238e-43,
                        "tr_5289_adjusted_pvalues_str": "1.238e-43", "tr_5289_aic": -183600,
                        "tr_5289_aic_str": "-183600.0", "tr_5289_estimates": 3.053e-14,
                        "tr_5289_estimates_str": "3.053e-14", "tr_5289_log_adjusted_pvalues": 42.91,
                        "tr_5289_log_adjusted_pvalues_str": "42.91", "tr_5289_pvalues": 2.146e-46,
                        "tr_5289_pvalues_str": "2.146e-46", "tr_5760_adjusted_pvalues": 2.878e-54,
                        "tr_5760_adjusted_pvalues_str": "2.878e-54", "tr_5760_aic": -246000,
                        "tr_5760_aic_str": "-246000.0", "tr_5760_estimates": -2.669e-14,
                        "tr_5760_estimates_str": "-2.669e-14", "tr_5760_log_adjusted_pvalues": -53.54,
                        "tr_5760_log_adjusted_pvalues_str": "-53.54", "tr_5760_pvalues": 4.988e-57,
                        "tr_5760_pvalues_str": "4.988e-57"},
                "426": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0156", "cpd_name": "PC(18:2/18:2)",
                        "harmonised_annotation_id": "426", "tr_5289_adjusted_pvalues": 2.987,
                        "tr_5289_adjusted_pvalues_str": "2.987", "tr_5289_aic": -174500, "tr_5289_aic_str": "-174500.0",
                        "tr_5289_estimates": 2.718e-14, "tr_5289_estimates_str": "2.718e-14",
                        "tr_5289_log_adjusted_pvalues": -0.4753, "tr_5289_log_adjusted_pvalues_str": "-0.4753",
                        "tr_5289_pvalues": 0.005177, "tr_5289_pvalues_str": "0.005177",
                        "tr_5760_adjusted_pvalues": 0.2177, "tr_5760_adjusted_pvalues_str": "0.2177",
                        "tr_5760_aic": -239300, "tr_5760_aic_str": "-239300.0", "tr_5760_estimates": -1.37e-14,
                        "tr_5760_estimates_str": "-1.37e-14", "tr_5760_log_adjusted_pvalues": -0.6622,
                        "tr_5760_log_adjusted_pvalues_str": "-0.6622", "tr_5760_pvalues": 0.0003773,
                        "tr_5760_pvalues_str": "0.0003773"},
                "427": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0242",
                        "cpd_name": "HEXCer(d18:1/23:0)", "harmonised_annotation_id": "427",
                        "tr_5289_adjusted_pvalues": 3.914e-10, "tr_5289_adjusted_pvalues_str": "3.914e-10",
                        "tr_5289_aic": -174400, "tr_5289_aic_str": "-174400.0", "tr_5289_estimates": 7.267e-14,
                        "tr_5289_estimates_str": "7.267e-14", "tr_5289_log_adjusted_pvalues": 9.407,
                        "tr_5289_log_adjusted_pvalues_str": "9.407", "tr_5289_pvalues": 6.783e-13,
                        "tr_5289_pvalues_str": "6.783e-13", "tr_5760_adjusted_pvalues": 0.001305,
                        "tr_5760_adjusted_pvalues_str": "0.001305", "tr_5760_aic": -249200,
                        "tr_5760_aic_str": "-249200.0", "tr_5760_estimates": -5.299e-15,
                        "tr_5760_estimates_str": "-5.299e-15", "tr_5760_log_adjusted_pvalues": -2.885,
                        "tr_5760_log_adjusted_pvalues_str": "-2.885", "tr_5760_pvalues": 0.000002261,
                        "tr_5760_pvalues_str": "2.261e-06"},
                "430": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0072", "cpd_name": "LPA(16:0/0:0)",
                        "harmonised_annotation_id": "430", "tr_5289_adjusted_pvalues": 0.7804,
                        "tr_5289_adjusted_pvalues_str": "0.7804", "tr_5289_aic": -181500,
                        "tr_5289_aic_str": "-181500.0", "tr_5289_estimates": 1.089e-14,
                        "tr_5289_estimates_str": "1.089e-14", "tr_5289_log_adjusted_pvalues": 0.1077,
                        "tr_5289_log_adjusted_pvalues_str": "0.1077", "tr_5289_pvalues": 0.001352,
                        "tr_5289_pvalues_str": "0.001352", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "432": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0075", "cpd_name": "LPA(20:4/0:0)",
                        "harmonised_annotation_id": "432", "tr_5289_adjusted_pvalues": 0.0000176,
                        "tr_5289_adjusted_pvalues_str": "1.76e-05", "tr_5289_aic": -182300,
                        "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": -1.504e-14,
                        "tr_5289_estimates_str": "-1.504e-14", "tr_5289_log_adjusted_pvalues": -4.754,
                        "tr_5289_log_adjusted_pvalues_str": "-4.754", "tr_5289_pvalues": 3.05e-8,
                        "tr_5289_pvalues_str": "3.05e-08", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "434": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0113",
                        "cpd_name": "LPC(O-18:0/0:0)", "harmonised_annotation_id": "434",
                        "tr_5289_adjusted_pvalues": 33.16, "tr_5289_adjusted_pvalues_str": "33.16",
                        "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": -7.407e-15,
                        "tr_5289_estimates_str": "-7.407e-15", "tr_5289_log_adjusted_pvalues": 1.521,
                        "tr_5289_log_adjusted_pvalues_str": "1.521", "tr_5289_pvalues": 0.05748,
                        "tr_5289_pvalues_str": "0.05748", "tr_5760_adjusted_pvalues": 1.722,
                        "tr_5760_adjusted_pvalues_str": "1.722", "tr_5760_aic": -242700, "tr_5760_aic_str": "-242700.0",
                        "tr_5760_estimates": 7.515e-15, "tr_5760_estimates_str": "7.515e-15",
                        "tr_5760_log_adjusted_pvalues": -0.236, "tr_5760_log_adjusted_pvalues_str": "-0.236",
                        "tr_5760_pvalues": 0.002984, "tr_5760_pvalues_str": "0.002984"},
                "436": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0082", "cpd_name": "LPC(0:0/18:2)",
                        "harmonised_annotation_id": "436", "tr_5289_adjusted_pvalues": None,
                        "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                        "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                        "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                        "tr_5760_adjusted_pvalues": 0.5067, "tr_5760_adjusted_pvalues_str": "0.5067",
                        "tr_5760_aic": -236800, "tr_5760_aic_str": "-236800.0", "tr_5760_estimates": -1.825e-14,
                        "tr_5760_estimates_str": "-1.825e-14", "tr_5760_log_adjusted_pvalues": -0.2953,
                        "tr_5760_log_adjusted_pvalues_str": "-0.2953", "tr_5760_pvalues": 0.0008781,
                        "tr_5760_pvalues_str": "0.0008781"},
                "444": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0322", "cpd_name": "TG(53:4)",
                        "harmonised_annotation_id": "444", "tr_5289_adjusted_pvalues": 16.19,
                        "tr_5289_adjusted_pvalues_str": "16.19", "tr_5289_aic": -185600, "tr_5289_aic_str": "-185600.0",
                        "tr_5289_estimates": -4.169e-15, "tr_5289_estimates_str": "-4.169e-15",
                        "tr_5289_log_adjusted_pvalues": 1.209, "tr_5289_log_adjusted_pvalues_str": "1.209",
                        "tr_5289_pvalues": 0.02806, "tr_5289_pvalues_str": "0.02806", "tr_5760_adjusted_pvalues": 3.315,
                        "tr_5760_adjusted_pvalues_str": "3.315", "tr_5760_aic": -245000, "tr_5760_aic_str": "-245000.0",
                        "tr_5760_estimates": 6.215e-15, "tr_5760_estimates_str": "6.215e-15",
                        "tr_5760_log_adjusted_pvalues": -0.5205, "tr_5760_log_adjusted_pvalues_str": "-0.5205",
                        "tr_5760_pvalues": 0.005745, "tr_5760_pvalues_str": "0.005745"},
                "445": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0159",
                        "cpd_name": "PC(34:0); (18:0/16:0) | PC(16:0/18:0)", "harmonised_annotation_id": "445",
                        "tr_5289_adjusted_pvalues": 4.229e-15, "tr_5289_adjusted_pvalues_str": "4.229e-15",
                        "tr_5289_aic": -186000, "tr_5289_aic_str": "-186000.0", "tr_5289_estimates": 1.238e-14,
                        "tr_5289_estimates_str": "1.238e-14", "tr_5289_log_adjusted_pvalues": 14.37,
                        "tr_5289_log_adjusted_pvalues_str": "14.37", "tr_5289_pvalues": 7.329e-18,
                        "tr_5289_pvalues_str": "7.329e-18", "tr_5760_adjusted_pvalues": 3.355e-32,
                        "tr_5760_adjusted_pvalues_str": "3.355e-32", "tr_5760_aic": -244100,
                        "tr_5760_aic_str": "-244100.0", "tr_5760_estimates": -2.684e-14,
                        "tr_5760_estimates_str": "-2.684e-14", "tr_5760_log_adjusted_pvalues": -31.47,
                        "tr_5760_log_adjusted_pvalues_str": "-31.47", "tr_5760_pvalues": 5.814e-35,
                        "tr_5760_pvalues_str": "5.814e-35"},
                "448": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0194",
                        "cpd_name": "SM(d18:2/23:0)", "harmonised_annotation_id": "448",
                        "tr_5289_adjusted_pvalues": 8.934e-20, "tr_5289_adjusted_pvalues_str": "8.934e-20",
                        "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": -1.649e-14,
                        "tr_5289_estimates_str": "-1.649e-14", "tr_5289_log_adjusted_pvalues": -19.05,
                        "tr_5289_log_adjusted_pvalues_str": "-19.05", "tr_5289_pvalues": 1.548e-22,
                        "tr_5289_pvalues_str": "1.548e-22", "tr_5760_adjusted_pvalues": 2.378e-24,
                        "tr_5760_adjusted_pvalues_str": "2.378e-24", "tr_5760_aic": -245900,
                        "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": 1.879e-14,
                        "tr_5760_estimates_str": "1.879e-14", "tr_5760_log_adjusted_pvalues": 23.62,
                        "tr_5760_log_adjusted_pvalues_str": "23.62", "tr_5760_pvalues": 4.121e-27,
                        "tr_5760_pvalues_str": "4.121e-27"},
                "454": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0133", "cpd_name": "PC(16:0/18:2)",
                        "harmonised_annotation_id": "454", "tr_5289_adjusted_pvalues": 78.66,
                        "tr_5289_adjusted_pvalues_str": "78.66", "tr_5289_aic": -178000, "tr_5289_aic_str": "-178000.0",
                        "tr_5289_estimates": 7.681e-15, "tr_5289_estimates_str": "7.681e-15",
                        "tr_5289_log_adjusted_pvalues": -1.896, "tr_5289_log_adjusted_pvalues_str": "-1.896",
                        "tr_5289_pvalues": 0.1363, "tr_5289_pvalues_str": "0.1363", "tr_5760_adjusted_pvalues": 82.9,
                        "tr_5760_adjusted_pvalues_str": "82.9", "tr_5760_aic": -241900, "tr_5760_aic_str": "-241900.0",
                        "tr_5760_estimates": 3.911e-15, "tr_5760_estimates_str": "3.911e-15",
                        "tr_5760_log_adjusted_pvalues": -1.919, "tr_5760_log_adjusted_pvalues_str": "-1.919",
                        "tr_5760_pvalues": 0.1437, "tr_5760_pvalues_str": "0.1437"},
                "458": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0196",
                        "cpd_name": "SM(d18:2/24:1)", "harmonised_annotation_id": "458",
                        "tr_5289_adjusted_pvalues": 129.7, "tr_5289_adjusted_pvalues_str": "129.7",
                        "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0", "tr_5289_estimates": -1.941e-15,
                        "tr_5289_estimates_str": "-1.941e-15", "tr_5289_log_adjusted_pvalues": 2.113,
                        "tr_5289_log_adjusted_pvalues_str": "2.113", "tr_5289_pvalues": 0.2248,
                        "tr_5289_pvalues_str": "0.2248", "tr_5760_adjusted_pvalues": 0.002186,
                        "tr_5760_adjusted_pvalues_str": "0.002186", "tr_5760_aic": -241800,
                        "tr_5760_aic_str": "-241800.0", "tr_5760_estimates": -1.361e-14,
                        "tr_5760_estimates_str": "-1.361e-14", "tr_5760_log_adjusted_pvalues": -2.66,
                        "tr_5760_log_adjusted_pvalues_str": "-2.66", "tr_5760_pvalues": 0.000003789,
                        "tr_5760_pvalues_str": "3.789e-06"},
                "459": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0124", "cpd_name": "MG(18:1)_1",
                        "harmonised_annotation_id": "459", "tr_5289_adjusted_pvalues": 8.29e-12,
                        "tr_5289_adjusted_pvalues_str": "8.29e-12", "tr_5289_aic": -180100,
                        "tr_5289_aic_str": "-180100.0", "tr_5289_estimates": 3.13e-14,
                        "tr_5289_estimates_str": "3.13e-14", "tr_5289_log_adjusted_pvalues": 11.08,
                        "tr_5289_log_adjusted_pvalues_str": "11.08", "tr_5289_pvalues": 1.437e-14,
                        "tr_5289_pvalues_str": "1.437e-14", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "461": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0358", "cpd_name": "TG(58:7)_2",
                        "harmonised_annotation_id": "461", "tr_5289_adjusted_pvalues": 6.046e-7,
                        "tr_5289_adjusted_pvalues_str": "6.046e-07", "tr_5289_aic": -185200,
                        "tr_5289_aic_str": "-185200.0", "tr_5289_estimates": 1.044e-14,
                        "tr_5289_estimates_str": "1.044e-14", "tr_5289_log_adjusted_pvalues": 6.219,
                        "tr_5289_log_adjusted_pvalues_str": "6.219", "tr_5289_pvalues": 1.048e-9,
                        "tr_5289_pvalues_str": "1.048e-09", "tr_5760_adjusted_pvalues": 4.252e-13,
                        "tr_5760_adjusted_pvalues_str": "4.252e-13", "tr_5760_aic": -238600,
                        "tr_5760_aic_str": "-238600.0", "tr_5760_estimates": 3.594e-14,
                        "tr_5760_estimates_str": "3.594e-14", "tr_5760_log_adjusted_pvalues": 12.37,
                        "tr_5760_log_adjusted_pvalues_str": "12.37", "tr_5760_pvalues": 7.369e-16,
                        "tr_5760_pvalues_str": "7.369e-16"},
                "466": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0297", "cpd_name": "TG(42:1)",
                        "harmonised_annotation_id": "466", "tr_5289_adjusted_pvalues": 0.00026,
                        "tr_5289_adjusted_pvalues_str": "0.00026", "tr_5289_aic": -180800,
                        "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -1.845e-14,
                        "tr_5289_estimates_str": "-1.845e-14", "tr_5289_log_adjusted_pvalues": -3.585,
                        "tr_5289_log_adjusted_pvalues_str": "-3.585", "tr_5289_pvalues": 4.507e-7,
                        "tr_5289_pvalues_str": "4.507e-07", "tr_5760_adjusted_pvalues": 0.001882,
                        "tr_5760_adjusted_pvalues_str": "0.001882", "tr_5760_aic": -236800,
                        "tr_5760_aic_str": "-236800.0", "tr_5760_estimates": -2.729e-14,
                        "tr_5760_estimates_str": "-2.729e-14", "tr_5760_log_adjusted_pvalues": -2.725,
                        "tr_5760_log_adjusted_pvalues_str": "-2.725", "tr_5760_pvalues": 0.000003261,
                        "tr_5760_pvalues_str": "3.261e-06"},
                "467": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0222", "cpd_name": "TG(52:4)_2",
                        "harmonised_annotation_id": "467", "tr_5289_adjusted_pvalues": 7.786e-8,
                        "tr_5289_adjusted_pvalues_str": "7.786e-08", "tr_5289_aic": -185100,
                        "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": 1.152e-14,
                        "tr_5289_estimates_str": "1.152e-14", "tr_5289_log_adjusted_pvalues": 7.109,
                        "tr_5289_log_adjusted_pvalues_str": "7.109", "tr_5289_pvalues": 1.349e-10,
                        "tr_5289_pvalues_str": "1.349e-10", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "468": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0141", "cpd_name": "PC(16:0/22:4)",
                        "harmonised_annotation_id": "468", "tr_5289_adjusted_pvalues": 2.132,
                        "tr_5289_adjusted_pvalues_str": "2.132", "tr_5289_aic": -183600, "tr_5289_aic_str": "-183600.0",
                        "tr_5289_estimates": 6.124e-15, "tr_5289_estimates_str": "6.124e-15",
                        "tr_5289_log_adjusted_pvalues": -0.3289, "tr_5289_log_adjusted_pvalues_str": "-0.3289",
                        "tr_5289_pvalues": 0.003696, "tr_5289_pvalues_str": "0.003696",
                        "tr_5760_adjusted_pvalues": 2.223, "tr_5760_adjusted_pvalues_str": "2.223",
                        "tr_5760_aic": -233500, "tr_5760_aic_str": "-233500.0", "tr_5760_estimates": -2.327e-14,
                        "tr_5760_estimates_str": "-2.327e-14", "tr_5760_log_adjusted_pvalues": 0.347,
                        "tr_5760_log_adjusted_pvalues_str": "0.347", "tr_5760_pvalues": 0.003853,
                        "tr_5760_pvalues_str": "0.003853"},
                "471": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0192",
                        "cpd_name": "SM(d18:2/18:0)", "harmonised_annotation_id": "471",
                        "tr_5289_adjusted_pvalues": 0.6012, "tr_5289_adjusted_pvalues_str": "0.6012",
                        "tr_5289_aic": -177700, "tr_5289_aic_str": "-177700.0", "tr_5289_estimates": 1.893e-14,
                        "tr_5289_estimates_str": "1.893e-14", "tr_5289_log_adjusted_pvalues": 0.2209,
                        "tr_5289_log_adjusted_pvalues_str": "0.2209", "tr_5289_pvalues": 0.001042,
                        "tr_5289_pvalues_str": "0.001042", "tr_5760_adjusted_pvalues": 0.0001904,
                        "tr_5760_adjusted_pvalues_str": "0.0001904", "tr_5760_aic": -235100,
                        "tr_5760_aic_str": "-235100.0", "tr_5760_estimates": -3.413e-14,
                        "tr_5760_estimates_str": "-3.413e-14", "tr_5760_log_adjusted_pvalues": -3.72,
                        "tr_5760_log_adjusted_pvalues_str": "-3.72", "tr_5760_pvalues": 3.299e-7,
                        "tr_5760_pvalues_str": "3.299e-07"},
                "472": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0256", "cpd_name": "LPE(20:4/0:0)",
                        "harmonised_annotation_id": "472", "tr_5289_adjusted_pvalues": 2.059,
                        "tr_5289_adjusted_pvalues_str": "2.059", "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0",
                        "tr_5289_estimates": -4.753e-15, "tr_5289_estimates_str": "-4.753e-15",
                        "tr_5289_log_adjusted_pvalues": 0.3137, "tr_5289_log_adjusted_pvalues_str": "0.3137",
                        "tr_5289_pvalues": 0.003569, "tr_5289_pvalues_str": "0.003569",
                        "tr_5760_adjusted_pvalues": 0.2447, "tr_5760_adjusted_pvalues_str": "0.2447",
                        "tr_5760_aic": -233500, "tr_5760_aic_str": "-233500.0", "tr_5760_estimates": -2.833e-14,
                        "tr_5760_estimates_str": "-2.833e-14", "tr_5760_log_adjusted_pvalues": -0.6114,
                        "tr_5760_log_adjusted_pvalues_str": "-0.6114", "tr_5760_pvalues": 0.0004241,
                        "tr_5760_pvalues_str": "0.0004241"},
                "473": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0187",
                        "cpd_name": "SM(d18:1/24:0)", "harmonised_annotation_id": "473",
                        "tr_5289_adjusted_pvalues": 6.447e-11, "tr_5289_adjusted_pvalues_str": "6.447e-11",
                        "tr_5289_aic": -182300, "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": -1.938e-14,
                        "tr_5289_estimates_str": "-1.938e-14", "tr_5289_log_adjusted_pvalues": -10.19,
                        "tr_5289_log_adjusted_pvalues_str": "-10.19", "tr_5289_pvalues": 1.117e-13,
                        "tr_5289_pvalues_str": "1.117e-13", "tr_5760_adjusted_pvalues": 3.006e-17,
                        "tr_5760_adjusted_pvalues_str": "3.006e-17", "tr_5760_aic": -240800,
                        "tr_5760_aic_str": "-240800.0", "tr_5760_estimates": -2.956e-14,
                        "tr_5760_estimates_str": "-2.956e-14", "tr_5760_log_adjusted_pvalues": -16.52,
                        "tr_5760_log_adjusted_pvalues_str": "-16.52", "tr_5760_pvalues": 5.209e-20,
                        "tr_5760_pvalues_str": "5.209e-20"},
                "474": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0163",
                        "cpd_name": "PC(O-16:0/18:2)", "harmonised_annotation_id": "474",
                        "tr_5289_adjusted_pvalues": 0.04019, "tr_5289_adjusted_pvalues_str": "0.04019",
                        "tr_5289_aic": -180800, "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": -1.367e-14,
                        "tr_5289_estimates_str": "-1.367e-14", "tr_5289_log_adjusted_pvalues": -1.396,
                        "tr_5289_log_adjusted_pvalues_str": "-1.396", "tr_5289_pvalues": 0.00006965,
                        "tr_5289_pvalues_str": "6.965e-05", "tr_5760_adjusted_pvalues": 0.005181,
                        "tr_5760_adjusted_pvalues_str": "0.005181", "tr_5760_aic": -235600,
                        "tr_5760_aic_str": "-235600.0", "tr_5760_estimates": 2.764e-14,
                        "tr_5760_estimates_str": "2.764e-14", "tr_5760_log_adjusted_pvalues": 2.286,
                        "tr_5760_log_adjusted_pvalues_str": "2.286", "tr_5760_pvalues": 0.000008978,
                        "tr_5760_pvalues_str": "8.978e-06"},
                "481": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0376",
                        "cpd_name": "LacCer(d18:1/22:0)", "harmonised_annotation_id": "481",
                        "tr_5289_adjusted_pvalues": 406, "tr_5289_adjusted_pvalues_str": "406.0",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -3.319e-16,
                        "tr_5289_estimates_str": "-3.319e-16", "tr_5289_log_adjusted_pvalues": 2.609,
                        "tr_5289_log_adjusted_pvalues_str": "2.609", "tr_5289_pvalues": 0.7036,
                        "tr_5289_pvalues_str": "0.7036", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "484": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0282",
                        "cpd_name": "PC(O-24:1/20:4) and/or PC(P-24:0/20:4)", "harmonised_annotation_id": "484",
                        "tr_5289_adjusted_pvalues": 7.265e-16, "tr_5289_adjusted_pvalues_str": "7.265e-16",
                        "tr_5289_aic": -180500, "tr_5289_aic_str": "-180500.0", "tr_5289_estimates": -3.221e-14,
                        "tr_5289_estimates_str": "-3.221e-14", "tr_5289_log_adjusted_pvalues": -15.14,
                        "tr_5289_log_adjusted_pvalues_str": "-15.14", "tr_5289_pvalues": 1.259e-18,
                        "tr_5289_pvalues_str": "1.259e-18", "tr_5760_adjusted_pvalues": 1.444e-15,
                        "tr_5760_adjusted_pvalues_str": "1.444e-15", "tr_5760_aic": -232000,
                        "tr_5760_aic_str": "-232000.0", "tr_5760_estimates": 8.628e-14,
                        "tr_5760_estimates_str": "8.628e-14", "tr_5760_log_adjusted_pvalues": 14.84,
                        "tr_5760_log_adjusted_pvalues_str": "14.84", "tr_5760_pvalues": 2.503e-18,
                        "tr_5760_pvalues_str": "2.503e-18"},
                "486": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0057", "cpd_name": "DG(16:0/18:1)",
                        "harmonised_annotation_id": "486", "tr_5289_adjusted_pvalues": 9.903,
                        "tr_5289_adjusted_pvalues_str": "9.903", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                        "tr_5289_estimates": -2.298e-15, "tr_5289_estimates_str": "-2.298e-15",
                        "tr_5289_log_adjusted_pvalues": 0.9958, "tr_5289_log_adjusted_pvalues_str": "0.9958",
                        "tr_5289_pvalues": 0.01716, "tr_5289_pvalues_str": "0.01716",
                        "tr_5760_adjusted_pvalues": 0.2236, "tr_5760_adjusted_pvalues_str": "0.2236",
                        "tr_5760_aic": -249200, "tr_5760_aic_str": "-249200.0", "tr_5760_estimates": 4.545e-15,
                        "tr_5760_estimates_str": "4.545e-15", "tr_5760_log_adjusted_pvalues": 0.6505,
                        "tr_5760_log_adjusted_pvalues_str": "0.6505", "tr_5760_pvalues": 0.0003876,
                        "tr_5760_pvalues_str": "0.0003876"},
                "488": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0200", "cpd_name": "TG(44:0)",
                        "harmonised_annotation_id": "488", "tr_5289_adjusted_pvalues": 0.00007882,
                        "tr_5289_adjusted_pvalues_str": "7.882e-05", "tr_5289_aic": -181400,
                        "tr_5289_aic_str": "-181400.0", "tr_5289_estimates": -1.726e-14,
                        "tr_5289_estimates_str": "-1.726e-14", "tr_5289_log_adjusted_pvalues": -4.103,
                        "tr_5289_log_adjusted_pvalues_str": "-4.103", "tr_5289_pvalues": 1.366e-7,
                        "tr_5289_pvalues_str": "1.366e-07", "tr_5760_adjusted_pvalues": 0.0001172,
                        "tr_5760_adjusted_pvalues_str": "0.0001172", "tr_5760_aic": -248000,
                        "tr_5760_aic_str": "-248000.0", "tr_5760_estimates": -7.285e-15,
                        "tr_5760_estimates_str": "-7.285e-15", "tr_5760_log_adjusted_pvalues": -3.931,
                        "tr_5760_log_adjusted_pvalues_str": "-3.931", "tr_5760_pvalues": 2.032e-7,
                        "tr_5760_pvalues_str": "2.032e-07"},
                "491": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0332", "cpd_name": "TG(55:2)",
                        "harmonised_annotation_id": "491", "tr_5289_adjusted_pvalues": 4.4e-9,
                        "tr_5289_adjusted_pvalues_str": "4.4e-09", "tr_5289_aic": -177700,
                        "tr_5289_aic_str": "-177700.0", "tr_5289_estimates": -4.32e-14,
                        "tr_5289_estimates_str": "-4.32e-14", "tr_5289_log_adjusted_pvalues": -8.357,
                        "tr_5289_log_adjusted_pvalues_str": "-8.357", "tr_5289_pvalues": 7.626e-12,
                        "tr_5289_pvalues_str": "7.626e-12", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "492": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0093", "cpd_name": "LPC(17:1/0:0)",
                        "harmonised_annotation_id": "492", "tr_5289_adjusted_pvalues": 1.598,
                        "tr_5289_adjusted_pvalues_str": "1.598", "tr_5289_aic": -177800, "tr_5289_aic_str": "-177800.0",
                        "tr_5289_estimates": -1.678e-14, "tr_5289_estimates_str": "-1.678e-14",
                        "tr_5289_log_adjusted_pvalues": 0.2037, "tr_5289_log_adjusted_pvalues_str": "0.2037",
                        "tr_5289_pvalues": 0.00277, "tr_5289_pvalues_str": "0.00277", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "493": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0170",
                        "cpd_name": "PE(O-18:1/18:1) and/or PE(P-18:0/18:1)", "harmonised_annotation_id": "493",
                        "tr_5289_adjusted_pvalues": 413, "tr_5289_adjusted_pvalues_str": "413.0",
                        "tr_5289_aic": -182600, "tr_5289_aic_str": "-182600.0", "tr_5289_estimates": -9.073e-16,
                        "tr_5289_estimates_str": "-9.073e-16", "tr_5289_log_adjusted_pvalues": 2.616,
                        "tr_5289_log_adjusted_pvalues_str": "2.616", "tr_5289_pvalues": 0.7157,
                        "tr_5289_pvalues_str": "0.7157", "tr_5760_adjusted_pvalues": 522,
                        "tr_5760_adjusted_pvalues_str": "522.0", "tr_5760_aic": -240000, "tr_5760_aic_str": "-240000.0",
                        "tr_5760_estimates": -4.204e-16, "tr_5760_estimates_str": "-4.204e-16",
                        "tr_5760_log_adjusted_pvalues": 2.718, "tr_5760_log_adjusted_pvalues_str": "2.718",
                        "tr_5760_pvalues": 0.9047, "tr_5760_pvalues_str": "0.9047"},
                "496": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0106", "cpd_name": "LPC(20:4/0:0)",
                        "harmonised_annotation_id": "496", "tr_5289_adjusted_pvalues": 8.421,
                        "tr_5289_adjusted_pvalues_str": "8.421", "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0",
                        "tr_5289_estimates": -4.005e-15, "tr_5289_estimates_str": "-4.005e-15",
                        "tr_5289_log_adjusted_pvalues": 0.9254, "tr_5289_log_adjusted_pvalues_str": "0.9254",
                        "tr_5289_pvalues": 0.01459, "tr_5289_pvalues_str": "0.01459", "tr_5760_adjusted_pvalues": 11.54,
                        "tr_5760_adjusted_pvalues_str": "11.54", "tr_5760_aic": -235800, "tr_5760_aic_str": "-235800.0",
                        "tr_5760_estimates": 1.429e-14, "tr_5760_estimates_str": "1.429e-14",
                        "tr_5760_log_adjusted_pvalues": -1.062, "tr_5760_log_adjusted_pvalues_str": "-1.062",
                        "tr_5760_pvalues": 0.02, "tr_5760_pvalues_str": "0.02"},
                "498": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0097", "cpd_name": "LPC(18:2/0:0)",
                        "harmonised_annotation_id": "498", "tr_5289_adjusted_pvalues": 63.15,
                        "tr_5289_adjusted_pvalues_str": "63.15", "tr_5289_aic": -184600, "tr_5289_aic_str": "-184600.0",
                        "tr_5289_estimates": -2.853e-15, "tr_5289_estimates_str": "-2.853e-15",
                        "tr_5289_log_adjusted_pvalues": 1.8, "tr_5289_log_adjusted_pvalues_str": "1.8",
                        "tr_5289_pvalues": 0.1094, "tr_5289_pvalues_str": "0.1094", "tr_5760_adjusted_pvalues": 2.834,
                        "tr_5760_adjusted_pvalues_str": "2.834", "tr_5760_aic": -236800, "tr_5760_aic_str": "-236800.0",
                        "tr_5760_estimates": -1.52e-14, "tr_5760_estimates_str": "-1.52e-14",
                        "tr_5760_log_adjusted_pvalues": 0.4524, "tr_5760_log_adjusted_pvalues_str": "0.4524",
                        "tr_5760_pvalues": 0.004911, "tr_5760_pvalues_str": "0.004911"},
                "499": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0131", "cpd_name": "PC(16:0/18:1)",
                        "harmonised_annotation_id": "499", "tr_5289_adjusted_pvalues": 0.00338,
                        "tr_5289_adjusted_pvalues_str": "0.00338", "tr_5289_aic": -177100,
                        "tr_5289_aic_str": "-177100.0", "tr_5289_estimates": 2.781e-14,
                        "tr_5289_estimates_str": "2.781e-14", "tr_5289_log_adjusted_pvalues": 2.471,
                        "tr_5289_log_adjusted_pvalues_str": "2.471", "tr_5289_pvalues": 0.000005858,
                        "tr_5289_pvalues_str": "5.858e-06", "tr_5760_adjusted_pvalues": 2.373e-7,
                        "tr_5760_adjusted_pvalues_str": "2.373e-07", "tr_5760_aic": -235700,
                        "tr_5760_aic_str": "-235700.0", "tr_5760_estimates": -3.718e-14,
                        "tr_5760_estimates_str": "-3.718e-14", "tr_5760_log_adjusted_pvalues": -6.625,
                        "tr_5760_log_adjusted_pvalues_str": "-6.625", "tr_5760_pvalues": 4.112e-10,
                        "tr_5760_pvalues_str": "4.112e-10"},
                "501": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0101", "cpd_name": "LPC(20:0/0:0)",
                        "harmonised_annotation_id": "501", "tr_5289_adjusted_pvalues": 16.45,
                        "tr_5289_adjusted_pvalues_str": "16.45", "tr_5289_aic": -179300, "tr_5289_aic_str": "-179300.0",
                        "tr_5289_estimates": 9.764e-15, "tr_5289_estimates_str": "9.764e-15",
                        "tr_5289_log_adjusted_pvalues": -1.216, "tr_5289_log_adjusted_pvalues_str": "-1.216",
                        "tr_5289_pvalues": 0.02852, "tr_5289_pvalues_str": "0.02852", "tr_5760_adjusted_pvalues": 15.95,
                        "tr_5760_adjusted_pvalues_str": "15.95", "tr_5760_aic": -242700, "tr_5760_aic_str": "-242700.0",
                        "tr_5760_estimates": -5.728e-15, "tr_5760_estimates_str": "-5.728e-15",
                        "tr_5760_log_adjusted_pvalues": 1.203, "tr_5760_log_adjusted_pvalues_str": "1.203",
                        "tr_5760_pvalues": 0.02764, "tr_5760_pvalues_str": "0.02764"},
                "502": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0096",
                        "cpd_name": "LPC(18:1/0:0)_1", "harmonised_annotation_id": "502",
                        "tr_5289_adjusted_pvalues": 93.03, "tr_5289_adjusted_pvalues_str": "93.03",
                        "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0", "tr_5289_estimates": -2.119e-15,
                        "tr_5289_estimates_str": "-2.119e-15", "tr_5289_log_adjusted_pvalues": 1.969,
                        "tr_5289_log_adjusted_pvalues_str": "1.969", "tr_5289_pvalues": 0.1612,
                        "tr_5289_pvalues_str": "0.1612", "tr_5760_adjusted_pvalues": 8.29,
                        "tr_5760_adjusted_pvalues_str": "8.29", "tr_5760_aic": -243600, "tr_5760_aic_str": "-243600.0",
                        "tr_5760_estimates": 5.494e-15, "tr_5760_estimates_str": "5.494e-15",
                        "tr_5760_log_adjusted_pvalues": -0.9185, "tr_5760_log_adjusted_pvalues_str": "-0.9185",
                        "tr_5760_pvalues": 0.01437, "tr_5760_pvalues_str": "0.01437"},
                "509": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0134", "cpd_name": "PC(16:0/18:3)",
                        "harmonised_annotation_id": "509", "tr_5289_adjusted_pvalues": 7.614e-9,
                        "tr_5289_adjusted_pvalues_str": "7.614e-09", "tr_5289_aic": -178200,
                        "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": 3.657e-14,
                        "tr_5289_estimates_str": "3.657e-14", "tr_5289_log_adjusted_pvalues": 8.118,
                        "tr_5289_log_adjusted_pvalues_str": "8.118", "tr_5289_pvalues": 1.32e-11,
                        "tr_5289_pvalues_str": "1.32e-11", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "513": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0260", "cpd_name": "PC(16:0/17:0)",
                        "harmonised_annotation_id": "513", "tr_5289_adjusted_pvalues": 0.02494,
                        "tr_5289_adjusted_pvalues_str": "0.02494", "tr_5289_aic": -189000,
                        "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": 3.525e-15,
                        "tr_5289_estimates_str": "3.525e-15", "tr_5289_log_adjusted_pvalues": 1.603,
                        "tr_5289_log_adjusted_pvalues_str": "1.603", "tr_5289_pvalues": 0.00004323,
                        "tr_5289_pvalues_str": "4.323e-05", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "514": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0038",
                        "cpd_name": "Cer(d16:1/22:0)", "harmonised_annotation_id": "514",
                        "tr_5289_adjusted_pvalues": None, "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf",
                        "tr_5289_aic_str": "inf", "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0",
                        "tr_5289_log_adjusted_pvalues": None, "tr_5289_log_adjusted_pvalues_str": None,
                        "tr_5289_pvalues": None, "tr_5289_pvalues_str": None, "tr_5760_adjusted_pvalues": 1.01e-27,
                        "tr_5760_adjusted_pvalues_str": "1.01e-27", "tr_5760_aic": -235800,
                        "tr_5760_aic_str": "-235800.0", "tr_5760_estimates": 7.325e-14,
                        "tr_5760_estimates_str": "7.325e-14", "tr_5760_log_adjusted_pvalues": 27,
                        "tr_5760_log_adjusted_pvalues_str": "27.0", "tr_5760_pvalues": 1.75e-30,
                        "tr_5760_pvalues_str": "1.75e-30"},
                "516": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0276",
                        "cpd_name": "PC(O-22:1/20:4) and/or PC(P-22:0/20:4)", "harmonised_annotation_id": "516",
                        "tr_5289_adjusted_pvalues": 1.082e-23, "tr_5289_adjusted_pvalues_str": "1.082e-23",
                        "tr_5289_aic": -172900, "tr_5289_aic_str": "-172900.0", "tr_5289_estimates": 1.426e-13,
                        "tr_5289_estimates_str": "1.426e-13", "tr_5289_log_adjusted_pvalues": 22.97,
                        "tr_5289_log_adjusted_pvalues_str": "22.97", "tr_5289_pvalues": 1.875e-26,
                        "tr_5289_pvalues_str": "1.875e-26", "tr_5760_adjusted_pvalues": 5.165e-24,
                        "tr_5760_adjusted_pvalues_str": "5.165e-24", "tr_5760_aic": -239800,
                        "tr_5760_aic_str": "-239800.0", "tr_5760_estimates": 4.112e-14,
                        "tr_5760_estimates_str": "4.112e-14", "tr_5760_log_adjusted_pvalues": 23.29,
                        "tr_5760_log_adjusted_pvalues_str": "23.29", "tr_5760_pvalues": 8.951e-27,
                        "tr_5760_pvalues_str": "8.951e-27"},
                "518": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0085", "cpd_name": "LPC(0:0/20:4)",
                        "harmonised_annotation_id": "518", "tr_5289_adjusted_pvalues": 21.43,
                        "tr_5289_adjusted_pvalues_str": "21.43", "tr_5289_aic": -183600, "tr_5289_aic_str": "-183600.0",
                        "tr_5289_estimates": 4.439e-15, "tr_5289_estimates_str": "4.439e-15",
                        "tr_5289_log_adjusted_pvalues": -1.331, "tr_5289_log_adjusted_pvalues_str": "-1.331",
                        "tr_5289_pvalues": 0.03715, "tr_5289_pvalues_str": "0.03715", "tr_5760_adjusted_pvalues": 8.081,
                        "tr_5760_adjusted_pvalues_str": "8.081", "tr_5760_aic": -246200, "tr_5760_aic_str": "-246200.0",
                        "tr_5760_estimates": 4.037e-15, "tr_5760_estimates_str": "4.037e-15",
                        "tr_5760_log_adjusted_pvalues": -0.9074, "tr_5760_log_adjusted_pvalues_str": "-0.9074",
                        "tr_5760_pvalues": 0.014, "tr_5760_pvalues_str": "0.014"},
                "519": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0121", "cpd_name": "LPE(18:2/0:0)",
                        "harmonised_annotation_id": "519", "tr_5289_adjusted_pvalues": 133.9,
                        "tr_5289_adjusted_pvalues_str": "133.9", "tr_5289_aic": -188300, "tr_5289_aic_str": "-188300.0",
                        "tr_5289_estimates": 1.152e-15, "tr_5289_estimates_str": "1.152e-15",
                        "tr_5289_log_adjusted_pvalues": -2.127, "tr_5289_log_adjusted_pvalues_str": "-2.127",
                        "tr_5289_pvalues": 0.232, "tr_5289_pvalues_str": "0.232", "tr_5760_adjusted_pvalues": 198.8,
                        "tr_5760_adjusted_pvalues_str": "198.8", "tr_5760_aic": -238900, "tr_5760_aic_str": "-238900.0",
                        "tr_5760_estimates": -3.86e-15, "tr_5760_estimates_str": "-3.86e-15",
                        "tr_5760_log_adjusted_pvalues": 2.298, "tr_5760_log_adjusted_pvalues_str": "2.298",
                        "tr_5760_pvalues": 0.3445, "tr_5760_pvalues_str": "0.3445"},
                "520": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0178",
                        "cpd_name": "SM(d17:1/24:1)", "harmonised_annotation_id": "520",
                        "tr_5289_adjusted_pvalues": 1.944e-15, "tr_5289_adjusted_pvalues_str": "1.944e-15",
                        "tr_5289_aic": -185800, "tr_5289_aic_str": "-185800.0", "tr_5289_estimates": 1.28e-14,
                        "tr_5289_estimates_str": "1.28e-14", "tr_5289_log_adjusted_pvalues": 14.71,
                        "tr_5289_log_adjusted_pvalues_str": "14.71", "tr_5289_pvalues": 3.37e-18,
                        "tr_5289_pvalues_str": "3.37e-18", "tr_5760_adjusted_pvalues": 0.001768,
                        "tr_5760_adjusted_pvalues_str": "0.001768", "tr_5760_aic": -252600,
                        "tr_5760_aic_str": "-252600.0", "tr_5760_estimates": -3.449e-15,
                        "tr_5760_estimates_str": "-3.449e-15", "tr_5760_log_adjusted_pvalues": -2.752,
                        "tr_5760_log_adjusted_pvalues_str": "-2.752", "tr_5760_pvalues": 0.000003064,
                        "tr_5760_pvalues_str": "3.064e-06"},
                "526": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0125", "cpd_name": "MG(18:1)_2",
                        "harmonised_annotation_id": "526", "tr_5289_adjusted_pvalues": 4.724e-10,
                        "tr_5289_adjusted_pvalues_str": "4.724e-10", "tr_5289_aic": -182400,
                        "tr_5289_aic_str": "-182400.0", "tr_5289_estimates": -1.966e-14,
                        "tr_5289_estimates_str": "-1.966e-14", "tr_5289_log_adjusted_pvalues": -9.326,
                        "tr_5289_log_adjusted_pvalues_str": "-9.326", "tr_5289_pvalues": 8.188e-13,
                        "tr_5289_pvalues_str": "8.188e-13", "tr_5760_adjusted_pvalues": 2.466e-14,
                        "tr_5760_adjusted_pvalues_str": "2.466e-14", "tr_5760_aic": -241900,
                        "tr_5760_aic_str": "-241900.0", "tr_5760_estimates": -2.535e-14,
                        "tr_5760_estimates_str": "-2.535e-14", "tr_5760_log_adjusted_pvalues": -13.61,
                        "tr_5760_log_adjusted_pvalues_str": "-13.61", "tr_5760_pvalues": 4.274e-17,
                        "tr_5760_pvalues_str": "4.274e-17"},
                "527": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0102", "cpd_name": "LPC(20:1/0:0)",
                        "harmonised_annotation_id": "527", "tr_5289_adjusted_pvalues": 361.4,
                        "tr_5289_adjusted_pvalues_str": "361.4", "tr_5289_aic": -185100, "tr_5289_aic_str": "-185100.0",
                        "tr_5289_estimates": 8.033e-16, "tr_5289_estimates_str": "8.033e-16",
                        "tr_5289_log_adjusted_pvalues": -2.558, "tr_5289_log_adjusted_pvalues_str": "-2.558",
                        "tr_5289_pvalues": 0.6263, "tr_5289_pvalues_str": "0.6263", "tr_5760_adjusted_pvalues": 55.49,
                        "tr_5760_adjusted_pvalues_str": "55.49", "tr_5760_aic": -232800, "tr_5760_aic_str": "-232800.0",
                        "tr_5760_estimates": -1.474e-14, "tr_5760_estimates_str": "-1.474e-14",
                        "tr_5760_log_adjusted_pvalues": 1.744, "tr_5760_log_adjusted_pvalues_str": "1.744",
                        "tr_5760_pvalues": 0.09617, "tr_5760_pvalues_str": "0.09617"},
                "528": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0098",
                        "cpd_name": "LPC(18:3/0:0)_1", "harmonised_annotation_id": "528",
                        "tr_5289_adjusted_pvalues": 311.6, "tr_5289_adjusted_pvalues_str": "311.6",
                        "tr_5289_aic": -193200, "tr_5289_aic_str": "-193200.0", "tr_5289_estimates": 2.608e-16,
                        "tr_5289_estimates_str": "2.608e-16", "tr_5289_log_adjusted_pvalues": -2.494,
                        "tr_5289_log_adjusted_pvalues_str": "-2.494", "tr_5289_pvalues": 0.54,
                        "tr_5289_pvalues_str": "0.54", "tr_5760_adjusted_pvalues": 265.7,
                        "tr_5760_adjusted_pvalues_str": "265.7", "tr_5760_aic": -241900, "tr_5760_aic_str": "-241900.0",
                        "tr_5760_estimates": 2.092e-15, "tr_5760_estimates_str": "2.092e-15",
                        "tr_5760_log_adjusted_pvalues": -2.424, "tr_5760_log_adjusted_pvalues_str": "-2.424",
                        "tr_5760_pvalues": 0.4605, "tr_5760_pvalues_str": "0.4605"},
                "533": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0239",
                        "cpd_name": "Cer(d18:0/24:0)", "harmonised_annotation_id": "533",
                        "tr_5289_adjusted_pvalues": 9.506e-7, "tr_5289_adjusted_pvalues_str": "9.506e-07",
                        "tr_5289_aic": -188100, "tr_5289_aic_str": "-188100.0", "tr_5289_estimates": 6.262e-15,
                        "tr_5289_estimates_str": "6.262e-15", "tr_5289_log_adjusted_pvalues": 6.022,
                        "tr_5289_log_adjusted_pvalues_str": "6.022", "tr_5289_pvalues": 1.647e-9,
                        "tr_5289_pvalues_str": "1.647e-09", "tr_5760_adjusted_pvalues": 6.549e-25,
                        "tr_5760_adjusted_pvalues_str": "6.549e-25", "tr_5760_aic": -237600,
                        "tr_5760_aic_str": "-237600.0", "tr_5760_estimates": -5.553e-14,
                        "tr_5760_estimates_str": "-5.553e-14", "tr_5760_log_adjusted_pvalues": -24.18,
                        "tr_5760_log_adjusted_pvalues_str": "-24.18", "tr_5760_pvalues": 1.135e-27,
                        "tr_5760_pvalues_str": "1.135e-27"},
                "535": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0245",
                        "cpd_name": "LPC(0:0/22:5)_2", "harmonised_annotation_id": "535",
                        "tr_5289_adjusted_pvalues": 0.000003412, "tr_5289_adjusted_pvalues_str": "3.412e-06",
                        "tr_5289_aic": -193100, "tr_5289_aic_str": "-193100.0", "tr_5289_estimates": 2.603e-15,
                        "tr_5289_estimates_str": "2.603e-15", "tr_5289_log_adjusted_pvalues": 5.467,
                        "tr_5289_log_adjusted_pvalues_str": "5.467", "tr_5289_pvalues": 5.913e-9,
                        "tr_5289_pvalues_str": "5.913e-09", "tr_5760_adjusted_pvalues": 1.526,
                        "tr_5760_adjusted_pvalues_str": "1.526", "tr_5760_aic": -252500, "tr_5760_aic_str": "-252500.0",
                        "tr_5760_estimates": 2.301e-15, "tr_5760_estimates_str": "2.301e-15",
                        "tr_5760_log_adjusted_pvalues": -0.1835, "tr_5760_log_adjusted_pvalues_str": "-0.1835",
                        "tr_5760_pvalues": 0.002644, "tr_5760_pvalues_str": "0.002644"},
                "536": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0269",
                        "cpd_name": "PC(O-16:0/22:5)", "harmonised_annotation_id": "536",
                        "tr_5289_adjusted_pvalues": 9.378e-32, "tr_5289_adjusted_pvalues_str": "9.378e-32",
                        "tr_5289_aic": -183500, "tr_5289_aic_str": "-183500.0", "tr_5289_estimates": 2.672e-14,
                        "tr_5289_estimates_str": "2.672e-14", "tr_5289_log_adjusted_pvalues": 31.03,
                        "tr_5289_log_adjusted_pvalues_str": "31.03", "tr_5289_pvalues": 1.625e-34,
                        "tr_5289_pvalues_str": "1.625e-34", "tr_5760_adjusted_pvalues": 4.509e-35,
                        "tr_5760_adjusted_pvalues_str": "4.509e-35", "tr_5760_aic": -235400,
                        "tr_5760_aic_str": "-235400.0", "tr_5760_estimates": -8.353e-14,
                        "tr_5760_estimates_str": "-8.353e-14", "tr_5760_log_adjusted_pvalues": -34.35,
                        "tr_5760_log_adjusted_pvalues_str": "-34.35", "tr_5760_pvalues": 7.815e-38,
                        "tr_5760_pvalues_str": "7.815e-38"},
                "537": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0191",
                        "cpd_name": "SM(d18:2/16:0)_2", "harmonised_annotation_id": "537",
                        "tr_5289_adjusted_pvalues": 3.956e-27, "tr_5289_adjusted_pvalues_str": "3.956e-27",
                        "tr_5289_aic": -187800, "tr_5289_aic_str": "-187800.0", "tr_5289_estimates": 1.277e-14,
                        "tr_5289_estimates_str": "1.277e-14", "tr_5289_log_adjusted_pvalues": 26.4,
                        "tr_5289_log_adjusted_pvalues_str": "26.4", "tr_5289_pvalues": 6.855e-30,
                        "tr_5289_pvalues_str": "6.855e-30", "tr_5760_adjusted_pvalues": 7.513e-61,
                        "tr_5760_adjusted_pvalues_str": "7.513e-61", "tr_5760_aic": -232000,
                        "tr_5760_aic_str": "-232000.0", "tr_5760_estimates": 1.778e-13,
                        "tr_5760_estimates_str": "1.778e-13", "tr_5760_log_adjusted_pvalues": 60.12,
                        "tr_5760_log_adjusted_pvalues_str": "60.12", "tr_5760_pvalues": 1.302e-63,
                        "tr_5760_pvalues_str": "1.302e-63"},
                "543": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0198",
                        "cpd_name": "SM(d35:1); SM(d17:1/18:0) | SM(d18:1/17:0)", "harmonised_annotation_id": "543",
                        "tr_5289_adjusted_pvalues": 0.01881, "tr_5289_adjusted_pvalues_str": "0.01881",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -3.549e-15,
                        "tr_5289_estimates_str": "-3.549e-15", "tr_5289_log_adjusted_pvalues": -1.726,
                        "tr_5289_log_adjusted_pvalues_str": "-1.726", "tr_5289_pvalues": 0.0000326,
                        "tr_5289_pvalues_str": "3.26e-05", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "544": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0090", "cpd_name": "LPC(16:0/0:0)",
                        "harmonised_annotation_id": "544", "tr_5289_adjusted_pvalues": 3.686,
                        "tr_5289_adjusted_pvalues_str": "3.686", "tr_5289_aic": -181400, "tr_5289_aic_str": "-181400.0",
                        "tr_5289_estimates": -6.027e-15, "tr_5289_estimates_str": "-6.027e-15",
                        "tr_5289_log_adjusted_pvalues": 0.5665, "tr_5289_log_adjusted_pvalues_str": "0.5665",
                        "tr_5289_pvalues": 0.006388, "tr_5289_pvalues_str": "0.006388",
                        "tr_5760_adjusted_pvalues": 0.272, "tr_5760_adjusted_pvalues_str": "0.272",
                        "tr_5760_aic": -233700, "tr_5760_aic_str": "-233700.0", "tr_5760_estimates": 2.112e-14,
                        "tr_5760_estimates_str": "2.112e-14", "tr_5760_log_adjusted_pvalues": 0.5654,
                        "tr_5760_log_adjusted_pvalues_str": "0.5654", "tr_5760_pvalues": 0.0004715,
                        "tr_5760_pvalues_str": "0.0004715"},
                "548": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0081", "cpd_name": "LPC(0:0/18:1)",
                        "harmonised_annotation_id": "548", "tr_5289_adjusted_pvalues": 58.01,
                        "tr_5289_adjusted_pvalues_str": "58.01", "tr_5289_aic": -176400, "tr_5289_aic_str": "-176400.0",
                        "tr_5289_estimates": 1.182e-14, "tr_5289_estimates_str": "1.182e-14",
                        "tr_5289_log_adjusted_pvalues": -1.763, "tr_5289_log_adjusted_pvalues_str": "-1.763",
                        "tr_5289_pvalues": 0.1005, "tr_5289_pvalues_str": "0.1005", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "549": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0148", "cpd_name": "PC(18:0/20:3)",
                        "harmonised_annotation_id": "549", "tr_5289_adjusted_pvalues": 0.000008792,
                        "tr_5289_adjusted_pvalues_str": "8.792e-06", "tr_5289_aic": -174900,
                        "tr_5289_aic_str": "-174900.0", "tr_5289_estimates": -5.351e-14,
                        "tr_5289_estimates_str": "-5.351e-14", "tr_5289_log_adjusted_pvalues": -5.056,
                        "tr_5289_log_adjusted_pvalues_str": "-5.056", "tr_5289_pvalues": 1.524e-8,
                        "tr_5289_pvalues_str": "1.524e-08", "tr_5760_adjusted_pvalues": 2.617e-7,
                        "tr_5760_adjusted_pvalues_str": "2.617e-07", "tr_5760_aic": -242200,
                        "tr_5760_aic_str": "-242200.0", "tr_5760_estimates": 1.737e-14,
                        "tr_5760_estimates_str": "1.737e-14", "tr_5760_log_adjusted_pvalues": 6.582,
                        "tr_5760_log_adjusted_pvalues_str": "6.582", "tr_5760_pvalues": 4.535e-10,
                        "tr_5760_pvalues_str": "4.535e-10"},
                "551": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0368",
                        "cpd_name": "alpha-carotene", "harmonised_annotation_id": "551",
                        "tr_5289_adjusted_pvalues": 0.531, "tr_5289_adjusted_pvalues_str": "0.531",
                        "tr_5289_aic": -179300, "tr_5289_aic_str": "-179300.0", "tr_5289_estimates": -1.549e-14,
                        "tr_5289_estimates_str": "-1.549e-14", "tr_5289_log_adjusted_pvalues": -0.2749,
                        "tr_5289_log_adjusted_pvalues_str": "-0.2749", "tr_5289_pvalues": 0.0009203,
                        "tr_5289_pvalues_str": "0.0009203", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "552": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0287",
                        "cpd_name": "PC(O-26:1/20:4) and/or PC(P-26:0/20:4)", "harmonised_annotation_id": "552",
                        "tr_5289_adjusted_pvalues": 0.0000883, "tr_5289_adjusted_pvalues_str": "8.83e-05",
                        "tr_5289_aic": -178200, "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": 2.813e-14,
                        "tr_5289_estimates_str": "2.813e-14", "tr_5289_log_adjusted_pvalues": 4.054,
                        "tr_5289_log_adjusted_pvalues_str": "4.054", "tr_5289_pvalues": 1.53e-7,
                        "tr_5289_pvalues_str": "1.53e-07", "tr_5760_adjusted_pvalues": 0.00293,
                        "tr_5760_adjusted_pvalues_str": "0.00293", "tr_5760_aic": -245900,
                        "tr_5760_aic_str": "-245900.0", "tr_5760_estimates": 7.888e-15,
                        "tr_5760_estimates_str": "7.888e-15", "tr_5760_log_adjusted_pvalues": 2.533,
                        "tr_5760_log_adjusted_pvalues_str": "2.533", "tr_5760_pvalues": 0.000005078,
                        "tr_5760_pvalues_str": "5.078e-06"},
                "555": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0144", "cpd_name": "PC(16:1/20:4)",
                        "harmonised_annotation_id": "555", "tr_5289_adjusted_pvalues": 4.858e-8,
                        "tr_5289_adjusted_pvalues_str": "4.858e-08", "tr_5289_aic": -183500,
                        "tr_5289_aic_str": "-183500.0", "tr_5289_estimates": 1.44e-14,
                        "tr_5289_estimates_str": "1.44e-14", "tr_5289_log_adjusted_pvalues": 7.314,
                        "tr_5289_log_adjusted_pvalues_str": "7.314", "tr_5289_pvalues": 8.419e-11,
                        "tr_5289_pvalues_str": "8.419e-11", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "560": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0309", "cpd_name": "TG(51:2)",
                        "harmonised_annotation_id": "560", "tr_5289_adjusted_pvalues": 8.747e-10,
                        "tr_5289_adjusted_pvalues_str": "8.747e-10", "tr_5289_aic": -185700,
                        "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": 1.125e-14,
                        "tr_5289_estimates_str": "1.125e-14", "tr_5289_log_adjusted_pvalues": 9.058,
                        "tr_5289_log_adjusted_pvalues_str": "9.058", "tr_5289_pvalues": 1.516e-12,
                        "tr_5289_pvalues_str": "1.516e-12", "tr_5760_adjusted_pvalues": 2.799e-14,
                        "tr_5760_adjusted_pvalues_str": "2.799e-14", "tr_5760_aic": -234900,
                        "tr_5760_aic_str": "-234900.0", "tr_5760_estimates": 6.199e-14,
                        "tr_5760_estimates_str": "6.199e-14", "tr_5760_log_adjusted_pvalues": 13.55,
                        "tr_5760_log_adjusted_pvalues_str": "13.55", "tr_5760_pvalues": 4.85e-17,
                        "tr_5760_pvalues_str": "4.85e-17"},
                "565": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0059", "cpd_name": "DG(18:0/18:1)",
                        "harmonised_annotation_id": "565", "tr_5289_adjusted_pvalues": 1.943e-10,
                        "tr_5289_adjusted_pvalues_str": "1.943e-10", "tr_5289_aic": -175000,
                        "tr_5289_aic_str": "-175000.0", "tr_5289_estimates": -7.484e-14,
                        "tr_5289_estimates_str": "-7.484e-14", "tr_5289_log_adjusted_pvalues": -9.712,
                        "tr_5289_log_adjusted_pvalues_str": "-9.712", "tr_5289_pvalues": 3.367e-13,
                        "tr_5289_pvalues_str": "3.367e-13", "tr_5760_adjusted_pvalues": 3.783e-11,
                        "tr_5760_adjusted_pvalues_str": "3.783e-11", "tr_5760_aic": -240800,
                        "tr_5760_aic_str": "-240800.0", "tr_5760_estimates": -2.764e-14,
                        "tr_5760_estimates_str": "-2.764e-14", "tr_5760_log_adjusted_pvalues": -10.42,
                        "tr_5760_log_adjusted_pvalues_str": "-10.42", "tr_5760_pvalues": 6.556e-14,
                        "tr_5760_pvalues_str": "6.556e-14"},
                "566": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0280",
                        "cpd_name": "PC(O-24:1/18:1) and/or PC(P-24:0/18:1)", "harmonised_annotation_id": "566",
                        "tr_5289_adjusted_pvalues": 1.309e-10, "tr_5289_adjusted_pvalues_str": "1.309e-10",
                        "tr_5289_aic": -174600, "tr_5289_aic_str": "-174600.0", "tr_5289_estimates": 7.395e-14,
                        "tr_5289_estimates_str": "7.395e-14", "tr_5289_log_adjusted_pvalues": 9.883,
                        "tr_5289_log_adjusted_pvalues_str": "9.883", "tr_5289_pvalues": 2.269e-13,
                        "tr_5289_pvalues_str": "2.269e-13", "tr_5760_adjusted_pvalues": 7.041e-10,
                        "tr_5760_adjusted_pvalues_str": "7.041e-10", "tr_5760_aic": -241800,
                        "tr_5760_aic_str": "-241800.0", "tr_5760_estimates": 2.106e-14,
                        "tr_5760_estimates_str": "2.106e-14", "tr_5760_log_adjusted_pvalues": 9.152,
                        "tr_5760_log_adjusted_pvalues_str": "9.152", "tr_5760_pvalues": 1.22e-12,
                        "tr_5760_pvalues_str": "1.22e-12"},
                "569": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0137",
                        "cpd_name": "PC(16:0/20:4)_1", "harmonised_annotation_id": "569",
                        "tr_5289_adjusted_pvalues": 0.603, "tr_5289_adjusted_pvalues_str": "0.603",
                        "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": 1.275e-14,
                        "tr_5289_estimates_str": "1.275e-14", "tr_5289_log_adjusted_pvalues": 0.2197,
                        "tr_5289_log_adjusted_pvalues_str": "0.2197", "tr_5289_pvalues": 0.001045,
                        "tr_5289_pvalues_str": "0.001045", "tr_5760_adjusted_pvalues": 0.2656,
                        "tr_5760_adjusted_pvalues_str": "0.2656", "tr_5760_aic": -245000,
                        "tr_5760_aic_str": "-245000.0", "tr_5760_estimates": 6.685e-15,
                        "tr_5760_estimates_str": "6.685e-15", "tr_5760_log_adjusted_pvalues": 0.5758,
                        "tr_5760_log_adjusted_pvalues_str": "0.5758", "tr_5760_pvalues": 0.0004603,
                        "tr_5760_pvalues_str": "0.0004603"},
                "574": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0252",
                        "cpd_name": "LPC(O-26:1/0:0)", "harmonised_annotation_id": "574",
                        "tr_5289_adjusted_pvalues": 229.8, "tr_5289_adjusted_pvalues_str": "229.8",
                        "tr_5289_aic": -185500, "tr_5289_aic_str": "-185500.0", "tr_5289_estimates": 1.294e-15,
                        "tr_5289_estimates_str": "1.294e-15", "tr_5289_log_adjusted_pvalues": -2.361,
                        "tr_5289_log_adjusted_pvalues_str": "-2.361", "tr_5289_pvalues": 0.3982,
                        "tr_5289_pvalues_str": "0.3982", "tr_5760_adjusted_pvalues": 15.12,
                        "tr_5760_adjusted_pvalues_str": "15.12", "tr_5760_aic": -249200, "tr_5760_aic_str": "-249200.0",
                        "tr_5760_estimates": 2.468e-15, "tr_5760_estimates_str": "2.468e-15",
                        "tr_5760_log_adjusted_pvalues": -1.18, "tr_5760_log_adjusted_pvalues_str": "-1.18",
                        "tr_5760_pvalues": 0.02621, "tr_5760_pvalues_str": "0.02621"},
                "575": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0152", "cpd_name": "PC(18:0/22:6)",
                        "harmonised_annotation_id": "575", "tr_5289_adjusted_pvalues": 8.169e-27,
                        "tr_5289_adjusted_pvalues_str": "8.169e-27", "tr_5289_aic": -185900,
                        "tr_5289_aic_str": "-185900.0", "tr_5289_estimates": 1.651e-14,
                        "tr_5289_estimates_str": "1.651e-14", "tr_5289_log_adjusted_pvalues": 26.09,
                        "tr_5289_log_adjusted_pvalues_str": "26.09", "tr_5289_pvalues": 1.416e-29,
                        "tr_5289_pvalues_str": "1.416e-29", "tr_5760_adjusted_pvalues": 1.175e-49,
                        "tr_5760_adjusted_pvalues_str": "1.175e-49", "tr_5760_aic": -231000,
                        "tr_5760_aic_str": "-231000.0", "tr_5760_estimates": -1.731e-13,
                        "tr_5760_estimates_str": "-1.731e-13", "tr_5760_log_adjusted_pvalues": -48.93,
                        "tr_5760_log_adjusted_pvalues_str": "-48.93", "tr_5760_pvalues": 2.037e-52,
                        "tr_5760_pvalues_str": "2.037e-52"},
                "577": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0003", "cpd_name": "CAR(10:0-OH)",
                        "harmonised_annotation_id": "577", "tr_5289_adjusted_pvalues": 539.4,
                        "tr_5289_adjusted_pvalues_str": "539.4", "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0",
                        "tr_5289_estimates": -3.281e-16, "tr_5289_estimates_str": "-3.281e-16",
                        "tr_5289_log_adjusted_pvalues": 2.732, "tr_5289_log_adjusted_pvalues_str": "2.732",
                        "tr_5289_pvalues": 0.9348, "tr_5289_pvalues_str": "0.9348", "tr_5760_adjusted_pvalues": 121,
                        "tr_5760_adjusted_pvalues_str": "121.0", "tr_5760_aic": -234000, "tr_5760_aic_str": "-234000.0",
                        "tr_5760_estimates": -9.804e-15, "tr_5760_estimates_str": "-9.804e-15",
                        "tr_5760_log_adjusted_pvalues": 2.083, "tr_5760_log_adjusted_pvalues_str": "2.083",
                        "tr_5760_pvalues": 0.2098, "tr_5760_pvalues_str": "0.2098"},
                "578": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0290",
                        "cpd_name": "SM(d16:1/23:0)", "harmonised_annotation_id": "578",
                        "tr_5289_adjusted_pvalues": 3.267e-30, "tr_5289_adjusted_pvalues_str": "3.267e-30",
                        "tr_5289_aic": -179800, "tr_5289_aic_str": "-179800.0", "tr_5289_estimates": 4.9e-14,
                        "tr_5289_estimates_str": "4.9e-14", "tr_5289_log_adjusted_pvalues": 29.49,
                        "tr_5289_log_adjusted_pvalues_str": "29.49", "tr_5289_pvalues": 5.662e-33,
                        "tr_5289_pvalues_str": "5.662e-33", "tr_5760_adjusted_pvalues": 5.929e-36,
                        "tr_5760_adjusted_pvalues_str": "5.929e-36", "tr_5760_aic": -237600,
                        "tr_5760_aic_str": "-237600.0", "tr_5760_estimates": -6.361e-14,
                        "tr_5760_estimates_str": "-6.361e-14", "tr_5760_log_adjusted_pvalues": -35.23,
                        "tr_5760_log_adjusted_pvalues_str": "-35.23", "tr_5760_pvalues": 1.028e-38,
                        "tr_5760_pvalues_str": "1.028e-38"},
                "583": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0080", "cpd_name": "LPC(0:0/18:0)",
                        "harmonised_annotation_id": "583", "tr_5289_adjusted_pvalues": 2.199e-12,
                        "tr_5289_adjusted_pvalues_str": "2.199e-12", "tr_5289_aic": -180000,
                        "tr_5289_aic_str": "-180000.0", "tr_5289_estimates": 3.006e-14,
                        "tr_5289_estimates_str": "3.006e-14", "tr_5289_log_adjusted_pvalues": 11.66,
                        "tr_5289_log_adjusted_pvalues_str": "11.66", "tr_5289_pvalues": 3.812e-15,
                        "tr_5289_pvalues_str": "3.812e-15", "tr_5760_adjusted_pvalues": 5.179e-13,
                        "tr_5760_adjusted_pvalues_str": "5.179e-13", "tr_5760_aic": -242200,
                        "tr_5760_aic_str": "-242200.0", "tr_5760_estimates": 2.153e-14,
                        "tr_5760_estimates_str": "2.153e-14", "tr_5760_log_adjusted_pvalues": 12.29,
                        "tr_5760_log_adjusted_pvalues_str": "12.29", "tr_5760_pvalues": 8.975e-16,
                        "tr_5760_pvalues_str": "8.975e-16"},
                "584": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0379", "cpd_name": "LacCer(d42:3)",
                        "harmonised_annotation_id": "584", "tr_5289_adjusted_pvalues": 0.289,
                        "tr_5289_adjusted_pvalues_str": "0.289", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                        "tr_5289_estimates": -2.981e-15, "tr_5289_estimates_str": "-2.981e-15",
                        "tr_5289_log_adjusted_pvalues": -0.5391, "tr_5289_log_adjusted_pvalues_str": "-0.5391",
                        "tr_5289_pvalues": 0.0005009, "tr_5289_pvalues_str": "0.0005009",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "587": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0319", "cpd_name": "TG(53:1)",
                        "harmonised_annotation_id": "587", "tr_5289_adjusted_pvalues": 7.889e-14,
                        "tr_5289_adjusted_pvalues_str": "7.889e-14", "tr_5289_aic": -178200,
                        "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": -4.736e-14,
                        "tr_5289_estimates_str": "-4.736e-14", "tr_5289_log_adjusted_pvalues": -13.1,
                        "tr_5289_log_adjusted_pvalues_str": "-13.1", "tr_5289_pvalues": 1.367e-16,
                        "tr_5289_pvalues_str": "1.367e-16", "tr_5760_adjusted_pvalues": 1.105e-13,
                        "tr_5760_adjusted_pvalues_str": "1.105e-13", "tr_5760_aic": -228600,
                        "tr_5760_aic_str": "-228600.0", "tr_5760_estimates": -1.353e-13,
                        "tr_5760_estimates_str": "-1.353e-13", "tr_5760_log_adjusted_pvalues": -12.96,
                        "tr_5760_log_adjusted_pvalues_str": "-12.96", "tr_5760_pvalues": 1.915e-16,
                        "tr_5760_pvalues_str": "1.915e-16"},
                "588": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0274",
                        "cpd_name": "PC(O-22:0/18:2)", "harmonised_annotation_id": "588",
                        "tr_5289_adjusted_pvalues": 0.01333, "tr_5289_adjusted_pvalues_str": "0.01333",
                        "tr_5289_aic": -180500, "tr_5289_aic_str": "-180500.0", "tr_5289_estimates": -1.624e-14,
                        "tr_5289_estimates_str": "-1.624e-14", "tr_5289_log_adjusted_pvalues": -1.875,
                        "tr_5289_log_adjusted_pvalues_str": "-1.875", "tr_5289_pvalues": 0.00002311,
                        "tr_5289_pvalues_str": "2.311e-05", "tr_5760_adjusted_pvalues": 0.02234,
                        "tr_5760_adjusted_pvalues_str": "0.02234", "tr_5760_aic": -233200,
                        "tr_5760_aic_str": "-233200.0", "tr_5760_estimates": -3.71e-14,
                        "tr_5760_estimates_str": "-3.71e-14", "tr_5760_log_adjusted_pvalues": -1.651,
                        "tr_5760_log_adjusted_pvalues_str": "-1.651", "tr_5760_pvalues": 0.00003872,
                        "tr_5760_pvalues_str": "3.872e-05"},
                "589": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0155", "cpd_name": "PC(18:1/20:4)",
                        "harmonised_annotation_id": "589", "tr_5289_adjusted_pvalues": 0.9858,
                        "tr_5289_adjusted_pvalues_str": "0.9858", "tr_5289_aic": -175600,
                        "tr_5289_aic_str": "-175600.0", "tr_5289_estimates": -2.504e-14,
                        "tr_5289_estimates_str": "-2.504e-14", "tr_5289_log_adjusted_pvalues": -0.006225,
                        "tr_5289_log_adjusted_pvalues_str": "-0.006225", "tr_5289_pvalues": 0.001708,
                        "tr_5289_pvalues_str": "0.001708", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "593": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0183",
                        "cpd_name": "SM(d18:1/20:0)", "harmonised_annotation_id": "593",
                        "tr_5289_adjusted_pvalues": 2.158e-8, "tr_5289_adjusted_pvalues_str": "2.158e-08",
                        "tr_5289_aic": -181200, "tr_5289_aic_str": "-181200.0", "tr_5289_estimates": 2.058e-14,
                        "tr_5289_estimates_str": "2.058e-14", "tr_5289_log_adjusted_pvalues": 7.666,
                        "tr_5289_log_adjusted_pvalues_str": "7.666", "tr_5289_pvalues": 3.74e-11,
                        "tr_5289_pvalues_str": "3.74e-11", "tr_5760_adjusted_pvalues": 0.01077,
                        "tr_5760_adjusted_pvalues_str": "0.01077", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": -3.095e-15,
                        "tr_5760_estimates_str": "-3.095e-15", "tr_5760_log_adjusted_pvalues": -1.968,
                        "tr_5760_log_adjusted_pvalues_str": "-1.968", "tr_5760_pvalues": 0.00001866,
                        "tr_5760_pvalues_str": "1.866e-05"},
                "595": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0258", "cpd_name": "PC(15:0/18:2)",
                        "harmonised_annotation_id": "595", "tr_5289_adjusted_pvalues": 332.6,
                        "tr_5289_adjusted_pvalues_str": "332.6", "tr_5289_aic": -188200, "tr_5289_aic_str": "-188200.0",
                        "tr_5289_estimates": -5.421e-16, "tr_5289_estimates_str": "-5.421e-16",
                        "tr_5289_log_adjusted_pvalues": 2.522, "tr_5289_log_adjusted_pvalues_str": "2.522",
                        "tr_5289_pvalues": 0.5764, "tr_5289_pvalues_str": "0.5764", "tr_5760_adjusted_pvalues": 47.08,
                        "tr_5760_adjusted_pvalues_str": "47.08", "tr_5760_aic": -236800, "tr_5760_aic_str": "-236800.0",
                        "tr_5760_estimates": -9.256e-15, "tr_5760_estimates_str": "-9.256e-15",
                        "tr_5760_log_adjusted_pvalues": 1.673, "tr_5760_log_adjusted_pvalues_str": "1.673",
                        "tr_5760_pvalues": 0.0816, "tr_5760_pvalues_str": "0.0816"},
                "600": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0243", "cpd_name": "LPC(0:0/20:2)",
                        "harmonised_annotation_id": "600", "tr_5289_adjusted_pvalues": 180.6,
                        "tr_5289_adjusted_pvalues_str": "180.6", "tr_5289_aic": -180000, "tr_5289_aic_str": "-180000.0",
                        "tr_5289_estimates": 3.778e-15, "tr_5289_estimates_str": "3.778e-15",
                        "tr_5289_log_adjusted_pvalues": -2.257, "tr_5289_log_adjusted_pvalues_str": "-2.257",
                        "tr_5289_pvalues": 0.313, "tr_5289_pvalues_str": "0.313", "tr_5760_adjusted_pvalues": 136.7,
                        "tr_5760_adjusted_pvalues_str": "136.7", "tr_5760_aic": -249200, "tr_5760_aic_str": "-249200.0",
                        "tr_5760_estimates": 1.274e-15, "tr_5760_estimates_str": "1.274e-15",
                        "tr_5760_log_adjusted_pvalues": -2.136, "tr_5760_log_adjusted_pvalues_str": "-2.136",
                        "tr_5760_pvalues": 0.2369, "tr_5760_pvalues_str": "0.2369"},
                "601": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0370",
                        "cpd_name": "beta carotene_1", "harmonised_annotation_id": "601",
                        "tr_5289_adjusted_pvalues": 415, "tr_5289_adjusted_pvalues_str": "415.0",
                        "tr_5289_aic": -175800, "tr_5289_aic_str": "-175800.0", "tr_5289_estimates": 2.979e-15,
                        "tr_5289_estimates_str": "2.979e-15", "tr_5289_log_adjusted_pvalues": -2.618,
                        "tr_5289_log_adjusted_pvalues_str": "-2.618", "tr_5289_pvalues": 0.7192,
                        "tr_5289_pvalues_str": "0.7192", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "602": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0116",
                        "cpd_name": "LPC(O-20:0/0:0)", "harmonised_annotation_id": "602",
                        "tr_5289_adjusted_pvalues": 11.56, "tr_5289_adjusted_pvalues_str": "11.56",
                        "tr_5289_aic": -183500, "tr_5289_aic_str": "-183500.0", "tr_5289_estimates": 5.114e-15,
                        "tr_5289_estimates_str": "5.114e-15", "tr_5289_log_adjusted_pvalues": -1.063,
                        "tr_5289_log_adjusted_pvalues_str": "-1.063", "tr_5289_pvalues": 0.02003,
                        "tr_5289_pvalues_str": "0.02003", "tr_5760_adjusted_pvalues": 2.507,
                        "tr_5760_adjusted_pvalues_str": "2.507", "tr_5760_aic": -233400, "tr_5760_aic_str": "-233400.0",
                        "tr_5760_estimates": 2.361e-14, "tr_5760_estimates_str": "2.361e-14",
                        "tr_5760_log_adjusted_pvalues": -0.3991, "tr_5760_log_adjusted_pvalues_str": "-0.3991",
                        "tr_5760_pvalues": 0.004344, "tr_5760_pvalues_str": "0.004344"},
                "603": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0238",
                        "cpd_name": "Cer(d18:0/22:0)", "harmonised_annotation_id": "603",
                        "tr_5289_adjusted_pvalues": 1.294e-16, "tr_5289_adjusted_pvalues_str": "1.294e-16",
                        "tr_5289_aic": -182300, "tr_5289_aic_str": "-182300.0", "tr_5289_estimates": 2.548e-14,
                        "tr_5289_estimates_str": "2.548e-14", "tr_5289_log_adjusted_pvalues": 15.89,
                        "tr_5289_log_adjusted_pvalues_str": "15.89", "tr_5289_pvalues": 2.242e-19,
                        "tr_5289_pvalues_str": "2.242e-19", "tr_5760_adjusted_pvalues": 4.748e-25,
                        "tr_5760_adjusted_pvalues_str": "4.748e-25", "tr_5760_aic": -238200,
                        "tr_5760_aic_str": "-238200.0", "tr_5760_estimates": -5.273e-14,
                        "tr_5760_estimates_str": "-5.273e-14", "tr_5760_log_adjusted_pvalues": -24.32,
                        "tr_5760_log_adjusted_pvalues_str": "-24.32", "tr_5760_pvalues": 8.229e-28,
                        "tr_5760_pvalues_str": "8.229e-28"},
                "609": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0190",
                        "cpd_name": "SM(d18:2/16:0)_1", "harmonised_annotation_id": "609",
                        "tr_5289_adjusted_pvalues": 1.793e-48, "tr_5289_adjusted_pvalues_str": "1.793e-48",
                        "tr_5289_aic": -178400, "tr_5289_aic_str": "-178400.0", "tr_5289_estimates": 8.219e-14,
                        "tr_5289_estimates_str": "8.219e-14", "tr_5289_log_adjusted_pvalues": 47.75,
                        "tr_5289_log_adjusted_pvalues_str": "47.75", "tr_5289_pvalues": 3.107e-51,
                        "tr_5289_pvalues_str": "3.107e-51", "tr_5760_adjusted_pvalues": 6.937e-64,
                        "tr_5760_adjusted_pvalues_str": "6.937e-64", "tr_5760_aic": -232800,
                        "tr_5760_aic_str": "-232800.0", "tr_5760_estimates": 1.65e-13,
                        "tr_5760_estimates_str": "1.65e-13", "tr_5760_log_adjusted_pvalues": 63.16,
                        "tr_5760_log_adjusted_pvalues_str": "63.16", "tr_5760_pvalues": 1.202e-66,
                        "tr_5760_pvalues_str": "1.202e-66"},
                "611": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0270",
                        "cpd_name": "PC(O-18:0/20:3)", "harmonised_annotation_id": "611",
                        "tr_5289_adjusted_pvalues": 2.719e-16, "tr_5289_adjusted_pvalues_str": "2.719e-16",
                        "tr_5289_aic": -178200, "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": 4.636e-14,
                        "tr_5289_estimates_str": "4.636e-14", "tr_5289_log_adjusted_pvalues": 15.57,
                        "tr_5289_log_adjusted_pvalues_str": "15.57", "tr_5289_pvalues": 4.713e-19,
                        "tr_5289_pvalues_str": "4.713e-19", "tr_5760_adjusted_pvalues": 1.838e-17,
                        "tr_5760_adjusted_pvalues_str": "1.838e-17", "tr_5760_aic": -235700,
                        "tr_5760_aic_str": "-235700.0", "tr_5760_estimates": 5.6e-14,
                        "tr_5760_estimates_str": "5.6e-14", "tr_5760_log_adjusted_pvalues": 16.74,
                        "tr_5760_log_adjusted_pvalues_str": "16.74", "tr_5760_pvalues": 3.185e-20,
                        "tr_5760_pvalues_str": "3.185e-20"},
                "618": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0049",
                        "cpd_name": "Cer(d18:2/22:0)", "harmonised_annotation_id": "618",
                        "tr_5289_adjusted_pvalues": 2.171e-22, "tr_5289_adjusted_pvalues_str": "2.171e-22",
                        "tr_5289_aic": -177200, "tr_5289_aic_str": "-177200.0", "tr_5289_estimates": 6.614e-14,
                        "tr_5289_estimates_str": "6.614e-14", "tr_5289_log_adjusted_pvalues": 21.66,
                        "tr_5289_log_adjusted_pvalues_str": "21.66", "tr_5289_pvalues": 3.763e-25,
                        "tr_5289_pvalues_str": "3.763e-25", "tr_5760_adjusted_pvalues": 1.277e-25,
                        "tr_5760_adjusted_pvalues_str": "1.277e-25", "tr_5760_aic": -233200,
                        "tr_5760_aic_str": "-233200.0", "tr_5760_estimates": -9.49e-14,
                        "tr_5760_estimates_str": "-9.49e-14", "tr_5760_log_adjusted_pvalues": -24.89,
                        "tr_5760_log_adjusted_pvalues_str": "-24.89", "tr_5760_pvalues": 2.213e-28,
                        "tr_5760_pvalues_str": "2.213e-28"},
                "621": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0180",
                        "cpd_name": "SM(d18:1/16:0)", "harmonised_annotation_id": "621",
                        "tr_5289_adjusted_pvalues": None, "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf",
                        "tr_5289_aic_str": "inf", "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0",
                        "tr_5289_log_adjusted_pvalues": None, "tr_5289_log_adjusted_pvalues_str": None,
                        "tr_5289_pvalues": None, "tr_5289_pvalues_str": None, "tr_5760_adjusted_pvalues": 5.664e-27,
                        "tr_5760_adjusted_pvalues_str": "5.664e-27", "tr_5760_aic": -244000,
                        "tr_5760_aic_str": "-244000.0", "tr_5760_estimates": 2.39e-14,
                        "tr_5760_estimates_str": "2.39e-14", "tr_5760_log_adjusted_pvalues": 26.25,
                        "tr_5760_log_adjusted_pvalues_str": "26.25", "tr_5760_pvalues": 9.816e-30,
                        "tr_5760_pvalues_str": "9.816e-30"},
                "624": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0166", "cpd_name": "PE(16:0/18:2)",
                        "harmonised_annotation_id": "624", "tr_5289_adjusted_pvalues": 21.75,
                        "tr_5289_adjusted_pvalues_str": "21.75", "tr_5289_aic": -175500, "tr_5289_aic_str": "-175500.0",
                        "tr_5289_estimates": -1.853e-14, "tr_5289_estimates_str": "-1.853e-14",
                        "tr_5289_log_adjusted_pvalues": 1.337, "tr_5289_log_adjusted_pvalues_str": "1.337",
                        "tr_5289_pvalues": 0.03769, "tr_5289_pvalues_str": "0.03769", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "627": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0095",
                        "cpd_name": "LPC(18:1/0:0)_2", "harmonised_annotation_id": "627",
                        "tr_5289_adjusted_pvalues": 0.01286, "tr_5289_adjusted_pvalues_str": "0.01286",
                        "tr_5289_aic": -183700, "tr_5289_aic_str": "-183700.0", "tr_5289_estimates": 8.626e-15,
                        "tr_5289_estimates_str": "8.626e-15", "tr_5289_log_adjusted_pvalues": 1.891,
                        "tr_5289_log_adjusted_pvalues_str": "1.891", "tr_5289_pvalues": 0.0000223,
                        "tr_5289_pvalues_str": "2.23e-05", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "634": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0246", "cpd_name": "LPC(20:2/0:0)",
                        "harmonised_annotation_id": "634", "tr_5289_adjusted_pvalues": 467.9,
                        "tr_5289_adjusted_pvalues_str": "467.9", "tr_5289_aic": -174600, "tr_5289_aic_str": "-174600.0",
                        "tr_5289_estimates": 2.262e-15, "tr_5289_estimates_str": "2.262e-15",
                        "tr_5289_log_adjusted_pvalues": -2.67, "tr_5289_log_adjusted_pvalues_str": "-2.67",
                        "tr_5289_pvalues": 0.8109, "tr_5289_pvalues_str": "0.8109", "tr_5760_adjusted_pvalues": 475.1,
                        "tr_5760_adjusted_pvalues_str": "475.1", "tr_5760_aic": -235300, "tr_5760_aic_str": "-235300.0",
                        "tr_5760_estimates": -1.42e-15, "tr_5760_estimates_str": "-1.42e-15",
                        "tr_5760_log_adjusted_pvalues": 2.677, "tr_5760_log_adjusted_pvalues_str": "2.677",
                        "tr_5760_pvalues": 0.8234, "tr_5760_pvalues_str": "0.8234"},
                "637": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0150", "cpd_name": "PC(18:0/22:4)",
                        "harmonised_annotation_id": "637", "tr_5289_adjusted_pvalues": 0.002877,
                        "tr_5289_adjusted_pvalues_str": "0.002877", "tr_5289_aic": -178000,
                        "tr_5289_aic_str": "-178000.0", "tr_5289_estimates": 2.613e-14,
                        "tr_5289_estimates_str": "2.613e-14", "tr_5289_log_adjusted_pvalues": 2.541,
                        "tr_5289_log_adjusted_pvalues_str": "2.541", "tr_5289_pvalues": 0.000004986,
                        "tr_5289_pvalues_str": "4.986e-06", "tr_5760_adjusted_pvalues": 0.002592,
                        "tr_5760_adjusted_pvalues_str": "0.002592", "tr_5760_aic": -234000,
                        "tr_5760_aic_str": "-234000.0", "tr_5760_estimates": -3.644e-14,
                        "tr_5760_estimates_str": "-3.644e-14", "tr_5760_log_adjusted_pvalues": -2.586,
                        "tr_5760_log_adjusted_pvalues_str": "-2.586", "tr_5760_pvalues": 0.000004492,
                        "tr_5760_pvalues_str": "4.492e-06"},
                "641": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0053",
                        "cpd_name": "Cer(d19:1/24:0)", "harmonised_annotation_id": "641",
                        "tr_5289_adjusted_pvalues": 1.259e-14, "tr_5289_adjusted_pvalues_str": "1.259e-14",
                        "tr_5289_aic": -186000, "tr_5289_aic_str": "-186000.0", "tr_5289_estimates": -1.236e-14,
                        "tr_5289_estimates_str": "-1.236e-14", "tr_5289_log_adjusted_pvalues": -13.9,
                        "tr_5289_log_adjusted_pvalues_str": "-13.9", "tr_5289_pvalues": 2.183e-17,
                        "tr_5289_pvalues_str": "2.183e-17", "tr_5760_adjusted_pvalues": 7.785e-35,
                        "tr_5760_adjusted_pvalues_str": "7.785e-35", "tr_5760_aic": -236400,
                        "tr_5760_aic_str": "-236400.0", "tr_5760_estimates": -7.445e-14,
                        "tr_5760_estimates_str": "-7.445e-14", "tr_5760_log_adjusted_pvalues": -34.11,
                        "tr_5760_log_adjusted_pvalues_str": "-34.11", "tr_5760_pvalues": 1.349e-37,
                        "tr_5760_pvalues_str": "1.349e-37"},
                "643": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0359", "cpd_name": "TG(58:8)",
                        "harmonised_annotation_id": "643", "tr_5289_adjusted_pvalues": None,
                        "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                        "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                        "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "644": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0197",
                        "cpd_name": "SM(d19:1/16:0)", "harmonised_annotation_id": "644",
                        "tr_5289_adjusted_pvalues": 3.914e-26, "tr_5289_adjusted_pvalues_str": "3.914e-26",
                        "tr_5289_aic": -177200, "tr_5289_aic_str": "-177200.0", "tr_5289_estimates": -6.977e-14,
                        "tr_5289_estimates_str": "-6.977e-14", "tr_5289_log_adjusted_pvalues": -25.41,
                        "tr_5289_log_adjusted_pvalues_str": "-25.41", "tr_5289_pvalues": 6.784e-29,
                        "tr_5289_pvalues_str": "6.784e-29", "tr_5760_adjusted_pvalues": 5.576e-36,
                        "tr_5760_adjusted_pvalues_str": "5.576e-36", "tr_5760_aic": -242400,
                        "tr_5760_aic_str": "-242400.0", "tr_5760_estimates": 3.454e-14,
                        "tr_5760_estimates_str": "3.454e-14", "tr_5760_log_adjusted_pvalues": 35.25,
                        "tr_5760_log_adjusted_pvalues_str": "35.25", "tr_5760_pvalues": 9.664e-39,
                        "tr_5760_pvalues_str": "9.664e-39"},
                "647": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0120", "cpd_name": "LPE(18:0/0:0)",
                        "harmonised_annotation_id": "647", "tr_5289_adjusted_pvalues": 4.699e-9,
                        "tr_5289_adjusted_pvalues_str": "4.699e-09", "tr_5289_aic": -185700,
                        "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": 1.052e-14,
                        "tr_5289_estimates_str": "1.052e-14", "tr_5289_log_adjusted_pvalues": 8.328,
                        "tr_5289_log_adjusted_pvalues_str": "8.328", "tr_5289_pvalues": 8.144e-12,
                        "tr_5289_pvalues_str": "8.144e-12", "tr_5760_adjusted_pvalues": 4.165e-14,
                        "tr_5760_adjusted_pvalues_str": "4.165e-14", "tr_5760_aic": -241200,
                        "tr_5760_aic_str": "-241200.0", "tr_5760_estimates": 2.623e-14,
                        "tr_5760_estimates_str": "2.623e-14", "tr_5760_log_adjusted_pvalues": 13.38,
                        "tr_5760_log_adjusted_pvalues_str": "13.38", "tr_5760_pvalues": 7.219e-17,
                        "tr_5760_pvalues_str": "7.219e-17"},
                "650": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0225", "cpd_name": "TG(54:3)",
                        "harmonised_annotation_id": "650", "tr_5289_adjusted_pvalues": 0.2403,
                        "tr_5289_adjusted_pvalues_str": "0.2403", "tr_5289_aic": -176700,
                        "tr_5289_aic_str": "-176700.0", "tr_5289_estimates": -2.479e-14,
                        "tr_5289_estimates_str": "-2.479e-14", "tr_5289_log_adjusted_pvalues": -0.6193,
                        "tr_5289_log_adjusted_pvalues_str": "-0.6193", "tr_5289_pvalues": 0.0004164,
                        "tr_5289_pvalues_str": "0.0004164", "tr_5760_adjusted_pvalues": 0.03842,
                        "tr_5760_adjusted_pvalues_str": "0.03842", "tr_5760_aic": -238100,
                        "tr_5760_aic_str": "-238100.0", "tr_5760_estimates": 1.884e-14,
                        "tr_5760_estimates_str": "1.884e-14", "tr_5760_log_adjusted_pvalues": 1.415,
                        "tr_5760_log_adjusted_pvalues_str": "1.415", "tr_5760_pvalues": 0.00006658,
                        "tr_5760_pvalues_str": "6.658e-05"},
                "654": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0119", "cpd_name": "LPE(16:0/0:0)",
                        "harmonised_annotation_id": "654", "tr_5289_adjusted_pvalues": 0.1859,
                        "tr_5289_adjusted_pvalues_str": "0.1859", "tr_5289_aic": -184700,
                        "tr_5289_aic_str": "-184700.0", "tr_5289_estimates": 6.501e-15,
                        "tr_5289_estimates_str": "6.501e-15", "tr_5289_log_adjusted_pvalues": 0.7308,
                        "tr_5289_log_adjusted_pvalues_str": "0.7308", "tr_5289_pvalues": 0.0003221,
                        "tr_5289_pvalues_str": "0.0003221", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": "inf", "tr_5760_aic_str": "inf",
                        "tr_5760_estimates": 0, "tr_5760_estimates_str": "0.0", "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "655": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0086", "cpd_name": "LPC(0:0/20:5)",
                        "harmonised_annotation_id": "655", "tr_5289_adjusted_pvalues": 4.076e-31,
                        "tr_5289_adjusted_pvalues_str": "4.076e-31", "tr_5289_aic": -174800,
                        "tr_5289_aic_str": "-174800.0", "tr_5289_estimates": -1.247e-13,
                        "tr_5289_estimates_str": "-1.247e-13", "tr_5289_log_adjusted_pvalues": -30.39,
                        "tr_5289_log_adjusted_pvalues_str": "-30.39", "tr_5289_pvalues": 7.064e-34,
                        "tr_5289_pvalues_str": "7.064e-34", "tr_5760_adjusted_pvalues": 2.371e-39,
                        "tr_5760_adjusted_pvalues_str": "2.371e-39", "tr_5760_aic": -236700,
                        "tr_5760_aic_str": "-236700.0", "tr_5760_estimates": 7.956e-14,
                        "tr_5760_estimates_str": "7.956e-14", "tr_5760_log_adjusted_pvalues": 38.63,
                        "tr_5760_log_adjusted_pvalues_str": "38.63", "tr_5760_pvalues": 4.109e-42,
                        "tr_5760_pvalues_str": "4.109e-42"},
                "662": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0094", "cpd_name": "LPC(18:0/0:0)",
                        "harmonised_annotation_id": "662", "tr_5289_adjusted_pvalues": 1.283e-11,
                        "tr_5289_adjusted_pvalues_str": "1.283e-11", "tr_5289_aic": -176000,
                        "tr_5289_aic_str": "-176000.0", "tr_5289_estimates": 5.778e-14,
                        "tr_5289_estimates_str": "5.778e-14", "tr_5289_log_adjusted_pvalues": 10.89,
                        "tr_5289_log_adjusted_pvalues_str": "10.89", "tr_5289_pvalues": 2.224e-14,
                        "tr_5289_pvalues_str": "2.224e-14", "tr_5760_adjusted_pvalues": 5.76e-13,
                        "tr_5760_adjusted_pvalues_str": "5.76e-13", "tr_5760_aic": -237800,
                        "tr_5760_aic_str": "-237800.0", "tr_5760_estimates": 3.714e-14,
                        "tr_5760_estimates_str": "3.714e-14", "tr_5760_log_adjusted_pvalues": 12.24,
                        "tr_5760_log_adjusted_pvalues_str": "12.24", "tr_5760_pvalues": 9.982e-16,
                        "tr_5760_pvalues_str": "9.982e-16"},
                "665": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0249",
                        "cpd_name": "LPC(22:5/0:0)_2", "harmonised_annotation_id": "665",
                        "tr_5289_adjusted_pvalues": 283.8, "tr_5289_adjusted_pvalues_str": "283.8",
                        "tr_5289_aic": -185400, "tr_5289_aic_str": "-185400.0", "tr_5289_estimates": 1.06e-15,
                        "tr_5289_estimates_str": "1.06e-15", "tr_5289_log_adjusted_pvalues": -2.453,
                        "tr_5289_log_adjusted_pvalues_str": "-2.453", "tr_5289_pvalues": 0.4919,
                        "tr_5289_pvalues_str": "0.4919", "tr_5760_adjusted_pvalues": 5.334,
                        "tr_5760_adjusted_pvalues_str": "5.334", "tr_5760_aic": -237600, "tr_5760_aic_str": "-237600.0",
                        "tr_5760_estimates": 1.248e-14, "tr_5760_estimates_str": "1.248e-14",
                        "tr_5760_log_adjusted_pvalues": -0.7271, "tr_5760_log_adjusted_pvalues_str": "-0.7271",
                        "tr_5760_pvalues": 0.009244, "tr_5760_pvalues_str": "0.009244"},
                "669": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0317", "cpd_name": "TG(52:6)_3",
                        "harmonised_annotation_id": "669", "tr_5289_adjusted_pvalues": 2.044e-12,
                        "tr_5289_adjusted_pvalues_str": "2.044e-12", "tr_5289_aic": -186000,
                        "tr_5289_aic_str": "-186000.0", "tr_5289_estimates": 1.219e-14,
                        "tr_5289_estimates_str": "1.219e-14", "tr_5289_log_adjusted_pvalues": 11.69,
                        "tr_5289_log_adjusted_pvalues_str": "11.69", "tr_5289_pvalues": 3.542e-15,
                        "tr_5289_pvalues_str": "3.542e-15", "tr_5760_adjusted_pvalues": 4.814e-22,
                        "tr_5760_adjusted_pvalues_str": "4.814e-22", "tr_5760_aic": -244100,
                        "tr_5760_aic_str": "-244100.0", "tr_5760_estimates": -2.403e-14,
                        "tr_5760_estimates_str": "-2.403e-14", "tr_5760_log_adjusted_pvalues": -21.32,
                        "tr_5760_log_adjusted_pvalues_str": "-21.32", "tr_5760_pvalues": 8.344e-25,
                        "tr_5760_pvalues_str": "8.344e-25"},
                "671": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0175",
                        "cpd_name": "SM(d16:1/24:0)", "harmonised_annotation_id": "671",
                        "tr_5289_adjusted_pvalues": 1.336e-7, "tr_5289_adjusted_pvalues_str": "1.336e-07",
                        "tr_5289_aic": -185800, "tr_5289_aic_str": "-185800.0", "tr_5289_estimates": -9.164e-15,
                        "tr_5289_estimates_str": "-9.164e-15", "tr_5289_log_adjusted_pvalues": -6.874,
                        "tr_5289_log_adjusted_pvalues_str": "-6.874", "tr_5289_pvalues": 2.315e-10,
                        "tr_5289_pvalues_str": "2.315e-10", "tr_5760_adjusted_pvalues": 3.819e-33,
                        "tr_5760_adjusted_pvalues_str": "3.819e-33", "tr_5760_aic": -241900,
                        "tr_5760_aic_str": "-241900.0", "tr_5760_estimates": -3.503e-14,
                        "tr_5760_estimates_str": "-3.503e-14", "tr_5760_log_adjusted_pvalues": -32.42,
                        "tr_5760_log_adjusted_pvalues_str": "-32.42", "tr_5760_pvalues": 6.619e-36,
                        "tr_5760_pvalues_str": "6.619e-36"},
                "672": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0074", "cpd_name": "LPA(18:2/0:0)",
                        "harmonised_annotation_id": "672", "tr_5289_adjusted_pvalues": 5.034e-14,
                        "tr_5289_adjusted_pvalues_str": "5.034e-14", "tr_5289_aic": -173400,
                        "tr_5289_aic_str": "-173400.0", "tr_5289_estimates": -1.087e-13,
                        "tr_5289_estimates_str": "-1.087e-13", "tr_5289_log_adjusted_pvalues": -13.3,
                        "tr_5289_log_adjusted_pvalues_str": "-13.3", "tr_5289_pvalues": 8.724e-17,
                        "tr_5289_pvalues_str": "8.724e-17", "tr_5760_adjusted_pvalues": None,
                        "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None, "tr_5760_aic_str": None,
                        "tr_5760_estimates": None, "tr_5760_estimates_str": None, "tr_5760_log_adjusted_pvalues": None,
                        "tr_5760_log_adjusted_pvalues_str": None, "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "673": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0233", "cpd_name": "CAR(20:0)",
                        "harmonised_annotation_id": "673", "tr_5289_adjusted_pvalues": 5.002e-41,
                        "tr_5289_adjusted_pvalues_str": "5.002e-41", "tr_5289_aic": -176000,
                        "tr_5289_aic_str": "-176000.0", "tr_5289_estimates": 1.198e-13,
                        "tr_5289_estimates_str": "1.198e-13", "tr_5289_log_adjusted_pvalues": 40.3,
                        "tr_5289_log_adjusted_pvalues_str": "40.3", "tr_5289_pvalues": 8.669e-44,
                        "tr_5289_pvalues_str": "8.669e-44", "tr_5760_adjusted_pvalues": 2.033e-53,
                        "tr_5760_adjusted_pvalues_str": "2.033e-53", "tr_5760_aic": -234800,
                        "tr_5760_aic_str": "-234800.0", "tr_5760_estimates": 1.227e-13,
                        "tr_5760_estimates_str": "1.227e-13", "tr_5760_log_adjusted_pvalues": 52.69,
                        "tr_5760_log_adjusted_pvalues_str": "52.69", "tr_5760_pvalues": 3.523e-56,
                        "tr_5760_pvalues_str": "3.523e-56"},
                "678": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0002",
                        "cpd_name": "Decanoylcarnitine CAR(10:0)", "harmonised_annotation_id": "678",
                        "tr_5289_adjusted_pvalues": 167, "tr_5289_adjusted_pvalues_str": "167.0",
                        "tr_5289_aic": -178600, "tr_5289_aic_str": "-178600.0", "tr_5289_estimates": -6.074e-15,
                        "tr_5289_estimates_str": "-6.074e-15", "tr_5289_log_adjusted_pvalues": 2.223,
                        "tr_5289_log_adjusted_pvalues_str": "2.223", "tr_5289_pvalues": 0.2894,
                        "tr_5289_pvalues_str": "0.2894", "tr_5760_adjusted_pvalues": 7.63,
                        "tr_5760_adjusted_pvalues_str": "7.63", "tr_5760_aic": -236800, "tr_5760_aic_str": "-236800.0",
                        "tr_5760_estimates": 1.588e-14, "tr_5760_estimates_str": "1.588e-14",
                        "tr_5760_log_adjusted_pvalues": -0.8825, "tr_5760_log_adjusted_pvalues_str": "-0.8825",
                        "tr_5760_pvalues": 0.01322, "tr_5760_pvalues_str": "0.01322"},
                "679": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0123", "cpd_name": "MG(16:0)",
                        "harmonised_annotation_id": "679", "tr_5289_adjusted_pvalues": 0.00001441,
                        "tr_5289_adjusted_pvalues_str": "1.441e-05", "tr_5289_aic": -185800,
                        "tr_5289_aic_str": "-185800.0", "tr_5289_estimates": -8.775e-15,
                        "tr_5289_estimates_str": "-8.775e-15", "tr_5289_log_adjusted_pvalues": -4.841,
                        "tr_5289_log_adjusted_pvalues_str": "-4.841", "tr_5289_pvalues": 2.498e-8,
                        "tr_5289_pvalues_str": "2.498e-08", "tr_5760_adjusted_pvalues": 3.564e-14,
                        "tr_5760_adjusted_pvalues_str": "3.564e-14", "tr_5760_aic": -236300,
                        "tr_5760_aic_str": "-236300.0", "tr_5760_estimates": -5.113e-14,
                        "tr_5760_estimates_str": "-5.113e-14", "tr_5760_log_adjusted_pvalues": -13.45,
                        "tr_5760_log_adjusted_pvalues_str": "-13.45", "tr_5760_pvalues": 6.177e-17,
                        "tr_5760_pvalues_str": "6.177e-17"},
                "682": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0209", "cpd_name": "TG(48:3)",
                        "harmonised_annotation_id": "682", "tr_5289_adjusted_pvalues": 0.0000286,
                        "tr_5289_adjusted_pvalues_str": "2.86e-05", "tr_5289_aic": -188000,
                        "tr_5289_aic_str": "-188000.0", "tr_5289_estimates": 5.877e-15,
                        "tr_5289_estimates_str": "5.877e-15", "tr_5289_log_adjusted_pvalues": 4.544,
                        "tr_5289_log_adjusted_pvalues_str": "4.544", "tr_5289_pvalues": 4.957e-8,
                        "tr_5289_pvalues_str": "4.957e-08", "tr_5760_adjusted_pvalues": 6.758e-9,
                        "tr_5760_adjusted_pvalues_str": "6.758e-09", "tr_5760_aic": -236300,
                        "tr_5760_aic_str": "-236300.0", "tr_5760_estimates": 4.114e-14,
                        "tr_5760_estimates_str": "4.114e-14", "tr_5760_log_adjusted_pvalues": 8.17,
                        "tr_5760_log_adjusted_pvalues_str": "8.17", "tr_5760_pvalues": 1.171e-11,
                        "tr_5760_pvalues_str": "1.171e-11"},
                "684": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0277",
                        "cpd_name": "PC(O-22:1/22:5) and/or PC(P-22:0/22:5)", "harmonised_annotation_id": "684",
                        "tr_5289_adjusted_pvalues": 0.00009438, "tr_5289_adjusted_pvalues_str": "9.438e-05",
                        "tr_5289_aic": -185800, "tr_5289_aic_str": "-185800.0", "tr_5289_estimates": 8.26e-15,
                        "tr_5289_estimates_str": "8.26e-15", "tr_5289_log_adjusted_pvalues": 4.025,
                        "tr_5289_log_adjusted_pvalues_str": "4.025", "tr_5289_pvalues": 1.636e-7,
                        "tr_5289_pvalues_str": "1.636e-07", "tr_5760_adjusted_pvalues": 3.531e-19,
                        "tr_5760_adjusted_pvalues_str": "3.531e-19", "tr_5760_aic": -236800,
                        "tr_5760_aic_str": "-236800.0", "tr_5760_estimates": -5.537e-14,
                        "tr_5760_estimates_str": "-5.537e-14", "tr_5760_log_adjusted_pvalues": -18.45,
                        "tr_5760_log_adjusted_pvalues_str": "-18.45", "tr_5760_pvalues": 6.12e-22,
                        "tr_5760_pvalues_str": "6.12e-22"},
                "685": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0128", "cpd_name": "PC(16:0/16:0)",
                        "harmonised_annotation_id": "685", "tr_5289_adjusted_pvalues": 5.662e-9,
                        "tr_5289_adjusted_pvalues_str": "5.662e-09", "tr_5289_aic": -180500,
                        "tr_5289_aic_str": "-180500.0", "tr_5289_estimates": 2.505e-14,
                        "tr_5289_estimates_str": "2.505e-14", "tr_5289_log_adjusted_pvalues": 8.247,
                        "tr_5289_log_adjusted_pvalues_str": "8.247", "tr_5289_pvalues": 9.813e-12,
                        "tr_5289_pvalues_str": "9.813e-12", "tr_5760_adjusted_pvalues": 1.542e-17,
                        "tr_5760_adjusted_pvalues_str": "1.542e-17", "tr_5760_aic": -241200,
                        "tr_5760_aic_str": "-241200.0", "tr_5760_estimates": 2.905e-14,
                        "tr_5760_estimates_str": "2.905e-14", "tr_5760_log_adjusted_pvalues": 16.81,
                        "tr_5760_log_adjusted_pvalues_str": "16.81", "tr_5760_pvalues": 2.673e-20,
                        "tr_5760_pvalues_str": "2.673e-20"},
                "686": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0173",
                        "cpd_name": "SM(d16:1/20:0)", "harmonised_annotation_id": "686",
                        "tr_5289_adjusted_pvalues": 1.742e-11, "tr_5289_adjusted_pvalues_str": "1.742e-11",
                        "tr_5289_aic": -175800, "tr_5289_aic_str": "-175800.0", "tr_5289_estimates": -6.011e-14,
                        "tr_5289_estimates_str": "-6.011e-14", "tr_5289_log_adjusted_pvalues": -10.76,
                        "tr_5289_log_adjusted_pvalues_str": "-10.76", "tr_5289_pvalues": 3.02e-14,
                        "tr_5289_pvalues_str": "3.02e-14", "tr_5760_adjusted_pvalues": 4.02e-18,
                        "tr_5760_adjusted_pvalues_str": "4.02e-18", "tr_5760_aic": -236200,
                        "tr_5760_aic_str": "-236200.0", "tr_5760_estimates": -5.432e-14,
                        "tr_5760_estimates_str": "-5.432e-14", "tr_5760_log_adjusted_pvalues": -17.4,
                        "tr_5760_log_adjusted_pvalues_str": "-17.4", "tr_5760_pvalues": 6.967e-21,
                        "tr_5760_pvalues_str": "6.967e-21"},
                "687": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0296", "cpd_name": "TG(42:0)",
                        "harmonised_annotation_id": "687", "tr_5289_adjusted_pvalues": 0.5489,
                        "tr_5289_adjusted_pvalues_str": "0.5489", "tr_5289_aic": -178700,
                        "tr_5289_aic_str": "-178700.0", "tr_5289_estimates": 1.717e-14,
                        "tr_5289_estimates_str": "1.717e-14", "tr_5289_log_adjusted_pvalues": 0.2605,
                        "tr_5289_log_adjusted_pvalues_str": "0.2605", "tr_5289_pvalues": 0.0009512,
                        "tr_5289_pvalues_str": "0.0009512", "tr_5760_adjusted_pvalues": 1.818,
                        "tr_5760_adjusted_pvalues_str": "1.818", "tr_5760_aic": -237600, "tr_5760_aic_str": "-237600.0",
                        "tr_5760_estimates": 1.54e-14, "tr_5760_estimates_str": "1.54e-14",
                        "tr_5760_log_adjusted_pvalues": -0.2597, "tr_5760_log_adjusted_pvalues_str": "-0.2597",
                        "tr_5760_pvalues": 0.003151, "tr_5760_pvalues_str": "0.003151"},
                "688": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0380", "cpd_name": "Luteine",
                        "harmonised_annotation_id": "688", "tr_5289_adjusted_pvalues": None,
                        "tr_5289_adjusted_pvalues_str": None, "tr_5289_aic": "inf", "tr_5289_aic_str": "inf",
                        "tr_5289_estimates": 0, "tr_5289_estimates_str": "0.0", "tr_5289_log_adjusted_pvalues": None,
                        "tr_5289_log_adjusted_pvalues_str": None, "tr_5289_pvalues": None, "tr_5289_pvalues_str": None,
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "689": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0174",
                        "cpd_name": "SM(d16:1/22:0)", "harmonised_annotation_id": "689",
                        "tr_5289_adjusted_pvalues": 1.188e-10, "tr_5289_adjusted_pvalues_str": "1.188e-10",
                        "tr_5289_aic": -179400, "tr_5289_aic_str": "-179400.0", "tr_5289_estimates": 3.072e-14,
                        "tr_5289_estimates_str": "3.072e-14", "tr_5289_log_adjusted_pvalues": 9.925,
                        "tr_5289_log_adjusted_pvalues_str": "9.925", "tr_5289_pvalues": 2.059e-13,
                        "tr_5289_pvalues_str": "2.059e-13", "tr_5760_adjusted_pvalues": 8.079e-16,
                        "tr_5760_adjusted_pvalues_str": "8.079e-16", "tr_5760_aic": -245000,
                        "tr_5760_aic_str": "-245000.0", "tr_5760_estimates": 1.621e-14,
                        "tr_5760_estimates_str": "1.621e-14", "tr_5760_log_adjusted_pvalues": 15.09,
                        "tr_5760_log_adjusted_pvalues_str": "15.09", "tr_5760_pvalues": 1.4e-18,
                        "tr_5760_pvalues_str": "1.4e-18"},
                "691": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0199",
                        "cpd_name": "Sphingosine-1-phosphate", "harmonised_annotation_id": "691",
                        "tr_5289_adjusted_pvalues": 5.329e-11, "tr_5289_adjusted_pvalues_str": "5.329e-11",
                        "tr_5289_aic": -178200, "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": 3.819e-14,
                        "tr_5289_estimates_str": "3.819e-14", "tr_5289_log_adjusted_pvalues": 10.27,
                        "tr_5289_log_adjusted_pvalues_str": "10.27", "tr_5289_pvalues": 9.236e-14,
                        "tr_5289_pvalues_str": "9.236e-14", "tr_5760_adjusted_pvalues": 2.421e-8,
                        "tr_5760_adjusted_pvalues_str": "2.421e-08", "tr_5760_aic": -241200,
                        "tr_5760_aic_str": "-241200.0", "tr_5760_estimates": -1.973e-14,
                        "tr_5760_estimates_str": "-1.973e-14", "tr_5760_log_adjusted_pvalues": -7.616,
                        "tr_5760_log_adjusted_pvalues_str": "-7.616", "tr_5760_pvalues": 4.196e-11,
                        "tr_5760_pvalues_str": "4.196e-11"},
                "692": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0224", "cpd_name": "TG(54:2)",
                        "harmonised_annotation_id": "692", "tr_5289_adjusted_pvalues": 7.218e-8,
                        "tr_5289_adjusted_pvalues_str": "7.218e-08", "tr_5289_aic": -180100,
                        "tr_5289_aic_str": "-180100.0", "tr_5289_estimates": -2.708e-14,
                        "tr_5289_estimates_str": "-2.708e-14", "tr_5289_log_adjusted_pvalues": -7.142,
                        "tr_5289_log_adjusted_pvalues_str": "-7.142", "tr_5289_pvalues": 1.251e-10,
                        "tr_5289_pvalues_str": "1.251e-10", "tr_5760_adjusted_pvalues": 2.458e-8,
                        "tr_5760_adjusted_pvalues_str": "2.458e-08", "tr_5760_aic": -247900,
                        "tr_5760_aic_str": "-247900.0", "tr_5760_estimates": -9.547e-15,
                        "tr_5760_estimates_str": "-9.547e-15", "tr_5760_log_adjusted_pvalues": -7.609,
                        "tr_5760_log_adjusted_pvalues_str": "-7.609", "tr_5760_pvalues": 4.26e-11,
                        "tr_5760_pvalues_str": "4.26e-11"},
                "701": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0346", "cpd_name": "TG(56:8)",
                        "harmonised_annotation_id": "701", "tr_5289_adjusted_pvalues": 1.86e-13,
                        "tr_5289_adjusted_pvalues_str": "1.86e-13", "tr_5289_aic": -178800,
                        "tr_5289_aic_str": "-178800.0", "tr_5289_estimates": -4.01e-14,
                        "tr_5289_estimates_str": "-4.01e-14", "tr_5289_log_adjusted_pvalues": -12.73,
                        "tr_5289_log_adjusted_pvalues_str": "-12.73", "tr_5289_pvalues": 3.224e-16,
                        "tr_5289_pvalues_str": "3.224e-16", "tr_5760_adjusted_pvalues": 6.929e-12,
                        "tr_5760_adjusted_pvalues_str": "6.929e-12", "tr_5760_aic": -247900,
                        "tr_5760_aic_str": "-247900.0", "tr_5760_estimates": -1.06e-14,
                        "tr_5760_estimates_str": "-1.06e-14", "tr_5760_log_adjusted_pvalues": -11.16,
                        "tr_5760_log_adjusted_pvalues_str": "-11.16", "tr_5760_pvalues": 1.201e-14,
                        "tr_5760_pvalues_str": "1.201e-14"},
                "703": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0092", "cpd_name": "LPC(17:0/0:0)",
                        "harmonised_annotation_id": "703", "tr_5289_adjusted_pvalues": 0.01012,
                        "tr_5289_adjusted_pvalues_str": "0.01012", "tr_5289_aic": -181400,
                        "tr_5289_aic_str": "-181400.0", "tr_5289_estimates": -1.302e-14,
                        "tr_5289_estimates_str": "-1.302e-14", "tr_5289_log_adjusted_pvalues": -1.995,
                        "tr_5289_log_adjusted_pvalues_str": "-1.995", "tr_5289_pvalues": 0.00001753,
                        "tr_5289_pvalues_str": "1.753e-05", "tr_5760_adjusted_pvalues": 111,
                        "tr_5760_adjusted_pvalues_str": "111.0", "tr_5760_aic": -252500, "tr_5760_aic_str": "-252500.0",
                        "tr_5760_estimates": -9.465e-16, "tr_5760_estimates_str": "-9.465e-16",
                        "tr_5760_log_adjusted_pvalues": 2.045, "tr_5760_log_adjusted_pvalues_str": "2.045",
                        "tr_5760_pvalues": 0.1924, "tr_5760_pvalues_str": "0.1924"},
                "712": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0023", "cpd_name": "CAR(18:2)",
                        "harmonised_annotation_id": "712", "tr_5289_adjusted_pvalues": 498.3,
                        "tr_5289_adjusted_pvalues_str": "498.3", "tr_5289_aic": -178500, "tr_5289_aic_str": "-178500.0",
                        "tr_5289_estimates": 9.018e-16, "tr_5289_estimates_str": "9.018e-16",
                        "tr_5289_log_adjusted_pvalues": -2.698, "tr_5289_log_adjusted_pvalues_str": "-2.698",
                        "tr_5289_pvalues": 0.8637, "tr_5289_pvalues_str": "0.8637", "tr_5760_adjusted_pvalues": 393.1,
                        "tr_5760_adjusted_pvalues_str": "393.1", "tr_5760_aic": -245100, "tr_5760_aic_str": "-245100.0",
                        "tr_5760_estimates": -8.105e-16, "tr_5760_estimates_str": "-8.105e-16",
                        "tr_5760_log_adjusted_pvalues": 2.594, "tr_5760_log_adjusted_pvalues_str": "2.594",
                        "tr_5760_pvalues": 0.6812, "tr_5760_pvalues_str": "0.6812"},
                "717": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0284",
                        "cpd_name": "PC(O-24:1/22:5) and/or PC(P-24:0/22:5)", "harmonised_annotation_id": "717",
                        "tr_5289_adjusted_pvalues": 1.702e-19, "tr_5289_adjusted_pvalues_str": "1.702e-19",
                        "tr_5289_aic": -180800, "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": 3.484e-14,
                        "tr_5289_estimates_str": "3.484e-14", "tr_5289_log_adjusted_pvalues": 18.77,
                        "tr_5289_log_adjusted_pvalues_str": "18.77", "tr_5289_pvalues": 2.949e-22,
                        "tr_5289_pvalues_str": "2.949e-22", "tr_5760_adjusted_pvalues": 5.753e-9,
                        "tr_5760_adjusted_pvalues_str": "5.753e-09", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": -5.3e-15,
                        "tr_5760_estimates_str": "-5.3e-15", "tr_5760_log_adjusted_pvalues": -8.24,
                        "tr_5760_log_adjusted_pvalues_str": "-8.24", "tr_5760_pvalues": 9.971e-12,
                        "tr_5760_pvalues_str": "9.971e-12"},
                "718": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0145", "cpd_name": "PC(18:0/18:0)",
                        "harmonised_annotation_id": "718", "tr_5289_adjusted_pvalues": 5.926e-19,
                        "tr_5289_adjusted_pvalues_str": "5.926e-19", "tr_5289_aic": -176800,
                        "tr_5289_aic_str": "-176800.0", "tr_5289_estimates": -6.519e-14,
                        "tr_5289_estimates_str": "-6.519e-14", "tr_5289_log_adjusted_pvalues": -18.23,
                        "tr_5289_log_adjusted_pvalues_str": "-18.23", "tr_5289_pvalues": 1.027e-21,
                        "tr_5289_pvalues_str": "1.027e-21", "tr_5760_adjusted_pvalues": 3.036e-23,
                        "tr_5760_adjusted_pvalues_str": "3.036e-23", "tr_5760_aic": -243800,
                        "tr_5760_aic_str": "-243800.0", "tr_5760_estimates": 2.341e-14,
                        "tr_5760_estimates_str": "2.341e-14", "tr_5760_log_adjusted_pvalues": 22.52,
                        "tr_5760_log_adjusted_pvalues_str": "22.52", "tr_5760_pvalues": 5.261e-26,
                        "tr_5760_pvalues_str": "5.261e-26"},
                "721": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0272",
                        "cpd_name": "PC(O-18:0/22:4)", "harmonised_annotation_id": "721",
                        "tr_5289_adjusted_pvalues": 4.467e-25, "tr_5289_adjusted_pvalues_str": "4.467e-25",
                        "tr_5289_aic": -178900, "tr_5289_aic_str": "-178900.0", "tr_5289_estimates": 5.206e-14,
                        "tr_5289_estimates_str": "5.206e-14", "tr_5289_log_adjusted_pvalues": 24.35,
                        "tr_5289_log_adjusted_pvalues_str": "24.35", "tr_5289_pvalues": 7.742e-28,
                        "tr_5289_pvalues_str": "7.742e-28", "tr_5760_adjusted_pvalues": 4.57e-32,
                        "tr_5760_adjusted_pvalues_str": "4.57e-32", "tr_5760_aic": -235200,
                        "tr_5760_aic_str": "-235200.0", "tr_5760_estimates": 8.085e-14,
                        "tr_5760_estimates_str": "8.085e-14", "tr_5760_log_adjusted_pvalues": 31.34,
                        "tr_5760_log_adjusted_pvalues_str": "31.34", "tr_5760_pvalues": 7.921e-35,
                        "tr_5760_pvalues_str": "7.921e-35"},
                "723": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0045",
                        "cpd_name": "Cer(d18:1/24:0)", "harmonised_annotation_id": "723",
                        "tr_5289_adjusted_pvalues": 2.712e-30, "tr_5289_adjusted_pvalues_str": "2.712e-30",
                        "tr_5289_aic": -174100, "tr_5289_aic_str": "-174100.0", "tr_5289_estimates": -1.302e-13,
                        "tr_5289_estimates_str": "-1.302e-13", "tr_5289_log_adjusted_pvalues": -29.57,
                        "tr_5289_log_adjusted_pvalues_str": "-29.57", "tr_5289_pvalues": 4.7e-33,
                        "tr_5289_pvalues_str": "4.7e-33", "tr_5760_adjusted_pvalues": 5.138e-9,
                        "tr_5760_adjusted_pvalues_str": "5.138e-09", "tr_5760_aic": -252500,
                        "tr_5760_aic_str": "-252500.0", "tr_5760_estimates": 5.178e-15,
                        "tr_5760_estimates_str": "5.178e-15", "tr_5760_log_adjusted_pvalues": 8.289,
                        "tr_5760_log_adjusted_pvalues_str": "8.289", "tr_5760_pvalues": 8.905e-12,
                        "tr_5760_pvalues_str": "8.905e-12"},
                "724": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0213", "cpd_name": "TG(50:1)",
                        "harmonised_annotation_id": "724", "tr_5289_adjusted_pvalues": 4.426e-8,
                        "tr_5289_adjusted_pvalues_str": "4.426e-08", "tr_5289_aic": -189000,
                        "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": -6.045e-15,
                        "tr_5289_estimates_str": "-6.045e-15", "tr_5289_log_adjusted_pvalues": -7.354,
                        "tr_5289_log_adjusted_pvalues_str": "-7.354", "tr_5289_pvalues": 7.671e-11,
                        "tr_5289_pvalues_str": "7.671e-11", "tr_5760_adjusted_pvalues": 3.203e-14,
                        "tr_5760_adjusted_pvalues_str": "3.203e-14", "tr_5760_aic": -240800,
                        "tr_5760_aic_str": "-240800.0", "tr_5760_estimates": -2.93e-14,
                        "tr_5760_estimates_str": "-2.93e-14", "tr_5760_log_adjusted_pvalues": -13.49,
                        "tr_5760_log_adjusted_pvalues_str": "-13.49", "tr_5760_pvalues": 5.551e-17,
                        "tr_5760_pvalues_str": "5.551e-17"},
                "726": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0056", "cpd_name": "DG(16:0/16:0)",
                        "harmonised_annotation_id": "726", "tr_5289_adjusted_pvalues": 0.000001594,
                        "tr_5289_adjusted_pvalues_str": "1.594e-06", "tr_5289_aic": -183600,
                        "tr_5289_aic_str": "-183600.0", "tr_5289_estimates": -1.437e-14,
                        "tr_5289_estimates_str": "-1.437e-14", "tr_5289_log_adjusted_pvalues": -5.797,
                        "tr_5289_log_adjusted_pvalues_str": "-5.797", "tr_5289_pvalues": 2.763e-9,
                        "tr_5289_pvalues_str": "2.763e-09", "tr_5760_adjusted_pvalues": 0.00004648,
                        "tr_5760_adjusted_pvalues_str": "4.648e-05", "tr_5760_aic": -246200,
                        "tr_5760_aic_str": "-246200.0", "tr_5760_estimates": 9.883e-15,
                        "tr_5760_estimates_str": "9.883e-15", "tr_5760_log_adjusted_pvalues": 4.333,
                        "tr_5760_log_adjusted_pvalues_str": "4.333", "tr_5760_pvalues": 8.056e-8,
                        "tr_5760_pvalues_str": "8.056e-08"},
                "733": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0303", "cpd_name": "TG(49:1)",
                        "harmonised_annotation_id": "733", "tr_5289_adjusted_pvalues": 1.099e-7,
                        "tr_5289_adjusted_pvalues_str": "1.099e-07", "tr_5289_aic": -193000,
                        "tr_5289_aic_str": "-193000.0", "tr_5289_estimates": 2.954e-15,
                        "tr_5289_estimates_str": "2.954e-15", "tr_5289_log_adjusted_pvalues": 6.959,
                        "tr_5289_log_adjusted_pvalues_str": "6.959", "tr_5289_pvalues": 1.905e-10,
                        "tr_5289_pvalues_str": "1.905e-10", "tr_5760_adjusted_pvalues": 2.402e-11,
                        "tr_5760_adjusted_pvalues_str": "2.402e-11", "tr_5760_aic": -233600,
                        "tr_5760_aic_str": "-233600.0", "tr_5760_estimates": -6.454e-14,
                        "tr_5760_estimates_str": "-6.454e-14", "tr_5760_log_adjusted_pvalues": -10.62,
                        "tr_5760_log_adjusted_pvalues_str": "-10.62", "tr_5760_pvalues": 4.162e-14,
                        "tr_5760_pvalues_str": "4.162e-14"},
                "734": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0019",
                        "cpd_name": "Stearoylcarnitine CAR(18:0)", "harmonised_annotation_id": "734",
                        "tr_5289_adjusted_pvalues": 2.735e-7, "tr_5289_adjusted_pvalues_str": "2.735e-07",
                        "tr_5289_aic": -181200, "tr_5289_aic_str": "-181200.0", "tr_5289_estimates": 2.11e-14,
                        "tr_5289_estimates_str": "2.11e-14", "tr_5289_log_adjusted_pvalues": 6.563,
                        "tr_5289_log_adjusted_pvalues_str": "6.563", "tr_5289_pvalues": 4.74e-10,
                        "tr_5289_pvalues_str": "4.74e-10", "tr_5760_adjusted_pvalues": 1.415e-9,
                        "tr_5760_adjusted_pvalues_str": "1.415e-09", "tr_5760_aic": -235200,
                        "tr_5760_aic_str": "-235200.0", "tr_5760_estimates": 4.882e-14,
                        "tr_5760_estimates_str": "4.882e-14", "tr_5760_log_adjusted_pvalues": 8.849,
                        "tr_5760_log_adjusted_pvalues_str": "8.849", "tr_5760_pvalues": 2.453e-12,
                        "tr_5760_pvalues_str": "2.453e-12"},
                "736": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0010", "cpd_name": "CAR(12:1-OH)",
                        "harmonised_annotation_id": "736", "tr_5289_adjusted_pvalues": 86.06,
                        "tr_5289_adjusted_pvalues_str": "86.06", "tr_5289_aic": -176700, "tr_5289_aic_str": "-176700.0",
                        "tr_5289_estimates": -1.016e-14, "tr_5289_estimates_str": "-1.016e-14",
                        "tr_5289_log_adjusted_pvalues": 1.935, "tr_5289_log_adjusted_pvalues_str": "1.935",
                        "tr_5289_pvalues": 0.1492, "tr_5289_pvalues_str": "0.1492", "tr_5760_adjusted_pvalues": 14.44,
                        "tr_5760_adjusted_pvalues_str": "14.44", "tr_5760_aic": -239500, "tr_5760_aic_str": "-239500.0",
                        "tr_5760_estimates": -8.746e-15, "tr_5760_estimates_str": "-8.746e-15",
                        "tr_5760_log_adjusted_pvalues": 1.16, "tr_5760_log_adjusted_pvalues_str": "1.16",
                        "tr_5760_pvalues": 0.02503, "tr_5760_pvalues_str": "0.02503"},
                "739": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0315", "cpd_name": "TG(52:6)_1",
                        "harmonised_annotation_id": "739", "tr_5289_adjusted_pvalues": 0.002945,
                        "tr_5289_adjusted_pvalues_str": "0.002945", "tr_5289_aic": -180800,
                        "tr_5289_aic_str": "-180800.0", "tr_5289_estimates": 1.653e-14,
                        "tr_5289_estimates_str": "1.653e-14", "tr_5289_log_adjusted_pvalues": 2.531,
                        "tr_5289_log_adjusted_pvalues_str": "2.531", "tr_5289_pvalues": 0.000005103,
                        "tr_5289_pvalues_str": "5.103e-06", "tr_5760_adjusted_pvalues": 0.0009142,
                        "tr_5760_adjusted_pvalues_str": "0.0009142", "tr_5760_aic": -241800,
                        "tr_5760_aic_str": "-241800.0", "tr_5760_estimates": -1.448e-14,
                        "tr_5760_estimates_str": "-1.448e-14", "tr_5760_log_adjusted_pvalues": -3.039,
                        "tr_5760_log_adjusted_pvalues_str": "-3.039", "tr_5760_pvalues": 0.000001584,
                        "tr_5760_pvalues_str": "1.584e-06"},
                "742": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0294",
                        "cpd_name": "SM(d32:1);  SM(d16:1/16:0) | SM(d18:1/14:0)", "harmonised_annotation_id": "742",
                        "tr_5289_adjusted_pvalues": 3.515e-12, "tr_5289_adjusted_pvalues_str": "3.515e-12",
                        "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0", "tr_5289_estimates": 6.811e-15,
                        "tr_5289_estimates_str": "6.811e-15", "tr_5289_log_adjusted_pvalues": 11.45,
                        "tr_5289_log_adjusted_pvalues_str": "11.45", "tr_5289_pvalues": 6.091e-15,
                        "tr_5289_pvalues_str": "6.091e-15", "tr_5760_adjusted_pvalues": 1.338e-59,
                        "tr_5760_adjusted_pvalues_str": "1.338e-59", "tr_5760_aic": -241000,
                        "tr_5760_aic_str": "-241000.0", "tr_5760_estimates": -5.373e-14,
                        "tr_5760_estimates_str": "-5.373e-14", "tr_5760_log_adjusted_pvalues": -58.87,
                        "tr_5760_log_adjusted_pvalues_str": "-58.87", "tr_5760_pvalues": 2.32e-62,
                        "tr_5760_pvalues_str": "2.32e-62"},
                "743": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0164",
                        "cpd_name": "PC(O-18:0/16:0)", "harmonised_annotation_id": "743",
                        "tr_5289_adjusted_pvalues": 0.3767, "tr_5289_adjusted_pvalues_str": "0.3767",
                        "tr_5289_aic": -185000, "tr_5289_aic_str": "-185000.0", "tr_5289_estimates": -5.607e-15,
                        "tr_5289_estimates_str": "-5.607e-15", "tr_5289_log_adjusted_pvalues": -0.424,
                        "tr_5289_log_adjusted_pvalues_str": "-0.424", "tr_5289_pvalues": 0.0006529,
                        "tr_5289_pvalues_str": "0.0006529", "tr_5760_adjusted_pvalues": 0.05666,
                        "tr_5760_adjusted_pvalues_str": "0.05666", "tr_5760_aic": -233900,
                        "tr_5760_aic_str": "-233900.0", "tr_5760_estimates": 2.96e-14,
                        "tr_5760_estimates_str": "2.96e-14", "tr_5760_log_adjusted_pvalues": 1.247,
                        "tr_5760_log_adjusted_pvalues_str": "1.247", "tr_5760_pvalues": 0.0000982,
                        "tr_5760_pvalues_str": "9.82e-05"},
                "745": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0161",
                        "cpd_name": "PC(O-16:0/16:0)", "harmonised_annotation_id": "745",
                        "tr_5289_adjusted_pvalues": 0.3154, "tr_5289_adjusted_pvalues_str": "0.3154",
                        "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0", "tr_5289_estimates": -5.158e-15,
                        "tr_5289_estimates_str": "-5.158e-15", "tr_5289_log_adjusted_pvalues": -0.5012,
                        "tr_5289_log_adjusted_pvalues_str": "-0.5012", "tr_5289_pvalues": 0.0005466,
                        "tr_5289_pvalues_str": "0.0005466", "tr_5760_adjusted_pvalues": 5.069e-7,
                        "tr_5760_adjusted_pvalues_str": "5.069e-07", "tr_5760_aic": -236300,
                        "tr_5760_aic_str": "-236300.0", "tr_5760_estimates": -3.479e-14,
                        "tr_5760_estimates_str": "-3.479e-14", "tr_5760_log_adjusted_pvalues": -6.295,
                        "tr_5760_log_adjusted_pvalues_str": "-6.295", "tr_5760_pvalues": 8.785e-10,
                        "tr_5760_pvalues_str": "8.785e-10"},
                "746": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0207", "cpd_name": "TG(48:1)",
                        "harmonised_annotation_id": "746", "tr_5289_adjusted_pvalues": 1.294e-7,
                        "tr_5289_adjusted_pvalues_str": "1.294e-07", "tr_5289_aic": -185100,
                        "tr_5289_aic_str": "-185100.0", "tr_5289_estimates": 1.119e-14,
                        "tr_5289_estimates_str": "1.119e-14", "tr_5289_log_adjusted_pvalues": 6.888,
                        "tr_5289_log_adjusted_pvalues_str": "6.888", "tr_5289_pvalues": 2.243e-10,
                        "tr_5289_pvalues_str": "2.243e-10", "tr_5760_adjusted_pvalues": 8.94e-15,
                        "tr_5760_adjusted_pvalues_str": "8.94e-15", "tr_5760_aic": -237800,
                        "tr_5760_aic_str": "-237800.0", "tr_5760_estimates": 4.293e-14,
                        "tr_5760_estimates_str": "4.293e-14", "tr_5760_log_adjusted_pvalues": 14.05,
                        "tr_5760_log_adjusted_pvalues_str": "14.05", "tr_5760_pvalues": 1.549e-17,
                        "tr_5760_pvalues_str": "1.549e-17"},
                "750": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0365", "cpd_name": "TG(60:4)_2",
                        "harmonised_annotation_id": "750", "tr_5289_adjusted_pvalues": 5.261,
                        "tr_5289_adjusted_pvalues_str": "5.261", "tr_5289_aic": -183400, "tr_5289_aic_str": "-183400.0",
                        "tr_5289_estimates": -6.773e-15, "tr_5289_estimates_str": "-6.773e-15",
                        "tr_5289_log_adjusted_pvalues": 0.7211, "tr_5289_log_adjusted_pvalues_str": "0.7211",
                        "tr_5289_pvalues": 0.009118, "tr_5289_pvalues_str": "0.009118",
                        "tr_5760_adjusted_pvalues": None, "tr_5760_adjusted_pvalues_str": None, "tr_5760_aic": None,
                        "tr_5760_aic_str": None, "tr_5760_estimates": None, "tr_5760_estimates_str": None,
                        "tr_5760_log_adjusted_pvalues": None, "tr_5760_log_adjusted_pvalues_str": None,
                        "tr_5760_pvalues": None, "tr_5760_pvalues_str": None},
                "754": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0201", "cpd_name": "TG(44:1)",
                        "harmonised_annotation_id": "754", "tr_5289_adjusted_pvalues": 1.146,
                        "tr_5289_adjusted_pvalues_str": "1.146", "tr_5289_aic": -189000, "tr_5289_aic_str": "-189000.0",
                        "tr_5289_estimates": -2.86e-15, "tr_5289_estimates_str": "-2.86e-15",
                        "tr_5289_log_adjusted_pvalues": 0.05922, "tr_5289_log_adjusted_pvalues_str": "0.05922",
                        "tr_5289_pvalues": 0.001986, "tr_5289_pvalues_str": "0.001986",
                        "tr_5760_adjusted_pvalues": 0.00001464, "tr_5760_adjusted_pvalues_str": "1.464e-05",
                        "tr_5760_aic": -239700, "tr_5760_aic_str": "-239700.0", "tr_5760_estimates": -2.253e-14,
                        "tr_5760_estimates_str": "-2.253e-14", "tr_5760_log_adjusted_pvalues": -4.835,
                        "tr_5760_log_adjusted_pvalues_str": "-4.835", "tr_5760_pvalues": 2.536e-8,
                        "tr_5760_pvalues_str": "2.536e-08"},
                "757": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0275",
                        "cpd_name": "PC(O-22:0/20:3)", "harmonised_annotation_id": "757",
                        "tr_5289_adjusted_pvalues": 2.246e-12, "tr_5289_adjusted_pvalues_str": "2.246e-12",
                        "tr_5289_aic": -184800, "tr_5289_aic_str": "-184800.0", "tr_5289_estimates": -1.401e-14,
                        "tr_5289_estimates_str": "-1.401e-14", "tr_5289_log_adjusted_pvalues": -11.65,
                        "tr_5289_log_adjusted_pvalues_str": "-11.65", "tr_5289_pvalues": 3.892e-15,
                        "tr_5289_pvalues_str": "3.892e-15", "tr_5760_adjusted_pvalues": 1.91e-11,
                        "tr_5760_adjusted_pvalues_str": "1.91e-11", "tr_5760_aic": -241800,
                        "tr_5760_aic_str": "-241800.0", "tr_5760_estimates": 2.19e-14,
                        "tr_5760_estimates_str": "2.19e-14", "tr_5760_log_adjusted_pvalues": 10.72,
                        "tr_5760_log_adjusted_pvalues_str": "10.72", "tr_5760_pvalues": 3.31e-14,
                        "tr_5760_pvalues_str": "3.31e-14"},
                "758": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0078", "cpd_name": "LPC(0:0/16:0)",
                        "harmonised_annotation_id": "758", "tr_5289_adjusted_pvalues": 83.54,
                        "tr_5289_adjusted_pvalues_str": "83.54", "tr_5289_aic": -185700, "tr_5289_aic_str": "-185700.0",
                        "tr_5289_estimates": 2.258e-15, "tr_5289_estimates_str": "2.258e-15",
                        "tr_5289_log_adjusted_pvalues": -1.922, "tr_5289_log_adjusted_pvalues_str": "-1.922",
                        "tr_5289_pvalues": 0.1448, "tr_5289_pvalues_str": "0.1448", "tr_5760_adjusted_pvalues": 16.76,
                        "tr_5760_adjusted_pvalues_str": "16.76", "tr_5760_aic": -239300, "tr_5760_aic_str": "-239300.0",
                        "tr_5760_estimates": 8.894e-15, "tr_5760_estimates_str": "8.894e-15",
                        "tr_5760_log_adjusted_pvalues": -1.224, "tr_5760_log_adjusted_pvalues_str": "-1.224",
                        "tr_5760_pvalues": 0.02905, "tr_5760_pvalues_str": "0.02905"},
                "763": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0118",
                        "cpd_name": "LPC(P-18:0/0:0)", "harmonised_annotation_id": "763",
                        "tr_5289_adjusted_pvalues": 134.7, "tr_5289_adjusted_pvalues_str": "134.7",
                        "tr_5289_aic": -180900, "tr_5289_aic_str": "-180900.0", "tr_5289_estimates": -4.09e-15,
                        "tr_5289_estimates_str": "-4.09e-15", "tr_5289_log_adjusted_pvalues": 2.129,
                        "tr_5289_log_adjusted_pvalues_str": "2.129", "tr_5289_pvalues": 0.2334,
                        "tr_5289_pvalues_str": "0.2334", "tr_5760_adjusted_pvalues": 379.2,
                        "tr_5760_adjusted_pvalues_str": "379.2", "tr_5760_aic": -233800, "tr_5760_aic_str": "-233800.0",
                        "tr_5760_estimates": 3.52e-15, "tr_5760_estimates_str": "3.52e-15",
                        "tr_5760_log_adjusted_pvalues": -2.579, "tr_5760_log_adjusted_pvalues_str": "-2.579",
                        "tr_5760_pvalues": 0.6573, "tr_5760_pvalues_str": "0.6573"},
                "765": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0100", "cpd_name": "LPC(19:0/0:0)",
                        "harmonised_annotation_id": "765", "tr_5289_adjusted_pvalues": 0.2421,
                        "tr_5289_adjusted_pvalues_str": "0.2421", "tr_5289_aic": -178200,
                        "tr_5289_aic_str": "-178200.0", "tr_5289_estimates": 1.918e-14,
                        "tr_5289_estimates_str": "1.918e-14", "tr_5289_log_adjusted_pvalues": 0.616,
                        "tr_5289_log_adjusted_pvalues_str": "0.616", "tr_5289_pvalues": 0.0004196,
                        "tr_5289_pvalues_str": "0.0004196", "tr_5760_adjusted_pvalues": 0.9569,
                        "tr_5760_adjusted_pvalues_str": "0.9569", "tr_5760_aic": -239600,
                        "tr_5760_aic_str": "-239600.0", "tr_5760_estimates": -1.207e-14,
                        "tr_5760_estimates_str": "-1.207e-14", "tr_5760_log_adjusted_pvalues": -0.01912,
                        "tr_5760_log_adjusted_pvalues_str": "-0.01912", "tr_5760_pvalues": 0.001658,
                        "tr_5760_pvalues_str": "0.001658"},
                "767": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0027", "cpd_name": "CAR(20:3)",
                        "harmonised_annotation_id": "767", "tr_5289_adjusted_pvalues": 234.1,
                        "tr_5289_adjusted_pvalues_str": "234.1", "tr_5289_aic": -193200, "tr_5289_aic_str": "-193200.0",
                        "tr_5289_estimates": -3.841e-16, "tr_5289_estimates_str": "-3.841e-16",
                        "tr_5289_log_adjusted_pvalues": 2.369, "tr_5289_log_adjusted_pvalues_str": "2.369",
                        "tr_5289_pvalues": 0.4057, "tr_5289_pvalues_str": "0.4057", "tr_5760_adjusted_pvalues": 378.9,
                        "tr_5760_adjusted_pvalues_str": "378.9", "tr_5760_aic": -241000, "tr_5760_aic_str": "-241000.0",
                        "tr_5760_estimates": -1.526e-15, "tr_5760_estimates_str": "-1.526e-15",
                        "tr_5760_log_adjusted_pvalues": 2.579, "tr_5760_log_adjusted_pvalues_str": "2.579",
                        "tr_5760_pvalues": 0.6568, "tr_5760_pvalues_str": "0.6568"},
                "773": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0300", "cpd_name": "TG(47:1)",
                        "harmonised_annotation_id": "773", "tr_5289_adjusted_pvalues": 4.527e-9,
                        "tr_5289_adjusted_pvalues_str": "4.527e-09", "tr_5289_aic": -179800,
                        "tr_5289_aic_str": "-179800.0", "tr_5289_estimates": 2.937e-14,
                        "tr_5289_estimates_str": "2.937e-14", "tr_5289_log_adjusted_pvalues": 8.344,
                        "tr_5289_log_adjusted_pvalues_str": "8.344", "tr_5289_pvalues": 7.846e-12,
                        "tr_5289_pvalues_str": "7.846e-12", "tr_5760_adjusted_pvalues": 1.471e-8,
                        "tr_5760_adjusted_pvalues_str": "1.471e-08", "tr_5760_aic": -232100,
                        "tr_5760_aic_str": "-232100.0", "tr_5760_estimates": -6.837e-14,
                        "tr_5760_estimates_str": "-6.837e-14", "tr_5760_log_adjusted_pvalues": -7.832,
                        "tr_5760_log_adjusted_pvalues_str": "-7.832", "tr_5760_pvalues": 2.55e-11,
                        "tr_5760_pvalues_str": "2.55e-11"},
                "778": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0126", "cpd_name": "PC(14:0/18:2)",
                        "harmonised_annotation_id": "778", "tr_5289_adjusted_pvalues": 0.002523,
                        "tr_5289_adjusted_pvalues_str": "0.002523", "tr_5289_aic": -179300,
                        "tr_5289_aic_str": "-179300.0", "tr_5289_estimates": -1.996e-14,
                        "tr_5289_estimates_str": "-1.996e-14", "tr_5289_log_adjusted_pvalues": -2.598,
                        "tr_5289_log_adjusted_pvalues_str": "-2.598", "tr_5289_pvalues": 0.000004373,
                        "tr_5289_pvalues_str": "4.373e-06", "tr_5760_adjusted_pvalues": 0.003754,
                        "tr_5760_adjusted_pvalues_str": "0.003754", "tr_5760_aic": -239300,
                        "tr_5760_aic_str": "-239300.0", "tr_5760_estimates": 1.749e-14,
                        "tr_5760_estimates_str": "1.749e-14", "tr_5760_log_adjusted_pvalues": 2.426,
                        "tr_5760_log_adjusted_pvalues_str": "2.426", "tr_5760_pvalues": 0.000006506,
                        "tr_5760_pvalues_str": "6.506e-06"},
                "779": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0138",
                        "cpd_name": "PC(16:0/20:4)_2", "harmonised_annotation_id": "779",
                        "tr_5289_adjusted_pvalues": 0.2711, "tr_5289_adjusted_pvalues_str": "0.2711",
                        "tr_5289_aic": -174600, "tr_5289_aic_str": "-174600.0", "tr_5289_estimates": 4.012e-14,
                        "tr_5289_estimates_str": "4.012e-14", "tr_5289_log_adjusted_pvalues": 0.5668,
                        "tr_5289_log_adjusted_pvalues_str": "0.5668", "tr_5289_pvalues": 0.0004699,
                        "tr_5289_pvalues_str": "0.0004699", "tr_5760_adjusted_pvalues": 8.247,
                        "tr_5760_adjusted_pvalues_str": "8.247", "tr_5760_aic": -249200, "tr_5760_aic_str": "-249200.0",
                        "tr_5760_estimates": -3.082e-15, "tr_5760_estimates_str": "-3.082e-15",
                        "tr_5760_log_adjusted_pvalues": 0.9163, "tr_5760_log_adjusted_pvalues_str": "0.9163",
                        "tr_5760_pvalues": 0.01429, "tr_5760_pvalues_str": "0.01429"},
                "785": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0254", "cpd_name": "LPE(0:0/18:0)",
                        "harmonised_annotation_id": "785", "tr_5289_adjusted_pvalues": 1.411e-16,
                        "tr_5289_adjusted_pvalues_str": "1.411e-16", "tr_5289_aic": -175300,
                        "tr_5289_aic_str": "-175300.0", "tr_5289_estimates": 7.666e-14,
                        "tr_5289_estimates_str": "7.666e-14", "tr_5289_log_adjusted_pvalues": 15.85,
                        "tr_5289_log_adjusted_pvalues_str": "15.85", "tr_5289_pvalues": 2.446e-19,
                        "tr_5289_pvalues_str": "2.446e-19", "tr_5760_adjusted_pvalues": 1.105e-15,
                        "tr_5760_adjusted_pvalues_str": "1.105e-15", "tr_5760_aic": -232900,
                        "tr_5760_aic_str": "-232900.0", "tr_5760_estimates": -7.601e-14,
                        "tr_5760_estimates_str": "-7.601e-14", "tr_5760_log_adjusted_pvalues": -14.96,
                        "tr_5760_log_adjusted_pvalues_str": "-14.96", "tr_5760_pvalues": 1.916e-18,
                        "tr_5760_pvalues_str": "1.916e-18"},
                "787": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0030",
                        "cpd_name": "Hexacosanoylcarnitine CAR(26:0)", "harmonised_annotation_id": "787",
                        "tr_5289_adjusted_pvalues": 5.391e-19, "tr_5289_adjusted_pvalues_str": "5.391e-19",
                        "tr_5289_aic": -174300, "tr_5289_aic_str": "-174300.0", "tr_5289_estimates": -1.114e-13,
                        "tr_5289_estimates_str": "-1.114e-13", "tr_5289_log_adjusted_pvalues": -18.27,
                        "tr_5289_log_adjusted_pvalues_str": "-18.27", "tr_5289_pvalues": 9.343e-22,
                        "tr_5289_pvalues_str": "9.343e-22", "tr_5760_adjusted_pvalues": 1.374e-22,
                        "tr_5760_adjusted_pvalues_str": "1.374e-22", "tr_5760_aic": -242900,
                        "tr_5760_aic_str": "-242900.0", "tr_5760_estimates": -2.974e-14,
                        "tr_5760_estimates_str": "-2.974e-14", "tr_5760_log_adjusted_pvalues": -21.86,
                        "tr_5760_log_adjusted_pvalues_str": "-21.86", "tr_5760_pvalues": 2.382e-25,
                        "tr_5760_pvalues_str": "2.382e-25"},
                "792": {"annotation_method": "PPR", "assay": "LPOS", "cpd_id": "LPOS-0313", "cpd_name": "TG(52:5)_2",
                        "harmonised_annotation_id": "792", "tr_5289_adjusted_pvalues": 6.805e-12,
                        "tr_5289_adjusted_pvalues_str": "6.805e-12", "tr_5289_aic": -178400,
                        "tr_5289_aic_str": "-178400.0", "tr_5289_estimates": 4.238e-14,
                        "tr_5289_estimates_str": "4.238e-14", "tr_5289_log_adjusted_pvalues": 11.17,
                        "tr_5289_log_adjusted_pvalues_str": "11.17", "tr_5289_pvalues": 1.179e-14,
                        "tr_5289_pvalues_str": "1.179e-14", "tr_5760_adjusted_pvalues": 2.967e-15,
                        "tr_5760_adjusted_pvalues_str": "2.967e-15", "tr_5760_aic": -245100,
                        "tr_5760_aic_str": "-245100.0", "tr_5760_estimates": 1.772e-14,
                        "tr_5760_estimates_str": "1.772e-14", "tr_5760_log_adjusted_pvalues": 14.53,
                        "tr_5760_log_adjusted_pvalues_str": "14.53", "tr_5760_pvalues": 5.142e-18,
                        "tr_5760_pvalues_str": "5.142e-18"}}

        dataframe = pd.DataFrame.from_dict(data)
        dataframe = dataframe.transpose()

        pass

    def test_noesy_biquant_scaling(self):

        task = RunPCA(saved_query_id=169,scaling='med')
        task.run()
        pass











