import pytest
from pathlib import Path

import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config

from phenomedb.models import *
from phenomedb.metadata import HarmoniseMetadataField

class TestCurateMetadata():
    """TestCurateMetadata class.
    """

    project_name = 'PipelineTesting'

    def test_alambda(self,create_min_database,
                                          create_pipeline_testing_project,
                                          create_age_sex_harmonised_fields,
                                          import_devset_sample_manifest):
        # Add units and metadata harmonised field
        task = HarmoniseMetadataField(project_name=self.project_name,
                                    metadata_field_name='Age',
                                    harmonised_metadata_field_name='Age',
                                    lambda_function_string="lambda x : x",
                                      db_env='TEST')

        output = task.run()

        assert 'counts' in output

    def test_simple_curate_age(self,create_min_database,
                               create_pipeline_testing_project,
                               create_age_sex_harmonised_fields,
                               import_devset_sample_manifest):

        # Add units and metadata harmonised field
        task = HarmoniseMetadataField(project_name=self.project_name,
                                       metadata_field_name='Age',
                                       harmonised_metadata_field_name='Age',
                                       inbuilt_transform_name='simple_assignment',
                                      db_env='TEST')

        output = task.run()

        assert 'counts' in output


    def test_transform_dob_and_sampling_date(self,create_min_database,
                                             create_pipeline_testing_project,
                                             create_age_sex_harmonised_fields,
                                             import_devset_sample_manifest):

        # Add units and metadata harmonised field
        task = HarmoniseMetadataField(project_name=self.project_name,
                                       metadata_field_name="DOB",
                                       harmonised_metadata_field_name='Age',
                                       inbuilt_transform_name='transform_dob_and_sampling_date_to_age',
                                      db_env='TEST')

        output = task.run()

        assert 'counts' in output
