# Add phenomedb to path if not already
from pathlib import Path
import sys
import time
import datetime
import os
from phenomedb.config import config
import phenomedb.utilities as utils
from phenomedb.database import *
from phenomedb.models import *
from phenomedb.exceptions import *
import re
import json
import inspect as isp
import importlib


class BasePipelineManager:
    """
        Abstract BasePipeline class. Extend this class to use another offline worker system, ie RedisQueue.

        add_task() and submit() must be implemented.

    """

    logger = utils.configure_logging(identifier="pipeline_factory")
    pipeline = None

    def __init__(self,pipeline_name=None,db_env=None,db_session=None,pipeline_id=None):
        """Abstract BasePipeline class. 
        
        Extend this class to use another offline worker system, ie RedisQueue.

        add_task() and submit() must be implemented.

        :param pipeline_name: The name of Pipeline, defaults to None
        :type pipeline_name: str, optional
        :param db_env: The DB to use, 'PROD' or 'TEST', defaults to None
        :type db_env: str, optional
        :param db_session: The DB session to use, defaults to None
        :type db_session: object, optional
        :param pipeline_id: The Pipeline ID, defaults to None
        :type pipeline_id: str, optional
        :raises Exception: Pipeline ID not recognised
        :raises Exception: Pipeline name and Pipeline ID do not match
        """

        #self.name = (name + "_" + str(datetime.datetime.now()).replace('-','').replace(':','').replace('.','_')).replace(' ','_')
        if db_env and db_env != 'PROD':
            self.db_env = db_env
        else:
            self.db_env = 'PROD'

        if db_session:
            self.db_session = db_session
        else:
            self.db_session = get_db_session(db_env=self.db_env)

        self.pipeline_id = pipeline_id
        if pipeline_id:
            self.pipeline = self.db_session.query(Pipeline).filter(Pipeline.id==pipeline_id).first()
            if not self.pipeline:
                raise Exception("Pipeline ID not recognised")
        elif pipeline_name:
            if self.db_session.query(Pipeline).filter(Pipeline.name==pipeline_name).count() > 0:
                self.pipeline = self.db_session.query(Pipeline).filter(Pipeline.name==pipeline_name).first()
        else:
            self.pipeline = None

        if pipeline_id and pipeline_name and self.pipeline.name != pipeline_name:
            raise Exception("Pipeline name and Existing Pipeline ID do not match %s %s %s" % (pipeline_id,pipeline_name,self.pipeline.name))

        self.task_runs = {}

    def add_task(self,task_module,task_class,task_id=None,run_config=None,upstream_task_id=None):
        """Add a task to the pipeline, either with a run_config for the task or not, and with an upstream_task_id or not.

        :param task_module: The module of the task, eg. 'phenomedb.imports'
        :type task_module: str
        :param task_class: The class of the task eg. 'ImportMetadata'
        :type task_class: str
        :param task_id: The unique identifier for the task in the pipeline, defaults to None
        :type task_id: str, optional
        :param run_config: The run_config for the task, e.g. dictionary of {task_id:**kwargs}, defaults to None
        :type run_config: dict, optional
        :param upstream_task_id: The ID of the upstream task, defaults to None
        :type upstream_task_id: str, optional
        :raises PipelineTaskIDError: Another task with that ID already exists
        :raises PipelineTaskIDError: Task ID cannot start with a number
        :raises PipelineTaskIDError: Upstream task with that ID does not exist
        :return: _description_
        :rtype: _type_
        """

        if self.pipeline:

            if task_id and utils.clean_task_id(task_id) in self.pipeline.definition.keys():
                raise PipelineTaskIDError('Another Task with that ID already exists in the pipeline %s' % task_id)
            elif task_id and re.match('^[0-9]',task_id):
                raise PipelineTaskIDError('Task ID cannot start with a number %s' % task_id)
            elif not task_id:
                dt = datetime.datetime.now()
                task_id = utils.clean_task_id(task_class) + "_" + str(dt.second) + str(dt.microsecond)
            else:
                task_id = utils.clean_task_id(task_id)

            pipeline_definition = dict(self.pipeline.definition)
            pipeline_definition[task_id] = {'task_module':task_module,
                                            'task_class':task_class}
            self.pipeline.definition = pipeline_definition
            task_order = list(self.pipeline.task_order)
            if upstream_task_id:
                if upstream_task_id not in task_order:
                    raise PipelineTaskIDError('Upstream task with task_id %s does not exist' % upstream_task_id)
                else:
                    task_order.insert(task_order.index(upstream_task_id)+1,task_id)
            else:
                task_order.append(task_id)

            self.pipeline.task_order = task_order

            self.db_session.flush()

            if run_config:

                if 'saved_query_id' in run_config:
                    saved_query_id = run_config['saved_query_id']
                else:
                    saved_query_id = None
                if 'username' in run_config:
                    username = run_config['username']
                elif self.pipeline.username_created:
                    username = self.pipeline.username_created
                else:
                    username = None

                task_run = TaskRun(pipeline_id=self.pipeline.id,
                                   datetime_started=datetime.datetime.now(),
                                   username=username,
                                   args=utils.convert_to_json_safe(run_config),
                                   module_name=self.pipeline.definition[task_id]['task_module'],
                                   class_name=self.pipeline.definition[task_id]['task_class'],
                                   task_id=task_id,
                                   status=TaskRun.Status.created,
                                   saved_query_id=saved_query_id,
                                   db_env=self.db_env,
                                   created_by_add_task=True)
                self.db_session.add(task_run)
                self.db_session.flush()
                self.logger.info("Added task %s %s" % (task_id,task_run.id))
                self.task_runs[task_id] = task_run.id

            return task_id
        else:
            return None

    def run_pipeline(self):
        """Run the pipeline
        """

        if self.pipeline:
           self.db_session.commit()


    def commit_definition(self):
        """Commit the definition using the PipelineManager
        """

        if self.pipeline and isinstance(self.pipeline,Pipeline):
            if not self.pipeline.name:
                return False
            else:
                self.db_session.commit()
                return True

class PipelineFactory:
    """PipelineFactory class. Default manager is apache-airflow. Most of the options below are airflow specific.

    :param pipeline_name: The pipeline name - the main identifier of the pipeline, must be unique
    :type pipeline_name: str
    :param pipeline_id: The :class:`phenomedb.models.Pipeline` ID
    :type pipeline_name: str
    :param description: The pipeline description, defaults to None.
    :type description: str, optional
    :param start_date: The start date of the airflow pipeline, defaults to None.
    :type start_date: :class:`datetime.datetime`, optional
    :param pipeline_folder_path: The path to the pipeline folder (default used otherwise)
    :type pipeline_folder_path: str, optional
    :param default_args: The default arguments of the airflow pipeline, defaults to {'owner': 'airflow','retries':1,'retries_delay':datetime.timedelta(minutes=5)}.
    :type default_args: dict, optional
    :param hard_code_data: Whether to create a dynamically parameterised pipeline or one with hard-coded parameters, default False (dynamic)
    :type hard_code_data: bool, optional
    :param schedule_interval: How often to run the airflow pipeline, defaults to "@once".
    :type schedule_interval: str, optional
    :param db_env: Which db to use - "PROD","BETA", or "TEST", defaults to None ("PROD").
    :type db_env: str, optional
    :param tags: The Airflow tags to add (for UI filtering), defaults to [].
    :type tags: list, optional
    :param sequential: Whether to run tasks sequentially, defaults to True. False means tasks will run concurrently, in no specific order.
    :type sequential: bool, optional
    :param max_active_runs: How many active runs of a pipeline can there be
    :type max_active_runs: int, optional
    :param concurrency: How many concurrent runs of a pipeline can be executed
    :type concurrency: int, optional
    """        

    logger = utils.configure_logging(identifier="pipeline_factory")

    def __init__(self,pipeline_name=None,pipeline_id=None,description=None,start_date=None,pipeline_folder_path=None,
                 default_args=None,hard_code_data=False,
                 schedule_interval="None",db_env=None,db_session=None,tags=None,sequential=True,max_active_runs=100,concurrency=1):
        
        #self.name = name

        if not default_args:
            default_args={'owner': 'airflow','retries':1,'retries_delay':datetime.timedelta(minutes=5)}
            
        if not tags:
            tags = []

        self.logger.info(str(config))
        if 'PIPELINES' in config and 'pipeline_manager' in config['PIPELINES'] and config['PIPELINES']['pipeline_manager'] == "apache-airflow":

            from phenomedb.airflow.pipeline_manager import AirflowPipelineManager
            self.pipeline_manager = AirflowPipelineManager(pipeline_name=pipeline_name,pipeline_id=pipeline_id,max_active_runs=max_active_runs,
                                                           description=description,start_date=start_date,concurrency=concurrency,
                                                           default_args=default_args,schedule_interval=schedule_interval,hard_code_data=hard_code_data,
                                                           db_env=db_env,db_session=db_session,tags=tags,sequential=sequential,pipeline_folder_path=pipeline_folder_path)

        elif not pipeline_name and not pipeline_id:
            self.logger.info("Pipeline name and pipeline_id both null, pipeline_manager has not initialised")

        else:

            self.logger.error("PIPELINES:pipeline_manager must be set in config")
            print("PIPELINES:pipeline_manager must be set in config")


    def add_task(self,task_module,task_class,upstream_task_id=None,run_config=None,task_id=None):
        """Add a task to the pipeline.

        :param task_module: The module of the task.
        :type task_module: str
        :param task_class: The class of the task.
        :type task_class: str
        :param upstream_task_id: If specified, specifies this task is downstream of the upstream_task_id, defaults to None
        :type upstream_task_id: int, optional
        :param depends_on_past: If specified, this will only run when upstream tasks complete, defaults to True
        :type depends_on_past: bool, optional
        :return: task_label: The label of the task.
        :rtype: str
        """


        return self.pipeline_manager.add_task(task_module,task_class,upstream_task_id=upstream_task_id,run_config=run_config,task_id=task_id)

    def commit_definition(self):
        """Commit the definition of the pipeline

        :return: _description_
        :rtype: _type_
        """

        return self.pipeline_manager.commit_definition()

    def run_pipeline(self,run_config=None,debug=False):
        """Submit the pipeline to the queue.

        :return: success (True) or failure (False)
        :rtype: bool
        """

        if not run_config:
            run_config = {}

        return self.pipeline_manager.run_pipeline(run_config=run_config,debug=debug)

    def pause_pipeline(self):
        """Pause the pipeline
        """

        return self.pipeline_manager.pause_pipeline()

    def delete_pipeline(self):
        """Delete the pipeline
        """

        return self.pipeline_manager.delete_pipeline()

    @staticmethod
    def get_json_task_spec():
        """Get the json task_spec

        :return: the json task spec dict
        :rtype: dict
        """
        json_spec = {}

        with open(config['DATA']['config'] + 'task_typespec.json', "r") as read_file:
            json_spec = json.load(read_file)

        return json_spec

    @staticmethod
    def get_tasks_from_json(modules_to_include=None):
        """Parse the tasks from the task_spec file

        :param modules_to_include: A list of modules to include, defaults to None
        :type modules_to_include: list, optional
        :return: task_spec_json
        :rtype: dict
        """
        task_spec = {}

        json_spec = PipelineFactory.get_json_task_spec()

        for module_class, argument_dict in json_spec.items():

            module_name, class_name = utils.get_module_and_class_name(module_class)
            full_module_name = "phenomedb." + module_name

            if not modules_to_include or (isinstance(modules_to_include,list) and full_module_name in modules_to_include):
                            
                if module_class not in task_spec:
                    task_spec[module_class] = []
    
                module = importlib.import_module(full_module_name)
    
                # get the name, package and parameters for the class
                class_members = isp.getmembers(module, isp.isclass)
    
                for name, cls in class_members:
    
                    if name == class_name:
                        param_list = json_spec.get(module_class)
    
                        result = {}
                        result['task'] = name
                        result['module'] = cls.__module__
    
                        # params = list(param_list.keys())
    
                        arg_spec = isp.getfullargspec(cls.__init__).args
    
                        arg_spec.remove("self")
                        result['args'] = ",".join(arg_spec)
                        result['params'] = json.dumps(param_list)
                        task_spec[module_class] = result

        return task_spec