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

API_NAME = "import"

class Import(BaseApi):
    """Import API. For triggering import jobs.

        You must first login and get a JWT access_token and JWT refresh token.

        The access_token is used on all method requests.

        If the access_token expires, refresh it using the refresh_token.

            import json
            import requests

            data = {"username": "xxxxx","password": "xxxxx","provider": 'ldap','refresh':True}

            session = requests.session()

            login_url = "https://phenomedb.npc.ic.ac.uk/custom/api/v1/security/login"
            refresh_url = "https://phenomedb.npc.ic.ac.uk/custom/api/v1/security/refresh"

            # Login and set the JWT tokens
            r = session.post(login_url,json=data)
            access_token = json.loads(r.content)['access_token']
            refresh_token = json.loads(r.content)['refresh_token']

            print(access_token)
            print(refresh_token)

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
            refresh_token = json.loads(r.content)['refresh_token']


    """

    def __init__(self):

        super().__init__()
        self.configure_logging(identifier=API_NAME)
        # all fields for table:

    def build_tags(self,params,task_name):

        tags = ['API',task_name]

        if 'username' in params:
            tags.append(params['username'])

        if 'project_name' in params:
            tags.append(params['project_name'])

        return tags

    def configure_logging(self,identifier='import_api', log_file='api.log', level=logging.DEBUG):
        '''
        to set up a logger
        :param identifier: an identifier for your messages in the log
        :param log_file: file to log to at location specified in config.ini; (will create this dir if nec).
        :param logging level DEBUG by default
        '''
        self.logger = None
        try:

            self.logger = logging.getLogger(identifier)

            log_dir =  config['LOGGING']['dir']
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

    @expose("/samplemanifest",methods=['POST'])
    @protect()
    def samplemanifest(self):
        """Import a sample manifest
        ---
        post:
          summary: Import a Sample Manifest
          parameters:
            - in: header
              name: username
              schema:
                type: string
              required: true
              description: The username of the person submitting
            - in: header
              name: project_name
              schema:
                type: string
              required: true
              description: The project name
            - in: header
              name: sample_manifest_path
              schema:
                type: string
              required: true
              description: The path to the sample manifest file
            - in: header
              name: columns_to_ignore
              schema:
                type: string
              required: true
              description: A CSV list of metadata columns to ignore
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
                #pipeline = PipelineFactory('ImportSampleManifest','API Import Sample Manifest',tags=self.build_tags(request.json,'ImportSampleManifest'),db_env=db_env)
                #pipeline.add_task('phenomedb.tasks.imports.import_sample_manifest','ImportSampleManifest', args['project_name'].replace('-','_') + "_sample_manifest",args,depends_on_past=True)

                pipeline = PipelineFactory('API_ImportSampleManifest',run_config=args,db_env=db_env)

                #if 'write_dag' not in request.json or request.json['write_dag'] == True:
                #    pipeline.submit()
                #    self.logger.info("new pipeline scheduled - " + pipeline.name)

                return self.response(200, message='Pipeline Name:' + pipeline.name)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')


    @expose("/datalocations",methods=['POST'])
    @protect()
    def datalocations(self):
        """Import a data locations file
        ---
        post:
          summary: Import data locations
          parameters:
            - in: header
              name: username
              schema:
                type: string
              required: true
              description: The username of the person submitting
            - in: header
              name: project_name
              schema:
                type: string
              required: true
              description: The project name
            - in: header
              name: data_locations_path
              schema:
                type: string
              required: true
              description: The path to the data locations file
            - in: header
              name: sample_matrix
              schema:
                type: string
              required: true
              description: The sample_matrix (ie 'plasma', 'serum', 'urine')
            - in: header
              name: assay_platform
              schema:
                type: string
              required: true
              description: The assay platform, must be 'NMR' or 'MS'
            - in: header
              name: assay_name
              schema:
                type: string
              description: For MS, specify 'LNEG', 'LPOS', 'BANEG', 'HPOS', 'RPOS', 'RNEG'
          responses:
            200:
              description: ImportDataLocations pipeline created
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
        """

        self.logger.info("API request: import/datalocations: " + str(request.json))

        if 'data_locations_path' in request.json \
            and 'project_name' in request.json \
                and 'sample_matrix' in request.json \
                    and 'assay_platform' in request.json \
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
                args['username'] = request.json['username']
                args['project_name'] = request.json['project_name']
                args['data_locations_path'] = request.json['data_locations_path']

                if request.json['assay_platform'] == 'MS' and 'assay_name' not in request.json:
                    raise Exception("assay_name must be specified for MS")

                elif request.json['assay_platform'] == 'MS' and 'assay_name' in request.json:
                    args['assay_name'] = request.json['assay_name']
                    task_name = args['project_name'].replace('-','_') + "_MS_" + args['assay_name'].replace('-','_')

                    if db_session.query(Assay).filter(Assay.name==args['assay_name']).count() != 1:
                        raise Exception("Unrecognised assay_name")

                elif request.json['assay_platform'] == 'NMR':
                    task_name = args['project_name'].replace('-','_') + "_NMR"

                else:
                    raise Exception("Unknown assay_platform, must be NMR or MS")

                #pipeline = PipelineFactory('ImportDataLocations '+args['project_name'],'API Import Data Locations',tags=self.build_tags(request.json,'ImportDataLocations'),db_env=db_env)
                #pipeline.add_task('phenomedb.tasks.imports.import_data_locations','ImportDataLocations',task_name,args,depends_on_past=True)

                pipeline = PipelineFactory('API_ImportDataLocations',run_config=args,db_env=db_env)

                #if 'write_dag' not in request.json or request.json['write_dag'] == True:
                #    pipeline.submit()
                #    self.logger.info("new pipeline scheduled - " + pipeline.name)

                return self.response(200, message='Pipeline Running:' + pipeline.name)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')

    @expose("/peakpanther",methods=['POST'])
    @protect()
    def peakpanther(self):
        """Import peak panther annotations

        ---
        post:
          summary: Import PeakPantheR annotations
          parameters:
            - in: header
              name: username
              schema:
                type: string
              required: true
              description: The username of the person submitting
            - in: header
              name: project_name
              schema:
                type: string
              required: true
              description: The project name
            - in: header
              name: feature_metadata_csv_path
              schema:
                type: string
              required: true
              description: The path to the feature metadata file
            - in: header
              name: sample_metadata_csv_path
              schema:
                type: string
              required: true
              description: The path to the sample metadata file
            - in: header
              name: intensity_data_csv_path
              schema:
                type: string
              required: true
              description: The path to the intensity data file
            - in: header
              name: batch_corrected_data_csv_path
              schema:
                type: string
              required: false
              description: The path to the batch corrected data file
            - in: header
              name: sample_matrix
              schema:
                type: string
              required: true
              description: The sample_matrix (ie 'plasma', 'serum', 'urine')
            - in: header
              name: roi_version
              schema:
                type: string
              required: false
              description: The ROI version used for annotation
            - in: header
              name: all_features_feature_metadata_csv_path
              schema:
                type: string
              required: false
              description: feature metadata file with all the features (including those excluded)
            - in: header
              name: ppr_annotation_parameters_csv_path
              schema:
                type: string
              required: false
              description: The PPR output annotation_parameters.csv
            - in: header
              name: ppr_mz_csv_path
              schema:
                type: string
              required: false
              description: The PPR output mz.csv
            - in: header
              name: ppr_rt_csv_path
              schema:
                type: string
              required: false
              description: The PPR output rt.csv
            - in: header
              name: assay_name
              schema:
                type: string
              description: For MS, specify 'LNEG', 'LPOS', 'BANEG', 'HPOS', 'RPOS', 'RNEG'
          responses:
            200:
              description: ImportPeakPantheR pipeline created
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
        """

        self.logger.info("API request: import/peakpanther: " + str(request.json))

        if 'project_name' in request.json \
            and 'sample_matrix' in request.json \
                and 'assay_name' in request.json \
                    and 'feature_metadata_csv_path' in request.json \
                        and 'sample_metadata_csv_path' in request.json \
                            and 'intensity_data_csv_path' in request.json \
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
                args['username'] = request.json['username']
                args['project_name'] = request.json['project_name']
                args['sample_matrix'] = request.json['sample_matrix']
                args['assay_name'] = request.json['assay_name']
                args['feature_metadata_csv_path'] = request.json['feature_metadata_csv_path']
                args['sample_metadata_csv_path'] = request.json['sample_metadata_csv_path']
                args['intensity_data_csv_path'] = request.json['intensity_data_csv_path']

                if 'roi_version' in request.json:
                    args['roi_version'] = request.json['roi_version']

                if 'batch_corrected_data_csv_path' in request.json:
                    args['batch_corrected_data_csv_path'] = request.json['batch_corrected_data_csv_path']

                if 'all_features_feature_metadata_data_csv_path' in request.json:
                    args['all_features_feature_metadata_data_csv_path'] = request.json['all_features_feature_metadata_data_csv_path']

                if 'ppr_annotation_parameters_csv_path' in request.json:
                    args['ppr_annotation_parameters_csv_path'] = request.json['ppr_annotation_parameters_csv_path']

                if 'ppr_mz_csv_path' in request.json:
                    args['ppr_mz_csv_path'] = request.json['ppr_mz_csv_path']

                if 'ppr_rt_csv_path' in request.json:
                    args['ppr_rt_csv_path'] = request.json['ppr_rt_csv_path']

                #pipeline = PipelineFactory('ImportPeakPanther '+args['project_name'],'API Import PeakPantheR',tags=self.build_tags(request.json,'ImportPeakPantheR'),db_env=db_env)
                #pipeline.add_task('phenomedb.tasks.imports.import_peakpanther_annotations','ImportPeakPantherAnnotations',args['project_name'].replace('-','_') + "_" + args['assay_name'].replace('-','_'),args,depends_on_past=True)

                pipeline = PipelineFactory('API_ImportPeakPantherAnnotations',run_config=args,db_env=db_env)

                return self.response(200, message='Pipeline Name:' + pipeline.name)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')

    @expose("/targetlynx",methods=['POST'])
    @protect()
    def targetlynx(self):
        """Import targetlynx annotations

        ---
        post:
          summary: Import TargetLynx annotations
          parameters:
            - in: header
              name: username
              schema:
                type: string
              required: true
              description: The username of the person submitting
            - in: header
              name: project_name
              schema:
                type: string
              required: true
              description: The project name
            - in: header
              name: feature_metadata_csv_path
              schema:
                type: string
              required: true
              description: The path to the feature metadata file
            - in: header
              name: sample_metadata_csv_path
              schema:
                type: string
              required: true
              description: The path to the sample metadata file
            - in: header
              name: intensity_data_csv_path
              schema:
                type: string
              required: true
              description: The path to the intensity data file
            - in: header
              name: batch_corrected_data_csv_path
              schema:
                type: string
              required: true
              description: The path to the batch corrected data file
            - in: header
              name: sample_matrix
              schema:
                type: string
              required: true
              description: The sample_matrix (ie 'plasma', 'serum', 'urine')
            - in: header
              name: assay_name
              schema:
                type: string
              description: For MS, specify 'LNEG', 'LPOS', 'BANEG', 'HPOS', 'RPOS', 'RNEG'
          responses:
            200:
              description: ImportTargetLynx pipeline created
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
        """

        self.logger.info("API request: import/targetlynx: " + str(request.json))

        if 'project_name' in request.json \
            and 'sample_matrix' in request.json \
                and 'assay_name' in request.json \
                    and 'unified_csv_path' in request.json \
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
                args['username'] = request.json['username']
                args['project_name'] = request.json['project_name']
                args['sample_matrix'] = request.json['sample_matrix']
                args['assay_name'] = request.json['assay_name']
                args['unified_csv_path'] = request.json['unified_csv_path']

                if 'sop' in request.json:
                    args['sop'] = request.json['sop']
                if 'sop_version' in request.json:
                    args['sop_version'] = request.json['sop_version']
                if 'sop_file_path' in request.json:
                    args['sop_file_path'] = request.json['sop_file_path']

                #pipeline = PipelineFactory('ImportTargetLynx '+args['project_name'],'API Import TargetLynx',tags=self.build_tags(request.json,'ImportTargetLynx'),db_env=db_env)

                #pipeline.add_task('phenomedb.tasks.imports.import_targetlynx_annotations','ImportTargetLynxAnnotations',args['project_name'].replace('-','_') + "_" + args['assay_name'].replace('-','_'),args,depends_on_past=True)

                pipeline = PipelineFactory('API_ImportTargetlynxAnnotations',run_config=args,db_env=db_env)

                return self.response(200, message='Pipeline Name:' + pipeline.name)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')

    @expose("/brukerivdr",methods=['POST'])
    @protect()
    def brukerivdr(self):
        """Import brukerivdr annotations

        ---
        post:
          summary: Import Bruker IVDr annotations
          parameters:
            - in: header
              name: username
              schema:
                type: string
              required: true
              description: The username of the person submitting
            - in: header
              name: project_name
              schema:
                type: string
              required: true
              description: The project name
            - in: header
              name: unified_csv_path
              schema:
                type: string
              required: true
              description: The path to the unified csv file
            - in: header
              name: sample_matrix
              schema:
                type: string
              required: true
              description: The sample_matrix (ie 'plasma', 'serum', 'urine')
            - in: header
              name: annotation_method
              schema:
                type: string
              description: BI-LISA or BI-QUANT
          responses:
            200:
              description: ImportBrukerIVDr pipeline created
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
        """

        self.logger.info("API request: import/brukerivdr: " + str(request.json))

        if 'project_name' in request.json \
            and 'sample_matrix' in request.json \
                and 'annotation_method' in request.json \
                    and 'unified_csv_path' in request.json \
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
                args['username'] = request.json['username']
                args['sample_matrix'] = request.json['sample_matrix']
                args['annotation_method_name'] = request.json['annotation_method']
                args['unified_csv_path'] = request.json['unified_csv_path']

                #pipeline = PipelineFactory('ImportBrukerIVDr '+args['project_name'],'API BrukerIVDr',tags=self.build_tags(request.json,'ImportBrukerIVDr'),db_env=db_env)

                #pipeline.add_task('phenomedb.tasks.imports.import_bruker_ivdr_annotations','ImportBrukerIVDRAnnotations',args['project_name'].replace('-','_') + "_" + args['annotation_method_name'].replace('-','_'),args,depends_on_past=True)
                pipeline = PipelineFactory('API_ImportBrukerIVDr',run_config=args,db_env=db_env)

                #if 'write_dag' not in request.json or request.json['write_dag'] == True:
                #    pipeline.submit()
                #    self.logger.info("new pipeline scheduled - " + pipeline.name)

                return self.response(200, message='Pipeline Name:' + pipeline.name)

            except Exception as err:
                self.logger.exception(err)
                print(err)
                return self.response(500, message=str(err))
        else:
            return self.response(400,message='fields must match spec')


appbuilder.add_api(Import)


