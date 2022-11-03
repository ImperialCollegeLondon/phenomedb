import pandas as pd

from phenomedb.task import Task
from phenomedb.models import *
import datetime
from phenomedb.query_factory import *
from phenomedb.analysis import *
import nPYc
import math
import shutil
import re

class RunNPYCBatchCorrection(NPYCTask):
    """RunNPYCBatchCorrection. Run a batch correction using the nPYc-toolbox methods.

    :param AnalysisResult: The CorrectionTask base class.
    :type AnalysisResult: `phenomedb.correction.CorrectionTask`
    """

    sample_types = None

    def __init__(self,username=None,task_run_id=None,query_factory=None,saved_query_id=None,save_correction=False,comment=None,
                 samples_to_exclude=[],exclude_on='Run Order',exclusion_comments={},pipeline_run_id=None,
                    correction_type="LTR",window=11,method="LOWESS",align='median',exclude_failures=True,reload_cache=False,amend_batches=None,db_env=None,db_session=None,execution_date=None):
        """The init method for the RunPCA.

        :param username: Username of user running analysis, defaults to None
        :type username: str, optional
        :param query_factory: The AnnotatedFeatureFactory object to load results from, defaults to None
        :type query_factory: `phenomedb.query_factory.AnnotatedFeatureFactory`, optional
        :param saved_query_id: The ID of the SavedQuery to load results from, defaults to None
        :type saved_query_id: int, optional
        :param type: Which SampleType to use for correction, LTR or SR, defaults to 'LTR'
        :type type: str, optional
        """

        output_dir = '/tmp/phenomedb/npyc-datasets/sq' + str(saved_query_id)
        columns_to_include = ['Sample File Name','Acquired Time','Batch','Run Order','SampleType','AssayRole','Sample ID']

        super().__init__(query_factory=query_factory,saved_query_id=saved_query_id,username=username,task_run_id=task_run_id,pipeline_run_id=pipeline_run_id,
                         reload_cache=reload_cache,output_dir=output_dir,columns_to_include=columns_to_include,db_env=db_env,db_session=db_session,execution_date=execution_date)

        if correction_type in [FeatureDataset.CorrectionType.LOESS_LTR,FeatureDataset.CorrectionType.LOESS_LTR.value]:
            self.batch_correction_type = FeatureDataset.CorrectionType.LOESS_LTR
            self.correction_sample_type = SampleType.ExternalReference
        elif correction_type in [FeatureDataset.CorrectionType.LOESS_SR,FeatureDataset.CorrectionType.LOESS_SR.value]:
            self.batch_correction_type = FeatureDataset.CorrectionType.LOESS_SR
            self.correction_sample_type = SampleType.StudyPool
        else:
            raise Exception("correction_type must be LTR or SR")

        self.method = method
        self.window = window
        self.align = align
        self.exclude_failures = exclude_failures
        self.samples_to_exclude = samples_to_exclude
        self.exclude_on = exclude_on
        self.amend_batches = amend_batches
        self.exclusion_comments = exclusion_comments
        self.comment = comment
        self.save_correction = save_correction
        self.sample_metadata_path = None

        self.args['saved_query_id'] = self.saved_query_id
        self.args['correction_type'] = self.batch_correction_type.value
        self.args['correction_sample_type'] = self.correction_sample_type.value
        self.args['method'] = self.method
        self.args['window'] = self.window
        self.args['align'] = self.align
        self.args['amend_batches'] = self.amend_batches
        self.args['samples_to_exclude'] = self.samples_to_exclude
        self.args['exclusion_comments'] = self.exclusion_comments
        self.args['exclude_on'] = self.exclude_on
        self.args['exclude_failures'] = self.exclude_failures
        self.args['comment'] = self.comment
        self.args['save_correction'] = self.save_correction

        self.get_class_name(self)

        self.logger.info('ARGS: %s' % self.args)

    def load_data(self):

        super().load_data()

        self.feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.saved_query_id==self.saved_query.id).first()
        if not self.feature_dataset:
            raise Exception("FeatureDataset with saved_query_id %s does not exist!" % self.saved_query.id)

        self.set_correction_batches()

        #self.npyc_dataset = self.load_npyc_dataset()

    def set_correction_batches(self):

        current_project = self.dataframe.loc[0,'Project']
        current_batch = utils.read_numeric_batch(self.dataframe.loc[0,'Batch'])
        current_correction_batch = utils.read_numeric_batch(self.dataframe.loc[0,'Correction Batch'])

        if not current_correction_batch or pd.isnull(current_correction_batch):
            current_correction_batch = 1.0

        sample_metadata_key = self.query_factory.get_dataframe_key(type='sample_metadata',model='AnnotatedFeature',db_env=self.db_env,correction_type=None)

        sample_metadata_with_correction_batch = self.query_factory.dataframes[sample_metadata_key].copy()

        for index, row in self.query_factory.dataframes[sample_metadata_key].iterrows():

            this_numeric_batch = utils.read_numeric_batch(row['Correction Batch'])

            if current_project != row['Project']:
                current_correction_batch = current_correction_batch + 1
                row['Correction Batch'] = current_correction_batch
            elif current_batch != utils.read_numeric_batch(row['Batch']):
                current_correction_batch = current_correction_batch + 1
                row['Correction Batch'] = current_correction_batch
            elif this_numeric_batch == 0:
                row['Correction Batch'] = current_correction_batch
            elif not current_correction_batch or pd.isnull(current_correction_batch):
                pass
            else:
                row['Correction Batch'] = current_correction_batch

            current_correction_batch = utils.read_numeric_batch(row['Correction Batch'])
            current_project = row["Project"]
            current_batch = utils.read_numeric_batch(row['Batch'])
            self.logger.debug("Correction Batch updated from %s to %s" % (self.query_factory.dataframes[sample_metadata_key].loc[index,'Correction Batch'],row['Correction Batch']))
            self.query_factory.dataframes[sample_metadata_key].loc[index,'Correction Batch'] = row['Correction Batch']

        self.query_factory.dataframes[sample_metadata_key].to_csv(self.query_factory.dataframe_csv_paths[sample_metadata_key])
        self.logger.info("Sample Metadata file updated with correction batches %s" % self.query_factory.dataframe_csv_paths[sample_metadata_key])

    def run_analysis(self):
        """Run the correction using the specified options.
        """

        if self.amend_batches and utils.is_number(self.amend_batches):
            self.npyc_dataset.amendBatches(self.amend_batches)

        if self.samples_to_exclude and self.exclude_on:
            if isinstance(self.exclusion_comments,list) and len(self.samples_to_exclude) == len(self.exclusion_comments):
                for i in len(self.samples_to_exclude):
                    self.npyc_dataset.excludeSamples(self.samples_to_exclude[i],on=self.exclude_on,message=self.exclusion_comments[i])
            elif isinstance(self.exclusion_comments,list):
                self.npyc_dataset.excludeSamples(self.samples_to_exclude,on=self.exclude_on,message=self.exclusion_comments[0])
            else:
                self.npyc_dataset.excludeSamples(self.samples_to_exclude,on=self.exclude_on,message=self.exclusion_comments)

        self.corrected_npyc_dataset = nPYc.batchAndROCorrection.correctMSdataset(self.npyc_dataset, window=self.window,
                                                                                 method=self.method, align=self.align,
                                                                                 parallelise=False, excludeFailures=True,
                                                                                 correctionSampleType=self.correction_sample_type)

        self.corrected_dataset = self.corrected_npyc_dataset.intensityData

        self.logger.info("Dataset corrected!")

    def save_results(self):
        """Save the results into HarmonisedAnnotatedFeature database table
        """

        self.logger.info("Running reports and saving results.....")
        self.combined_key = self.query_factory.get_dataframe_key(type='combined',
                                                                        model=self.saved_query_model,
                                                                        correction_type=self.correction_type,
                                                                        db_env=self.db_env)
        self.combined_key = self.query_factory.get_dataframe_key(type='combined',
                                                                 model=self.saved_query_model,
                                                                 correction_type=self.correction_type,
                                                                 db_env=self.db_env)
        self.feature_id_matrix_key = self.query_factory.get_dataframe_key(type='feature_id_matrix',
                                                                 model=self.saved_query_model,
                                                                 correction_type=self.correction_type,
                                                                 db_env=self.db_env)

        self.results = {'original_annotated_feature_id_matrix':self.query_factory.dataframes[self.feature_id_matrix_key],
                            'original_sample_metadata':self.query_factory.dataframes[self.sample_metadata_key],
                            'original_feature_metadata':self.query_factory.dataframes[self.feature_metadata_key],
                            'original_intensity_data':self.query_factory.dataframes[self.intensity_data_key],
                            'corrected_sample_metadata':self.corrected_npyc_dataset.sampleMetadata,
                            'corrected_feature_metadata':self.corrected_npyc_dataset.featureMetadata,
                            'corrected_intensity_data':self.corrected_npyc_dataset.intensityData,
                            'feature_dataset_id':self.feature_dataset.id,
                            }

        super().save_results()

        report_folder = config['DATA']['app_data'] + ("/task_runs/task_run_%s/reports/batch correction summary/" % self.task_run.id)
        self.task_run.reports = {}
        self.task_run.reports['batch correction summary'] = report_folder
        self.db_session.flush()

        if not os.path.exists(report_folder):
            os.makedirs(report_folder)

        nPYc.reports.generateReport(self.npyc_dataset, 'batch correction summary', msDataCorrected=self.corrected_npyc_dataset, destinationPath=report_folder)

        report_folder = config['DATA']['app_data'] + ("/task_runs/task_run_%s/reports/batch correction assessment/" % self.task_run.id)
        self.task_run.reports['batch correction assessment'] = report_folder
        self.task_run.npyc_report_folder = report_folder
        self.db_session.flush()

        if not os.path.exists(report_folder):
            os.makedirs(report_folder)

        nPYc.reports.generateReport(self.npyc_dataset, 'batch correction assessment',destinationPath=report_folder)

        if self.save_correction:

            if self.batch_correction_type in [FeatureDataset.CorrectionType.LOESS_SR,
                                                                    FeatureDataset.CorrectionType.LOESS_SR.value]:
                self.feature_dataset.sr_correction_params = self.args
                self.feature_dataset.sr_correction_task_run_id = self.task_run.id
            elif self.batch_correction_type in [FeatureDataset.CorrectionType.LOESS_LTR,
                                                                      FeatureDataset.CorrectionType.LOESS_LTR.value]:
                self.feature_dataset.ltr_correction_params = self.args
                self.feature_dataset.ltr_correction_task_run_id = self.task_run.id

            annotated_feature_list = self.db_session.query(AnnotatedFeature).filter(
                AnnotatedFeature.id.in_(self.query_factory.dataframes[self.feature_id_matrix_key].flatten().tolist())).all()

            annotated_feature_dict = {}
            for annotated_feature in annotated_feature_list:
                annotated_feature_dict[annotated_feature.id] = annotated_feature

            for row_index, sample_row in self.corrected_npyc_dataset.sampleMetadata.iterrows():

                for col_index, feature_column in self.corrected_npyc_dataset.featureMetadata.iterrows():
                    row_int = int(row_index)
                    col_int = int(col_index)

                    # Need to check exactly what happens with the exclusions - its possible the shape of the dataframes will be different!

                    #if math.isinf(self.corrected_npyc_dataset.intensityData[row_int, col_int]):
                    #ß    bp = True
                    if self.batch_correction_type in [FeatureDataset.CorrectionType.LOESS_SR,
                                                                            FeatureDataset.CorrectionType.LOESS_SR.value]\
                            and not math.isinf(self.corrected_npyc_dataset.intensityData[row_int, col_int]):
                        annotated_feature_dict[self.query_factory.dataframes[self.feature_id_matrix_key][
                            row_int, col_int]].sr_corrected_intensity = \
                            self.corrected_npyc_dataset.intensityData[row_int, col_int]
                    elif self.batch_correction_type in [FeatureDataset.CorrectionType.LOESS_LTR,
                                                                              FeatureDataset.CorrectionType.LOESS_LTR.value] \
                            and not math.isinf(self.corrected_npyc_dataset.intensityData[row_int, col_int]):
                        annotated_feature_dict[self.query_factory.dataframes[self.feature_id_matrix_key][
                            row_int, col_int]].ltr_corrected_intensity = \
                            self.corrected_npyc_dataset.intensityData[row_int, col_int]

                    # self.logger.debug("Added/updated %s" % corrected_annotated_feature)

            # self.db_session.add_all(corrected_annotated_features)
            self.db_session.flush()

        self.output = {'task_run_id':self.task_run.id}

        self.logger.info("Save complete...!")

class SaveBatchCorrection(Task):

    def __init__(self,correction_data_task_run_id=None,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None):

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)

        self.correction_data_task_run_id = correction_data_task_run_id
        self.args['correction_data_task_run_id'] = correction_data_task_run_id

    def process(self):

        if not self.correction_data_task_run_id:
            raise Exception("No task run id set")

        correction_data_task_run = self.db_session.query(TaskRun).filter(TaskRun.id==self.correction_data_task_run_id).first()

        if not correction_data_task_run:
            raise Exception("No TaskRun with id %" % self.correction_data_task_run_id)
        else:
            self.logger.info('TaskRun found: %s' % correction_data_task_run)

        if 'saved_query_id' not in correction_data_task_run.args:
            raise Exception("TaskRun has no SavedQuery id %" % self.correction_data_task_run_id)
        if 'correction_type' not in correction_data_task_run.args:
            raise Exception("TaskRun has no Type %" % self.correction_data_task_run_id)

        if 'comment' in correction_data_task_run.args.keys():
            comment = correction_data_task_run.args['comment']
        else:
            comment = None
        correction_data_task_run_output = correction_data_task_run.get_task_output(self.cache)
        if 'corrected_sample_metadata' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no corrected_sample_metadata")
        if 'corrected_feature_metadata' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no corrected_feature_metadata")
        if 'corrected_intensity_data' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no corrected_intensity_data")
        if 'original_annotated_feature_id_matrix' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no original_annotated_feature_id_matrix")
        if 'original_sample_metadata' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no original_sample_metadata")
        if 'original_feature_metadata' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no original_feature_metadata")
        if 'original_intensity_data' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no original_intensity_data")
        if 'feature_dataset_id' not in correction_data_task_run_output:
            raise Exception("TaskRun.results has no feature_dataset_id")

        feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.id==correction_data_task_run_output['feature_dataset_id']).first()
        if correction_data_task_run.args['correction_type'] in [FeatureDataset.CorrectionType.LOESS_SR,FeatureDataset.CorrectionType.LOESS_SR.value]:
            feature_dataset.sr_correction_params = correction_data_task_run.args
            feature_dataset.sr_correction_task_run_id = self.correction_data_task_run_id
        elif correction_data_task_run.args['correction_type'] in [FeatureDataset.CorrectionType.LOESS_LTR,FeatureDataset.CorrectionType.LOESS_LTR.value]:
            feature_dataset.ltr_correction_params = correction_data_task_run.args
            feature_dataset.ltr_correction_task_run_id = self.correction_data_task_run_id

        corrected_sample_metadata = pd.DataFrame.from_dict(correction_data_task_run_output['corrected_sample_metadata'])
        corrected_feature_metadata = pd.DataFrame.from_dict(correction_data_task_run_output['corrected_feature_metadata'])
        corrected_intensity_data = np.matrix(correction_data_task_run_output['corrected_intensity_data'])
        original_annotated_feature_id_matrix = np.matrix(correction_data_task_run_output['original_annotated_feature_id_matrix'])
        original_sample_metadata = pd.DataFrame.from_dict(correction_data_task_run_output['original_sample_metadata'])
        original_feature_metadata = pd.DataFrame.from_dict(correction_data_task_run_output['original_feature_metadata'])
        original_intensity_data = np.matrix(correction_data_task_run_output['original_intensity_data'])

        if np.shape(corrected_intensity_data) != np.shape(original_intensity_data):
            raise Exception("Sample and Feature Exclusions are not yet implemented!")

        annotated_feature_list = self.db_session.query(AnnotatedFeature).filter(AnnotatedFeature.id.in_(original_annotated_feature_id_matrix.flatten().tolist()[0])).all()

        annotated_feature_dict = {}
        for annotated_feature in annotated_feature_list:
            annotated_feature_dict[annotated_feature.id] = annotated_feature

        for row_index, sample_row in corrected_sample_metadata.iterrows():

            for col_index, feature_column in original_feature_metadata.iterrows():

                row_int = int(row_index)
                col_int = int(col_index)

                # Need to check exactly what happens with the exclusions - its possible the shape of the dataframes will be different!

                if correction_data_task_run.args['correction_type'] in [FeatureDataset.CorrectionType.LOESS_SR,
                                         FeatureDataset.CorrectionType.LOESS_SR.value]\
                        and not math.isinf(corrected_intensity_data[row_int,col_int]):
                    annotated_feature_dict[original_annotated_feature_id_matrix[row_int,col_int]].sr_corrected_intensity = corrected_intensity_data[row_int,col_int]
                elif correction_data_task_run.args['correction_type'] in [FeatureDataset.CorrectionType.LOESS_LTR,
                                       FeatureDataset.CorrectionType.LOESS_LTR.value]\
                        and not math.isinf(corrected_intensity_data[row_int,col_int]):
                    annotated_feature_dict[original_annotated_feature_id_matrix[row_int,col_int]].ltr_corrected_intensity = corrected_intensity_data[row_int,col_int]

                #self.logger.debug("Added/updated %s" % corrected_annotated_feature)

        #self.db_session.add_all(corrected_annotated_features)
        self.db_session.flush()
        self.logger.info("Corrected features added/flushed")

        self.output = None
        #self.saved_output = {'harmonised_dataset_id':self.harmonised_dataset.id}

        self.logger.info("Save complete...!")


class RunNPYCBatchCorrectionReportsForExistingCorrectedFeatureDataset(NPYCTask):
    """RunNPYCBatchCorrectionReportsForExistingCorrectedFeatureDataset.
        Sometimes it is necessary to update an existing sr_corrected_task_run with the reports.
        This is because we actually import the SR batch corrected dataset during the import, but its still useful to view the reports (which haven't been generated).

    :param AnalysisResult: The CorrectionTask base class.
    :type AnalysisResult: `phenomedb.correction.CorrectionTask`
    """

    def __init__(self,username=None,task_run_id=None,saved_query_id=None,correction_type="SR",reload_cache=False,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None):
        """The init method for the RunPCA.

        :param username: Username of user running analysis, defaults to None
        :type username: str, optional
        :param query_factory: The AnnotatedFeatureFactory object to load results from, defaults to None
        :type query_factory: `phenomedb.query_factory.AnnotatedFeatureFactory`, optional
        :param saved_query_id: The ID of the SavedQuery to load results from, defaults to None
        :type saved_query_id: int, optional
        :param type: Which SampleType to use for correction, LTR or SR, defaults to 'LTR'
        :type type: str, optional
        """


        output_dir = '/tmp/phenomedb/npyc-datasets/sq' + str(saved_query_id)
        columns_to_include = ['Sample File Name','Acquired Time','Batch','Run Order','SampleType','AssayRole','Sample ID']

        super().__init__(username=username,task_run_id=task_run_id,saved_query_id=saved_query_id,reload_cache=reload_cache,output_dir=output_dir,
                         columns_to_include=columns_to_include,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)

        if correction_type in [FeatureDataset.CorrectionType.LOESS_LTR,FeatureDataset.CorrectionType.LOESS_LTR.value]:
            self.batch_correction_type = FeatureDataset.CorrectionType.LOESS_LTR
            self.correction_sample_type = SampleType.ExternalReference
        elif correction_type in [FeatureDataset.CorrectionType.LOESS_SR,FeatureDataset.CorrectionType.LOESS_SR.value]:
            self.batch_correction_type = FeatureDataset.CorrectionType.LOESS_SR
            self.correction_sample_type = SampleType.StudyPool
        else:
            raise Exception("correction_type must be LTR or SR")

        self.correction_type = self.batch_correction_type

        self.args['saved_query_id'] = self.saved_query_id
        self.args['correction_type'] = self.batch_correction_type.value

        self.get_class_name(self)

        self.logger.info('ARGS: %s' % self.args)

    def load_data(self):

        self.feature_dataset = self.db_session.query(FeatureDataset).filter(
            FeatureDataset.saved_query_id == self.saved_query_id).first()
        if not self.feature_dataset:
            raise Exception("FeatureDataset with saved_query_id %s does not exist!" % self.saved_query_id)

        if self.correction_type == FeatureDataset.CorrectionType.LOESS_SR and not self.feature_dataset.sr_correction_task_run:
            raise Exception("The FeatureDataset must have an sr_correction_task_run_id")

        if self.correction_type == FeatureDataset.CorrectionType.LOESS_LTR and not self.feature_dataset.ltr_correction_task_run:
            raise Exception("The FeatureDataset must have a ltr_correction_task_run_id")

        #1. Load the batch_corrected_data
        super().load_data()

        self.corrected_dataset = nPYc.MSDataset(self.query_factory.dataframe_csv_paths[self.sample_metadata_key],
                                           fileType='csv export')

        # 2. Load the non-batch corrected data
        self.correction_type = None
        super().load_data()

        self.uncorrected_dataset = nPYc.MSDataset(self.query_factory.dataframe_csv_paths[self.sample_metadata_key],
                                                fileType='csv export')

        if self.batch_correction_type == FeatureDataset.CorrectionType.LOESS_SR:
            self.correction_task_run = self.feature_dataset.sr_correction_task_run
        else:
            self.correction_task_run = self.feature_dataset.ltr_correction_task_run

    def save_results(self):
        """Save the results into HarmonisedAnnotatedFeature database table
        """

        super().save_results()

        report_folder = config['DATA']['app_data'] + ("/task_runs/task_run_%s/reports/batch correction summary/" % self.correction_task_run.id)
        if self.correction_task_run.reports:
            reports = dict(self.correction_task_run.reports)
        else:
            reports = {}
        reports['batch correction summary'] = report_folder

        if not os.path.exists(report_folder):
            os.makedirs(report_folder)

        nPYc.reports.generateReport(self.uncorrected_dataset, 'batch correction summary', msDataCorrected=self.corrected_dataset, destinationPath=report_folder)

        report_folder = config['DATA']['app_data'] + ("/task_runs/task_run_%s/reports/batch correction assessment/" % self.correction_task_run.id)
        reports['batch correction assessment'] = report_folder
        npyc_report_folder = report_folder

        if not os.path.exists(report_folder):
            os.makedirs(report_folder)

        nPYc.reports.generateReport(self.uncorrected_dataset, 'batch correction assessment',destinationPath=report_folder)

        self.correction_task_run.reports = reports
        self.db_session.flush()




class RunCombatCorrection(RAnalysisTask):

    r_code = None
    r_script_path = None
    #r_script_folder = config['R']['script_directory']
    r_template = 'combat.r'
    correction_type = HarmonisedDataset.Type.COMBAT
    sample_types = [SampleType.StudySample]

    def __init__(self,query_factory=None,saved_query_id=None,username=None,task_run_id=None,comment=None,model_Y_variable=None,columns_to_include=None,
                 model_X_variables=None,par_prior=True,prior_plots=False,mean_only=False,ref_batch=None,reload_cache=False,correction_type=None,
                 exclude_samples_with_na_feature_values=True,scaling=None,transform='log',exclude_features_with_na_feature_values=False,pipeline_run_id=None,
                 include_harmonised_metadata=True,batch_variable='Project',db_env=None,db_session=None,execution_date=None,exclude_features_not_in_all_projects=True):
        """Init method

        :param query_factory: The query factory, defaults to None
        :type query_factory: `phenomedb.query_factory.QueryFactory`, optional
        :param saved_query_id: The ID of the SavedQuery, defaults to None
        :type saved_query_id: int, optional
        :param username: The username of the user running the task, defaults to None
        :type username: str, optional
        """

        if columns_to_include is None:
            columns_to_include = [batch_variable]

        super().__init__(query_factory=query_factory,correction_type=correction_type,saved_query_id=saved_query_id,username=username,columns_to_include=columns_to_include,
                         db_env=db_env,db_session=db_session,execution_date=execution_date,transform=transform,include_default_columns=False,exclude_features_not_in_all_projects=exclude_features_not_in_all_projects,
                         task_run_id=task_run_id,exclude_samples_with_na_feature_values=exclude_samples_with_na_feature_values,drop_sample_column=True,pipeline_run_id=pipeline_run_id,
                         exclude_features_with_na_feature_values=exclude_features_with_na_feature_values,scaling=scaling,include_harmonised_metadata=include_harmonised_metadata,
                         exclude_na_metadata_samples=True,exclude_one_factor_columns=False,reload_cache=reload_cache,harmonise_annotations=True)

        self.comment = comment
        self.par_prior = par_prior
        self.prior_plots = prior_plots
        self.mean_only = mean_only
        self.ref_batch = ref_batch
        self.model_Y_variable = model_Y_variable
        self.model_X_variables = model_X_variables
        self.batch_variable = batch_variable

        self.args['batch_variable'] = batch_variable
        self.args['comment'] = comment
        self.args['par_prior'] = par_prior
        self.args['prior_plots'] = prior_plots
        self.args['mean_only'] = mean_only
        self.args['ref_batch'] = ref_batch
        self.args['model_Y_variable'] = model_Y_variable
        self.args['model_X_variables'] = model_X_variables

        if model_Y_variable:
            self.model_X_variables.append(model_Y_variable)

        self.get_class_name(self)


    def method_specific_steps(self):

        # 1. Write out data to /tmp/phenomedb/R_jobs/<self.job_name>/<files>

        intensity_file_path = self.job_folder + "intensity.csv"
        # pd.DataFrame(self.query_factory.intensity_data).to_csv(intensity_file_path,header=False,index=False)
        intensity_data = np.matrix(self.data['intensity_data'])
        pd.DataFrame(intensity_data).to_csv(intensity_file_path, index=False)

        sample_metadata_file_path = self.job_folder + "sample_metadata.csv"
        # self.query_factory.dataframes[self.sample_metadata_key].to_csv(sample_metadata_file_path,index=False)
        sample_metadata = pd.DataFrame.from_dict(self.data['sample_metadata'])
        if 'Sample ID' in sample_metadata.columns:
            sample_metadata = sample_metadata.drop('Sample ID',axis=1)
        sample_metadata.to_csv(sample_metadata_file_path, index=False)

        # 2. Load vars into template_data

        template_data = {'intensity_data_file_path': intensity_file_path,
                         'sample_metadata_file_path':sample_metadata_file_path,
                         'batch_variable': self.batch_variable.replace(" ","."),
                         'par_prior':self.par_prior,
                         'prior_plots':self.prior_plots,
                         'mean_only':self.mean_only,
                         'ref_batch':self.ref_batch,
                         'model_Y_variable':self.model_Y_variable,
                         'model_X_variables':self.model_X_variables}

        self.parameters = template_data

        return template_data

    def save_results(self):
        """Save the results into HarmonisedAnnotatedFeature database table
        """

        self.logger.info("Saving results.....")

        self.results = {#'combined_data':self.clean_data_for_jsonb(self.data['combined_data']),
                        'sample_metadata':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.data['sample_metadata'])),
                        'feature_metadata':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.data['feature_metadata'])),
                        'intensity_data':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.results))}

        super().save_results()
        self.logger.info("Save complete...!")

class RunDBnormCorrection(RAnalysisTask):

    r_code = None
    r_script_path = None
    #r_script_folder = config['R']['script_directory']
    r_template = 'dbnorm.r'
    #correction_type = HarmonisedDataset.Type.COMBAT
    sample_types = [SampleType.StudySample]

    def __init__(self,query_factory=None,saved_query_id=None,username=None,task_run_id=None,comment=None,model_Y_variable=None,pipeline_run_id=None,
                 model_X_variables=None,reload_cache=False,correction_type=None,imputation_method='emvf',scaling=None,transform='log',
                 include_harmonised_metadata=True,batch_variable='Unique Batch',db_env=None,db_session=None,execution_date=None):
        """Init method

        :param query_factory: The query factory, defaults to None
        :type query_factory: `phenomedb.query_factory.QueryFactory`, optional
        :param saved_query_id: The ID of the SavedQuery, defaults to None
        :type saved_query_id: int, optional
        :param username: The username of the user running the task, defaults to None
        :type username: str, optional
        """

        scaling = None

        super().__init__(query_factory=query_factory,correction_type=correction_type,saved_query_id=saved_query_id,username=username,columns_to_include=[],
                         task_run_id=task_run_id,exclude_samples_with_na_feature_values=False,db_env=db_env,pipeline_run_id=pipeline_run_id,
                         db_session=db_session,execution_date=execution_date,scaling=scaling,transform=transform,
                         exclude_features_with_na_feature_values=False,include_harmonised_metadata=include_harmonised_metadata,
                         exclude_na_metadata_samples=False,exclude_one_factor_columns=False,reload_cache=reload_cache,harmonise_annotations=True)

        self.comment = comment
        self.model_Y_variable = model_Y_variable
        self.model_X_variables = model_X_variables
        self.batch_variable = batch_variable
        self.imputation_method = imputation_method

        self.args['imputation_method'] = imputation_method
        self.args['batch_variable'] = batch_variable
        self.args['model_Y_variable'] = model_Y_variable
        self.args['model_X_variables'] = model_X_variables

        self.get_class_name(self)


    def method_specific_steps(self):

        # 1. Write out data to /tmp/phenomedb/R_jobs/<self.job_name>/<files>

        intensity_file_path = self.job_folder + "intensity.csv"
        intensity_data = np.matrix(self.data['intensity_data'])
        pd.DataFrame(intensity_data).to_csv(intensity_file_path, index=False)

        sample_metadata_file_path = self.job_folder + "sample_metadata.csv"
        sample_metadata = pd.DataFrame.from_dict(self.data['sample_metadata'])
        sample_metadata.to_csv(sample_metadata_file_path, index=False)

        batch_dataframe = sample_metadata[[self.batch_variable]].copy()

        dbnorm_file_path = self.job_folder + "dbnorm_dataframe.csv"
        dbnorm_dataframe = pd.concat([batch_dataframe,
                                      pd.DataFrame(np.matrix(self.data['intensity_data']))
                                      ], ignore_index=True, axis=1)
        dbnorm_dataframe.to_csv(dbnorm_file_path, index=False)

        self.task_run_folder = config['DATA']['app_data'] + (
                "task_runs/task_run_%s/" % (self.task_run.id))

        os.makedirs(self.task_run_folder)

        # 2. Load vars into template_data

        template_data = {'dbnorm_file_path': dbnorm_file_path,
                         'intensity_data_file_path': intensity_file_path,
                         'sample_metadata_file_path': sample_metadata_file_path,
                         'batch_variable': self.batch_variable.replace(" ","."),
                         'task_run_folder':self.task_run_folder}

        self.parameters = template_data

        return template_data

    def save_results(self):
        """Save the results into HarmonisedAnnotatedFeature database table
        """

        self.logger.info("Saving results.....")
        #parametric_combat_pdf_file = '%s/dbnormParaComBat_Plot.pdf' % self.job_folder
        #report_path = self.task_run_folder + 'parcombat/'
        #if os.path.exists(parametric_combat_pdf_file):
        #    if not os.path.exists(report_path):
        #        os.makedirs(report_path)
        #    shutil.copy(parametric_combat_pdf_file,report_path+"/report.pdf")
        #tempfolder = self.results[0]
        #if os.path.exists(tempfolder):
        #shutil.copy(tempfolder + "/Rawdata_adjR2.csv",self.task_run_folder + "/Rawdata_adjR2.csv")
        #    shutil.copy(tempfolder + "/SCore_MaxAdjR2.csv", self.task_run_folder + "/SCore_MaxAdjR2.csv")
        #    shutil.copy(tempfolder + "/mydata_parametricComBatCorrected.csv", self.task_run_folder + "/mydata_parametricComBatCorrected.csv")
        #    shutil.copy(tempfolder + "/parametricComBatData_adjR2.csv",self.task_run_folder + "/parametricComBatData_adjR2.csv")

        reports = {}

        for dir in os.listdir(self.task_run_folder):
            if re.search('viewhtml',dir):
                report_folder = self.task_run_folder + "reports/" + dir
                shutil.move(self.task_run_folder + dir,report_folder)
                reports[dir] = report_folder

        intensity_data_all = pd.read_csv(self.task_run_folder + "mydata_parametricComBatCorrected.csv")
        intensity_data = intensity_data_all.drop(['Unnamed: 0', 'Batch'], axis=1)

        self.results = {'raw_data_adjR2':
                            utils.convert_to_json_safe(self.clean_data_for_jsonb(
                                pd.read_csv(self.task_run_folder + "Rawdata_adjR2.csv").to_dict()
                            )),
                        'score_max_adjR2':
                            utils.convert_to_json_safe(self.clean_data_for_jsonb(
                                pd.read_csv(self.task_run_folder + "SCore_MaxAdjR2.csv").to_dict()
                            )),
                        'intensity_data':
                            utils.convert_to_json_safe(self.clean_data_for_jsonb(intensity_data)),
                        'corrected_data_adjR2.csv':
                            utils.convert_to_json_safe(self.clean_data_for_jsonb(
                                pd.read_csv(self.task_run_folder + "parametricComBatData_adjR2.csv").to_dict()
                            )),
                        'pdf_report':self.task_run_folder + 'dbnormParaComBat_Plot.pdf'}

        self.task_run.reports = reports
        #self.task_run.pdf_reports = {'Parametric ComBat correction': report_path}


        #self.results = {'sample_metadata':self.data['sample_metadata'],
        #                'feature_metadata':self.data['feature_metadata'],
        #                'intensity_data':self.results}

        #self.results = {'sample_metadata': self.data['sample_metadata'],
        #                'feature_metadata':self.data['feature_metadata']}

        super().save_results()
        self.logger.info("Save complete...!")

class RunNormResidualsMM(RAnalysisTask):

    r_code = None
    r_script_path = None
    #r_script_folder = config['R']['script_directory']
    r_template = 'norm_residual_mixed_models.r'
    #correction_type = HarmonisedDataset.Type.COMBAT
    sample_types = [SampleType.StudySample]

    def __init__(self,query_factory=None,saved_query_id=None,db_env=None,db_session=None,execution_date=None,username=None,pipeline_run_id=None,
                 task_run_id=None,comment=None,heteroscedastic_columns=None,transform='log',exclude_features_not_in_all_projects=False,
                 reload_cache=False,correction_type=None,columns_fixed_to_keep=None,columns_fixed_to_correct=None,scaling=None,
                 include_harmonised_metadata=True,columns_random_to_correct=None,identifier_column='Sample File Name'):
        """Init method

        :param query_factory: The query factory, defaults to None
        :type query_factory: `phenomedb.query_factory.QueryFactory`, optional
        :param saved_query_id: The ID of the SavedQuery, defaults to None
        :type saved_query_id: int, optional
        :param username: The username of the user running the task, defaults to None
        :type username: str, optional
        """

#        scaling = None

        super().__init__(query_factory=query_factory,correction_type=correction_type,saved_query_id=saved_query_id,username=username,columns_to_include=['Project','Unique Batch','Sample File Name','Sample ID'],
                         task_run_id=task_run_id,exclude_samples_with_na_feature_values=False,db_env=db_env,db_session=db_session,execution_date=execution_date,scaling=scaling,
                         exclude_features_with_na_feature_values=False,transform=transform,include_harmonised_metadata=include_harmonised_metadata,pipeline_run_id=pipeline_run_id,
                         exclude_na_metadata_samples=False,exclude_one_factor_columns=False,reload_cache=reload_cache,harmonise_annotations=True,exclude_features_not_in_all_projects=exclude_features_not_in_all_projects)

        self.comment = comment

        if not columns_random_to_correct:
            columns_random_to_correct = ['Project', 'Unique Batch']
            heteroscedastic_columns = ['Project','Unique Batch']
        elif not heteroscedastic_columns and len(columns_random_to_correct) == 1 and columns_random_to_correct[0] == 'Project':
            heteroscedastic_columns = ['Project']
        elif not heteroscedastic_columns and len(columns_random_to_correct) == 1 and columns_random_to_correct[0] == 'Unique Batch':
            heteroscedastic_columns = ['Unique Batch']
        elif not heteroscedastic_columns and len(columns_random_to_correct) == 1 and columns_random_to_correct[0] == 'Batch':
            heteroscedastic_columns = ['Batch']
        elif not heteroscedastic_columns and len(columns_random_to_correct) == 2 and 'Unique Batch' in columns_random_to_correct and 'Project' in columns_random_to_correct:
            heteroscedastic_columns = ['Project','Unique Batch']

        if not columns_fixed_to_correct:
            columns_fixed_to_correct = []
        if not columns_fixed_to_keep:
            columns_fixed_to_keep = []

        self.columns_random_to_correct = columns_random_to_correct
        self.columns_fixed_to_correct = columns_fixed_to_correct
        self.columns_fixed_to_keep = columns_fixed_to_keep
        self.identifier_column = identifier_column
        self.heteroscedastic_columns = heteroscedastic_columns

        #self.args['batch_variable'] = batch_variable
        self.args['comment'] = comment
        self.args['columns_random_to_correct'] = columns_random_to_correct
        self.args['columns_fixed_to_correct'] = columns_fixed_to_correct
        self.args['columns_fixed_to_keep'] = columns_fixed_to_keep
        self.args['identifier_column'] = identifier_column
        self.args['heteroscedastic_columns'] = heteroscedastic_columns


        self.get_class_name(self)


    def method_specific_steps(self):
        # https://code.iarc.fr/viallonv/pipeline_biocrates/-/blob/master/Illustration_EPICBiocratesData.Rmd

        # 1. Write out data to /tmp/phenomedb/R_jobs/<self.job_name>/<files>

        intensity_file_path = self.job_folder + "intensity.csv"
        intensity_data = np.matrix(self.data['intensity_data'])
        pd.DataFrame(intensity_data).to_csv(intensity_file_path, index=False)

        self.identifier_column = 'Sample File Name'
        #self.columns_fixed_to_correct = ['Project','Unique Batch']
        #self.columns_fixed_to_keep = ['h_metadata::Age','h_metadata::Sex']

        sample_metadata = pd.DataFrame.from_dict(self.data['sample_metadata'])
        feature_metadata = pd.DataFrame.from_dict(self.data['feature_metadata'])
        self.combined_dataframe = utils.build_combined_dataframe_from_seperate(intensity_data, sample_metadata, feature_metadata)

        metabo = pd.DataFrame()
        others = pd.DataFrame()

        self.original_feature_ids = {}

        p = 0
        while p < self.combined_dataframe.shape[1]:

            colname = self.combined_dataframe.columns[p]

            # Put this in both dataframes
            if colname == self.identifier_column or colname in self.columns_random_to_correct:
                metabo.insert(len(metabo.columns), colname, self.combined_dataframe.loc[:, colname])
                others.insert(len(others.columns), colname, self.combined_dataframe.loc[:, colname])

            # just metabo
            elif re.search('feature:',colname):

                # is harmonised
                if re.search('feature.ha.',colname):
                    feature_metadata_id, harmonised_annotation_id, assay, annotation_method, feature_name, version, unit = utils.breakdown_annotation_id(colname,harmonise_annotations=True)
                    unique_column_name = "ha." + harmonised_annotation_id
                # is compound_class
                elif re.search('compound_class',colname):
                    compound_class_id, class_type, class_level, class_name, unit = utils.breakdown_compound_class_id(colname)
                    unique_column_name = "cc." + compound_class_id
                # is unique per study (not harmonised)
                else:
                    feature_metadata_id, harmonised_annotation_id, assay, annotation_method, feature_name, version, unit = utils.breakdown_annotation_id(colname, harmonise_annotations=False)
                    unique_column_name = "fm.".feature_metadata_id

                metabo.insert(len(metabo.columns), unique_column_name, self.combined_dataframe.loc[:,colname])
                self.original_feature_ids[unique_column_name] = colname

            # just others
            elif colname in self.columns_fixed_to_keep:
                others.insert(len(others.columns),colname,self.combined_dataframe.loc[:,colname])

            p = p + 1

        metabo_file_path = self.job_folder + "metabo.csv"
        metabo.to_csv(metabo_file_path, index=False)
        others_file_path = self.job_folder + "others.csv"
        others.to_csv(others_file_path, index=False)

        aux = pd.DataFrame(columns=['Name','Class','Type'])
        i = 0
        while i < feature_metadata.shape[0]:
            feature_id = feature_metadata.loc[i,'feature_id']

            if re.search('feature.ha.', feature_id):
                feature_metadata_id, harmonised_annotation_id, assay, annotation_method, feature_name, version, unit = utils.breakdown_annotation_id(
                    feature_id, harmonise_annotations=True)
                unique_column_name = "ha." + harmonised_annotation_id
            # is compound_class
            elif re.search('compound_class',feature_id):
                compound_class_id, class_type, class_level, class_name, unit = utils.breakdown_compound_class_id(
                    feature_id)
                unique_column_name = "cc." + compound_class_id
            # is unique per study (not harmonised)
            else:
                feature_metadata_id, harmonised_annotation_id, assay, annotation_method, feature_name, version, unit = utils.breakdown_annotation_id(
                    feature_id, harmonise_annotations=False)
                unique_column_name = "fm." + feature_metadata_id

            if feature_metadata.loc[i, 'QuantificationType'] == 'absolute':
                feature_type = 'quantified'
            elif feature_metadata.loc[i, 'QuantificationType'] == 'relative':
                feature_type = 'semi-quantified'
            else:
                raise Exception("Unknown QuantificationType %s" % feature_metadata.loc[i, 'QuantificationType'])
            if 'c1#classyfire Sub Class' in feature_metadata.columns:
                feature_class = feature_metadata.loc[i, 'c1#classyfire Sub Class']
            elif 'Compound Class Name' in feature_metadata.columns:
                feature_class = feature_metadata.loc[i, 'Compound Class Name']
            else:
                feature_class = 'Unknown'
            aux.loc[i] = [unique_column_name,feature_class,feature_type]
            i = i + 1
        aux_file_path = self.job_folder + "aux.csv"
        aux.to_csv(aux_file_path,index=False)

        # 2. Load vars into template_data

        template_data = {'metabo_file_path': metabo_file_path,
                         'others_file_path':others_file_path,
                         'aux_file_path': aux_file_path,
                         'identifier_column': self.identifier_column,
                         'columns_random_to_correct': self.columns_random_to_correct,
                         'columns_fixed_to_keep': self.columns_fixed_to_keep,
                         'heteroscedastic_columns': self.heteroscedastic_columns,
                         }
                         #'batch_variable': self.batch_variable.replace(" ","."),
                         #'model_Y_variable':self.model_Y_variable,
                         #'model_X_variables':self.model_X_variables}

        self.parameters = template_data

        return template_data

    def save_results(self):
        """Save the results. Reconstruct the dataframes with corrected data.
        """

        self.logger.info("Saving results.....")

        corrected_intensity_data = np.matrix(self.data['intensity_data'])
        feature_metadata_original = pd.DataFrame.from_dict(self.data['feature_metadata'])
        corrected_data_from_R = pd.DataFrame.from_dict(self.results['data'])
        corrected_data_from_R = corrected_data_from_R.set_index(self.identifier_column.replace(' ','.'))
        corrected_data_from_R = corrected_data_from_R.reindex(index=self.combined_dataframe[self.identifier_column])
        corrected_data_from_R = corrected_data_from_R.reset_index()
        corrected_features = []
        p = 0
        matrix_col_p = 0
        while p < corrected_data_from_R.shape[1]:
            colname = corrected_data_from_R.columns[p]
            if colname in self.original_feature_ids.keys():
                original_combined_column_id = self.original_feature_ids[colname]
                # Update the combined_original_dat
                self.combined_dataframe.loc[:,original_combined_column_id] = corrected_data_from_R.loc[:,colname]

                # check its not been unsorted somewhere.
                try:
                    feature_index = np.where(feature_metadata_original.loc[:, 'feature_id'] == original_combined_column_id)[0][0]
                except:
                    feature_index = None
                    self.logger.info("Unable to find feature index %s" % feature_metadata_original.loc[:, 'feature_id'])

                if feature_index is not None:
                    corrected_intensity_data[:,matrix_col_p] = np.transpose(np.matrix(corrected_data_from_R.loc[:,colname].to_numpy()))
                    corrected_features.append(feature_metadata_original.loc[:, 'feature_id'])
                else:
                    corrected_intensity_data[:,matrix_col_p] = 0

                matrix_col_p = matrix_col_p + 1

            p = p + 1

        self.results = {'combined_data':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.combined_dataframe)),
                        'intensity_data':utils.convert_to_json_safe(self.clean_data_for_jsonb(corrected_intensity_data)),
                        'sample_metadata':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.data['sample_metadata'])),
                        'feature_metadata':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.data['feature_metadata']))}

        super().save_results()
        self.logger.info("Save complete...!")