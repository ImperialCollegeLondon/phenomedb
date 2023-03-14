import unittest

import sys,os
import json
from pathlib import Path

#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])

import os
from phenomedb.config import config
import requests
import pytest

class TestModelAPI():

    def test_b_get_project(self,create_min_database,
                           create_pipeline_testing_project,
                           get_api_access_token):
        '''
            Method to test getting a project - should return 200
        :return:
        '''


        r = requests.get('http://localhost:5000/custom/api/v1/project/1',
                        headers={'Authorization': 'Bearer '+get_api_access_token})

        content = json.loads(r.content)

        assert r.status_code == 200

