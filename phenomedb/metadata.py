from random import *
import datetime
from pathlib import Path
import numpy as np
from nPYc.enumerations import *
import pandas as pd
from phenomedb.imports import ImportTask
from phenomedb.utilities import *
import math
import importlib
import time
import datetime
import os
from dateutil import parser
from phenomedb.models import *
from phenomedb.exceptions import *


class HarmoniseMetadataField(ImportTask):
    """AutoHarmoniseMetadataField Class. Takes a project metadata field and harmonised metadata field, and applies a lambda
    function to transform the raw data into the harmonised one.

    :param task_options: A dictionary containing the task options
    :type task_options: dict

    """

    use_inbuilt = False

    def __init__(self,project_name=None,metadata_field_name=None,harmonised_metadata_field_name=None,inbuilt_transform_name=None,pipeline_run_id=None,
                 lambda_function_string='lambda x : x',allowed_decimal_places=None,allowed_data_range=None,task_run_id=None,username=None,db_env=None,execution_date=None,db_session=None):
        """Constructor method
        """
        super().__init__(project_name=project_name,username=username,task_run_id=task_run_id,db_env=db_env,execution_date=execution_date,db_session=db_session,pipeline_run_id=pipeline_run_id)

        self.metadata_field_name = metadata_field_name
        self.harmonised_metadata_field_name = harmonised_metadata_field_name
        self.lambda_function_string = lambda_function_string
        self.inbuilt_transform_name = inbuilt_transform_name

        if allowed_data_range and isinstance(allowed_data_range,list) and len(allowed_data_range) == 2:
            self.allowed_data_range = allowed_data_range
        else:
            self.allowed_data_range = None

        if allowed_decimal_places and isinstance(allowed_decimal_places,int):
            self.allowed_decimal_places = allowed_decimal_places
        else:
            self.allowed_decimal_places = None

        self.missing_import_data = []
        self.args['metadata_field_name'] = metadata_field_name
        self.args['harmonised_metadata_field_name'] = harmonised_metadata_field_name
        self.args['lambda_function_string'] = lambda_function_string
        self.args['inbuilt_transform_name'] = inbuilt_transform_name
        self.args['allowed_data_range'] = allowed_data_range
        self.args['allowed_decimal_places'] = allowed_decimal_places

        self.get_class_name(self)

    def check_functions(self):
        """Check the functions
        """        

        if self.inbuilt_transform_name:
            # Check it exists
            try:
                exec('from phenomedb.metadata import ' + self.inbuilt_transform_name)
            except Exception:
                error_message = 'The transform function does not exist: ' + self.inbuilt_transform_name
                self.logger.exception(error_message)
                raise Exception(error_message)

            self.use_inbuilt = True
            self.logger.info("Inbuilt transform function used: " + self.inbuilt_transform_name)

        elif self.lambda_function_string:
            # Try and evaluate it
            try:
                self.lambda_function = eval(self.lambda_function_string)

            except Exception:
                error_message = 'The lambda function was not evaluable: ' + self.lambda_function_string
                self.logger.exception(error_message)
                raise Exception(error_message)

            self.logger.info("Lambda function used: " + self.lambda_function_string)

        else:

            self.logger.error('No lambda or inbuilt function set')
            raise Exception('No lambda or inbuilt function set' )


    def load_dataset(self):
        """Load the dataset

        """

        self.harmonised_metadata_field = self.db_session.query(HarmonisedMetadataField).filter(
            HarmonisedMetadataField.name == self.harmonised_metadata_field_name).first()

        if not self.harmonised_metadata_field:
            error = "No HarmonisedMetadataField.name == " + self.harmonised_metadata_field_name
            self.logger.error(error)
            raise Exception(error)

        if self.metadata_field_name:

            self.metadata_field = self.db_session.query(MetadataField) \
                .filter(MetadataField.project_id==self.project.id) \
                .filter(MetadataField.name==self.metadata_field_name).first()

            if not self.metadata_field:
                error = "No MetadataField.name == " + self.metadata_field_name + " for project " + str(self.project.id)
                self.logger.error(error)
                raise Exception(error)

            self.metadata_values = self.db_session.query(MetadataValue) \
                .filter(MetadataValue.metadata_field_id == self.metadata_field.id)

        else:
            self.metadata_field = MetadataField(name='dummy_%s' % self.metadata_field_name,
                                                project_id=self.project.id)
            self.db_session.add(self.metadata_field)
            self.db_session.flush()
            self.metadata_values = []
            if self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
                default_raw = ''
            elif self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
                default_raw = 0
            elif self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:
                default_raw = datetime.datetime.now()

            samples = self.db_session.query(Sample).join(Subject).filter(Subject.project_id==self.project.id).all()

            for sample in samples:
                self.metadata_values.append(MetadataValue(sample_id=sample.id,raw_value=default_raw,metadata_field_id=self.metadata_field.id))
            self.db_session.add_all(self.metadata_values)
            self.db_session.flush()

        self.metadata_field.harmonised_metadata_field_id = self.harmonised_metadata_field.id

    def map_and_add_dataset_data(self):
        """Map and add dataset data
        """        

        for metadata_value in self.metadata_values:
            try:

                if self.use_inbuilt:
                    metadata_value = self.call_inbuilt_transform(metadata_value)

                else:
                    metadata_value = self.call_lambda(metadata_value)

            except MetadataHarmonisationError as err:
                self.logger.exception(err)
                missing_import_data = MissingImportData(task_run_id=self.task_run.id,
                                                        type='MetadataValue.harmonised_value',
                                                        value=metadata_value.raw_value,
                                                        comment="Metadata could not be harmonised")
                self.db_session.add(missing_import_data)
                self.db_session.flush()
                self.missing_import_data.append(missing_import_data)

            except Exception as err:
                self.logger.exception("The harmonised value could not be calculated - raw value: " + str(metadata_value.raw_value))
                raise Exception(err)

    def call_lambda(self,metadata_value):

        if self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
            metadata_value.harmonised_text_value = str(self.lambda_function(str(metadata_value.raw_value)))
            self.logger.info("Harmonised " + str(metadata_value.raw_value) + " to " + str(metadata_value.harmonised_text_value))

        elif self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
            metadata_value.harmonised_numeric_value = float(self.lambda_function(float(metadata_value.raw_value)))
            self.logger.info("Harmonised " + str(metadata_value.raw_value) + " to " + str(metadata_value.harmonised_numeric_value))

        elif self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:
            metadata_value.harmonised_datetime_value = self.lambda_function(metadata_value.raw_value)
            self.logger.info("Harmonised " + str(metadata_value.raw_value) + " to " + str(metadata_value.harmonised_datetime_value))

        return metadata_value

    def call_inbuilt_transform(self,metadata_value):

        module = importlib.import_module('phenomedb.metadata')

        transform_function = getattr(module, self.inbuilt_transform_name)

        metadata_value = transform_function(metadata_value,self.harmonised_metadata_field.datatype,self.allowed_data_range,self.allowed_decimal_places,db_session=self.db_session,db_env=self.db_env)

        if self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
            self.logger.info("Curated " + str(metadata_value.raw_value) + " to " + str(metadata_value.harmonised_text_value))
        elif self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
            self.logger.info("Curated " + str(metadata_value.raw_value) + " to " + str(metadata_value.harmonised_numeric_value))
        elif self.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:
            self.logger.info("Curated " + str(metadata_value.raw_value) + " to " + str(metadata_value.harmonised_datetime_value))

        return metadata_value

    def process(self):

        self.check_functions()
        super().process()


    def basic_validation(self):

        super().basic_validation()
        self.logger.info("The following metadata_values could not be harmonised: " + str(self.missing_import_data))

    def task_validation(self):
        pass
        #if len(self.missing_import_data) > 0:
        #    raise ValidationError("Not all values could be harmonised %s" % self.missing_import_data)

# All functions must take db_session and metadata_value
# Metadata value contains sample_id. From this we have everything from the project down,
# including subjects, other metadata fields, etc. We can even pull out other metadata fields if necessary (although
# harmonised ones would be easier

def transform_dob_and_sampling_date_to_age(metadata_value,datatype,allowed_data_range,allowed_decimal_places,db_session=None,db_env=None):
    """Method to transform date of birth and sampling date into a harmonised numeric age. Requires Sample.sample_date to exists.

    :param metadata_value: The MetadataValue object.
    :type metadata_value: :class:`phenomedb.models.MetadataValue`
    :param datatype: The HarmonisedMetadataField.datatype.
    :type datatype: :class:`phenomedb.models.HarmonisedMetadataField.HarmonisedMetadataFieldDatatype`
    :param allowed_data_range: A constraint to prevent values outside of this allowed range.
    :type allowed_data_range: list
    :param allowed_decimal_places: How many decimal places are allowed.
    :type allowed_decimal_places: int
    :param db_session: The db_session to use, defaults to None.
    :type db_session: :class:`sqlalchemy.orm.session`, optional
    :param db_env: The db_env to use, 'PROD', 'BETA', or 'TEST', defaults to None ('PROD').
    :type db_env: str, optional
    :raises MetadataHarmonisationError: If the transform cannot work, raise this Exception.
    :return: The transformed, harmonised MetadataValue object.
    :rtype: :class:`phenomedb.models.MetadataValue`
    """
    if not db_session:
        db_session = db.get_db_session(db_env=db_env)
    sample = db_session.query(Sample).filter(Sample.id==metadata_value.sample_id).first()

    if sample.sampling_date is None:
        raise MetadataHarmonisationError('No sampling date for this sample: ' + str(sample.id))

    date_of_birth = parser.parse(metadata_value.raw_value)
    sampling_date = sample.sampling_date
    delta = sampling_date - date_of_birth
    days_in_year = 365
    no_of_leaps = round((delta.days / 4) / days_in_year)
    years = round(delta.days / days_in_year)
    remaining_days = delta.days % days_in_year

    harmonised_value = math.floor(years - (no_of_leaps / days_in_year) + (remaining_days/ days_in_year))

    if allowed_data_range:
        if harmonised_value >= allowed_data_range[0] and harmonised_value <= allowed_data_range[1]:
            metadata_value.harmonised_numeric_value = harmonised_value
        else:
            raise MetadataHarmonisationError("Harmonised value not within allowed range: " + str(harmonised_value) + " - " + str(allowed_data_range))
    else:
        metadata_value.harmonised_numeric_value = harmonised_value
    return metadata_value

def simple_assignment(metadata_value,datatype,allowed_data_range,allowed_decimal_places,db_session=None,db_env=None):
    """ Method for simple assignment of data from raw to harmonised. Uses the HarmonisedMetadataField.datatype to cast to correct harmonised value.

    :raises MetadataHarmonisationError: If the transform cannot work, raise this Exception.
    :return: The transformed, harmonised MetadataValue object.
    :rtype: :class:`phenomedb.models.MetadataValue`
    """

    if datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
        metadata_value.harmonised_text_value = str(metadata_value.raw_value)

    elif datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:

        if utils.is_number(metadata_value.raw_value):

            if allowed_data_range:
                if float(metadata_value.raw_value) >= allowed_data_range[0] and float(metadata_value.raw_value) <= allowed_data_range[1]:
                    pass
                else:
                    raise MetadataHarmonisationError("Harmonised value not within allowed range: " + str(metadata_value.raw_value) + " - " + str(allowed_data_range))

            if utils.isint(metadata_value.raw_value):
                metadata_value.harmonised_numeric_value = int(float(metadata_value.raw_value))
            else:
                if allowed_decimal_places:
                    metadata_value.harmonised_numeric_value = round(float(metadata_value.raw_value),allowed_decimal_places)
                else:
                    metadata_value.harmonised_numeric_value = float(metadata_value.raw_value)

    elif datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:

        metadata_value.harmonised_datetime_value = parser.parse(metadata_value.raw_value)

    return metadata_value

def categorise_bmi(metadata_value,datatype,allowed_data_range,allowed_decimal_places,db_session=None,db_env=None):

    raw_value = None

    #1. Check it is numeric
    if utils.is_number(metadata_value.raw_value):
        raw_value = float(metadata_value.raw_value)
    else:
        raise MetadataHarmonisationError("Harmonised value not a number: %s" % metadata_value.raw_value)

    if raw_value:

        if raw_value < 18.5:
            metadata_value.harmonised_text_value = 'Underweight'
        elif raw_value < 24.9:
            metadata_value.harmonised_text_value = 'Healthy'
        elif raw_value < 29.9:
            metadata_value.harmonised_text_value = 'Overweight'
        else:
            metadata_value.harmonised_text_value = 'Obese'

    return metadata_value