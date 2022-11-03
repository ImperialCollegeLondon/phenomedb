import unittest

import sys,os
import json
from pathlib import Path
import datetime

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config

import requests
from requests.auth import HTTPBasicAuth

class TestDAGS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        data = {"username":config['HPC']['user'],
                "password":config['HPC']['password'],
                "provider": 'db'}

        cls.session = requests.session()
        r = cls.session.post('http://localhost:8080/api/v1/security/login', json=data)
        response = json.loads(r.content)
        print(response)
        cls.access_token = response['access_token']

    def test_a_login(self):
        '''
            Method to test whether we have been successful logging in
        :return:
        '''
        self.assertIsNotNone(self.access_token)

    def test_b_import_samplemanifest(self):
        '''
            Method to test scheduling an import sample manifest task - should return 200
        :return:
        '''

        r = self.session.get('http://localhost:8080/api/v1/dags',
                             auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                            headers={'Content-Type':'application/json'})

        body = json.loads(r.content)

        print(body)

        dag_id = 'API_ImportSampleManifest'

        found_dag = False
        for dag in body['dags']:
            if dag['dag_id'] == dag_id:
                found_dag = True

        self.assertTrue(found_dag)

        params = {"project_name":"PipelineTesting",
                  "sample_manifest_path": config['DATA']['test_data'] + '/sample_manifests/DEVSET_sampleManifest.xlsx',
                  "columns_to_ignore":[],
                  "username": "test",
                  "db_env":"TEST",
                  #"username":config['HPC']['user']
                  }

        data = {
            #"execution_date": datetime.datetime.now().strftime("%Y-%m-%dY%H:%M:%S%Z"),
            "conf": params,
        }

        r = self.session.post('http://localhost:8080/api/v1/dags/'+str(dag_id)+"/dagRuns",
                              json=data,
                              auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                              headers={'Content-Type':'application/json'})

        print(json.loads(r.content))

        self.assertEqual(r.status_code,200)

    def test_c_import_datalocations(self):
        '''
            Method to test scheduling an import sample manifest task - should return 200
        :return:
        '''

        r = self.session.get('http://localhost:8080/api/v1/dags',
                             auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                             headers={'Content-Type':'application/json'})

        body = json.loads(r.content)

        dag_id = 'API_ImportDataLocations'

        found_dag = False
        for dag in body['dags']:
            if dag['dag_id'] == dag_id:
                found_dag = True

        self.assertTrue(found_dag)

        params = {"project_name":"PipelineTesting",
                "data_locations_path":"../test/manifest/path",
                "assay_platform":"NMR",
                "sample_matrix": "urine",
                "username": "test",
                "db_env":"TEST",
                #"username":config['HPC']['user']
                }


        data = {
            "conf": params,
            #'dag_run_id': 'unique_id'
        }

        r = self.session.post('http://localhost:8080/api/v1/dags/'+str(dag_id)+"/dagRuns",
                              json={'conf':params},
                              auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                              headers={'Content-Type':'application/json'})

        print(json.loads(r.content))

        self.assertEqual(r.status_code,200)

    def test_d_import_bruker_ivdr(self):
        '''
            Method to test scheduling an import sample manifest task - should return 200
        :return:
        '''

        r = self.session.get('http://localhost:8080/api/v1/dags',
                             auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                             headers={'Content-Type':'application/json'})

        body = json.loads(r.content)

        dag_id = 'API_ImportBrukerIVDrAnnotations'

        found_dag = False
        for dag in body['dags']:
            if dag['dag_id'] == dag_id:
                found_dag = True

        self.assertTrue(found_dag)

        params = {"project_name":"PipelineTesting",
                "annotation_method":"BI-LISA",
                "sample_matrix": "plasma",
                "unified_csv_path": "../..testpth",
                "username": "test",
                "db_env":"TEST"}


        data = {
            "conf": params,
            #'dag_run_id': 'unique_id'
        }

        r = self.session.post('http://localhost:8080/api/v1/dags/'+str(dag_id)+"/dagRuns",
                              json={'conf':params},
                              auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                              headers={'Content-Type':'application/json'})

        print(json.loads(r.content))

        self.assertEqual(r.status_code,200)

    def test_e_import_targetlynx(self):
        '''
            Method to test scheduling an import sample manifest task - should return 200
        :return:
        '''

        r = self.session.get('http://localhost:8080/api/v1/dags',
                             auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                             headers={'Content-Type':'application/json'})

        body = json.loads(r.content)

        dag_id = 'API_ImportTargetlynxAnnotations'

        found_dag = False
        for dag in body['dags']:
            if dag['dag_id'] == dag_id:
                found_dag = True

        self.assertTrue(found_dag)

        params = {"project_name":"PipelineTesting",
                  "assay_name":"LC-QqQ Amino Acids",
                  "sample_matrix": "plasma",
                  "unified_csv_path": "../..testpth",
                  "username": "test",
                  "db_env":"TEST"}

        data = {
            "conf": params,
            #'dag_run_id': 'unique_id'
        }

        r = self.session.post('http://localhost:8080/api/v1/dags/'+str(dag_id)+"/dagRuns",
                              json={'conf':params},
                              auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                              headers={'Content-Type':'application/json'})

        print(json.loads(r.content))

        self.assertEqual(r.status_code,200)

    def test_f_import_peakpanther(self):
        '''
            Method to test scheduling an import sample manifest task - should return 200
        :return:
        '''

        r = self.session.get('http://localhost:8080/api/v1/dags',
                             auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                             headers={'Content-Type':'application/json'})

        body = json.loads(r.content)

        dag_id = 'API_ImportPeakPantherAnnotations'

        found_dag = False
        for dag in body['dags']:
            if dag['dag_id'] == dag_id:
                found_dag = True

        self.assertTrue(found_dag)

        params = {"project_name":"PipelineTesting",
                  "feature_metadata_csv_path":"../test/manifest/path",
                  "sample_metadata_csv_path":"../test/manifest/path",
                  "intensity_data_csv_path":"../test/manifest/path",
                  "batch_corrected_data_csv_path":"../test/manifest/path",
                  "assay_name":"MS",
                  "sample_matrix": "urine",
                  "username": "test",
                  "db_env":"TEST"}


        data = {
            "conf": params,
            #'dag_run_id': 'unique_id'
        }

        r = self.session.post('http://localhost:8080/api/v1/dags/'+str(dag_id)+"/dagRuns",
                              json={'conf':params},
                              auth = HTTPBasicAuth(config['HPC']['user'], config['HPC']['password']),
                              headers={'Content-Type':'application/json'})

        print(json.loads(r.content))

        self.assertEqual(r.status_code,200)


if __name__ == '__main__':
    unittest.main()