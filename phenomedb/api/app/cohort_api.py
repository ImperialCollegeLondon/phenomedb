import sys
import logging
import os

if os.environ['PHENOMEDB_PATH'] not in sys.path:
   sys.path.append(  os.environ['PHENOMEDB_PATH'])
# PhenomeDB imports

from flask import request
from flask_appbuilder.api import BaseApi, expose
from flask_appbuilder.security.decorators import protect
from . import appbuilder

from phenomedb.models import *
from phenomedb.config import config
from phenomedb.pipeline_factory import PipelineFactory

API_NAME = "cohort"

class Cohort(BaseApi):
    """Cohort API. For building and getting cohorts

        You must first login and get a JWT access_token and JWT refresh token.

        The access_token is used on all method requests.

        If the access_token expires, refresh it using the refresh_token.

            import json
            import requests

            data = {"username": "xxxxx","password": "xxxxx","provider": 'ldap','refresh':True}

            session = requests.session()

            login_url = "https://<host>/custom/api/v1/security/login"
            refresh_url = "https://<host>/custom/api/v1/security/refresh"

            # Login and set the JWT tokens
            r = session.post(login_url,json=data)
            access_token = json.loads(r.content)['access_token']
            refresh_token = json.loads(r.content)['refresh_token']

            # Import a sample manifest
            data = {"project_name":"PipelineTesting",
                    "sample_manifest_path": config['DATA']['test_data'] + 'sample_manifests/DEVSET_sampleManifest.xlsx',
                    "columns_to_ignore":[],
                    "username": "xxxx"}

            r = self.session.post('http://localhost:5000/custom/api/v1/import/samplemanifest',
                                  json=data,
                                  headers={'Authorization': 'Bearer '+ access_token})


            # Refresh the JWT token
            r = session.post(refresh_url,headers={"Authorization": "Bearer " + refresh_token})
            access_token = json.loads(r.content)['access_token']


    """

    def __init__(self):
        """Constructor for Cohort API
        """        

        super().__init__()
        self.configure_logging(identifier=API_NAME)
        # all fields for table:

    def configure_logging(self,identifier='cohort_api', log_file='api.log', level=logging.DEBUG):
        '''
        to set up a logger
        :param identifier: an identifier for your messages in the log
        :param log_file: file to log to at location specified in config.ini; (will create this dir if nec).
        :param logging level DEBUG by default
        '''
        self.logger = None
        try:

            self.logger = logging.getLogger(identifier)

            log_dir = config['LOGGING']['dir']
            log_file = os.path.join(log_dir, log_file)

            os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(log_file, mode="a", encoding="utf-8", delay=False)

            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            fh.setFormatter(formatter)

            self.logger.addHandler(fh)
            self.logger.setLevel(level)
            #print("Initialised " + identifier + " to log to", log_file)
        except OSError as e:
            print('Error configuring logging', e)

    @expose("/summary/",methods=['GET'])
    @protect()
    def name(self):
        """Get a summary by name
        ---
        get:
          summary: Get a cohort by
          parameters:
            - in: header
              name: username
              schema:
                type: string
              required: true
              description: The name of the cohort
          responses:
            200:
              description: ImportSampleManifest pipeline created
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
        """

        if 'sample_manifest_path' in request.json \
            and 'project_name' in request.json \
                and 'columns_to_ignore' in request.json \
                    and 'username' in request.json:

            try:
                if 'db_env' in request.json:
                    db_env = request.json['db_env']
                else:
                    db_env = 'PROD'

                db_session = db.get_db_session(db_env=db_env)
                if db_session.query(Project).filter(Project.name==request.json['project_name']).count() == 0:
                    raise Exception("Unknown project name")

                args = {}
                args['project_name'] = request.json['project_name']
                args['sample_manifest_path'] = request.json['sample_manifest_path']

                if isinstance(request.json['columns_to_ignore'],str):
                    args['columns_to_ignore'] = request.json['columns_to_ignore'].split(",")
                elif isinstance(request.json['columns_to_ignore'],list):
                    args['columns_to_ignore'] = request.json['columns_to_ignore']

                #args['username'] = request.json['json']['user']
                pipeline = PipelineFactory('ImportSampleManifest '+args['project_name'],'API Import Sample Manifest',tags=self.build_tags(request.json,'ImportSampleManifest'),db_env=db_env)
                pipeline.add_task('phenomedb.tasks.imports.import_sample_manifest','ImportSampleManifest', args['project_name'].replace('-','_') + "_sample_manifest",args,depends_on_past=True)

                if 'write_dag' not in request.json or request.json['write_dag'] == True:
                    pipeline.submit()
                    self.logger.info("new pipeline scheduled - " + pipeline.name)

                return self.response(200, message='Pipeline Name:' + pipeline.name)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')





appbuilder.add_api(Cohort)


