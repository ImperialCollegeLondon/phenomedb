# Add phenomedb to path if not already
from pathlib import Path
import sys
import time
import datetime
import os
from jinja2 import Template
from phenomedb.config import config
import phenomedb.utilities as utils
from phenomedb.pipeline_factory import BasePipelineManager
import pathlib
import requests
from requests.auth import HTTPBasicAuth
import json
from phenomedb.models import *
import importlib
import inspect

class AirflowPipelineManager(BasePipelineManager):
    """AirflowPipeline class. For generating or running Airflow DAGs.

        If an Airflow DAG of the specified name exists, it will run that. Otherwise it will generate a DAG file and schedule it's execution.

        :param name: The pipeline name - the main identifier of the pipeline.
        :type name: str
        :param description: The pipeline description, defaults to None.
        :type description: str, optional
        :param run_config: The parameters to use in the pipeline tasks, defaults to None.
        :type run_config: dict, optional
        :param start_date: The start date of the airflow pipeline, defaults to None.
        :type start_date: :class:`datetime.datetime`, optional
        :param default_args: The default arguments of the airflow pipeline, defaults to {'owner': 'airflow','retries':1,'retries_delay':datetime.timedelta(minutes=5)}.
        :type default_args: dict, optional
        :param schedule_interval: How often to run the airflow pipeline, defaults to "@once".
        :type schedule_interval: str, optional
        :param db_env: Which db to use - "PROD","BETA", or "TEST", defaults to None ("PROD").
        :type db_env: str, optional
        :param tags: The Airflow tags to add (for UI filtering), defaults to [].
        :type tags: list, optional
        :param sequential: Whether to run tasks sequentially, defaults to True. False means tasks will run concurrently, in no specific order.
        :type sequential: bool, optional
    """        
    """
        AirflowPipelineManager class. For generating or running Airflow pipelines.
    """

    logger = utils.configure_logging(identifier="pipeline_factory")
    dag_str = ""
    new_pipeline = False
    pipeline_run = False
    session = None
    tags = []
    task_runs = {}

    def __init__(self,pipeline_name=None,description='default description',pipeline_folder_path=None,max_active_runs=200,concurrency=1,
                 start_date=None,default_args=None,
                 schedule_interval='None',db_env=None,db_session=None,tags=None,sequential=True,username=None,pipeline_id=None,hard_code_data=False):

        if not default_args:
            default_args = {'owner': 'airflow', 'retries': 1, 'retries_delay': datetime.timedelta(minutes=5)}

        if not tags:
            tags = []

        if not pipeline_name and not pipeline_id:
            raise Exception("Either pipeline_name or pipeline_id must be set")

        if pipeline_name and db_env and db_env == 'TEST':
            pipeline_name = pipeline_name + "_TEST"

        super().__init__(pipeline_name=pipeline_name,db_env=db_env,db_session=db_session,pipeline_id=pipeline_id)

        if not self.pipeline:

            if not pipeline_folder_path:
                pipeline_folder_path = config['PIPELINES']['PIPELINE_FOLDER']

            pipeline_file_path = os.path.join(pipeline_folder_path,pipeline_name+".py")

            if 'pipeline_factory' not in tags:
                tags.append('pipeline_factory')

            if not start_date:
                today = datetime.datetime.now()
                yesterday = today - datetime.timedelta(days=1)
                start_date = yesterday

            self.pipeline = Pipeline(name=pipeline_name,
                                     description=description,
                                     date_created=datetime.datetime.now(),
                                     schedule_interval=schedule_interval,
                                     start_date=start_date,
                                     username_created=username,
                                     hard_code_data=hard_code_data,
                                     task_order=[],
                                     default_args=utils.convert_to_json_safe(default_args),
                                     sequential=sequential,
                                     pipeline_file_path=pipeline_file_path,
                                     definition={},
                                     max_active_runs=max_active_runs,
                                     concurrency=concurrency,
                                     tags=tags)
            self.db_session.add(self.pipeline)
            self.db_session.flush()

#        self.pipeline.sequential = sequential

 #       self.task_ids = []

        #from airflow.configuration import conf
        #self.dag_output_dir = config['PIPELINES']['PIPELINE_FOLDER']

        # If the dag already exists, just run it with the config
        #dagbag = DagBag(read_dags_from_db=True)
        #



    def load_boiler_plate(self):
        """Load the pipeline boiler plate.
        """        

        template_data = {'pipeline': self.pipeline,
                         'start_timestamp': self.start_timestamp}

        self.load_dag_template('boiler_plate',template_data)

    def set_upstream(self,upstream_task_id,downstream_task_id):
        """Set the upstream task.

        :param upstream_task_id: The upstream task id.
        :type upstream_task_id: str
        :param downstream_task_id: The downstream task id.
        :type downstream_task_id: str
        """        

        self.logger.debug('Setting upstream task: ' + str(upstream_task_id) + " >> " + str(downstream_task_id))

        self.load_dag_template("set_upstream",{'upstream_task_id':upstream_task_id,
                                               'downstream_task_id':downstream_task_id})

    def load_dag_template(self,template_name,template_data):
        """Load the DAG template.

        :param template_name: The name of the template.
        :type template_name: str
        :param template_data: The data for the template.
        :type template_data: dict
        """        

        template_data['name'] = self.pipeline.name

        parent_folder = str(pathlib.Path(__file__).parent.absolute())

        f = open(parent_folder + "/dag_templates/" + template_name + ".py", "r")
        t = Template(f.read())
        rendered_template = t.render(template_data)
        f.close()

        self.dag_str += rendered_template + "\n"

    def set_sequential_dependencies(self):
        """Set the sequential dependencies of the DAG.
        """        

        if len(self.pipeline.definition.keys()) > 1:
            i = 0
            while i < len(self.pipeline.task_order):
                if i != 0:
                    self.set_upstream(self.pipeline.task_order[i-1],self.pipeline.task_order[i])
                i = i + 1

    def run_pipeline(self,run_config=None,debug=False):
        """Run the pipeline using the Airflow scheduler.

        Single-Task Pipelines can use the Airflow API to run Pipelines that already exist.
        Multi-Task Pipelines write an Airflow DAG file to the dag_output_directory.

        :return: success (True) or failure (False)
        :rtype: bool
        """
        if not run_config:
            run_config = {}
        #if self.pipeline_run:
        #    raise Exception("The Pipeline has already run! %s" % self.pipeline.name)

        try:

            if not self.pipeline:
                raise Exception("No pipeline to run")
            elif not self.pipeline.definition or self.pipeline.definition == {}:
                raise Exception("Pipeline has no definition %s %s" % (self.pipeline.id,self.pipeline.name))

            else:

                if not os.path.exists(self.get_dag_path()):
                    self.commit_definition()
                    time.sleep(100)

                for task_id,args in run_config.items():
                    if task_id not in self.pipeline.definition.keys():
                        raise Exception("Unrecognised task_id %s \n Expected task ids: %s" % (task_id,self.pipeline.definition.keys()))

                if self.check_if_pipeline_in_airflow():
                    self.trigger_pipeline(run_config=run_config,debug=debug)
                else:
                    time.sleep(100)
                    if self.check_if_pipeline_in_airflow():
                        self.trigger_pipeline(run_config=run_config,debug=debug)
                    else:
                        time.sleep(100)
                        if self.check_if_pipeline_in_airflow():
                            self.trigger_pipeline(run_config=run_config,debug=debug)
                        else:
                            time.sleep(300)
                            if self.check_if_pipeline_in_airflow():
                                self.trigger_pipeline(run_config=run_config,debug=debug)
                            else:
                                raise Exception("Airflow Pipeline not registered after 10 minutes... please investigate: %s %s" % (self.pipeline.id,self.pipeline.pipeline_file_path))

                self.db_session.commit()
                return True

        except Exception as err:
            self.logger.exception(err)
            self.db_session.rollback()
            raise Exception(err)

    def pause_pipeline(self):
        return self.check_if_pipeline_in_airflow(pause=True)

    def delete_pipeline(self):

        if self.check_if_pipeline_in_airflow(pause=True):

            response = self.session.delete('http://%s/api/v1/dags/%s' % (config['PIPELINES']['pipeline_manager_api_host'],self.pipeline.name),
                                            auth=HTTPBasicAuth(config['PIPELINES']['pipeline_manager_user'],
                                                                config['PIPELINES']['pipeline_manager_password']))


        if os.path.exists(self.pipeline.pipeline_file_path):
            os.remove(self.pipeline.pipeline_file_path)
        self.pipeline.deleted = True
        self.db_session.commit()
        return self.pipeline.deleted


    def check_if_pipeline_in_airflow(self,pause=False):

        if not self.session:
            self.session = requests.session()

        response = self.session.get('http://%s/api/v1/dags' % config['PIPELINES']['pipeline_manager_api_host'],
                                           auth=HTTPBasicAuth(config['PIPELINES']['pipeline_manager_user'],
                                                              config['PIPELINES']['pipeline_manager_password']))
        if response.status_code == 200:
            dags = json.loads(response.content)
            if 'dags' in dags:
                for dag in dags['dags']:
                    if str(self.pipeline.name) == dag['dag_id']:
                        if dag['is_paused']:
                            update = self.session.patch(
                                'http://%s/api/v1/dags/%s' % (config['PIPELINES']['pipeline_manager_api_host'],dag['dag_id']),
                                json={'is_paused': pause},
                                auth=HTTPBasicAuth(config['PIPELINES']['pipeline_manager_user'],
                                                   config['PIPELINES']['pipeline_manager_password']))
                            if update.status_code == 200:
                                return True
                        else:
                            return True
        else:
            raise Exception("Airflow API error %s %s" % (response.status_code,response.content))
        return False

    def commit_definition(self):

        super().commit_definition()
        self.write_out_pipeline()

    def add_or_update_task(self,task_id,args):

        if 'saved_query_id' in args:
            saved_query_id = args['saved_query_id']
        else:
            saved_query_id = None
        if 'username' in args:
            username = args['username']
        elif self.pipeline.username_created:
            username = self.pipeline.username_created
        else:
            username = None

        task_run = self.db_session.query(TaskRun).filter(TaskRun.pipeline_id == self.pipeline.id,
                                                         TaskRun.task_id == task_id).first()

        if not task_run:
            task_run = TaskRun(pipeline_id=self.pipeline.id,
                               datetime_started=datetime.datetime.now(),
                               username=username,
                               args=utils.convert_to_json_safe(args),
                               module_name=self.pipeline.definition[task_id]['task_module'],
                               class_name=self.pipeline.definition[task_id]['task_class'],
                               task_id=task_id,
                               status=TaskRun.Status.created,
                               saved_query_id=saved_query_id,
                               db_env=self.db_env)
            self.db_session.add(task_run)
            self.db_session.flush()

        args['task_run_id'] = task_run.id
        args['db_env'] = self.db_env
        task_run.args = args
        self.db_session.flush()
        return task_run

    def trigger_pipeline(self,run_config=None,debug=False):

        if not run_config:
            run_config = {}

        task_runs = {}

        task_run_ids = {}

        task_id_task_runs = {}

        tasks_with_upstream = {}

        # Create all the TaskRuns
        for task_id in self.pipeline.task_order:

            if task_id in run_config.keys():
                # if there is a task_run_id set, get that one!
                if 'task_run_id' in run_config[task_id].keys() and run_config[task_id]['task_run_id'] is not None:
                    task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(run_config[task_id]['task_run_id'])).first()
                    args = run_config[task_id]

                    if 'saved_query_id' in args:
                        task_run.saved_query_id = args['saved_query_id']
                    if 'username' in args:
                        task_run.username = args['username']

                    args_with_none = []

                    for arg_name, arg_value in args.items():
                        if arg_value == '' or arg_value is None:
                            args_with_none.append(arg_name)

                    for arg_name in args_with_none:
                        del args[arg_name]

                else:
                    args = {}
                    # 1. Check whether the Task Runs already exist (created_by_add_task=True), if so, use them!
                    # 2. Otherwise, use the pipeline_config
                    task_run = self.db_session.query(TaskRun).filter(TaskRun.task_id==task_id,
                                                            TaskRun.pipeline_id==self.pipeline.id,
                                                             TaskRun.status==TaskRun.Status.created,
                                                            TaskRun.created_by_add_task==True).first()

                    if not task_run:
                        saved_query_id = None
                        username = None
                        if task_id in run_config:
                            args = run_config[task_id]

                            if 'saved_query_id' in args:
                                saved_query_id = args['saved_query_id']
                            if 'username' in args:
                                username = args['username']
                            if 'upstream_task_id' in args:
                                tasks_with_upstream[task_id] = args['upstream_task_id']
                                del args['upstream_task_id']

                        else:
                            args = {}
                            if not username:
                                username = self.pipeline.username_created

                        args_with_none = []

                        for arg_name,arg_value in args.items():
                            if arg_value == '':
                                args_with_none.append(arg_name)

                        for arg_name in args_with_none:
                            del args[arg_name]

                        task_run = TaskRun(pipeline_id=self.pipeline.id,
                                           datetime_started=datetime.datetime.now(),
                                           username=username,
                                           args=utils.convert_to_json_safe(args),
                                           module_name=self.pipeline.definition[task_id]['task_module'],
                                           class_name=self.pipeline.definition[task_id]['task_class'],
                                           task_id=task_id,
                                           status=TaskRun.Status.created,
                                           saved_query_id=saved_query_id,
                                           db_env=self.db_env)
                        self.db_session.add(task_run)
                        self.db_session.flush()
                    else:
                        args = task_run.args

                args['task_run_id'] = task_run.id
                args['db_env'] = self.db_env
                i = importlib.import_module(task_run.module_name)
                task = getattr(sys.modules[task_run.module_name], task_run.class_name)
                signature = inspect.signature(task)
                arglist = list(signature.parameters.keys())
                argcopy = dict(args)
                for arg_name,arg_bvalue in argcopy.items():
                    if arg_name not in arglist:
                        self.logger.info("Arg is not in the task arg spec, so its being deleted! %s %s %s" % (task_run.class_name,arg_name,arglist))
                        del(args[arg_name])

                task_run.args = args
                self.db_session.flush()
                # Updates/overrides the run_config
                run_config[task_id] = args
                task_runs[task_run.id] = task_run

                task_run_ids[task_id] = task_run.id
                task_id_task_runs[task_id] = task_run

        # Add the upstream_task_run_id from the upstream_task_id
        for task_id,upstream_task_id in tasks_with_upstream.items():
            this_task_run = task_id_task_runs[task_id]
            upstream_task_run = task_id_task_runs[upstream_task_id]
            args = dict(this_task_run.args)
            args['upstream_task_run_id'] = upstream_task_run.id
            this_task_run.args = args
            this_task_run.upstream_task_run_id = upstream_task_run.id
            self.db_session.flush()
            run_config[task_id] = args

        if debug:
            self.db_session.commit()
            for task_id in self.pipeline.task_order:
                if task_id in task_run_ids.keys():
                    task_run = task_runs[task_run_ids[task_id]]
                    i = importlib.import_module(task_run.module_name)
                    task = getattr(sys.modules[task_run.module_name], task_run.class_name)(**task_run.args,execution_date=datetime.datetime.now())
                    task.run()
        else:
            if not self.session:
                self.session = requests.session()
            r = self.session.post('http://%s/api/v1/dags/%s/dagRuns' % (config['PIPELINES']['pipeline_manager_api_host'],self.pipeline.name),
                                json={'conf':run_config},
                             auth = HTTPBasicAuth(config['PIPELINES']['pipeline_manager_user'],
                                                  config['PIPELINES']['pipeline_manager_password']),
                             headers={'Content-Type':'application/json'})

            if r.status_code == 200:
                content = json.loads(r.content.decode())
                for task_id,task_run in task_runs.items():
                    task_run.status = TaskRun.Status.scheduled
                    task_run.pipeline_run_id = content['dag_run_id']
                self.db_session.commit()
                self.logger.info("DAG run via API: " + str(self.pipeline.name) + " options: " + str(run_config) + " pipeline_run_id:" + str(content['dag_run_id']))

            self.logger.info(str(r.status_code))
            self.logger.info(str(r.content))
        self.task_runs = {**self.task_runs,**task_runs}
        return True

    def get_dag_path(self):

        if config['PIPELINES']['docker'] != 'false':
            filepath = self.pipeline.pipeline_file_path
        else:
            filepath = self.pipeline.pipeline_file_path.replace("/opt/airflow/dags",config['PIPELINES']['pipeline_folder'])

        return filepath

    def write_out_pipeline(self):

        self.logger.info("Writing pipeline %s to %s" % (self.pipeline.name,self.pipeline.pipeline_file_path))

        self.start_timestamp = datetime.datetime.timestamp(self.pipeline.start_date)

        self.load_boiler_plate()

        filepath = self.get_dag_path()
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        for task_id in self.pipeline.task_order:

            task_definition = self.pipeline.definition[task_id]

            template_data = {'task_module':task_definition['task_module'],
                             'task_id':task_id,
                             'task_class':task_definition['task_class']}

            if self.pipeline.hard_code_data:
                task_run = self.db_session.query(TaskRun).filter(TaskRun.task_id == task_id,
                                                                 TaskRun.pipeline_id == self.pipeline.id,
                                                                 TaskRun.created_by_add_task == True).first()
                if not task_run:
                    raise Exception('Pipeline Task with hard_code_data=True does not have a matching TaskRun %s %s' % (self.pipeline.id,task_id))
                else:
                    task_run.args['task_run_id'] = task_run.id
                    task_run.args['db_env'] = self.db_env
                    template_data['task_run'] = task_run
                    self.load_dag_template("python_operator_with_data", template_data)
            else:
                self.load_dag_template("python_operator_with_config",template_data)

        self.set_sequential_dependencies()

        f = open(filepath, "w")
        f.write(self.dag_str)
        f.close()
        self.logger.info("Pipeline written to %s" % filepath)

        self.db_session.commit()
