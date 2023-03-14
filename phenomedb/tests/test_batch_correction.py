import pytest
import random

import pandas as pd

import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *
from phenomedb.query_factory import *
from phenomedb.batch_correction import *
from phenomedb.config import config
test_db_session = get_db_session(db_env='TEST')
prod_db_session = get_db_session()

class TestBatchCorrection:
    """TestAnalysisTasks class. Tests the AnalysisTasks
    """

    def test_a_run_sr_batch_correction_airwave_hpos(self):

        task = RunNPYCBatchCorrection(saved_query_id=2,correction_type='SR')
        output = task.run()
        #output = task.run()
        #print(output)
        assert True

    def test_commit_batch_correction(self):
        task = RunNPYCBatchCorrection(saved_query_id=2, correction_type='SR')
        task.run()
        task = SaveBatchCorrection(correction_data_task_run_id = task.task_run.id)
        output = task.run()
        task = RunNPYCBatchCorrection(saved_query_id=2, correction_type='LTR')
        task.run()
        task = SaveBatchCorrection(correction_data_task_run_id=task.task_run.id)
        output = task.run()
        # output = task.run()
        # print(output)
        assert 'harmonised_dataset_id' in output.keys()


    def test_a_run_sr_batch_correction(self,create_min_database,
                                       create_pipeline_testing_project,
                                       import_devset_sample_manifest,
                                       create_lab,
                                       create_ms_assays,
                                       create_annotation_methods,
                                       import_devset_lpos_peakpanther_annotations
                                       ):
        task = RunNPYCBatchCorrection(saved_query_id=import_devset_lpos_peakpanther_annotations['saved_query_id'],
                                      correction_type='LTR', db_env='TEST', save_correction=True)
        task.run()
        #saved_query = test_db_session.query(SavedQuery).filter(SavedQuery.name=='test_query_lpos').first()
        task = RunNPYCBatchCorrection(saved_query_id=import_devset_lpos_peakpanther_annotations['saved_query_id'],correction_type='SR',db_env='TEST')
        output = task.run()
        task = SaveBatchCorrection(correction_data_task_run_id=task.task_run.id,db_env='TEST')
        output = task.run()

     #   task = SaveBatchCorrection(correction_data_task_run_id=task.task_run.id,db_env='TEST')
     #   output = task.run()



        #assert output is not None

#   def test_a_run_ltr_batch_correction(self,create_min_database,
#                                      create_pipeline_testing_project,
#                                      import_devset_sample_manifest,
#                                      create_lab,
#                                      create_ms_assays,
#                                      create_annotation_methods,
#                                      import_devset_lpos_peakpanther_annotations,
#                                       create_saved_queries):
#
#
#       saved_query = db_session.query(SavedQuery).filter(SavedQuery.name=='test_query_lpos').first()
#       task = RunNPYCBatchCorrection(saved_query_id=saved_query.id,correction_type='LTR')
#       #output = task.run(db_env='TEST')
#
    def test_a_run_mm_residuals_normalisation(self):

        # Run a PCA with UV scaling
       # task = RunPCA(saved_query_id=58,correction_type="SR",transform='log')
       # output = task.run()
       # print('Pre-MM_residuals correction (log): http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunNormResidualsMM(saved_query_id=58,correction_type='SR',columns_fixed_to_keep=['h_metadata::Age','h_metadata::Sex'],
                                    columns_random_to_correct=['Project','Unique Batch'],transform='log')
        output = task.run()
        #task = RunPCA(saved_query_id=58, upstream_task_run_id=task.task_run.id,correction_type='SR')
        #output = task.run()
        #print('Post MM_residuals correction (log): http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

    def test_a_run_combat_batch_correction(self):
        # Run a PCA with UV scaling
        task = RunPCA(saved_query_id=58, correction_type="SR")
        output = task.run()
        print('Pre-COMBAT UV scaling: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunCombatCorrection(saved_query_id=58, correction_type='SR', model_Y_variable='h_metadata::Age',
                                   model_X_variables=['h_metadata::Sex'],transform='log')
        output = task.run()
        task = RunPCA(saved_query_id=58, upstream_task_run_id=task.task_run.id, correction_type='SR')
        output = task.run()
        print(
            'Post COMBAT Project correction with UV transform: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        #task = RunCombatCorrection(saved_query_id=58,batch_variable='Unique Batch',scaling='uv',correction_type='SR')
        #output = task.run()
        #task = RunPCA(saved_query_id=58, upstream_task_run_id=task.task_run.id,correction_type='SR')
        #output = task.run()
        #print('COMBAT Unique Batch transform: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)


    def test_combat_then_pca_small_ltr(self):
        #task = RunPCA(saved_query_id=32)
        #output = task.run()
        #print(task.task_run.id)

        task = RunCombatCorrection(saved_query_id=32,columns_to_include=['Project'],include_harmonised_metadata=True)
        output = task.run()

        print(task.task_run.id)

        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()

        print(task.task_run.id)

    def test_db_norm(self):
        task = RunDBnormCorrection(saved_query_id=58, correction_type='SR')
        task.run()

    def test_combat_then_pca_airwave_airwave2(self):
        task = RunPCA(saved_query_id=59,transform='log')
        print("AIRWAVE AIRWAVE2 plasma LNEG only SR - http://localhost:8080/queryfactoryview/edit/?id=59")
        output = task.run()
        print('Raw pre-correction - only SR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=59)
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('Raw post-correction - only SR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=59, correction_type='SR')
        print("AIRWAVE AIRWAVE2 plasma LNEG only SR - http://localhost:8080/queryfactoryview/edit/?id=59")
        output = task.run()
        print('SR pre-correction - only SR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=59, correction_type='SR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('SR post-correction - only SR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=59, correction_type='LTR')
        print("AIRWAVE AIRWAVE2 plasma LNEG only SR - http://localhost:8080/queryfactoryview/edit/?id=59")
        output = task.run()
        print('LTR pre-correction - only SR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=59, correction_type='LTR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('LTR post-correction - only SR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=60)
        print("AIRWAVE AIRWAVE2 plasma LNEG only LTR - http://localhost:8080/queryfactoryview/edit/?id=60")
        output = task.run()
        print('Raw pre-correction - only LTR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=60)
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('Raw post-correction - only LTR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=60, correction_type='SR')
        print("AIRWAVE AIRWAVE2 plasma LNEG only LTR - http://localhost:8080/queryfactoryview/edit/?id=60")
        output = task.run()
        print('SR pre-correction - only LTR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=60, correction_type='SR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('SR post-correction - only LTR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=60, correction_type='LTR')
        print("AIRWAVE AIRWAVE2 plasma LNEG only LTR - http://localhost:8080/queryfactoryview/edit/?id=60")
        output = task.run()
        print('LTR pre-correction - only LTR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=60, correction_type='LTR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('LTR post-correction - only LTR: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        print("AIRWAVE AIRWAVE2 plasma LNEG all samples - http://localhost:8080/queryfactoryview/edit/?id=57")
        task = RunPCA(saved_query_id=57)
        output = task.run()
        print('Raw pre-correction - all sample types: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=57)
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('Raw post-correction - all sample types: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=57,correction_type='SR')
        print("AIRWAVE AIRWAVE2 plasma LNEG all samples - http://localhost:8080/queryfactoryview/edit/?id=57")
        output = task.run()
        print('SR pre-correction - all sample types: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=57,correction_type='SR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('SR post-correction - all sample types: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=57, correction_type='LTR')
        print("AIRWAVE AIRWAVE2 plasma LNEG all samples - http://localhost:8080/queryfactoryview/edit/?id=57")
        output = task.run()
        print('LTR pre-correction - all sample types: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=57, correction_type='LTR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('LTR post-correction - all sample types: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=58)
        print("AIRWAVE AIRWAVE2 plasma LNEG only SS- http://localhost:8080/queryfactoryview/edit/?id=58")
        output = task.run()
        print('Raw pre-correction - only SS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=58)
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('Raw post-correction - only SS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=58,correction_type='SR')
        print("AIRWAVE AIRWAVE2 plasma LNEG only SS - http://localhost:8080/queryfactoryview/edit/?id=58")
        output = task.run()
        print('SR pre-correction - only SS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=58,correction_type='SR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('SR post-correction - only SS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=58, correction_type='LTR')
        print("AIRWAVE AIRWAVE2 plasma LNEG only SS - http://localhost:8080/queryfactoryview/edit/?id=58")
        output = task.run()
        print('LTR pre-correction - only SS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunCombatCorrection(saved_query_id=58, correction_type='LTR')
        output = task.run()
        task = RunPCA(upstream_task_run_id=task.task_run.id)
        output = task.run()
        print('LTR post-correction - only SS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

    def test_compare_batch_correction_methods(self):

        pcpr2_columns_to_include = ['Project','h_metadata::Age','h_metadata::Sex']
        columns_fixed_to_keep = ['h_metadata::Age', 'h_metadata::Sex']

        #task = RunNPYCReport(report_name='feature summary', saved_query_id=31,correction_type='SR',transform='log',reload_cache=True)
        #output = task.run()
        #print('Pre-correction (SR-log) Feature summary: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        # Run a PCA with log scaling
        task = RunPCA(saved_query_id=75,correction_type="SR",transform='log')
        output = task.run()
        print('Pre-correction (SR-log) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCPR2(saved_query_id=75, correction_type="SR", transform='log',columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print('Pre-correction (SR-log) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunMWAS(saved_query_id=75, correction_type='SR', transform='log', model_Y_variable="h_metadata::Age", model_X_variables=['h_metadata::Sex'])
        output = task.run()
        print('Pre-correction (SR-log) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=75, correction_type="SR", scaling='uv', transform='log')
        output = task.run()
        print('UV-scaling (SR-log-uv) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCPR2(saved_query_id=75, correction_type="SR", scaling='uv', transform='log',
                        columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print('UV-scaling (SR-log-uv) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunMWAS(saved_query_id=75, correction_type='SR', scaling='uv', transform='log', model_Y_variable="h_metadata::Age",
                       model_X_variables=['h_metadata::Sex'])
        output = task.run()
        print('UV-scaling (SR-log-uv) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCA(saved_query_id=75, correction_type="SR", scaling='med', transform='log')
        output = task.run()
        print('Median-fold-change-scaling (SR-log-med) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunPCPR2(saved_query_id=75, correction_type="SR", scaling='med', transform='log',
                        columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print('Median-fold-change-scaling (SR-log-med) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunMWAS(saved_query_id=75, correction_type='SR', scaling='med', transform='log',
                       model_Y_variable="h_metadata::Age",
                       model_X_variables=['h_metadata::Sex'])
        output = task.run()
        print('Median-fold-change-scaling (SR-log-med) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        combat_task = RunCombatCorrection(saved_query_id=75, correction_type='SR',scaling='uv',model_Y_variable='h_metadata::Age',
                                   batch_variable='Unique Batch',model_X_variables=columns_fixed_to_keep,transform='log')
        output = combat_task.run()
        task = RunPCA(saved_query_id=75, upstream_task_run_id=combat_task.task_run.id)
        output = task.run()
        print('Post-ComBat-correction (SR-log-uv) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunPCPR2(saved_query_id=75,upstream_task_run_id=combat_task.task_run.id,columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print('Post-ComBat-correction (SR-log-uv) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunMWAS(saved_query_id=75, model_Y_variable="h_metadata::Age", model_X_variables=['h_metadata::Sex'],upstream_task_run_id=combat_task.task_run.id)
        output = task.run()
        print('Post-ComBat-correction (SR-log-uv) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        combat_task = RunCombatCorrection(saved_query_id=75, correction_type='SR', scaling='med',
                                          model_Y_variable='h_metadata::Age',
                                          batch_variable='Unique Batch', model_X_variables=columns_fixed_to_keep,
                                          transform='log')
        output = combat_task.run()
        task = RunPCA(saved_query_id=75, upstream_task_run_id=combat_task.task_run.id)
        output = task.run()
        print(
            'Post-ComBat-correction (SR-log-med) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunPCPR2(saved_query_id=75, upstream_task_run_id=combat_task.task_run.id,
                        columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print(
            'Post-ComBat-correction (SR-log-med) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunMWAS(saved_query_id=75, model_Y_variable="h_metadata::Age", model_X_variables=['h_metadata::Sex'],
                       upstream_task_run_id=combat_task.task_run.id)
        output = task.run()
        print(
            'Post-ComBat-correction (SR-log-med) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)


        mm_residual_task = RunNormResidualsMM(saved_query_id=75,correction_type='SR',columns_fixed_to_keep=['h_metadata::Age','h_metadata::Sex'],
                                    columns_random_to_correct=['Project','Unique Batch'],transform='log')
        output = mm_residual_task.run()
        task = RunPCA(saved_query_id=75, upstream_task_run_id=mm_residual_task.task_run.id)
        output = task.run()
        print('Post-MM-residuals-correction (SR-log) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunPCPR2(saved_query_id=75, upstream_task_run_id=mm_residual_task.task_run.id,
                        columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print('Post-MM-residuals-correction (SR-log) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunMWAS(saved_query_id=75, model_Y_variable="h_metadata::Age", model_X_variables=['h_metadata::Sex'],
                       upstream_task_run_id=mm_residual_task.task_run.id)
        output = task.run()
        print('Post-MM-residuals-correction (SR-log) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        mm_residual_task = RunNormResidualsMM(saved_query_id=75, correction_type='SR',
                                              columns_fixed_to_keep=['h_metadata::Age', 'h_metadata::Sex'],
                                              columns_random_to_correct=['Project', 'Unique Batch'], transform='log')
        output = mm_residual_task.run()
        task = RunPCA(saved_query_id=75, upstream_task_run_id=mm_residual_task.task_run.id)
        output = task.run()
        print(
            'Post-MM-residuals-correction (SR-log) PCA: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)
        task = RunPCPR2(saved_query_id=75, upstream_task_run_id=mm_residual_task.task_run.id,
                        columns_to_include=pcpr2_columns_to_include)
        output = task.run()
        print(
            'Post-MM-residuals-correction (SR-log) PCPR2: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

        task = RunMWAS(saved_query_id=75, model_Y_variable="h_metadata::Age", model_X_variables=['h_metadata::Sex'],
                       upstream_task_run_id=mm_residual_task.task_run.id)
        output = task.run()
        print(
            'Post-MM-residuals-correction (SR-log) MWAS: http://localhost:8080/analysisview/analysisresult/%s' % task.task_run.id)

    def test_run_batch_correction_assessment_pipeline(self):

        from pipelines import RunBatchCorrectionAssessmentPipeline
        saved_query_id = 144
        correction_type = 'SR'
        variable_of_interest = 'h_metadata::Age'
        run_combat_and_norm_mixedresiduals = True
        wait_for_completion = True
        task = RunBatchCorrectionAssessmentPipeline(saved_query_id=144,correction_type='SR',wait_for_completion=wait_for_completion,
                                                    variable_of_interest=variable_of_interest,
                                                    run_combat_and_norm_mixedresiduals=run_combat_and_norm_mixedresiduals)
        task.run()
        pass



