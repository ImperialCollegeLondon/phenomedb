import pytest
import random

import pandas as pd

import sys, os
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *
from phenomedb.query_factory import *
from phenomedb.imports import *

from phenomedb.config import config

DB_ENV = "TEST"
PROJECT_NAME = "PipelineTesting"
LAB_NAME = "TestLab"
LAB_AFFILIATION = "TestUniversity"
USERNAME = config['PIPELINES']['pipeline_manager_user']

db_session = db.get_test_database_session()

class TestImports:
    """TestTasks class. Tests the output of the import task classes with test configurations
    """


    def test_a_import_sample_manifest(self,create_min_database,
                                      create_pipeline_testing_project,
                                      import_devset_sample_manifest):
        """Tests the sample manifest importer. Checks the counts and whether the models have been made.

        :param create_min_database:
        :param create_pipeline_testing_project:
        :param import_devset_sample_manifest:
        :return:
        """

        import_counts = {
            "project_id": 1,
            "subjects": 6,
            "samples": 78,
            "sample_assays": 0,
            "metadata_values": 312,
            "annotated_features": 0
        }

        assert 'validation_error' not in import_devset_sample_manifest
        assert import_devset_sample_manifest['counts'] == import_counts
        assert 'error' not in import_devset_sample_manifest


    def test_sql_task(self, create_min_database,
                      create_lab,
                      create_pipeline_testing_project,
                      create_ms_assays,
                      create_annotation_methods,
                      import_devset_sample_manifest):

        sql_file = config['DATA']['test_data'] + "test-manual.sql"
        from phenomedb.task import ManualSQL
        task = ManualSQL(db_env='TEST', sql_file=sql_file)
        task.run()

        db_session = db.get_db_session('TEST')
        assert db_session.query(Sample).filter(Sample.name == 'test-update').count() == 1

 #   def test_b_import_data_locations_nmr(self,create_min_database,
 #                                        create_pipeline_testing_project,
 #                                        import_devset_sample_manifest,
 #                                        create_lab,
 #                                        create_nmr_assays,
 #                                        import_devset_datalocations_nmr):

 #       import_counts = {
 #           "project_id": 1,
 #           "subjects": 9,
 #           "samples": 92,
 #           "sample_assays": 84,
 #           "metadata_values": 312,
 #           "annotated_features": 0}

     #   assert import_devset_datalocations_nmr['counts'] == import_counts
 #       assert 'error' not in import_devset_datalocations_nmr
 #       assert 'validation_error' not in import_devset_datalocations_nmr


 #   def test_c_import_data_locations_ms(self,create_min_database,
 #                                        create_pipeline_testing_project,
 #                                        import_devset_sample_manifest,
 #                                        create_lab,
 #                                        create_ms_assays,
 #                                        import_devset_datalocations_ms):#

 #       import_counts = {
 #           "project_id": 1,
 #           "subjects": 9,
 #           "samples": 104,
 #           "sample_assays": 174,
 #           "metadata_values": 312,
 #           "annotated_features": 0}

     #   assert import_devset_datalocations_ms['counts'] == import_counts
 #       assert 'error' not in import_devset_datalocations_ms
 #       assert 'validation_error' not in import_devset_datalocations_ms


    def test_e_import_peakpanther_annotations(self,benchmark,
                                              create_min_database,
                                              add_single_task_pipelines,
                                              create_pipeline_testing_project,
                                              import_devset_sample_manifest,
                                              create_lab,
                                              create_ms_assays,
                                              create_annotation_methods,
                                             import_devset_lpos_peakpanther_annotations):
        import_counts = {
            "project_id": 1,
            "subjects": 8,
            "samples": 115,
            "sample_assays": 64,
            "metadata_values": 312,
            "annotated_features": 10816}

        assert 'validation_error' not in import_devset_lpos_peakpanther_annotations
        assert import_devset_lpos_peakpanther_annotations['counts'] == import_counts

        #expected_dataframe = pd.read_csv(config['DATA']['test_data'] + "expected_lpos.csv")

        #query_factory = AnnotatedFeatureFactory(query_name='test query',query_description='test description',db_env='TEST')
        #query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        #query_factory.add_filter(query_filter=QueryFilter(model='Assay',property='name',operator='eq',value='LPOS'))
        #df = query_factory.execute_and_build_dataframe(csv_path="/tmp/test_lpos.csv",convert_units=False)

        #actual_dataframe = pd.read_csv("/tmp/test_lpos.csv")

        #assert expected_dataframe.equals(actual_dataframe) == True


    def test_f_import_ivdr_biquant_annotations(self,create_min_database,
                                                    add_single_task_pipelines,
                                                      create_pipeline_testing_project,
                                                      import_devset_sample_manifest,
                                                      create_lab,
                                                      create_nmr_assays,
                                                      create_annotation_methods,
                                                      import_devset_ivdr_biquant_annotations):

        import_counts = {
            "project_id": 1,
            "subjects": 8,
            "samples": 120,
            "sample_assays": 98,
            "metadata_values": 312,
            "annotated_features": 12210}

        assert 'validation_error' not in import_devset_ivdr_biquant_annotations
        assert import_devset_ivdr_biquant_annotations['counts'] == import_counts


    #     expected_dataframe = pd.read_csv(config['DATA']['test_data'] + "expected_biquant.csv")
  #
  #     query_factory = AnnotatedFeatureFactory(query_name='test query',query_description='test description',db_env='TEST')
  #     query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
  #     query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='BI-QUANT'))
  #     df = query_factory.execute_and_build_dataframe(csv_path="/tmp/test_biquant.csv",convert_units=False)
  #
  #     actual_dataframe = pd.read_csv("/tmp/test_biquant.csv")
  #
  #     assert expected_dataframe.equals(actual_dataframe) == True



    def test_g_import_ivdr_bilisa_annotations(self,create_min_database,
                                              #add_single_task_pipelines,
                                               create_pipeline_testing_project,
                                               import_devset_sample_manifest,
                                               create_lab,
                                               create_nmr_assays,
                                               create_annotation_methods,
                                               import_devset_ivdr_bilisa_annotations):

        import_counts = {
            "project_id": 1,
            "subjects": 8,
            "samples": 123,
            "sample_assays": 179,
            "metadata_values": 312,
            "annotated_features": 21282}

        assert 'validation_error' not in import_devset_ivdr_bilisa_annotations
        assert import_devset_ivdr_bilisa_annotations['counts'] == import_counts


  #
  #      expected_dataframe = pd.read_csv(config['DATA']['test_data'] + "expected_bilisa.csv")
  #
  #      query_factory = AnnotatedFeatureFactory(query_name='test query',query_description='test description',db_env='TEST')
  #      query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
  #      query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='BI-LISA'))
  #      df = query_factory.execute_and_build_dataframe(csv_path="/tmp/test_bilisa.csv",convert_units=False)
  #
  #      actual_dataframe = pd.read_csv("/tmp/test_bilisa.csv")
  #
  #      assert expected_dataframe.equals(actual_dataframe) == True

    def test_h_targetlynx_import_task_bile_acid_plasma_unified_csv_local(self,create_min_database,
                                                                         create_pipeline_testing_project,
                                                                         import_devset_sample_manifest,
                                                                         create_lab,
                                                                         create_ms_assays,
                                                                         create_annotation_methods,
                                                                         import_devset_bile_acid_targeted_annotations):

        import_counts = {
            "project_id": 1,
            "subjects": 8,
            "samples": 126,
            "sample_assays": 249,
            "metadata_values": 312,
            "annotated_features": 25552}

        assert 'validation_error' not in import_devset_bile_acid_targeted_annotations
        assert import_devset_bile_acid_targeted_annotations['counts'] == import_counts


    def test_import_extra_metadata(self):

        id_column = 'BARCODE'

        columns_to_import = ['BODY_MASS_INDEX', 'HOURS_SINCE_EAT_BLOOD']

        filepath = config['DATA']['app_data'] + "backfill_files/AW2_metabolomics_metadata_Gordon.csv"
        task = ImportExtraMetadata(project_name='AIRWAVE2', filepath=filepath, id_type='Subject',
                                   id_column=id_column, columns_to_import=columns_to_import)
        task.run()

        columns_to_import = ['BMI_cont', 'HOURS_SINCE_EAT_BLOOD']

        filepath = config['DATA']['app_data'] + "backfill_files/AW1_metabolomics_metadata_Gordon.csv"
        task = ImportExtraMetadata(project_name='AIRWAVE',filepath=filepath,id_type='Subject',
                                   id_column=id_column,columns_to_import=columns_to_import)
        task.run()




 #     expected_dataframe = pd.read_csv(config['DATA']['test_data'] + "expected_targetlynx.csv")
 #
 #     query_factory = AnnotatedFeatureFactory(query_name='test query',query_description='test description',db_env='TEST')
 #     query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
 #     query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='TargetLynx'))
 #     df = query_factory.execute_and_build_dataframe(csv_path="/tmp/test_targetlynx.csv",convert_units=False)
 #
 #     actual_dataframe = pd.read_csv("/tmp/test_targetlynx.csv")
 #
 #     assert expected_dataframe.equals(actual_dataframe) == True
 #
    def test_import_metabolights(self,create_min_database):
         #TODO: add this to conftest.py including the exported values

        from phenomedb.imports import ImportMetabolightsStudy

        study_id = "MTBLS1073"

        study_folder_path = config["DATA"]['test_data'] + study_id

        task = ImportMetabolightsStudy(study_folder_path=study_folder_path,username=config['TEST']['USERNAME'],db_env='TEST')

        task.run()