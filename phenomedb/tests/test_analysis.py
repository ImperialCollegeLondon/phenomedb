import pytest
import random

import pandas as pd

import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])

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

    def test_a_run_pca_saved_query(self,create_min_database,
                                   create_pipeline_testing_project,
                                   create_nmr_assays,
                                   create_ms_assays,
                                   create_annotation_methods,
                                   import_devset_sample_manifest,
                                   import_devset_ivdr_bilisa_annotations,
                                   import_devset_lpos_peakpanther_annotations,
                                   create_age_sex_harmonised_fields,
                                   dummy_harmonise_annotations,
                                    create_saved_queries):

        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name=='test_query_bilisa').first()
        task = RunPCA(saved_query_id=saved_query.id,username='testuser',reload_cache=True)
        output = task.run()

        assert isinstance(output,dict)
        assert 'ncomps' in output.keys()
        assert 'scores' in output.keys()
        assert 'loadings' in output.keys()

    def test_a_run_pca_multi_project(self,create_min_database,
                                   create_pipeline_testing_project,
                                   create_nmr_assays,
                                   create_ms_assays,
                                   create_annotation_methods,
                                   import_devset_sample_manifest,
                                   import_devset_ivdr_bilisa_annotations,
                                   import_devset_lpos_peakpanther_annotations,
                                     create_age_sex_harmonised_fields,
                                     dummy_harmonise_annotations,
                                    create_saved_queries):
        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_bilisa_2_projects').first()
        task = RunPCA(saved_query_id=saved_query.id,exclude_features_not_in_all_projects=True,
                      scaling='uv',transform='log',correction_type='SR',
                      harmonise_annotations=True,sample_types=["StudySample"])
        output = task.run()

        assert isinstance(output, dict)
        assert 'ncomps' in output.keys()
        assert 'scores' in output.keys()
        assert 'loadings' in output.keys()

    def test_a_run_pca_compare_scaling(self,create_min_database,
                                   create_pipeline_testing_project,
                                   create_nmr_assays,
                                   create_ms_assays,
                                   create_annotation_methods,
                                   import_devset_sample_manifest,
                                   import_devset_ivdr_bilisa_annotations,
                                   import_devset_lpos_peakpanther_annotations,
                                    create_age_sex_harmonised_fields,
                                       dummy_harmonise_annotations,
                                    create_saved_queries):

        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_lpos').first()

        task = RunPCA(saved_query_id=saved_query.id,username='testuser',scaling='log')
        output = task.run()
        print('Log transform: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=saved_query.id, username='testuser', scaling='uv')
        output = task.run()
        print('UV transform: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

    def test_a_run_pcpr2(self,
                         create_min_database,
                         create_pipeline_testing_project,
                         create_nmr_assays,
                         create_ms_assays,
                         create_annotation_methods,
                         import_devset_sample_manifest,
                         import_devset_ivdr_bilisa_annotations,
                         import_devset_lpos_peakpanther_annotations,
                         create_age_sex_harmonised_fields,
                         dummy_harmonise_annotations,
                         create_saved_queries
                         ):

        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_bilisa').first()

        task = RunPCPR2(saved_query_id=saved_query.id, correction_type='SR',columns_to_include=['Project'])
        output = task.run()
        print('PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCPR2(saved_query_id=saved_query.id, correction_type='SR', include_harmonised_metadata=False)
        output = task.run()
        print('PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)


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


    def test_multi_pcpr2(self,create_min_database,
                                   create_pipeline_testing_project,
                                   create_nmr_assays,
                                   create_ms_assays,
                                   create_annotation_methods,
                                   import_devset_sample_manifest,
                                   import_devset_ivdr_bilisa_annotations,
                                   import_devset_lpos_peakpanther_annotations,
                                    create_age_sex_harmonised_fields,
                                       dummy_harmonise_annotations,
                                    create_saved_queries):

        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_bilisa').first()

        args = {'columns_to_include': ['Project', 'Sample Matrix'],
                 'correction_type': 'SR',
                 'db_env': 'PROD',
                 'exclude_features_not_in_all_projects': True,
                 'harmonise_annotations': True,
                 'reload_cache': False,
                 'saved_query_id': saved_query.id,
                 'saved_query_model': 'AnnotatedFeature'}
        task = RunPCPR2(**args)
        task.run()

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

    def test_combined_generator(self,create_min_database,
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

        query_factory = QueryFactory(saved_query_id=saved_query.id)
        query_factory.build_intensity_data_sample_metadata_and_feature_metadata()
        combined = utils.build_combined_dataframe_from_seperate(
            query_factory.dataframes['intensity_data::AnnotatedFeature'],
            query_factory.dataframes['sample_metadata::AnnotatedFeature'],
            query_factory.dataframes['feature_metadata::AnnotatedFeature'])

        assert isinstance(combined,pd.DataFrame) == True
        assert combined.shape == (query_factory.dataframes['sample_metadata::AnnotatedFeature'].shape[0],query_factory.dataframes['sample_metadata::AnnotatedFeature'].shape[1] + query_factory.dataframes['feature_metadata::AnnotatedFeature'].shape[0])

    def test_combined_generator_from_task_run(self,create_min_database,
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

        db_session = db.get_db_session()
        cache = Cache()
        task_run = db_session.query(TaskRun).filter(TaskRun.class_name == 'RunPCA').first()
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

    def test_mwas_tools(self,create_min_database,
                         create_pipeline_testing_project,
                         create_lab,
                         create_nmr_assays,
                         create_annotation_methods,
                         import_devset_sample_manifest,
                         import_devset_ivdr_bilisa_annotations,
                         create_age_sex_harmonised_fields,
                         dummy_harmonise_annotations,
                         create_saved_queries):
        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_lpos').first()

        task = RunMWAS(saved_query_id=saved_query.id,correction_type='SR',scaling='uv',transform='log',reload_cache=False,model_Y_ci=0.8,
                       model_Y_variable='h_metadata::Age',model_X_variables=['h_metadata::Sex','h_metadata::BMI'])
        task.run()
        print("task: %s" % task.task_run.id)

        task2 = RunMWAS(saved_query_id=saved_query.id, correction_type='SR', scaling='uv', transform='log',model_Y_min=25,model_Y_max=60,
                       model_Y_variable='h_metadata::Age', model_X_variables=['h_metadata::Sex','h_metadata::BMI'])
        task2.run()
        print("task: %s" % task2.task_run.id)

    def test_mwas_2_projects(self,create_min_database,
                         create_pipeline_testing_project,
                         create_lab,
                         create_nmr_assays,
                         create_annotation_methods,
                         import_devset_sample_manifest,
                         import_devset_ivdr_bilisa_annotations,
                         create_age_sex_harmonised_fields,
                         dummy_harmonise_annotations,
                         create_saved_queries):
        saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name == 'test_query_bilisa_2_projects').first()

        task = RunMWAS(saved_query_id=saved_query.id,correction_type='SR',scaling='uv',transform='log',reload_cache=False,model_Y_ci=0.9,
                       model_Y_variable='h_metadata::Age',model_X_variables=['h_metadata::Sex','h_metadata::BMI',"Project","Sample Matrix"])
        task.run()
        print("task: %s" % task.task_run.id)







