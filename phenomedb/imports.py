import nPYc
import os
from abc import abstractmethod
from phenomedb.task import Task
from phenomedb.models import *
from phenomedb.utilities import *
from phenomedb.exceptions import *
from nPYc.enumerations import *
import numpy as np
import pandas as pd
import datetime
import re
import json
from sqlalchemy import func
import math
from pathlib import Path
from dateutil import parser
from random import *
import json
#from redisearch import Client, Query
import redis
import requests
from phenomedb.query_factory import *
from libchebipy._chebi_entity import ChebiEntity

class ImportTask(Task):
    """The ImportTask class. Used as the base class for the major import methods. Not used for compounds. Should not be instantiated itself, only from a child class.

    :param project_name: The name of the project, defaults to None
    :type project_name: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """

    feature_names_ignored = []
    assay_name = None
    project_name = None
    project = None
    annotation_method_name = None
    assay = None
    annotation_method = None

    def __init__(self,project_name=None,task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,validate=True,pipeline_run_id=None):


        self.project_name = project_name
        self.feature_dataset = None
        self.missing_import_data = []
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

        self.args['project_name'] = project_name
        #self.logger = configure_logging(self.get_class_name() + " " + str(project_name), "phenomedb-tasks.log")

    def send_user_failure_email(self,err):
        """Send a TaskRun failure email to the user

        :param err: The error message
        :type err: str
        """


        if self.username and self.db_env != 'TEST':

            email = self.username + "@ic.ac.uk"
            subject = 'PhenomeDB ImportTask failed: %s %s' % (self.db_env, self.class_name)
            body = "PhenomeDB ImportTask failed: %s %s %s %s" % (self.db_env,self.class_name, self.task_run, err)

            try:
                utils.send_tls_email(email,subject,body)
            except Exception:
                self.logger.warning("Email failed")

    def send_user_success_email(self):
        """Send a TaskRun success email to the user

        :param err: The error message
        :type err: str
        """

        if self.username and self.db_env != 'TEST':

            email = self.username + "@ic.ac.uk"
            subject = 'PhenomeDB ImportTask successful: %s %s' % (self.db_env, self.class_name)
            body = "PhenomeDB ImportTask successful: %s %s %s %s" % (self.db_env, self.class_name, self.task_run, self.output)

            try:
                utils.send_tls_email(email,subject,body)
            except Exception:
                self.logger.warning("Email failed")

    def get_project(self):
        """Gets a project to the database (by project_name)

        :raises Exception: If no project by that name exists
        :return: sample_assay object :class:`phenomedb.models.Project`
        :rtype: class:`phenomedb.models.Project`
        """
        self.project = self.db_session.query(Project).filter(func.lower(Project.name)==self.project_name.lower()).first()

        if not self.project:

            raise Exception("Project not recognised: " + self.project_name)

    def get_annotated_feature(self,feature_metadata_id,sample_assay_id):
        """Get a annotated_feature by feature metadata id and sample_assay.id

        :param feature_metadata_id: The id of the annotation
        :type feature_metadata_id: int
        :param sample_assay_id: The id of the SampleAssay
        :type sample_assay_id: int
        :return: The AnnotatedFeature
        :rtype: :class:`phenomedb.models.AnnotatedFeature`
        """

        return self.db_session.query(AnnotatedFeature) \
            .filter(AnnotatedFeature.feature_metadata_id == feature_metadata_id) \
            .filter(AnnotatedFeature.sample_assay_id==sample_assay_id).first()

    def get_sample_assay(self,sample,sample_row_index):
        """Get or add a new sample_assay

        :param sample: The sample of the sample_assay
        :type sample: :class:`phenomedb.models.sample`
        :param sample_row_index: The dataset row index of the sample
        :type sample_row_index: int
        :return: sample_assay object :class:`phenomedb.models.SampleAssay`
        :rtype: class:`phenomedb.models.sample_assay`
        """

        sample_assay = self.db_session.query(SampleAssay) \
            .filter(SampleAssay.assay_id==self.assay.id) \
            .filter(SampleAssay.sample_id==sample.id).first()

        if(sample_assay is None):

            missing_import_data = MissingImportData(task_run_id=self.task_run.id,
                                                    type='SampleAssay.assay_id + SampleAssay.sample_id',
                                                    value="assay_id:" + str(self.assay.id) + ":sample_id:" + str(sample.id),
                                                    comment="Sampling Event Assay not found: " + str(sample.name) + " - row index: " + str(sample_row_index))
            self.db_session.add(missing_import_data)
            self.db_session.flush()
            self.missing_import_data.append(missing_import_data)

            return None

        return sample_assay

    def get_annotation_by_cpd_name_and_annotation_method(self,cpd_name):
        """Get the annotation by cpd_name

        :param cpd_name: The name of the compound as seen seen in the annotation datasets
        :type cpd_name: str
        :return: The found AnnotationCompound
        :rtype: :class:`phenomedb.models.AnnotationCompound`
        """

        cpd_name = cpd_name.strip()

        annotation = self.db_session.query(Annotation) \
            .filter(Annotation.annotation_method_id==self.annotation_method.id) \
            .filter(Annotation.cpd_name==cpd_name) \
            .filter(Annotation.assay_id==self.assay.id).first()

        if not annotation:

            annotation = self.db_session.query(Annotation) \
                .filter(Annotation.annotation_method_id==self.annotation_method.id) \
                .filter(Annotation.assay_id==self.assay.id) \
                .filter(Annotation.cpd_name==cpd_name+"_1").first()

            if not annotation:
                return None

        return annotation

    def get_or_build_subject_name(self,index,sample_metadata_row,sample_type_column_name='SampleType',subject_column_name='Subject ID'):
        """Get or build subject name

        :param index: The row index
        :type index: int
        :param sample_metadata_row: The sample_metadata row
        :type sample_metadata_row: :class:`numpy.Series`
        :param sample_type_column_name: The name of the column with SampleType, defaults to 'SampleType'
        :type sample_type_column_name: str, optional
        :param subject_column_name: The name of the column with the Subject ID, defaults to 'Subject ID'
        :type subject_column_name: str, optional
        :return: The subject name
        :rtype: str
        """

        if subject_column_name in sample_metadata_row and sample_metadata_row[sample_type_column_name] == SampleType.StudySample.value:
            return sample_metadata_row[subject_column_name]
        elif sample_metadata_row[sample_type_column_name] == SampleType.StudySample.value:
            return sample_metadata_row[sample_type_column_name]
        elif sample_metadata_row[sample_type_column_name] == SampleType.ProceduralBlank.value:
            return 'Blank'
        elif sample_metadata_row[sample_type_column_name] == SampleType.StudyPool.value:
            return 'Study Pool'
        elif sample_metadata_row[sample_type_column_name] == SampleType.ExternalReference.value:
            return 'Long Term Reference'
        else:
            return "Unknown"

    def get_or_add_subject(self,sample_row_index):
        """Get or add a new subject

        :param index: The row number of the sample_metadata
        :type index: int
        :return: subject object :class:`phenomedb.models.subject`
        :rtype: class:`phenomedb.models.subject`
        """

        subject_name = self.get_or_build_subject_name(sample_row_index,self.dataset.loc[sample_row_index])

        subject = self.db_session.query(Subject).filter(Subject.name==subject_name).filter(Subject.project_id==self.project.id).first()

        if(subject is None):

            subject = Subject( name=subject_name,
                               project_id=self.project.id)

            self.db_session.add(subject)
            self.db_session.flush()

        return subject


    def get_or_build_sample_name(self,sample_row_index,column=None):
        """Get or build the sample name

        :param sample_row_index: The row index of the sample metadata
        :type sample_row_index: int
        :param column: The column name to use, default None
        :type sample_row_index: str, optional
        :raises Exception: Sample ID not found
        :return: The sample name
        :rtype: str
        """

        if column and column in self.dataset.loc[sample_row_index]:
            sample_id_field = column
        else:
            if 'Sampling ID' in self.dataset.loc[sample_row_index]:
                sample_id_field = 'Sampling ID'
            elif 'Sample ID' in self.dataset.loc[sample_row_index]:
                sample_id_field = 'Sample ID'
            else:
                sample_id_field = None
                if 'Sample File Name' in self.dataset.loc[sample_row_index]:
                    return None

        if sample_id_field:

            if 'SampleType' in self.dataset.loc[sample_row_index] and self.dataset.loc[sample_row_index,'SampleType'] == SampleType.StudySample.value:
                return self.dataset.loc[sample_row_index,sample_id_field]

            elif self.dataset.loc[sample_row_index,sample_id_field] != 'Study Pool Sample':
                return self.dataset.loc[sample_row_index,sample_id_field]

            elif self.dataset.loc[sample_row_index,sample_id_field] == 'Study Pool Sample':
                return self.dataset.loc[sample_row_index,'Sample File Name']

            elif sample_id_field in self.dataset.loc[sample_row_index]:
                return self.dataset.loc[sample_row_index,sample_id_field]

            else:
                self.logger.info('No field called ' + sample_id_field)
                return None

        elif 'SampleType' in self.dataset.loc[sample_row_index] and self.dataset.loc[sample_row_index,'SampleType'] in [SampleType.ExternalReference.value,SampleType.StudyPool.value,SampleType.MethodReference.value,SampleType.ProceduralBlank.value]:
            return self.dataset.loc[sample_row_index,'Sample File Name']

        else:
            self.logger.info(str(self.dataset.loc[sample_row_index]))
            raise Exception("Sample name not recognised: sample_row_index "+str(sample_row_index))


    def get_or_add_sample(self,subject,sample_row_index):
        """Get or add a new sample

        :param subject: The subject of the sample
        :type subject: :class:`phenomedb.models.subject`
        :param sample_row_index: The dataset row index the sample
        :type sample_row_index: in
        :return: sample object :class:`phenomedb.models.Sample`
        :rtype: class:`phenomedb.models.Sample`
        """

        sample_name = self.dataset.loc[sample_row_index,'Sample ID']

        sample = self.db_session.query(Sample).filter(Sample.name==sample_name).filter(Sample.subject_id==subject.id).first()

        if(sample == None):

            if(self.dataset.loc[sample_row_index,'SampleType'] == SampleType.StudySample.value):

                Exception('Sample ID not found: ' + sample_name + " - file row: " + str(sample_row_index))

            else:

                sample = Sample(name=sample_name,
                                               sample_type=self.dataset.loc[sample_row_index,'SampleType'].replace(' ',''),
                                               assay_role=self.dataset.loc[sample_row_index,'AssayRole'].replace(' ',''),
                                               sample_matrix=self.sample_matrix,
                                               subject_id=subject.id)

                self.db_session.add(sample)
                self.db_session.flush()

        return sample

    def add_metadata_field_and_value(self,sample_id,field_name,field_value):
        """Adds and flushes the metadata field and values

        :param sample_id: The :class:`phenomedb.model.Sample` ID
        :type sample_id: int
        :param field_name: The name of the metadata field
        :type field_name: str
        :param field_value: The value of the metadata field for the sample
        :type field_value: str
        """

        # Do not import if it's blank or nan or if the field name is 'Unnamed X'
        if str(field_value) == '' \
                or str(field_value) == 'nan' \
                or re.match(r'Unnamed: [0-9]+',field_name) \
                or field_value is None:
            self.logger.info("Ignoring metadata field %s = %s ", str(field_name), str(field_value))
            return

        self.logger.info("Adding metadata field %s = %s ", str(field_name), str(field_value))

        # GET OR ADD THE FIELD
        metadata_field = self.db_session.query(MetadataField) \
            .filter(MetadataField.project_id==self.project.id) \
            .filter(MetadataField.name==str(field_name)) \
            .first()

        if not metadata_field:
            metadata_field = self.add_metadata_field(field_name)

        # GET OR ADD THE VALUE
        metadata_value = self.db_session.query(MetadataValue) \
            .filter(MetadataValue.sample_id==sample_id) \
            .filter(MetadataValue.metadata_field_id==metadata_field.id).first()

        if not metadata_value:
            self.add_metadata_value(metadata_field,sample_id,field_value)
        elif metadata_value.raw_value != field_value:
            metadata_value.raw_value = field_value
            self.db_session.flush()

    def add_metadata_field(self,field_name):
        """Add a :class:`phenomedb.models.MetadataField`

        :param field_name: The :class:`phenomedb.models.MetadataField` name
        :type field_name: str
        :return: The added :class:`phenomedb.models.MetadataField`
        :rtype: :class:`phenomedb.models.MetadataField`
        """

        metadata_field = MetadataField(project_id=self.project.id,
                                       name=str(field_name))
        self.db_session.add(metadata_field)
        self.db_session.flush()

        return metadata_field


    def add_metadata_value(self,metadata_field,sample_id,field_value):
        """Add a :class:`phenomedb.models.MetadataValue`.

        :param metadata_field: The :class:`phenomedb.models.MetadataField`
        :type metadata_field: :class:`phenomedb.models.MetadataField`
        :param sample_id: The :class:`phenomedb.models.Sample` ID
        :type sample_id: int
        :param field_value: The value of the metadata field for the sample
        :type field_value: str
        """
        

        metadata_value = MetadataValue(sample_id=sample_id,
                                       raw_value=str(field_value),
                                       metadata_field_id=metadata_field.id)
        self.db_session.add(metadata_value)
        self.db_session.flush()

    @abstractmethod
    def load_dataset(self):
        """Load that dataset. This method should be over-ridden in the task class.
           This method can call a python package or do a system call.
        """
        pass

    @abstractmethod
    def map_and_add_dataset_data(self):
        """Map the dataset and import to phenomeDB
        """
        pass


    def process(self):
        """Main method
        """        

        if self.project_name:
            self.get_or_add_project(self.project_name)
        if self.assay_name:
            self.get_or_add_assay(self.assay_name)
        if self.annotation_method_name:
            self.get_or_add_annotation_method(self.annotation_method_name)
        self.load_dataset()
        self.map_and_add_dataset_data()

    def task_validation(self):
        """Validate the task - default method
        """

        self.clear_saved_query_cache()

    def simple_report(self):
        """Check the database contains entries for all records in the dataset
        """

        counts = {}
        text = ''
        project = self.db_session.query(Project).filter(Project.id == self.project.id).first()
        try:
            counts = project.getCounts()
            text = counts.pop("text")
        except NameError:
            pass

        self.task_run.output['counts'] = counts
        self.logger.info("Project counts: %s" % text)

        if self.feature_dataset:
            self.task_run.output['saved_query_id'] = self.feature_dataset.saved_query_id

        self.logger.info("Missing import data: " + str(self.missing_import_data))

    def parse_value(self,value):
        """Parse a raw value to convert the necessary type

        :param value: The raw value to convert
        :type value: object
        :return: The parsed, converted value
        :rtype: float
        """

        if value == '-':
            value = None
        elif str(value).lower() == 'nan':
            value = None
        elif is_number(value):
            value = float(value)

        return value

class ImportSampleManifest(ImportTask):
    """Import a Sample Manifest XLS file. The format of which is an excel file with 2 sheets, one called 'samples' with sample-level metadata, another called 'subjects', with subject-level metadata. Both sample-level and subject-level metadata are imported at the sample-level.

    :param sample_manifest_path: _description_, defaults to None
    :type sample_manifest_path: str, optional
    :param columns_to_ignore: _description_, defaults to None
    :type columns_to_ignore: str, optional
    :param project_name: The name of the project, defaults to None
    :type project_name: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """

    already_mapped_fields = ['Subject ID','Original Sampling ID','Sampling ID','Sample Type', 'Sampling Date', 'Box location','Comment']

    def __init__(self,project_name=None,sample_manifest_path=None,columns_to_ignore=None,task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,validate=True,pipeline_run_id=None):
    
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

        self.sample_manifest_path = sample_manifest_path
        if columns_to_ignore:
            if not isinstance(columns_to_ignore,list):
                self.columns_to_ignore = columns_to_ignore.split(" ")
            else:
                self.columns_to_ignore = columns_to_ignore
        else:
            self.columns_to_ignore = []
        self.args['sample_manifest_path'] = sample_manifest_path
        self.args['columns_to_ignore'] = columns_to_ignore
        self.get_class_name(self)

    # Load the nPYC dataset
    def load_dataset(self):
        """Loads the task dataset

        :raises Exception: If the file extension is not .xlsx or .xlsx
        """

        self.logger.info("Loading Dataset")
        path = str(Path(self.sample_manifest_path).absolute())
        self.logger.info("XLS Path :: "+path)

        filename, file_extension = os.path.splitext(path)

        if file_extension.lower() == '.xls':
            engine = 'xlrd'
        elif file_extension.lower() == '.xlsx':
            engine = 'openpyxl'
        else:
            raise Exception('File extension not XLS or XLSX')

        self.subject_dataset = pd.read_excel(path,engine=engine,sheet_name='Subject Info', dtype={'Subject ID':str,'Class':object,'Age':object,'Gender':object})
        self.sample_dataset = pd.read_excel(path,engine=engine,sheet_name='Sampling Events',dtype={'Sampling ID':str,'Subject ID':str,'Sample Type':object,'Sampling Date':object})

        self.subject_dataset = self.subject_dataset.where(pd.notnull(self.subject_dataset), None)
        self.sample_dataset = self.sample_dataset.where(pd.notnull(self.sample_dataset), None)

        #self.subject_dataset.dropna(how='all', axis='columns')
        #self.sample_dataset.dropna(how='all', axis='columns')

        self.logger.info("subject types %s", self.subject_dataset.dtypes)
        self.logger.info("sample types %s", self.sample_dataset.dtypes)
        sub_fields = []
        samp_fields = []

        for sub_field in list(self.subject_dataset.columns):
            if not re.search(r'Unnamed:',sub_field):
                sub_fields.append(sub_field)

        for samp_field in list(self.sample_dataset.columns):
            if not re.search(r'Unnamed:',samp_field):
                samp_fields.append(samp_field)

        cols_to_ignore = self.columns_to_ignore + self.already_mapped_fields

        self.cleaned_subject_fields = [x for x in sub_fields if x not in cols_to_ignore]

        self.cleaned_sample_fields = [x for x in samp_fields if x not in cols_to_ignore]

        self.cleaned_all_fields = self.cleaned_subject_fields + self.cleaned_sample_fields

        print('columns to ignore')
        print(self.columns_to_ignore)
        print('cols to ignore')
        print(cols_to_ignore)
        print('cleaned all fields')
        print(self.cleaned_all_fields)

    def get_or_add_subject(self,subject_name):
        """Get or add the subject

        :param subject_name: the :class:`phenomedb.models.Subject` name
        :type subject_name: str
        :return: the matching :class:`phenomedb.models.Subject`
        :rtype: :class:`phenomedb.models.subject`
        """

        self.logger.info("type of subject %s is %s", subject_name, type(subject_name))
        subject = self.db_session.query(Subject).filter(Subject.name==subject_name) \
            .filter(Subject.project_id==self.project.id).first()

        if subject is None:
            subject = Subject( name=subject_name,
                               project_id=self.project.id)
            self.db_session.add(subject)
            self.db_session.flush()

        return subject

    def get_or_add_sample(self,subject,sample_row_index):
        """Get or add a sample

        :param subject: the subject of the sample
        :type subject: :class:`phenomedb.models.subject`
        :param sample_row_index: The dataset row index of the sample
        :type sample_row_index: int
        :return: sample object :class:`phenomedb.models.Sample`
        :rtype: :class:`phenomedb.models.sample`
        """

        sample_name = self.sample_dataset.loc[sample_row_index,'Sampling ID'].replace(",","_").strip()

        sample = self.db_session.query(Sample).filter(Sample.name==sample_name) \
            .filter(Sample.subject_id==subject.id) \
            .filter(Sample.sample_matrix==self.sample_dataset.loc[sample_row_index,'Sample Type'].lower().strip().replace("plasma bile acids","plasma")).first()

        if sample == None:
            sampling_date = None
            try:
                if math.isnan(self.sample_dataset.loc[sample_row_index,'Sampling Date']):
                    sampling_date = None
            except:

                try:
                    sampling_date = self.sample_dataset.loc[sample_row_index,'Sampling Date']
                except:
                    sampling_date = None

            try:
                if pd.isna(sampling_date):
                    sampling_date = None
            except:
                sampling_date = sampling_date

            if isinstance(sampling_date,str):
                sampling_date = parser.parse(sampling_date)

            sample_matrix = self.sample_dataset.loc[sample_row_index,'Sample Type'].strip().lower()

            sample = Sample(name=sample_name,
                           sample_type=SampleType.StudySample,
                           assay_role=AssayRole.Assay,
                           sample_matrix=sample_matrix,
                           biological_tissue=Sample.get_biological_tissue(sample_matrix),
                           sampling_date=sampling_date,
                           subject_id=subject.id)

            self.db_session.add(sample)
            self.logger.info("Added new sample for sample %s on %s",sample_name,sampling_date)
            self.db_session.flush()

        return sample

    def add_metadata_from_subject_worksheet(self, sample, sample_row_index,metadata_row={}):
        """Adds metadata fields from the subject worksheet

        :param sample: sample object :class:`phenomedb.models.Sample`
        :type sample: :class:`phenomedb.models.Sample`
        :param sample_row_index: The dataset row index
        :type sample_row_index: int
        """

        subject_row_index = np.where(self.subject_dataset.loc[:,'Subject ID'] == self.sample_dataset.loc[sample_row_index,'Subject ID'])[0][0]

        for field_name,field_value in self.subject_dataset.loc[subject_row_index,:].iteritems():
            if field_name in self.cleaned_all_fields:
                self.add_metadata_field_and_value(sample.id,field_name,field_value)
                if str(field_value).lower() == 'nan':
                    metadata_row[field_name] = None
                else:
                    metadata_row[field_name] = field_value

        return metadata_row


    def add_metadata_from_sample_worksheet(self,sample,sample_row_index,metadata_row={}):
        """Adds metadata from the sample worksheet

        :param sample: sample object :class:`phenomedb.models.Sample`
        :type sample: :class:`phenomedb.models.Sample`
        :param sample_row_index: The dataset row index
        :type sample_row_index: int
        """

        for field_name,field_value in self.sample_dataset.loc[sample_row_index,:].iteritems():
            if field_name in self.cleaned_all_fields:
                self.add_metadata_field_and_value(sample.id,field_name,field_value)
                if str(field_value).lower() == 'nan':
                    metadata_row[field_name] = None
                else:
                    metadata_row[field_name] = field_value

        return metadata_row


    def add_metadata(self,sample,sample_row_index):
        """Add the raw metadata to the metadata_raw table

        :param sample: The sampling event of metadata_raw
        :type sample: :class:`phenomedb.models.Sample`
        :param sample_row_index: The dataset row index
        :type sample_row_index: int
        :return:
        """

        if self.cleaned_subject_fields:
            metadata_row = self.add_metadata_from_subject_worksheet(sample,sample_row_index,metadata_row={})
        if self.cleaned_sample_fields:
            metadata_row = self.add_metadata_from_sample_worksheet(sample,sample_row_index,metadata_row=metadata_row)

        sample.sample_metadata = utils.serialise_unserialise(metadata_row)


    def map_and_add_dataset_data(self):
        """Map the imported nPYc dataset to the phenomeDB models and add to db.
        """

        #1. Loop over each sample and import metadata fields

        sample_row_index = 0

        self.logger.info("Number of rows: " + str(len(self.sample_dataset.loc[:,'Sampling ID'])))

        while(sample_row_index < len(self.sample_dataset.loc[:,'Sampling ID'])):

            subject_id = self.sample_dataset.loc[sample_row_index,'Subject ID']

            if str(subject_id).lower() == 'nan':
                break
                #sample_row_index = sample_row_index + 1
                #continue
            else:
                subject = self.get_or_add_subject(subject_id)

            sample = self.get_or_add_sample(subject,sample_row_index)

            self.add_metadata(sample,sample_row_index)

            sample_row_index = sample_row_index + 1

    def task_validation(self):
        """Task validation, checks every entry exists in the database, and the values match.

        :raises ValidationError: MetadataField incorrectly added
        :raises ValidationError: MetadataField missing
        :raises ValidationError: MetadataValue incorrectly added
        :raises ValidationError: MetadataValue missing
        """

        super().task_validation()

        return

        filename, file_extension = os.path.splitext(self.sample_manifest_path)

        if file_extension.lower() == '.xls':
            engine = 'xlrd'
        elif file_extension.lower() == '.xlsx':
            engine = 'openpyxl'

        subject_dataset = pd.read_excel(self.sample_manifest_path,engine=engine,sheet_name='Subject Info', dtype={'Subject ID':str,'Class':object,'Age':object,'Gender':object})
        sample_dataset = pd.read_excel(self.sample_manifest_path,engine=engine,sheet_name='Sampling Events',dtype={'Sampling ID':str,'Subject ID':str,'Sample Type':object,'Sampling Date':object})

        subject_dataset = subject_dataset.where(pd.notnull(subject_dataset), None)
        sample_dataset = sample_dataset.where(pd.notnull(sample_dataset), None)

        sub_fields = []
        samp_fields = []

        for sub_field in list(subject_dataset.columns):
            if not re.search(r'Unnamed:',sub_field):
                sub_fields.append(sub_field)

        for samp_field in list(sample_dataset.columns):
            if not re.search(r'Unnamed:',samp_field):
                samp_fields.append(samp_field)

        cols_to_ignore = self.columns_to_ignore + self.already_mapped_fields

        cleaned_subject_fields = [x for x in sub_fields if x not in cols_to_ignore]
        cleaned_sample_fields = [x for x in samp_fields if x not in cols_to_ignore]
        found_metadata_fields = {}

        for field_name, field_value in sample_dataset.iteritems():
            if field_name in cleaned_sample_fields:
                if str(field_value) in ['','nan','None'] or re.match(r'Unnamed: [0-9]+',field_name) or not sample_dataset.loc[:,field_name].notnull().values.any():
                    if self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id,
                                                                        MetadataField.name==field_name).count() != 0:
                        self.validation_failures.push('MetadataField incorrectly added %s' % field_name)
                else:
                    metadata_fields = self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id,
                                                                                                MetadataField.name==field_name,
                                                                                           ).all()
                    if len(metadata_fields) != 1:
                        self.validation_failures.push('MetadataField missing %s' % field_name)

                    found_metadata_fields[field_name] = metadata_fields[0]

        for field_name, field_value in subject_dataset.iteritems():
            if field_name in cleaned_subject_fields:
                if str(field_value) in ['','nan','None'] or re.match(r'Unnamed: [0-9]+',field_name) or not subject_dataset.loc[:,field_name].notnull().values.any():
                    if self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id,
                                                                   MetadataField.name==field_name).count() != 0:
                        self.validation_failures.push('MetadataField incorrectly added %s' % field_name)
                else:
                    metadata_fields = self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id,
                                                                                  MetadataField.name==field_name,
                                                                                  ).all()
                    if len(metadata_fields) != 1:
                        self.validation_failures.push('MetadataField missing %s' % field_name)

                    found_metadata_fields[field_name] = metadata_fields[0]

        sample_row_index = 0
        while(sample_row_index < len(sample_dataset.loc[:,'Sampling ID'])):

            subject_id = sample_dataset.loc[sample_row_index,'Subject ID']
            if self.db_session.query(Subject).filter(Subject.project_id==self.project.id,
                                                                  Subject.name==subject_id).count() == 0:
                raise ValidationError("Subject missing %s" % subject_id)

            sample_id = sample_dataset.loc[sample_row_index,'Sampling ID'].replace(",","_").strip()
            sampling_date = sample_dataset.loc[sample_row_index,'Sampling Date']
            try:
                if pd.isna(sampling_date):
                    sampling_date = None
                elif np.isnan(sampling_date):
                    sampling_date = None
            except:
                pass

            sample_matrix = sample_dataset.loc[sample_row_index,'Sample Type'].strip().lower()
            samples = self.db_session.query(Sample).join(Subject).filter(Subject.project_id==self.project.id,
                                                                            Subject.name==subject_id,
                                                                            Sample.name==sample_id,
                                                                            Sample.sample_type==SampleType.StudySample,
                                                                            Sample.assay_role==AssayRole.Assay,
                                                                            Sample.sample_matrix==sample_matrix,
                                                                            Sample.biological_tissue==Sample.get_biological_tissue(sample_matrix)
                                                                            ).all()
            if len(samples) != 1:
                raise ValidationError("Sample missing %s" % sample_id)

            sample = samples[0]

            for field_name, field_value in sample_dataset.iteritems():
                if field_name in cleaned_sample_fields:
                    if str(field_value) in ['','nan'] or re.match(r'Unnamed: [0-9]+',field_name) or not sample_dataset.loc[:,field_name].notnull().values.any():
                        if field_name in found_metadata_fields:
                            raise ValidationError("MetadataField incorrectly added %s" % field_name)
                    else:
                        metadata_field = found_metadata_fields[field_name]
                        if self.db_session.query(MetadataValue).join(Sample).filter(MetadataValue.metadata_field_id==metadata_field.id,
                                                                                   MetadataValue.sample_id==sample.id,
                                                                                   MetadataValue.raw_value==str(sample_dataset.loc[sample_row_index,field_name])
                                                                                   ).count() != 1:
                            raise ValidationError("MetadataValue missing %s %s" % (field_name,field_value))
            subject_id = sample_dataset.loc[sample_row_index,'Subject ID']
            subject_row_index = np.where(subject_dataset.loc[:,'Subject ID'] == sample_dataset.loc[sample_row_index,'Subject ID'])[0][0]

            for field_name, field_value in subject_dataset.iteritems():
                if field_name in cleaned_subject_fields:
                    if str(field_value) in ['','nan'] or re.match(r'Unnamed: [0-9]+',field_name) or not subject_dataset.loc[:,field_name].notnull().values.any():
                        if field_name in found_metadata_fields:
                            raise ValidationError("MetadataField incorrectly added %s" % field_name)
                    else:
                        metadata_field = found_metadata_fields[field_name]
                        if self.db_session.query(MetadataValue).join(Sample).filter(MetadataValue.metadata_field_id==metadata_field.id,
                                                                                    MetadataValue.sample_id==sample.id,
                                                                                    MetadataValue.raw_value==str(subject_dataset.loc[subject_row_index,field_name])
                                                                                    ).count() != 1:
                            raise ValidationError("MetadataValue missing %s %s" % (field_name,field_value))

            sample_row_index = sample_row_index + 1


class ImportDataLocations(ImportTask):

    nmr_blood_structure = ['serum',
                           'plasma']

    nmr_urine_structure = ['urine',
                           'faecal extract',
                           'faecal extract method',
                           'organic tissue extract',
                           'organic tissue']

    nmr_assay_regexes = {
        'blood': { r'0$': 'NOESY',r'1$': 'CPMG',r'2$': 'JRES',r'3$': 'DAS'},
        'urine': { r'0$': 'NOESY',r'1$': 'JRES',r'2$': 'DAS'}
    }

    """Import Run Order Class. Imports a run order file.
    :param task_options: A dictionary containing the task options
    :type task_options: dict
    """

    def __init__(self,project_name,assay_name,data_locations_path=None,assay_platform=None,sample_matrix=None,task_run_id=None,username=None,db_env=None):
        """Constructor method
        """
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env)

        self.missing_import_data = []

        self.data_locations_path = data_locations_path
        if sample_matrix:
            self.sample_matrix = sample_matrix.lower()
        else:
            self.sample_matrix = None
        self.assay_platform = assay_platform
        self.assay_name = assay_name

        if self.assay_platform == "NMR" and self.sample_matrix != None \
                and self.sample_matrix.lower() not in self.nmr_blood_structure \
                and self.sample_matrix.lower() not in self.nmr_urine_structure:
            raise Exception("Unknown NMR Sample Type: " + self.sample_matrix)

        self.args['data_locations_path'] = data_locations_path
        self.args['sample_matrix'] = sample_matrix
        self.args['assay_platform'] = assay_platform
        self.args['assay_name'] = assay_name
        self.get_class_name(self)

    def get_assay(self):

        self.assay = self.db_session.query(Assay).filter(Assay.name==self.assay_name).first()

        if self.assay is None:
            raise Exception('Assay not recognised: ' + str(self.assay_name))

    # Load the nPYC dataset
    def load_dataset(self):
        """Loads the task dataset
        """
        self.logger.info("Loading Dataset")
        path = str(Path(self.data_locations_path).absolute())
        self.logger.info("XLS Path :: "+path)

        self.data_locations = pd.read_csv(path, dtype={'Assay data name':str,
                                                       'Assay data location':str,
                                                       'Sample position':str,
                                                       'Sample batch':str,
                                                       'Assay protocol':str,
                                                       'Instrument':str,
                                                       'Sample ID':str,
                                                       'Status':str})

        self.data_locations = self.data_locations.where(pd.notnull(self.data_locations), None)

        self.logger.info("column types %s", self.data_locations.dtypes)

        if self.assay_name:
            self.get_assay()

    def get_or_add_subject(self,subject_name):
        """Get or add a new subject

        :param sample_row_index: The row number of the UnifiedCSV dataset
        :type index: int
        :return: subject object :class:`phenomedb.models.subject`
        :rtype: class:`phenomedb.models.subject`
        """

        self.logger.info("type of subject %s is %s", subject_name, type(subject_name))
        subject = self.db_session.query(Subject).filter(Subject.name==subject_name).filter(Subject.project_id==self.project.id).first()

        if subject is None:
            subject = Subject( name=subject_name,
                               project_id=self.project.id)
            self.db_session.add(subject)
            self.db_session.flush()

        return subject


    def get_or_add_sample(self,sample_row_index):
        """Get or add Sample

        :param sample_row_index: The index of the sample file
        :type sample_row_index: int
        :return: Sample
        :rtype: `phenomedb.models.Sample`
        """        

        status_field = self.data_locations.loc[sample_row_index,'Status'].replace(" ","").lower().strip()

        # Study samples should already exist
        if status_field in [SampleType.StudySample.value.replace(" ","").lower(),
                            'sample']:

            sample = self.db_session.query(Sample).join(Subject,Project) \
                .filter(Sample.name == self.data_locations.loc[sample_row_index,'Sample ID'].strip()) \
                .filter(Sample.sample_matrix == self.sample_matrix.lower()) \
                .filter(Project.id == self.project.id).first()

            if not sample:
                missing_import_data = MissingImportData(task_run_id=self.task_run.id,
                                                        type='Sample.name',
                                                        value=self.data_locations.loc[sample_row_index,'Sample ID'],
                                                        comment='Sample ID - ' + str(self.data_locations.loc[sample_row_index,'Sample ID']) + ' and sample matrix ' + self.sample_matrix.lower() + ' missing')
                self.db_session.add(missing_import_data)
                self.db_session.flush()
                self.missing_import_data.append(missing_import_data)
                return None

        elif status_field == 'missing':

            try:
                if np.isnan(self.data_locations.loc[sample_row_index,'Sample ID']):
                    sample_id = ''
                else:
                    sample_id = self.data_locations.loc[sample_row_index,'Sample ID']
            except:
                sample_id = self.data_locations.loc[sample_row_index,'Sample ID']

            missing_import_data = MissingImportData(task_run_id=self.task_run.id,
                                                    type='Sample.name',
                                                    value=sample_id,
                                                    comment="Missing in data locations")
            self.db_session.add(missing_import_data)
            self.db_session.flush()
            self.missing_import_data.append(missing_import_data)
            return None

        elif status_field in ['longtermreference',
                              'studyreference',
                              'studypool',
                              'methodreference',
                              'proceduralblank',
                              'blank']:

            if status_field == 'longtermreference':
                sample_type = SampleType.ExternalReference

            elif status_field in ['studyreference','studypool']:
                sample_type = SampleType.StudyPool

            elif status_field == 'methodreference':
                sample_type = SampleType.MethodReference

            elif status_field in ['proceduralblank','blank']:
                sample_type = SampleType.ProceduralBlank

            subject = self.db_session.query(Subject) \
                .filter(Subject.name==sample_type.value) \
                .filter(Subject.project_id==self.project.id).first()

            if not subject:
                subject = Subject( name=sample_type.value,
                                   project_id=self.project.id)

                self.db_session.add(subject)
                self.db_session.flush()

            if self.assay_platform == "NMR":
                sample_file_name = str(self.data_locations.loc[sample_row_index,'Assay data location']) + '/' + str(self.data_locations.loc[sample_row_index,'Assay data name'])
            elif self.assay_platform == "MS":
                sample_file_name = str(self.data_locations.loc[sample_row_index,'Assay data name'])

            sample = self.db_session.query(Sample) \
                .filter(Sample.subject_id == subject.id) \
                .filter(Sample.sample_matrix == self.sample_matrix.lower()) \
                .filter(Sample.name == sample_file_name).first()

            if not sample:

                sample = Sample( name=sample_file_name,
                                                sample_type=sample_type,
                                                sample_matrix=self.sample_matrix,
                                                biological_tissue=Sample.get_biological_tissue(self.sample_matrix),
                                                subject_id=subject.id)

                self.db_session.add(sample)
                self.db_session.flush()

        else:
            raise Exception("Unrecognised sample type - " + self.data_locations.loc[sample_row_index,'Status'])

        return sample

    def task_validation(self):

        assay_regexes = { r'0$': 'NOESY',r'1$': 'CPMG',r'2$': 'JRES',r'3$': 'DAS'}

        data_locations = pd.read_csv(self.data_locations_path, dtype={'Assay data name':str,
                                                                 'Assay data location':str,
                                                                 'Sample position':str,
                                                                 'Sample batch':str,
                                                                 'Assay protocol':str,
                                                                 'Instrument':str,
                                                                 'Sample ID':str,
                                                                 'Status':str})

        data_locations = data_locations.where(pd.notnull(data_locations), None)

        sample_row_index = 0

        assays = {}
        if self.assay_platform == "NMR":
            nmr_assays = self.db_session.query(Assay).filter(Assay.name.in_(['NOESY','CPMG','JRES'])).all()
            for assay in nmr_assays:
                assays[assay.name] = assay

        while(sample_row_index < len(data_locations.loc[:,'Assay data name'])):

            status_field = data_locations.loc[sample_row_index,'Status'].replace(" ","").lower().strip()
            sample = None

            if self.assay_platform == "NMR":
                sample_file_name = str(self.data_locations.loc[sample_row_index,'Assay data location']) + '/' + str(self.data_locations.loc[sample_row_index,'Assay data name'])
                expno = str(self.data_locations.loc[sample_row_index,'Assay data name'])
            else:
                sample_file_name = str(self.data_locations.loc[sample_row_index,'Assay data name'])
                expno = False

            sample_base_name = str(data_locations.loc[sample_row_index,'Assay data location'])
            sample_id = str(data_locations.loc[sample_row_index,'Sample ID']).strip()

            if status_field in [SampleType.StudySample.value.replace(" ","").lower(),
                                'sample']:

                sample = self.db_session.query(Sample).join(Subject,Project) \
                    .filter(Sample.name == sample_id) \
                    .filter(Sample.sample_matrix == self.sample_matrix.lower()) \
                    .filter(Project.id == self.project.id).first()


            elif status_field in ['longtermreference',
                                  'studyreference',
                                  'studypool',
                                  'methodreference',
                                  'proceduralblank',
                                  'blank']:

                if status_field == 'longtermreference':
                    sample_type = SampleType.ExternalReference

                elif status_field in ['studyreference','studypool']:
                    sample_type = SampleType.StudyPool

                elif status_field == 'methodreference':
                    sample_type = SampleType.MethodReference

                elif status_field in ['proceduralblank','blank']:
                    sample_type = SampleType.ProceduralBlank

                else:
                    sample_type = None

                if sample_type:

                    subject = self.db_session.query(Subject) \
                        .filter(Subject.name==sample_type.value) \
                        .filter(Subject.project_id==self.project.id).first()

                    sample = self.db_session.query(Sample) \
                        .filter(Sample.subject_id == subject.id) \
                        .filter(Sample.sample_matrix == self.sample_matrix.lower()) \
                        .filter(Sample.name == sample_file_name).first()

            if sample is None:
                raise ValidationError('Sample is missing %s' % sample_id)

            sample_assay = None

            if self.assay_platform == 'NMR':

                is_das = False
                for regex,assay_name in assay_regexes.items():
                    if re.search(regex,sample_file_name):
                        if assay_name == "DAS" or sample_base_name.lower() == 'nan':
                            if self.db_session.query(SampleAssay) \
                                       .filter(SampleAssay.sample_id == sample.id) \
                                       .filter(SampleAssay.sample_file_name == sample_file_name) \
                                       .filter(SampleAssay.sample_base_name == sample_base_name).count() > 0:
                                raise ValidationError('SampleAssay incorrectly added %s' % sample_file_name)
                                is_das = True
                        else:
                            sample_assay = self.db_session.query(SampleAssay) \
                                .filter(SampleAssay.sample_id == sample.id) \
                                .filter(SampleAssay.assay_id == assays[assay_name].id) \
                                .filter(SampleAssay.sample_file_name == sample_file_name) \
                                .filter(SampleAssay.sample_base_name == sample_base_name).first()

                if not is_das and not sample_assay:
                    raise ValidationError("SampleAssay missing %s" % sample_file_name)

            else:
                sample_assay = self.db_session.query(SampleAssay) \
                    .filter(SampleAssay.sample_id == sample.id) \
                    .filter(SampleAssay.assay_id == self.assay.id) \
                    .filter(SampleAssay.sample_file_name == sample_file_name) \
                    .filter(SampleAssay.sample_base_name == sample_base_name).first()

            if sample_assay:
                self.check_field('SampleAssay.batch',sample_file_name,sample_assay.batch,data_locations.loc[sample_row_index,'Sample batch'])
                self.check_field('SampleAssay.position',sample_file_name,sample_assay.position,data_locations.loc[sample_row_index,'Sample position'])

                if self.assay_platform == 'NMR':
                    self.check_field('SampleAssay.instrument',sample_file_name,sample_assay.instrument,data_locations.loc[sample_row_index,'Instrument'])

            sample_row_index = sample_row_index + 1


    def get_or_add_sample_assay(self,sample_row_index,sample):
        """Get or add a SampleAssay

        :param sample_row_index: The row index of the sample Dataframe
        :type sample_row_index: int
        :param sample: The Sample of the SampleAssay
        :type sample: `phenomedb.models.Sample`
        :return: SampleAssay
        :rtype: `phenomedb.models.SampleAssay`
        """        

        # Assays are global for MS, but are not for NMR, and are different if blood or urine
        #ie *0 = NOESY, *1 = CPMG/JRES, *12 = JRES/DAS *13 = DAS

        if self.assay_platform == "NMR":
            sample_file_name = str(self.data_locations.loc[sample_row_index,'Assay data location']) + '/' + str(self.data_locations.loc[sample_row_index,'Assay data name'])
            expno = str(self.data_locations.loc[sample_row_index,'Assay data name'])
        elif self.assay_platform == "MS":
            sample_file_name = str(self.data_locations.loc[sample_row_index,'Assay data name'])
            expno = False

        sample_base_name = self.data_locations.loc[sample_row_index,'Assay data location']

        if self.assay_platform == 'NMR':
            if self.sample_matrix.lower() in self.nmr_blood_structure:
                regexes = self.nmr_assay_regexes['blood']
            elif self.sample_matrix.lower()  in self.nmr_urine_structure:
                regexes = self.nmr_assay_regexes['urine']
            else:
                raise Exception("Unknown sample type")

            for regex,assay_name in regexes.items():
                if re.search(regex,sample_file_name):
                    if assay_name == "DAS":
                        # IGNORE THESE
                        return None

                    self.assay_name = assay_name
                    self.get_assay()
                    break

        if not self.assay:
            raise Exception("Unable to identify assay")

        # SampleAssays should be imported based on sample_id, assay_id, sample_file_name, and sample_base_name
        sample_assay = self.db_session.query(SampleAssay) \
            .filter(SampleAssay.sample_id == sample.id) \
            .filter(SampleAssay.assay_id == self.assay.id) \
            .filter(SampleAssay.sample_file_name == sample_file_name) \
            .filter(SampleAssay.sample_base_name == sample_base_name).first()

        if not sample_assay:
            if self.assay_platform == 'NMR':
                if 'Sample batch' in self.data_locations.columns:
                    batch = self.data_locations.loc[sample_row_index,'Sample batch'].strip()
                else:
                    batch = None
                if 'Sample position' in self.data_locations.columns:
                    position = self.data_locations.loc[sample_row_index,'Sample position'].strip()
                else:
                    position = None
                if 'Instrument' in self.data_locations.columns:
                    instrument = self.data_locations.loc[sample_row_index,'Instrument'].strip()
                else:
                    instrument = None
            else:
                batch = None
                position = None
                instrument = None

            sample_assay = SampleAssay(
                sample_id = sample.id,
                assay_id = self.assay.id,
                sample_file_name = sample_file_name,
                sample_base_name = sample_base_name,
                instrument = instrument,
                position = position,
                batch = batch
            )
            self.db_session.add(sample_assay)
            self.db_session.flush()

            self.logger.info("SampleAssay added: " + str(sample_assay))
        else:
            self.logger.info("SampleAssay already exists: " + str(sample_assay))

        return sample_assay

    def map_and_add_dataset_data(self):
        """Map the imported nPYc dataset to the phenomeDB models and add to db.
        """
        #1. Loop over each sample and import metadata fields

        sample_row_index = 0

        while(sample_row_index < len(self.data_locations.loc[:,'Assay data name'])):

            sample = self.get_or_add_sample(sample_row_index)

            if sample:
                sample_assay = self.get_or_add_sample_assay(sample_row_index,sample)

            sample_row_index = sample_row_index + 1

class AnnotationImportTask(ImportTask):
    """The AnnotationImportTask class. Used as the base class for the major annotation import methods.

    :param project_name: The name of the project, defaults to None
    :type project_name: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """
   
    first_feature_column_index = None
    dataset = None
    feature_name_row_index = None
    unit_row_index = None
    minimum_columns = ['Sample File Name', 'Sample Base Name']
    sample_id_column = None
    sample_type_column = None
    assay_role_column = None
    sample_matrix = None
    version = None
    feature_metadata = None

    def __init__(self,project_name=None,task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,validate=True,pipeline_run_id=None):
        
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

    def process(self):
        """The annotation import process method
        """        

        if self.project_name:
            self.get_or_add_project(self.project_name)
        if self.assay_name:
            self.get_or_add_assay(self.assay_name)
        if self.annotation_method_name:
            self.get_or_add_annotation_method(self.annotation_method_name)
        if self.project and self.assay and self.sample_matrix and self.annotation_method:
            self.create_saved_query()
        self.load_dataset()
        self.map_and_add_dataset_data()

    def create_saved_query(self):
        """Create a SavedQuery for the dataset for downstream analysis
        """

        query_name = "%s %s %s %s" % (self.project.name,self.sample_matrix,self.assay.name,self.annotation_method.name)

        saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.name==query_name).first()

        if saved_query:
            self.query_factory = QueryFactory(saved_query_id=saved_query.id,db_env=self.db_env)
            self.saved_query = saved_query
            self.logger.info("SavedQuery for import found %s" % self.saved_query)

        else:

            self.query_factory = QueryFactory(query_name=query_name,query_description=query_name,db_env=self.db_env)
            self.query_factory.add_filter(query_filter=QueryFilter(model="Project",property="name",operator='eq',value=self.project.name))
            self.query_factory.add_filter(query_filter=QueryFilter(model="Sample", property="sample_matrix", operator='eq', value=self.sample_matrix))
            self.query_factory.add_filter(query_filter=QueryFilter(model="Assay", property="name", operator='eq', value=self.assay.name))
            self.query_factory.add_filter(query_filter=QueryFilter(model="AnnotationMethod", property="name", operator='eq', value=self.annotation_method.name))

            self.saved_query = self.query_factory.save_query()
            self.logger.info("SavedQuery for import created %s" % self.saved_query)


    def check_sample_columns(self, dataset):
        """Check the sample columns in the dataset

        :param dataset: The imported dataset/CSV file
        :type dataset: :class:`pandas.DataFrame`
        :raises Exception: No Sample ID or Sample ID column
        :raises Exception: Minimum column missing
        """

        if 'Sampling ID' in dataset.columns:
            self.sample_id_column = 'Sampling ID'
        elif 'Sample ID' in dataset.columns:
            self.sample_id_column = 'Sample ID'
        else:
            raise Exception("No Sample ID or Sampling ID column %s" % (dataset.columns))

        if 'SampleType' in dataset.columns:
            self.sample_type_column = "SampleType"
        elif 'Sample Type' in dataset.columns:
            self.sample_type_column = "Sample Type"
        else:
            self.sample_type_column = None
            #raise Exception("No SampleType or Sample Type column %s" % (dataset.columns))

        if 'AssayRole' in dataset.columns:
            self.assay_role_column = 'AssayRole'
        elif 'Assay Role' in dataset.columns:
            self.assay_role_column = 'Assay Role'

        for colname in self.minimum_columns:
            if colname not in dataset.columns:
                raise Exception("%s missing from columns %s" % (colname, dataset.columns))

    def get_or_add_annotation_not_unified(self,feature_row_index):
        """Get or add an annotation from a 3-file dataset

        :param feature_row_index: The feature metadata row index
        :type feature_row_index: int
        :return: A corresponding :class:`phenomedb.models.Annotation` object
        :rtype: :class:`phenomedb.models.Annotation`
        """

        feature_row = self.feature_metadata.iloc[feature_row_index, :]
        feature_row = feature_row.where(pd.notnull(feature_row), None)
        cpd_name = feature_row['cpdName'].strip()
        cpd_id = None
        if 'Feature Name' in feature_row:
            cpd_id = feature_row['Feature Name'].strip().replace('.1', '').replace('.2', '').replace('.3','').replace('.4', '')
        return self.get_or_add_annotation(cpd_name,cpd_id)

    def get_or_add_annotation_unified(self,feature_column_index):
        """Get or add an annotation from a combined CSV file

        :param feature_column_index: The feature column index
        :type feature_column_index: int
        :return: A corresponding :class:`phenomedb.models.Annotation` object
        :rtype: :class:`phenomedb.models.Annotation`
        """

        cpd_name = self.dataset.iloc[self.feature_name_row_index, feature_column_index].strip()
        return self.get_or_add_annotation(cpd_name)

    def get_or_add_annotation(self,cpd_name,cpd_id=None):
        """_summary_

        :param cpd_name: The cpd_name to add
        :type cpd_name: str
        :param cpd_id: The cpd_id to import, defaults to None
        :type cpd_id: str, optional
        :return: A corresponding :class:`phenomedb.models.Annotation` object
        :rtype: :class:`phenomedb.models.Annotation`
        """
        #Get or add annotation
        #    1. Try and find an existing Annotation with following matches:
        #        Annotation.cpd_name, Annotation.cpd_id, Annotation.version
        #        HarmonisedAnnotation.assay_id, HarmonisedAnnotation.annotation_method_id.

        #    2. If that doesn't exist, try again with the "_1" syntax.

        #    3. If that exists, use that annotation/harmonised_annotation.

        #    4. If that doesn't exist, create the Annotation + HarmonisedAnnotation using the cpd_name.


        annotation = self.db_session.query(Annotation) \
            .filter(func.lower(func.replace(Annotation.cpd_name," ","")) == func.lower(func.replace(cpd_name," ",""))) \
            .filter(Annotation.version == self.version) \
            .filter(Annotation.annotation_method_id == self.annotation_method.id) \
            .filter(Annotation.assay_id == self.assay.id).first()

        if not annotation:
            annotation = self.db_session.query(Annotation) \
                .filter(func.lower(func.replace(Annotation.cpd_name," ","")) == func.lower(func.replace(cpd_name + "_1"," ",""))) \
                .filter(Annotation.version == self.version) \
                .filter(Annotation.annotation_method_id == self.annotation_method.id) \
                .filter(Annotation.assay_id == self.assay.id).first()

        if not annotation:
            # Try and find a matching harmonised_annotation
            harmonised_annotation = self.db_session.query(HarmonisedAnnotation) \
                .filter(HarmonisedAnnotation.annotation_method_id == self.annotation_method.id) \
                .filter(func.lower(func.replace(HarmonisedAnnotation.cpd_name," ","")) == func.lower(func.replace(cpd_name," ",""))) \
                .filter(HarmonisedAnnotation.assay_id == self.assay.id).first()

            if not harmonised_annotation:
                harmonised_annotation = self.db_session.query(HarmonisedAnnotation) \
                    .filter(HarmonisedAnnotation.annotation_method_id == self.annotation_method.id) \
                    .filter(HarmonisedAnnotation.assay_id == self.assay.id) \
                    .filter(func.lower(func.replace(HarmonisedAnnotation.cpd_name," ","")) == func.lower(func.replace(cpd_name + "_1"," ",""))).first()

            if harmonised_annotation:
                harmonised_annotation_id = harmonised_annotation.id
                self.logger.info('found HarmonisedAnnotation %s' % harmonised_annotation)
            else:
                harmonised_annotation_id = None
                self.logger.info('not found HarmonisedAnnotation %s' % cpd_name)

            # add the annotation_compound (without a corresponding compound)
            annotation = Annotation(cpd_name=cpd_name,
                                    harmonised_annotation_id=harmonised_annotation_id,
                                    cpd_id=cpd_id,
                                    version=self.version,
                                    assay_id=self.assay.id,
                                    annotation_method_id=self.annotation_method.id)
            self.db_session.add(annotation)

            self.db_session.flush()
            self.logger.info('added Annotation %s' % annotation)
        else:
            self.logger.info('found Annotation %s' % annotation)

        self.annotations[cpd_name] = annotation
        return annotation

    @abstractmethod
    def add_or_update_feature_metadata(self):
        pass

    def get_or_add_feature_metadata_unified(self):
        """Gets or adds the :class:`phenomedb.models.FeatureMetadata` (where cpd_name == Feature Name)
        """

        self.feature_metadatas = {}
        self.annotations = {}

        self.get_or_add_feature_dataset_unified()

        feature_column_index = self.first_feature_column_index
        while(feature_column_index < len(self.dataset.iloc[0,:])):

            annotation = self.get_or_add_annotation_unified(feature_column_index)

            self.add_or_update_feature_metadata(annotation.id,feature_column_index)

            feature_column_index = feature_column_index + 1

    def get_or_add_feature_dataset_unified(self):
        """Get or add a :class:`phenomedb.models.FeatureDataset`
        """

        dataset_name = FeatureDataset.get_dataset_name(self.project.name,self.assay.name,self.sample_matrix)
        self.feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.name==dataset_name).first()
        feature_extraction_params = {'type': '%s %s' % (self.annotation_method_name, self.version)}

        if not self.feature_dataset:

            self.feature_dataset = FeatureDataset(unified_csv_filename=self.unified_csv_path,
                                                  name=dataset_name,
                                                  filetype=FeatureDataset.Type.unified_csv,
                                                  feature_extraction_params=feature_extraction_params,
                                                  sample_matrix=self.sample_matrix,
                                                  project_id=self.project.id,
                                                  assay_id=self.assay.id,
                                                  saved_query_id=self.saved_query.id
                                                  #annotation_extraction_params=feature_extraction_params
                                                )
            self.db_session.add(self.feature_dataset)
            self.logger.info("Added %s" % self.feature_dataset)

        else:
            self.feature_dataset.unified_csv_filename = self.unified_csv_path
            self.feature_dataset.filetype = FeatureDataset.Type.unified_csv
            self.feature_dataset.feature_extraction_params = feature_extraction_params
            self.feature_dataset.sample_matrix = self.sample_matrix
            self.feature_dataset.project_id = self.project.id
            self.feature_dataset.assay_id = self.assay.id
            self.feature_dataset.saved_query_id = self.saved_query.id

            self.logger.info("Updated %s" % self.feature_dataset)

        self.db_session.flush()


    def add_or_update_annotated_feature_unified(self,sample_assay,sample_row_index,feature_index):
        """Add a annotated_feature

        :param sample_assay: The sample_assay of the annotation
        :type sample_assay: :class:`phenomedb.models.SampleAssay`
        :param feature_metadata_row: The row the feature_metadata
        :type feature_metadata_row: dict
        :param intensity: The intensity value
        :type intensity: float
        """

        feature_name = self.dataset.iloc[self.feature_name_row_index,feature_index].strip()
        feature_metadata = self.feature_metadatas[feature_name]
        annotated_feature = self.get_annotated_feature(feature_metadata.id,sample_assay.id)
        if self.unit_row_index:
            unit_text = self.dataset.iloc[self.unit_row_index,feature_index]
        else:
            unit_text = 'mg/dL'
        unit = self.get_or_add_unit(unit_text)
        above_uloq = False
        below_lloq = False
        # Try casting the value to a float, if it doesn't work, its <LLOQ or >ULOQ
        try:
            intensity = float(self.dataset.iloc[sample_row_index,feature_index])
            comment = None
        except:
            intensity = None
            comment = str(self.dataset.iloc[sample_row_index,feature_index])
            if comment == '<LLOQ':
                below_lloq = True
            if comment == '>ULOQ':
                above_uloq = True

        if annotated_feature is None:
            annotated_feature = AnnotatedFeature( feature_metadata_id = feature_metadata.id,
                                                sample_assay_id = sample_assay.id,
                                                unit_id = unit.id,
                                                intensity=intensity,
                                                comment = comment,
                                                below_lloq = below_lloq,
                                                above_uloq = above_uloq)

            #self.db_session.add(annotated_feature)
            #self.db_session.flush()
            self.logger.debug('Added: %s' % annotated_feature)
        else:
            annotated_feature.feature_metadata_id = feature_metadata.id
            annotated_feature.sample_assay_id = sample_assay.id
            annotated_feature.unit_id = unit.id
            annotated_feature.intensity=intensity
            annotated_feature.comment = comment
            annotated_feature.below_lloq = below_lloq
            annotated_feature.above_uloq = above_uloq
            #self.db_session.flush()
            self.logger.debug('Updated: %s' % annotated_feature)

        return annotated_feature

    def add_or_update_sample_assay(self,sample,sample_row_index,dataset):
        """Get or add a new sample_assay

        :param sample: The sample of the sample_assay
        :type sample: :class:`phenomedb.models.Sample`
        :param sample_row_index: The dataset row index of the sample
        :type sample_row_index: int
        :param sample_row_index: The dataset
        :type sample_row_index: :class:`pd.DataFrame`
        :return: sample_assay object :class:`phenomedb.models.sample_assay`
        :rtype: class:`phenomedb.models.SampleAssay`
        """

        sample_assay = None
        sample_file_name = None
        sample_base_name = None
        acquired_time = None
        run_order = None
        batch = None
        correction_batch = None
        dilution = None
        exclusion_details = None
        instrument = None
        expno = None
        detector_voltage = None

        #dataset = dataset.where(pd.notnull(dataset),None)

        if 'Sample File Name' in dataset.columns and dataset.loc[sample_row_index, 'Sample File Name']:
            sample_file_name = dataset.loc[sample_row_index, 'Sample File Name']
        if 'Sample Base Name' in dataset.columns:
            sample_base_name = dataset.loc[sample_row_index, 'Sample Base Name']
        if 'Acquired Time' in dataset.columns:
            acquired_time = utils.get_date(dataset.loc[sample_row_index, 'Acquired Time'])
        if 'Run Order' in dataset.columns and dataset.loc[sample_row_index, 'Run Order']:
            run_order = int(float(dataset.loc[sample_row_index, 'Run Order']))
        if 'Dilution' in dataset.columns and dataset.loc[sample_row_index, 'Dilution']:# and str(dataset.loc[sample_row_index, 'Dilution']).lower != 'nan':
            dilution = float(dataset.loc[sample_row_index, 'Dilution'])
        if 'Batch' in dataset.columns:# and str(dataset.loc[sample_row_index, 'Batch']).lower != 'nan':
            batch = dataset.loc[sample_row_index, 'Batch']
        if 'Correction Batch' in dataset.columns:# and str(dataset.loc[sample_row_index, 'Correction Bath']).lower != 'nan':
            correction_batch = dataset.loc[sample_row_index, 'Correction Batch']
        if 'Exclusion Details' in dataset.columns:# and str(dataset.loc[sample_row_index, 'Exclusion Details']).lower != 'nan':
            exclusion_details = dataset.loc[sample_row_index, 'Exclusion Details']
        if 'expno' in dataset.columns:
            expno = dataset.loc[sample_row_index, 'expno']
            if isinstance(expno,str):
                expno = expno.strip()
        if 'Instrument' in dataset.columns:
            instrument = dataset.loc[sample_row_index, 'Instrument']
            if isinstance(instrument,str):
                instrument = instrument.strip()
        if 'Detector Voltage' in dataset.columns:
            detector_voltage = dataset.loc[sample_row_index, 'Detector Voltage']

        if self.assay.platform.name == "NMR" and sample_base_name and expno and not re.search('\w+\/[0-9]+$',sample_base_name):
            sample_file_name = '%s/%s' % (sample_base_name, expno)

        sample_assay_query = self.db_session.query(SampleAssay) \
            .filter(SampleAssay.assay_id==self.assay.id) \
            .filter(SampleAssay.sample_id==sample.id)\
            .filter(SampleAssay.sample_file_name==sample_file_name)#\
            #.filter(SampleAssay.acquired_time == acquired_time)

        count = sample_assay_query.count()
        if count == 1:
            sample_assay = sample_assay_query.first()
        elif count > 1:
            self.logger.info("Multiple SampleAssays match! select * from sample_assay where assay_id = %s and sample_id = %s and sample_file_name = '%s';" % (self.assay.id,self.sample.id,sample_file_name))

        if not sample_assay:

            sample_assay = SampleAssay(
                sample_id = sample.id,
                assay_id = self.assay.id,
                acquired_time = acquired_time,
                sample_file_name = sample_file_name,
                sample_base_name = sample_base_name,
                run_order = run_order,
                batch = batch,
                correction_batch = correction_batch,
                dilution = dilution,
                exclusion_details = exclusion_details,
                expno = expno,
                instrument = instrument,
                detector_voltage = detector_voltage,
                instrument_metadata = utils.convert_to_json_safe(dataset.loc[sample_row_index,:])
            )

            self.db_session.add(sample_assay)
            self.db_session.flush()
            self.logger.debug("SampleAssay found %s" % sample_assay)
        else:
            sample_assay.acquired_time = acquired_time
            sample_assay.sample_file_name = sample_file_name
            sample_assay.sample_base_name = sample_base_name
            sample_assay.run_order = run_order
            sample_assay.batch = batch
            sample_assay.correction_batch = correction_batch
            sample_assay.dilution = dilution
            sample_assay.expno = expno
            sample_assay.instrument = instrument
            sample_assay.detector_voltage = detector_voltage
            sample_assay.exclusion_details = exclusion_details
            sample_assay.instrument_metadata = utils.convert_to_json_safe(dataset.loc[sample_row_index,:])
            self.db_session.flush()
            self.logger.debug("SampleAssay updated %s. SampleAssay.annotated_feature_count: %s" % (sample_assay,sample_assay.getCountAnnotatedFeatures()))

        return sample_assay



class ImportBrukerIVDRAnnotations(AnnotationImportTask):
    """Import Bruker IVDr Annotations

    :param annotation_method: name of the annotation method, BI-QUANT or BI-LISA
    :type annotation_method: str, required
    :param unified_csv_path: the path to the unified csv file
    :type unified_csv_path: str, required
    :param sample_matrix: the sample matrix, ie plasma, urine, serum, etc
    :type sample_matrix: str, required
    :param project_name: The name of the project, defaults to None
    :type project_name: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    
        """        

    assay_name = 'NOESY'
    already_mapped_fields = ['Sample File Name','Sample Base Name','expno','Path','Acquired Time','Run Order','Correction Batch','Exclusion Details','Batch','Metadata Available','Assay data name','Assay data location','Sample position','Sample batch','Assay protocol','Instrument','Acquisition','batch','Sampling ID','Sample ID','Status','AssayRole','SampleType','Dilution']
    units = {}
    minimum_columns = []

    def __init__(self,project_name=None,annotation_method=None,version=None,is_latest=True,unified_csv_path=None,pipeline_run_id=None,
                 sample_matrix=None,task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,validate=True):
        
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

        if version:
            self.version = str(version)
        else:
            self.version = version
        self.is_latest = is_latest
        self.unified_csv_path = unified_csv_path
        self.annotation_method_name = annotation_method
        if sample_matrix:
            self.sample_matrix = sample_matrix.lower()

        self.args['unified_csv_path'] = unified_csv_path
        self.args['annotation_method'] = annotation_method
        self.args['sample_matrix'] = sample_matrix
        self.get_class_name(self)


    def add_or_update_feature_metadata(self,annotation_id,feature_column_index):
        """Get FeatureMetadata (column) based on FeatureDataset.id and the Feature Name

        :param feature_column_index: The column index from the feature file
        :type feature_column_index: int
        :return: Annotation
        :rtype: `phenomedb.models.Annotation`
        """


        feature_column = self.dataset.iloc[:,feature_column_index].where(pd.notnull(self.dataset.iloc[:,feature_column_index]),None)

        feature_name = feature_column[self.feature_name_row_index]

        if self.lod_row_index:
            lod = feature_column[self.lod_row_index]
        else:
            lod = None

        if self.uloq_row_index:
            uloq = feature_column[self.uloq_row_index]
        else:
            uloq = None

        if self.lloq_row_index:
            lloq = feature_column[self.lloq_row_index]
        else:
            lloq = None

        if self.low_ref_percentile_row_index:
            lower_reference_percentile = feature_column[self.low_ref_percentile_row_index]
            if lower_reference_percentile == '-':
                lower_reference_percentile = None
        else:
            lower_reference_percentile = None

        if self.upper_ref_percentile_row_index:
            upper_reference_percentile = feature_column[self.upper_ref_percentile_row_index]
            if upper_reference_percentile == '-':
                upper_reference_percentile = None
        else:
            upper_reference_percentile = None

        if self.low_ref_value_row_index:
            lower_reference_value = feature_column[self.low_ref_value_row_index]
            if lower_reference_value == '-':
                lower_reference_value = None
        else:
            lower_reference_value = None

        if self.upper_ref_value_row_index:
            upper_reference_value = feature_column[self.upper_ref_value_row_index]
            if upper_reference_value == '-':
                upper_reference_value = None
        else:
            upper_reference_value = None

        if(self.calibration_method_row_index):
            calibration_method = get_npyc_enum_from_value(feature_column[self.calibration_method_row_index])
        else:
            #TODO! Change this to 'unknown' when possible
            calibration_method = CalibrationMethod.otherCalibration

        if(self.quantification_type_row_index):
            quantification_type = get_npyc_enum_from_value(feature_column[self.quantification_type_row_index])
        else:
            #TODO! Change this to 'unknown' when possible
            quantification_type = QuantificationType.QuantOther

        feature_metadata = self.db_session.query(FeatureMetadata) \
                                        .filter(FeatureMetadata.feature_name==feature_name,
                                                FeatureMetadata.feature_dataset_id==self.feature_dataset.id,
                                        ).first()

        if not feature_metadata:

            feature_metadata = FeatureMetadata(feature_dataset_id=self.feature_dataset.id,
                                               feature_name=feature_name,
                                                lloq=lloq,
                                                uloq=uloq,
                                                lod=lod,
                                                lower_reference_percentile=lower_reference_percentile,
                                                upper_reference_percentile=upper_reference_percentile,
                                                lower_reference_value=lower_reference_value,
                                                upper_reference_value=upper_reference_value,
                                                calibration_method=calibration_method,
                                                quantification_type=quantification_type,
                                                annotation_id=annotation_id,
                                    )
            self.db_session.add(feature_metadata)

        else:
            feature_metadata.lloq = lloq
            feature_metadata.uloq = uloq
            feature_metadata.lod = lod
            feature_metadata.lower_reference_percentile = lower_reference_percentile
            feature_metadata.upper_reference_percentile = upper_reference_percentile
            feature_metadata.lower_reference_value = lower_reference_value
            feature_metadata.upper_reference_value = upper_reference_value
            feature_metadata.calibration_method = calibration_method
            feature_metadata.quantification_type = quantification_type
            feature_metadata.annotation_id = annotation_id
        
        self.db_session.flush()

        self.feature_metadatas[feature_name] = feature_metadata

        return feature_metadata

    # Load the nPYC dataset
    def load_dataset(self):
        """Loads the task dataset
        """
        self.dataset = self.load_tabular_file(str(Path(self.unified_csv_path).absolute()),
                                              na_values=None,
                                              dtype={'Sample File Name':str,'Sample Base Name':str,'expno':str,'Path':str,'Acquired Time':str,'Run Order':object,'Correction Batch':str,'Exclusion Details':str,'Batch':str,'Metadata Available':str,'Assay data name':str,'Assay data location':str,'Sample position':str,'Sample batch':str,'Assay protocol':str,'Instrument':str,'Acquisition':str,'batch':str,'Sampling ID':str,'Sample ID':str,'Status':str,'AssayRole':str,'SampleType':str,'Dilution':str})
       # self.dataset = pd.read_csv(str(Path(self.unified_csv_path).absolute()),dtype={'Sample File Name':str,'Sample Base Name':str,'expno':int,'Path':str,'Acquired Time':str,'Run Order':object,'Correction Batch':str,'Exclusion Details':str,'Batch':str,'Metadata Available':str,'Assay data name':str,'Assay data location':str,'Sample position':str,'Sample batch':str,'Assay protocol':str,'Instrument':str,'Acquisition':str,'batch':str,'Sampling ID':str,'Sample ID':str,'Status':str,'AssayRole':str,'SampleType':str,'Dilution':str})

        self.check_sample_columns(self.dataset)
        try:
            self.unit_row_index = np.where(self.dataset.iloc[:,0] == 'Unit')[0][0]
        except:
            self.unit_row_index = None

        try:
            self.feature_name_row_index = np.where(self.dataset.iloc[:,0] == 'Feature Name')[0][0]
        except:
            self.feature_name_row_index = 0

        if(len(np.where(self.dataset.iloc[:,0] == 'calibrationMethod')[0]) > 0):
            self.calibration_method_row_index = np.where(self.dataset.iloc[:,0] == 'calibrationMethod')[0][0]
        else:
            self.calibration_method_row_index = None

        if(len(np.where(self.dataset.iloc[:,0] == 'quantificationType')[0]) > 0):
            self.quantification_type_row_index = np.where(self.dataset.iloc[:,0] == 'quantificationType')[0][0]
        else:
            self.quantification_type_row_index = None

        try:
            self.lloq_row_index = np.where(self.dataset.iloc[:,0] == 'LLOQ')[0][0]
        except:
            self.lloq_row_index = None
        try:
            self.uloq_row_index = np.where(self.dataset.iloc[:,0] == 'ULOQ')[0][0]
        except:
            self.uloq_row_index = None
        try:
            self.lod_row_index = np.where(self.dataset.iloc[:,0] == 'LOD')[0][0]
        except:
            self.lod_row_index = None
        try:
            self.low_ref_percentile_row_index = np.where(self.dataset.iloc[:,0] == 'Lower Reference Percentile')[0][0]
        except:
            self.low_ref_percentile_row_index = None
        try:
            self.upper_ref_percentile_row_index = np.where(self.dataset.iloc[:,0] == 'Upper Reference Percentile')[0][0]
        except:
            self.upper_ref_percentile_row_index = None
        try:
            self.low_ref_value_row_index = np.where(self.dataset.iloc[:,0] == 'Lower Reference Value')[0][0]
        except:
            self.low_ref_value_row_index = None
        try:
            self.upper_ref_value_row_index = np.where(self.dataset.iloc[:,0] == 'Upper Reference Value')[0][0]
        except:
            self.upper_ref_value_row_index = None

        #self.cpd_name_row_index = np.where(self.dataset.iloc[:,0] == 'cpdName')[0][0]

    def get_or_add_unit(self,unit_name):
        """Gets or adds a unit to the database (by unit name)

        :param unit_name: The :class:`phenomedb.models.Unit` name
        :type unit_name: str
        :return: The :class:`phenomedb.models.Unit`
        :rtype: :class:`phenomedb.models.Unit`
        """

        if unit_name not in self.units.keys():
            unit = self.db_session.query(Unit).filter(Unit.name==unit_name).first()

            if (unit is None):

                unit = Unit(name=unit_name,
                            description="")

                self.db_session.add(unit)
                self.db_session.flush()
            self.units[unit_name] = unit
        else:
            unit = self.units[unit_name]

        return unit

    def get_or_add_metadata(self,sample,sample_row_index):
        """Add the raw metadata to the metadata_raw table

        :param sample: The sampling event of metadata_raw
        :type sample: :class:`phenomedb.models.sample`
        :param sample_row_index: The dataset row index of the sample
        :type sample_row_index: int
        """

        column_index = 0
        for field_name,field_value in self.dataset.loc[sample_row_index,:].iteritems():

            if(field_name not in self.already_mapped_fields) and column_index < self.first_feature_column_index:

                self.add_metadata_field_and_value(sample.id,field_name,field_value)

            column_index = column_index + 1

    def map_and_add_dataset_data(self):
        """Map the imported nPYc dataset to the phenomeDB models and add to db.
        """

        self.first_feature_column_index = None

        self.dataset = self.dataset.where(pd.notnull(self.dataset), None)

        # Find the first column of the first row which contains a numeric entry
        p = 0
        while(p < np.size(self.dataset.columns)):
            if(is_number(self.dataset.columns[p])):
                self.first_feature_column_index = p
                break
            p = p + 1

        sample_row_index = 0

        # Find the first row of the first column which contains a numeric entry
        i = 0
        while(i < np.size(self.dataset.iloc[:,0])):
            if(is_number(self.dataset.iloc[i,0])):
                sample_row_index = i
                break
            i = i + 1

        self.get_or_add_feature_metadata_unified()

        while(sample_row_index < len(self.dataset.iloc[:,0])):

            #if self.dataset.iloc[sample_row_index,0] == None:
            #    sample_row_index = sample_row_index + 1
            #    continue

            sample = None
            sample_assay = None
            assay_role = None
            sample_name = None

            if self.sample_id_column in self.dataset.columns and self.sample_id_column not in self.dataset.loc[sample_row_index]:
                break

#            if self.dataset.loc[sample_row_index,'Sample Base Name'] == 'PipelineTest_Urine_300K_RFT_290118':
#                bp = True

            if 'Sample Base Name' in self.dataset.columns\
                    and 'expno' in self.dataset.columns\
                    and self.dataset.loc[sample_row_index,'Sample Base Name']\
                    and self.dataset.loc[sample_row_index,'expno']\
                    and not re.search('\w+\/[0-9]+$',self.dataset.loc[sample_row_index,'Sample Base Name']):
                sample_file_name = '%s/%s' % (self.dataset.loc[sample_row_index,'Sample Base Name'].strip(),int(self.dataset.loc[sample_row_index,'expno'].strip()))
            elif 'Sample File Name' in self.dataset.columns and self.dataset.loc[sample_row_index,'Sample File Name']:
                sample_file_name = self.dataset.loc[sample_row_index,'Sample File Name'].strip()
            else:
                sample_file_name = 'Unknown'

            if self.sample_type_column and self.sample_type_column in self.dataset.columns and self.dataset.loc[sample_row_index,self.sample_type_column]:
                sample_type = utils.get_npyc_enum_from_value(self.dataset.loc[sample_row_index,self.sample_type_column])
            else:
                sample_type = SampleType.StudySample

            if sample_type == SampleType.StudySample:
                sample_name = self.dataset.loc[sample_row_index,self.sample_id_column].strip()
            else:
                sample_name = sample_file_name

            sample = self.db_session.query(Sample) \
                .join(Subject,Project) \
                .filter(Sample.name==sample_name) \
                .filter(Sample.sample_matrix==self.sample_matrix) \
                .filter(Project.id==self.project.id).first()

            if not sample and sample_type != SampleType.StudySample:
                subject_name = sample_type.value
                subject = self.db_session.query(Subject).filter(Subject.project_id==self.project.id) \
                    .filter(Subject.name==subject_name).first()

                if not subject:
                    subject = Subject(project_id=self.project.id,
                                      name=subject_name)
                    self.db_session.add(subject)
                    self.db_session.flush()
                    self.logger.info("Added Subject %s" % subject)
                else:
                    self.logger.info("Found Subject %s" % subject)

                if self.assay_role_column and self.assay_role_column in self.dataset.loc[sample_row_index]:
                    assay_role = utils.get_npyc_enum_from_value(self.dataset.loc[sample_row_index,self.assay_role_column])

                sample = Sample(name=sample_name,
                               sample_type=sample_type,
                               assay_role=assay_role,
                               subject_id=subject.id,
                               sample_matrix=self.sample_matrix)

                self.db_session.add(sample)
                self.db_session.flush()
                self.logger.info("Added Sample %s" % sample)

            if sample:

                sample_assay = self.add_or_update_sample_assay(sample,sample_row_index,self.dataset)

                #self.get_or_add_metadata(sample,sample_row_index)
                if sample_assay:
                    annotated_features = []
                    feature_column_index = self.first_feature_column_index
                    while(feature_column_index < len(self.dataset.iloc[0,:])):

                        if re.match('Unnamed',self.dataset.columns[feature_column_index]):
                            break
                        feature_name = self.dataset.iloc[self.feature_name_row_index, feature_column_index]
                        if not feature_name:
                            break
                        annotated_features.append(self.add_or_update_annotated_feature_unified(sample_assay,sample_row_index,feature_column_index))

                        feature_column_index = feature_column_index + 1

                    self.db_session.add_all(annotated_features)
                    self.db_session.flush()

                    self.logger.info("Imported SampleAssay AnnotatedFeatures %s/%s" % (sample_assay.getCountAnnotatedFeatures(),feature_column_index))

            sample_row_index = sample_row_index + 1
    def post_commit_actions(self):
        """ Triggers the post-commit pipelines
        """

        super().post_commit_actions()

    def task_validation(self):
        """Run the task validation to check number and values of imported data

        :raises ValidationError: FeatureDataset does not exist
        :raises ValidationError: FeatureDataset.saved_query_id does not exist
        :raises ValidationError: SampleAssay does not exist
        :raises ValidationError: Annotation does not exist
        :raises ValidationError: AnnotatedFeature does not exist
        :raises ValidationError: Unit does not exist
        :raises ValidationError: FeatureMetadata does not exist
        """
        dataset = pd.read_csv(self.unified_csv_path,dtype={'Sample File Name':str,'Sample Base Name':str,'expno':str,'Path':str,'Acquired Time':str,'Run Order':object,'Correction Batch':str,'Exclusion Details':str,'Batch':str,'Metadata Available':str,'Assay data name':str,'Assay data location':str,'Sample position':str,'Sample batch':str,'Assay protocol':str,'Instrument':str,'Acquisition':str,'batch':str,'Sampling ID':str,'Sample ID':str,'Status':str,'AssayRole':str,'SampleType':str,'Dilution':str})
        dataset = dataset.where(pd.notnull(dataset), None)
        unit_row_index = np.where(dataset.iloc[:,0] == 'Unit')[0][0]
        feature_name_row_index = np.where(dataset.iloc[:,0] == 'Feature Name')[0][0]

        if(len(np.where(dataset.iloc[:,0] == 'calibrationMethod')[0]) > 0):
            calibration_method_row_index = np.where(dataset.iloc[:,0] == 'calibrationMethod')[0][0]
        else:
            calibration_method_row_index = None

        if(len(np.where(dataset.iloc[:,0] == 'quantificationType')[0]) > 0):
            quantification_type_row_index = np.where(dataset.iloc[:,0] == 'quantificationType')[0][0]
        else:
            quantification_type_row_index = None

        try:
            lloq_row_index = np.where(dataset.iloc[:,0] == 'LLOQ')[0][0]
        except:
            lloq_row_index = None
        try:
            uloq_row_index = np.where(dataset.iloc[:,0] == 'ULOQ')[0][0]
        except:
            uloq_row_index = None
        try:
            lod_row_index = np.where(dataset.iloc[:,0] == 'LOD')[0][0]
        except:
            lod_row_index = None
        try:
            low_ref_percentile_row_index = np.where(dataset.iloc[:,0] == 'Lower Reference Percentile')[0][0]
        except:
            low_ref_percentile_row_index = None
        try:
            upper_ref_percentile_row_index = np.where(dataset.iloc[:,0] == 'Upper Reference Percentile')[0][0]
        except:
            upper_ref_percentile_row_index = None
        try:
            low_ref_value_row_index = np.where(dataset.iloc[:,0] == 'Lower Reference Value')[0][0]
        except:
            low_ref_value_row_index = None
        try:
            upper_ref_value_row_index = np.where(dataset.iloc[:,0] == 'Upper Reference Value')[0][0]
        except:
            upper_ref_value_row_index = None

        first_feature_column_index = None
        p = 0
        while(p < np.size(dataset.columns)):
            if(utils.is_number(dataset.columns[p])):
                first_feature_column_index = p
                break
            p = p + 1

        first_sample_row_index = 0

        i = 0
        while(i < np.size(dataset.iloc[:,0])):
            if(utils.is_number(dataset.iloc[i,0])):
                first_sample_row_index = i
                break
            i = i + 1

        dataset_name = FeatureDataset.get_dataset_name(self.project.name,self.assay.name,self.sample_matrix)
        feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.name==dataset_name).first()
        if not feature_dataset:
            raise ValidationError('FeatureDataset does not exist %s' % dataset_name)
        if not feature_dataset.saved_query_id:
            raise ValidationError('FeatureDataset.saved_query_id does not exist')

        feature_metadatas = {}
        units = {}

        feature_column_index = first_feature_column_index
        while(feature_column_index < len(dataset.iloc[0,:])):

            unit_name = dataset.iloc[unit_row_index,feature_column_index]
            if unit_name not in units.keys():
                unit = self.db_session.query(Unit).filter(Unit.name==unit_name).first()
                if not unit:
                    raise ValidationError('Unit does not exist %s' % unit)
                units[unit_name] = unit

            feature_name = dataset.iloc[feature_name_row_index,feature_column_index].strip()
            annotation = self.db_session.query(Annotation) \
                .filter(func.lower(func.replace(Annotation.cpd_name, " ", "")) == func.lower(func.replace(feature_name, " ", ""))) \
                .filter(Annotation.version == self.version) \
                .filter(Annotation.annotation_method_id == self.annotation_method.id) \
                .filter(Annotation.assay_id == self.assay.id).first()

            if not annotation:
                raise ValidationError('Annotation does not exist %s' % feature_name)

            feature_metadata = self.db_session.query(FeatureMetadata).filter(FeatureMetadata.feature_dataset_id==feature_dataset.id,
                                                                        FeatureMetadata.feature_name==feature_name,
                                                                        FeatureMetadata.annotation_id==annotation.id).first()

            if not feature_metadata:
                raise ValidationError('FeatureMetadata does not exist %s' % feature_name)
            else:
                if lod_row_index:
                    self.check_field('FeatureMetadata.lod',feature_metadata.feature_name,feature_metadata.lod,dataset.iloc[lod_row_index,feature_column_index])
                if lloq_row_index:
                    self.check_field('FeatureMetadata.lloq',feature_metadata.feature_name,feature_metadata.lloq,dataset.iloc[lloq_row_index,feature_column_index])
                if uloq_row_index:
                    self.check_field('FeatureMetadata.uloq',feature_metadata.feature_name,feature_metadata.uloq,dataset.iloc[uloq_row_index,feature_column_index])
                if low_ref_percentile_row_index:
                    self.check_field('FeatureMetadata.lower_reference_percentile',feature_metadata.feature_name,feature_metadata.lower_reference_percentile,dataset.iloc[low_ref_percentile_row_index,feature_column_index])
                if upper_ref_percentile_row_index:
                    self.check_field('FeatureMetadata.upper_reference_percentile',feature_metadata.feature_name,feature_metadata.upper_reference_percentile,dataset.iloc[upper_ref_percentile_row_index,feature_column_index])
                if low_ref_value_row_index:
                    self.check_field('FeatureMetadata.lower_reference_value',feature_metadata.feature_name,feature_metadata.lower_reference_value,dataset.iloc[low_ref_value_row_index,feature_column_index])
                if upper_ref_value_row_index:
                    self.check_field('FeatureMetadata.upper_reference_value',feature_metadata.feature_name,feature_metadata.upper_reference_value,dataset.iloc[upper_ref_value_row_index,feature_column_index])

            feature_metadatas[feature_name] = feature_metadata

            feature_column_index = feature_column_index + 1

        sample_row_index = first_sample_row_index
        while(sample_row_index < len(dataset.iloc[:,0])):

            sample_name = None
            sample_file_name = None

            if self.sample_id_column in dataset.columns and not dataset.loc[sample_row_index, self.sample_id_column]:
                break

            #sample_file_name = dataset.loc[sample_row_index,'Sample File Name']
            #if
            #sample_assay = db_session.query(SampleAssay).filter(SampleAssay.sample_file_name==sample_file_name).first()

            if self.sample_type_column in dataset.columns and not dataset.loc[sample_row_index,self.sample_type_column]:
                break

            if self.sample_type_column:
                sample_type = utils.get_npyc_enum_from_value(dataset.loc[sample_row_index,self.sample_type_column])
            else:
                sample_type = SampleType.StudySample

            if 'Sample Base Name' in dataset.columns \
                    and 'expno' in dataset.columns \
                    and dataset.loc[sample_row_index, 'Sample Base Name'] \
                    and dataset.loc[sample_row_index, 'expno'] \
                    and not re.search('\w+\/[0-9]+$', self.dataset.loc[sample_row_index, 'Sample Base Name'].strip()):
                sample_file_name = '%s/%s' % (
                dataset.loc[sample_row_index, 'Sample Base Name'], int(dataset.loc[sample_row_index, 'expno'].strip()))
            else:
                sample_file_name = dataset.loc[sample_row_index, 'Sample File Name']

            if sample_type == SampleType.StudySample:
                sample_name = dataset.loc[sample_row_index,self.sample_id_column].strip()
            else:
                sample_name = sample_file_name
                self.logger.debug("Sample File Name %s" % sample_file_name)

            if not sample_name:
                sample_row_index = sample_row_index + 1
                continue

           #if not sample_file_name and 'Sample File Name' in dataset.loc[sample_row_index,:]:
           #     sample_file_name = dataset.loc[sample_row_index,'Sample File Name']

            sample_assay = self.db_session.query(SampleAssay) \
                .join(Sample,Subject,Project) \
                .filter(Sample.name==sample_name) \
                .filter(SampleAssay.sample_file_name == sample_file_name) \
                .filter(Sample.sample_matrix==self.sample_matrix) \
                .filter(Project.id==self.project.id) \
                .filter(SampleAssay.assay_id==self.assay.id).first()

            if not sample_assay:
                raise ValidationError('SampleAssay does not exist %s %s %s' % (sample_name,self.sample_matrix,self.assay.id))
            else:
                if 'expno' in dataset.loc[sample_row_index]:
                    self.check_field('SampleAssay.expno',sample_assay,sample_assay.expno,dataset.loc[sample_row_index,'expno'])
                if 'Instrument' in dataset.loc[sample_row_index]:
                    self.check_field('SampleAssay.instrument',sample_assay,sample_assay.instrument,dataset.loc[sample_row_index,'Instrument'])
                if 'Acquired Time' in dataset.loc[sample_row_index]:
                    self.check_field('SampleAssay.acquired_time',sample_assay,sample_assay.acquired_time,utils.get_date(dataset.loc[sample_row_index,'Acquired Time']))
                if 'Run Order' in dataset.loc[sample_row_index] and dataset.loc[sample_row_index,'Run Order']:
                    self.check_field('SampleAssay.run_order',sample_assay,int(sample_assay.run_order),int(float(dataset.loc[sample_row_index,'Run Order'])))
                if 'Batch' in dataset.loc[sample_row_index]:
                    self.check_field('SampleAssay.batch',sample_assay,sample_assay.batch,dataset.loc[sample_row_index,'Batch'])
                if 'Dilution' in dataset.loc[sample_row_index] and dataset.loc[sample_row_index,'Dilution']:
                    self.check_field('SampleAssay.dilution',sample_assay,sample_assay.dilution,float(dataset.loc[sample_row_index,'Dilution']))
                if 'Exclusion Details' in dataset.loc[sample_row_index]:
                    self.check_field('SampleAssay.exclusion_details',sample_assay,sample_assay.exclusion_details,dataset.loc[sample_row_index,'Exclusion Details'])

                feature_column_index = first_feature_column_index
                while(feature_column_index < len(dataset.iloc[0,:])):
                    if re.match('Unnamed', self.dataset.columns[feature_column_index]):
                        break
                    if not dataset.iloc[feature_name_row_index,feature_column_index]:
                        break
                    feature_name = dataset.iloc[feature_name_row_index,feature_column_index].strip()
                    feature_metadata = feature_metadatas[feature_name]

                    unit_name = dataset.iloc[unit_row_index,feature_column_index]
                    unit = units[unit_name]

                    above_uloq = False
                    below_lloq = False
                    # Try casting the value to a float, if it doesn't work, its <LLOQ or >ULOQ
                    try:
                        intensity = float(dataset.iloc[sample_row_index,feature_column_index])
                        comment = None
                    except:
                        intensity = None
                        comment = str(dataset.iloc[sample_row_index,feature_column_index])
                        if comment == '<LLOQ':
                            below_lloq = True
                        if comment == '>ULOQ':
                            above_uloq = True

                    annotated_feature = self.db_session.query(AnnotatedFeature).filter(AnnotatedFeature.sample_assay_id==sample_assay.id,
                                                                                  AnnotatedFeature.feature_metadata_id==feature_metadata.id,
                                                                                  AnnotatedFeature.unit_id==unit.id,
                                                                                  AnnotatedFeature.intensity==intensity,
                                                                                  AnnotatedFeature.below_lloq==below_lloq,
                                                                                  AnnotatedFeature.above_uloq==above_uloq).first()

                    if not annotated_feature:
                        raise ValidationError('AnnotatedFeature does not exist %s %s %s' % (sample_assay.id,feature_metadata.id,intensity))

                    feature_column_index = feature_column_index + 1

            sample_row_index = sample_row_index + 1

class ImportPeakPantherAnnotations(AnnotationImportTask):
    """ImportPeakPantherAnnotations Class. Using the Basic CSV format, imports a peakPantheR Dataset, maps to phenomeDB.models, and commits to DB.

    :param feature_metadata_csv_path: The path to the feature metadata csv file, defaults to None
    :type feature_metadata_csv_path: str, optional
    :param sample_metadata_csv_path: The path to the sample metadata csv file, defaults to None
    :type sample_metadata_csv_path: str, optional
    :param intensity_data_csv_path: The path to the intensity file, defaults to None
    :type intensity_data_csv_path: str, optional
    :param ppr_annotation_parameters_csv_path: The path to the PPR annotation parameters file, defaults to None
    :type ppr_annotation_parameters_csv_path: str, optional
    :param sample_matrix: The sample_matrix being imported, defaults to None
    :type sample_matrix: str, optional
    :param assay_name: The assay name being imported, defaults to None
    :type assay_name: str, optional
    :param roi_version: The version of the ROI file used for annotations, defaults to None
    :type roi_version: str, optional
    :param batch_corrected_data_csv_path: The path to the batch corrected intensity data, defaults to None
    :type batch_corrected_data_csv_path: str, optional
    :param all_features_feature_metadata_csv_path: The path to the file containing all the searched features, defaults to None
    :type all_features_feature_metadata_csv_path: str, optional
    :param ppr_mz_csv_path: The PPR MZ csv file path, defaults to None
    :type ppr_mz_csv_path: str, optional
    :param ppr_rt_csv_path: The PPR RT csv file path, defaults to None
    :type ppr_rt_csv_path: str, optional
    :param project_name: The name of the project, defaults to None
    :type project_name: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """        

    annotation_name = 'peakPantheR'
    annotation_method_name = 'PPR'
    assay_platform = AnalyticalPlatform.MS
    #assay_platform = 'MS'
    assay_targeted = 'N'
    all_feature_metadata = None

    rt_unit_name = 'seconds'
    no_unit_name = 'noUnit'

    minimum_columns = ['Sample File Name']

    already_mapped_fields = ['Sample ID','Sample File Name', 'Run Order', 'AssayRole', 'SampleType']

    def __init__(self,project_name=None,feature_metadata_csv_path=None,
                 sample_metadata_csv_path=None,intensity_data_csv_path=None,ppr_annotation_parameters_csv_path=None,
                 sample_matrix=None,assay_name=None,roi_version=None,batch_corrected_data_csv_path=None,
                 all_features_feature_metadata_csv_path=None,ppr_mz_csv_path=None,ppr_rt_csv_path=None,is_latest=True,
                 task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,validate=True,
                 run_batch_correction=False):
        
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate)

        self.is_latest = is_latest

        self.feature_metadata_csv_path = feature_metadata_csv_path

        self.sample_metadata_csv_path = sample_metadata_csv_path

        self.intensity_data_csv_path = intensity_data_csv_path

        self.batch_corrected_data_csv_path = batch_corrected_data_csv_path

        self.ppr_annotation_parameters_csv_path = ppr_annotation_parameters_csv_path
        self.ppr_mz_csv_path = ppr_mz_csv_path
        self.ppr_rt_csv_path = ppr_rt_csv_path

        if run_batch_correction and run_batch_correction not in ['SR','LTR']:
            raise Exception("run_batch_correction must be False, SR, or LTR")

        self.run_batch_correction = run_batch_correction

        if sample_matrix:
            self.sample_matrix = sample_matrix.lower()

        if all_features_feature_metadata_csv_path:
            self.all_features_feature_metadata_csv_path = all_features_feature_metadata_csv_path
        else:
            self.all_features_feature_metadata_csv_path = None

        self.assay_name = assay_name
        if roi_version:
            self.version = str(roi_version)
        else:
            self.version = None

        self.columns_to_import = []
        self.missing_import_data = []

        self.args['is_latest'] = is_latest
        self.args['project_name'] = project_name
        self.args['feature_metadata_csv_path'] = feature_metadata_csv_path
        self.args['sample_metadata_csv_path'] = sample_metadata_csv_path
        self.args['intensity_data_csv_path'] = intensity_data_csv_path
        self.args['batch_corrected_data_csv_path'] = batch_corrected_data_csv_path
        self.args['sample_matrix'] = sample_matrix
        self.args['assay_name'] = assay_name
        self.args['roi_version'] = roi_version
        self.args['all_features_feature_metadata_csv_path'] = all_features_feature_metadata_csv_path
        self.args['ppr_annotation_parameters_csv_path'] = ppr_annotation_parameters_csv_path
        self.args['ppr_mz_csv_path'] = ppr_mz_csv_path
        self.args['ppr_rt_csv_path'] = ppr_rt_csv_path
        self.args['run_batch_correction'] = run_batch_correction

        self.get_class_name(self)

    def get_or_add_feature_dataset(self):
        """Get or add a :class:`phenomedb.models.FeatureDataset`
        """

        dataset_name = FeatureDataset.get_dataset_name(self.project.name,self.assay.name,self.sample_matrix)
        self.feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.name==dataset_name).first()

        if self.batch_corrected_data_csv_path:
            sr_correction_parameters = {'Project': self.project.name, 'Assay': self.assay.name, 'Sample Matrix': self.sample_matrix}
        else:
            sr_correction_parameters = None

        feature_extraction_params = {'type': '%s %s' % (self.annotation_method_name, self.version)}

        if not self.feature_dataset:

            self.feature_dataset = FeatureDataset(sample_metadata_filename=self.sample_metadata_csv_path,
                                                  feature_metadata_filename=self.feature_metadata_csv_path,
                                                  intensity_data_filename=self.intensity_data_csv_path,
                                                  name=dataset_name,
                                                  assay_id=self.assay.id,
                                                  project_id=self.project.id,
                                                  filetype=FeatureDataset.Type.separate_csvs,
                                                  feature_extraction_params=feature_extraction_params,
                                                  sample_matrix = self.sample_matrix,
                                                  sr_correction_parameters=sr_correction_parameters,
                                                  sr_correction_task_run_id=self.task_run.id,
                                                  saved_query_id=self.saved_query.id
                                                )
            self.db_session.add(self.feature_dataset)
            self.logger.info("Added %s" % self.feature_dataset)

        else:
            self.feature_dataset.sample_metadata_filename = self.sample_metadata_csv_path
            self.feature_dataset.feature_metadata_filename = self.feature_metadata_csv_path
            self.feature_dataset.intensity_data_csv_path = self.intensity_data_csv_path
            self.feature_dataset.filetype = FeatureDataset.Type.separate_csvs
            self.feature_dataset.feature_extraction_params = feature_extraction_params
            self.feature_dataset.sample_matrix = self.sample_matrix
            self.feature_dataset.sr_correction_parameters = sr_correction_parameters
            self.feature_dataset.saved_query_id = self.saved_query.id
            self.logger.info("Updated %s" % self.feature_dataset)

        self.db_session.flush()


    def get_or_add_unit(self):
        """Get or add :class:`phenomedb.models.Unit`
        """        

        self.rt_unit = self.db_session.query(Unit).filter(Unit.name==self.rt_unit_name).first()

        if self.rt_unit is None:
            self.rt_unit = Unit(name=self.rt_unit_name, description="")

            self.db_session.add(self.rt_unit)
            self.db_session.flush()

        self.no_unit = self.db_session.query(Unit).filter(Unit.name==self.no_unit_name).first()

        if self.no_unit is None:
            self.no_unit = Unit(name=self.no_unit_name, description="")

            self.db_session.add(self.no_unit)
            self.db_session.flush()

    def load_dataset(self):
        """Loads the PeakPanther dataset, sets the name, and the loads the sampleInfo
        """

        #"Sample File Name,AssayRole,SampleType,Run Order,Sample ID,"

        #        if self.unified_csv_path:
        #            self.dataset = pd.read_csv(str(Path(self.unified_csv_path).absolute()),dtype={'Sample File Name':str,'AssayRole':str,'Run Order':object,'Sample ID':str})

        if self.feature_metadata_csv_path:
            self.feature_metadata = self.load_tabular_file(str(Path(self.feature_metadata_csv_path).absolute()))

        if self.all_features_feature_metadata_csv_path:
            self.all_feature_metadata = self.load_tabular_file(str(Path(self.all_features_feature_metadata_csv_path).absolute()),replace_na_with_none=False)

        if self.sample_metadata_csv_path:
            dtype = {'Sample File Name': str, 'Acquired Time': object, 'Run Order': object, 'Batch': object,
                     'Sample ID': str, 'SampleType': str, 'AssayRole': str}
            self.sample_metadata = self.load_tabular_file(str(Path(self.sample_metadata_csv_path).absolute()),dtype=dtype)
            self.check_sample_columns(self.sample_metadata)
        
        if self.intensity_data_csv_path:
            self.intensity_data = self.load_tabular_file(str(Path(self.intensity_data_csv_path).absolute()),header=None)

        if self.batch_corrected_data_csv_path:
            self.batch_corrected_data = self.load_tabular_file(str(Path(self.batch_corrected_data_csv_path).absolute()),header=None)
        else:
            self.batch_corrected_data = None

        if self.ppr_annotation_parameters_csv_path:
            self.ppr_annotation_parameters = self.load_tabular_file(str(Path(self.ppr_annotation_parameters_csv_path).absolute()))
        else:
            self.ppr_annotation_parameters = None

        if self.ppr_mz_csv_path:
            self.ppr_mz = self.load_tabular_file(str(Path(self.ppr_mz_csv_path).absolute()))
        else:
            self.ppr_mz = None

        if self.ppr_rt_csv_path:
            self.ppr_rt = self.load_tabular_file(str(Path(self.ppr_rt_csv_path).absolute()))
        else:
            self.ppr_rt = None

        self.get_or_add_unit()


    def add_or_update_feature_metadata(self,annotation_id,feature_metadata_row,feature_name):
        """Get or update a :class:`phenomedb.models.FeatureMetadata` object

        :param annotation_id: The :class:`phenomedb.models.Annotation` ID
        :type annotation_id: int
        :param feature_metadata_row: The row of the feature metadata dataset
        :type feature_metadata_row: :class:`pd.Series`
        :param feature_name: The name of the feature
        :type feature_name: str
        :return: The :class:`phenomedb.models.FeatureMetadata` object
        :rtype: :class:`phenomedb.models.FeatureMetadata`
        """

        feature_metadata = self.db_session.query(FeatureMetadata) \
            .filter(FeatureMetadata.feature_name == feature_name,
                    FeatureMetadata.feature_dataset_id == self.feature_dataset.id,
                    ).first()

        ion_id = None
        rsd_filter = None
        variance_ratio_filter = None
        excluded = False
        exclusion_details = False
        correlation_to_dilution_filter = None
        blank_filter = None
        artifactual_filter = None
        rsd_sp = None
        rsd_ss_rsd_sp = None
        correlation_to_dilution = None
        blank_value = None
        rt_average = None
        rt_min = None
        rt_max = None
        mz_average = None
        mz_min = None
        mz_max = None
        final_assessment_pass = None
        quantification_type = None
        calibration_method = None
        annotation_version = self.version

        if 'Feature Name' in feature_metadata_row:
            ion_id = feature_metadata_row["Feature Name"].strip()
        if 'rsdFilter' in feature_metadata_row:
            rsd_filter = feature_metadata_row['rsdFilter']
        if 'varianceRatioFilter' in feature_metadata_row:
            variance_ratio_filter = feature_metadata_row['varianceRatioFilter']
        if 'User Excluded' in feature_metadata_row:
            excluded = feature_metadata_row['User Excluded']
        if 'Exclusion Details' in feature_metadata_row:
            exclusion_details = feature_metadata_row['Exclusion Details']
        if 'correlationToDilutionFilter' in feature_metadata_row:
            correlation_to_dilution_filter = feature_metadata_row['correlationToDilutionFilter']
        if 'blankFilter' in feature_metadata_row:
            blank_filter = feature_metadata_row['blankFilter']
        if 'artifactualFilter' in feature_metadata_row:
            artifactual_filter = feature_metadata_row['artifactualFilter']
        if 'rsdSP' in feature_metadata_row:
            rsd_sp = feature_metadata_row['rsdSP']
        if 'rsdSS/rsdSP' in feature_metadata_row:
            rsd_ss_rsd_sp = feature_metadata_row['rsdSS/rsdSP']
        if 'correlationToDilutionValue' in feature_metadata_row:
            correlation_to_dilution = feature_metadata_row['correlationToDilutionValue']
        if 'BlankValue' in feature_metadata_row:
            blank_value = feature_metadata_row['BlankValue']
        if 'm/z' in feature_metadata_row:
            mz_average = feature_metadata_row['m/z']
        if 'm/z min' in feature_metadata_row:
            mz_min = feature_metadata_row['m/z min']
        if 'm/z max' in feature_metadata_row:
            mz_max = feature_metadata_row['m/z max']
        if 'Retention Time' in feature_metadata_row:
            rt_average = feature_metadata_row['Retention Time']
        if 'Retention Time min' in feature_metadata_row:
            rt_min = feature_metadata_row['Retention Time min']
        if 'Retention Time max' in feature_metadata_row:
            rt_max = feature_metadata_row['Retention Time max']
        if 'QuantificationType' in feature_metadata_row:
            quantification_type = feature_metadata_row['Quantification Type']
        if 'CalibrationMethod' in feature_metadata_row:
            calibration_method = feature_metadata_row['Calibration Method']
        if 'Passing Selection' in feature_metadata_row:
            final_assessment_pass = feature_metadata_row['Passing Selection']

        if self.ppr_annotation_parameters_csv_path:
            try:
                annotation_parameters_index = np.where(self.ppr_annotation_parameters.loc[:,'cpdID'] == ion_id)[0][0]
                annotation_parameters = utils.convert_to_json_safe(self.clean_data_for_jsonb(self.ppr_annotation_parameters.iloc[annotation_parameters_index,:].to_dict()))
            except:
                annotation_parameters = None
        else:
            annotation_parameters = None

        if not feature_metadata:

            feature_metadata = FeatureMetadata(feature_dataset_id=self.feature_dataset.id,
                                               feature_name=feature_name,
                                               ion_id=ion_id,
                                               annotation_id=annotation_id,
                                               rsd_filter=rsd_filter,
                                               variance_ratio_filter=variance_ratio_filter,
                                               excluded=excluded,
                                               exclusion_details=exclusion_details,
                                               correlation_to_dilution_filter=correlation_to_dilution_filter,
                                               blank_filter=blank_filter,
                                               artifactual_filter=artifactual_filter,
                                               rsd_sp=rsd_sp,
                                               rt_min=rt_min,
                                               rt_max=rt_max,
                                               mz_min=mz_min,
                                               mz_max=mz_max,
                                               rsd_ss_rsd_sp=rsd_ss_rsd_sp,
                                               correlation_to_dilution=correlation_to_dilution,
                                               blank_value=blank_value,
                                               mz_average=mz_average,
                                               rt_average=rt_average,
                                               quantification_type=quantification_type,
                                               calibration_method=calibration_method,
                                               final_assessment_pass = final_assessment_pass,
                                               annotation_parameters = annotation_parameters,
                                               feature_metadata = utils.convert_to_json_safe(self.clean_data_for_jsonb(feature_metadata_row.to_dict())),
                                               annotation_version = annotation_version
                                               )
            self.db_session.add(feature_metadata)

        else:
            feature_metadata.annotation_id = annotation_id
            feature_metadata.excluded = excluded
            feature_metadata.exclusion_details = exclusion_details
            feature_metadata.rsd_filter = rsd_filter
            feature_metadata.variance_ratio_filter = variance_ratio_filter
            feature_metadata.correlation_to_dilution_filter = correlation_to_dilution_filter
            feature_metadata.blank_filter = blank_filter
            feature_metadata.artifactual_filter = artifactual_filter
            feature_metadata.rsd_sp = rsd_sp
            feature_metadata.rsd_ss_rsd_sp = rsd_ss_rsd_sp
            feature_metadata.correlation_to_dilution = correlation_to_dilution
            feature_metadata.blank_value = blank_value
            feature_metadata.mz_min = mz_min
            feature_metadata.mz_max = mz_max
            feature_metadata.mz_average = mz_average
            feature_metadata.rt_average = rt_average
            feature_metadata.rt_min = rt_min
            feature_metadata.rt_max = rt_max
            feature_metadata.ion_id = ion_id
            feature_metadata.quantification_type = quantification_type
            feature_metadata.calibration_method = calibration_method
            feature_metadata.final_assessment_pass = final_assessment_pass
            feature_metadata.annotation_parameters = annotation_parameters
            feature_metadata.feature_metadata = utils.convert_to_json_safe(self.clean_data_for_jsonb(feature_metadata_row.to_dict()))
            feature_metadata.annotation_version = annotation_version

        self.db_session.flush()
        return feature_metadata

    def get_or_add_feature_metadata(self):
        """Get or add feature metadata
        """

        self.feature_metadatas = {}
        self.annotations = {}

        self.get_or_add_feature_dataset()

        feature_row_index = 0
        while feature_row_index < self.feature_metadata.shape[0]:

            annotation = self.get_or_add_annotation_not_unified(feature_row_index)
            feature_row = self.feature_metadata.iloc[feature_row_index, :]
            feature_row = feature_row.where(pd.notnull(feature_row), None)
            feature_name = feature_row['cpdName'].strip()
            self.feature_metadatas[feature_name] = self.add_or_update_feature_metadata(annotation.id,feature_row,feature_name)
            feature_row_index = feature_row_index + 1

        #feature_row_index = 0
        #while feature_row_index < self.feature_metadata.shape[0]:

            #feature_row = self.feature_metadata.iloc[feature_row_index, :]
            #feature_row = feature_row.where(pd.notnull(feature_row), None)
            #feature_name = feature_row['cpdName'].strip()
            #annotation = self.annotations[feature_name]

            #self.feature_metadatas[feature_name] = self.add_or_update_feature_metadata(annotation.id,feature_row,feature_name)
            #feature_row_index = feature_row_index + 1

    def map_and_add_dataset_data(self):
        """Map and add the intensity/abundances/annotated_features
        """        

        # loop over the sample rows.
        # using that row index, get the corresponding intensity row
        # loop over the feature_metadata rows, using that row index, get the corresponding intensity column
        # add the intensity (intensity default, or intensity_batch_corrected if self.batch_corrected=True)

        self.get_or_add_feature_metadata()

        sample_row_index = 0
        while(sample_row_index < len(self.sample_metadata.iloc[:,0])):

            sample = None
            sample_assay = None
            subject_name = None

            if self.sample_id_column in self.sample_metadata.columns and self.sample_id_column not in self.sample_metadata.loc[sample_row_index]:
                break

            sample_type = utils.get_npyc_enum_from_value(self.sample_metadata.loc[sample_row_index,self.sample_type_column])

            assay_role = utils.get_npyc_enum_from_value(self.sample_metadata.loc[sample_row_index,self.assay_role_column])

            if sample_type == SampleType.StudySample:
                sample_name = self.sample_metadata.loc[sample_row_index, self.sample_id_column]

                if 'Subject ID' in self.sample_metadata.columns:
                    subject_name = str(self.sample_metadata.loc[sample_row_index,'Subject ID'])
                else:
                    subject_name = None

            else:
                sample_name = self.sample_metadata.loc[sample_row_index,'Sample File Name']

                subject_name = sample_type.value

            if sample_name == '1.13E+11':
                bp = True

            sample = self.db_session.query(Sample).join(Subject,Project) \
                .filter(Sample.name==sample_name) \
                .filter(Sample.assay_role==assay_role) \
                .filter(Sample.sample_type==sample_type) \
                .filter(Sample.sample_matrix==self.sample_matrix)\
                .filter(Project.id==self.project.id).first()

            if not sample and subject_name:

                subject = self.db_session.query(Subject).filter(Subject.project_id==self.project.id) \
                    .filter(Subject.name==subject_name).first()

                if not subject:
                    subject = Subject(project_id=self.project.id,
                                      name=subject_name)
                    self.db_session.add(subject)
                    self.db_session.flush()
                    self.logger.info("Added Subject %s" % subject)
                else:
                    self.logger.info("Found Subject %s" % subject)

                sample = Sample(name=sample_name,
                                               sample_type=sample_type,
                                               assay_role=assay_role,
                                               subject_id=subject.id,
                                               sample_matrix=self.sample_matrix)

                self.db_session.add(sample)
                self.db_session.flush()
                self.logger.info("Added sample %s" % sample)

                if sample_type == SampleType.StudySample:
                    metadata_fields = self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id).all()

                    for metadata_field in metadata_fields:
                        if metadata_field.name in self.sample_metadata.columns:
                            raw_value = self.sample_metadata.loc[sample_row_index,metadata_field.name]
                            if raw_value:
                                metadata_value = MetadataValue(metadata_field_id=metadata_field.id,
                                                               raw_value=raw_value)
                                self.db_session.add(metadata_value)
                                self.db_session.flush()

            elif not sample:
                self.missing_import_data.append(MissingImportData(task_run_id=self.task_run.id,
                                                                  type='Sample',
                                                                  comment="Sample Missing",
                                                                  value=sample_name + " " + self.sample_matrix))

            if sample:
                sample_assay = self.add_or_update_sample_assay(sample, sample_row_index, self.sample_metadata)

            if sample_assay:

                self.logger.info("Added or updated sample_assay: %s, adding %s features" % (sample_assay, self.feature_metadata.shape[0]))
                annotated_features = []
                harmonised_annotated_features = []
                feature_row_index = 0
                while feature_row_index < self.feature_metadata.shape[0]:
                
                    feature_name = self.feature_metadata.loc[feature_row_index, 'cpdName'].strip()

                    annotated_feature = self.add_or_update_annotated_feature_not_unified(sample_assay, sample_row_index,
                                                                                         feature_row_index,
                                                                                         feature_name)
                    annotated_features.append(annotated_feature)

                    feature_row_index = feature_row_index + 1

                self.db_session.add_all(annotated_features)
                self.db_session.flush()
                self.logger.info("Imported SampleAssay AnnotatedFeatures %s/%s %s" % (
                sample_assay.getCountAnnotatedFeatures(), feature_row_index, sample_assay))

            sample_row_index = sample_row_index + 1

        self.logger.info("All features imported!")

    def post_commit_actions(self):
        """ Triggers the post-commit pipelines
        """
        from phenomedb.pipeline_factory import PipelineFactory

        if self.run_batch_correction == "LTR" and self.batch_corrected_data_csv_path:
            try:
                post_import_ppr_pipline = PipelineFactory(pipeline_name='npc_post_import_ppr_pipeline')
                run_config = {
                            utils.clean_task_id('CreateSavedQuerySummaryStatsCache'):{
                                'saved_query_id':self.saved_query.id,
                                'db_env':self.db_env
                            },
                            utils.clean_task_id('RunNPYCBatchCorrectionReportsForExistingCorrectedFeatureDataset'):{
                                'saved_query_id':self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env':self.db_env
                            },
                            utils.clean_task_id('RunNPYCBatchCorrection'):{
                                'saved_query_id':self.saved_query.id,
                                'correction_type':'LTR',
                                'db_env':self.db_env,
                                'save_correction': True,
                            },
                            utils.clean_task_id('RunSRFeatureSummaryReport'): {
                                'report_name': 'feature summary',
                                'saved_query_id': self.saved_query.id,
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunRawSampleSummaryReport'): {
                                'report_name': 'sample summary',
                                'saved_query_id': self.saved_query.id,
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunRawCorrelationToDilutionReport'): {
                                'report_name': 'correlation to dilution',
                                'saved_query_id': self.saved_query.id,
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunRawFeatureSelectionReport'): {
                                'report_name': 'feature selection',
                                'saved_query_id': self.saved_query.id,
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunRawMultivariateReport'): {
                                'report_name': 'multivariate report',
                                'saved_query_id': self.saved_query.id,
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunRawFinalReport'): {
                                'report_name': 'final report',
                                'saved_query_id': self.saved_query.id,
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunSRFeatureSummaryReport'): {
                                'report_name': 'feature summary',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunSRSampleSummaryReport'): {
                                'report_name': 'sample summary',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunSRCorrelationToDilutionReport'): {
                                'report_name': 'correlation to dilution',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunSRFeatureSelectionReport'): {
                                'report_name': 'feature selection',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunSRMultivariateReport'): {
                                'report_name': 'multivariate report',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunSRFinalReport'): {
                                'report_name': 'final report',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'SR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunLTRFeatureSummaryReport'): {
                                'report_name': 'feature summary',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'LTR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunLTRSampleSummaryReport'): {
                                'report_name': 'sample summary',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'LTR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunLTRCorrelationToDilutionReport'): {
                                'report_name': 'correlation to dilution',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'LTR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunLTRFeatureSelectionReport'): {
                                'report_name': 'feature selection',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'LTR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunLTRMultivariateReport'): {
                                'report_name': 'multivariate report',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'LTR',
                                'db_env': self.db_env,
                            },
                            utils.clean_task_id('RunLTRFinalReport'): {
                                'report_name': 'final report',
                                'saved_query_id': self.saved_query.id,
                                'correction_type': 'LTR',
                                'db_env': self.db_env,
                            },
                }

                post_import_ppr_pipline.run_pipeline(run_config=run_config)
                task_run_urls = []
                for task_run_id,task_run in post_import_ppr_pipline.pipeline_manager.task_runs.items():
                    task_run_urls.append(task_run.get_url())
                self.logger.info("npc_post_import_ppr_pipeline %s batch correction pipeline triggered %s" % (self.run_batch_correction,
                                                                                   "\n".join(post_import_ppr_pipline.pipeline_manager.task_runs.keys())))
            except Exception as err:
                self.logger.info("npc_sr_correction_report_and_ltr_correction %s batch correction not triggered!" % self.run_batch_correction)
                self.logger.exception(err)

        elif self.run_batch_correction:
            try:
                self.batch_correction_pipeline = PipelineFactory(pipeline_name='RunNPYCBatchCorrection')
                run_config = {utils.clean_task_id('RunNPYCBatchCorrection'):{'correction_type':self.run_batch_correction,
                                                                             'saved_query_id': self.saved_query.id,
                                                                             'db_env': self.db_env}}
                self.batch_correction_pipeline.run_pipeline(run_config=run_config)
                #self.logger.info("RunNPYCBatchCorrection %s batch correction pipeline triggered %s" % (self.run_batch_correction,self.batch_correction_pipeline.pipeline_manager.task_runs[0].get_url()))
            except Exception as err:
                self.logger.info("RunNPYCBatchCorrection %s batch correction not triggered!" % self.run_batch_correction)
                self.logger.exception(err)

        super().post_commit_actions()

    def add_or_update_annotated_feature_not_unified(self,sample_assay,sample_row_index,feature_index,feature_name):
        """Add or update a :class:`phenomedb.models.AnnotatedFeature` from a 3-file format file.

        :param sample_assay: The :class:`phenomedb.models.SampleAssay` object
        :type sample_assay: :class:`phenomedb.models.SampleAssay`
        :param sample_row_index: The row of the sample metadata dataset
        :type sample_row_index: int
        :param feature_index: The row of the feature metadata dataset
        :type feature_index: int
        :param feature_name: The name of the feature
        :type feature_name: str
        :raises Exception: Feature name not found
        :return: The created/found :class:`phenomedb.models.AnnotatedFeature`
        :rtype: :class:`phenomedb.models.AnnotatedFeature`
        """

        if feature_name == 'LPC(20:2/0:0)':
            bp = True

        if feature_name in self.feature_metadatas.keys():
            feature_metadata = self.feature_metadatas[feature_name]
        elif feature_name+"_1" in self.feature_metadata.keys():
            feature_metadata = self.feature_metadatas[feature_name+"_1"]
        elif feature_name + "_2" in self.feature_metadata.keys():
            feature_metadata = self.feature_metadatas[feature_name + "_2"]
        else:
            bp = True
            raise Exception("Feature name not found, nor _1, nor _2 %s " % (feature_name))

        self.logger.debug("Found feature_metadata %s " % feature_metadata)

        annotated_feature = self.get_annotated_feature(feature_metadata.id, sample_assay.id)

        sr_corrected_intensity = None
        if self.batch_corrected_data_csv_path:
            sr_corrected_intensity, below_lloq, above_uloq, comment = utils.parse_intensity(
                self.batch_corrected_data.iloc[sample_row_index, feature_index])

        intensity, below_lloq, above_uloq, comment = utils.parse_intensity(
            self.intensity_data.iloc[sample_row_index, feature_index])

        if intensity == '833739.1990787229' and feature_name == 'CAR(12:0)':
            bp = True

        if annotated_feature is None:
            annotated_feature = AnnotatedFeature(feature_metadata_id=feature_metadata.id,
                                                 sample_assay_id=sample_assay.id,
                                                 unit_id=self.no_unit.id,
                                                 intensity=intensity,
                                                 sr_corrected_intensity=sr_corrected_intensity,
                                                 comment=comment,
                                                 below_lloq=below_lloq,
                                                 above_uloq=above_uloq)

            #self.db_session.add(annotated_feature)
            #self.db_session.flush()
            self.logger.debug('Added: %s' % annotated_feature)
        else:
            annotated_feature.feature_metadata_id = feature_metadata.id
            annotated_feature.sample_assay_id = sample_assay.id
            annotated_feature.unit_id = self.no_unit.id
            annotated_feature.intensity = intensity
            annotated_feature.comment = comment
            annotated_feature.below_lloq = below_lloq
            annotated_feature.above_uloq = above_uloq
            annotated_feature.sr_corrected_intensity = sr_corrected_intensity
            #self.db_session.flush()
            self.logger.debug('Updated: %s' % annotated_feature)

        return annotated_feature

    def task_validation(self):
        """The task validation for the import, checking the number of entries and the values match.

        :raises ValidationError: sample metadata file is not the same
        :raises ValidationError: feature metadata file is not the same
        :raises ValidationError: intensity data file is not the same 
        :raises ValidationError: FeatureMetadata does not exist
        :raises ValidationError: FeatureDataset does not exist
        :raises ValidationError: AnnotatedFeature does not exist
        :raises ValidationError: SR corrected intensity does not match expected
        :raises ValidationError: Annotation does not exist
        :raises ValidationError: Expected FeatureDataset.sr_correction_parameters does not exist
        :raises ValidationError: FeatureDataset.saved_query_id does not exist
        """

        self.logger.info("Validating...")

        harmonised_dataset = None

        if self.feature_metadata_csv_path:
            feature_metadataset = pd.read_csv(self.feature_metadata_csv_path)

        if self.all_features_feature_metadata_csv_path:
            all_feature_metadataset = pd.read_csv(self.all_features_feature_metadata_csv_path)

        if self.sample_metadata_csv_path:
            dtype = {'Sample File Name': str, 'Acquired Time': object, 'Run Order': object, 'Batch': object,
                     'Sample ID': str, 'SampleType': str, 'AssayRole': str}
            sample_metadata = pd.read_csv(self.sample_metadata_csv_path,dtype=dtype)

        if self.intensity_data_csv_path:
            intensity_data = pd.read_csv(self.intensity_data_csv_path,header=None)

        if self.batch_corrected_data_csv_path:
            batch_corrected_data = pd.read_csv(self.batch_corrected_data_csv_path,header=None)
        else:
            batch_corrected_data = None

        if self.ppr_annotation_parameters_csv_path:
            ppr_annotation_parameters = pd.read_csv(self.ppr_annotation_parameters_csv_path)
        else:
            ppr_annotation_parameters = None

        if self.ppr_mz_csv_path:
            ppr_mz = pd.read_csv(self.ppr_mz_csv_path)
        else:
            ppr_mz = None

        if self.ppr_rt_csv_path:
            ppr_rt = pd.read_csv(self.ppr_rt_csv_path)
        else:
            ppr_rt = None

        self.get_or_add_unit()
        feature_metadataset = feature_metadataset.where(pd.notnull(feature_metadataset), None)
        sample_metadata = sample_metadata.where(pd.notnull(sample_metadata), None)
        intensity_data = intensity_data.where(pd.notnull(intensity_data), None)

        if not sample_metadata.equals(self.sample_metadata):
            raise ValidationError("sample_metadata != self.sample_metadata")
        if not feature_metadataset.equals(self.feature_metadata):
            raise ValidationError("feature_metadata != self.feature_metadata")
        if not intensity_data.equals(self.intensity_data):
            raise ValidationError("intensity_data != self.intensity_data")

        dataset_name = FeatureDataset.get_dataset_name(self.project.name, self.assay.name, self.sample_matrix)
        feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.name == dataset_name).first()
        if not feature_dataset:
            raise ValidationError('FeatureDataset does not exist %s' % dataset_name)
        if not feature_dataset.saved_query_id:
            raise ValidationError('FeatureDataset.saved_query_id does not exist')
        if self.batch_corrected_data_csv_path:
            if not self.feature_dataset.sr_correction_parameters:
                raise ValidationError('Expected FeatureDataset.sr_correction_parameters does not exist')

        feature_metadatas = {}
        units = {}

        for feature_row_index, feature_row in feature_metadataset.iterrows():
            cpd_id = None
            feature_name = feature_row['cpdName'].strip()
            if 'Feature Name' in feature_row:
                cpd_id = feature_row['Feature Name'].strip().replace('.1', '').replace('.2', '').replace('.3','').replace('.4', '')

            annotation = self.get_or_add_annotation(feature_name,cpd_id)
            if not annotation:
                raise ValidationError('Annotation does not exist %s' % feature_name)
            else:

                feature_metadata = self.db_session.query(FeatureMetadata).filter(
                    FeatureMetadata.feature_dataset_id == feature_dataset.id,
                    FeatureMetadata.feature_name == feature_name,
                    FeatureMetadata.annotation_id == annotation.id).first()

                if not feature_metadata:
                    raise ValidationError('FeatureMetadata does not exist %s' % feature_name)
                else:
                    if 'rsdFilter' in feature_row:
                        self.check_field('FeatureMetadata.rsd_filter', feature_metadata.feature_name, feature_metadata.rsd_filter,feature_row['rsdFilter'])
                    if 'varianceRatioFilter' in feature_row:
                        self.check_field('FeatureMetadata.variance_ratio_filter', feature_metadata.feature_name, feature_metadata.variance_ratio_filter,feature_row['varianceRatioFilter'])
                    if 'User Excluded' in feature_row:
                        self.check_field('FeatureMetadata.excluded', feature_metadata.feature_name, feature_metadata.excluded,feature_row['User Excluded'])
                    if 'Exclusion Details' in feature_row:
                        self.check_field('FeatureMetadata.exclusion_details', feature_metadata.feature_name, feature_metadata.exclusion_details,feature_row['Exclusion Details'])
                    if 'correlationToDilutionFilter' in feature_row:
                        self.check_field('FeatureMetadata.correlation_to_dilution_filter', feature_metadata.feature_name, feature_metadata.correlation_to_dilution_filter,feature_row['correlationToDilutionFilter'])
                    if 'blankFilter' in feature_row:
                        self.check_field('FeatureMetadata.blank_filter', feature_metadata.feature_name, feature_metadata.blank_filter,feature_row['blankFilter'])
                    if 'artifactualFilter' in feature_row:
                        self.check_field('FeatureMetadata.artifactual_filter', feature_metadata.feature_name, feature_metadata.artifactual_filter,feature_row['artifactualFilter'])
                    if 'rsdSP' in feature_row:
                        self.check_field('FeatureMetadata.rsd_sp', feature_metadata.feature_name, feature_metadata.rsd_sp,feature_row['rsdSP'])
                    if 'rsdSS/rsdSP' in feature_row:
                        self.check_field('FeatureMetadata.rsd_ss_rsd_sp', feature_metadata.feature_name, feature_metadata.rsd_ss_rsd_sp,feature_row['rsdSS/rsdSP'])
                    if 'correlationToDilutionValue' in feature_row:
                        self.check_field('FeatureMetadata.correlation_to_dilution', feature_metadata.feature_name, feature_metadata.correlation_to_dilution,feature_row['correlationToDilutionValue'])
                    if 'blankValue' in feature_row:
                        self.check_field('FeatureMetadata.blank_value', feature_metadata.feature_name, feature_metadata.blank_value,feature_row['blankValue'])
                    if 'm/z' in feature_row:
                        self.check_field('FeatureMetadata.mz_average', feature_metadata.feature_name, feature_metadata.mz_average,feature_row['m/z'])
                    if 'Retention Time' in feature_row:
                        self.check_field('FeatureMetadata.rt_average', feature_metadata.feature_name, feature_metadata.rt_average,feature_row['Retention Time'])
                    if 'QuantificationType' in feature_row:
                        self.check_field('FeatureMetadata.quantification_type', feature_metadata.feature_name, feature_metadata.quantification_type,feature_row['QuantificationType'])
                    if 'CalibrationMethod' in feature_row:
                        self.check_field('FeatureMetadata.calibration_method', feature_metadata.feature_name, feature_metadata.calibration_method,feature_row['CalibrationMethod'])
                    if 'Passing Selection' in feature_row:
                        self.check_field('FeatureMetadata.final_assessment_pass', feature_metadata.feature_name, feature_metadata.final_assessment_pass,feature_row['Passing Selection'])

                feature_metadatas[feature_name] = feature_metadata

        sample_row_index = 0
        while sample_row_index < sample_metadata.shape[0]:

            sample_metadata_row = sample_metadata.iloc[sample_row_index,:]

            sample = None
            sample_assay = None
            assay_role = None
            sample_name = None
            acquired_time = None

            if self.sample_id_column in sample_metadata.columns and self.sample_id_column not in sample_metadata.loc[sample_row_index]:
                break

            sample_type = utils.get_npyc_enum_from_value(sample_metadata.loc[sample_row_index, self.sample_type_column])
            if self.assay_role_column:
                assay_role = utils.get_npyc_enum_from_value(sample_metadata.loc[sample_row_index,self.assay_role_column])

            if sample_type == SampleType.StudySample:
                sample_name = sample_metadata.loc[sample_row_index, self.sample_id_column]
            else:
                sample_name = sample_metadata.loc[sample_row_index, 'Sample File Name']

            if 'Acquired Time' in sample_metadata_row:
                acquired_time = utils.get_date(sample_metadata_row['Acquired Time'])

         #   sample_assay = self.db_session.query(SampleAssay) \
         #       .join(Sample, Subject, Project) \
         #       .filter(SampleAssay.sample_file_name == sample_metadata.loc[sample_row_index, 'Sample File Name']) \
         #       .filter(SampleAssay.acquired_time == acquired_time) \
         #       .filter(Sample.name == sample_name) \
         #       .filter(Sample.sample_matrix == self.sample_matrix) \
         #       .filter(Project.id == self.project.id) \
         #       .filter(SampleAssay.assay_id == self.assay.id).first()

            sample_assay = self.db_session.query(SampleAssay) \
                .join(Sample, Subject, Project) \
                .filter(SampleAssay.sample_file_name == sample_metadata.loc[sample_row_index, 'Sample File Name']) \
                .filter(Sample.name == sample_name) \
                .filter(Sample.sample_matrix == self.sample_matrix) \
                .filter(Project.id == self.project.id) \
                .filter(SampleAssay.assay_id == self.assay.id).first()

            if not sample_assay:
                raise ValidationError('SampleAssay does not exist %s %s %s' % (sample_name, self.sample_matrix,self.assay.id))
            else:
                try:
                    if 'Acquired Time' in sample_metadata_row and sample_assay.run_order:
                        self.check_field('SampleAssay.acquired_time', sample_assay, sample_assay.acquired_time,
                                         utils.get_date(sample_metadata_row['Acquired Time']))
                    if 'Run Order' in sample_metadata_row and sample_assay.run_order:
                        self.check_field('SampleAssay.run_order', sample_assay, int(sample_assay.run_order),
                                         int(float(sample_metadata_row['Run Order'])))
                    if 'Batch' in sample_metadata_row and sample_assay.batch:
                        self.check_field('SampleAssay.batch', sample_assay, sample_assay.batch,
                                         sample_metadata_row['Batch'])
                    if 'Dilution' in sample_metadata_row:
                        self.check_field('SampleAssay.dilution', sample_assay, sample_assay.dilution,
                                         sample_metadata_row['Dilution'])
                    if 'Exclusion details' in sample_metadata_row:
                        self.check_field('SampleAssay.exclusion_details', sample_assay, sample_assay.exclusion_details,
                                         sample_metadata_row['Exclusion Details'])
                except Exception as err:
                    bp = True

                feature_row_index = 0
                while feature_row_index < feature_metadataset.shape[0]:

                    feature_metadata_row = feature_metadataset.iloc[feature_row_index,:]
                    feature_name = feature_metadata_row['cpdName'].strip()
                    feature_metadata = feature_metadatas[feature_name]

                    intensity, below_lloq, above_uloq, comment = utils.parse_intensity(intensity_data.iloc[sample_row_index,feature_row_index])

                    annotated_feature = self.db_session.query(AnnotatedFeature).filter(
                        AnnotatedFeature.sample_assay_id == sample_assay.id,
                        AnnotatedFeature.feature_metadata_id == feature_metadata.id,
                        AnnotatedFeature.unit_id == self.no_unit.id,
                        AnnotatedFeature.intensity == intensity,
                        AnnotatedFeature.below_lloq == below_lloq,
                        AnnotatedFeature.above_uloq == above_uloq).first()

                    if not annotated_feature:
                        raise ValidationError('AnnotatedFeature does not exist %s %s %s' % (sample_assay.id,feature_metadata.feature_name, intensity))

                    else:
                        sr_corrected_intensity = None
                        if self.batch_corrected_data_csv_path:
                            sr_corrected_intensity, below_lloq, above_uloq, comment = utils.parse_intensity(
                                    batch_corrected_data.iloc[sample_row_index,feature_row_index])

                        if annotated_feature.sr_corrected_intensity != sr_corrected_intensity:
                            raise ValidationError("SR Corrected intensity does not match expected %s %s" % (annotated_feature.sr_corrected_intensity,sr_corrected_intensity))

                    feature_row_index = feature_row_index + 1

                sample_row_index = sample_row_index + 1


class ImportTargetLynxAnnotations(AnnotationImportTask):
    """TargetLynx Task Class. Imports an nPYc TargetLynx Targeted Dataset, maps to phenomeDB.models, and commits to DB.

    :param unified_csv_path: The path to the unified csv file, defaults to None.
    :type sample_manifest_path: str, optional
    :param sop: The SOP to use, defaults to None.
    :type sop: str, optional
    :param sop_version: The version of the SOP used, defaults to None.
    :type sop_version: str, optional
    :param assay_name: The name of the assay (ie LC-QQQ Bile Acids), defaults to None.
    :type assay_name: str, optional
    :param sample_matrix:  The sample matrix (ie urine, plasma), defaults to None.
    :type sample_matrix: str, optional
    :param sop_file_path: The path to the SOP file used, defaults to "".
    :type sop_file_path: str, optional
        :param project_name: The name of the project, defaults to None
    :type project_name: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """        

    assay_platform = AnalyticalPlatform.MS
    assay_targeted = 'Y'
    annotation_method_name = 'TargetLynx'
    minimum_columns = ['Sample File Name']

    def __init__(self,project_name=None,unified_csv_path=None,sop=None,sop_version=None,assay_name=None,sample_matrix=None,sop_file_path="",is_latest=True,task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,validate=True):
        
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

        self.is_latest = is_latest
        self.unified_csv_path = unified_csv_path
        self.sop = sop
        if sop_version:
            self.version = str(sop_version)
        else:
            self.version = None
        self.sop_file_path = sop_file_path
        self.assay_name = assay_name
        if sample_matrix:
            self.sample_matrix = sample_matrix.lower()

        self.args['is_latest'] = is_latest
        self.args['project_name'] = project_name
        self.args['unified_csv_path'] = unified_csv_path
        self.args['sop'] = sop
        self.args['assay_name'] = assay_name
        self.args['sop_version'] = sop_version
        self.args['sop_file_path'] = sop_file_path
        self.args['sample_matrix'] = sample_matrix
        self.get_class_name(self)

    # Load the nPYC dataset
    def load_dataset(self):
        """Loads the task datasets.
        """

        #self.dataset = pd.read_csv(str(Path(self.unified_csv_path).absolute()),
        #                           na_values=None,
        #                           dtype={'Sample File Name':str,'Acquired Time':object,'Run Order':object,'Batch':object,'Sample ID':str,'SampleType':str,'AssayRole':str})

        self.dataset = self.load_tabular_file(str(Path(self.unified_csv_path).absolute()),na_values=None,
                                              dtype={'Sample File Name':str,'Acquired Time':object,'Run Order':object,'Batch':object,'Sample ID':str,'SampleType':str,'AssayRole':str})
        self.check_sample_columns(self.dataset)
        self.unit_row_index = np.where(self.dataset.iloc[:,0] == 'Unit')[0][0]
        self.feature_name_row_index = np.where(self.dataset.iloc[:,0] == 'Feature Name')[0][0]

        if(len(np.where(self.dataset.iloc[:,0] == 'calibrationMethod')[0]) > 0):
            self.calibration_method_row_index = np.where(self.dataset.iloc[:,0] == 'calibrationMethod')[0][0]
        else:
            self.calibration_method_row_index = None

        if(len(np.where(self.dataset.iloc[:,0] == 'quantificationType')[0]) > 0):
            self.quantification_type_row_index = np.where(self.dataset.iloc[:,0] == 'quantificationType')[0][0]
        else:
            self.quantification_type_row_index = None

        self.lloq_row_index = np.where(self.dataset.iloc[:,0] == 'LLOQ')[0][0]
        self.uloq_row_index = np.where(self.dataset.iloc[:,0] == 'ULOQ')[0][0]

    def add_or_update_feature_metadata(self, annotation_id, feature_column_index):
        """Get FeatureMetadata (column) based on FeatureDataset.id and the Feature Name

        :param feature_column_index: The column index from the feature file
        :type feature_column_index: int
        :return: The `phenomedb.models.Annotation` object
        :rtype: `phenomedb.models.Annotation`
        """

        feature_column = self.dataset.iloc[:, feature_column_index].where(
            pd.notnull(self.dataset.iloc[:, feature_column_index]), None)

        feature_name = feature_column[self.feature_name_row_index].strip()

        if (self.calibration_method_row_index):
            calibration_method = get_npyc_enum_from_value(
                self.dataset.iloc[self.calibration_method_row_index, feature_column_index])
        else:
            # TODO! Change this to 'unknown' when possible
            calibration_method = CalibrationMethod.otherCalibration

        if (self.quantification_type_row_index):
            quantification_type = get_npyc_enum_from_value(
                self.dataset.iloc[self.quantification_type_row_index, feature_column_index])
        else:
            # TODO! Change this to 'unknown' when possible
            quantification_type = QuantificationType.QuantOther

        feature_metadata = self.db_session.query(FeatureMetadata) \
                    .filter(FeatureMetadata.feature_name == feature_name,
                            FeatureMetadata.feature_dataset_id == self.feature_dataset.id).first()

        if not feature_metadata:

            feature_metadata = FeatureMetadata(feature_dataset_id=self.feature_dataset.id,
                                               feature_name=feature_name,
                                               quantification_type=quantification_type,
                                               calibration_method=calibration_method,
                                               uloq=self.dataset.iloc[self.uloq_row_index, feature_column_index],
                                               lloq=self.dataset.iloc[self.lloq_row_index, feature_column_index],
                                               annotation_id=annotation_id,
                                               )
            self.db_session.add(feature_metadata)

        else:
            feature_metadata.lloq = self.dataset.iloc[self.lloq_row_index, feature_column_index]
            feature_metadata.uloq = self.dataset.iloc[self.uloq_row_index, feature_column_index]
            feature_metadata.calibration_method = calibration_method
            feature_metadata.quantification_type = quantification_type
            feature_metadata.annotation_id = annotation_id

        self.db_session.flush()

        self.feature_metadatas[feature_name] = feature_metadata

        return feature_metadata

    def map_and_add_dataset_data(self):
        """Map the imported nPYc dataset to the phenomeDB models and add to db.
        """

        # Find the first column of the first row which contains a numeric entry
        p = 0
        while(p < np.size(self.dataset.columns)):
            if(is_number(self.dataset.columns[p])):
                self.first_feature_column_index = p
                break
            p = p + 1

        sample_row_index = 0

        # Find the first row which contains a numeric entry
        i = 0
        while(i < np.size(self.dataset.iloc[:,0])):
            if(is_number(self.dataset.iloc[i,0])):
                sample_row_index = i
                break
            i = i + 1

        self.get_or_add_feature_metadata_unified()

        #1. Loop over each sample and import

        while(sample_row_index < self.dataset.shape[0]):

            sample = None
            sample_assay = None
            sample_name = None
            assay_role = None

            if self.sample_id_column in self.dataset.columns and self.sample_id_column not in self.dataset.loc[sample_row_index]:
                break

            sample_type = utils.get_npyc_enum_from_value(self.dataset.loc[sample_row_index,'SampleType'])

            if sample_type == SampleType.StudySample:
                sample_name = self.dataset.loc[sample_row_index,self.sample_id_column]
            else:
                sample_name = self.dataset.loc[sample_row_index,'Sample File Name']

            sample = self.db_session.query(Sample) \
                .join(Subject,Project) \
                .filter(Sample.name==sample_name) \
                .filter(Sample.sample_matrix==self.sample_matrix) \
                .filter(Project.id==self.project.id).first()

            if not sample and sample_type != SampleType.StudySample:

                subject_name = sample_type.value
                subject = self.db_session.query(Subject).filter(Subject.project_id==self.project.id) \
                    .filter(Subject.name==subject_name).first()

                if not subject:
                    subject = Subject(project_id=self.project.id,
                                      name=subject_name)
                    self.db_session.add(subject)
                    self.db_session.flush()
                    self.logger.info("Added Subject %s" % subject)

                if self.assay_role_column:
                    assay_role = utils.get_npyc_enum_from_value(self.dataset.loc[sample_row_index,'AssayRole'])

                sample = Sample(name=sample_name,
                                               sample_type=sample_type,
                                               assay_role=assay_role,
                                               subject_id=subject.id,
                                               sample_matrix=self.sample_matrix)

                self.db_session.add(sample)
                self.db_session.flush()
                self.logger.info("Added Sample %s" % sample)

            elif not sample and sample_type == SampleType.StudySample:
                bp = True

            if sample:

                sample_assay = self.add_or_update_sample_assay(sample,sample_row_index,self.dataset)

                #self.get_or_add_metadata(sample,sample_row_index)

                if sample_assay:
                
                    annotated_features = []    
                
                    feature_column_index = self.first_feature_column_index
                    while(feature_column_index < len(self.dataset.iloc[0,:])):
                        if re.match('Unnamed',self.dataset.columns[feature_column_index]):
                            break
                        annotated_features.append(self.add_or_update_annotated_feature_unified(sample_assay,sample_row_index,feature_column_index))

                        feature_column_index = feature_column_index + 1

                    self.db_session.add_all(annotated_features)
                    self.db_session.flush()
                    self.logger.info("Imported SampleAssay AnnotatedFeatures %s/%s %s" % (sample_assay.getCountAnnotatedFeatures(),feature_column_index,sample_assay))

            sample_row_index = sample_row_index + 1

    def task_validation(self):
        """The task validation, checks the counts and values of imported data

        :raises ValidationError: FeatureDataset does not exist
        :raises ValidationError: FeatureDataset.saved_query_id does not exist
        :raises ValidationError: SampleAssay does not exist
        :raises ValidationError: AnnotatedFeature does not exist
        :raises ValidationError: FeatureMetadata does not exist
        :raises ValidationError: Annotation does not exist
        """

        dataset = pd.read_csv(self.unified_csv_path,
                              na_values=None,
                              dtype={'Sample File Name':str,'Acquired Time':object,'Run Order':object,'Batch':object,'Sample ID':str,'SampleType':str,'AssayRole':str})

        dataset = dataset.where(pd.notnull(dataset), None)
        unit_row_index = np.where(dataset.iloc[:, 0] == 'Unit')[0][0]
        feature_name_row_index = np.where(dataset.iloc[:, 0] == 'Feature Name')[0][0]

        if (len(np.where(dataset.iloc[:, 0] == 'calibrationMethod')[0]) > 0):
            calibration_method_row_index = np.where(dataset.iloc[:, 0] == 'calibrationMethod')[0][0]
        else:
            calibration_method_row_index = None

        if (len(np.where(dataset.iloc[:, 0] == 'quantificationType')[0]) > 0):
            quantification_type_row_index = np.where(dataset.iloc[:, 0] == 'quantificationType')[0][0]
        else:
            quantification_type_row_index = None

        lloq_row_index = np.where(dataset.iloc[:, 0] == 'LLOQ')[0][0]
        uloq_row_index = np.where(dataset.iloc[:, 0] == 'ULOQ')[0][0]

        first_feature_column_index = None
        p = 0
        while (p < np.size(dataset.columns)):
            if (utils.is_number(dataset.columns[p])):
                first_feature_column_index = p
                break
            p = p + 1

        first_sample_row_index = 0

        i = 0
        while (i < np.size(dataset.iloc[:, 0])):
            if (utils.is_number(dataset.iloc[i, 0])):
                first_sample_row_index = i
                break
            i = i + 1

        dataset_name = FeatureDataset.get_dataset_name(self.project.name, self.assay.name, self.sample_matrix)
        feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.name == dataset_name).first()
        if not feature_dataset:
            raise ValidationError('FeatureDataset does not exist %s' % dataset_name)
        if not feature_dataset.saved_query_id:
            raise ValidationError('FeatureDataset.saved_query_id does not exist')

        feature_metadatas = {}
        units = {}

        feature_column_index = first_feature_column_index
        while (feature_column_index < len(dataset.iloc[0, :])):

            unit_name = dataset.iloc[unit_row_index, feature_column_index]
            if unit_name not in units.keys():
                unit = self.db_session.query(Unit).filter(Unit.name == unit_name).first()
                if not unit:
                    raise ValidationError('Unit does not exist %s' % unit)
                units[unit_name] = unit

            feature_name = dataset.iloc[feature_name_row_index, feature_column_index].strip()

            annotation = self.get_or_add_annotation(feature_name)

            if not annotation:
                raise ValidationError('Annotation does not exist %s' % annotation)

            else:
                feature_metadata = self.db_session.query(FeatureMetadata).filter(
                    FeatureMetadata.feature_dataset_id == feature_dataset.id,
                    FeatureMetadata.feature_name == feature_name,
                    FeatureMetadata.annotation_id == annotation.id).first()

                if not feature_metadata:
                    raise ValidationError('FeatureMetadata does not exist %s' % feature_metadata)
                else:
                    self.check_field('FeatureMetadata.lloq', feature_metadata.feature_name, feature_metadata.lloq,
                                     dataset.iloc[lloq_row_index, feature_column_index])
                    self.check_field('FeatureMetadata.uloq', feature_metadata.feature_name, feature_metadata.uloq,
                                     dataset.iloc[uloq_row_index, feature_column_index])

                    feature_metadatas[feature_name] = feature_metadata

            feature_column_index = feature_column_index + 1

        sample_row_index = first_sample_row_index
        while (sample_row_index < dataset.shape[0]):

            sample = None
            sample_assay = None

            if 'Sample ID' in dataset.columns and 'Sample ID' not in dataset.loc[sample_row_index]:
                break

            if 'SampleType' in dataset.loc[sample_row_index]:
                sample_type = utils.get_npyc_enum_from_value(self.dataset.loc[sample_row_index, 'SampleType'])
            else:
                sample_type = SampleType.StudySample

            if sample_type == SampleType.StudySample:
                sample_name = dataset.loc[sample_row_index, 'Sample ID']
            else:
                sample_name = dataset.loc[sample_row_index, 'Sample File Name']

            if not sample_name:
                sample_row_index = sample_row_index + 1
                continue

            sample_file_name = dataset.loc[sample_row_index,'Sample File Name']

            sample_assay = self.db_session.query(SampleAssay) \
                .join(Sample, Subject, Project) \
                .filter(Sample.name == sample_name) \
                .filter(SampleAssay.sample_file_name == sample_file_name)\
                .filter(Sample.sample_matrix == self.sample_matrix) \
                .filter(Project.id == self.project.id) \
                .filter(SampleAssay.assay_id == self.assay.id).first()

            if not sample_assay:
                raise ValidationError('SampleAssay does not exist %s %s %s' % (sample_name, self.sample_matrix,
                                                self.assay.id))
            else:

                if 'Acquired Time' in dataset.columns:
                    self.check_field('SampleAssay.acquired_time', sample_assay, sample_assay.acquired_time,
                                     utils.get_date(dataset.loc[sample_row_index, 'Acquired Time']))
                if 'Run Order' in dataset.columns:
                    self.check_field('SampleAssay.run_order', sample_assay, int(sample_assay.run_order),
                                     int(float(dataset.loc[sample_row_index, 'Run Order'])))
                if 'Batch' in dataset.columns:
                    self.check_field('SampleAssay.batch', sample_assay, sample_assay.batch,
                                     dataset.loc[sample_row_index, 'Batch'])
                if 'Correction Batch' in dataset.columns:
                    self.check_field('SampleAssay.dilution', sample_assay, sample_assay.correction_batch,
                                     dataset.loc[sample_row_index, 'Correction Batch'])
                if 'Dilution' in dataset.columns:
                    self.check_field('SampleAssay.dilution', sample_assay, sample_assay.dilution,
                                     dataset.loc[sample_row_index, 'Dilution'])
                if 'Sample File Name' in dataset.columns:
                    self.check_field('SampleAssay.sample_file_name', sample_assay, sample_assay.sample_file_name,
                                     dataset.loc[sample_row_index, 'Sample File Name'])
                if 'Sample Base Name' in dataset.columns:
                    self.check_field('SampleAssay.sample_base_name', sample_assay, sample_assay.sample_base_name,
                                     dataset.loc[sample_row_index, 'Sample Base Name'])
                if 'Exclusion Details' in dataset.columns:
                    self.check_field('SampleAssay.exclusion_details', sample_assay, sample_assay.exclusion_details,
                                     dataset.loc[sample_row_index, 'Exclusion Details'])

                feature_column_index = first_feature_column_index
                while feature_column_index < len(dataset.iloc[0, :]):
                    feature_name = dataset.iloc[feature_name_row_index, feature_column_index].strip()
                    feature_metadata = feature_metadatas[feature_name]

                    unit_name = dataset.iloc[unit_row_index, feature_column_index]
                    unit = units[unit_name]

                    above_uloq = False
                    below_lloq = False
                    # Try casting the value to a float, if it doesn't work, its <LLOQ or >ULOQ
                    try:
                        intensity = float(dataset.iloc[sample_row_index, feature_column_index])
                        comment = None
                    except:
                        intensity = None
                        comment = str(dataset.iloc[sample_row_index, feature_column_index])
                        if comment == '<LLOQ':
                            below_lloq = True
                        if comment == '>ULOQ':
                            above_uloq = True

                    annotated_feature = self.db_session.query(AnnotatedFeature).filter(
                        AnnotatedFeature.sample_assay_id == sample_assay.id,
                        AnnotatedFeature.feature_metadata_id == feature_metadata.id,
                        AnnotatedFeature.unit_id == unit.id,
                        AnnotatedFeature.intensity == intensity,
                        AnnotatedFeature.below_lloq == below_lloq,
                        AnnotatedFeature.above_uloq == above_uloq).first()

                    if not annotated_feature:
                        raise ValidationError('AnnotatedFeature does not exist %s %s %s' % sample_assay.id,
                                                        feature_metadata.id, intensity)

                    feature_column_index = feature_column_index + 1

            sample_row_index = sample_row_index + 1



class ImportXCMSFeatures(ImportTask):
    """XCMSFeatureImportTaskUnifiedCSV Class. Using the Unified CSV format, imports an XCMS Dataset, maps to phenomeDB.models, and commits to DB.

        TO DO: Finish the import code

        :param unified_csv_path: The path to the unified csv file, defaults to None.
        :type unified_csv_path: str, optional
        :param assay_name: The name of the assay (ie LC-QQQ Bile Acids), defaults to None.
        :type assay_name: str, optional
        :param sample_matrix:  The sample matrix (ie urine, plasma), defaults to None.
        :type sample_matrix: str, optional
        :param project_name: The name of the project, defaults to None
        :type project_name: str, optional
        :param task_run_id: The TaskRun ID
        :type task_run_id: float, optional
        :param username: The username of the user running the job, defaults to None
        :type username: str, optional
        :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
        :type db_env: str, optional
        :param db_session: The db_session to use
        :type db_session: object, optional
        :param execution_date: The date of execution, str format.
        :type execution_date: str, optional
        :param validate: Whether to run validation, default True
        :type validate: boolean
        :param pipeline_run_id: The Pipeline run ID
        :type pipeline_run_id: str, optional
        """

    assay_platform = AnalyticalPlatform.MS
    #assay_platform = 'MS'
    assay_targeted = 'N'

    already_mapped_fields = ['Sample File Name', 'Run Order', 'AssayRole', 'SampleType','Sample ID']

    def __init__(self,project_name=None,unified_csv_path=None,sample_matrix=None,assay_name=None,task_run_id=None,
                 username=None,db_env=None):
        
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

        self.unified_csv_path = unified_csv_path
        self.sample_matrix = sample_matrix
        self.assay_name = assay_name
        self.client_name = 'dev'
        self.feature_names = []

        self.args['project_name'] = self.project_name
        self.args['unified_csv_path'] = self.unified_csv_path
        self.args['sample_matrix'] = self.sample_matrix
        self.args['assay_name'] = self.assay_name
        self.get_class_name(self)

    def get_or_add_assay(self):
        """Gets or adds an assay to the database (by assay_name)
        """

        # Get the assay name? Where from? The config.ini ?

        self.assay = self.db_session.query(Assay).filter(Assay.platform==self.assay_platform).filter(Assay.name==self.assay_name).first()
        print("Assay :: "+self.assay.__str__())
        if(self.assay is None):

            raise Exception('Assay not recognised: ' + str(self.assay_name))


    def load_dataset(self):
        """Loads the XCMS dataset, sets the name, and the loads the sampleInfo
        """

        #Sample File Name,AssayRole,SampleType,Run Order,Sample ID
        self.dataset = pd.read_csv(str(Path(self.unified_csv_path).absolute()),dtype={'Sample File Name':str,'AssayRole':str,'SampleType':str,'Run Order':object,'Sample ID':str})

        self.feature_name_row_index = np.where(self.dataset.iloc[:,0] == 'Feature Name')[0][0]
        #self.cpdName_index = np.where(self.dataset.iloc[:,0] == 'cpdName')[0][0]
        try:
            self.rt_row_index = np.where(self.dataset.iloc[:,0] == 'Retention Time')[0][0]
            self.mz_row_index = np.where(self.dataset.iloc[:,0] == 'm/z')[0][0]
            self.rt_max_row_index = np.where(self.dataset.iloc[:,0] == 'Retention Time - Maximum')[0][0]
            self.rt_min_row_index = np.where(self.dataset.iloc[:,0] == 'Retention Time - Minimum')[0][0]
            self.mz_max_row_index = np.where(self.dataset.iloc[:,0] == 'm/z - Maximum')[0][0]
            self.mz_min_row_index = np.where(self.dataset.iloc[:,0] == 'm/z - Minimum')[0][0]
            self.exclusion_details_row_index = np.where(self.dataset.iloc[:,0] == 'Exclusion Details')[0][0]
            self.user_excluded_row_index = np.where(self.dataset.iloc[:,0] == 'User Excluded')[0][0]
        except:
            pass
        p = 0
        while(p < np.size(self.dataset.columns)):
            if(utils.is_number(self.dataset.columns[p])):
                self.first_feature_column_index = p
                break
            p = p + 1

        # Find the first row of the first column which contains a numeric entry
        i = 0
        while(i < np.size(self.dataset.iloc[:,0])):
            if(utils.is_number(self.dataset.iloc[i,0])):
                self.first_sample_row_index = i
                break
            i = i + 1

    # Map and add the dataset to phenomedb
    def map_and_add_dataset_data(self):
        """Map and add the dataset data

        :raises Exception: No Sampling ID or Sample File Name in row
        """

        # create the unique feature names
        feature_column_index = self.first_feature_column_index
        while(feature_column_index < len(self.dataset.iloc[0,:])):
            feature_name = self.dataset.iloc[self.feature_name_row_index,feature_column_index]
            if feature_name in self.feature_names:
                feature_name = feature_name + "_2"
            self.feature_names.append(feature_name)
            feature_column_index = feature_column_index + 1

        sample_row_index = self.first_sample_row_index

        while(sample_row_index < len(self.dataset.iloc[:,0])):

            sample_name = self.get_or_build_sample_name(sample_row_index)

            if sample_name:

                sample = self.db_session.query(Sample).join(Subject,Project) \
                    .filter(Sample.name==sample_name).filter(Project.id==self.project.id).first()

                if sample is None:
                    missing_import_data = MissingImportData(task_run_id=self.task_run.id,
                                                            type='Sample.name',
                                                            value=sample_name,
                                                            comment="Sample ID not found: "+ sample_name + " - row index: " + str(sample_row_index))
                    self.db_session.add(missing_import_data)
                    self.db_session.flush()
                    self.missing_import_data.append(missing_import_data)

                sample_assay = self.get_sample_assay(sample,sample_row_index)

            elif 'Sample File Name' in self.dataset.loc[sample_row_index]:

                sample_assay = self.db_session.query(SampleAssay).filter(SampleAssay.sample_file_name==self.dataset.loc[sample_row_index,'Sample File Name']).first()

            else:
                raise Exception('No Sampling ID or Sample File Name for row ' + str(sample_row_index))

            self.logger.info("Found matching sample_assay: " + str(sample_assay))
            
            if sample_assay:
                annotated_features = dict()
                feature_column_index = self.first_feature_column_index
                while(feature_column_index < len(self.dataset.iloc[0,:])):

                    feature_name_index = feature_column_index - self.first_feature_column_index
                    feature_name = self.feature_names[feature_name_index]

                    annotated_features[feature_name] = self.build_feature_dict(sample_row_index,feature_column_index)
                    feature_column_index = feature_column_index + 1

                sample_assay.annotated_features = annotated_features
                self.logger.info("Added SampleAssay features %s %s %s" % (sample_assay,len(annotated_features),annotated_features))
                self.db_session.flush()

            sample_row_index = sample_row_index + 1

    def build_feature_dict(self,sample_row_index,feature_column_index):
        """Build a dictionary of features

        :param sample_row_index: The row index of the sample metadata dataset
        :type sample_row_index: int
        :param feature_column_index: The column index of the feature metadata dataset
        :type feature_column_index: int
        :return: A dictionary of FeatureMetadata properties
        :rtype: dict
        """

        feature_name_index = feature_column_index - self.first_feature_column_index
        feature_name = self.feature_names[feature_name_index]

        feature_name_split = feature_name.split("_")
        retention_time = float(feature_name_split[0])
        mz = float(feature_name_split[1].replace('m/z',''))

        feature = { #feature_metadata_id=self.feature_metadatas[feature_name],
                    'feature_name': feature_name,
                    'mz': mz,
                    'rt': retention_time,
                    'intensity': self.dataset.iloc[sample_row_index,feature_column_index]}

        self.logger.debug("Adding new feature - se:%s feature:%s" % (feature))
        return feature

class ImportNPYC(ImportTask):
    """_summary_

        :param dataset_path: The path to the dataset folder, defaults to None.
        :type dataset_path_path: str, optional
        :param sample_metadata_path: The path to the sample_metadata file, defaults to None.
        :type sample_metadata_path: str, optional
        :param sample_metadata_format: The sample_metadata format, defaults to None.
        :type sample_metadata_format: str, optional
        :param sop: The SOP to use, defaults to None.
        :type sop: str, optional
        :param assay_name: The name of the assay (ie LC-QQQ Bile Acids), defaults to None.
        :type assay_name: str, optional
        :param sample_matrix: The sample matrix (ie urine, plasma), defaults to None.
        :type sample_matrix: str, optional
        :param sop_file_path: The path to the SOP file used, defaults to "".
        :type sop_file_path: str, optional
        :param project_name: The name of the project, defaults to None
        :type project_name: str, optional
        :param task_run_id: The TaskRun ID
        :type task_run_id: float, optional
        :param username: The username of the user running the job, defaults to None
        :type username: str, optional
        :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
        :type db_env: str, optional
        :param db_session: The db_session to use
        :type db_session: object, optional
        :param execution_date: The date of execution, str format.
        :type execution_date: str, optional
        :param validate: Whether to run validation, default True
        :type validate: boolean
        :param pipeline_run_id: The Pipeline run ID
        :type pipeline_run_id: str, optional
        """

    npyc_dataset = None
    annotations = {}
    already_mapped_fields = ['Sample File Name','Sample Base Name','expno','Path','Acquired Time','Run Order','Correction Batch','Exclusion Details','Batch','Metadata Available','Assay data name','Assay data location','Sample position','Sample batch','Assay protocol','Instrument','Acquisition','batch','Sampling ID','Sample ID','Status','AssayRole','SampleType','Dilution']

    def __init__(self,project_name=None,assay_name=None,sample_matrix=None,dataset_path=None,sop=None,sample_metadata_path=None,sample_metadata_format=None,task_run_id=None,username=None,db_env=None,db_session=None,pipeline_run_id=None,execution_date=None):
        
        super().__init__(project_name=project_name,task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,validate=validate,pipeline_run_id=pipeline_run_id)

        self.assay_name = assay_name
        self.sample_matrix = sample_matrix
        self.dataset_path = dataset_path
        self.sop = sop
        self.sample_metadata_format = sample_metadata_format
        self.sample_metadata_path = sample_metadata_path

        self.args['assay_name'] = assay_name
        self.args['sample_matrix'] = sample_matrix
        self.args['dataset_path'] = dataset_path
        self.args['sop'] = sop
        self.args['sample_metadata_format'] = sample_metadata_format
        self.args['sample_metadata_path'] = sample_metadata_path



    def map_and_add_dataset_data(self):
        """Map and add the data
        """


        # 1. Get or add project, assay
        # 2. loop over the features and add the annotations + configs ?
        # 2. loop over the sample metadata and get or set the Samples and Sample Assays
        # 3. loop over the annotated_features and add the annotated_features

        self.get_or_add_unit('noUnit',description='no units')

        for index, row in self.npyc_dataset.featureMetadata.iterrows():
            self.annotations[row['Feature Name']] = self.get_or_add_annotation(row)

        for index, row in self.npyc_dataset.sampleMetadata.iterrows():
            subject = self.get_or_add_subject(sample_row_index=index)
            sample = self.get_or_add_sample(subject,index)
            self.get_or_add_metadata(sample,index)
            sample_assay = self.get_or_add_sample_assay(sample,index)
            self.get_or_add_annotated_features(sample_assay,index)

    def get_or_add_subject(self,sample_row_index):
        """Get or add a new subject

        :param index: The row number of the sample_metadata
        :type index: int
        :return: subject object :class:`phenomedb.models.Subject`
        :rtype: class:`phenomedb.models.subject`
        """

        subject_name = self.get_or_build_subject_name(sample_row_index,self.npyc_dataset.sampleMetadata.loc[sample_row_index])

        subject = self.db_session.query(Subject).filter(Subject.name==subject_name).filter(Subject.project_id==self.project.id).first()

        if(subject is None):

            subject = Subject( name=subject_name,
                               project_id=self.project.id)

            self.db_session.add(subject)
            self.db_session.flush()
            self.logger.info("Subject added %s" % subject)

        else:
            self.logger.info("Subject found %s" % subject)

        return subject

    def get_or_add_sample(self,subject,sample_row_index):
        """Get or add a new sample

        :param subject: The subject of the sample
        :type subject: :class:`phenomedb.models.Subject`
        :param sample_row_index: The dataset row index the sample
        :type sample_row_index: int
        :return: sample object :class:`phenomedb.models.Sample`
        :rtype: class:`phenomedb.models.Sample`
        """

        sample_name = self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Sample ID']

        sample = self.db_session.query(Sample).filter(Sample.name==sample_name).filter(Sample.subject_id==subject.id).first()

        if not sample:

            sample = Sample(name=sample_name,
                            sample_type=self.npyc_dataset.sampleMetadata.loc[sample_row_index,'SampleType'].value,
                            assay_role=self.npyc_dataset.sampleMetadata.loc[sample_row_index,'AssayRole'].value,
                            sample_matrix=self.sample_matrix,
                            subject_id=subject.id)

            self.db_session.add(sample)
            self.db_session.flush()
            self.logger.info("Sample added %s" % sample)
        else:
            self.logger.info("Sample found %s" % sample)

        return sample

    def get_or_add_metadata(self,sample,sample_row_index):
        """Get or add metadata

        :param sample: The :class:`phenomedb.models.Sample`
        :type sample: :class:`phenomedb.models.Sample`
        :param sample_row_index: The sample metadata dataset row index
        :type sample_row_index: int
        """

        for field_name in self.npyc_dataset.sampleMetadata.columns:
            if field_name not in self.already_mapped_fields:

                metadata_field = self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id,
                                                                             MetadataField.name==field_name).first()
                if not metadata_field:
                    metadata_field = MetadataField(name=field_name,
                                                   project_id=self.project.id)
                    self.db_session.add(metadata_field)
                    self.db_session.flush()
                    self.logger.info("Metadata field added %s" % metadata_field)
                else:
                    self.logger.info("Metadata field found %s" % metadata_field)

                field_value = str(self.npyc_dataset.sampleMetadata.loc[sample_row_index,field_name]).strip()

                metadata_value = self.db_session.query(MetadataValue).filter(MetadataValue.sample_id==sample.id,
                                                                             MetadataValue.metadata_field_id==metadata_field.id).first()
                if not metadata_value:
                    metadata_value = MetadataValue(sample_id=sample.id,
                                                   metadata_field_id=metadata_field.id,
                                                   raw_value=field_value)
                    self.db_session.add(metadata_value)
                    self.db_session.flush()
                    self.logger.info("Metadata value added %s" % metadata_value)
                else:
                    self.logger.info("Metadata value found %s" % metadata_value)



    def get_or_add_sample_assay(self,sample,sample_row_index):
        """Get or add a new sample

        :param subject: The :class:`phenomedb.models.Subject` of the :class:`phenomedb.models.Sample`
        :type subject: :class:`phenomedb.models.Subject`
        :param sample_row_index: The dataset row index the sample
        :type sample_row_index: int
        :return: :class:`phenomedb.models.SampleAssay` object
        :rtype: class:`phenomedb.models.SampleAssay`
        """

        sample_assay = self.db_session.query(Sample).filter(SampleAssay.sample_id==sample.id,
                                                            SampleAssay.assay_id==self.assay.id).first()

        if not sample_assay:

            sample_assay = SampleAssay(sample_id=sample.id,
                                       sample_file_name=self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Sample File Name'].strip(),
                                       acquired_time=utils.get_date(self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Acquired Time']),
                                       run_order=int(float(self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Run Order'])),
                                       batch=self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Batch'],
                                       instrument_metadata=utils.convert_to_json_safe(self.clean_data_for_jsonb(self.npyc_dataset.sampleMetadata.loc[sample_row_index])))

            if 'Dilution' in self.npyc_dataset.sampleMetadata.loc[sample_row_index]:
                sample_assay.dilution = self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Dilution']

            if 'expno' in self.npyc_dataset.sampleMetadata.loc[sample_row_index]:
                sample_assay.expno =  self.npyc_dataset.sampleMetadata.loc[sample_row_index,'expno']

            if 'Sample Base Name' in self.npyc_dataset.sampleMetadata.loc[sample_row_index]:
                sample_assay.sample_base_name =  self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Sample Base Name']

            if 'Detector' in self.npyc_dataset.sampleMetadata.loc[sample_row_index]:
                sample_assay.detector =  self.npyc_dataset.sampleMetadata.loc[sample_row_index,'Detector']


            self.db_session.add(sample_assay)
            self.db_session.flush()
            self.logger.info("SampleAssay added %s" % sample_assay)
        else:
            self.logger.info("SampleAssay found %s" % sample_assay)

        return sample

    def get_or_add_annotated_features(self,sample_assay,sample_index):
        """Get or add annotated features

        :param sample_assay: The :class:`phenomedb.models.SampleAssay` object
        :type sample_assay: :class:`phenomedb.models.SampleAssay`
        :param sample_index: The sample metadata row index
        :type sample_index: int
        """

        for feature_index, feature_metadata_row in self.npyc_dataset.featureMetadata.iterrows():

            intensity = self.npyc_dataset.intensityData[sample_index,feature_index]
            annotation = self.annotations[feature_metadata_row['Feature Name'].strip()]

            annotated_feature = self.db_session.query(AnnotatedFeature).filter(AnnotatedFeature.sample_assay_id==sample_assay.id,
                                                                    AnnotatedFeature.feature_metadata_id==annotation.id).first()
            if not annotated_feature:
                annotated_feature = AnnotatedFeature(sample_assay_id=sample_assay.id,
                                          intensity=intensity,

                                          unit_id=self.unit_id)
                self.db_session.add(annotated_feature)
                self.db_session.flush()
                self.logger.info("AnnotatedFeature added %s" % annotated_feature)

            else:
                self.logger.info("AnnotatedFeature found %s" % annotated_feature)




class DownloadMetabolightsStudy(Task):
    """Download a Metabolights Study. If only study_id set, will download the study as well

    :param study_folder_path: Path to the study folder, defaults to None
    :type study_folder_path: str, optional
    :param study_id: ID of the Study, defaults to None
    :type study_id: int, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """

    def __init__(self, study_folder_path=None, study_id=None, task_run_id=None, username=None, db_env=None,
                 execution_date=None, db_session=None, pipeline_run_id=None):
        
        self.study_folder_path = study_folder_path
        self.study_id = study_id

        super().__init__(username=username, task_run_id=task_run_id, db_env=db_env, db_session=db_session,
                         execution_date=execution_date, pipeline_run_id=pipeline_run_id)

        self.args['study_id'] = study_id
        self.get_class_name(self)

    def process(self):
        if self.study_id and not os.path.exists(config['DATA']['app_data'] + "metabolights/" + self.study_id):
            self.download_files_from_metabolights(self.study_id,prefixes=['a', 'i', 's', 'm'], suffixes='mzml')

class ImportMetabolightsXCMSAnnotations(ImportTask):
    """Import MetabolightsXCMSAnnotations, e.g. to be run after DownloadMetabolightStudy and RunXCMS"

    :param study_folder_path: Path to the study folder, defaults to None
    :type study_folder_path: str, optional
    :param study_id: ID of the Study, defaults to None
    :type study_id: int, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    
    """

    def __init__(self,study_id=None,xcms_file=None,assay_name=None,assay_name_order=None,sample_matrix=None,task_run_id=None,username=None,db_env=None,execution_date=None,db_session=None,pipeline_run_id=None):
        
        self.study_id = study_id
        self.xcms_file = xcms_file
        self.assay_name = assay_name
        self.sample_matrix = sample_matrix
        self.assay_name_order = assay_name_order

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)

        self.args['study_id'] = study_id
        self.args['xcms_file'] = xcms_file
        self.args['assay_name'] = assay_name
        self.args['sample_matrix'] = sample_matrix
        self.args['assay_name_order'] = assay_name_order

        self.get_class_name(self)

        self.assay_information_dataframes = {}
        self.metabolite_information_dataframes = {}
        self.study_description_dict = {}
        self.annotation_assay_map = {}
        self.feature_dataset_map = {}
        self.annotation_method_map = {}
        self.annotation_map = {}

        self.study_folder_path = config['DATA']['app_data'] + "metabolights/" + self.study_id

    def load_dataset(self):
        """Loads the dataset
        """
        if self.study_id and not os.path.exists(self.study_folder_path):
            # raise NotImplementedError('API download not yet implemented')
            self.download_files_from_metabolights(prefixes=['a', 'i', 's', 'm'], suffixes=['mzml'])

        study_files = os.listdir(self.study_folder_path)

        for study_file in study_files:
            filepath = self.study_folder_path + "/" + study_file
            if re.search(r'^i_.*.txt$', study_file):
                self.load_study_description_file(filepath)
            elif re.search(r'^s_.*.txt$', study_file):
                self.sample_information_dataframe = self.load_tabular_file(filepath)
            elif re.search(r'^a_.*.txt$', study_file):
                self.assay_information_dataframes[study_file] = self.load_tabular_file(filepath)
            elif re.search(r'^m_.*.tsv$', study_file):
                self.metabolite_information_dataframes[study_file] = self.load_tabular_file(filepath)

        self.xcms_data = self.load_tabular_file(self.xcms_file)

    def load_study_description_file(self, filepath):
        """Takes study description file and builds a 2D dictionary of sections, and key -> values
            Lists

        ONTOLOGY SOURCE REFERENCE
        Term Source Name	"OBI"	"NCBITAXON"	"CHMO"	"CL"	"EFO"	"MS"	"NCIT"
        INVESTIGATION
        Investigation Identifier	"MTBLS1073"

        study_description_dict['ONTOLOGY SOURCE REFERENCE']['Term Source Name'] = ["OBI","NCBITAXON","CHMO","CL","EFO","MS","NCIT"]
        study_description_dict['INVESTIGATION']['Investigation Identifier'] = "MTBLS1073"

        :param filepath: The path to the study description file
        :type filepath: str
        """

        file = open(filepath, 'r')
        lines = file.readlines()
        file.close()

        current_section = ''
        for line in lines:
            try:
                line = line.rstrip()
                if line.strip().isupper():
                    current_section = line.strip()
                    self.study_description_dict[current_section] = {}
                else:
                    split_line = line.strip().split('\t')
                    split_line = [i.replace('"', '') for i in split_line]
                    key = split_line.pop(0)

                    # If its an array, or the current_section is a plural
                    if len(split_line) > 1 or re.search('S$', current_section):
                        self.study_description_dict[current_section][key] = split_line
                    elif len(split_line) == 1:
                        self.study_description_dict[current_section][key] = split_line.pop(0)
                    else:
                        self.study_description_dict[current_section][key] = None
            except Exception as err:
                self.logger.error('load_study_description_file error' + line)
                raise Exception(err)

    def map_and_add_dataset_data(self):
        """Map and add dataset data
        """

        self.parse_study_description()
        self.parse_sample_information()

        from phenomedb.compounds import CompoundTask
        self.compoundtask = CompoundTask(db_session=self.db_session)

        for assay_file, data in self.assay_information_dataframes.items():
            if assay_file in self.assays.keys() and self.assays[assay_file].name == self.assay_name:
                self.parse_assay_file(assay_file, data)

    def parse_assay_file(self, assay_file, data):
        """Parse an assay file

        :param assay_file: The name of the assay file
        :type assay_file: str
        :param data: The assay data
        :type data: `pandas.Dataframe`
        :raises NotImplementedError: [description]
        """
        if assay_file not in self.assays.keys():
            self.logger.error('Assay file not as expected %s %s' % (assay_file, self.assays))
        else:
            assay = self.assays[assay_file]
            metabolite_assignment_files = self.assay_information_dataframes[assay_file][
                'Metabolite Assignment File'].unique()
            if len(metabolite_assignment_files) == 1:
                self.add_annotation_compounds(assay, metabolite_assignment_files[0],assay_file)
            else:
                raise NotImplementedError("Multiple maf files per assay %s" % metabolite_assignment_files)

            assay_index = self.study_description_dict['STUDY ASSAYS']['Study Assay File Name'].index(assay_file)
            measurement_type = self.study_description_dict['STUDY ASSAYS']['Study Assay Measurement Type'][assay_index]
            default_unit = self.get_or_add_unit('noUnit', "no unit, for dimensionless variables (ie untargeted LC-MS)")

            feature_metadatas = self.add_feature_metadata(assay,assay_file)

            for row in data.iterrows():

                if assay.platform == AnalyticalPlatform.NMR:
                    sample_file_name = row[1]['Free Induction Decay Data File']
                elif assay.platform == AnalyticalPlatform.MS:
                    sample_file_name = row[1]['Raw Spectral Data File']
                else:
                    raise NotImplementedError('Assay platform not implemented: %s' % assay.platform)

                assay_parameters = row[1].where(pd.notnull(row[1]), None).to_dict()

                sample_name = row[1]['Sample Name']
                extract_name = row[1]['Sample Name']

                sample = self.db_session.query(Sample).join(Subject).filter(Sample.name == sample_name,
                                                                            Subject.project_id == self.project.id).first()

                if sample:

                    sample_assay = self.db_session.query(SampleAssay).filter(SampleAssay.sample_id == sample.id,
                                                                             SampleAssay.name == extract_name,
                                                                             SampleAssay.assay_id == assay.id).first()

                    if not sample_assay:
                        sample_assay = SampleAssay(name=extract_name,
                                                   sample_id=sample.id,
                                                   assay_id=assay.id,
                                                   sample_file_name=sample_file_name,
                                                   assay_parameters=assay_parameters)
                        self.db_session.add(sample_assay)
                        self.db_session.flush()

                    self.generate_feature_jsonb(sample_assay,feature_metadatas)

                    metabolite_assignment_file = row[1]['Metabolite Assignment File']

                    if metabolite_assignment_file is not None:
                        self.add_annotated_features(assay, metabolite_assignment_file, sample_assay, default_unit)

                else:
                    self.logger.info("No Sample found for %s" % sample_name)

                self.annotation_assay_map[row[1]['Metabolite Assignment File']] = assay

    def generate_feature_jsonb(self,sample_assay,feature_metadatas):
        """Build the features jsonb and add to SampleAssayFeatures

        :param sample_assay: The :class:`phenomedb.models.SampleAssay` object
        :type sample_assay: :class:`phenomedb.models.SampleAssay`
        :param feature_metadatas: The list of added FeatureMetadatas
        :type feature_metadatas: list
        """

        if sample_assay.assay_parameters['Derived Spectral Data File'] in self.xcms_data.columns:
            sample_assay_features = []
            features = self.xcms_data[sample_assay.assay_parameters['Derived Spectral Data File']].tolist()
            feature_map = {}
            i = 0
            while i < len(features):
                if features[i] is not None:
                    feature_map["fm_%s" % feature_metadatas[i].id] = features[i]
                i = i + 1
            sample_assay_features = SampleAssayFeatures(sample_assay_id=sample_assay.id,
                                                             features=feature_map)
            self.db_session.add(sample_assay_features)
            self.db_session.flush()

    def add_feature_metadata(self,assay,assay_file):
        """Add FeatureMetadata objects

        :param assay: The assay to import
        :type assay: str
        :param assay_file: The name of the assay file
        :type assay_file: str
        :return: List of added FeatureMetadatas
        :rtype: list
        """
        if assay_file in self.feature_dataset_map.keys():
            feature_dataset = self.feature_dataset_map[assay_file]
        else:
            feature_dataset = FeatureDataset(filetype='Metabolights',
                                             assay_id=assay.id,
                                             sample_matrix=self.sample_matrix)
            self.db_session.add(feature_dataset)
            self.db_session.flush()
        feature_metadatas = []
        i = 0
        while i < self.xcms_data.shape[0]:

            feature_metadatas.append(FeatureMetadata(feature_dataset_id=feature_dataset.id,
                                               mz_average=self.xcms_data.loc[i,'mz'],
                                               mz_min=self.xcms_data.loc[i,'mzmin'],
                                               mz_max=self.xcms_data.loc[i,'mzmax'],
                                               rt_average=self.xcms_data.loc[i,'rt'],
                                               rt_min=self.xcms_data.loc[i,'rtmin'],
                                               rt_max=self.xcms_data.loc[i,'rtmax']))
            i = i + 1
        self.db_session.add_all(feature_metadatas)
        self.db_session.flush()
        return feature_metadatas

    def add_annotated_features(self, assay, metabolite_assignment_file, sample_assay, default_unit):
        """Add Annotations and AnnotatedFeatures

        :param assay: The Assay
        :type assay: :class:`phenomedb.models.Assay`
        :param metabolite_assignment_file: The maf file
        :type metabolite_assignment_file: str
        :param sample_assay: The SampleAssay
        :type sample_assay: `phenomedb.models.SampleAssay`
        :param default_unit: The default unit to use
        :type default_unit: :class:`phenomedb.models.Unit`
        """

        feature_dataset = self.feature_dataset_map[metabolite_assignment_file]

        annotated_features = []
        if self.metabolite_information_dataframes[metabolite_assignment_file] is not None:
            for row in self.metabolite_information_dataframes[metabolite_assignment_file].iterrows():

                the_row = row[1].where(pd.notnull(row[1]), None)

                if sample_assay.name in the_row.keys():

                    intensity = the_row[sample_assay.name]
                else:
                    self.logger.info("%s not in columns for %s" % (sample_assay.sample.name,
                                                                   self.metabolite_information_dataframes[
                                                                       metabolite_assignment_file].columns))
                    intensity = None

                if intensity:
                    intensity = utils.parse_intensity_metabolights(intensity)
                #     if unit_string is not None and unit_string not in self.units.keys():
                #         self.units[unit_string] = self.get_or_add_unit(unit_string,unit_description=unit_string)

                #     if unit_string is not None:
                #         unit = self.units[unit_string]
                #         unit_id = unit.id
                #     else:
                #         unit_id = None

                if intensity is not None and the_row['database_identifier'] in self.annotation_map[assay.id].keys():

                    annotation = self.annotation_map[assay.id][the_row['database_identifier']]

                    mz = None
                    retention_time = None

                    if assay.platform == AnalyticalPlatform.MS:
                        if 'mass_to_charge' in the_row:
                            mz = the_row['mass_to_charge']
                        elif 'mz' in the_row:
                            mz = the_row['mz']

                        if 'retention_time' in the_row:
                            retention_time = the_row['retention_time']

                    feature_metadata = self.db_session.query(FeatureMetadata).filter(
                        FeatureMetadata.feature_dataset_id == feature_dataset.id,
                        FeatureMetadata.rt_average == retention_time,
                        FeatureMetadata.mz_average == mz,
                        FeatureMetadata.annotation_id == annotation.id).first()

                    if not feature_metadata:
                        feature_metadata = FeatureMetadata(feature_dataset_id=feature_dataset.id,
                                                           rt_average=retention_time,
                                                           mz_average=mz,
                                                           annotation_id=annotation.id)
                        self.db_session.add(feature_metadata)
                        self.db_session.flush()
                        self.logger.info("FeatureMetadata added %s" % feature_metadata)
                    else:
                        self.logger.info("FeatureMetadata found %s" % feature_metadata)

                    annotated_feature = self.db_session.query(AnnotatedFeature).filter(
                        AnnotatedFeature.sample_assay_id == sample_assay.id,
                        AnnotatedFeature.feature_metadata_id == feature_metadata.id).first()

                    if not annotated_feature:

                        annotated_feature = AnnotatedFeature(feature_metadata_id=feature_metadata.id,
                                                             sample_assay_id=sample_assay.id,
                                                             intensity=intensity,
                                                             unit_id=default_unit.id)
                        # annotated_features.append(annotated_feature)
                        self.db_session.add(annotated_feature)
                        self.db_session.flush()

                        self.logger.info("AnnotatedFeature added %s" % annotated_feature)
                    else:
                        self.logger.info("AnnotatedFeature found %s" % annotated_feature)

    def add_annotation_compounds(self, assay, annotation_file, assay_file):
        """Add the AnnotationCompounds.

        1. Add the Compound
        3. Add the HarmonisedAnnotation
        4. Add the AnnotationCompound

        :param assay: the Assay
        :type assay: `phenomedb.models.Assay`
        :param annotation_file: The annotation file
        :type annotation_file: str
        :param assay_file: The name of the assay file
        :type assay_file: str
        """

        if assay.id not in self.annotation_map.keys():
            self.annotation_map[assay.id] = {}

        # 1. What is the annotation_method? Is this findable in the Metabolights data?
        annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name == 'Unknown').first()

        if not annotation_method:
            annotation_method = AnnotationMethod(name='Unknown',
                                                 description='Unknown')
            self.db_session.add(annotation_method)
            self.db_session.flush()

        sample_matrices = self.sample_information_dataframe['Characteristics[Organism part]'].unique()
        if len(sample_matrices) == 1:
            sample_matrix = sample_matrices[0]
        else:
            sample_matrix = ",".join(sample_matrices)

        feature_dataset = self.db_session.query(FeatureDataset).filter(
            FeatureDataset.filetype == FeatureDataset.Type.metabolights,
            FeatureDataset.assay_id == assay.id,
            FeatureDataset.sample_matrix == sample_matrix).first()

        if not feature_dataset:
            feature_dataset = FeatureDataset(filetype=FeatureDataset.Type.metabolights,
                                             assay_id=assay.id,
                                             sample_matrix=sample_matrix)
            self.db_session.add(feature_dataset)
            self.db_session.flush()
            self.logger.info("FeatureDataset added %s" % feature_dataset)
        else:
            self.logger.info("FeatureDataset found %s" % feature_dataset)

        self.feature_dataset_map[assay_file] = feature_dataset
        self.annotation_method_map[annotation_file] = annotation_method

        if annotation_file in self.metabolite_information_dataframes.keys():
            for row in self.metabolite_information_dataframes[annotation_file].iterrows():

                the_row = row[1].where(pd.notnull(row[1]), None)

                chebi_id = the_row['database_identifier']
                cpd_name = the_row['metabolite_identification']

                if chebi_id not in self.annotation_map[assay.id].keys() and cpd_name is not None:
                    self.annotation_map[assay.id][chebi_id] = self.get_or_add_metabolights_compound(assay,
                                                                                                    annotation_method,
                                                                                                    the_row)

    def get_or_add_metabolights_compound(self, assay, annotation_method, the_row):
        """Get or add Metabolights Compound

        :param assay: The :class:`phenomedb.models.Assay`
        :type assay: :class:`phenomedb.models.Assay`
        :param annotation_method: The :class:`phenomedb.models.AnnotationMethod`
        :type annotation_method: :class:`phenomedb.models.AnnotationMethod`
        :param the_row: The row from the dataframe
        :type the_row: :class:`pd.Series`
        :return: AnnotationCompound
        :rtype: `phenomedb.models.AnnotationCompound`
        """
        chebi_id = the_row['database_identifier']
        if chebi_id is not None:
            chebi_split = chebi_id.split(':')
        else:
            chebi_split = []

        cpd_name = the_row['metabolite_identification']

        harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
            HarmonisedAnnotation.cpd_name == cpd_name,
            HarmonisedAnnotation.annotation_method_id == annotation_method.id,
            HarmonisedAnnotation.assay_id == assay.id).first()

        if not harmonised_annotation:
            harmonised_annotation = HarmonisedAnnotation(cpd_name=cpd_name,
                                                         annotation_method_id=annotation_method.id,
                                                         assay_id=assay.id)

            self.db_session.add(harmonised_annotation)
            self.db_session.flush()
            self.logger.info("HarmonisedAnnotation added %s" % harmonised_annotation)
        else:
            self.logger.info("HarmonisedAnnotation found %s" % harmonised_annotation)

        annotation = self.db_session.query(Annotation).filter(Annotation.cpd_name == cpd_name,
                                                              Annotation.annotation_method_id == annotation_method.id,
                                                              Annotation.assay_id == assay.id,
                                                              Annotation.harmonised_annotation_id == harmonised_annotation.id).first()

        if not annotation:
            annotation = Annotation(cpd_name=cpd_name,
                                    annotation_method_id=annotation_method.id,
                                    assay_id=assay.id,
                                    harmonised_annotation_id=harmonised_annotation.id,
                                    config=utils.convert_to_json_safe(
                                        self.clean_data_for_jsonb(the_row.to_dict())))

            self.db_session.add(annotation)
            self.db_session.flush()
            self.logger.info("Annotation added %s" % annotation)
        else:
            self.logger.info("Annotation found %s" % annotation)

        inchi = None
        if not the_row['inchi'] and chebi_id is not None and len(chebi_split) > 1:
            try:
                chebi_entity = ChebiEntity(chebi_split[1])
                inchi = chebi_entity.get_inchi()
            except Exception as err:
                self.logger.exception(err)

        else:
            inchi = the_row['inchi']

        if inchi is None:
            inchi = 'Unknown'

        compound = self.db_session.query(Compound).filter(Compound.inchi == inchi, Compound.name == cpd_name).first()

        if not compound:

            try:
                compound = Compound(name=cpd_name,
                                    inchi=inchi,
                                    chemical_formula=the_row['chemical_formula'],
                                    smiles=the_row['smiles'])
                compound.set_inchi_key_from_rdkit()
                compound.set_log_p_from_rdkit()
                self.db_session.add(compound)
                self.db_session.flush()
                pubchem_cid = self.compoundtask.add_or_update_pubchem_from_api(compound)
                chebi_id = self.compoundtask.add_or_update_chebi(compound)
                refmet_name = self.compoundtask.update_name_to_refmet(compound)
                kegg_id = self.compoundtask.add_or_update_kegg(compound, pubchem_cid=pubchem_cid)
                hmdb_id = self.compoundtask.add_or_update_hmdb(compound)
                lm_id = self.compoundtask.add_or_update_lipid_maps(compound)
                chembl_id = self.compoundtask.add_or_update_chembl(compound)
                self.compoundtask.add_or_update_classyfire(compound)
                self.logger.info("Compound added %s" % compound)
            except Exception as err:
                self.logger.exception("Compound import failed: %s" % err)
        else:
            self.logger.info("Compound found %s" % compound)

        annotation_compound = self.db_session.query(AnnotationCompound).filter(
            AnnotationCompound.harmonised_annotation_id == harmonised_annotation.id,
            AnnotationCompound.compound_id == compound.id).first()

        if not annotation_compound:
            annotation_compound = AnnotationCompound(harmonised_annotation_id=harmonised_annotation.id,
                                                     compound_id=compound.id)

            self.db_session.add(annotation_compound)
            self.db_session.flush()
            self.logger.info("AnnotationCompound added %s" % annotation_compound)
        else:
            self.logger.info("AnnotationCompound found %s" % annotation_compound)

        return annotation

    def parse_sample_information(self):
        """Parse sample information
        """
        # 1. Loop over rows and add Subjects & Samples & MetadataFields and MetadataValues

        # 'Source Name	Characteristics[Organism]	Term Source REF	Term Accession Number	Characteristics[Variant]	Term Source REF	Term Accession Number	Characteristics[Organism part]	Term Source REF	Term Accession Number	Protocol REF	Sample Name	Factor Value[Virus]	Term Source REF	Term Accession Number	Factor Value[Replicate]	Term Source REF	Term Accession Number'

        for row in self.sample_information_dataframe.iterrows():

            i = 0

            sample_name = None
            sample_type = 'experimental sample'
            sample_matrix = None
            ontology_refs = {}
            metadata_fields = {}

            while i < len(self.sample_information_dataframe.columns):

                col = self.sample_information_dataframe.columns[i]

                if re.search('Characteristics', col) or re.search('Factor Value', col):
                    splitted = col.split('[')
                    field_name = splitted[1].replace(']', '')

                    ontology_refs[field_name] = {}
                    ontology_refs[field_name]['ref'] = row[1][self.sample_information_dataframe.columns[(i + 1)]]
                    ontology_refs[field_name]['accession'] = row[1][self.sample_information_dataframe.columns[(i + 2)]]

                    if field_name == 'Sample type':
                        sample_type = row[1][col]
                    elif field_name == 'Organism part':
                        sample_matrix = row[1][col]
                    else:
                        metadata_fields[field_name] = row[1][col]

                    i = i + 3

                else:
                    if col == 'Sample Name':
                        sample_name = str(row[1]['Sample Name'])

                    i = i + 1

            # 1. Get the correct sample_type enum value

            try:
                sample_type_enum = utils.get_npyc_enum_from_value(sample_type)
            except NotImplementedError:
                sample_type_enum = SampleType.StudySample

            # 2. Get or add the Subject (if QC sample, use that as name, otherwise use sample_name as Subject.name)
            subject = self.get_or_add_subject(sample_name, sample_type_enum)

            # 3. Get or add the Sample
            sample = self.get_or_add_sample(subject, sample_name, sample_type_enum, sample_matrix)

            for field_name, field_value in metadata_fields.items():
                self.get_or_add_metadata_field(field_name, field_value, sample)

    def get_or_add_subject(self, sample_name, sample_type_enum):
        """Get or add subject

        :param sample_name: Sample name
        :type sample_name: str
        :param sample_type_enum: Sample Type
        :type sample_type_enum: str
        :return: Subject
        :rtype: :class:`phenomedb.models.Subject`
        """

        if sample_type_enum == SampleType.StudySample:
            subject_name = sample_name
        else:
            subject_name = sample_type_enum.value

        subject = self.db_session.query(Subject).filter(Subject.name == subject_name,
                                                        Subject.project_id == self.project.id).first()

        if not subject:
            subject = Subject(name=subject_name,
                              project_id=self.project.id)
            self.db_session.add(subject)
            self.db_session.flush()
            self.logger.info("Subject added %s" % subject)
        else:
            self.logger.info("Subject found %s" % subject)

        return subject

    def get_or_add_sample(self, subject, sample_name, sample_type_enum, sample_matrix):
        """Get or add Sample

        :param subject: Subject
        :type subject: :class:`phenomedb.models.Subject`
        :param sample_name: Sample name
        :type sample_name: str
        :param sample_type_enum: SampleType enum
        :type sample_type_enum: `SampleType`
        :param sample_matrix: Sample matrix
        :type sample_matrix: sample matrix
        :return: Sample
        :rtype: :class:`phenomedb.models.Sample`
        """
        # Need to check what the sample_names, plus types of QC samples, and what their assay roles are

        sample = self.db_session.query(Sample).filter(Sample.subject_id == subject.id,
                                                      Sample.name == sample_name).first()

        if not sample:
            if sample_type_enum == SampleType.StudySample:
                assay_role = AssayRole.Assay
            else:
                assay_role = None

            try:
                biological_tissue = Sample.get_biological_tissue(sample_matrix)
            except NotImplementedError as err:
                self.logger.exception(err)
                biological_tissue = None

            sample = Sample(name=sample_name,
                            sample_type=sample_type_enum,
                            assay_role=assay_role,
                            sample_matrix=sample_matrix,
                            biological_tissue=biological_tissue,
                            subject_id=subject.id
                            )
            self.db_session.add(sample)
            self.db_session.flush()
            self.logger.info("Sample added %s" % sample)
        else:
            self.logger.info("Sample added %s" % sample)

        return sample

    def get_or_add_metadata_field(self, field_name, field_value, sample):
        """Get or add metadata field

        :param field_name: The name of the metadata field
        :type field_name: str
        :param field_value: The value of the metadata field
        :type field_value: str
        :param sample: Sample
        :type sample: :class:`phenomedb.models.Sample`
        """

        metadata_field = self.db_session.query(MetadataField).filter(MetadataField.project_id == self.project.id,
                                                                     MetadataField.name == field_name).first()

        if not metadata_field:
            metadata_field = MetadataField(name=field_name,
                                           project_id=self.project.id)
            self.db_session.add(metadata_field)
            self.db_session.flush()

        metadata_value = self.db_session.query(MetadataValue).filter(
            MetadataValue.metadata_field_id == metadata_field.id,
            MetadataValue.sample_id == sample.id).first()

        if not metadata_value:
            metadata_value = MetadataValue(metadata_field_id=metadata_field.id,
                                           sample_id=sample.id,
                                           raw_value=str(field_value)
                                           )
            self.db_session.add(metadata_value)
            self.db_session.flush()
            self.logger.info("MetadataValue added %s" % metadata_value)

        else:
            self.logger.info("MetadataValue found %s" % metadata_value)

    def parse_study_description(self):
        """Parse the study description
        """

        persons = self.parse_persons()

        self.get_or_add_project(self.study_description_dict['STUDY']['Study Identifier'],
                                project_description=self.study_description_dict['STUDY']['Study Description'],
                                project_folder_name=None,
                                lims_id=None,
                                short_description=self.study_description_dict['STUDY']['Study Title'],
                                persons=persons)

        self.get_or_add_data_repository('Metabolights',
                                        accession_number=self.study_description_dict['STUDY']['Study Identifier'],
                                        submission_date=utils.get_date(
                                            self.study_description_dict['STUDY']['Study Submission Date']),
                                        public_release_date=utils.get_date(
                                            self.study_description_dict['STUDY']['Study Public Release Date']))

        self.parse_protocols()
        self.parse_publications()
        self.parse_assays()

    def parse_persons(self):
        """Parse the persons

        :return: person dict
        :rtype: dict
        """

        persons = {}

        i = 0
        while i < len(self.study_description_dict['STUDY CONTACTS']['Study Person Email']):
            person_dict = {}
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person First Name']) > i:
                person_dict['first_name'] = self.study_description_dict['STUDY CONTACTS']['Study Person First Name'][i]
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person Last Name']) > i:
                person_dict['last_name'] = self.study_description_dict['STUDY CONTACTS']['Study Person Last Name'][i]
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person Affiliation']) > i:
                person_dict['affiliation'] = self.study_description_dict['STUDY CONTACTS']['Study Person Affiliation'][
                    i]
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person Roles']) > i:
                person_dict['role'] = self.study_description_dict['STUDY CONTACTS']['Study Person Roles'][i]
            persons[self.study_description_dict['STUDY CONTACTS']['Study Person Email'][i]] = person_dict
            i = i + 1

        return persons

    def get_or_add_data_repository(self, name,
                                   accession_number=None,
                                   submission_date=None,
                                   public_release_date=None):
        """Get or add repository

        :param name: Name of the repo
        :type name: str
        :param accession_number: accession number of repo, defaults to None
        :type accession_number: str, optional
        :param submission_date: Date of submission, defaults to None
        :type submission_date: `datetime.datetime`, optional
        :param public_release_date: Date of release, defaults to None
        :type public_release_date: `datetime.datetime`, optional
        :return: DataRepository
        :rtype: `phenomedb.models.DataRepository`
        """

        data_repository = self.db_session.query(DataRepository).filter(DataRepository.name == name,
                                                                       DataRepository.accession_number == accession_number).first()

        if not data_repository:

            data_repository = DataRepository(name=name,
                                             accession_number=accession_number,
                                             submission_date=submission_date,
                                             public_release_date=utils.get_date(public_release_date),
                                             project_id=self.project.id)
            self.db_session.add(data_repository)
            self.db_session.flush()
            self.logger.info("DataRepository added %s" % data_repository)
        else:
            self.logger.info("DataRepository found %s" % data_repository)

        return data_repository

    def parse_protocols(self):
        """Parse the protocols
        """

        i = 0
        while i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Name']):

            name = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Name'][i]
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Type']):
                type = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Type'][i]
            else:
                type = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Description']):
                description = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Description'][i]
            else:
                description = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol URI']):
                uri = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol URI'][i]
            else:
                uri = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Version']):
                version = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Version'][i]
            else:
                version = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Parameters Name']):
                parameters = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Parameters Name'][i].split(
                    ';')
            else:
                parameters = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Components Name']):
                components = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Components Name'][i].split(
                    ';')
            else:
                components = None

            self.get_or_add_protocol(name=name,
                                     type=type,
                                     description=description,
                                     uri=uri,
                                     version=version,
                                     parameters=parameters,
                                     components=components
                                     )

            i = i + 1

    def get_or_add_protocol(self, name=None,
                            type=None,
                            description=None,
                            uri=None,
                            version=None,
                            parameters=None,
                            components=None):
        """Get or add the protocol

        :param name: protocol name, defaults to None
        :type name: str, optional
        :param type: protocol type, defaults to None
        :type type: str, optional
        :param description: description, defaults to None
        :type description: str, optional
        :param uri: URI of the protocol, defaults to None
        :type uri: str, optional
        :param version: version of the protocol, defaults to None
        :type version: str, optional
        :param parameters: parameters of the protocol, defaults to None
        :type parameters: dict, optional
        :param components: components of the protocol, defaults to None
        :type components: dict, optional
        """

        protocol = self.db_session.query(Protocol).filter(Protocol.name == name,
                                                          Protocol.type == type).first()

        if not protocol:
            protocol = Protocol(name=name,
                                type=type,
                                description=description,
                                uri=uri,
                                version=version,
                                )
            self.db_session.add(protocol)
            self.db_session.flush()

            self.logger.info("Protocol added %s" % protocol)
        else:
            self.logger.info("Protocol found %s " % protocol)

        if isinstance(parameters, list):
            for parameter in parameters:
                if parameter != '':
                    protocol_parameter = self.db_session.query(ProtocolParameter).filter(
                        ProtocolParameter.name == parameter,
                        ProtocolParameter.protocol_id == protocol.id).first()
                    if not protocol_parameter:
                        protocol_parameter = ProtocolParameter(name=parameter, protocol_id=protocol.id)
                        self.db_session.add(protocol_parameter)
                        self.db_session.flush()

                        self.logger.info("ProtocolParameter added %s" % protocol_parameter)
                    else:
                        self.logger.info("ProtocolParameter found %s " % protocol_parameter)

    def parse_publications(self):
        """Parse the publications
        """

        i = 0
        while i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Title']):

            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study PubMed ID']):
                pubmed_id = self.study_description_dict['STUDY PUBLICATIONS']['Study PubMed ID'][i]
            else:
                pubmed_id = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication DOI']):
                doi = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication DOI'][i]
            else:
                doi = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Author List']):
                author_list = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Author List'][i]
            else:
                author_list = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Title']):
                title = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Title'][i]
            else:
                title = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Status']):
                status = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Status'][i]
            else:
                status = None

            self.get_or_add_publication(pubmed_id=pubmed_id,
                                        doi=doi,
                                        author_list=author_list,
                                        title=title,
                                        status=status,
                                        )
            i = i + 1

    def get_or_add_publication(self, pubmed_id=None, doi=None, author_list=None, title=None, status=None):
        """Get or add publication

        :param pubmed_id: pubmed id, defaults to None
        :type pubmed_id: int, optional
        :param doi: DOI, defaults to None
        :type doi: str, optional
        :param author_list: List of authors, defaults to None
        :type author_list: list, optional
        :param title: publication title, defaults to None
        :type title: str, optional
        :param status: Publication status, defaults to None
        :type status: str, optional
        """

        publication = self.db_session.query(Publication).filter(Publication.title == title,
                                                                Publication.doi == doi,
                                                                Publication.project_id == self.project.id).first()

        if not publication:
            publication = Publication(pubmed_id=pubmed_id,
                                      doi=doi,
                                      author_list=author_list,
                                      title=title,
                                      status=status,
                                      project_id=self.project.id)
            self.db_session.add(publication)
            self.db_session.flush()
            self.logger.info("Publication added %s" % publication)
        else:
            self.logger.info("Publication found %s" % publication)

    def parse_assays(self):
        """Parse the assays
        """

        self.assays = {}

        i = 0
        while i < len(self.study_description_dict['STUDY ASSAYS']['Study Assay File Name']):
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay File Name']) > i:
                study_assay_file_name = self.study_description_dict['STUDY ASSAYS']['Study Assay File Name'][i]
            else:
                study_assay_file_name = None
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay Measurement Type']) > i:
                measurement_type = self.study_description_dict['STUDY ASSAYS']['Study Assay Measurement Type'][i]
            else:
                measurement_type = None
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Type']) > i:
                long_platform = self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Type'][i]
            else:
                long_platform = None
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Platform']) > i:
                long_name = self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Platform'][i]
            else:
                long_name = None

            if 'targeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS'][
                'Study Design Type'] and \
                    'untargeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS'][
                'Study Design Type']:
                raise Exception(
                    "Both targeted and untargeted assays exist, please specify which is which in the task parameters")
            elif 'targeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS']['Study Design Type']:
                targeted = 'Y'
            elif 'untargeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS'][
                'Study Design Type']:
                targeted = 'N'
            else:
                targeted = None

            if isinstance(self.assay_name_order,list) and i < len(self.assay_name_order):
                assay_name = self.assay_name_order[i]
            else:
                assay_name = long_name

            assay = self.db_session.query(Assay).filter(or_(Assay.name == assay_name,
                                                            Assay.long_name == long_name)).first()

            if not assay:

                assay = Assay(name=assay_name,
                              long_platform=long_platform,
                              long_name=long_name,
                              measurement_type=measurement_type,
                              targeted=targeted
                              )
                assay.set_platform_from_long_platform(long_platform)

                self.db_session.add(assay)
                self.db_session.flush()
                self.logger.info('Assay added %s' % assay)
            else:
                self.logger.info('Assay found %s' % assay)

            self.assays[study_assay_file_name] = assay

            i = i + 1

class ImportMetabolightsStudy(ImportTask):
    """Import a Metabolights Study. If only study_id set, will download the study as well

    :param study_folder_path: Path to the study folder, defaults to None
    :type study_folder_path: str, optional
    :param study_id: ID of the Study, defaults to None
    :type study_id: int, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """        
   

    def __init__(self,study_id=None,task_run_id=None,username=None,db_env=None,execution_date=None,db_session=None,pipeline_run_id=None):
        
        self.study_id = study_id

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)

        self.args['study_id'] = study_id
        self.get_class_name(self)

        self.assay_information_dataframes = {}
        self.metabolite_information_dataframes = {}
        self.study_description_dict = {}
        self.annotation_assay_map = {}
        self.feature_dataset_map = {}
        self.annotation_method_map = {}
        self.annotation_map = {}

        self.study_folder_path = config['DATA']['app_data'] + "metabolights/" + self.study_id

    def load_dataset(self):
        """Loads the dataset
        """
        if self.study_id and not os.path.exists(self.study_folder_path):
            #raise NotImplementedError('API download not yet implemented')
            self.download_files_from_metabolights(prefixes=['a','i','s','m'],suffixes=['mzml'])

        study_files = os.listdir(self.study_folder_path)

        for study_file in study_files:
            filepath = self.study_folder_path + "/" + study_file
            if re.search(r'^i_.*.txt$',study_file):
                self.load_study_description_file(filepath)
            elif re.search(r'^s_.*.txt$',study_file):
                self.sample_information_dataframe = self.load_tabular_file(filepath)
            elif re.search(r'^a_.*.txt$',study_file):
                self.assay_information_dataframes[study_file] = self.load_tabular_file(filepath)
            elif re.search(r'^m_.*.tsv$',study_file):
                self.metabolite_information_dataframes[study_file] = self.load_tabular_file(filepath)



    def load_study_description_file(self,filepath):
        """Takes study description file and builds a 2D dictionary of sections, and key -> values
            Lists

        ONTOLOGY SOURCE REFERENCE
        Term Source Name	"OBI"	"NCBITAXON"	"CHMO"	"CL"	"EFO"	"MS"	"NCIT"
        INVESTIGATION
        Investigation Identifier	"MTBLS1073"

        study_description_dict['ONTOLOGY SOURCE REFERENCE']['Term Source Name'] = ["OBI","NCBITAXON","CHMO","CL","EFO","MS","NCIT"]
        study_description_dict['INVESTIGATION']['Investigation Identifier'] = "MTBLS1073"

        :param filepath: The path to the study description file
        :type filepath: str
        """

        file = open(filepath,'r')
        lines = file.readlines()
        file.close()
        
        current_section = ''
        for line in lines:
            try:
                line = line.rstrip()
                if line.strip().isupper():
                    current_section = line.strip()
                    self.study_description_dict[current_section] = {}
                else:
                    split_line = line.strip().split('\t')
                    split_line = [i.replace('"', '') for i in split_line]
                    key = split_line.pop(0)

                    # If its an array, or the current_section is a plural
                    if len(split_line) > 1 or re.search('S$',current_section):
                        self.study_description_dict[current_section][key] = split_line
                    elif len(split_line) == 1:
                        self.study_description_dict[current_section][key] = split_line.pop(0)
                    else:
                        self.study_description_dict[current_section][key] = None
            except Exception as err:
                self.logger.error('load_study_description_file error' + line)
                raise Exception(err)

    def map_and_add_dataset_data(self):
        """Map and add dataset data
        """        

        self.parse_study_description()
        self.parse_sample_information()

        from phenomedb.compounds import CompoundTask
        self.compoundtask = CompoundTask(db_session=self.db_session)

        for assay_file, data in self.assay_information_dataframes.items():
            self.parse_assay_file(assay_file,data)


    def parse_assay_file(self,assay_file,data):
        """Parse an assay file

        :param assay_file: The name of the assay file
        :type assay_file: str
        :param data: The assay data
        :type data: :class:`pd.Dataframe`
        :raises NotImplementedError: Assay platform not implemented
        """        
        if assay_file not in self.assays.keys():
            self.logger.error('Assay file not as expected %s %s' % (assay_file,self.assays))
        else:
            assay = self.assays[assay_file]
            metabolite_assignment_files = self.assay_information_dataframes[assay_file]['Metabolite Assignment File'].unique()
            if len(metabolite_assignment_files) == 1:
                self.add_annotation_compounds(assay, metabolite_assignment_files[0])
            else:
                raise NotImplementedError("Multiple maf files per assay %s" % metabolite_assignment_files)

            assay_index = self.study_description_dict['STUDY ASSAYS']['Study Assay File Name'].index(assay_file)
            measurement_type = self.study_description_dict['STUDY ASSAYS']['Study Assay Measurement Type'][assay_index]
            default_unit = self.get_or_add_unit('noUnit',"no unit, for dimensionless variables (ie untargeted LC-MS)")

            for row in data.iterrows():

                if row[1]['Metabolite Assignment File'] is not None:
                    if assay.platform == AnalyticalPlatform.NMR:
                        sample_file_name = row[1]['Free Induction Decay Data File']
                    elif assay.platform == AnalyticalPlatform.MS:
                        sample_file_name = row[1]['Raw Spectral Data File']
                    else:
                        raise NotImplementedError('Assay platform not implemented: %s' % assay.platform)

                    assay_parameters = row[1].where(pd.notnull(row[1]), None).to_dict()

                    sample_name = row[1]['Sample Name']
                    extract_name = row[1]['Sample Name']

                    sample = self.db_session.query(Sample).join(Subject).filter(Sample.name==sample_name,
                                                                                               Subject.project_id==self.project.id).first()

                    if sample:

                        sample_assay = self.db_session.query(SampleAssay).filter(SampleAssay.sample_id==sample.id,
                                                                                 SampleAssay.name==extract_name,
                                                                                                SampleAssay.assay_id==assay.id).first()

                        if not sample_assay:
                            sample_assay = SampleAssay(name=extract_name,
                                                       sample_id=sample.id,
                                                       assay_id=assay.id,
                                                       sample_file_name=sample_file_name,
                                                       assay_parameters=assay_parameters)
                            self.db_session.add(sample_assay)
                            self.db_session.flush()

                        metabolite_assignment_file = row[1]['Metabolite Assignment File']

                        if metabolite_assignment_file is not None:
                            self.add_annotated_features(assay,metabolite_assignment_file,sample_assay,default_unit)

                    else:
                        self.logger.info("No Sample found for %s" % sample_name)

                    self.annotation_assay_map[row[1]['Metabolite Assignment File']] = assay

    def add_annotated_features(self,assay,metabolite_assignment_file,sample_assay,default_unit):
        """Add Annotations and AnnotatedFeatures

        :param assay: The Assay
        :type assay: `phenomedb.models.Assay`
        :param metabolite_assignment_file: The maf file
        :type metabolite_assignment_file: str
        :param sample_assay: The SampleAssay
        :type sample_assay: :class:`phenomedb.models.SampleAssay`
        """

        feature_dataset = self.feature_dataset_map[metabolite_assignment_file]
        
        annotated_features = []
        if self.metabolite_information_dataframes[metabolite_assignment_file] is not None:
            for row in self.metabolite_information_dataframes[metabolite_assignment_file].iterrows():

                the_row = row[1].where(pd.notnull(row[1]), None)

                if sample_assay.name in the_row.keys():

                    intensity = the_row[sample_assay.name]
                else:
                    self.logger.info("%s not in columns for %s" % (sample_assay.sample.name,self.metabolite_information_dataframes[metabolite_assignment_file].columns))
                    intensity = None

                if intensity:
                    intensity = utils.parse_intensity_metabolights(intensity)
               #     if unit_string is not None and unit_string not in self.units.keys():
               #         self.units[unit_string] = self.get_or_add_unit(unit_string,unit_description=unit_string)

               #     if unit_string is not None:
               #         unit = self.units[unit_string]
               #         unit_id = unit.id
               #     else:
               #         unit_id = None

                if intensity is not None and the_row['database_identifier'] in self.annotation_map[assay.id].keys():

                    annotation = self.annotation_map[assay.id][the_row['database_identifier']]

                    mz = None
                    retention_time = None

                    if assay.platform == AnalyticalPlatform.MS:
                        if 'mass_to_charge' in the_row:
                            mz = the_row['mass_to_charge']
                        elif 'mz' in the_row:
                            mz = the_row['mz']

                        if 'retention_time' in the_row:
                            retention_time = the_row['retention_time']

                    feature_metadata = self.db_session.query(FeatureMetadata).filter(FeatureMetadata.feature_dataset_id==feature_dataset.id,
                                                                                     FeatureMetadata.rt_average==retention_time,
                                                                                     FeatureMetadata.mz_average==mz,
                                                                                     FeatureMetadata.annotation_id==annotation.id).first()

                    if not feature_metadata:
                        feature_metadata = FeatureMetadata(feature_dataset_id=feature_dataset.id,
                                                           rt_average=retention_time,
                                                           mz_average=mz,
                                                           annotation_id=annotation.id)
                        self.db_session.add(feature_metadata)
                        self.db_session.flush()
                        self.logger.info("FeatureMetadata added %s" % feature_metadata)
                    else:
                        self.logger.info("FeatureMetadata found %s" % feature_metadata)

                    annotated_feature = self.db_session.query(AnnotatedFeature).filter(AnnotatedFeature.sample_assay_id==sample_assay.id,
                                                                                        AnnotatedFeature.feature_metadata_id==feature_metadata.id).first()

                    if not annotated_feature:

                        annotated_feature = AnnotatedFeature(feature_metadata_id=feature_metadata.id,
                                                            sample_assay_id=sample_assay.id,
                                                            intensity=intensity,
                                                             unit_id=default_unit.id)
                        #annotated_features.append(annotated_feature)
                        self.db_session.add(annotated_feature)
                        self.db_session.flush()

                        self.logger.info("AnnotatedFeature added %s" % annotated_feature)
                    else:
                        self.logger.info("AnnotatedFeature found %s" % annotated_feature)

    def add_annotation_compounds(self,assay,annotation_file):
        """Add the AnnotationCompounds.

        1. Add the Compound
        3. Add the HarmonisedAnnotation
        4. Add the AnnotationCompound

        :param assay: the Assay
        :type assay: :class:`phenomedb.models.Assay`
        :param annotation_file: The annotation file
        :type annotation_file: str
        """        

        if assay.id not in self.annotation_map.keys():
            self.annotation_map[assay.id] = {}

        # 1. What is the annotation_method? Is this findable in the Metabolights data?
        annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name=='Unknown').first()

        if not annotation_method:
            annotation_method = AnnotationMethod(name='Unknown',
                                                 description='Unknown')
            self.db_session.add(annotation_method)
            self.db_session.flush()

        sample_matrices = self.sample_information_dataframe['Characteristics[Organism part]'].unique()
        if len(sample_matrices) == 1:
            sample_matrix = sample_matrices[0]
        else:
            sample_matrix = ",".join(sample_matrices)

        feature_dataset = self.db_session.query(FeatureDataset).filter(FeatureDataset.filetype==FeatureDataset.Type.metabolights,
                                                                     FeatureDataset.assay_id==assay.id,
                                                                       FeatureDataset.sample_matrix==sample_matrix).first()

        if not feature_dataset:
            feature_dataset = FeatureDataset(filetype=FeatureDataset.Type.metabolights,
                                             assay_id=assay.id,
                                             sample_matrix=sample_matrix)
            self.db_session.add(feature_dataset)
            self.db_session.flush()
            self.logger.info("FeatureDataset added %s" % feature_dataset)
        else:
            self.logger.info("FeatureDataset found %s" % feature_dataset)


        self.feature_dataset_map[annotation_file] = feature_dataset
        self.annotation_method_map[annotation_file] = annotation_method

        if annotation_file in self.metabolite_information_dataframes.keys():
            for row in self.metabolite_information_dataframes[annotation_file].iterrows():

                the_row = row[1].where(pd.notnull(row[1]), None)

                chebi_id = the_row['database_identifier']
                cpd_name = the_row['metabolite_identification']

                if chebi_id not in self.annotation_map[assay.id].keys() and cpd_name is not None:
                    self.annotation_map[assay.id][chebi_id] = self.get_or_add_metabolights_compound(assay,annotation_method,the_row)

    def get_or_add_metabolights_compound(self,assay,annotation_method,the_row):
        """Get or add Metabolights Compound

        :param assay: Assay
        :type assay: :class:`phenomedb.models.Assay`
        :param annotation_method: AnnotationMethod
        :type annotation_method: :class:`phenomedb.models.AnnotationMethod`
        :param chebi_id: ChEBI ID
        :type chebi_id: str
        :param chemical_formula: Chemical formula
        :type chemical_formula: str
        :param smiles: SMILES 
        :type smiles: str
        :param inchi: InChI
        :type inchi: str
        :param cpd_name: cpd_name
        :type cpd_name: str
        :return: AnnotationCompound
        :rtype: :class:`phenomedb.models.AnnotationCompound`
        """
        chebi_id = the_row['database_identifier']
        if chebi_id is not None:
            chebi_split = chebi_id.split(':')
        else:
            chebi_split = []

        cpd_name = the_row['metabolite_identification']

        harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(HarmonisedAnnotation.cpd_name == cpd_name,
                                                                               HarmonisedAnnotation.annotation_method_id == annotation_method.id,
                                                                               HarmonisedAnnotation.assay_id == assay.id).first()

        if not harmonised_annotation:
            harmonised_annotation = HarmonisedAnnotation(cpd_name=cpd_name,
                                                        annotation_method_id=annotation_method.id,
                                                         assay_id=assay.id)

            self.db_session.add(harmonised_annotation)
            self.db_session.flush()
            self.logger.info("HarmonisedAnnotation added %s" % harmonised_annotation)
        else:
            self.logger.info("HarmonisedAnnotation found %s" % harmonised_annotation)

        annotation = self.db_session.query(Annotation).filter(Annotation.cpd_name == cpd_name,
                                                            Annotation.annotation_method_id == annotation_method.id,
                                                            Annotation.assay_id == assay.id,
                                                            Annotation.harmonised_annotation_id==harmonised_annotation.id).first()

        if not annotation:
            annotation = Annotation(cpd_name=cpd_name,
                                    annotation_method_id=annotation_method.id,
                                    assay_id=assay.id,
                                    harmonised_annotation_id=harmonised_annotation.id,
                                    config=utils.convert_to_json_safe(
                                                           self.clean_data_for_jsonb(the_row.to_dict())))

            self.db_session.add(annotation)
            self.db_session.flush()
            self.logger.info("Annotation added %s" % annotation)
        else:
            self.logger.info("Annotation found %s" % annotation)

        inchi = None
        if not the_row['inchi'] and chebi_id is not None and len(chebi_split) > 1:
            try:
                chebi_entity = ChebiEntity(chebi_split[1])
                inchi = chebi_entity.get_inchi()
            except Exception as err:
                self.logger.exception(err)

        else:
            inchi = the_row['inchi']

        if inchi is None:
            inchi = 'Unknown'

        compound = self.db_session.query(Compound).filter(Compound.inchi==inchi,Compound.name==cpd_name).first()

        if not compound:

            try:
                compound = Compound(name=cpd_name,
                                    inchi=inchi,
                                    chemical_formula=the_row['chemical_formula'],
                                    smiles=the_row['smiles'])
                compound.set_inchi_key_from_rdkit()
                compound.set_log_p_from_rdkit()
                self.db_session.add(compound)
                self.db_session.flush()
                pubchem_cid = self.compoundtask.add_or_update_pubchem_from_api(compound)
                chebi_id = self.compoundtask.add_or_update_chebi(compound)
                refmet_name = self.compoundtask.update_name_to_refmet(compound)
                kegg_id = self.compoundtask.add_or_update_kegg(compound, pubchem_cid=pubchem_cid)
                hmdb_id = self.compoundtask.add_or_update_hmdb(compound)
                lm_id = self.compoundtask.add_or_update_lipid_maps(compound)
                chembl_id = self.compoundtask.add_or_update_chembl(compound)
                self.compoundtask.add_or_update_classyfire(compound)
                self.logger.info("Compound added %s" % compound)
            except Exception as err:
                self.logger.exception("Compound import failed: %s" % err)
        else:
            self.logger.info("Compound found %s" % compound)

        annotation_compound = self.db_session.query(AnnotationCompound).filter(AnnotationCompound.harmonised_annotation_id==harmonised_annotation.id,
                                                                               AnnotationCompound.compound_id==compound.id).first()

        if not annotation_compound:
            annotation_compound = AnnotationCompound(harmonised_annotation_id=harmonised_annotation.id,
                                                    compound_id=compound.id)

            self.db_session.add(annotation_compound)
            self.db_session.flush()
            self.logger.info("AnnotationCompound added %s" % annotation_compound)
        else:
            self.logger.info("AnnotationCompound found %s" % annotation_compound)

        return annotation


    def parse_sample_information(self):
        """Parse sample information
        """        
        # 1. Loop over rows and add Subjects & Samples & MetadataFields and MetadataValues

        #'Source Name	Characteristics[Organism]	Term Source REF	Term Accession Number	Characteristics[Variant]	Term Source REF	Term Accession Number	Characteristics[Organism part]	Term Source REF	Term Accession Number	Protocol REF	Sample Name	Factor Value[Virus]	Term Source REF	Term Accession Number	Factor Value[Replicate]	Term Source REF	Term Accession Number'

        for row in self.sample_information_dataframe.iterrows():

            i = 0

            sample_name = None
            sample_type = 'experimental sample'
            sample_matrix = None
            ontology_refs = {}
            metadata_fields = {}

            while i < len(self.sample_information_dataframe.columns):

                col = self.sample_information_dataframe.columns[i]

                if re.search('Characteristics',col) or re.search('Factor Value',col):
                    splitted = col.split('[')
                    field_name = splitted[1].replace(']','')

                    ontology_refs[field_name] = {}
                    ontology_refs[field_name]['ref'] = row[1][self.sample_information_dataframe.columns[(i + 1)]]
                    ontology_refs[field_name]['accession'] = row[1][self.sample_information_dataframe.columns[(i + 2)]]

                    if field_name == 'Sample type':
                        sample_type = row[1][col]
                    elif field_name == 'Organism part':
                        sample_matrix = row[1][col]
                    else:
                        metadata_fields[field_name] = row[1][col]

                    i = i + 3

                else:
                    if col == 'Sample Name':
                        sample_name = str(row[1]['Sample Name'])

                    i = i + 1

            # 1. Get the correct sample_type enum value

            try:
                sample_type_enum = utils.get_npyc_enum_from_value(sample_type)
            except NotImplementedError:
                sample_type_enum = SampleType.StudySample

            # 2. Get or add the Subject (if QC sample, use that as name, otherwise use sample_name as Subject.name)
            subject = self.get_or_add_subject(sample_name,sample_type_enum)

            # 3. Get or add the Sample
            sample = self.get_or_add_sample(subject,sample_name,sample_type_enum,sample_matrix)

            for field_name,field_value in metadata_fields.items():
                self.get_or_add_metadata_field(field_name,field_value,sample)

    def get_or_add_subject(self,sample_name,sample_type_enum):
        """Get or add subject

        :param sample_name: Sample name
        :type sample_name: str
        :param sample_type_enum: Sample Type
        :type sample_type_enum: str
        :return: Subject
        :rtype: :class:`phenomedb.models.Subject`
        """        

        if sample_type_enum == SampleType.StudySample:
            subject_name = sample_name
        else:
            subject_name = sample_type_enum.value

        subject = self.db_session.query(Subject).filter(Subject.name == subject_name,
                                                            Subject.project_id == self.project.id).first()

        if not subject:
            subject = Subject(name=subject_name,
                              project_id=self.project.id)
            self.db_session.add(subject)
            self.db_session.flush()
            self.logger.info("Subject added %s" % subject)
        else:
            self.logger.info("Subject found %s" % subject)

        return subject

    def get_or_add_sample(self,subject,sample_name,sample_type_enum,sample_matrix):
        """Get or add Sample

        :param subject: Subject
        :type subject: :class:`phenomedb.models.Subject`
        :param sample_name: Sample name
        :type sample_name: str
        :param sample_type_enum: SampleType enum
        :type sample_type_enum: `SampleType`
        :param sample_matrix: Sample matrix
        :type sample_matrix: sample matrix
        :return: Sample
        :rtype: :class:`phenomedb.models.Sample`
        """        
        # Need to check what the sample_names, plus types of QC samples, and what their assay roles are

        sample = self.db_session.query(Sample).filter(Sample.subject_id==subject.id,
                                                                     Sample.name==sample_name).first()

        if not sample:
            if sample_type_enum == SampleType.StudySample:
                assay_role = AssayRole.Assay
            else:
                assay_role = None

            try:
                biological_tissue = Sample.get_biological_tissue(sample_matrix)
            except NotImplementedError as err:
                self.logger.exception(err)
                biological_tissue = None

            sample = Sample(name=sample_name,
                                           sample_type=sample_type_enum,
                                           assay_role=assay_role,
                                           sample_matrix=sample_matrix,
                                           biological_tissue=biological_tissue,
                                           subject_id=subject.id
                                           )
            self.db_session.add(sample)
            self.db_session.flush()
            self.logger.info("Sample added %s" % sample)
        else:
            self.logger.info("Sample added %s" % sample)

        return sample

    def get_or_add_metadata_field(self,field_name,field_value,sample):
        """Get or add metadata field

        :param field_name: The name of the metadata field
        :type field_name: str
        :param field_value: The value of the metadata field
        :type field_value: str
        :param sample: Sample
        :type sample: :class:`phenomedb.models.Sample`
        """        

        metadata_field = self.db_session.query(MetadataField).filter(MetadataField.project_id==self.project.id,
                                                                     MetadataField.name==field_name).first()

        if not metadata_field:
            metadata_field = MetadataField(name=field_name,
                                           project_id=self.project.id)
            self.db_session.add(metadata_field)
            self.db_session.flush()

        metadata_value = self.db_session.query(MetadataValue).filter(MetadataValue.metadata_field_id==metadata_field.id,
                                                                     MetadataValue.sample_id==sample.id).first()

        if not metadata_value:
            metadata_value = MetadataValue(metadata_field_id=metadata_field.id,
                                           sample_id=sample.id,
                                           raw_value=str(field_value)
                                           )
            self.db_session.add(metadata_value)
            self.db_session.flush()
            self.logger.info("MetadataValue added %s" % metadata_value)

        else:
            self.logger.info("MetadataValue found %s" % metadata_value)

    def parse_study_description(self):
        """Parse the study description
        """        

        persons = self.parse_persons()

        self.get_or_add_project(self.study_description_dict['STUDY']['Study Identifier'],
                                project_description=self.study_description_dict['STUDY']['Study Description'],
                                project_folder_name=None,
                                lims_id=None,
                                short_description=self.study_description_dict['STUDY']['Study Title'],
                                persons=persons)

        self.get_or_add_data_repository('Metabolights',
                                        accession_number=self.study_description_dict['STUDY']['Study Identifier'],
                                        submission_date=utils.get_date(self.study_description_dict['STUDY']['Study Submission Date']),
                                        public_release_date=utils.get_date(self.study_description_dict['STUDY']['Study Public Release Date']))

        self.parse_protocols()
        self.parse_publications()
        self.parse_assays()


    def parse_persons(self):
        """Parse the persons

        :return: person dict
        :rtype: dict
        """        

        persons = {}

        i = 0
        while i < len(self.study_description_dict['STUDY CONTACTS']['Study Person Email']):
            person_dict = {}
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person First Name']) > i:
                person_dict['first_name'] = self.study_description_dict['STUDY CONTACTS']['Study Person First Name'][i]
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person Last Name']) > i:
                person_dict['last_name'] = self.study_description_dict['STUDY CONTACTS']['Study Person Last Name'][i]
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person Affiliation']) > i:
                person_dict['affiliation'] = self.study_description_dict['STUDY CONTACTS']['Study Person Affiliation'][i]
            if len(self.study_description_dict['STUDY CONTACTS']['Study Person Roles']) > i:
                person_dict['role'] = self.study_description_dict['STUDY CONTACTS']['Study Person Roles'][i]
            persons[self.study_description_dict['STUDY CONTACTS']['Study Person Email'][i]] = person_dict
            i = i + 1

        return persons

    def get_or_add_data_repository(self,name,
                                   accession_number=None,
                                   submission_date=None,
                                   public_release_date=None):
        """Get or add repository

        :param name: Name of the repo
        :type name: str
        :param accession_number: accession number of repo, defaults to None
        :type accession_number: str, optional
        :param submission_date: Date of submission, defaults to None
        :type submission_date: `datetime.datetime`, optional
        :param public_release_date: Date of release, defaults to None
        :type public_release_date: `datetime.datetime`, optional
        :return: DataRepository
        :rtype: :class:`phenomedb.models.DataRepository`
        """        

        data_repository = self.db_session.query(DataRepository).filter(DataRepository.name==name,
                                                                       DataRepository.accession_number==accession_number).first()

        if not data_repository:

            data_repository = DataRepository(name=name,
                                             accession_number=accession_number,
                                             submission_date=submission_date,
                                             public_release_date=utils.get_date(public_release_date),
                                             project_id=self.project.id)
            self.db_session.add(data_repository)
            self.db_session.flush()
            self.logger.info("DataRepository added %s" % data_repository)
        else:
            self.logger.info("DataRepository found %s" % data_repository)

        return data_repository

    def parse_protocols(self):
        """Parse the protocols
        """        

        i = 0
        while i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Name']):


            name = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Name'][i]
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Type']):
                type = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Type'][i]
            else:
                type = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Description']):
                description = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Description'][i]
            else:
                description = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol URI']):
                uri = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol URI'][i]
            else:
                uri = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Version']):
                version = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Version'][i]
            else:
                version = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Parameters Name']):
                parameters = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Parameters Name'][i].split(';')
            else:
                parameters = None
            if i < len(self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Components Name']):
                components = self.study_description_dict['STUDY PROTOCOLS']['Study Protocol Components Name'][i].split(';')
            else:
                components = None

            self.get_or_add_protocol(name=name,
                                     type=type,
                                     description=description,
                                     uri=uri,
                                     version=version,
                                     parameters=parameters,
                                     components=components
                                     )

            i = i + 1

    def get_or_add_protocol(self,name=None,
                            type=None,
                            description=None,
                            uri=None,
                            version=None,
                            parameters=None,
                            components=None):
        """Get or add the protocol

        :param name: protocol name, defaults to None
        :type name: str, optional
        :param type: protocol type, defaults to None
        :type type: str, optional
        :param description: description, defaults to None
        :type description: str, optional
        :param uri: URI of the protocol, defaults to None
        :type uri: str, optional
        :param version: version of the protocol, defaults to None
        :type version: str, optional
        :param parameters: parameters of the protocol, defaults to None
        :type parameters: dict, optional
        :param components: components of the protocol, defaults to None
        :type components: dict, optional
        """

        protocol = self.db_session.query(Protocol).filter(Protocol.name==name,
                                                         Protocol.type==type).first()

        if not protocol:
            protocol = Protocol(name=name,
                                type=type,
                                description=description,
                                uri=uri,
                                version=version,
                                )
            self.db_session.add(protocol)
            self.db_session.flush()

            self.logger.info("Protocol added %s" % protocol)
        else:
            self.logger.info("Protocol found %s " % protocol)

        if isinstance(parameters,list):
            for parameter in parameters:
                if parameter != '':
                    protocol_parameter = self.db_session.query(ProtocolParameter).filter(ProtocolParameter.name==parameter,
                                                                                         ProtocolParameter.protocol_id==protocol.id).first()
                    if not protocol_parameter:
                        protocol_parameter = ProtocolParameter(name=parameter,protocol_id=protocol.id)
                        self.db_session.add(protocol_parameter)
                        self.db_session.flush()

                        self.logger.info("ProtocolParameter added %s" % protocol_parameter)
                    else:
                        self.logger.info("ProtocolParameter found %s " % protocol_parameter)

    def parse_publications(self):
        """Parse the publications
        """        

        i = 0
        while i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Title']):

            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study PubMed ID']):
                pubmed_id = self.study_description_dict['STUDY PUBLICATIONS']['Study PubMed ID'][i]
            else:
                pubmed_id = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication DOI']):
                doi = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication DOI'][i]
            else:
                doi = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Author List']):
                author_list = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Author List'][i]
            else:
                author_list = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Title']):
                title = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Title'][i]
            else:
                title = None
            if i < len(self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Status']):
                status = self.study_description_dict['STUDY PUBLICATIONS']['Study Publication Status'][i]
            else:
                status = None


            self.get_or_add_publication(pubmed_id=pubmed_id,
                                     doi=doi,
                                     author_list=author_list,
                                     title=title,
                                     status=status,
                                     )
            i = i + 1

    def get_or_add_publication(self,pubmed_id=None,doi=None,author_list=None,title=None,status=None):
        """Get or add publication

        :param pubmed_id: pubmed id, defaults to None
        :type pubmed_id: int, optional
        :param doi: DOI, defaults to None
        :type doi: str, optional
        :param author_list: List of authors, defaults to None
        :type author_list: list, optional
        :param title: publication title, defaults to None
        :type title: str, optional
        :param status: Publication status, defaults to None
        :type status: str, optional
        """        

        publication = self.db_session.query(Publication).filter(Publication.title==title,
                                                                Publication.doi==doi,
                                                                Publication.project_id==self.project.id).first()

        if not publication:
            publication = Publication(pubmed_id=pubmed_id,
                                      doi=doi,
                                      author_list=author_list,
                                      title=title,
                                      status=status,
                                      project_id=self.project.id)
            self.db_session.add(publication)
            self.db_session.flush()
            self.logger.info("Publication added %s" % publication)
        else:
            self.logger.info("Publication found %s" % publication)

    def parse_assays(self):
        """Parse the assays
        """        

        self.assays = {}

        i = 0
        while i < len(self.study_description_dict['STUDY ASSAYS']['Study Assay File Name']):
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay File Name']) > i:
                study_assay_file_name = self.study_description_dict['STUDY ASSAYS']['Study Assay File Name'][i]
            else:
                study_assay_file_name = None
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay Measurement Type']) > i:
                measurement_type = self.study_description_dict['STUDY ASSAYS']['Study Assay Measurement Type'][i]
            else:
                measurement_type = None
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Type']) > i:
                long_platform = self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Type'][i]
            else:
                long_platform = None
            if len(self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Platform']) > i:
                long_name = self.study_description_dict['STUDY ASSAYS']['Study Assay Technology Platform'][i]
            else:
                long_name = None

            if 'targeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS']['Study Design Type'] and\
                'untargeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS']['Study Design Type']:
                raise Exception("Both targeted and untargeted assays exist, please specify which is which in the task parameters")
            elif 'targeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS']['Study Design Type']:
                targeted = 'Y'
            elif 'untargeted_metabolites' in self.study_description_dict['STUDY DESIGN DESCRIPTORS']['Study Design Type']:
                targeted = 'N'
            else:
                targeted = None

            assay = self.db_session.query(Assay).filter(or_(Assay.name==long_name,
                                                                 Assay.long_name==long_name)).first()

            if not assay:

                assay = Assay(name=long_name,
                                   long_platform=long_platform,
                                   long_name=long_name,
                                   measurement_type=measurement_type,
                              targeted=targeted
                                   )
                assay.set_platform_from_long_platform(long_platform)

                self.db_session.add(assay)
                self.db_session.flush()
                self.logger.info('Assay added %s' % assay)
            else:
                self.logger.info('Assay found %s' % assay)

            self.assays[study_assay_file_name] = assay

            i = i + 1

class ImportMetadata(ImportTask):
    """Import Metadata from a CSV file where rows are samples and columns are metadata fields.

    :param project_name: The name of the Project, defaults to None
    :type project_name: str, optional
    :param filepath: The path to the CSV file, defaults to None
    :type filepath: str, optional
    :param id_column: The column name of the ID field, defaults to None
    :type id_column: str, optional
    :param id_type: Are the IDs for Subject or Sample?, defaults to 'Sample'
    :type id_type: str, optional
    :param columns_to_import: Which columns to import, defaults to None
    :type columns_to_import: list, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param validate: Whether to run validation, default True
    :type validate: boolean
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional
    """

    def __init__(self,project_name=None,filepath=None,id_column=None,id_type='Sample',columns_to_import=None,
                    username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None):
        
        super().__init__(project_name=project_name,username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)

        self.filepath = filepath
        self.args['filepath'] = filepath

        if id_type:
            self.id_type = id_type

        self.args['id_type'] = id_type

        if id_column:
            self.id_column = id_column
        else:
            self.id_column = 'Sample ID'

        self.args['id_column'] = id_column

        if columns_to_import:
            self.columns_to_import = columns_to_import
        else:
            self.columns_to_import = ['BMI_cont','ethnicity_sure','HOUSE_SINCE_EAT_BLOOD','PARTICIPANT_REGION','centre']

        self.args['columns_to_import'] = columns_to_import

        self.get_class_name(self)

    def load_dataset(self):
        """Load the dataset
        """

        self.dataset = self.load_tabular_file(self.filepath)

    def map_and_add_dataset_data(self):
        """Parse the dataset

        :raises Exception: Unknown id_type (must be Sample or Subject)
        """

        i=0
        while i < self.dataset.shape[0]:

            name = self.dataset.loc[i, self.id_column]

            samples = []

            if self.id_type == 'Sample':

                samples = self.db_session.query(Sample).join(Subject).filter(Sample.name==str(name),
                                                                            Subject.project_id==self.project.id).all()

                if len(samples) == 0:
                    self.logger.info("No matching samples %s" % name)
                    i = i + 1
                    continue

            elif self.id_type == 'Subject':
                samples = self.db_session.query(Sample).join(Subject).filter(Subject.name == str(name),
                                                                             Subject.project_id == self.project.id).all()

                if len(samples) == 0:
                    self.logger.info("No matching samples %s" % name)
                    i = i + 1
                    continue

            else:
                raise Exception("Unknown id_type %s" % self.id_type)

            p = 1
            while p < self.dataset.shape[1]:

                field_name = self.dataset.columns[p].strip()

                if field_name in self.columns_to_import and field_name != self.id_column:

                    field_value = self.dataset.iloc[i,p]
                    if field_value:
                        field_value = str(field_value).strip()

                    for sample in samples:
                        self.add_metadata_field_and_value(sample.id,field_name,field_value)

                p = p + 1

            i = i + 1