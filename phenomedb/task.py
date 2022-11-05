import distutils.command.config
from abc import abstractmethod, ABC
import phenomedb.database as db
import logging
import pandas as pd
from pathlib import Path
import os
import math
import numpy as np
from nPYc.enumerations import *
from phenomedb.models import *
import os
import datetime
import redis
from phenomedb.config import config
from phenomedb.exceptions import *
import time

class Task(ABC):
    """Base Task class.

    :param ABC: abstract base class
    :type ABC: :class:`abc.ABC`
    :raises Exception: Raised when tabular file is not of correct type (xlsx,xls,csv,tsv)
    :return: The Task class.
    :rtype: :class:`phenomedb.task.Task`
    """

    output = {}
    saved_output = {}
    validation_failures = []
    username = None
    db_session = None
    pipeline_id = None
    saved_query_id = None
    saved_query = None
    class_name = None
    module_name = None
    task_run = None
    reset_generate_cache_on_fail = False
    output_model = None
    harmonised_dataset_id = None
    class_type = None
    class_level = None
    aggregate_function = None
    run_batch_correction = False
    upstream_task_run_id = None

    def __init__(self,task_run_id=None,pipeline_run_id=None,username=None,db_env=None,db_session=None,execution_date=None,
                 validate=True,upstream_task_run_id=None,debug=False):
        from phenomedb.cache import Cache
        self.logger = logging.getLogger("airflow.task")
        self.cache = Cache()
        self.task_run_id = task_run_id
        self.pipeline_run_id = pipeline_run_id
        self.username = username
        self.execution_date = execution_date
        self.upstream_task_run_id = upstream_task_run_id
        if db_env:
            self.db_env = db_env
        else:
            self.db_env = 'PROD'
        if db_session:
            self.db_session = db_session
        self.validate = validate
        self.debug = debug
        self.args = {'task_run_id':task_run_id,
                     'pipeline_run_id':pipeline_run_id,
                     'execution_date': execution_date,
                     'username':username,
                     'db_env':db_env,
                     'validate':validate,
                     'debug': debug,
                     'upstream_task_run_id':upstream_task_run_id}
        self.validation_failures = []
        self.data = {}
        self.rerun_task = False     # overwritten in start_task_run if output exists and task_run_id is set
        self.task_run_output = None

    def get_class_name(self,instance):
        """Get the name of the class from the instance.

        :param instance: The instance of the class.
        :type instance: :class:`phenomedb.task.Task`
        :return: The class name.
        :rtype: str
        """
        self.module_name = instance.__module__
        self.class_name = instance.__class__.__name__
        return self.class_name

    def reset_generate_cache(self):

        if self.saved_query_id and self.reset_generate_cache_on_fail and self.output_model:
            saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==self.saved_query_id).first()
            if saved_query.cache_state:
                cache_state = dict(saved_query.cache_state)
            else:
                cache_state = {}
            from phenomedb.query_factory import QueryFactory
            query_factory = QueryFactory(saved_query_id=self.saved_query_id,db_env=self.db_env)
            key = query_factory.get_dataframe_key(type='combined',model=self.output_model,correction_type=self.correction_type,
                                                     aggregate_function=self.aggregate_function,
                                                     class_type=self.class_type,class_level=self.class_level,db_env=self.db_env)
            if saved_query and key in cache_state and cache_state[key] == 'generating':
                del cache_state[key]
                self.db_session.flush()
                self.logger.info("Key %s removed from SavedQuery.cache_state %s" % (key,cache_state))

    def clean_project_name(self,project_name):
        """Clean the project name (lower and replace hypens (-) with underscores (_))

        :param project_name: The name of the project.
        :type project_name: str
        :return: The cleaned the project name.
        :rtype: str
        """

        return project_name.lower().replace("-","_")


    def load_tabular_file(self,file,sheet_name=0,dtype=None,header='infer',na_values=None,replace_na_with_none=True,strip_whitespace=True):
        """Load a tabular file into a pandas dataframe. Works with xlsx, xls, csv, tsv, and txt files.

        :param file: The file (and path) to open.
        :type file: str
        :param sheet_name: The name of the sheet to open (xlsx and xls), defaults to 0.
        :type sheet_name: int, optional
        :param dtype: The column types of the file (pandas dtypes), defaults to None.
        :type dtype: object, optional
        :raises Exception: Raises if not xlsx, xls, csv, tsv, or txt.
        :return: The created pandas dataframe.
        :rtype: :class:`pd.Dataframe`
        """

        path = str(Path(file).absolute())
        self.logger.info("Loading file :: Path: %s \n :: Arguments :: file=%s, sheet_name=%s,\n dtype=%s \n header=%s,na_values=%s,replace_na_with_none=%s" % (path,file,sheet_name,dtype,header,na_values,replace_na_with_none))

        filename, file_extension = os.path.splitext(path)

        if file_extension.lower() == '.xls':
            dataframe = pd.read_excel(path,engine="xlrd",sheet_name=sheet_name, dtype=dtype,na_values=na_values)

        elif file_extension.lower() == '.xlsx':
            dataframe = pd.read_excel(path,engine="openpyxl",sheet_name=sheet_name, dtype=dtype,na_values=na_values)

        elif file_extension.lower() == '.csv':
            dataframe = pd.read_csv(path,dtype=dtype,header=header,na_values=na_values)

        elif file_extension.lower() == '.tsv':
            dataframe = pd.read_csv(path,dtype=dtype,sep='\t',header=header,na_values=na_values)

        elif file_extension.lower() == '.txt':
            dataframe = pd.read_csv(path,dtype=dtype,sep='\t',header=header)

        else:
            raise Exception('File extension not XLS or XLSX or CSV or TSV')

        # Remove all fully empty rows
        if not na_values:
            dataframe.dropna(how="all", inplace=True)

        if replace_na_with_none:
            dataframe = dataframe.where(pd.notnull(dataframe),None)

        if strip_whitespace:
            dataframe.rename(columns=lambda x: x.strip() if isinstance(x, str) else x, inplace=True)

        self.logger.info("Dataset loaded: %s \n Shape: %s \n Head: %s \n Columns: %s" % (filename,dataframe.head(),dataframe.shape,dataframe.columns))

        return dataframe

    def log_info(self,message):
        """Add the info log and print.

        :param message: The message to log.
        :type message: str
        """

        self.logger.info(str(message))
        #print(str(message))

    @abstractmethod
    def process(self):
        pass

    def task_validation(self):
        pass


    def get_db_size(self,pretty=False):

        db_name = self.get_db_name()

        if not pretty:
            sql = "SELECT pg_database_size('%s');" % db_name
        else:
            sql = "SELECT pg_size_pretty( pg_database_size('%s') );" % db_name

        result = self.db_session.execute(sql, None).fetchall()

        self.logger.info("DB size: %s" % result[0][0])

        return result[0][0]

    def get_db_name(self):

        if self.db_env and self.db_env == "TEST":
            return config['DB']['test']
        elif self.db_env and self.db_env == "BETA":
            return config['DB']['beta']
        else:
            return config['DB']['name']


    def start_benchmarks(self):

        self.task_run.db_size_start = self.get_db_size()
        self.get_db_size(pretty=True)
        #self.task_run.memory_start =

#    def read_benchmarks(self):

#        time_start = time.time()
#        sql = "select * from v_read_benchmark"
#        self.db_session.execute(sql)
#        time_end = time.time()
#        self.task_run.sql_benchmark = time_end - time_start

#        time_start = time.time()
#        self.db_session.query(AnnotatedFeature).join(SampleAssay,Sample,MetadataValue,MetadataField,Subject,Project,FeatureMetadata,
#                                                     Annotation,AnnotationCompound,Compound,CompoundClassCompound,CompoundClass,
#                                                     CompoundExternalDB,ExternalDB).all()
#        time_end = time.time()
#        self.task_run.sql_alchemy_benchmark = time_end - time_start

    def end_benchmarks(self):

        self.task_run.db_size_end = self.get_db_size()
        self.task_run.db_size_bytes = self.task_run.db_size_end - self.task_run.db_size_start
        self.task_run.db_size_megabytes = self.task_run.db_size_bytes / 1000
        self.get_db_size(pretty=True)

    def check_field(self,field_name,id,actual,expected):

        if actual and expected:
            if type(actual).__module__ == np.__name__:
                actual = actual.item()
            if type(actual) != type(expected):
                # This is because we often cast numerics to different types in the models.
                if utils.is_number(actual) and utils.is_number(expected):
                    pass
                else:
                    raise ValidationError("%s has different type, %s: Actual: %s type(%s) != Expected: %s type(%s)" % (field_name,id,actual,type(actual),expected,type(expected)))
            else:
                if isinstance(expected,str):
                    expected = expected.strip()
                if actual != expected:
                    raise ValidationError("%s has different value, %s: Actual: %s != Expected: %s" % (field_name,id,actual,expected))

        elif actual and not expected:
            raise ValidationError('%s has imported unexpectedly, %s: Actual: %s != Expected: %s' % (field_name,id,actual,expected))
        elif expected and not actual:
            if isinstance(expected,str) and expected.strip() not in ['-','nan','None']:
                raise ValidationError('%s has not imported, %s: Actual: %s != Expected: %s' % (field_name,id,actual,expected))

    def get_db_session(self,db_env=None,db_session=None):

        if db_env:
            self.db_env = db_env
        else:
            self.db_env = 'PROD'

        if db_session:
            self.db_session = db_session
        else:
            self.db_session = db.get_db_session(db_env=db_env)

    def run(self):
        """Run the task. You must implement the process method in your inherited class.

        """
        self.get_db_session(db_env=self.db_env)

        self.start_task_run()

        try:

            self.process()
            
            if self.validate:
                self.task_validation()
                self.logger.info("Validation passed")
            else:
                self.logger.info("No validation")

            self.save_task_run(TaskRun.Status.success)
            self.post_commit_actions()
            if not isinstance(self.task_run.output, dict):
                self.task_run.output = {}

        except ValidationError as err:
            self.task_run.output = {'validation_error':err}
            self.logger.exception(err)
            self.logger.exception("!!! %s Validation failed : Items have not been committed to the DB : Please investigate further: %s" % (self.class_name,err))
            self.db_session.rollback()
            self.reset_generate_cache()
            self.save_task_run(TaskRun.Status.error)
            self.send_user_failure_email(err)
            if not isinstance(self.task_run.output, dict):
                self.task_run.output = {}
            raise Exception(err)

        except Exception as err:

            self.task_run.output = {'error':err}
            self.logger.exception(err)
            self.logger.exception("!!! Exception encountered : Items have not been committed to the DB : Please investigate further: %s" % err)
            self.db_session.rollback()
            self.reset_generate_cache()
            self.save_task_run(TaskRun.Status.error)
            self.send_user_failure_email(err)
            self.reset_generate_cache()
            if not isinstance(self.task_run.output, dict):
                self.task_run.output = {}
            raise Exception(err)

        self.simple_report()
        self.send_user_success_email()

        if self.cache.exists(self.task_run.get_task_output_cache_key()):
            self.logger.info('output: %s' % self.task_run.get_task_output(self.cache))
            return self.task_run.get_task_output(self.cache)
        else:
            self.logger.info('output: %s' % self.task_run.output)
            return self.task_run.output

    def post_commit_actions(self):
        pass

    def start_task_run(self):

        if self.task_run_id:

            self.task_run = self.db_session.query(TaskRun).filter(TaskRun.id==self.task_run_id).first()
            key = 'analysis_view_table_row_%s' % self.task_run_id
            if self.cache.exists(key):
                self.cache.delete(key)
                self.logger.info("analysis_view_table_row_%s deleted" % self.task_run_id)

            if self.cache.exists(self.task_run.get_task_output_cache_key()):
                self.cache.delete(self.task_run.get_task_output_cache_key())
                self.logger.info("%s deleted" % self.task_run.get_task_output_cache_key())

        if not self.task_run:

            self.task_run = TaskRun(pipeline_id=self.pipeline_id,
                               datetime_started=datetime.datetime.now(),
                                execution_date=self.execution_date,
                               username=self.username,
                              args = utils.convert_to_json_safe(self.args),
                               module_name=self.module_name,
                               class_name=self.class_name,
                               upstream_task_run_id=self.upstream_task_run_id,
                               status=TaskRun.Status.started,
                               pipeline_run_id=self.pipeline_run_id,
                               saved_query_id=self.saved_query_id,
                               db_env=self.db_env)
            self.db_session.add(self.task_run)
            self.db_session.flush()

        else:
            self.logger.info("Existing TaskRun.args %s" % self.task_run.args)
            self.task_run.args = utils.convert_to_json_safe(dict(self.args))
            self.logger.info("Updated TaskRun.args %s" % self.task_run.args)
            self.task_run.saved_query_id = self.saved_query_id
            self.task_run.execution_date = self.execution_date
            self.task_run.status = TaskRun.Status.started
            self.task_run.datetime_started = datetime.datetime.now()
            self.db_session.flush()

        self.start_benchmarks()
        self.db_session.commit()
        self.logger.info("self.args %s" % self.args)
        self.logger.info("TaskRun.args %s" % self.task_run.args)
        self.logger.info("TaskRun: %s %s" % (self.task_run.id, self.task_run.for_log()))


    def save_task_run(self,status):

        self.task_run.datetime_finished = datetime.datetime.now()
        self.task_run.run_time = (self.task_run.datetime_finished - self.task_run.datetime_started).total_seconds()
        self.task_run.status = status
        self.task_run.output = utils.convert_to_json_safe(self.clean_data_for_jsonb(self.saved_output))
        self.cache.set(self.task_run.get_task_output_cache_key(),self.task_run.output)
        self.task_run.output = None

        if self.saved_query:
            self.task_run.saved_query_id = self.saved_query.id
        if 'saved_query_id' in self.args.keys() and self.args['saved_query_id'] is not None:
            self.task_run.saved_query_id = self.args['saved_query_id']

        self.db_session.commit()

        self.end_benchmarks()

        self.db_session.commit()

        self.logger.info("TaskRun: %s" % self.task_run.for_log())

        utils.clear_task_view_cache(self.task_run.id)

        if status == TaskRun.Status.success and not self.run_batch_correction \
                and self.class_name in []:#'ImportBrukerIVDRAnnotations',
                                        #'ImportPeakPantherAnnotations',
                                        #'ImportTargetLynxAnnotations']:
            from phenomedb.pipeline_factory import PipelineFactory
            pipeline_factory = PipelineFactory(pipeline_name='CreateSavedQueryDataframeCache',db_env=self.db_env)
            if utils.clean_task_id(
                    'CreateSavedQuerySummaryStatsCache') in pipeline_factory.pipeline_manager.pipeline.definition.keys():
                pipeline_factory.run_pipeline(
                    run_config={
                        utils.clean_task_id('CreateSavedQueryDataframeCache'):{'saved_query_id':self.saved_query.id,
                                                                               'output_model':"AnnotatedFeature"}})
                self.logger.info("SavedQueryDataframeCache pipeline triggered")
            else:
                self.logger.info("SavedQueryDataframeCache pipeline has no definition!")

            pipeline_factory = PipelineFactory(pipeline_name='CreateSavedQuerySummaryStatsCache',db_env=self.db_env)
            if utils.clean_task_id('CreateSavedQuerySummaryStatsCache') in pipeline_factory.pipeline_manager.pipeline.definition.keys():
                pipeline_factory.run_pipeline(
                    run_config={
                        utils.clean_task_id('CreateSavedQuerySummaryStatsCache'): {'saved_query_id': self.saved_query.id}})
                self.logger.info("CreateSavedQuerySummaryStatsCache pipeline triggered")
            else:
                self.logger.info("CreateSavedQuerySummaryStatsCache pipeline has no definition!")


    def clean_data_for_jsonb(self,data,current_depth=0,max_depth=2):

        if current_depth >= max_depth:
            return data

        if isinstance(data, np.ndarray):
            data = np.nan_to_num(data)
            data = data.tolist()

        elif isinstance(data,pd.DataFrame):
            data = data.where(pd.notnull(data), None)
            data = data.to_dict()

        elif isinstance(data,dict):
            for key, value in data.items():
                data[key] = self.clean_data_for_jsonb(data[key],current_depth=current_depth+1,max_depth=max_depth)

        elif isinstance(data,list):
            i = 0
            for value in data:
                data[i] = self.clean_data_for_jsonb(value,current_depth=current_depth+1,max_depth=max_depth)
                i = i + 1
        else:
            try:
                if np.isinf(data) or np.isnan(data):
                    data = None
            except:
                pass

        return data



    def send_user_failure_email(self,err):

        if self.username and self.db_env != 'TEST':

            email = self.username + "@ic.ac.uk"
            subject = 'PhenomeDB Task failed: %s %s' % (self.db_env, self.class_name)
            body = "PhenomeDB Task failed: %s %s %s %s" % (self.db_env,self.class_name, self.task_run.args, err)

            try:
                utils.send_tls_email(email,subject,body)
            except Exception:
                self.logger.warning("Email failed")

    def send_user_success_email(self):

        if self.username and self.db_env != 'TEST':

            email = self.username + "@ic.ac.uk"
            subject = 'PhenomeDB Task successful: %s %s' % (self.db_env, self.class_name)
            body = "PhenomeDB Task successful: %s %s %s %s" % (self.db_env, self.class_name, self.task_run.args, self.output)

            try:
                utils.send_tls_email(email,subject,body)
                self.logger.info('sent email to %s' % email)
            except Exception:
                self.logger.warning("Email failed")

    def clear_saved_query_cache(self):

        saved_queries = self.db_session.query(SavedQuery).all()
        #for saved_query in saved_queries:

        #    if self.cache.exists(saved_query.get_cache_dataframe_key()):
        #        self.cache.delete(saved_query.get_cache_dataframe_key())
        #    if self.cache.exists(saved_query.get_cache_summary_stats_key()):
        #        self.cache.delete(saved_query.get_cache_summary_stats_key())

        self.logger.info("All SavedQueryDataframe and SavedQuerySummaryStats caches deleted")

    def simple_report(self):

        pass

    def get_or_add_harmonised_field(self,field_name,unit,datatype):
        """Gets or adds a project to the database (by project_name)
        """
        self.harmonised_metadata_field = self.db_session.query(HarmonisedMetadataField).filter(HarmonisedMetadataField.name==field_name).first()

        if not self.harmonised_metadata_field:

            self.harmonised_metadata_field = HarmonisedMetadataField(name=field_name,
                                                                unit_id=unit.id,
                                                                datatype = datatype)

            self.db_session.add(self.harmonised_metadata_field)
            self.db_session.flush()
        self.logger.info("Added/found %s" % self.harmonised_metadata_field)
        return self.harmonised_metadata_field

    def get_or_add_laboratory(self,lab_name,lab_affiliation=None):
        """Gets or adds a project to the database (by project_name)
        """
        self.lab = self.db_session.query(Laboratory).filter(Laboratory.name==lab_name).first()

        if not self.lab:

            self.lab = Laboratory(name=lab_name,
                             affiliation = lab_affiliation)

            self.db_session.add(self.lab)
            self.db_session.flush()

        self.logger.info("Added/found %s" % self.lab)

        return self.lab

    def get_or_add_annotation_method(self,annotation_method_name,description=None):
        """Gets or adds a project to the database (by project_name)
        """
        self.annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name==annotation_method_name).first()

        if not self.annotation_method:

            self.annotation_method = AnnotationMethod(name=annotation_method_name,
                                                    description = description)

            self.db_session.add(self.annotation_method)
            self.db_session.flush()

        self.logger.info("Added/found %s" % self.annotation_method)

        return self.annotation_method

    def get_or_add_assay(self,assay_name,platform=None,targeted=None,ms_polarity=None,long_name=None,long_platform=None,quantification_type=None):
        """Gets or adds a project to the database (by project_name)
        """
        self.assay = self.db_session.query(Assay).filter(Assay.name==assay_name).first()

        if not self.assay:

            self.assay = Assay(name=assay_name,
                              platform = platform,
                              targeted = targeted,
                              ms_polarity = ms_polarity,
                              long_name=long_name,
                              long_platform=long_platform,
                               quantification_type=quantification_type)

            if long_platform and not platform:
                self.assay.set_platform_from_long_platform(long_platform)

            self.db_session.add(self.assay)
            self.db_session.flush()

        self.logger.info("Added/found %s" % self.assay)

        return self.assay

    def get_or_add_project(self,project_name,project_description=None,project_folder_name=None,lims_id=None,
                           short_description=None,persons=None,laboratory_id=None):
        """Gets or adds a project to the database (by project_name)
        """
        self.project = self.db_session.query(Project).filter(Project.name==project_name).first()

        if not self.project:

            self.project = Project(name=project_name,
                                  description=project_description,
                                  project_folder_name=project_folder_name,
                                  lims_id=lims_id,
                                  date_added=datetime.datetime.now(),
                                    short_description=short_description,
                                    persons=persons,
                                   laboratory_id=laboratory_id
                                   )

            self.db_session.add(self.project)
            self.db_session.flush()
            self.logger.info("Project Added %s" % self.project)
        else:
            self.logger.info("Project Found %s %s" % (self.project,self.project.getCounts()))

        return self.project

    def get_assay(self):

        if hasattr(self,'assay_name'):

            if self.assay_name:
                self.assay = self.db_session.query(Assay).filter(Assay.name==self.assay_name).first()

            if not self.assay:
                raise Exception("Unknown assay name: " + self.assay_name)
        else:
            raise Exception('No self.assay_name')

    def get_or_add_unit(self, unit_name,unit_description=None):
        """Gets or adds a unit to the database (by unit name)
        """

        if not unit_description:
            unit_description = unit_name

        self.unit = self.db_session.query(Unit).filter(Unit.name == unit_name).first()

        if not self.unit:
            self.unit = Unit(name=unit_name,
                        description=unit_description)

            self.db_session.add(self.unit)
            self.db_session.flush()

        self.logger.debug("Added/found %s" % self.unit)

        return self.unit

class CreateUnit(Task):

    def __init__(self,unit_name=None,unit_description=None,task_run_id=None,username=None,db_env=None):
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env)
        self.unit_name = unit_name
        self.unit_description = unit_description

    def process(self):

        self.get_or_add_unit(self.unit_name,unit_description=self.unit_description)

class CreateProject(Task):

    """ImportNewProjectTask: Imports a new project
    """
    def __init__(self,project_name=None,description=None,project_folder_name=None,lims_id=None,task_run_id=None,username=None,db_env=None):
        """Constructor method
        """
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env)

        self.project_name = project_name,
        self.description = description
        self.project_folder_name = project_folder_name
        self.lims_id = lims_id
        self.args['project_name'] = project_name
        self.args['description'] = description
        self.args['project_folder_name'] = project_folder_name
        self.args['lims_id'] = lims_id

        self.get_class_name(self)

    def process(self):

        self.get_or_add_project(self.project_name,project_description=self.description,project_folder_name=self.project_folder_name,lims_id=self.lims_id)


class CreateLab(Task):

    """CreateAssay: Creates an Assay
    """
    def __init__(self,lab_name=None,lab_affiliation=None,task_run_id=None,username=None,db_env=None):
        """Constructor method
        """
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env)

        self.lab_name = lab_name
        self.lab_affiliation = lab_affiliation
        self.args['lab_name'] = lab_name
        self.args['lab_affiliation'] = lab_affiliation

        self.get_class_name(self)


    def process(self):

        self.get_or_add_laboratory(self.lab_name,lab_affiliation=self.lab_affiliation)



class CreateAssay(Task):

    """CreateAssay: Creates an Assay
    """
    def __init__(self,assay_name=None,platform=None,targeted=None,
                 ms_polarity=None,laboratory_name=None,long_name=None,
                 long_platform=None,task_run_id=None,username=None,db_env=None):
        """Constructor method
        """
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env)

        self.assay_name = assay_name
        self.platform = platform
        self.targeted = targeted
        self.ms_polarity = ms_polarity
        self.long_name = long_name
        self.long_platform = long_platform
        self.laboratory_name = laboratory_name

        self.args['assay_name'] = assay_name
        self.args['platform'] = platform
        self.args['targeted'] = targeted
        self.args['ms_polarity'] = ms_polarity
        self.args['laboratory_name'] = laboratory_name
        self.args['long_name'] = long_name
        self.args['long_platform'] = long_platform

        self.get_class_name(self)


    def process(self):

        self.get_or_add_assay(self.assay_name,platform=self.platform,targeted=self.targeted,ms_polarity=self.ms_polarity)

class CreateAnnotationMethod(Task):

    """CreateAnnotationMethod: Creates an AnnotationMethod
    """
    def __init__(self,annotation_method_name=None,description=None,task_run_id=None,username=None,db_env=None):
        """Constructor method
        """
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env)

        self.annotation_method_name = annotation_method_name
        self.description = description

        self.args['annotation_method_name'] = annotation_method_name
        self.args['description'] = description

        self.get_class_name(self)

    def process(self):

        self.get_or_add_annotation_method(self.annotation_method_name,description=self.description)

class CreateHarmonisedMetadataField(Task):

    unit = None

    def __init__(self,name=None,unit_name=None,datatype=None,unit_description=None,task_run_id=None,username=None,db_env=None,db_session=None,execution_date=None):
        """Constructor method
        """
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,execution_date=execution_date)

        self.name = name
        self.unit_name = unit_name
        self.datatype = datatype
        self.unit_description = unit_description

        self.args['name'] = name
        self.args['unit_name'] = unit_name
        self.args['datatype'] = datatype
        self.args['unit_description'] = unit_description

        self.get_class_name(self)


    def process(self):

        self.get_or_add_unit(self.unit_name,self.unit_description)
        self.get_or_add_harmonised_field(self.name,self.unit,self.datatype)



class ManualSQL(Task):

    def __init__(self,sql_file=None,username=None,task_run_id=None,db_env=None):

        if sql_file:
           self.sql_file = sql_file

        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env)

    def process(self):

        self.logger.info("Running manual SQL File: %s" % self.sql_file)
        sqh = open(self.sql_file,'r')
        text = sqh.read()
        sqh.close()

        if self.db_env == 'TEST':
            engine = db.test_engine
        elif self.db_env == 'BETA':
            engine = db.beta_engine
        else:
            engine = db.prod_engine

        for statement in text.split(";"):
            if statement != '':
                self.logger.info("SQL to be executed: %s" % statement)
                result = engine.execute(statement)
                self.logger.info("SQL Result: %s" % result)