import os, sys, json, glob
import re

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.pipeline_factory import PipelineFactory
from phenomedb.query_factory import QueryFactory
import phenomedb.utilities as utils
from phenomedb.models import *
# Flask imports
from flask import Blueprint, jsonify
from flask_appbuilder import expose, has_access

# Airflow imports:
from airflow.plugins_manager import AirflowPlugin
from werkzeug.utils import secure_filename

VIEW_NAME = "pipeline_factory"

from phenomedb.base_view import *
import urllib.parse

class PipelineFactoryView(PhenomeDBBaseView):

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)
            
    @expose('/')
    @has_access
    def list(self, data_dict=None):
        if not data_dict:
            data_dict = {}
        self.set_db_session(request)
        data = self.get_default_data(data_dict)
        self.db_session.close()
        return self.render_template("pipeline_factory/pipeline_factory.html", data=data)
        
    def get_default_data(self, data_dict):       
        try:               
            # get data to populate dropdowns
            data_dict['tasks'] = PipelineFactory.get_tasks_from_json()
            self.logger.debug("tasks: " + str(data_dict['tasks']))
        except Exception as e:
            self.logger.exception(str(e))
            data_dict["error"] = str(e)       
        return data_dict


    def read_task_typespec_json(self,json_file):
        task_spec = ""
        with open(json_file, "r") as read_file:
            task_spec = json.load(read_file)
        return task_spec


    @expose("/projects", methods=["GET"])
    @has_access
    def get_projects(self):
        return self.get_dropdown_options('project')

    @expose("/harmonised_metadata_field", methods=["GET"])
    @has_access
    def get_harmonised_metadata_field(self):
        return self.get_dropdown_options('harmonised_metadata_field')
    
    @expose("/units", methods=["GET"])
    @has_access
    def get_units(self):  
        return self.get_dropdown_options('unit')
    
    @expose("/options", methods=["GET"])
    @has_access
    def get_dropdown_options(self):
        self.set_db_session(request)
        options = []    
        try:
            table_name = request.args.get("table")  
            self.logger.debug("getting %s", table_name)
            if table_name is not None:
                rows = self.execute_sql("select name from " + str(table_name) + " order by name")
                for row in rows:    
                    options.append(row['name'])
               
                response_body = jsonify(options)
                  
        except Exception as e: 
            
            return self.handle_json_error(e)
        self.db_session.close()
        return make_response(response_body, 200) 
    

                       


    @expose("/upload_file", methods=["POST"])
    @has_access
    def upload_file(self):
        try:
            file = request.files['uploaded_file']
            overwrite = json.loads(request.values['overwrite'])

            if file:
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(config['DATA']['app_data'],'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                filepath = os.path.join(upload_folder,filename)

                if os.path.isfile(filepath) and not overwrite:
                    raise Exception(filename + ' already exists, please rename the file or overwrite the existing')

                file.save(filepath)

                self.logger.info('File saved - ' + filename)
                return make_response({'success':True}, 200)

        except Exception as err:
            self.logger.exception('File upload failed: ' + str(err))
            return make_response(str(err), 400)

    '''    
    [Request {'dag_def': '[{"task_name":"XCMSFeatureImportTaskUnifiedCSV","task_module":"phenomedb.tasks.xcms_features_import_unified_csv","args":{"project_name":"nPYc-toolbox-tutorials","unified_csv_path":"airflow.txt","sample_matrix":"Plasma","assay_name":"HPOS"},"index":1}]', 'name': 'test', 'dag_description': 'test'}
    [SUBMITTED ARG project_name
    [DEFINITION ARG {'type': 'project', 'label': 'Project', 'required': True}
    [SUBMITTED ARG unified_csv_path
    [DEFINITION ARG {'type': 'file_path_remote', 'label': 'Unified CSV file', 'remote_folder_path': 'imports', 'required': True, 'project_folder': False}
    [This is NOT a project folder
    [SUBMITTED ARG sample_matrix
    [DEFINITION ARG {'type': 'dropdown', 'label': 'Sample matrix', 'options': {'Serum': 'Serum', 'Plasma': 'Plasma', 'Urine': 'Urine'}, 'required': True}
    [SUBMITTED ARG assay_name
    [DEFINITION ARG {'type': 'dropdown', 'label': 'Assay', 'options': {'LPOS': 'LPOS', 'HPOS': 'HPOS', 'RPOS': 'RPOS', 'LNEG': 'LNEG', 'RNEG': 'RNEG'}, 'required': True}
    '''
    @expose('/dag', methods=["POST"])
    @has_access
    def create_dag(self):
        self.set_db_session(request)
        data = {}       
        try:
            # get the parameters from the input form submitted
            param_dict = self.flask_form_to_ORM_dict(request.form)
            self.logger.debug("Request %s", param_dict)

            dag_def = param_dict['dag_def']          
            dag_json = json.loads(dag_def)

            self.logger.debug("Request %s", dag_json)
            json_spec = PipelineFactory.get_tasks_from_json()

            if len(dag_json) > 0:
                desc = param_dict['dag_description']
                name = param_dict['name'].replace(" ","_")
                if self.db_session.query(Pipeline).filter(Pipeline.name==name).count() > 0:
                    raise Exception('Pipeline with that name already exists, please choose another')

                db_env = param_dict['set_db_env']
                schedule_interval = param_dict['schedule_interval']

                if schedule_interval == 'manual':
                    schedule_interval = 'None'

                if 'dag_tags' in param_dict:
                    dag_tags = param_dict['dag_tags'].split(' ')
                else:
                    dag_tags = []

                if 'sequential' in param_dict:
                    sequential = True
                else:
                    sequential = False

                pipeline = PipelineFactory(pipeline_name=name,description=desc, schedule_interval=schedule_interval,
                                           db_env=db_env,tags=dag_tags,sequential=sequential,hard_code_data=True)

                airflow_dir = config['DATA']['app_data']
                project_dir = config['DATA']['project_data_base_path']
                upstream_task_id = None      
                for task in dag_json:

                    task_class = task['task_class']
                    task_label = task['task_label']

                    if re.match(r'^[0-9+]',task_label):
                        raise Exception('Task labels cannot begin with numbers - ' + task_label)

                    task_mod = task['task_module']
                    task_args = task['args']

                    if task_args is None:
                        task_args = {}
                    else:
                        task_mod_split = task_mod.split('.')
                        task_key = task_mod_split[1] + '.' + task_class

                        #self.logger.info(json_spec)
                        self.logger.info(task_key)
                        self.logger.info(task_args)

                        method_params = json.loads(json_spec[task_key]['params'])
                        for arg_name in task_args.keys():

                            self.logger.debug("SUBMITTED ARG %s = %s", arg_name, task_args[arg_name])

                            if task_args[arg_name] != '':

                                arg_def = method_params[arg_name]
                                if arg_def['type'] == 'lambda' and task_args[arg_name] != '':

                                    try:
                                        test_lambda = eval(task_args[arg_name])
                                    except Exception:
                                        self.logger.exception('User enterered lambda is not computable - ' + task_args[arg_val])
                                        raise Exception('User enterered lambda is not computable - ' + task_args[arg_val])

                                elif arg_def['type'] == 'lambda' and task_args[arg_name] == '':
                                    task_args[arg_name] = None

                                elif arg_def['type'] == 'list':

                                    list = []
                                    for col in task_args[arg_name].split(','):
                                        if col != '':
                                            list.append(col.strip())
                                    task_args[arg_name] = list

                                elif arg_def['type']=='file_path_remote' or arg_def['type']=='file_upload':

                                    remote_folder_path = arg_def['remote_folder_path']

                                    self.logger.debug("FILE TYPE DEF is %s", arg_def)
                                    if arg_def['project_folder'] == True:
                                        project_name = task_args['project_name']
                                        if project_name is None or len(project_name)==0:
                                            self.logger.error("Missing project name from %s task_typespec: cannot get path to \
                                                                project folder", task_class)
                                            file_path = os.path.join(project_dir, remote_folder_path, task_args[arg_name])
                                        else:

                                            project_folder = ""
                                            data_dir = self.execute_sql("SELECT project_folder_name from project where name = :name", {"name":project_name})
                                            if ( len(data_dir) > 0 ):
                                                project_folder = data_dir[0]['project_folder_name']
                                            file_path = os.path.join(project_dir, project_folder, remote_folder_path, task_args[arg_name])

                                    else:
                                        self.logger.debug("This is NOT a project folder, using airflow path")
                                        print(task_args[arg_name])
                                        file_path = os.path.join(airflow_dir, remote_folder_path, secure_filename(task_args[arg_name]))


                                    self.logger.debug("Built file path for %s at %s", arg_name, file_path)
                                    task_args[arg_name] = file_path

                    pipeline.add_task(task_module=task_mod, task_class=task_class, task_id=task_label, run_config=task_args)
                    upstream_task_id = task_label

                pipeline.commit_definition()
                data['user_msg'] = ["Pipeline '" + name + "' saved."]
            
        except Exception as e:
            self.logger.exception(str(e))
            data['error'] = str(e)

        self.db_session.close()
        return self.list(data_dict=data)


    @expose('/taskrun/<id>', methods=["GET"])
    @has_access
    def viewtaskrun(self,id):
        self.set_db_session(request)
        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==id).first()
        data = {'task_run':task_run}
        self.db_session.close()
        return self.render_template("pipeline_factory/task_run.html", data=data)

    @expose('/pipelinerun/', methods=["GET"])
    @has_access
    def viewpipelinerun(self):
        self.set_db_session(request)
        id = urllib.parse.unquote(request.args.get("id"))
        self.logger.info("Pipeline Run ID %s " % id)

        task_runs = self.db_session.query(TaskRun).filter(TaskRun.pipeline_run_id == id).all()
        for task_run in task_runs:
            task_run.log_url = task_run.get_log_url()
        pipeline_id = task_runs[0].pipeline_id
        pipeline = self.db_session.query(Pipeline).filter(Pipeline.id == task_runs[0].pipeline_id).first()
        data = {'task_runs':task_runs,
                'pipeline':pipeline}
        self.db_session.close()
        return self.render_template("pipeline_factory/pipeline_run.html", data=data)

    @expose('/run_pipeline', methods=["POST"])
    @has_access
    def run_pipeline(self):
        self.set_db_session(request)
        request_data = request.get_json()
        #self.logger.info(request.form.keys())
        self.logger.info("RunPipeline View %s" % request_data)
        pipeline_factory = PipelineFactory(db_session=self.db_session,pipeline_name=request_data['pipeline_name'])
        if pipeline_factory.run_pipeline(run_config=request_data['run_config']):
            response_data = {'success':'true'}
            response_data['pipeline_url'] = "%s/tree?dag_id=%s&root=" % (config['WEBSERVER']['url'],request_data['pipeline_name'])
            response_data['task_run_urls'] = []
            response_data['task_run_logs'] = []
            for task_run_id,task_run in pipeline_factory.pipeline_manager.task_runs.items():
                response_data['task_run_urls'].append(task_run.get_url())
                response_data['task_run_logs'].append(task_run.get_log_url())
                utils.clear_task_view_cache(task_run_id)
        else:
            response_data = {'error': 'true'}
        self.db_session.close()
        return jsonify(response_data)

    @expose("/exclude_samples_and_rerun",methods=["POST"])
    @has_access
    def exclude_samples_and_rerun(self):
        self.set_db_session(request)
        request_data = request.get_json()
        self.logger.info("request_data %s" % request_data)
        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(request_data['task_run_id'])).first()
        if task_run:
            if task_run.saved_query_id and 'excluded_samples' in request_data.keys():
                query_factory = QueryFactory(saved_query_id=task_run.saved_query_id,db_session=self.db_session)
                query_factory.add_filter(model='Sample',property='name',operator='not_in',value=request_data['excluded_samples'].split(","))
                query_factory.save_query()
                self.logger.info("SavedQuery %s updated - samples excluded %s" % (task_run.saved_query_id,request_data['excluded_samples']))
            if task_run.pipeline:
                pipeline_factory = PipelineFactory(db_session=self.db_session,pipeline_name=task_run.pipeline.name)
                run_config = { task_run.task_id : task_run.args }
                pipeline_factory.run_pipeline(run_config=run_config)
                #print(pipeline_factory.pipeline_manager.task_runs)
                task_run_url = pipeline_factory.pipeline_manager.task_runs[task_run.id].get_url()
                response_data = {'success':'true','task_run_url':task_run_url,"task_id":task_run.task_id}
                self.logger.info("Pipeline run %s task_run_url %s task_run_log" % (task_run.pipeline.name,task_run_url,task_run.get_log_url))
            else:
                response_data = {'error': "no pipeline for task run with id %s" % request_data['task_run_id']}
        else:
            response_data = {'error': "no task run with id %s" % request_data['task_run_id']}

        return jsonify(response_data)
'''
BLUEPRINT
template_folder is where the html files for this module live
static_folder is the same for all modules; contains eg css and js libraries
static_url_path maps the physical path in static_folder to this value, eg
http://localhost:8080/static/phenomedb/phenomedb.css
'''
pipeline_factory_bp = Blueprint(
        VIEW_NAME, __name__,
        template_folder='../templates',
        static_folder='../templates/static',
        static_url_path='/static/phenomedb')

'''
Create the view class
'category' parameter is the item on the Airflow menu bar,
'name' parameter is the item in that menu
'''
v_appbuilder_view = PipelineFactoryView()
v_appbuilder_package = {"name": "Pipeline Factory",
                        "category": "PhenomeDB",
                        "category_icon": "fa-th",
                        "view": v_appbuilder_view}

class PipelineFactoryPlugin(AirflowPlugin):
   
    name = VIEW_NAME
    # the variables called flask_blueprints and admin_views 
    # are inherited AirflowPlugin properties
    flask_blueprints = [pipeline_factory_bp]
    appbuilder_views = [v_appbuilder_package]
    #admin_views = [pipeline_factory_view]
    
    

