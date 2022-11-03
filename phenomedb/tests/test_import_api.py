import pytest

import sys,os
import json
from pathlib import Path

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

import os
from phenomedb.config import config
import requests

class TestImportAPI():

    devset_sample_manifest = config['DATA']['test_data'] + '/DEVSET_sampleManifest.xlsx',
    devset_data_locations_nmr = config['DATA']['test_data'] + '/DEVSET_datalocations_NMR.csv',
    devset_data_locations_ms = config['DATA']['test_data'] + '/DEVSET_LPOS_data_locations.csv',


    def test_b_import_samplemanifest(self,create_min_database,
                                     create_pipeline_testing_project,
                                     get_api_access_token):
        '''
            Method to test scheduling an import sample manifest task - should return 200
        :return:
        '''

        print(get_api_access_token)

        data = {"project_name":"PipelineTesting",
                "sample_manifest_path": self.devset_sample_manifest,
                "columns_to_ignore":[],
                "username": "test",
                "write_dag": True,
                "db_env":"TEST",
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/samplemanifest',
                              json=data,
                              headers={'Authorization': 'Bearer '+ get_api_access_token})

        print(json.loads(r.content))

        assert r.status_code == 200

    def test_c_import_with_unknown_project(self,create_min_database,
                                           create_pipeline_testing_project,
                                           get_api_access_token):
        '''
            Method to test passing an unknown project - should return 500
        :return:
        '''

        data = {"project_name":"PipelineTesting1212",
                "sample_manifest_path": self.devset_sample_manifest,
                "columns_to_ignore":[],
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/samplemanifest',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})

        print(json.loads(r.content))

        assert r.status_code == 500

    def test_d_import_data_locations_nmr(self,create_min_database,
                                         create_pipeline_testing_project,
                                         get_api_access_token):
        '''
            Method to test importing a data locations NMR - should return 200
        :return:
        '''

        data = {"project_name":"PipelineTesting",
                "data_locations_path":self.devset_data_locations_nmr,
                "assay_platform":"NMR",
                "sample_matrix": "urine",
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/datalocations',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})
        print(json.loads(r.content))
        assert r.status_code == 200

    def test_d_import_data_locations_ms(self,create_min_database,
                                        create_pipeline_testing_project,
                                        import_devset_sample_manifest,
                                        create_lab,
                                        create_ms_assays,
                                        get_api_access_token):
        '''
            Method to test importing a data locations MS - should return 200
        :return:
        '''

        data = {"project_name":"PipelineTesting",
                "data_locations_path":self.devset_data_locations_ms,
                "assay_platform":"MS",
                "assay_name":"LNEG",
                "sample_matrix": "urine",
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/datalocations',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})
        print(json.loads(r.content))
        assert r.status_code == 200

    def test_h_import_peakpanther_missing_fields(self,create_min_database,

                                            get_api_access_token):
        '''
            Method to test importing peakpanther - missing fields - should return 400
        :return:
        '''

        data = {"project_name":"PipelineTesting",
                "assay_name":"HPOS",
                "sample_matrix": "urine",
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/peakpanther',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})
        print(json.loads(r.content))
        assert r.status_code == 400

    def test_e_import_data_locations_ms_no_assay_name(self,create_min_database,
                                                      create_pipeline_testing_project,
                                                      create_lab,
                                                      create_ms_assays,
                                                      import_devset_sample_manifest,
                                                      get_api_access_token):
        '''
            Method to test importing a data locations MS with missing assay_name - should return 500
        :return:
        '''

        data = {"project_name":"PipelineTesting",
                "data_locations_path":self.devset_data_locations_ms,
                "assay_platform":"MS",
                "sample_matrix": "urine",
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/datalocations',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})

        print(json.loads(r.content))

        assert r.status_code == 500

    def test_f_import_peakpanther(self,create_min_database,
                                  create_pipeline_testing_project,
                                  import_devset_sample_manifest,
                                  create_lab,
                                  create_ms_assays,
                                  create_annotation_methods,
                                  get_api_access_token):
        '''
            Method to test importing peakpanther - should return 200
        :return:
        '''

        project_name = "PipelineTesting"
        sample_matrix="serum"
        assay_name="LPOS"

        feature_metadata_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_featureMetadata.csv',
        sample_metadata_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_sampleMetadata.csv',
        intensity_data_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_intensityData.csv',

        username = 'admin'

        data = {'project_name':project_name,
                'sample_matrix':sample_matrix,
                'assay_name':assay_name,
                'feature_metadata_csv_path':feature_metadata_csv_path,
                'sample_metadata_csv_path':sample_metadata_csv_path,
                'intensity_data_csv_path': intensity_data_csv_path,
                'roi_version': 3.1,
                'username':username}

        r = requests.post('http://localhost:5000/custom/api/v1/import/peakpanther',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})

        print(json.loads(r.content))
        assert r.status_code == 200

    def test_i_import_targetlynx(self,create_min_database,
                                 create_pipeline_testing_project,
                                 import_devset_sample_manifest,
                                 create_lab,
                                 create_nmr_assays,
                                 create_annotation_methods,
                                 get_api_access_token):
        '''
            Method to test importing targetlynx - should return 200
        :return:
        '''

        data = {"project_name":"PipelineTesting",
                "assay_name":"LC-QqQ Amino Acids",
                "sample_matrix": "plasma",
                "unified_csv_path": config['DATA']['test_data'] + 'DEVSET BileAcid Plasma_combinedData.csv',
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/targetlynx',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})
        print(json.loads(r.content))
        assert r.status_code == 200


    def test_j_import_bruker_ivdr(self,create_min_database,
                                  create_pipeline_testing_project,
                                  import_devset_sample_manifest,
                                  create_lab,
                                  create_nmr_assays,
                                  create_annotation_methods,
                                  get_api_access_token):
        '''
            Method to test importing peakpanther - missing fields - should return 400
        :return:
        '''

        data = {"project_name":"PipelineTesting",
                "annotation_method":"BI-LISA",
                "unified_csv_path": config['DATA']['test_data'] + 'DEVSET_P_BILISA_combinedData.csv',
                "sample_matrix":"plasma",
                "username": "test",
                "db_env":"TEST",
                "write_dag": False,
                #"username":config['HPC_ACCOUNT']['username']
                }

        r = requests.post('http://localhost:5000/custom/api/v1/import/brukerivdr',
                              json=data,
                              headers={'Authorization': 'Bearer '+get_api_access_token})
        print(json.loads(r.content))
        assert r.status_code == 200
