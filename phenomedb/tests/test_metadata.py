import pytest
import random

import pandas as pd

import sys, os

import metadata

 #if os.environ['PHENOMEDB_PATH'] not in sys.path:
 #   sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *
from phenomedb.query_factory import *
from phenomedb.metadata import *

from phenomedb.config import config

DB_ENV = "TEST"
PROJECT_NAME = "PipelineTesting"
LAB_NAME = "TestLab"
LAB_AFFILIATION = "TestUniversity"
USERNAME = config['PIPELINES']['pipeline_manager_user']

db_session = db.get_test_database_session()

class TestMetadata:
    """TestTasks class. Tests the output of the import task classes with test configurations
    """


    def test_bmi(self):
        """Tests the sample manifest importer. Checks the counts and whether the models have been made.

        :param create_min_database:
        :param create_pipeline_testing_project:
        :param import_devset_sample_manifest:
        :return:
        """

        #metadata_value = MetadataValue(raw_value='None')
        #pytest.raises(MetadataHarmonisationError,metadata.categorise_bmi,*{metadata_value,'text',10,10})

        metadata_value = MetadataValue(raw_value='6')
        harmonised = metadata.categorise_bmi(metadata_value,'text',10,10)
        assert harmonised.harmonised_text_value == 'Underweight'

        metadata_value = MetadataValue(raw_value='19')
        harmonised = metadata.categorise_bmi(metadata_value, 'text', 10, 10)
        assert harmonised.harmonised_text_value == 'Healthy'

        metadata_value = MetadataValue(raw_value='24')
        harmonised = metadata.categorise_bmi(metadata_value, 'text', 10, 10)
        assert harmonised.harmonised_text_value == 'Healthy'

        metadata_value = MetadataValue(raw_value='28')
        harmonised = metadata.categorise_bmi(metadata_value, 'text', 10, 10)
        assert harmonised.harmonised_text_value == 'Overweight'

        metadata_value = MetadataValue(raw_value="36.51")
        harmonised = metadata.categorise_bmi(metadata_value, 'text', 10, 10)
        assert harmonised.harmonised_text_value == 'Obese'
