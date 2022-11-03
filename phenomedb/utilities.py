import os,sys
import logging

import re

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append(os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config
from nPYc.enumerations import *
import datetime
import sqlalchemy
import json
import smtplib
import math
from email.mime.text import MIMEText
from phenomedb.exceptions import *
import numpy as np
import pandas as pd
from decimal import Decimal
import subprocess

class CustomEncoder(json.JSONEncoder):
    """ Custom encoder for numpy data types """
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):

            return int(obj)

        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64, Decimal)):
            return float(obj)

        elif isinstance(obj, (np.complex_, np.complex64, np.complex128)):
            return {'real': obj.real, 'imag': obj.imag}

        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()

        elif isinstance(obj, (np.bool_)):
            return bool(obj)

        elif isinstance(obj, (np.void)):
            return None

        elif isinstance(obj, (pd.Series, pd.DataFrame)):
            return obj.to_dict()
        else:
            print(obj)
            print(type(obj))

        return json.JSONEncoder.default(self, obj)


def configure_logging(identifier='phenomedb', log_file='phenomedb.log', level=logging.INFO):
    """Setup a logger.

    :param identifier: an identifier for your messages in the log, defaults to 'phenomedb'.
    :type identifier: str, optional
    :param log_file: file to log to at location specified in config.ini; (will create this dir if necessary), defaults to 'phenomedb.log'.
    :type log_file: str, optional
    :param level: log level, logging.INFO, logging.ERROR, logging.WARNING, defaults to logging.DEBUG.
    :type level: int, optional
    :return: the logger.
    :rtype: :class:`logging.logger`
    """    
    
    logger = None
    try:

        logger = logging.getLogger(identifier)

        log_dir =  config['LOGGING']['dir']

        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')

        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, log_file)
        log_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8", delay=False)
        log_handler.setFormatter(formatter)
        log_handler.setLevel(level)
        logger.addHandler(log_handler)

        print("Initialised " + identifier + " to log to", log_file)

    except OSError as e:
        print('Error configuring logging', e)
    return logger
               
def get_npyc_enum_from_value(value):
    """Get the nPYc enum from the value.

    :param value: the value of the enum.
    :type value: :class:`nPYc.enumerations.AssayRole` or :class:`nPYc.enumerations.SampleType` or :class:`nPYc.enumerations.QuantificationType` or :class:`nPYc.enumerations.CalibrationMethod`
    :return: The corresponding enum.
    :rtype: :class:`nPYc.enumerations.AssayRole` or :class:`nPYc.enumerations.SampleType` or :class:`nPYc.enumerations.QuantificationType` or :class:`nPYc.enumerations.CalibrationMethod`
    """

    if not value:
        return None

    if isinstance(value, (SampleType,AssayRole,QuantificationType)):
        return value

    elif isinstance(value,str):
        if value.lower().replace(" ","") in ['sampletype.studyreference','sampletype.studypool','studypool','studyreference']:
            return SampleType.StudyPool

        elif value.lower().replace(" ","") in ['sampletype.externalreference','externalreference','longtermreference']:
            return SampleType.ExternalReference

        elif value.lower().replace(" ","") in ['sampletype.studysample','studysample','experimentalsample','sample']:
            return SampleType.StudySample

        elif value.lower().replace(" ","") in ['assayrole.precisionreference','precisionreference']:
            return AssayRole.PrecisionReference

        elif value.lower().replace(" ","") in ['assayrole.linearityreference','linearityreference']:
            return AssayRole.LinearityReference

        elif value.lower().replace(" ","") in ['assayrole.assay','assay']:
            return AssayRole.Assay

        elif value == "Quantified and validated with own labeled analogue":
            return QuantificationType.QuantOwnLabeledAnalogue

        elif value == "Quantified and validated with alternative labeled analogue":
            return QuantificationType.QuantAltLabeledAnalogue

        elif value in ['Other quantification','Quantified without labeled analogue']:
            return QuantificationType.QuantOther

        elif value == 'Monitored for relative information':
            return QuantificationType.Monitored

        elif value == 'No calibration':
            return CalibrationMethod.noCalibration

        elif value in ["No Internal Standard",'Backcalculated without Internal Standard']:
            return CalibrationMethod.noIS

        elif value == 'Backcalculated with Internal Standard':
            return CalibrationMethod.backcalculatedIS

        elif value == 'Other calibration method':
            return CalibrationMethod.otherCalibration

        else:
            raise NotImplementedError("NPYC enum not recognised - %s" % value)
    else:
        raise NotImplementedError("NPYC enum not recognised - %s" % value)

def is_number(s):
    """Check if is number.

    :param s: value to check.
    :type s: float, int, or str
    :return: True or False.
    :rtype: boolean
    """    
    try:
        float(s)
        return True
    except ValueError:
        return False

def isfloat(x):
    """Check is a float.

    :param x: value to check.
    :type x: float, int, or str
    :return: True or False.
    :rtype: boolean
    """    
    try:
        a = float(x)
    except (TypeError, ValueError):
        return False
    else:
        return True

def isint(x):
    """Check if is an integer.

    :param x: value to check.
    :type x: float, int, or str
    :return: True or False.
    :rtype: boolean
    """    
    try:
        a = float(x)
        b = int(a)
    except (TypeError, ValueError):
        return False
    else:
        return a == b


def flatten_model_for_search(model):
    """Flatten an SQLAlchemy model for the search index. Takes a model and returns a paragraph containing the values.

    :param model: The model to flatten.
    :type model: :class:`phenomedb.models.*`
    :return: The whitespace seperated values.
    :rtype: str
    """        

    document = ""
    for field,value in model.__dict__.items():
        if not isinstance(value,sqlalchemy.orm.state.InstanceState) \
                and value is not None \
                and str(value).lower() != 'nan' \
                and not isinstance(value,datetime.datetime):

            document = document + " " + str(value)

    return document

def get_module_and_class_name(mod_class):
    """Get the module name and class name from the module.class_name string from the typespec.json

    :param mod_class: The module and class name string, ie imports.ImportSampleManifest
    :type mod_class: str
    :raises Exception: mod_class not in the correct format
    :return: module_name, class_name 
    :rtype: tuple
    """

    splitted = str(mod_class).split('.')

    if len(splitted) != 2:
        raise Exception("module_class format is not module.class %s" % str(mod_class))

    return splitted[0], splitted[1]

def serialise_unserialise(my_dict):
    """Serialise unserialise

    :param my_dict: Dictionary to serialise and unserialise
    :type my_dict: dict
    :return: my_dict
    :rtype: dict
    """    

    serialised = json.dumps(my_dict,default=str)
    return json.loads(serialised)

def get_date(date_string):
    """Get data from potential formats

    :param date: date string
    :type date: str
    :return: Date object
    :rtype: `datetime.datetime`
    """
    if not date_string:
        return None

    if isinstance(date_string,(pd.Timestamp,datetime.datetime)):
        return date_string

    if is_number(date_string):
        return datetime.datetime.fromtimestamp(int(date_string))

    formats = ['%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S']

    for format in formats:
        try:
            return datetime.datetime.strptime(date_string,format)
        except Exception:
            continue

    raise Exception('Date format unknown - ' +  str(date_string))

def breakdown_compound_class_id(colname):
    """Breakdown a compound_class id

    compound_class:1828::hmdb:direct_parent:Hypoxanthines:noUnit
    """

    splitted = colname.split('::')
    main_split = splitted[1].split(':')
    feature_id_split = splitted[0].split(':')
    compound_class_id = feature_id_split[1]

    class_type = main_split[0]
    class_level = main_split[1]

    if len(main_split) == 4:
        class_name = main_split[2]
        unit = main_split[3]
    else:
        raise Exception("Less than 4 parts to colname: " + colname)

    return compound_class_id, class_type, class_level, class_name, unit


def breakdown_annotation_id(colname,harmonise_annotations=False):
    """Breakdown an annotation id into its constituent parts
    ie
    feature::1::LPOS:PPR:CAR(8:10):noUnit

    :param colname: The column name to breakdown
    :type colname: str
    """

    version = None

    splitted = colname.split('::')
    main_split = splitted[1].split('#')
    feature_id_split = splitted[0].split(':')
    feature_metadata_id = None
    harmonised_annotation_id = None
    if len(feature_id_split) > 1:
        if feature_id_split[1] == 'fm':
            feature_metadata_id = feature_id_split[2]
        elif feature_id_split[1] == 'ha':
            harmonised_annotation_id = feature_id_split[2]
    if harmonise_annotations and not harmonised_annotation_id:
        raise UnharmonisedAnnotationException("Breakdown Annotation ID expecting a harmonised annotation ID %s " % colname)

    assay = main_split[0]
    annotation_method = main_split[1]

    if harmonise_annotations:
        if len(main_split) == 4:
            feature_name = main_split[2]
            unit = main_split[3]
        else:
            raise Exception("Less than 4 parts to colname: " + colname)

    else:
        if len(main_split) == 5:
            feature_name = main_split[2]
            version = main_split[3]
            unit = main_split[4]
        elif len(main_split) > 5:

            version = main_split[(len(main_split) - 2)]
            unit = max(main_split)
            feature_name = ''
            i = 2
            while i < len(main_split) - 1:
                if i == 2:
                    feature_name = main_split[i]
                else:
                    feature_name = feature_name + ":" + main_split[i]
                i = i + 1
        else:
            raise Exception("Less than 5 parts to colname: " + colname)

    return feature_metadata_id, harmonised_annotation_id, assay, annotation_method, feature_name, version, unit



def send_tls_email(user_email, subject, message_text):
    """Send TLS email. Email settings are configuration options.

    :param user_email: The email of the recipient
    :type user_email: str
    :param subject: The email subject
    :type subject: str
    :param message_text: The email body
    :type message_text: str
    """    

    email_on = config['SMTP']['enabled']
    logging.debug('Email is on %s', email_on)

    if email_on and user_email is not None:


        msg = MIMEText(message_text)
        msg['Subject'] = subject
        msg['From'] = config['SMTP']['from']
        msg['To'] = user_email

        smtp_server = smtplib.SMTP(config['SMTP']['host'], port=config['SMTP']['port'])

        smtp_server.starttls()

        smtp_server.set_debuglevel(1)
        logging.debug("About to send email to %s", user_email)
        smtp_server.login(config['SMTP']['user'], config['SMTP']['password'])
        smtp_server.send_message(msg)
        smtp_server.quit()

    else:
        logging.info("Email is disabled to user %s : %s", user_email, message_text)

def round_decimals_up(number:float, decimals:int=2):
    """Returns a value rounded up to a specific number of decimal places.

    :param number: the number to round
    :type number: float
    :param decimals: How many decimals to round to defaults to 2
    :type decimals: int, optional
    :return: The rounded value
    :rtype: float
    """  
    
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.ceil(number)

    factor = 10 ** decimals
    return math.ceil(number * factor) / factor

def round_decimals_down(number:float, decimals:int=2):
    """Returns a value rounded down to a specific number of decimal places.

    :param number: the number to round
    :type number: float
    :param decimals: How many decimals to round to defaults to 2
    :type decimals: int, optional
    :raises TypeError: [description]
    :raises ValueError: [description]
    :return: The rounded value
    :rtype: float
    """    
    
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor

def get_scaling_text(scaling):

    if scaling is None:
        return None
    elif isinstance(scaling,str) and scaling in ['uv','mc','pa','log']:
        return scaling
    elif scaling == 0:
        return 'mc'
    elif scaling == 1:
        return 'uv'
    elif scaling == 2:
        return 'pa'
    else:
        raise Exception("Unknown scaling type %s" % scaling)

def get_pyc_scaling(scaling):

    if scaling == 'mc':
        return 0
    elif scaling == 'uv':
        return 1
    elif scaling == 'pa':
        return 2
    else:
        raise Exception("Unknown scaling type %s" % scaling)

def convert_to_json_safe(data):

    if isinstance(data,pd.Series):
        data = data.where(pd.notnull(data), None)

    return json.loads(json.dumps(data, cls=CustomEncoder,default=str))

def read_numeric_batch(batch):

    if batch is None:
        return 0
    elif is_number(batch):
        return float(batch)
    else:
        raise Exception("Batch not numeric %s" % batch)

def clean_task_id(task_id):
    return task_id.lower().replace("-","_").replace(" ","_").replace(".","_").replace(")","_").replace("(","_")

def parse_intensity(intensity):
    # Try casting the value to a float, if it doesn't work, its <LLOQ or >ULOQ

    above_uloq = False
    below_lloq = False
    comment = None
    try:
        intensity = float(intensity)
        if math.isnan(intensity):
            below_lloq = True
            intensity = None
        elif math.isinf(intensity):
            above_uloq = True
            intensity = None
    except:
        intensity = None
        comment = str(intensity)
        if comment == '<LLOQ':
            below_lloq = True
        if comment == '>ULOQ':
            above_uloq = True

    return intensity,below_lloq,above_uloq,comment

def parse_ion_id(ion_id):
    return ion_id.strip().replace('.1', '').replace('.2', '').replace('.3', '').replace('.4', '')

def parse_cpd_name(cpd_name):
    return cpd_name.replace("_1","").replace("_2","").replace("_3","")

def build_combined_dataframe_from_seperate(intensity_data,sample_metadata,feature_metadata):

    if np.shape(intensity_data) != (sample_metadata.shape[0],feature_metadata.shape[0]):
        raise Exception("The intensity data shape does not match the sample_metadata and feature_metadata %s != [%s,%s]" % (np.shape(intensity_data),sample_metadata.shape[0],feature_metadata.shape[0]))

    # copy the entire sample_metadata dataframe
    df = sample_metadata.copy()

    # iterate over the feature rows, and then get the associated columns from the intensity_data and insert them with column header 'feature_id'
    feature_row_index = 0
    while feature_row_index < feature_metadata.shape[0]:
        feature_id = feature_metadata.loc[feature_row_index,'feature_id']
        df.loc[:,feature_id] = intensity_data[:, feature_row_index]
        feature_row_index = feature_row_index + 1

    return df

def replace_floating_point_imprecision(str_value):

    replace_strings = ['0000000000001',
                         '0000000000002',
                         '0000000000003',
                         '0000000000004',
                         '0000000000005',
                         '0000000000006',
                         '0000000000007',
                         '0000000000008',
                         '0000000000009',
                         '9999999999991',
                         '9999999999992',
                         '9999999999993',
                         '9999999999994',
                         '9999999999995',
                         '9999999999996',
                         '9999999999997',
                         '9999999999998',
                         '9999999999999',
                       '000000000001',
                         '000000000002',
                         '000000000003',
                         '000000000004',
                         '000000000005',
                         '000000000006',
                         '000000000007',
                         '000000000008',
                         '000000000009',
                         '999999999991',
                         '999999999992',
                         '999999999993',
                         '999999999994',
                         '999999999995',
                         '999999999996',
                         '999999999997',
                         '999999999998',
                         '999999999999']
    for string in replace_strings:
        str_value = str_value.replace(string,'')
    return str_value

def precision_round(number,digits=3,type='float'):
    if number is None:
        return None
    try:
        power = "{:e}".format(number).split('e')[1]
        value = round(number, -(int(power) - digits))
        if type == 'str':
            return replace_floating_point_imprecision(str(value))
            #regex = r'[1-9]+(0|9)(0|9)(0|9)(0|9)[1-9]'
            #value_string = str(value)
            #value_string_one = value_string.split('e')
            #value_string_two = value_string_one[0].split('.')
            #decimal_string = value_string_two[1]
            #search = re.search(regex, decimal_string)
            #match_pos = None
            #substring = None
            #if search:
            #    value_string = replace_floating_point_imprecision(value_string)
                #match_pos = search.end()
                #if match_pos is not None:
                #    substring = decimal_string[0:(match_pos - 5)]
                #    reconstructed_string = value_string_two[0] + "." + substring
                #    if len(value_string_one) > 1:
                #        reconstructed_string = reconstructed_string + "e" + value_string_one[1]
                #    value_string = reconstructed_string
            #return value_string
        else:
            return value

    except Exception as err:
        value = float(number)
        if math.isinf(value):
            value = 'inf'
        elif math.isnan(value):
            value = 'nan'
        return value

def clear_task_view_cache(task_run_id):
    return
    #session = requests.session()
    #session.get('curl -X PURGE -D – "%s/analysisview/analysisresult/%s"' % (config['WEBSERVER']['url'],task_run_id))

    #pc1 = subprocess.Popen('grep -lr cache-clear-target-task-view-%s %s' % (task_run_id,config['DATA']['nginx_cache']), stdout=subprocess.PIPE, shell=True)
    #out, err = pc1.communicate()
    #lines = out.decode('utf-8').split('\n')
    #for line in lines:
    #    if line != "":
    #        os.remove(line)

from sys import getsizeof, stderr
from itertools import chain
from collections import deque
try:
    from reprlib import repr
except ImportError:
    pass

def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)
