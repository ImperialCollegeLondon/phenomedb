import os, sys

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append(os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
import phenomedb.utilities as utils
import re
import pandas as pd
import numpy as np
from sqlalchemy import func
from phenomedb.cache import Cache
from phenomedb.exceptions import *
from pyChemometrics.ChemometricsScaler import ChemometricsScaler
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.collections import InstrumentedList
import nPYc
import shutil
from sqlalchemy.sql.expression import cast
import sqlalchemy.types


import gc

class QueryFactory:
    """Class for building, executing, and saving SQLAlchemy queries that define 'SavedQueries'.

        A QueryFactory is simply a collection of filters that match on table properties.

        Generates an SQLAlchemy query object that allows for further filters to be added as required, or .all() or
        .count() methods to be used.

        Query dict structure:

            query_dict = { 'model': str
                           'joins':[str,str],
                           'filters': [{ 'filter_operator': str,
                                         'matches': [{  'model': str,
                                                         'property': str,
                                                         "operator": str,
                                                         'value': str, float, list
                                                      }]
                                       }]
                         }

            query_dict['model']: The model object to return
            query_dict['joins']: The list of models to join
            query_dict['filters'] : The list of 'filters'.
            query_dict['filters']['filter_operator]: The type of filter - 'AND', 'OR'
            query_dict['filters']['matches']: A list of 'matches'
            query_dict['filters']['matches']['model']: The name of the model to match against.
            query_dict['filters']['matches']['property']: The name of the property to match against.
            query_dict['filters']['matches']['operator']: The operator to use - 'eq','not_eq','gt','lt','gte','lte','between','not_between','in','not_in','like','not_like','ilike','not_ilike'
            query_dict['filters']['matches']['value']: The value to match on. Must be of expected type - ie str, float, [0,1] (for between) or [0,N] (for in or in)

        Example usage:

            Creating and saving new query with the following structure:

                    query_dict = { 'model': 'Sample',
                                   'joins':['Subject','Project','MetadataValue','MetadataField','HarmonisedMetadataField'],
                                   'filters': [{
                                       'filter_operator': 'OR',
                                       'matches': [{
                                               'model': 'Project',
                                               'property':'name',
                                               'operator': 'eq',
                                               'value': 'PipelineTesting',
                                       }]
                                   },{
                                   'filter_operator': 'AND',
                                   'matches': [{
                                           'model': 'HarmonisedMetadataField',
                                           'property': 'name',
                                           "operator": 'eq',
                                           'value': 'Age',
                                        },
                                       {
                                           'model': 'MetadataValue',
                                           'property': 'harmonised_numeric_value',
                                           "operator": 'in',
                                           'value': ["30","35","40"]
                                       }]
                                    }]
                                 }

            query_factory = CohortQuery()

            filter = QueryFilter(filter_operator='AND')
            filter.add_match(model='Project',property='name',operator='eq',value='PipelineTesting')
            query_factory.add_filter(query_filter=filter)

            filter = QueryFilter(filter_operator='AND')
            filter.add_match(model='HarmonisedMetadataField',property='name',operator='eq',value='Age')
            filter.add_match(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=[30,40,50])
            query_factory.add_filter(query_filter=filter)

            query = query_factory.save()

            query_retrieved_from_db = db_session.query(CohortQuery).filter(CohortQuery.id==query.id).first()
            query_factory_retrieved = CohortQuery(query=query_retrieved_from_db)
            rows = query_factory_retrieved.get_query_rows()


        Example queries and query_dicts:

            All Samples from PipelineTesting project

                query = db_session.query(Sample).join(Subject,Project).filter(Project.name=='PipelineTesting')

                query_dict = {  'model': 'Sample',
                                'joins':['Subject','Project'],
                                'filters': [{
                                               'filter_operator': 'AND',
                                               'matches': [{
                                                            'model': 'Project',
                                                            'property': 'name',
                                                            "operator": 'eq',
                                                            'value': 'PipelineTesting',
                                                        }]
                                           }]
                              }

            All from every project NOT PipelineTesting

                query = db_session.query(Sample).join(Subject,Project).filter(Project.name != 'PipelineTesting')

                query_dict = {  'model': 'Sample',
                                'joins':['Subject','Project'],
                                'filters': [{
                                               'filter_operator': 'AND',
                                               'matches': [{
                                                            'model': 'Project',
                                                            'property': 'name',
                                                            "operator": 'not_eq',
                                                            'value': 'PipelineTesting',
                                                        }]
                                           }]
                              }


            All "Plasma" samples

                query = db_session.query(Sample).filter(Sample.sample_type=='Plasma')

                query_dict = { 'model': 'Sample',
                                'joins':[],
                               'filters': [{
                                               'filter_operator': 'AND',
                                               'matches': [{
                                                            'model': 'Sample',
                                                            'property': 'sample_type',
                                                            "operator": 'eq',
                                                            'value': 'Plasma',
                                                        }]
                                         }]
                             }


            All "HPOS" samples

                query = db_session.query(Sample).join(SampleAssay,Assay).filter(Assay.name=='HPOS')

                query_dict = {  'model': 'Sample',
                                'joins':['SampleAssay','Assay'],
                                'filters': [{
                                               'filter_operator': 'AND',
                                               'matches': [{
                                                            'model': 'Assay',
                                                            'property': 'name',
                                                            "operator": 'eq',
                                                            'value': 'HPOS',
                                                        }]
                                           }]
                              }

            All samples with subjects between ages 30 and 40

                query = db_session.query(Sample).join(MetadataValue,MetadataField,HarmonisedMetadataField)\
                    .filter(HarmonisedMetadataField.name=='Age')\
                    .filter(MetadataValue.harmonised_numeric_value.between(30,40))

                query_dict = {  'model': 'Sample',
                                'joins':['MetadataValue','MetadataField','HarmonisedMetadataField'],
                                'filters': [{
                                               'filter_operator': 'AND',
                                               'matches': [{
                                                            'model': 'HarmonisedMetadataField',
                                                            'property': 'name',
                                                            "operator": 'eq',
                                                            'value': 'Age',
                                                        }]
                                           },
                                           {
                                               'filter_operator': 'AND',
                                               'matches': [{
                                                            'model': 'MetadataValue',
                                                            'property': 'harmonised_numeric_value',
                                                            "operator": 'between',
                                                            'value': [30,40]
                                                        }]
                                           }]
                              }

            All samples with 'Glucose' annotations, with intensity > 0.3

                query = db_session.query(Sample)\
                    .join(SampleAssay,AnnotatedFeature,Annotation,AnnotationCompound,Compound)\
                    .filter(Compound.name=='Glucose')\
                    .filter(AnnotatedFeature.intensity > 0.3)

                query_dict = { 'model': 'Sample',
                               'joins':['SampleAssay','AnnotatedFeature','Annotation','AnnotationCompound','Compound'],
                               'filters': [{ 'filter_operator': 'AND',
                                            'matches': [{
                                                          'model': 'Compound',
                                                          'property': 'name',
                                                          "operator": 'eq',
                                                          'value': 'Glucose',
                                                      }]
                                           },
                                           { 'filter_operator': 'AND',
                                              'matches': [{
                                                            'model': 'AnnotatedFeature',
                                                            'property': 'intensity',
                                                           "operator": 'gt',
                                                           'value': 0.3
                                                          }]
                                           },
                                         ]}
                              }

            All samples with Pubchem CID 16217534 annotations, with intensity > 0.3

                query = db_session.query(Sample)\
                    .join(SampleAssay,AnnotatedFeature,Annotation,AnnotationCompound,Compound,CompoundExternalDB,ExternalDB)\
                    .filter(ExternalDB.name=='PubChem CID')\
                    .filter(CompoundExternalDB.database_ref=='16217534')\
                    .filter(AnnotatedFeature.intensity > 0.3)


                query_dict = { 'model': 'Sample',
                               'joins':['SampleAssay','AnnotatedFeature','Annotation','AnnotationCompound','Compound'
                                        'CompoundExternalDB','ExternalDB'],
                              'filters': [{ 'filter_operator': 'AND',
                                            'matches': [{
                                                          'model': 'ExternalDB',
                                                          'property': 'name',
                                                          "operator": 'eq',
                                                          'value': 'PubChem CID',
                                                      }]
                                           },
                                           { 'filter_operator': 'AND',
                                             'matches': [{
                                                            'model': 'CompoundExternalDB',
                                                            'property': 'database_ref',
                                                            "operator": 'eq',
                                                            'value': '16217534',
                                                          }]

                                           },
                                           { 'filter_operator': 'AND',
                                              'matches': [{
                                                           'model': 'AnnotatedFeature',
                                                            'property': 'intensity',
                                                            "operator": 'gt',
                                                            'value': 0.3,
                                                          }]

                                           },
                                         ]}
                              }


            All samples from PipelineTesting project OR nPYc-toolbox-tutorials

                query = db_session.query(Sample).join(Subject,Project).filter(Project.name=='PipelineTesting' | Project.name=='nPYc-toolbox-tutorials')

                query_dict = { 'model': 'Sample',
                               'joins':['Subject','Project'],
                               'filters': [{
                                               'filter_operator': 'OR',
                                               'matches': [{
                                                                'model': 'Project',
                                                                'property': 'name',
                                                                "operator": 'eq',
                                                                'value': 'PipelineTesting',
                                                             },
                                                             {
                                                                'model': 'Project',
                                                                'property': 'name',
                                                                "operator": 'eq',
                                                                'value': 'nPYc-toolbox-tutorials',
                                                             }]
                                            }]
                             }

            All from PipelineTesting project OR nPYc-toolbox-tutorials and with annotations with Pubchem CID ref IN ('16217534', '3082637')

                query = db_session.query(Sample).join(Subject,Project,SampleAssay,AnnotatedFeature,\
                    Annotation,AnnotationCompound,Compound,CompoundExternalDB,ExternalDB)\
                    .filter(Project.name=='PipelineTesting' | Project.name=='nPYc-toolbox-tutorials')\
                    .filter(ExternalDB.name=='PubChem CID' & CompoundExternalDB.database_ref.in_(['16217534','3082637'])

                query_dict = { 'model': 'Sample',
                               'joins':['Subject','Project','SampleAssay','Annotation','AnnotatedFeature',\
                                        'AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                               'filters': [{
                                               'filter_operator': 'OR',
                                               'matches': [{
                                                                'model': 'Project',
                                                                'property':'name',
                                                                "operator": 'eq',
                                                                'value': 'PipelineTesting',
                                                             },
                                                             {
                                                                'model': 'Project',
                                                                'property': 'name',
                                                                "operator": 'eq',
                                                                'value': 'nPYc-toolbox-tutorials'
                                                             }]
                                            },{
                                              'filter_operator': 'AND',
                                               'matches': [{
                                                                'model': 'ExternalDB'
                                                                'property': 'name',
                                                                "operator": 'eq',
                                                                'value': 'PubChem CID',
                                                             },
                                                             {
                                                                'model': 'CompoundExternalDB'
                                                                'property': 'database_ref',
                                                                "operator": 'in',
                                                                'value': ['16217534','3082637']
                                                             }]
                                            }]
                             }

            All annotations that a not PubChem CID ('16217534', '3082637')

                query = db_session.query(Sample).join(SampleAssay, Annotation,AnnotatedFeature,\
                    AnnotationCompound,Compound,CompoundExternalDB,ExternalDB)\
                    .filter(ExternalDB.name=='PubChem CID' & ~CompoundExternalDB.database_ref.in_(['16217534','3082637'])

                query_dict = {
                               'model': 'Sample',
                               'joins':['SampleAssay','Annotation','AnnotatedFeature',\
                                        'AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                               'filters': [{
                                               'matches': [{
                                                                'model': 'ExternalDB'
                                                                'property': 'name',
                                                                "operator": 'eq',
                                                                'value': 'PubChem CID',
                                                             },
                                                             {
                                                                'model': 'CompoundExternalDB'
                                                                'property': 'database_ref',
                                                                "operator": 'not_in',
                                                                'value': ['16217534','3082637']
                                                             }]
                                            }]
                             }
    :return: query_factory: The query factory object.
    :rtype: :class:`phenomedb.query_factory.base_query_factory`
    """

    foreign_keys = {
        'SampleAssay-Sample':['SampleAssay.sample_id','Sample.id'],
        'Sample-Subject':['Sample.subject_id', 'Subject.id'],
        'Subject-Project': ['Subject.project_id', 'Project.id'],
        'SampleAssay-AnnotatedFeature': ['AnnotatedFeature.sample_assay_id', 'SampleAssay.id'],
        'AnnotatedFeature-FeatureMetadata': ['AnnotatedFeature.feature_metadata_id', 'FeatureMetadata.id'],
        'FeatureMetadata-Annotation': ['FeatureMetadata.annotation_id', 'Annotation.id'],
        'Annotation-HarmonisedAnnotation': ['Annotation.harmonised_annotation_id', 'HarmonisedAnnotation.id'],
        'HarmonisedAnnotation-Assay': ['HarmonisedAnnotation.assay_id', 'Assay.id'],
        'HarmonisedAnnotation-AnnotationMethod': ['HarmonisedAnnotation.annotation_method_id', 'AnnotationMethod.id'],
        'HarmonisedAnnotation-AnnotationCompound': ['HarmonisedAnnotation.annotation_compound_id', 'AnnotationCompound.id'],
        'AnnotationCompound-Compound': ['AnnotationCompound.compound_id', 'Compound.id'],
     #   'Sample-SampleAssay': ['SampleAssay.sample_id', 'Sample.id'],
     #   'Subject-Sample': ['Sample.subject_id', 'Subject.id'],
     #   'Project-Subject': ['Subject.project_id', 'Project.id'],
     #   'SampleAssay-AnnotatedFeature': ['AnnotatedFeature.sample_assay_id', 'SampleAssay.id'],
     #   'AnnotatedFeature-FeatureMetadata': ['AnnotatedFeature.feature_metadata_id', 'FeatureMetadata.id'],
     #   'FeatureMetadata-Annotation': ['FeatureMetadata.annotation_id', 'Annotation.id'],
     #   'Annotation-HarmonisedAnnotation': ['Annotation.harmonised_annotation_id', 'HarmonisedAnnotation.id'],
     #   'HarmonisedAnnotation-Assay': ['HarmonisedAnnotation.assay_id', 'Assay.id'],
     #   'HarmonisedAnnotation-AnnotationMethod': ['HarmonisedAnnotation.annotation_method_id', 'Assay.id'],
     #   'HarmonisedAnnotation-AnnotationCompound': ['HarmonisedAnnotation.annotation_compound_id',
    #                                                'AnnotationCompound.id'],
    #    'AnnotationCompound-Compound': ['AnnotationCompound.compound_id', 'Compound.id']
    }

    join_routes = {'AnnotatedFeature':
        {
            "AnnotatedFeature": [],
            "SampleAssay": ["SampleAssay"],
            "Sample": ["SampleAssay", "Sample"],
            "Assay": ["SampleAssay", "Assay"],
            "Subject": ["SampleAssay", "Sample", "Subject"],
            "Project": ["SampleAssay", "Sample", "Subject", "Project"],
            "ProjectRole": ["SampleAssay", "Sample", "Subject", "Project", "ProjectRole"],
            "MetadataValue": ["SampleAssay", "Sample", "MetadataValue"],
            "MetadataField": ["SampleAssay", "Sample", "MetadataValue", "MetadataField"],
            "HarmonisedMetadataField": ["SampleAssay", "Sample", "MetadataValue", "MetadataField",
                                        "HarmonisedMetadataField"],
            "FeatureMetadata": ["FeatureMetadata"],
            "Annotation": ["FeatureMetadata", "Annotation"],
            "HarmonisedAnnotation" : ["FeatureMetadata","Annotation","HarmonisedAnnotation"],
            "AnnotationCompound": ["FeatureMetadata", "Annotation","HarmonisedAnnotation", "AnnotationCompound"],
            "AnnotationMethod": ["FeatureMetadata", "Annotation", "HarmonisedAnnotation", "AnnotationMethod"],
            "Compound": ["FeatureMetadata", "Annotation","HarmonisedAnnotation", "AnnotationCompound", "Compound"],
            "CompoundExternalDB": ["FeatureMetadata", "Annotation","HarmonisedAnnotation", "AnnotationCompound", "Compound",
                                   "CompoundExternalDB"],
            "ExternalDB": ["FeatureMetadata", "Annotation","HarmonisedAnnotation", "AnnotationCompound", "Compound",
                           "CompoundExternalDB", "ExternalDB"],
        },
        'SampleAssay':
            {
                "SampleAssay": [],
                "Sample": ["Sample"],
                "Assay": ["Assay"],
                "Subject": ["Sample", "Subject"],
                "Project": ["Sample", "Subject", "Project"],
                "ProjectRole": ["Sample", "Subject", "Project", "ProjectRole"],
                "MetadataValue": ["Sample", "MetadataValue"],
                "MetadataField": ["Sample", "MetadataValue", "MetadataField"],
                "HarmonisedMetadataField": ["Sample", "MetadataValue", "MetadataField", "HarmonisedMetadataField"],
                "AnnotatedFeature": ["AnnotatedFeature"],
                "FeatureMetadata": ["AnnotatedFeature", "FeatureMetadata"],
                "Annotation": ["AnnotatedFeature", "FeatureMetadata", "Annotation"],
                "HarmonisedAnnotation": ["FeatureMetadata", "Annotation", "HarmonisedAnnotation"],
                "AnnotationCompound": ["AnnotatedFeature", "FeatureMetadata", "Annotation", "HarmonisedAnnotation", "AnnotationCompound"],
                "AnnotationMethod": ["AnnotatedFeature", "FeatureMetadata", "Annotation", "HarmonisedAnnotation", "AnnotationMethod"],
                "Compound": ["AnnotatedFeature", "FeatureMetadata", "Annotation", "HarmonisedAnnotation", "AnnotationCompound", "Compound"],
                "CompoundExternalDB": ["AnnotatedFeature", "FeatureMetadata", "Annotation", "HarmonisedAnnotation", "AnnotationCompound",
                                       "Compound", "CompoundExternalDB"],
                "ExternalDB": ["AnnotatedFeature", "FeatureMetadata", "Annotation", "HarmonisedAnnotation", "AnnotationCompound", "Compound",
                               "CompoundExternalDB", "ExternalDB"]
            },
        'HarmonisedAnnotation':
            {
                "SampleAssay": ["Annotation","FeatureMetadata","AnnotatedFeature"],
                "Sample": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample"],
                "Assay": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample","Assay"],
                "Subject": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample", "Subject",],
                "Project": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample", "Subject", "Project"],
                "ProjectRole": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample", "Subject", "Project", "ProjectRole"],
                "MetadataValue": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample", "MetadataValue"],
                "MetadataField": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample", "MetadataValue", "MetadataField"],
                "HarmonisedMetadataField": ["Annotation","FeatureMetadata","AnnotatedFeature","SampleAssay","Sample", "MetadataValue", "MetadataField", "HarmonisedMetadataField"],
                "AnnotatedFeature": ["Annotation","FeatureMetadata","AnnotatedFeature"],
                "FeatureMetadata": ["Annotation", "FeatureMetadata"],
                "Annotation": ["Annotation"],
                "HarmonisedAnnotation": [],
                "AnnotationCompound": ["AnnotationCompound"],
                "AnnotationMethod": ["AnnotationMethod"],
                "Compound": ["AnnotationCompound", "Compound"],
                "CompoundExternalDB": ["AnnotationCompound",
                                       "Compound", "CompoundExternalDB"],
                "ExternalDB": ["ExternalDB"]
            }
    }

    # Some models, such as CompoundClass, actually use the AnnotatedFeature query results.
    parent_model = {'CompoundClass':"AnnotatedFeature",
                    'AnnotatedFeature':'AnnotatedFeature',
                    'SampleAssay':'SampleAssay',
                    'HarmonisedAnnotation':'HarmonisedAnnotation'}

    logger = utils.configure_logging(identifier="query_factory")

    comparison_operator_map = {'eq': '==',
                               'not_eq': '!=',
                               'gt': '>',
                               'lt': '<',
                               'gte': '>=',
                               'lte': '<='}

    function_operator_map = {'between': '.between(',
                             'not_between': '.between(',
                             'like': '.like(',
                             'not_like': '.like(',
                             'ilike': '.ilike(',
                             'not_ilike': '.ilike(',
                             'in': '.in_(',
                             'not_in': '.in_('}


    def __init__(self, saved_query=None, saved_query_id=None, filters=None, query_dict=None,
                 db_env=None,db_session=None,project_short_label=None,
                 query_name=None, query_description=None, username=None, role_id=None, output_model='SampleAssay'):

        self.dataframes = {}
        self.dataframe_csv_paths = {}
        self.query_dict = None
        self.saved_query = None
        self.compound_class_feature_map = {}

        self.query_name = query_name
        self.query_description = query_description
        self.project_short_label = project_short_label
        self.query = None
        self.__code_string = None
        self.query_results = None
        self.unique_match_models = []
        self.summary = {}
        self.username = username

        self.annotated_feature_id_matrix = None

        self.logger = utils.configure_logging('query_factory')

        self.role_id = role_id

        self.set_db_session(db_session=db_session, db_env=db_env)
        self.cache = Cache()

        if saved_query_id:
            self.saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id == saved_query_id).first()
            if not self.saved_query:
                raise Exception("SavedQuery with id=%s does not exist" % saved_query_id)
        elif saved_query:
            self.saved_query = saved_query
        else:
            self.saved_query = None

        if self.saved_query:
            self.query_dict = self.saved_query.json
            if query_name:
                self.query_name = query_name
                self.saved_query.name = query_name
            else:
                self.query_name = self.saved_query.name
            if query_description:
                self.query_description = query_description
                self.saved_query.description = query_description
            else:
                self.query_description = self.saved_query.description

        if query_dict:
            self.query_dict = query_dict
        elif not self.query_dict:
            self.query_dict = {"filters": []}

        if filters:
            self.query_dict['filters'] = filters
            # self.generate_query(output_model=output_model)

        self.logger.debug(self.query_dict)

        if saved_query or filters:
            self.generate_query(output_model=output_model)

    def get_code_string(self):

        return self.__code_string

    def set_db_session(self, db_session=None, db_env=None):
        """Set the db session

        :param db_session: The db_session to use, default None.
        :type db_session: :class:`sqlalchemy.orm.Session`
        :param db_env: The db to use, "PROD", "BETA", or "TEST, default None ("PROD")
        :type db_env: str
        """

        if db_env:
            self.db_env = db_env
        else:
            self.db_env = 'PROD'

        if db_session:
            self.db_session = db_session
        else:
            self.db_session = db.get_db_session(db_env=db_env)

    def get_dataframe_key(self, type, model, class_type=None, class_level=None, correction_type=None, aggregate_function=None,
                          annotation_version=None, db_env=None, scaling=None, harmonise_annotations=False, transform=None,
                          sample_orientation=None, sample_label=None,
                          feature_orientation=None, feature_label=None,
                          metadata_bin_definition=None,convert_units=True, master_unit='mmol/L'
                          ):

        if type not in ['combined','intensity_data','sample_metadata',
                        'feature_metadata','feature_id_matrix','feature_id_combined_dataframe',
                        'metaboanalyst_data','metaboanalyst_metadata']:
            raise Exception("Dataframe type not recognised %s" % type)

        if db_env and db_env == 'TEST':
            key = "TEST::"
        else:
            key = ""

        key = key + "%s::%s" % (type,model)

        if model == 'CompoundClass':
            if class_type:
                if isinstance(class_type, str):
                    key = key + ":%s" % class_type
                elif isinstance(class_type, CompoundClass.CompoundClassType):
                    key = key + ":%s" % class_type.value
                else:
                    raise Exception("Unknown class_type type %s %s" % (class_type,type(class_type)))

            if class_level:
                key = key + ":%s" % class_level.replace(" ","_").lower()

            if aggregate_function:
                key = key + ":%s" % aggregate_function

        if annotation_version:
            key = key + ":%s" % str(annotation_version).replace(" ", "_").replace(".","_").lower()

        if correction_type:
            if isinstance(correction_type,FeatureDataset.CorrectionType):
                key = key + ":%s" % correction_type.value
            elif isinstance(correction_type,str):
                key = key + ":%s" % correction_type

        #if type == 'intensity_data' and transform is not None:
        #    key = key + ":t:%s" % transform

        #if type == 'intensity_data' and scaling is not None:
        #    key = key + ":s:%s" % utils.get_scaling_text(scaling)

        if harmonise_annotations is True:
            key = key + ":HA"

        if type in ['metaboanalyst_data'] and feature_label is not None:
            key = key + ":%s" % feature_label

        if type in ['metaboanalyst_data','metaboanalyst_metadata'] and sample_label is not None:
            key = key + ":%s" % sample_label

       # if feature_orientation is not None:
       #     key = key + ":fo:%s" % feature_orientation

       # if sample_label is not None:
       #     key = key + ":sl:%s" % sample_label

       # if sample_orientation is not None:
       #     key = key + ":so:%s" % sample_orientation

       # if metadata_bin_definition is not None:
       #     key = key + ":mbin:%s" % json.dumps(metadata_bin_definition)

        if convert_units and master_unit:
            key = key + ":%s" % master_unit

        key = key.replace("/","_")

        self.logger.debug("QueryFactory.get_dataframe_key %s" % key)

        return key


    def calculate_joins(self, output_model='SampleAssay'):
        """
            Calculates the joins necessary to execute the query

            Uses prior information of the join routes from the main model to the match model

        :return:
        """

        # if not self.query_dict['model']:
        #    self.logger.error('query_dict model must be specified before attempting join map')
        #    raise Exception('query_dict model must be specified before attempting join map')

        self.query_dict['model'] = output_model

        if len(self.query_dict['filters']) == 0:
            self.logger.info('no filters have been added')

        print(self.query_dict)

        self.query_dict['joins'] = []

        self.get_unique_match_models()

        print(self.join_routes[output_model])

        for model in self.unique_match_models:
            for join_model in self.join_routes[output_model][model]:
                if join_model not in self.query_dict['joins']:
                    self.query_dict['joins'].append(join_model)

    def get_unique_match_models(self):
        """
            Get all unique models and map the joins between these models and the main model.
            Add the

        :return:
        """

        for filter in self.query_dict['filters']:
            for sub_filter in filter['sub_filters']:
                for match in sub_filter['matches']:
                    if match['model'] not in self.unique_match_models and match['model'] != self.query_dict['model']:
                        self.unique_match_models.append(match['model'])

    def add_filter(self, filter_operator='AND', match_dicts=[], filter_dict=None, query_filter=None, model=None,
                   property=None, operator=None, value=None):
        """Add a filter to the query_dict. Either generate a new one with this method or pass in a filter_dict or QueryFilter()

           Usage:
                query_factory = CohortQuery()
                filter = QueryFilter(filter_operator='AND')
                filter.add_match(QueryMatch(model='Project',property='name',operator='eq',value='PipelineTesting'))
                cohort_query.add_filter(query_filter=filter)
                cohort_query.calculate_joins()

           filter = {
                        'filter_operator': 'AND',
                        'matches': [{
                            'model': 'Project',
                            'property': 'name',
                            "operator": 'eq',
                            'value': 'PipelineTesting',
                        }]
                    }

        :param filter_operator: The top-level filter operator, "AND" or "OR", defaults to "AND".
        :type filter_operator: str, optional
        :param match_dicts: List of match dictionaries, defaults to [].
        :type match_dicts: list, optional
        :param filter_dict: The filter dictionary to use, defaults to None.
        :type filter_dict: dict, optional
        :param query_filter: The query filter object to use, defaults to None.
        :type query_filter: :class:`phenomedb.query_factory.QueryFilter`, optional
        :param model: The model to match on, defaults to None.
        :type model: str, optional
        :param property: The property to match on, defaults to None.
        :type property: str, optional
        :param operator: The operator to use, defaults to None.
        :type operator: str, optional
        :param value: The value to match on, defaults to None.
        :type value: str, int, float, or list, optional
        """

        if 'filters' not in self.query_dict:
            self.query_dict['filters'] = []

        if filter_dict:
            self.query_dict['filters'].append(filter_dict)

        elif query_filter:

            if isinstance(query_filter, QuerySubFilter) or isinstance(query_filter, MetadataFilter) or isinstance(
                    query_filter, ProjectRoleFilter):
                # We have to create the filter first!
                filter = QueryFilter()
                filter.add_sub_filter(query_filter)
            else:
                filter = query_filter

            self.query_dict['filters'].append(filter.get_filter_dict())

        elif model and property and operator and value:

            query_filter = QueryFilter(filter_operator=filter_operator, model=model, property=property,
                                       operator=operator, value=value)
            self.query_dict['filters'].append(query_filter.get_filter_dict())

        else:

            filter_dict = {"filter_operator": filter_operator,
                           "matches": match_dicts}

            self.query_dict['filters'].append(filter_dict)

    def build_query_string(self, output_model='SampleAssay',harmonise_annotations=True):
        """ Translates the query_dict into an SQLAlchemy query object string

        ie:

        query = db_session.query(SampleAssay).join(Sample,Subject,Project).filter(Project.name=='PipelineTesting')

        query_dict = {  'model': 'SampleAssay',
                        'joins':['Subject','Project'],
                        'filters': [{
                                    'filter_operator': 'AND'
                                    'sub_filters': [{
                                                    'sub_filter_operator': 'AND',
                                                    'matches': [{
                                                                'model': 'Project',
                                                                'property': 'name',
                                                                "operator": 'eq',
                                                            'value': 'PipelineTesting',
                                                    }]
                                    }]
                        }]
                      }

        """

        if self.query_dict:

            self.calculate_joins(output_model=self.parent_model[output_model])

            self.__code_string = 'db_session.query(' + self.query_dict['model'] + ')'

            if len(self.query_dict['joins']) > 0:
                i = 1
                while i < len(self.query_dict['joins']):
                    key = None
                    if self.parent_model[output_model] + "-" + self.query_dict['joins'][i-1] in self.foreign_keys.keys():
                        key = self.parent_model[output_model] + "-" + self.query_dict['joins'][i-1]
                    elif self.query_dict['joins'][i-1] + "-" + self.parent_model[output_model] in self.foreign_keys.keys():
                        key = self.query_dict['joins'][i-1] + "-" + self.parent_model[output_model]
                    elif self.query_dict['joins'][i-1] + "-" + self.query_dict['joins'][i-2] in self.foreign_keys.keys():
                        key = self.query_dict['joins'][i-1] + "-" + self.query_dict['joins'][i-2]
                    elif self.query_dict['joins'][i-2] + "-" + self.query_dict['joins'][i-1] in self.foreign_keys.keys():
                        key = self.query_dict['joins'][i-2] + "-" + self.query_dict['joins'][i-1]
                    else:
                        self.__code_string = "%s.join(%s)" % (self.__code_string,self.query_dict['joins'][i-1])

                    if key:
                        self.__code_string = "%s.join(%s,%s==%s)" % (self.__code_string,self.query_dict['joins'][i-1],self.foreign_keys[key][0],self.foreign_keys[key][1])
                    i = i + 1
            #        self.__code_string = self.__code_string + '.filter(HarmonisedAnnotation.annotation_method_id==AnnotationMethod.id)'
            #    elif not harmonise_annotations and 'Annotation' in self.query_dict['joins'] and 'AnnotationMethod' in \
            #            self.query_dict['joins']:
            #        self.__code_string = self.__code_string + '.filter(Annotation.annotation_method_id==AnnotationMethod.id)'
#
#                else:
#                    self.__code_string = self.__code_string + '.join(' + ','.join(self.query_dict['joins']) + ')'


            for filter in self.query_dict['filters']:
                self.build_filter_string(filter)

            self.__code_string = self.__code_string + ".group_by(" + self.query_dict['model'] + ".id)"
            self.__code_string = self.__code_string + ".order_by(" + self.query_dict['model'] + ".id)"
        else:
            self.logger.error('No query dictionary specification to execute')
            raise Exception('No query dictionary specification to execute')

    def build_filter_string(self, filter):
        """Builds the filter string based on a query_dict filter

        :param filter: The filter to build.
        :type filter: dict
        """

        self.__code_string = self.__code_string + '.filter('

        if len(filter['sub_filters']) > 1:
            self.build_logical_operator(filter['filter_operator'])

        i = 0
        for sub_filter in filter['sub_filters']:

            if i > 0 and i < len(filter['sub_filters']):
                self.__code_string = self.__code_string + ","

            self.build_sub_filter_string(sub_filter)

            i = i + 1

        if len(filter['sub_filters']) > 1:
            self.__code_string = self.__code_string + ')'

        self.__code_string = self.__code_string + ')'

    def build_sub_filter_string(self, sub_filter):
        """Builds the sub filter string based on the query_dict subfilter.

        :param sub_filter: The subfilter to build.
        :type sub_filter: dict
        """

        if len(sub_filter['matches']) > 1:
            self.build_logical_operator(sub_filter['sub_filter_operator'])

        i = 0
        for match in sub_filter['matches']:

            if i > 0 and i < len(sub_filter['matches']):
                self.__code_string = self.__code_string + ","

            self.build_match_string(match)

            i = i + 1

        if len(sub_filter['matches']) > 1:
            self.__code_string = self.__code_string + ')'

    def build_match_string(self, match):
        """Build the match string.

        :param match: The match dictionary.
        :type match: dict
        """

        if match['operator'] in self.comparison_operator_map.keys():
            self.build_comparison_operation(match)

        elif match['operator'] in self.function_operator_map.keys():
            self.build_function_operation(match)

    def build_logical_operator(self, operator):
        """Builds a logical operator.

        :param operator: The operator to use (AND or OR).
        :type operator: str
        :raises Exception: If the filter type is unknown.
        """

        if operator == 'AND':
            self.__code_string = self.__code_string + "and_("

        elif operator == 'OR':
            self.__code_string = self.__code_string + "or_("

        else:
            raise Exception("Unknown filter operator " + operator)

    def build_model_property_name(self, match):
        """Builds the model property name.

        :param match: The match dictionary.
        :type match: dict
        """

        self.__code_string = self.__code_string + match['model'] + '.' + match['property']

    def build_function_operation(self, match):
        """Builds a function operation.

        :param match: The match dictionary.
        :type match: dict
        """

        if re.match(r'^not_', match['operator']):
            self.__code_string = self.__code_string + 'not_('

        self.build_model_property_name(match)
        self.__code_string = self.__code_string + self.function_operator_map[match['operator']]
        self.build_match_value(match)
        self.__code_string = self.__code_string + ')'

        if re.match(r'^not_', match['operator']):
            self.__code_string = self.__code_string + ')'

    def build_comparison_operation(self, match):
        """Builds a comparison operation.

        :param match: The match dictionary.
        :type match: dict
        """

        self.build_model_property_name(match)
        self.__code_string = self.__code_string + self.comparison_operator_map[match['operator']]
        self.build_match_value(match)

    def build_match_value(self, match):
        """Builds the match value.

        :param match: The match dictionary.
        :type match: dict
        """

        if isinstance(match['value'], str):
            self.__code_string = self.__code_string + '"' + match['value'] + '"'

        elif isinstance(match['value'], list) and match['operator'] in ['in', 'not_in']:
            self.__code_string = self.__code_string + str(match['value']).replace("'", '"').replace(" ", "")

        elif isinstance(match['value'], list) and match['operator'] not in ['in', 'not_in']:
            p = 0
            for value in match['value']:
                if p > 0:
                    self.__code_string = self.__code_string + ","
                self.__code_string = self.__code_string + str(value)
                p = p + 1

        elif utils.is_number(match['value']):
            self.__code_string = self.__code_string + str(match['value'])

    def generate_query(self, output_model='SampleAssay',harmonise_annotations=True):
        """Generate the query. Builds the query code string and evaluates it.

        :raises Exception: If the query is invalid.
        """

        if self.role_id:
            self.add_filter(query_filter=ProjectRoleFilter(1))

        self.build_query_string(output_model=self.parent_model[output_model],harmonise_annotations=harmonise_annotations)

        try:
            self.query = eval('self.%s' % self.get_code_string())

        except:
            self.logger.exception("Query string unexecutable - %s " % self.get_code_string())
            raise Exception("Query string unexecutable - %s " % self.get_code_string())

    def execute_query(self, type="all", limit=None, offset=None):
        """Execute the query.

        :param type: What kind of query, 'all', 'first', or 'count', defaults to "all".
        :type type: str, optional
        :param limit: The query limit, defaults to None.
        :type limit: int, optional
        :param offset: The query offset, defaults to None.
        :type offset: int, optional
        :raises Exception: type not recognised.
        :raises Exception: no query object to execute.
        """

        if self.query:

            if limit:
                self.query = self.query.limit(int(limit))
            if offset:
                self.query = self.query.offset(int(offset))

            if type == 'all':
                self.query_results = self.query.all()
                self.logger.info('Number of results: %s' % len(self.query_results))

            elif type == 'first':
                self.query_results = self.query.first()
                self.logger.info('First result only: %s' % self.query_results)

            elif type == 'count':
                self.query_results = self.query.count()
                self.logger.info('Result count: %s' % self.query_results)

            else:
                self.logger.error("type " + str(type) + " not recognised")
                raise Exception("type " + str(type) + " not recognised")

            return self.query_results
        else:
            self.logger.error("No query object to execute")
            raise Exception("No query object to execute")

    def generate_and_execute_query(self, output_model='SampleAssay', type='all', limit=None, offset=None):
        """Generate and execute the query.

        :param type: What kind of query, 'all', 'first', or 'count', defaults to "all".
        :type type: str, optional
        :param limit: The query limit, defaults to None.
        :type limit: int, optional
        :param offset: The query offset, defaults to None.
        :type offset: int, optional
        :return: the query results.
        :rtype: int, :class:`phenomedb.models.*`, or list
        """

        # Hack because CompoundClass results are generated from AnnotatedFeature dataframes

        self.generate_query(output_model=self.parent_model[output_model])
        self.logger.info(self.get_code_string())
        self.logger.info(self.query.statement.compile(dialect=postgresql.dialect(),
                           compile_kwargs={
                               "literal_binds": True}))
        self.execute_query(type=type, limit=limit, offset=offset)
        return self.query_results

    def get_query_rows(self):
        """Get the query result rows.

        :return: The query results.
        :rtype: int, :class:`phenomedb.models.*`, or list
        """

        if not self.query_results:
            self.generate_and_execute_query(type='all')

        return self.query_results

    def save_query(self, type='custom'):
        """Save the query definition.

        :param type: The query definition type, defaults to 'custom'.
        :type type: str, optional
        :return: The SavedQuery. 
        :rtype: :class:`phenomedb.models.SavedQuery`
        """

        # self.build_query_string()
        self.generate_query()

        if not self.saved_query:
            if self.db_session.query(SavedQuery).filter(SavedQuery.name == self.query_name).count() > 0:
                raise Exception("SavedQuery.name == %s already exists!" % self.query_name)
            self.saved_query = SavedQuery(name=self.query_name,
                                          description=self.query_description,
                                          project_short_label=self.project_short_label,
                                          code_string=self.__code_string,
                                          sql=str(self.query.statement.compile(dialect=postgresql.dialect(),
                                                                               compile_kwargs={"literal_binds": True})),
                                          json=self.query_dict,
                                          type=type,
                                          created_by=self.username,
                                          role_id=self.role_id)
            self.db_session.add(self.saved_query)
            self.db_session.flush()

        else:

            self.saved_query.name = self.query_name
            self.saved_query.description = self.query_description
            self.project_short_label = self.project_short_label
            self.saved_query.code_string = self.__code_string
            self.saved_query.sql = str(
                self.query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
            self.saved_query.json = None
            self.saved_query.role_id = self.role_id
            self.db_session.flush()
            self.saved_query.json = dict(self.query_dict)
            self.db_session.flush()

        self.db_session.commit()
        self.logger.info("Query saved! %s" % self.saved_query)
        self.logger.info("Query definition! %s" % self.saved_query.json)

        # Reset the dataframe cache
        self.delete_cache()

        return self.saved_query

    def load_summary_statistics(self,reload_cache=False):

        # If it is saved, it can cache the dataframe in redis
        if self.saved_query:

            key = self.saved_query.get_cache_summary_stats_key()

            if self.cache.exists(key) and not reload_cache:
                self.summary = self.cache.get(key)
                self.logger.info("Got from redis %s" % key)
            else:
                # Expires after 24 hours
                self.calculate_summary_statistics()
                self.logger.debug("Query Summary %s %s" % (type(self.summary),self.summary))
                self.cache.set(key, utils.convert_to_json_safe(self.summary))
                self.logger.info("Set into redis %s" % key)
        else:
            self.calculate_summary_statistics()

        return self.summary

    def calculate_summary_statistics(self):
        """Calculate the summary statistics of the query.

        :return: summary: dictionary of summary statistics.
        :rtype: dict
        """

        if not self.query:
            self.generate_query(output_model='SampleAssay')

        print(self.query)

        summary = {}
        self.execute_query()
        sample_assay_ids = [sample_assay.id for sample_assay in self.query_results]

        self.logger.info("Number of sampling event assay ids: " + str(len(sample_assay_ids)))

        summary['number_of_sample_assays'] = len(sample_assay_ids)

        summary['number_samples'] = self.db_session.query(Sample).join(SampleAssay) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(Sample.id).count()

        summary['number_subjects'] = self.db_session.query(Subject).join(Sample, SampleAssay) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(Subject.id).count()

        summary['number_of_annotated_features'] = self.db_session.query(AnnotatedFeature).join(SampleAssay) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(AnnotatedFeature.id).count()

        if self.db_env == 'TEST':
            engine = db.test_engine
        elif self.db_env == 'BETA':
            engine = db.beta_engine
        else:
            engine = db.prod_engine

        import sqlalchemy

        sql = text("select min(sq.subject_annotation_count) from (" + \
                "select subject_id, count(annotation_id) as subject_annotation_count " + \
                "from feature_metadata fm inner join annotated_feature af on af.feature_metadata_id = fm.id " + \
                "inner join sample_assay sa on sa.id = af.sample_assay_id " + \
                "inner join sample s on s.id = sa.sample_id " + \
                "where sa.id = ANY(:saids) " + \
                "group by subject_id) sq;")# % (",".join([str(sample_id) for sample_id in sample_assay_ids]))

        summary['min_annotated_feature_count'] = engine.execute(sql,saids=sample_assay_ids).fetchall()[0][0]

      #  sql = "select min(sq.subject_annotation_count) from (" + \
      #        "select subject_id, count(annotation_id) as subject_annotation_count " + \
      #        "from feature_metadata fm inner join annotated_feature af on af.feature_metadata_id = fm.id " + \
      #        "inner join sample_assay sa on sa.id = af.sample_assay_id " + \
      #        "inner join sample s on s.id = sa.sample_id " + \
      #        "group by subject_id) sq;"#

        #summary['unique_annotated_features'] = engine.execute(sql).fetchall()[0][0]

        summary['project_counts'] = {x[0]: x[1] for x in
                                     self.db_session.query(Project.name, func.count(SampleAssay.id)).join(Subject,
                                                                                                          Sample,
                                                                                                          SampleAssay) \
                                         .filter(SampleAssay.id.in_(sample_assay_ids)) \
                                         .group_by(Project.name).order_by(Project.name).all()}

        summary['assay_counts'] = {x[0]: x[1] for x in
                                   self.db_session.query(Assay.name, func.count(SampleAssay.id)).join(SampleAssay) \
                                       .filter(SampleAssay.id.in_(sample_assay_ids)) \
                                       .group_by(Assay.name).all()}

      #  summary['annotation_method_counts'] = {'%s-%s' % (x[0],x[1]): x[2] for x in
      #                             self.db_session.query(Assay.name, AnnotationMethod.name, func.count(SampleAssay.id)).join(SampleAssay,AnnotatedFeature,Annotation,HarmonisedAnnotation,AnnotationMethod) \
      #                                 .filter(SampleAssay.id.in_(sample_assay_ids)) \
      #                                 .group_by(Assay.name,AnnotationMethod.name).all()}

        summary['sample_matrix_counts'] = {x[0]: x[1] for x in self.db_session.query(Sample.sample_matrix,
                                                                                     func.count(
                                                                                         SampleAssay.id)).join(
            SampleAssay) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(Sample.sample_matrix).all()}

        summary['sample_type_counts'] = {x[0].value: x[1] for x in
                                         self.db_session.query(Sample.sample_type, func.count(SampleAssay.id)).join(
                                             SampleAssay) \
                                             .filter(SampleAssay.id.in_(sample_assay_ids)) \
                                             .group_by(Sample.sample_type).all()}

        raw_counts = self.db_session.query(MetadataField.name,
                              MetadataValue.raw_value,
                              func.count(MetadataValue.raw_value)) \
            .join(MetadataValue, Sample, SampleAssay) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(MetadataField.name, MetadataValue.raw_value) \
            .order_by(MetadataField.name,MetadataValue.raw_value).all()

        summary['metadata_counts_raw'] = {}
        for result in raw_counts:
            if result[0] not in summary['metadata_counts_raw'].keys():
                summary['metadata_counts_raw'][result[0]] = {}
            if result[1] not in summary['metadata_counts_raw'][result[0]].keys():
                summary['metadata_counts_raw'][result[0]][result[1]] = {}
            summary['metadata_counts_raw'][result[0]][result[1]] = result[2]

        harmonised_text_counts = self.db_session.query(HarmonisedMetadataField.name,
                                           MetadataValue.harmonised_text_value,
                                           func.count(MetadataValue.harmonised_text_value)) \
            .select_from(HarmonisedMetadataField,MetadataField,MetadataValue,Sample,SampleAssay) \
            .join(MetadataField, MetadataField.harmonised_metadata_field_id == HarmonisedMetadataField.id) \
            .join(MetadataValue, MetadataValue.metadata_field_id == MetadataField.id) \
            .join(Sample, MetadataValue.sample_id == Sample.id) \
            .join(SampleAssay, SampleAssay.sample_id == Sample.id) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(HarmonisedMetadataField.name, MetadataValue.harmonised_text_value).all()
        summary['metadata_counts_harmonised_text'] = {}
        for result in harmonised_text_counts:
            if result[0] not in summary['metadata_counts_harmonised_text'].keys():
                summary['metadata_counts_harmonised_text'][result[0]] = {}
            if result[1] not in summary['metadata_counts_harmonised_text'][result[0]].keys():
                summary['metadata_counts_harmonised_text'][result[0]][result[1]] = {}
            summary['metadata_counts_harmonised_text'][result[0]][result[1]] = result[2]

        harmonised_numeric_counts = self.db_session.query(HarmonisedMetadataField.name,
                                                       MetadataValue.harmonised_numeric_value,
                                                       func.count(MetadataValue.harmonised_numeric_value)) \
            .select_from(HarmonisedMetadataField, MetadataField, MetadataValue, Sample, SampleAssay) \
            .join(MetadataField, MetadataField.harmonised_metadata_field_id == HarmonisedMetadataField.id) \
            .join(MetadataValue, MetadataValue.metadata_field_id == MetadataField.id) \
            .join(Sample, MetadataValue.sample_id == Sample.id) \
            .join(SampleAssay, SampleAssay.sample_id == Sample.id) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .group_by(HarmonisedMetadataField.name, MetadataValue.harmonised_numeric_value).all()
        summary['metadata_counts_harmonised_numeric'] = {}
        for result in harmonised_numeric_counts:
            if result[0] not in summary['metadata_counts_harmonised_numeric'].keys():
                summary['metadata_counts_harmonised_numeric'][result[0]] = {}
            if result[1] not in summary['metadata_counts_harmonised_numeric'][result[0]].keys():
                summary['metadata_counts_harmonised_numeric'][result[0]][result[1]] = {}
            summary['metadata_counts_harmonised_numeric'][result[0]][result[1]] = result[2]

        harmonised_datetime_counts = self.db_session.query(HarmonisedMetadataField.name,
                                                          MetadataValue.harmonised_datetime_value,
                                                          func.count(MetadataValue.harmonised_datetime_value)) \
            .select_from(HarmonisedMetadataField, MetadataField, MetadataValue, Sample, SampleAssay) \
            .join(MetadataField, MetadataField.harmonised_metadata_field_id == HarmonisedMetadataField.id) \
            .join(MetadataValue, MetadataValue.metadata_field_id == MetadataField.id) \
            .join(Sample, MetadataValue.sample_id == Sample.id) \
            .join(SampleAssay, SampleAssay.sample_id == Sample.id) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .filter(MetadataValue.harmonised_datetime_value!=None) \
            .group_by(HarmonisedMetadataField.name, MetadataValue.harmonised_datetime_value).all()
        
        summary['metadata_counts_harmonised_datetime'] = {}
        for result in harmonised_datetime_counts:
            if result[0] not in summary['metadata_counts_harmonised_datetime'].keys():
                summary['metadata_counts_harmonised_datetime'][result[0]] = {}
            if result[1] not in summary['metadata_counts_harmonised_datetime'][result[0]].keys():
                summary['metadata_counts_harmonised_datetime'][result[0]][result[1]] = {}
            summary['metadata_counts_harmonised_datetime'][result[0]][result[1]] = result[2]

        harmonised_text_counts_by_project = self.db_session.query(Project.name,
                                                       HarmonisedMetadataField.name,
                                                       MetadataValue.harmonised_text_value,
                                                       func.count(MetadataValue.harmonised_text_value)) \
            .select_from(HarmonisedMetadataField, MetadataField, MetadataValue, Sample, SampleAssay, Subject, Project) \
            .join(MetadataField, MetadataField.harmonised_metadata_field_id == HarmonisedMetadataField.id) \
            .join(MetadataValue, MetadataValue.metadata_field_id == MetadataField.id) \
            .join(Sample, MetadataValue.sample_id == Sample.id) \
            .join(SampleAssay, SampleAssay.sample_id == Sample.id) \
            .join(Subject, Subject.id == Sample.subject_id) \
            .join(Project, Project.id == Subject.project_id) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .filter(MetadataValue.harmonised_text_value != None) \
            .group_by(Project.name, HarmonisedMetadataField.name, MetadataValue.harmonised_text_value)\
            .order_by(Project.name,HarmonisedMetadataField.name).all()

        summary['metadata_counts_harmonised_text_by_project'] = {}
        for result in harmonised_text_counts_by_project:
            if result[1] not in summary['metadata_counts_harmonised_text_by_project'].keys():
                summary['metadata_counts_harmonised_text_by_project'][result[1]] = {}
            if result[0] not in summary['metadata_counts_harmonised_text_by_project'][result[1]].keys():
                summary['metadata_counts_harmonised_text_by_project'][result[1]][result[0]] = {}
            if result[2] not in summary['metadata_counts_harmonised_text_by_project'][result[1]][result[0]].keys():
               summary['metadata_counts_harmonised_text_by_project'][result[1]][result[0]][result[2]] = {}
            summary['metadata_counts_harmonised_text_by_project'][result[1]][result[0]][result[2]] = result[3]

        harmonised_numeric_counts_by_project = self.db_session.query(Project.name,
                                                       HarmonisedMetadataField.name,
                                                       MetadataValue.harmonised_numeric_value,
                                                       func.count(MetadataValue.harmonised_numeric_value)) \
            .select_from(HarmonisedMetadataField, MetadataField, MetadataValue, Sample, SampleAssay, Subject, Project) \
            .join(MetadataField, MetadataField.harmonised_metadata_field_id == HarmonisedMetadataField.id) \
            .join(MetadataValue, MetadataValue.metadata_field_id == MetadataField.id) \
            .join(Sample, MetadataValue.sample_id == Sample.id) \
            .join(SampleAssay, SampleAssay.sample_id == Sample.id) \
            .join(Subject, Subject.id == Sample.subject_id) \
            .join(Project, Project.id == Subject.project_id) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .filter(MetadataValue.harmonised_numeric_value != None) \
            .group_by(Project.name,HarmonisedMetadataField.name, MetadataValue.harmonised_numeric_value)\
            .order_by(Project.name,HarmonisedMetadataField.name).all()
        summary['metadata_counts_harmonised_numeric_by_project'] = {}
        for result in harmonised_numeric_counts_by_project:
            if result[1] not in summary['metadata_counts_harmonised_numeric_by_project'].keys():
                summary['metadata_counts_harmonised_numeric_by_project'][result[1]] = {}
            if result[0] not in summary['metadata_counts_harmonised_numeric_by_project'][result[1]].keys():
                summary['metadata_counts_harmonised_numeric_by_project'][result[1]][result[0]] = {}
            if result[2] not in summary['metadata_counts_harmonised_numeric_by_project'][result[1]][result[0]].keys():
                summary['metadata_counts_harmonised_numeric_by_project'][result[1]][result[0]][result[2]] = {}
            summary['metadata_counts_harmonised_numeric_by_project'][result[1]][result[0]][result[2]] = result[3]

        harmonised_datetime_counts_by_project = self.db_session.query(Project.name,
                                                                     HarmonisedMetadataField.name,
                                                                     MetadataValue.harmonised_numeric_value,
                                                                     func.count(MetadataValue.harmonised_numeric_value)) \
            .select_from(HarmonisedMetadataField, MetadataField, MetadataValue, Sample, SampleAssay, Subject, Project) \
            .join(MetadataField, MetadataField.harmonised_metadata_field_id == HarmonisedMetadataField.id) \
            .join(MetadataValue, MetadataValue.metadata_field_id == MetadataField.id) \
            .join(Sample, MetadataValue.sample_id == Sample.id) \
            .join(SampleAssay, SampleAssay.sample_id == Sample.id) \
            .join(Subject, Subject.id == Sample.subject_id) \
            .join(Project, Project.id == Subject.project_id) \
            .filter(SampleAssay.id.in_(sample_assay_ids)) \
            .filter(MetadataValue.harmonised_numeric_value != None) \
            .group_by(Project.name, HarmonisedMetadataField.name, MetadataValue.harmonised_numeric_value)\
            .order_by(Project.name,HarmonisedMetadataField.name).all()
        summary['metadata_counts_harmonised_datetime_by_project'] = {}
        for result in harmonised_datetime_counts_by_project:
            if result[1] not in summary['metadata_counts_harmonised_datetime_by_project'].keys():
                summary['metadata_counts_harmonised_datetime_by_project'][result[1]] = {}
            if result[0] not in summary['metadata_counts_harmonised_datetime_by_project'][result[1]].keys():
                summary['metadata_counts_harmonised_datetime_by_project'][result[1]][result[0]] = {}
            if result[2] not in summary['metadata_counts_harmonised_datetime_by_project'][result[1]][result[0]].keys():
                summary['metadata_counts_harmonised_datetime_by_project'][result[1]][result[0]][result[2]] = {}
            summary['metadata_counts_harmonised_datetime_by_project'][result[1]][result[0]][result[2]] = result[3]
        self.query_results = None
        self.summary = summary
        return summary

    def execute_and_build_annotated_feature_dataframe(self,convert_units=True,zero_lloq=True,inf_uloq=True,
                                                        master_unit='mmol/L',correction_type=None):

        self.generate_query(output_model='SampleAssay')
        sample_assays = self.execute_query()
        self.generate_query(output_model='HarmonisedAnnotation')
        harmonised_annotations = self.execute_query()
        harmonised_annotation_ids = []
        # harmonised_annotation_ids = [harmonised_annotation.id for harmonised_annotation in harmonised_annotations]
        sample_assay_ids = []
        sample_ids = []
        for sample_assay in sample_assays:
            sample_assay_ids.append(sample_assay.id)
            if sample_assay.sample.id not in sample_ids:
                sample_ids.append(sample_assay.sample.id)

        del sample_assays
        gc.collect()

        # dataframe = pd.DataFrame(columns=['Project', 'Acquired Time', 'Sample ID', 'Unique Name','Unique Batch',])
        query = self.db_session.query(SampleAssay.id.label('SampleAssay ID'),Sample.name.label('Sample ID'), Subject.name.label('Subject ID'),
                                 Sample.sample_matrix.label('Sample Matrix'), Project.name.label("Project"),
                                 Sample.assay_role.label('AssayRole'),Sample.sample_type.label('SampleType'),
                                 SampleAssay.sample_file_name.label('Sample File Name'),
                                 SampleAssay.batch.label('Batch'),
                                 SampleAssay.correction_batch.label('Correction Batch'),
                                 SampleAssay.run_order.label('Run Order'), SampleAssay.dilution.label('Dilution'),
                                 SampleAssay.acquired_time.label('Acquired Time'),
                                 SampleAssay.exclusion_details.label('Exclusion Details'),
                                 Assay.name.label('Assay')) \
            .filter(SampleAssay.sample_id == Sample.id) \
            .filter(Subject.id == Sample.subject_id) \
            .filter(Project.id == Subject.project_id) \
            .filter(Assay.id == SampleAssay.assay_id) \
            .filter(SampleAssay.id.in_(sample_assay_ids))

        combined_data = pd.read_sql(query.statement, query.session.bind)
        combined_data['Unique Name'] = combined_data['Project'] + '-' + combined_data['Sample ID']
        combined_data['Unique ID'] = combined_data['Project'] + '-' + combined_data['SampleAssay ID'].astype(str)
        combined_data['Unique Batch'] = combined_data['Project'] + '-' + combined_data['Assay'] + '-' + combined_data['Batch'].astype(str)
        combined_data['Unique Run Order'] = combined_data['Project'] + '-' + combined_data['Assay'] + '-' + combined_data['Run Order'].astype(str)
        combined_data['Batch'] = combined_data['Batch'].astype(float)
        combined_data['Correction Batch'] = combined_data['Correction Batch'].astype(float)
        combined_data['Run Order'] = combined_data['Run Order'].astype(float)
        combined_data['Dilution'] = combined_data['Dilution'].astype(float)
        combined_data['Acquired Time'] = combined_data['Acquired Time'].astype(str)
        combined_data['AssayRole'] = combined_data['AssayRole'].astype(str)
        combined_data['SampleType'] = combined_data['SampleType'].astype(str)
        combined_data['Unique Batch Numeric'] = None

        self.logger.info("combined data created with sample info")

        unique_project_names = combined_data['Project'].unique()
        #metadata_df = pd.DataFrame(columns=['Unique Name'])
        #metadata_df['Unique Name'] = combined_data['Unique Name']

        #annotated_feature_df = pd.DataFrame(columns=['Unique ID'])
        #annotated_feature_df['Unique ID'] = combined_data['Unique ID']

        #import tempfile
        #tmpdir = tempfile.TemporaryDirectory()

        #combined_data.to_csv("%s/main.csv" % tmpdir.name,index=False)
        #del combined_data
        #gc.collect()

        harmonised_fields = self.db_session.query(HarmonisedMetadataField)\
                                .join(MetadataField,Project)\
                                .filter(Project.name.in_(unique_project_names)).all()
        for harmonised_field in harmonised_fields:
            field_name = 'h_metadata::' + harmonised_field.name
            if harmonised_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
                query = self.db_session.query((Project.name + '-' + Sample.name).label('Unique Name'),
                                         MetadataValue.harmonised_text_value.label(field_name))
            elif harmonised_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
                query = self.db_session.query((Project.name + '-' + Sample.name).label('Unique Name'),
                                         MetadataValue.harmonised_numeric_value.label(field_name))
            elif harmonised_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:
                query = self.db_session.query((Project.name + '-' + Sample.name).label('Unique Name'),
                                         MetadataValue.harmonised_datetime_value.label(field_name))

            query = query.join(MetadataField, MetadataField.id == MetadataValue.metadata_field_id) \
                .filter(MetadataValue.sample_id == Sample.id) \
                .filter(Project.id == Subject.project_id) \
                .filter(Sample.subject_id == Subject.id) \
                .filter(Sample.id == MetadataValue.sample_id) \
                .filter(Sample.id.in_(sample_ids)) \
                .filter(MetadataField.harmonised_metadata_field_id == harmonised_field.id)

            metadata_column_table = pd.read_sql(query.statement, query.session.bind)
            #metadata_df = pd.merge(metadata_df,metadata_column_table,how='left',on=['Unique Name'])
            combined_data = pd.merge(combined_data, metadata_column_table, how='left', on=['Unique Name'])
            #self.logger.info('metadata_df shape: %s,%s' % metadata_df.shape)
            #combined_data = pd.merge(combined_data, metadata_column_table, how='left', on=['Unique Name'])

            self.logger.info("%s merged" % field_name)

        if len(unique_project_names) == 1:
            metadata_fields = self.db_session.query(MetadataField)\
                                    .join(Project)\
                                    .filter(Project.name.in_(unique_project_names)).all()
            for metadata_field in metadata_fields:
                field_name = 'metadata::' + metadata_field.name
                query = self.db_session.query((Project.name + '-' + Sample.name).label('Unique Name'), MetadataValue.raw_value.label(field_name)) \
                    .join(MetadataField, MetadataField.id == MetadataValue.metadata_field_id) \
                    .filter(Sample.id == MetadataValue.sample_id) \
                    .filter(MetadataField.project_id == Project.id)\
                    .filter(Sample.id.in_(sample_ids)) \
                    .filter(MetadataField.id == metadata_field.id)

                metadata_column_table = pd.read_sql(query.statement, query.session.bind)
                #metadata_df = pd.merge(metadata_df, metadata_column_table, how='left', on=['Unique Name'])
                combined_data = pd.merge(combined_data, metadata_column_table, how='left', on=['Unique Name'])

                self.logger.info("%s merged" % field_name)
                #self.logger.info('metadata_df shape: %s,%s' % metadata_df.shape)


        #metadata_df.to_csv("%s/metadata.csv" % tmpdir.name,index=False)
        #del metadata_df
        #gc.collect()

        units = {}
        i = 0
        for harmonised_annotation in harmonised_annotations:
            self.logger.info("Querying HA %s" % harmonised_annotation.id)

            query = self.db_session.query((Project.name + '-' + cast(SampleAssay.id, sqlalchemy.types.Unicode)).label('Unique ID'),
                                          AnnotatedFeature.intensity, AnnotatedFeature.sr_corrected_intensity,
                                     AnnotatedFeature.ltr_corrected_intensity, AnnotatedFeature.below_lloq,
                                     AnnotatedFeature.above_uloq,
                                     Unit.name.label('Unit Name')).join(Unit, FeatureMetadata,
                                                                                          Annotation) \
                .filter(Sample.id == SampleAssay.sample_id) \
                .filter(Subject.id == Sample.subject_id) \
                .filter(Project.id == Subject.project_id) \
                .filter(SampleAssay.id == AnnotatedFeature.sample_assay_id) \
                .filter(AnnotatedFeature.sample_assay_id.in_(sample_assay_ids)) \
                .filter(Annotation.harmonised_annotation_id == harmonised_annotation.id).limit(len(sample_assay_ids))

            intensity_row_table = pd.read_sql(query.statement, query.session.bind)

            #if intensity_row_table.shape[0] != combined_data.shape[0]:
            #    raise Exception("The intensity table for feature %s is not the same length as expected %s != %s, this is probably due to duplicated AnnotatedFeatures!" % (harmonised_annotation.id,intensity_row_table.shape[0],combined_data.shape[0]))

            if convert_units and master_unit and intensity_row_table.loc[0, 'Unit Name'] != 'noUnit':
                unit_name = master_unit
            else:
                unit_name = intensity_row_table.loc[0, 'Unit Name']
            if unit_name not in units.keys():
                units[unit_name] = self.db_session.query(Unit).filter(Unit.name==unit_name).first()
            column_name = 'feature:ha:%s::%s#%s#%s#%s' % (harmonised_annotation.id, harmonised_annotation.assay.name,
                                                          harmonised_annotation.annotation_method.name,
                                                          harmonised_annotation.cpd_name, unit_name)

            feature_df = pd.DataFrame(columns=['Unique ID', column_name])
            feature_df['Unique ID'] = intensity_row_table['Unique ID']

            if correction_type and harmonised_annotation.assay.quantification_type in [
                Assay.QuantificationType.relative, Assay.QuantificationType.relative.value]:
                if correction_type in [FeatureDataset.CorrectionType.LOESS_SR,
                                       FeatureDataset.CorrectionType.LOESS_SR.value]:

                    feature_df[column_name] = intensity_row_table['sr_corrected_intensity']
                elif correction_type in [FeatureDataset.CorrectionType.LOESS_LTR,
                                         FeatureDataset.CorrectionType.LOESS_LTR.value]:
                    feature_df[column_name] = intensity_row_table['ltr_corrected_intensity']
                else:
                    raise Exception("Unknown correction_type %s" % correction_type)
                # if SR is specified and it's not a relative abundance, just use the raw value
            else:
                feature_df[column_name] = intensity_row_table['intensity']
            if inf_uloq:
                feature_df[column_name] = np.where(intensity_row_table['above_uloq'] == True, float('inf'),
                                                   feature_df[column_name])
            if zero_lloq:
                feature_df[column_name] = np.where(intensity_row_table['below_lloq'] == True, 0,
                                                   feature_df[column_name])

            if convert_units and master_unit and master_unit != unit_name and unit_name != 'noUnit':
                try:
                    feature_df[column_name] = feature_df[column_name].apply(units[unit_name].convert,args=(master_unit, self.logger))
                except NoUnitConversionError:
                    self.logger.debug("Cannot convert noUnit to %s" % master_unit)
                    pass
                except NotImplementedUnitConversionError as err:
                    self.logger.exception(err)
                    raise NotImplementedUnitConversionError(err)
                except Exception as err:
                    self.logger.exception(err)
                    raise Exception(err)

            feature_df[column_name] = feature_df[column_name].astype(float)

            self.logger.info('feature series shape: %s,%s' % feature_df.shape)

            #combined_data = pd.merge(combined_data, feature_df, how='left', on=['Unique ID'],validate='1:1')
            #self.logger.info('annotated feature dataframe shape: %s,%s' % annotated_feature_df.shape)
            self.logger.info("%s merged" % column_name)

            i = i + 1

        unique_batches = combined_data.loc[:, 'Unique Batch'].unique().tolist()
        unique_batches_numeric = {}
        p = 0
        while p < len(unique_batches):
            unique_batches_numeric[unique_batches[p]] = p + 1
            p = p + 1
        for unique_batch, unique_batch_numeric in unique_batches_numeric.items():
            combined_data.loc[
                (combined_data['Unique Batch'] == unique_batch), 'Unique Batch Numeric'] = unique_batch_numeric

        return combined_data.where(pd.notnull(combined_data), None)

    def execute_and_build_dataframe(self, annotations_only=False, csv_path=None, sort_by=None,
                                    annotation_version='latest', output_model='SampleAssay',
                                    class_level=None, class_type=None,aggregate_function='mean',
                                    sort_by_ascending=(True, True), convert_units=True, master_unit='mmol/L',method=None,
                                    correction_type=None, zero_lloq=True, inf_uloq=True,harmonise_annotations=False):
        """
            Builds dataframe with following structure.

            project_name, sample_name, unique_name, metadata::age, h_metadata::age, cpd::HPOS-PPR::Glucose::mmol/L, m::HPOS::rt:37:mz:12.13::mmol/L
            npc-devset, sample_1, npc-devset-sample_1, 20,          20,             0.1

            metadata::age -> MetadataField called "age"
            h_metadata::Age -> HarmonisedMetadataField called "Age"
            cpd::HPOS-PPR:Glucose -> HPOS-PPR AnnotationCompound called "Glucose"

            Converts units by default to mmol/L

        :return:
        """

        if not sort_by:
            sort_by = ['Project', 'Acquired Time']

        # if annotation_version:
        #    if annotation_version == 'latest':
        #        self.add_filter(
        #            query_filter=QueryFilter(model='Annotation', property='is_latest', operator='eq', value=True))
        #    else:
        #        self.add_filter(query_filter=QueryFilter(model='Annotation', property='version', operator='eq',
        #
        #                                                 value=annotation_version))

        if output_model == 'AnnotatedFeature' and harmonise_annotations and method == 'columnwise':
            dataframe = self.execute_and_build_annotated_feature_dataframe(convert_units=convert_units,zero_lloq=zero_lloq,inf_uloq=inf_uloq,
                                                                   master_unit=master_unit,correction_type=correction_type)

        else:

            result_set = self.generate_and_execute_query(output_model=self.parent_model[output_model])

            dataframe = pd.DataFrame(columns=sort_by)

            parent_key = self.get_dataframe_key(type='combined',model=self.parent_model[output_model], db_env=self.db_env,
                                                        correction_type=correction_type,convert_units=convert_units,
                                                        annotation_version=annotation_version,master_unit=master_unit,
                                                        harmonise_annotations=harmonise_annotations)

            if output_model == 'AnnotatedFeature' or (self.parent_model[output_model] == 'AnnotatedFeature' and parent_key not in self.dataframes.keys()):

                dataframe = self.build_annotated_feature_dataframe(annotations_only=annotations_only,
                                                                   convert_units=convert_units,
                                                                   master_unit=master_unit,
                                                                   correction_type=correction_type,
                                                                   zero_lloq=zero_lloq, inf_uloq=inf_uloq,
                                                                   result_set=result_set,harmonise_annotations=harmonise_annotations)

                self.dataframes[parent_key] = dataframe
                feature_id_combined_dataframe_key = self.get_dataframe_key(type='feature_id_combined_dataframe',correction_type=correction_type,
                                                                           model='AnnotatedFeature', db_env=self.db_env,harmonise_annotations=harmonise_annotations)
                self.dataframes[feature_id_combined_dataframe_key] = self.dataframes[feature_id_combined_dataframe_key].sort_values(sort_by, ascending=sort_by_ascending, ignore_index=True)
                if self.saved_query:
                    self.cache.set(self.saved_query.get_cache_dataframe_key(feature_id_combined_dataframe_key),self.dataframes[feature_id_combined_dataframe_key])

            if output_model == 'CompoundClass':
                dataframe = self.build_compound_class_dataframe(aggregate_function=aggregate_function,class_level=class_level,class_type=class_type,
                                                                   convert_units=convert_units,zero_lloq=zero_lloq,inf_uloq=inf_uloq,annotation_version=annotation_version,
                                                                   master_unit=master_unit,parent_key=parent_key,harmonise_annotations=harmonise_annotations)


        dataframe = dataframe.sort_values(sort_by, ascending=sort_by_ascending, ignore_index=True)

        if csv_path:
            dataframe.to_csv(csv_path, index=False)
            self.dataframe_csv_paths[parent_key] = csv_path

        return dataframe

    def build_annotated_feature_dataframe(self, annotations_only=False, convert_units=True, master_unit='mmol/L',
                                          correction_type=None, harmonise_annotations=False, zero_lloq=True, inf_uloq=True, result_set=None):

        if not result_set:
            result_set = []

        # 2. create the start dataframe
        dataframe = pd.DataFrame(columns=['Project', 'Acquired Time', 'Sample ID', 'Unique Name','Unique Batch'])
        feature_id_combined_dataframe = dataframe.copy()

        feature_id_combined_dataframe_key = self.get_dataframe_key(type='feature_id_combined_dataframe',model='AnnotatedFeature',
                                                                   db_env=self.db_env,correction_type=correction_type, harmonise_annotations=harmonise_annotations)

        i = 0
        for annotated_feature in result_set:

            self.logger.debug("Processing %s/%s %s" % (i, len(result_set), annotated_feature))

            #if annotated_feature.feature_metadata.annotation.cpd_name == 'LDHD':
            #    bp = True

            if annotations_only and not annotated_feature.annotation:
                self.logger.debug("Skipping un-annotated annotated_feature: %s" % (annotated_feature))
                i = i + 1
                continue
            else:
                if correction_type and annotated_feature.sample_assay.assay.quantification_type in [
                    Assay.QuantificationType.relative, Assay.QuantificationType.relative.value]:
                    if correction_type in [FeatureDataset.CorrectionType.LOESS_SR,
                                           FeatureDataset.CorrectionType.LOESS_SR.value]:
                        intensity = annotated_feature.sr_corrected_intensity
                    elif correction_type in [FeatureDataset.CorrectionType.LOESS_LTR,
                                             FeatureDataset.CorrectionType.LOESS_LTR.value]:
                        intensity = annotated_feature.ltr_corrected_intensity
                    else:
                        raise Exception("Unknown correction_type %s" % correction_type)
                # if SR is specified and it's not a relative abundance, just use the raw value
                else:
                    intensity = annotated_feature.intensity

                if intensity is None:
                    self.logger.debug("Skipping intensities with NaN %s" % annotated_feature)
                    i = i + 1
                    continue

            # 3. Add the annotated_feature sample name, project name, and unique name row.

            unique_name = annotated_feature.sample_assay.sample.subject.project.name + "-" + \
                          annotated_feature.sample_assay.sample.name

            unique_batch = annotated_feature.sample_assay.sample.subject.project.name + "-" + \
                           annotated_feature.sample_assay.assay.name + "-" + \
                           str(annotated_feature.sample_assay.batch)

            unique_run_order = annotated_feature.sample_assay.sample.subject.project.name + "-" + \
                               annotated_feature.sample_assay.assay.name + "-" + \
                               str(annotated_feature.sample_assay.run_order)

            # 4. Get the row index for this entry, if not exists, add it
            try:
                self.row_index = np.where(dataframe.loc[:, 'Unique Name'] == unique_name)[0][0]
            except Exception:

                dataframe = dataframe.append({'Unique Name': unique_name,
                                              'Project': annotated_feature.sample_assay.sample.subject.project.name,
                                              'Sample ID': annotated_feature.sample_assay.sample.name,
                                              'Subject ID': annotated_feature.sample_assay.sample.subject.name,
                                              'Sample Matrix': annotated_feature.sample_assay.sample.sample_matrix,
                                              'SampleType': annotated_feature.sample_assay.sample.sample_type.value,
                                              'AssayRole': annotated_feature.sample_assay.sample.assay_role.value,
                                              'Sample File Name': annotated_feature.sample_assay.sample_file_name,
                                              'Batch': annotated_feature.sample_assay.batch,
                                              'Unique Batch': unique_batch,
                                              'Unique Batch Numeric': None,
                                              'Correction Batch': annotated_feature.sample_assay.correction_batch,
                                              'Run Order': annotated_feature.sample_assay.run_order,
                                              'Unique Run Order': unique_run_order,
                                              'Dilution': annotated_feature.sample_assay.dilution,
                                              'Acquired Time': annotated_feature.sample_assay.acquired_time,
                                              'Exclusion Details': annotated_feature.sample_assay.exclusion_details},
                                             ignore_index=True)

                self.row_index = np.where(dataframe.loc[:, 'Unique Name'] == unique_name)[0][0]

            # 5. Add the metadata fields
            for metadata_value in annotated_feature.sample_assay.sample.metadata_value:
                metadata_column_header = "metadata::" + metadata_value.metadata_field.name
                if metadata_column_header not in dataframe.columns:
                    dataframe[metadata_column_header] = 0
                dataframe.loc[self.row_index, metadata_column_header] = metadata_value.raw_value

                if metadata_value.metadata_field.harmonised_metadata_field:
                    harmonised_column_header = "h_metadata::" + metadata_value.metadata_field.harmonised_metadata_field.name
                    if harmonised_column_header not in dataframe.columns:
                        if metadata_value.metadata_field.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
                            dataframe[harmonised_column_header] = ''
                        elif metadata_value.metadata_field.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
                            dataframe[harmonised_column_header] = 0
                        elif metadata_value.metadata_field.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
                            dataframe[harmonised_column_header] = np.nan

                    if metadata_value.metadata_field.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
                        dataframe.loc[
                            self.row_index, harmonised_column_header] = metadata_value.harmonised_text_value
                    elif metadata_value.metadata_field.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
                        dataframe.loc[
                            self.row_index, harmonised_column_header] = metadata_value.harmonised_numeric_value
                    elif metadata_value.metadata_field.harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:
                        dataframe.loc[
                            self.row_index, harmonised_column_header] = metadata_value.harmonised_datetime_value

            if convert_units and master_unit and annotated_feature.unit.name != 'noUnit':
                unit_name = master_unit
            else:
                unit_name = annotated_feature.unit.name

            if harmonise_annotations and annotated_feature.feature_metadata.annotation.harmonised_annotation_id:
                # Uses the
                column_header = 'feature:ha:%s::%s#%s#%s#%s' % (annotated_feature.feature_metadata.annotation.harmonised_annotation.id,
                                                             annotated_feature.feature_metadata.annotation.harmonised_annotation.assay.name,
                                                             annotated_feature.feature_metadata.annotation.harmonised_annotation.annotation_method.name,
                                                             annotated_feature.feature_metadata.annotation.harmonised_annotation.cpd_name,
                                                             unit_name)

            elif annotated_feature.feature_metadata and annotated_feature.feature_metadata.annotation:

                # 6. Add the intensity value for the annotated metabolite
                column_header = 'feature:fm:%s::%s#%s#%s#%s#%s' % (annotated_feature.feature_metadata.id,
                                                                 annotated_feature.feature_metadata.annotation.assay.name,
                                                                 annotated_feature.feature_metadata.annotation.annotation_method.name,
                                                                 annotated_feature.feature_metadata.annotation.cpd_name,
                                                                 annotated_feature.feature_metadata.annotation.version,
                                                                 unit_name)

            elif annotated_feature.feature_metadata.mz and annotated_feature.feature_metadata.rt:
                column_header = \
                    'feature:fm:%s::%s:rt:%s:mz:%s:%s' % (
                annotated_feature.feature_metadata.id,
                annotated_feature.sample_assay.assay.name,
                annotated_feature.feature_metadata.rt,
                annotated_feature.feature_metadata.mz,
                unit_name)
            else:
                column_header = 'feature:fm:%s::%s#%s' % (
                annotated_feature.feature_metadata.id, annotated_feature.sample_assay.assay.name, unit_name)

            if column_header not in dataframe.columns:
                dataframe[column_header] = 0

            if column_header not in feature_id_combined_dataframe.columns:
                feature_id_combined_dataframe[column_header] = 0

            if intensity:

                if convert_units and master_unit:
                    try:
                        converted_intensity = annotated_feature.unit.convert(intensity, master_unit,self.logger)
                    except NoUnitConversionError:
                        #self.logger.debug("Cannot convert noUnit to %s" % master_unit)
                        converted_intensity = intensity
                    except NotImplementedUnitConversionError as err:
                        self.logger.exception(err)
                        raise NotImplementedUnitConversionError(err)
                    except Exception as err:
                        self.logger.exception(err)
                        raise Exception(err)

                    dataframe.loc[self.row_index, column_header] = converted_intensity
                else:
                    dataframe.loc[self.row_index, column_header] = intensity

            elif annotated_feature.below_lloq and zero_lloq:
                dataframe.loc[self.row_index, column_header] = 0
            elif annotated_feature.below_lloq and not zero_lloq:
                dataframe.loc[self.row_index, column_header] = "<LLOQ"
            elif annotated_feature.above_uloq and inf_uloq:
                dataframe.loc[self.row_index, column_header] = float('inf')
            elif annotated_feature.above_uloq and not inf_uloq:
                dataframe.loc[self.row_index, column_header] = ">ULOQ"

            feature_id_combined_dataframe.loc[self.row_index, column_header] = int(annotated_feature.id)

            i = i + 1

        self.logger.info("Dataframe built: Results: %s  Dataframe shape %s" % (len(result_set), dataframe.shape))

        for colname,colval in dataframe.iteritems():
            if not re.search("feature:",colname):
                feature_id_combined_dataframe.loc[:,colname] = dataframe.loc[:,colname]

        unique_batches = dataframe.loc[:,'Unique Batch'].unique().tolist()
        unique_batches_numeric = {}
        p = 0
        while p < len(unique_batches):
            unique_batches_numeric[unique_batches[p]] = p+1
            p = p + 1
        for unique_batch,unique_batch_numeric in unique_batches_numeric.items():
            dataframe.loc[(dataframe['Unique Batch'] == unique_batch), 'Unique Batch Numeric'] = unique_batch_numeric

        self.dataframes[feature_id_combined_dataframe_key] = feature_id_combined_dataframe
        #if self.saved_query:
        #    self.cache.set(self.saved_query.get_cache_dataframe_key(feature_id_combined_dataframe_key),feature_id_combined_dataframe)

        return dataframe

    def build_compound_class_dataframe(self,class_type=CompoundClass.CompoundClassType.classyfire,
                                       class_level='direct_parent',
                                       aggregate_function='mean',
                                       convert_units=True, master_unit='mmol/L',
                                       correction_type=None,zero_lloq=True,
                                       inf_uloq=True,parent_key=None,scaling=None,transform=None,
                                       annotation_version=None,harmonise_annotations=False,
                                       ):

        if not parent_key:
            parent_key = self.get_dataframe_key(type='combined',model=self.parent_model['CompoundClass'],
                                                                       db_env=self.db_env,
                                                                       correction_type=correction_type,
                                                                       annotation_version=annotation_version,
                                                                        harmonise_annotations=harmonise_annotations)

        if isinstance(class_type,str):
            if class_type == 'hmdb':
                class_type = CompoundClass.CompoundClassType.hmdb
            elif class_type == 'lipidmaps':
                class_type = CompoundClass.CompoundClassType.lipidmaps
            elif class_type == 'classyfire':
                class_type = CompoundClass.CompoundClassType.classyfire
            else:
                raise Exception("Unknown CompoundClass Type %s" % class_type)

        class_level = class_level.lower().replace(" ","_")
        allowed_class_levels = ['kingdom', 'category', 'main_class', 'sub_class', 'direct_parent']
        if class_level not in allowed_class_levels:
            raise Exception("Class level %s must be one of %s " % (class_level,allowed_class_levels))

        # Relies on the AnnotatedFeature dataframe to exist
        if parent_key not in self.dataframes.keys():
            self.dataframes[parent_key] = self.load_dataframe(output_model='AnnotatedFeature',
                                convert_units=convert_units, master_unit=master_unit,harmonise_annotations=harmonise_annotations,
                                correction_type=correction_type,zero_lloq=zero_lloq,inf_uloq=inf_uloq)

        if 'CompoundClass' not in self.dataframes.keys():
            self.dataframes['CompoundClass'] = {}

        key = self.get_dataframe_key(type='combined',model='CompoundClass',
                                                 aggregate_function=aggregate_function,
                                                 class_type=class_type,class_level=class_level,
                                                 correction_type=correction_type,harmonise_annotations=harmonise_annotations,
                                                 annotation_version=annotation_version,db_env=self.db_env)
        dataframe = pd.DataFrame()

        # Adds all the non-feature columns to the new dataframe
        for colname in self.dataframes[parent_key].columns:

            if re.search('feature:',colname):

                feature_metadata_id, harmonised_annotation_id, assay, annotation_method, cpd_name, version, unit = utils.breakdown_annotation_id(colname,harmonise_annotations=harmonise_annotations)
                if harmonised_annotation_id:
                    compound_class = self.db_session.query(CompoundClass).join(CompoundClassCompound, Compound,
                                                                               AnnotationCompound, HarmonisedAnnotation).filter(
                                                                                CompoundClass.type == class_type,
                                                                                getattr(CompoundClass, class_level) != None,
                                                                                HarmonisedAnnotation.id == int(harmonised_annotation_id)).first()
                elif feature_metadata_id:
                    compound_class = self.db_session.query(CompoundClass).join(CompoundClassCompound,Compound,AnnotationCompound,HarmonisedAnnotation,Annotation,FeatureMetadata).filter(
                                                                                CompoundClass.type == class_type,
                                                                                getattr(CompoundClass, class_level) != None,
                                                                                FeatureMetadata.id==int(feature_metadata_id)).first()
                if compound_class:
                    self.logger.info("Class found: %s %s" % (colname, compound_class))
                    class_column_name = "compound_class:%s::%s:%s:%s:noUnit" % (compound_class.id, compound_class.type.value, class_level, getattr(compound_class, class_level))
                    if class_column_name not in dataframe.columns:
                        dataframe[class_column_name] = 0
                    if class_column_name not in self.compound_class_feature_map.keys():
                        self.compound_class_feature_map[class_column_name] = []
                    self.compound_class_feature_map[class_column_name].append(colname)

            if not re.search('feature:', colname) and colname not in dataframe.columns:
                dataframe[colname] = self.dataframes[parent_key].loc[:,colname]

        # ADD TRANSFORM AND SCALING HERE!!!

        for class_column_name,feature_names in self.compound_class_feature_map.items():

            i = 0
            while i < dataframe.shape[0]:
                if aggregate_function == 'sum':
                    dataframe.loc[i,class_column_name] = self.dataframes[parent_key].loc[i,feature_names].sum()
                elif aggregate_function == 'min':
                    dataframe.loc[i,class_column_name] = self.dataframes[parent_key].loc[i,feature_names].min()
                elif aggregate_function == 'max':
                    dataframe.loc[i,class_column_name] = self.dataframes[parent_key].loc[i,feature_names].max()
                elif aggregate_function == 'median':
                    dataframe.loc[i,class_column_name] = self.dataframes[parent_key].loc[i,feature_names].median()
                elif aggregate_function == 'mean':
                    dataframe.loc[i,class_column_name] = self.dataframes[parent_key].loc[i,feature_names].mean()
                else:
                    raise Exception("Unknown aggregation function")
                i = i + 1

        self.dataframes[key] = dataframe

        return dataframe

    def build_intensity_data_sample_metadata_and_feature_metadata(self, output_dir=None,
                                                                  exclude_features_with_na_feature_values=False,
                                                                  columns_to_exclude=None,
                                                                  columns_to_include=None,
                                                                  harmonise_annotations=False,
                                                                  output_model='AnnotatedFeature',
                                                                  class_type=None,
                                                                  class_level=None,
                                                                  aggregate_function=None,
                                                                  correction_type=None,
                                                                  save_cache=True,
                                                                  compound_fields_to_include=None,
                                                                  compound_class_types_to_include=None,
                                                                  convert_units=True,
                                                                  master_unit='mmol/L'
                                                                  ):

        if compound_fields_to_include is None:
            compound_fields_to_include = ['Monoisotopic Mass',
                                          'Chemical Formula',
                                          'InChI', 'InChI Key',
                                          'refmet', 'ChEBI',
                                          'ChEMBL', 'CAS',
                                          'PubChem CID', 'KEGG',
                                          'HMDB', 'LipidMAPS']

        if compound_class_types_to_include is None:
            compound_class_types_to_include = ['hmdb',
                                               'classyfire',
                                               'lipidmaps',
                                               'refmet']

        if columns_to_include is None:
            columns_to_include = ['Project', 'Unique Batch','Sample ID','Sample File Name','AssayRole',
                                  'Unique Correction Batch','Unique Batch Numeric','Batch','Correction Batch'
                                  'Run Order', 'Acquired Time','Sample Matrix','SampleType','Unique Run Order','Dilution']

        if columns_to_exclude is None:
            columns_to_exclude = []

        if output_model == "CompoundClass" and (not class_type or not class_level):
            raise Exception("If outputting CompoundClass, class_type and class_level must be specified")

        combined_key, sample_metadata_key, feature_metadata_key, intensity_data_key = self.set_three_file_format_keys(
            output_model=output_model, class_type=class_type, class_level=class_level,
            aggregate_function=aggregate_function, correction_type=correction_type,
            harmonise_annotations=harmonise_annotations,
            convert_units=convert_units, master_unit=master_unit)

        self.compound_fields_to_include = compound_fields_to_include
        self.compound_class_types_to_include = compound_class_types_to_include
        self.logger.info("Compound Class types to include... %s" % self.compound_class_types_to_include)
        self.logger.info("Building X matrix, sample metadata, and feature metadata... ")

        if combined_key not in self.dataframes.keys() or self.dataframes[combined_key] is None:
            self.load_dataframe(type='combined',correction_type=correction_type,output_model=output_model,
                                class_level=class_level,class_type=class_type,harmonise_annotations=harmonise_annotations)
        if combined_key not in self.dataframes.keys() or self.dataframes[combined_key] is None:
            raise Exception("The main dataframe does not exist... %s" % (combined_key))

        combined_dataframe = self.dataframes[combined_key]

        shape = combined_dataframe.shape
        matrix_length = shape[0]

        matrix_width = 0
        for (colname, colval) in combined_dataframe.iteritems():
            if re.search('feature:', colname):
                matrix_width = matrix_width + 1
            elif re.search('compound_class:', colname):
                matrix_width = matrix_width + 1

        intensity_data = np.zeros(shape=(matrix_length, matrix_width))
        sample_metadata = pd.DataFrame()  # DO NOT SET THE OTHER COLUMNS HERE OTHERWISE THE COLUMNS WILL NOT BE POPULATED
        feature_metadata = pd.DataFrame()

        feature_id_matrix = None
        feature_id_matrix_key = None
        feature_id_combined_dataframe = None
        feature_id_combined_dataframe_key = None
        if output_model == 'AnnotatedFeature':
            feature_id_matrix = np.zeros(shape=(matrix_length, matrix_width))
            feature_id_combined_dataframe_key = self.get_dataframe_key(type='feature_id_combined_dataframe',model='AnnotatedFeature',
                                                                       db_env=self.db_env,correction_type=correction_type,
                                                                       harmonise_annotations=harmonise_annotations)
            feature_id_matrix_key = self.get_dataframe_key(type='feature_id_matrix',model='AnnotatedFeature', db_env=self.db_env,correction_type=correction_type,
                                                           harmonise_annotations=harmonise_annotations)

            if feature_id_combined_dataframe_key not in self.dataframes.keys():
                raise Exception("Expected feature_id_combined_dataframe does not exist... %s %s" % (feature_id_combined_dataframe_key,self.dataframes.keys()))
            else:
                feature_id_combined_dataframe = self.dataframes[feature_id_combined_dataframe_key]

        matrix_col_i = 0
        for (colname, colval) in combined_dataframe.iteritems():

            if re.search('feature:', colname):
                # Add the column to the X matrix
                try:
                    feature_metadata_row = self.build_annotated_feature_feature_metadata_row(colname,
                                                                  harmonise_annotations=harmonise_annotations)
                except UnharmonisedAnnotationException as err:
                    self.logger.exception(err)
                    continue

                intensity_data[:, matrix_col_i] = colval.values
                if output_model == 'AnnotatedFeature' and feature_id_combined_dataframe is not None:
                    feature_id_matrix[:, matrix_col_i] = feature_id_combined_dataframe.loc[:, colname]

                matrix_col_i = matrix_col_i + 1

                feature_metadata = feature_metadata.append(feature_metadata_row,ignore_index=True)

            elif re.search('compound_class:',colname):

                if exclude_features_with_na_feature_values and combined_dataframe[colname].isnull().values.any():
                    continue
                else:
                    intensity_data[:, matrix_col_i] = colval.values

                    matrix_col_i = matrix_col_i + 1

                    feature_metadata = feature_metadata.append(
                        self.build_compound_class_feature_metadata_row(colname),
                        ignore_index=True)

            else:
                if colname not in sample_metadata.columns:
                    sample_metadata.insert(len(sample_metadata.columns), colname, colval.values)

        #          if len(columns_to_exclude) > 0 and colname in columns_to_exclude:
        #              # ignore these are they are specifically being ignored
        #              pass
        #
        #          #elif exclude_one_factor_columns and self.is_unique(colval):
        #              # ignore these as they have only 1 factor
        #          #    pass
        #
        #          elif len(columns_to_include) > 0 and colname in columns_to_include:
        #              # include these (unique will be excluded later)
        #              sample_metadata.insert(len(sample_metadata.columns), colname, colval.values)
        #
        #          elif include_harmonised_metadata and re.search('h_metadata::', colname):
        #              sample_metadata.insert(len(sample_metadata.columns), colname, colval.values)
        #
        #          elif include_metadata and re.search('metadata::', colname):
        #              sample_metadata.insert(len(sample_metadata.columns), colname, colval.values)
        #
        #          elif len(columns_to_include) > 0 and colname not in columns_to_include:
        #              # ignore these (unique will be excluded later)
        #              pass
        #
        #          elif only_metadata and not re.search('metadata::', colname):
        #              # ignore these as we do not want any non-metadata columns
        #              pass
        #
        #          elif re.search('metadata::',colname) and only_harmonised_metadata and not re.search('h_metadata::', colname):
        #              # ignore these as we only want the harmonised metadata (but keep any fields that not metadata::, ie sample_name)
        #              pass
        #
        #          elif re.search('metadata::',colname) and exclude_na_metadata_columns and combined_dataframe[colname].isnull().values.any():
        #              # ignore these as they have null values!
        #              pass
        #
        #          else:
        #              sample_metadata.insert(len(sample_metadata.columns), colname, colval.values)

        # Method to remove any columns with null metadata columns

       # if exclude_samples_with_na_feature_values or exclude_na_metadata_samples:
       #     excluded_sample_metadata = sample_metadata
       #     excluded_intensity_data = intensity_data
       #     for index, row in sample_metadata.iterrows():
       #         if exclude_na_metadata_samples and row.isnull().values.any():
       #             excluded_sample_metadata = sample_metadata.drop(index=index)
       #             excluded_intensity_data = np.delete(intensity_data, index, 0)
       #         if exclude_samples_with_na_feature_values and np.isnan(intensity_data[index,:]).any():
       #             excluded_sample_metadata = sample_metadata.drop(index=index)
       #             excluded_intensity_data = np.delete(intensity_data, index, 0)
       #     intensity_data = excluded_intensity_data
       #     sample_metadata = excluded_sample_metadata

       # if exclude_features_with_na_feature_values:
       #     excluded_feature_metadata = feature_metadata
       #     excluded_intensity_data = intensity_data
       #     for index,row in feature_metadata.iterrows():
       #         if np.isnan(intensity_data[:,index]).any():
       #             excluded_feature_metadata = feature_metadata.drop(index=index)
       #             excluded_intensity_data = np.delete(intensity_data, index, 1)
       #     intensity_data = excluded_intensity_data
       #     feature_metadata = excluded_feature_metadata

        #metadata_config = {label:{'method':'bin','column':'h_metadata::Age','bins':[18,30,50,70,90]}}
   #     if metadata_bin_definition is not None and isinstance(metadata_bin_definition,dict):
   #         for label, definition in metadata_bin_definition.items():
   #             if definition['method'] == 'bin':
   #                 sample_metadata[label] = pd.cut(sample_metadata.loc[:, definition['column']], definition['bins'],include_lowest=True).astype('str')

        intensity_data = np.nan_to_num(intensity_data, copy=False)

        if 'Correction Batch' not in sample_metadata.columns and 'Batch' in sample_metadata.columns:
            sample_metadata['Correction Batch'] = sample_metadata['Batch']
        elif 'Correction Batch' not in sample_metadata.columns:
            sample_metadata['Correction Batch'] = 1


        #if for_npyc and 'Correction Batch' not in sample_metadata.columns:
            #sample_metadata['Run Order'] = range(1, 1+sample_metadata.shape[0])
            #sample_metadata.insert(len(sample_metadata.columns), 'Metadata Available', 'TRUE')
        #    sample_metadata['Correction Batch'] = 1
       # if transform:
       #     if transform == 'log':
       #         scaled_intensity_data = np.log(intensity_data + 1)
       #     elif transform == 'sqrt':
       #         scaled_intensity_data = np.sqrt(intensity_data)

       #     intensity_data = scaled_intensity_data


        #if scaling:
        #    if scaling not in ['uv', 'mc', 'pa',0,1,2]:
        #        raise Exception("Scaling type not implemented/recognised: %s" % scaling)
        #    if scaling in ['uv','mc','pa']:
        #        scaling = utils.get_pyc_scaling(scaling)
        #    scaler = ChemometricsScaler(scaling)
        #    scaler.fit(intensity_data)
        #    scaled_intensity_data = scaler.transform(intensity_data, copy=True)
        #    self.logger.info('Intensity data scaled using %s' % scaling)

        #    intensity_data = scaled_intensity_data

        if output_model == 'AnnotatedFeature':
            feature_id_matrix_key = self.get_dataframe_key(type='feature_id_matrix', model=output_model,
                                                        correction_type=correction_type,harmonise_annotations=harmonise_annotations,
                                                        db_env=self.db_env,class_type=class_type,class_level=class_level,aggregate_function=aggregate_function)
            self.dataframes[feature_id_matrix_key] = feature_id_matrix.astype(int)
            if save_cache:
                self.cache.set(self.saved_query.get_cache_dataframe_key(feature_id_matrix_key), feature_id_matrix)

        if output_dir:

            self.output_files('intensity_data',intensity_data_key,None,output_dir)
            self.output_files('sample_metadata',sample_metadata_key,None,output_dir)
            self.output_files('feature_metadata', feature_metadata_key,None,output_dir)

            if feature_id_matrix is not None and output_model == "AnnotatedFeature" and self.saved_query:
                feature_id_matrix_csv_path = output_dir + "/%s_feature_id_matrix.csv" % (
                    self.saved_query.name.replace(" ", "_"))
                pd.DataFrame(self.dataframes[feature_id_matrix_key]).to_csv(feature_id_matrix_csv_path, header=None,
                                                                   index=None)
                self.dataframe_csv_paths[feature_id_matrix_key] = feature_id_matrix_csv_path

        return sample_metadata,feature_metadata,intensity_data

    def delete_cache(self):

        summary_key = self.saved_query.get_cache_summary_stats_key()
        if self.cache.exists(summary_key):
            self.cache.delete(summary_key)
        cache_state = dict(self.saved_query.cache_state)
        if summary_key in cache_state.keys():
            del cache_state[summary_key]

        for key, state in self.saved_query.cache_state.items():

            annotated_feature_id_key = self.saved_query.get_cache_annotated_feature_id_key(key)
            cache_key = self.saved_query.get_cache_dataframe_key(key)

            if self.cache.exists(annotated_feature_id_key):
                self.cache.delete(annotated_feature_id_key)
            if self.cache.exists(cache_key):
                self.cache.delete(cache_key)

            if key in cache_state.keys():
                del cache_state[key]
            if annotated_feature_id_key in cache_state.keys():
                del cache_state[annotated_feature_id_key]

        self.saved_query.cache_state = cache_state
        self.db_session.commit()

    def is_unique(self, colvalue):

        return (colvalue[0] == colvalue).all(0)

    def build_compound_class_feature_metadata_row(self,colname):

        compound_class_id, class_type, class_level, class_name, unit = utils.breakdown_compound_class_id(colname)

        row = {'feature_name': class_name,
               'Feature Name': class_name,
               'Compound Column ID': colname,
               'Compound Class ID': compound_class_id,
               'Compound Class Type': class_type,
               'Compound Class Level': class_level,
               'Compound Class Name': class_name,
               'Unit': unit}

        if self.compound_class_feature_map and colname in self.compound_class_feature_map:
            row['features'] = ",".join(self.compound_class_feature_map[colname])

        compound_class = self.db_session.query(CompoundClass).filter(CompoundClass.id == int(compound_class_id)).first()

        if not compound_class:
            raise Exception("Unknown CompoundClass with id %s" % compound_class_id)

        compound_class_fields = [a for a in dir(compound_class) if
                                   not a.startswith('_') and not callable(getattr(compound_class, a)) \
                                   and not isinstance(a, InstrumentedList) \
                                   and a not in ['compounds','metadata','type']]

        for attr in compound_class_fields:
            if getattr(compound_class,attr) is not None and not isinstance(getattr(compound_class,attr), InstrumentedList):
                row[attr] = getattr(compound_class,attr)

        return row

    def build_feature_name_from_compound_id(self,row, compound_db_name,harmonised_annotation_id):
        # 1. find all the columns that match ChEBI.
        # 2. For each, merge them together using the operator
        harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
            HarmonisedAnnotation.id == harmonised_annotation_id).all()
        if harmonised_annotation.multi_compound_operator is not None:
            matches = []
            for key in row.keys():
                if re.search('ChEBI', key):
                    matches.append(key)
            feature_name = row[matches[0]]
            i = 1
            while i < len(matches):
                feature_name = "%s %s %s " % (feature_name, harmonised_annotation.multi_compound_operator.value, row[matches[i]])
                i = i + 1
        else:
            feature_name = row['c1'+compound_db_name]

        return feature_name

    def build_annotated_feature_feature_metadata_row(self, colname,harmonise_annotations=False):
        try:
            feature_metadata_id, harmonised_annotation_id, assay, annotation_method, cpd_name, version, unit = utils.breakdown_annotation_id(colname,harmonise_annotations=harmonise_annotations)

            self.logger.debug("Annotation Breakdown: %s fm:%s ha:%s %s %s %s %s %s" % (colname,feature_metadata_id,harmonised_annotation_id,assay,annotation_method,cpd_name,version,unit))
        except UnharmonisedAnnotationException as err:
            raise UnharmonisedAnnotationException(err)

        if harmonise_annotations and harmonised_annotation_id:
            row = self.build_harmonised_annotation_row(harmonised_annotation_id,assay, annotation_method, unit)
        else:
            row = self.build_feature_metadata_row(feature_metadata_id,assay, annotation_method, version, unit)

        row['feature_id'] = colname
        row["Feature Name"] = row['feature_name']

        return row

    def build_harmonised_annotation_row(self,harmonised_annotation_id,assay, annotation_method, unit):

        harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
            HarmonisedAnnotation.id == harmonised_annotation_id).first()

        # Add the other FeatureMetadata fields here
        row = {'assay': assay,
               'annotation_method': annotation_method,
                'feature_name': harmonised_annotation.cpd_name,
               'cpd_id': harmonised_annotation.cpd_id,
               'unit': unit,
                'harmonised_annotation_id': harmonised_annotation.id,
                'annotated_by': harmonised_annotation.annotated_by,
                'confidence_score': harmonised_annotation.confidence_score,
                'annotation_multi_compound_operator': harmonised_annotation.multi_compound_operator}

        if harmonised_annotation.assay.quantification_type in [Assay.QuantificationType.relative,
                                                Assay.QuantificationType.relative.value]:
            row['QuantificationType'] = 'relative'
        elif harmonised_annotation.assay.quantification_type in [Assay.QuantificationType.absolute,
                                                  Assay.QuantificationType.absolute.value]:
            row['QuantificationType'] = 'absolute'
        else:
            row['QuantificationType'] = 'unknown'

        if harmonised_annotation.compounds \
                and len(harmonised_annotation.compounds) > 0:
            row = self.build_single_or_multi(row, harmonised_annotation)

        return row

    def build_feature_metadata_row(self,feature_metadata_id,assay, annotation_method, version, unit):

        feature_metadata = self.db_session.query(FeatureMetadata).filter(
            FeatureMetadata.id == feature_metadata_id).first()

        # Add the other FeatureMetadata fields here
        row = {'feature_metadata_id': feature_metadata_id,
               'feature_name': feature_metadata.feature_name,
               'Feature Name': feature_metadata.feature_name,
               'assay': assay,
               'annotation_method': annotation_method,
               'unit': unit}

        if feature_metadata.rt_average is not None and feature_metadata.mz_average is not None:
            row['rt'] = feature_metadata.rt_average
            row['mz'] = feature_metadata.mz_average

        if feature_metadata.feature_dataset.assay.quantification_type in [Assay.QuantificationType.relative,
                                                Assay.QuantificationType.relative.value]:
            row['quantification_type'] = 'relative'
        elif feature_metadata.feature_dataset.assay.quantification_type in [Assay.QuantificationType.absolute,
                                                  Assay.QuantificationType.absolute.value]:
            row['quantification_type'] = 'absolute'
        else:
            row['quantification_type'] = 'unknown'

        if isinstance(feature_metadata.calibration_method,CalibrationMethod):
            row['calibration_method'] = feature_metadata.calibration_method.value

        if feature_metadata.annotation:
            row['cpd_name'] = feature_metadata.annotation.cpd_name
            row['cpd_id'] = feature_metadata.annotation.cpd_id
            row['harmonised_cpd_name'] = feature_metadata.annotation.harmonised_annotation.cpd_name
            row['annotation_id'] = feature_metadata.annotation.id
            row['annotation_version'] = version
            row['annotated_by'] = feature_metadata.annotation.annotated_by
            row['confidence_score'] = feature_metadata.annotation.confidence_score
            row['annotation_multi_compound_operator'] = feature_metadata.annotation.multi_compound_operator

        feature_metadata_fields = [a for a in dir(feature_metadata) if
                                   not a.startswith('_') and not callable(getattr(feature_metadata, a)) \
                                   and not isinstance(a, InstrumentedList) \
                                   and a not in ['annotation',
                                                 'annotation_parameters',
                                                 'feature_dataset',
                                                 'feature_metadata',
                                                 'feature_metadatas',
                                                 'quantification_type',
                                                 'calibration_method']]
        for attr, value in feature_metadata.__dict__.items():
            if attr in feature_metadata_fields and value is not None and isinstance(value, Enum):
                row[attr] = value.value
            elif attr in feature_metadata_fields and value is not None and not isinstance(value, InstrumentedList):
                row[attr] = value
        if feature_metadata.annotation and feature_metadata.annotation.harmonised_annotation and feature_metadata.annotation.harmonised_annotation.compounds \
                and len(feature_metadata.annotation.harmonised_annotation.compounds) > 0:
            row = self.build_single_or_multi(row, feature_metadata.annotation.harmonised_annotation)
        return row

    def build_single_or_multi(self, row, harmonised_annotation):

        if len(harmonised_annotation.compounds) == 1:
            col_prefix = ''
        else:
            col_prefix = None

        i = 1

        for annotation_compound in harmonised_annotation.compounds:
            if not col_prefix:
                col_prefix = 'c' + str(i) + '#'

            added_fields = []
            row[col_prefix + 'PhenomeDB ID'] = annotation_compound.compound.id
            if 'Compound Name' in self.compound_fields_to_include:
                row[col_prefix + 'Compound Name'] = annotation_compound.compound.name
                added_fields.append('Compound Name')
            if 'Chemical Formula' in self.compound_fields_to_include:
                row[col_prefix + 'Chemical Formula'] = annotation_compound.compound.chemical_formula
                added_fields.append('Chemical Formula')
            if 'Monoisotopic Mass' in self.compound_fields_to_include:
                row[col_prefix + 'Monoisotopic Mass'] = annotation_compound.compound.monoisotopic_mass
                added_fields.append('Monoisotopic Mass')
            if 'InChI' in self.compound_fields_to_include:
                row[col_prefix + 'InChI'] = annotation_compound.compound.inchi
                added_fields.append('InChI')
            if 'InChI Key' in self.compound_fields_to_include:
                row[col_prefix + 'InChI Key'] = annotation_compound.compound.inchi_key
                added_fields.append('InChI Key')
            if 'SMILES' in self.compound_fields_to_include:
                row[col_prefix + 'SMILES'] = annotation_compound.compound.smiles
                added_fields.append('SMILES')
            if 'IUPAC' in self.compound_fields_to_include:
                row[col_prefix + 'IUPAC'] = annotation_compound.compound.iupac
                added_fields.append('IUPAC')
            for field in self.compound_fields_to_include:
                if field not in added_fields:
                    row[col_prefix + field] = self.get_compound_db_ref(annotation_compound.compound, field)
            for class_type in self.compound_class_types_to_include:
                row = self.get_compound_class_refs(col_prefix, row, annotation_compound.compound, class_type)

        return row

    def get_compound_db_ref(self, compound, field):

        db_ref = self.db_session.query(CompoundExternalDB).join(ExternalDB).filter(ExternalDB.name == field,
                                                                                 CompoundExternalDB.compound_id == compound.id).first()

        if db_ref:
            return db_ref.database_ref
        else:
            return None

    def get_compound_class_refs(self, col_prefix, row, compound, class_type):

        compound_class = self.db_session.query(CompoundClass).join(CompoundClassCompound).filter(
            CompoundClassCompound.compound_id == compound.id,
            CompoundClass.type == class_type).first()

        if compound_class:
            class_type_stripped = class_type.replace("_class", "")
            if compound_class.kingdom:
                row[col_prefix + class_type_stripped + " Kingdom"] = compound_class.kingdom
            if compound_class.category:
                row[col_prefix + class_type_stripped + " Category"] = compound_class.category
            if compound_class.main_class:
                row[col_prefix + class_type_stripped + " Main Class"] = compound_class.main_class
            if compound_class.sub_class:
                row[col_prefix + class_type_stripped + " Sub Class"] = compound_class.sub_class
            if compound_class.direct_parent:
                row[col_prefix + class_type_stripped + " Direct Parent"] = compound_class.direct_parent

        return row

    def set_three_file_format_keys(self, output_model=None, class_type=None, class_level=None, correction_type=None,
                                   harmonise_annotations=None, aggregate_function=None,convert_units=True, master_unit='mmol/L'):

        combined_key = self.get_dataframe_key(type='combined', model=output_model,
                                                          class_type=class_type,
                                                          class_level=class_level,
                                                          correction_type=correction_type,
                                                          db_env=self.db_env, convert_units=convert_units,
                                                          master_unit=master_unit,
                                                          harmonise_annotations=harmonise_annotations,
                                                          aggregate_function=aggregate_function)

        sample_metadata_key = self.get_dataframe_key(type='sample_metadata', model=output_model,
                                                          class_type=class_type,
                                                          class_level=class_level,
                                                          correction_type=correction_type,
                                                          db_env=self.db_env,convert_units=convert_units, master_unit=master_unit,
                                                          harmonise_annotations=harmonise_annotations,
                                                          aggregate_function=aggregate_function)
        feature_metadata_key = self.get_dataframe_key(type='feature_metadata', model=output_model,
                                                           class_type=class_type,
                                                           class_level=class_level,
                                                           correction_type=correction_type,
                                                           db_env=self.db_env,convert_units=convert_units, master_unit=master_unit,
                                                           harmonise_annotations=harmonise_annotations,
                                                           aggregate_function=aggregate_function
                                                           )
        intensity_data_key = self.get_dataframe_key(type='intensity_data', model=output_model,
                                                         class_type=class_type,
                                                         class_level=class_level,
                                                         correction_type=correction_type,
                                                         db_env=self.db_env,convert_units=convert_units, master_unit=master_unit,
                                                         harmonise_annotations=harmonise_annotations,
                                                         aggregate_function=aggregate_function
                                                         )

        return combined_key, sample_metadata_key, feature_metadata_key, intensity_data_key

    def set_metaboanalyst_keys(self, output_model=None, class_type=None, class_level=None, correction_type=None,
                                   harmonise_annotations=None, aggregate_function=None,sample_label=None,
                                feature_label=None,convert_units=True, master_unit='mmol/L'):

        combined_key = self.get_dataframe_key(type='combined', model=output_model,
                                                   class_type=class_type,
                                                   class_level=class_level,
                                                   correction_type=correction_type,
                                                   db_env=self.db_env, convert_units=convert_units,
                                                   master_unit=master_unit,
                                                   harmonise_annotations=harmonise_annotations,
                                                   aggregate_function=aggregate_function)

        metaboanalyst_metadata_key = self.get_dataframe_key(type='metaboanalyst_metadata', model=output_model,
                                                            class_type=class_type, class_level=class_level,correction_type=correction_type,
                                                            convert_units=convert_units, master_unit=master_unit,
                                                            aggregate_function=aggregate_function, db_env=self.db_env,
                                                            sample_label=sample_label,
                                                            harmonise_annotations=harmonise_annotations)

        metaboanalyst_data_key = self.get_dataframe_key(type='metaboanalyst_data', model=output_model,
                                                        class_type=class_type, class_level=class_level,correction_type=correction_type,
                                                        convert_units=convert_units, master_unit=master_unit,
                                                        aggregate_function=aggregate_function, db_env=self.db_env,
                                                        sample_label=sample_label, feature_label=feature_label,
                                                        harmonise_annotations=harmonise_annotations)

        return combined_key, metaboanalyst_metadata_key, metaboanalyst_data_key

    def load_dataframe_from_task_run(self,type=None,task_run_id=None,
                                     convert_units=True, master_unit='mmol/L', reload_cache=False,
                                     correction_type=None, annotation_version=None, output_model='AnnotatedFeature',
                                     output_dir=None, harmonise_annotations=False,
                                     class_level=None, class_type=None, zero_lloq=True, inf_uloq=True,
                                     aggregate_function=None, scaling=None, transform=None, for_npyc=True,
                                     sample_orientation=None, sample_label=None, feature_orientation=None,
                                     feature_label=None, metadata_bin_definition=None,
                                     include_harmonised_metadata=True, only_harmonised_metadata=False,
                                     include_metadata=True, only_metadata=False,
                                     columns_to_include=None, columns_to_exclude=None,
                                     exclude_features_with_na_feature_values=False
                                     ):

        task_run = self.db_session.query(TaskRun).filter(TaskRun.id == task_run_id).first()
        if not task_run:
            raise Exception('Unknown TaskRun with id %s' % task_run_id)
        task_run_output = task_run.get_task_output(self.cache)
        if type in task_run_output.keys():
            dataframe = task_run_output[type]
        else:
            raise Exception('File type %s not found in TaskRun with id %s' % (type, task_run_id))
        if type in ['sample_metadata', 'feature_metadata', 'intensity_data']:
            if 'sample_metadata' not in task_run_output.keys():
                self.sample_metadata_key = '%s_sample_metadata' % task_run_id
            else:
                raise Exception("Sample Metadata file not in TaskRun %s output" % task_run_id)
            if 'feature_metadata' not in task_run_output.keys():
                self.feature_metadata_key = '%s_feature_metadata' % task_run_id
            else:
                raise Exception("Feature Metadata file not in TaskRun %s output" % task_run_id)
            if 'intensity_data' not in task_run_output.keys():
                self.intensity_data_key = '%s_intensity_data' % task_run_id
            else:
                raise Exception("Intensity data file not in TaskRun %s output" % task_run_id)
            self.dataframes[self.sample_metadata_key] = task_run_output['sample_metadata']
            self.dataframes[self.feature_metadata_key] = task_run_output['feature_metadata']
            self.dataframes[self.intensity_data_key] = task_run_output['intensity_data']

        transformed_dataframe = self.transform_dataframe(type, dataframe, transform=transform,
                                                         scaling=scaling, sample_label=sample_label,
                                                         sample_orientation=sample_orientation,
                                                         feature_orientation=feature_orientation,
                                                         metadata_bin_definition=metadata_bin_definition,
                                                         for_npyc=for_npyc,
                                                         include_metadata=include_metadata,
                                                         only_metadata=only_metadata,
                                                         columns_to_include=columns_to_include,
                                                         columns_to_exclude=columns_to_exclude,
                                                         include_harmonised_metadata=include_harmonised_metadata,
                                                         only_harmonised_metadata=only_harmonised_metadata,
                                                         task_run_id=task_run_id)
        return transformed_dataframe

    def load_dataframe(self, type='combined', combined_csv_path=None, convert_units=True, master_unit='mmol/L', reload_cache=False,
                       correction_type=None, annotation_version=None, output_model='AnnotatedFeature',output_dir=None,harmonise_annotations=False,
                       class_level=None,class_type=None,zero_lloq=True, inf_uloq=True,aggregate_function=None,save_cache=True,
                       sample_label=None,feature_label=None):
        # csv_path is the name of the file to store on disk - can be removed once the cache object is built as the files will just exist anyway.

        # If it is saved, it can cache the dataframe in redis
        if self.saved_query:

            key = self.get_dataframe_key(type=type,model=output_model,class_type=class_type,class_level=class_level,
                                         aggregate_function=aggregate_function,correction_type=correction_type,
                                         annotation_version=annotation_version,db_env=self.db_env,
                                         harmonise_annotations=harmonise_annotations,
                                          sample_label=sample_label,feature_label=feature_label,
                                          convert_units=convert_units, master_unit=master_unit)

            if type == 'combined':
                combined_key = self.get_dataframe_key(type='combined', model=output_model,
                                                           class_type=class_type,
                                                           class_level=class_level,
                                                           correction_type=correction_type,
                                                           db_env=self.db_env, convert_units=convert_units,
                                                           master_unit=master_unit,
                                                           harmonise_annotations=harmonise_annotations,
                                                           aggregate_function=aggregate_function)
            else:
                combined_key, sample_metadata_key, feature_metadata_key, intensity_data_key = self.set_three_file_format_keys(output_model=output_model,class_type=class_type,class_level=class_level,
                                                aggregate_function=aggregate_function,correction_type=correction_type,
                                                harmonise_annotations=harmonise_annotations,
                                                convert_units=convert_units, master_unit=master_unit)
            if type in ['metaboanalyst_metadata','metaboanalyst_data']:
                combined_key, metaboanalyst_metadata_key, metaboanalyst_data_key = self.set_metaboanalyst_keys(output_model=output_model,class_type=class_type,class_level=class_level,
                                            aggregate_function=aggregate_function,correction_type=correction_type,
                                            harmonise_annotations=harmonise_annotations,
                                            sample_label=sample_label,feature_label=feature_label,
                                            convert_units=convert_units, master_unit=master_unit)


            cache_key = self.saved_query.get_cache_dataframe_key(key)

            if key in self.dataframes and not reload_cache:
                self.output_files(type, key, combined_csv_path, output_dir)
                self.logger.info("Dataframe exists in QueryFactory %s" % key)
                return self.dataframes[key]

            if self.saved_query.cache_state:
                cache_state = dict(self.saved_query.cache_state)
            else:
                cache_state = {}
            feature_id_combined_dataframe_key = None
            if output_model == 'AnnotatedFeature':
                feature_id_combined_dataframe_key = self.get_dataframe_key(type='feature_id_combined_dataframe',model='AnnotatedFeature',
                                                                           correction_type=correction_type,db_env=self.db_env,
                                                                           harmonise_annotations=harmonise_annotations)
            # If the cache exists, get it from the cache
            if reload_cache and self.cache.exists(cache_key):
                self.logger.info("Reload cache is true so rebuilding cache")
                self.cache.delete(cache_key)
                if key in cache_state:
                    del cache_state[key]
                if output_model == 'AnnotatedFeature':
                    self.cache.delete(feature_id_combined_dataframe_key)
                    if feature_id_combined_dataframe_key in cache_state:
                        del cache_state[feature_id_combined_dataframe_key]

            if self.cache.exists(cache_key):
                self.dataframes[key] = self.cache.get(cache_key)
                self.logger.info("Got from cache %s" % key)
                if output_model == "AnnotatedFeature":
                    self.dataframes[feature_id_combined_dataframe_key] = self.cache.get(self.saved_query.get_cache_dataframe_key(feature_id_combined_dataframe_key))
                    self.logger.info("Got from cache %s" % feature_id_combined_dataframe_key)
                cache_state[key] = 'exists'
                self.saved_query.cache_state = cache_state
                self.db_session.commit()

                if self.cache.exists(self.saved_query.get_cache_dataframe_key(combined_key)):
                    self.dataframes[combined_key] = self.cache.get(
                        self.saved_query.get_cache_dataframe_key(combined_key))

                if type in ['sample_metadata','feature_metadata','intensity_data']:
                    if self.cache.exists(self.saved_query.get_cache_dataframe_key(sample_metadata_key)):
                        self.dataframes[sample_metadata_key] = self.cache.get(
                            self.saved_query.get_cache_dataframe_key(sample_metadata_key))
                    if self.cache.exists(self.saved_query.get_cache_dataframe_key(feature_metadata_key)):
                        self.dataframes[feature_metadata_key] = self.cache.get(
                            self.saved_query.get_cache_dataframe_key(feature_metadata_key))
                    if self.cache.exists(self.saved_query.get_cache_dataframe_key(intensity_data_key)):
                        self.dataframes[intensity_data_key] = self.cache.get(
                            self.saved_query.get_cache_dataframe_key(intensity_data_key))

                elif type in ['metaboanalyst_data','metaboanalyst_metadata']:
                    if self.cache.exists(self.saved_query.get_cache_dataframe_key(sample_metadata_key)):
                        self.dataframes[sample_metadata_key] = self.cache.get(
                            self.saved_query.get_cache_dataframe_key(sample_metadata_key))
                    if self.cache.exists(self.saved_query.get_cache_dataframe_key(feature_metadata_key)):
                        self.dataframes[feature_metadata_key] = self.cache.get(
                            self.saved_query.get_cache_dataframe_key(feature_metadata_key))
                    if self.cache.exists(self.saved_query.get_cache_dataframe_key(intensity_data_key)):
                        self.dataframes[intensity_data_key] = self.cache.get(
                            self.saved_query.get_cache_dataframe_key(intensity_data_key))

            else:
                # No cache
                self.logger.info("Not in cache %s" % key)
                #if output_model == "AnnotatedFeature":
                #    self.logger.info("Not in cache %s" % annotated_feature_id_key)
                if key not in cache_state:
                    cache_state[key] = 'generating'
                self.saved_query.cache_state = cache_state
                self.db_session.commit()
                # Expires after 24 hours

                if output_model != self.parent_model[output_model]:
                    parent_key = self.get_dataframe_key(type='combined',model=self.parent_model[output_model],
                                                        correction_type=correction_type,annotation_version=annotation_version,
                                                        db_env=self.db_env,harmonise_annotations=harmonise_annotations,
                                                        convert_units=convert_units,master_unit=master_unit
                                                        #scaling=scaling,transform=transform,
                                                        #sample_orientation=sample_orientation,
                                                        #sample_label=sample_label,
                                                        #feature_orientation=feature_orientation,
                                                        #feature_label=feature_label,
                                                        #metadata_bin_definition=metadata_bin_definition
                                                        )
                else:
                    parent_key = None

                if not parent_key:
                    # ie AnnotatedFeature
                    if type == 'combined':
                        self.dataframes[combined_key] = self.execute_and_build_dataframe(csv_path=combined_csv_path,
                                                                                convert_units=convert_units,
                                                                                master_unit=master_unit,
                                                                                class_level=class_level,
                                                                                class_type=class_type,
                                                                                correction_type=correction_type,
                                                                                annotation_version=annotation_version,
                                                                                aggregate_function=aggregate_function,
                                                                                output_model=output_model,
                                                                                zero_lloq=zero_lloq, inf_uloq=inf_uloq,
                                                                                harmonise_annotations=harmonise_annotations)
                        if save_cache:
                            self.cache.set(cache_key, self.dataframes[combined_key])
                        cache_state[combined_key] = 'exists'

                    else:
                        self.load_dataframe(type='combined', output_model=output_model,
                                            combined_csv_path=combined_csv_path, convert_units=convert_units,
                                            master_unit=master_unit, reload_cache=reload_cache,
                                            correction_type=correction_type,
                                            annotation_version=annotation_version,
                                            aggregate_function=aggregate_function, output_dir=output_dir,
                                            class_level=class_level, class_type=class_type, zero_lloq=zero_lloq,
                                            inf_uloq=inf_uloq,save_cache=save_cache,
                                            harmonise_annotations=harmonise_annotations)

                        sample_metadata,feature_metadata,intensity_data = self.build_intensity_data_sample_metadata_and_feature_metadata(
                                correction_type=correction_type,
                                output_model=output_model,
                                class_type=class_type,
                                class_level=class_level,
                                save_cache=save_cache,
                                aggregate_function=aggregate_function,
                                harmonise_annotations=harmonise_annotations)

                        self.dataframes[sample_metadata_key] = sample_metadata
                        self.dataframes[feature_metadata_key] = feature_metadata
                        self.dataframes[intensity_data_key] = intensity_data

                        if save_cache:
                            self.cache.set(self.saved_query.get_cache_dataframe_key(sample_metadata_key),
                                           sample_metadata)
                            self.cache.set(self.saved_query.get_cache_dataframe_key(feature_metadata_key),
                                           feature_metadata)
                            self.cache.set(self.saved_query.get_cache_dataframe_key(intensity_data_key), intensity_data)

                        if type in ['metaboanalyst_data','metaboanalyst_metadata']:
                            # build these!
                            metaboanalyst_metadata, metaboanalyst_data = self.build_metaboanalyst_data_and_metadata(sample_label=sample_label,
                                                                                                                   feature_label=feature_label,
                                                                                                                    feature_metadata=feature_metadata,
                                                                                                                    sample_metadata=sample_metadata,
                                                                                                                    intensity_data=intensity_data)
                            if save_cache:
                                self.cache.set(
                                    self.saved_query.get_cache_dataframe_key(metaboanalyst_metadata_key),
                                    metaboanalyst_metadata)
                                self.cache.set(self.saved_query.get_cache_dataframe_key(metaboanalyst_data_key),
                                               metaboanalyst_data)

                            self.dataframes[metaboanalyst_metadata_key] = metaboanalyst_metadata
                            self.dataframes[metaboanalyst_data_key] = metaboanalyst_data

                            #,sample_orientation=sample_orientation,sample_label=sample_label,feature_orientation=feature_orientation,feature_label=feature_label
                            # build the metaboanalyst_data and metaboanalyst_metadata


                else:
                    # ie CompoundClass
                    if parent_key not in self.dataframes.keys():
                        # Load the parent combined
                        self.load_dataframe(type='combined',output_model=self.parent_model[output_model],combined_csv_path=combined_csv_path, convert_units=convert_units,
                                            master_unit=master_unit, reload_cache=reload_cache,correction_type=correction_type,harmonise_annotations=harmonise_annotations,
                                            annotation_version=annotation_version, output_dir=output_dir,zero_lloq=zero_lloq, inf_uloq=inf_uloq,save_cache=save_cache)

                    # load the required dataframe
                    #combined_key = self.get_dataframe_key(type='combined',model=output_model,aggregate_function=aggregate_function,
                    #                                      class_type=class_type,class_level=class_level,harmonise_annotations=harmonise_annotations,
                    #                                      correction_type=correction_type,db_env=self.db_env)
                    self.dataframes[combined_key] = self.build_compound_class_dataframe(aggregate_function=aggregate_function,
                                                                    class_level=class_level, class_type=class_type,
                                                                    convert_units=convert_units, zero_lloq=zero_lloq,
                                                                    inf_uloq=inf_uloq,annotation_version=annotation_version,
                                                                    master_unit=master_unit, parent_key=parent_key,harmonise_annotations=harmonise_annotations)
                    self.cache.set(self.saved_query.get_cache_dataframe_key(combined_key), self.dataframes[combined_key])
                    cache_state[combined_key] = 'exists'
                    if type != 'combined':
                        sample_metadata,feature_metadata,intensity_data = self.build_intensity_data_sample_metadata_and_feature_metadata(
                            correction_type=correction_type,
                            output_model=output_model,
                            class_type=class_type,
                            class_level=class_level,
                            aggregate_function=aggregate_function,
                            output_dir=output_dir,
                            save_cache=save_cache,
                            harmonise_annotations=harmonise_annotations,
                            )

                        if type in ['metaboanalyst_data', 'metaboanalyst_metadata']:
                            # build these!
                            self.build_metaboanalyst_data_and_metadata(sample_metadata=sample_metadata,
                                                                       feature_metadata=feature_metadata,
                                                                       intensity_data=intensity_data,
                                                                        sample_label=sample_label,
                                                                       feature_label=feature_label)

                        cache_state[key] = 'exists'


                self.saved_query.cache_state = cache_state
                self.db_session.commit()
                self.logger.info("Set into redis %s" % key)

            if save_cache:
                if not self.cache.exists(self.saved_query.get_cache_dataframe_key(key)):
                    self.cache.set(self.saved_query.get_cache_dataframe_key(key),self.dataframes[key])
                if feature_id_combined_dataframe_key and feature_id_combined_dataframe_key in self.dataframes.keys() and not self.cache.exists(self.saved_query.get_cache_dataframe_key(feature_id_combined_dataframe_key)):
                    self.cache.set(self.saved_query.get_cache_dataframe_key(feature_id_combined_dataframe_key),self.dataframes[feature_id_combined_dataframe_key])

            self.output_files(type,key,combined_csv_path,output_dir)

        else:
            key = self.get_dataframe_key(type='combined',model=output_model,class_type=class_type,class_level=class_level,correction_type=correction_type,annotation_version=annotation_version,db_env=self.db_env,aggregate_function=aggregate_function)
            self.dataframes[key] = self.execute_and_build_dataframe(csv_path=combined_csv_path,
                                                                    harmonise_annotations=harmonise_annotations,
                                                                             output_model=output_model)
        if isinstance(self.dataframes[key],pd.DataFrame):
            self.dataframes[key] = self.dataframes[key].where(pd.notnull(self.dataframes[key]), None)

        return self.dataframes[key]

    def build_metaboanalyst_data_and_metadata(self,sample_metadata,feature_metadata,intensity_data,sample_label=None,feature_label=None):

        if not sample_label:
            sample_label = 'Sample ID'
        cols = list(sample_metadata)
        if sample_label not in sample_metadata:
            raise Exception("Sample Label does not exist %s" % sample_label)
        # move the column to head of list using index, pop and insert
        cols.insert(0, cols.pop(cols.index(sample_label)))
        # reorder
        metaboanalyst_metadata = sample_metadata.loc[:, cols]

        if not feature_label :
            feature_label = 'Feature Name'

        metaboanalyst_data = pd.DataFrame(columns=[sample_label])
        metaboanalyst_data.loc[:,sample_label] = sample_metadata.loc[:,sample_label]

        feature_row_index = 0
        while feature_row_index < feature_metadata.shape[0]:

            if feature_label in feature_metadata.columns:
                feature_column = feature_metadata.loc[feature_row_index, feature_label]
            elif feature_label == 'feature_name':
                feature_column = feature_metadata.loc[feature_row_index,feature_label]
            elif feature_label == 'cpd_id' and 'cpd_id' in feature_metadata.columns:
                feature_column = feature_metadata.loc[feature_row_index,feature_label]
            elif feature_label == 'rt_mz' and 'rt' in feature_metadata.columns and 'mz' in feature_metadata.columns:
                feature_column = "%s_%s" % (feature_metadata.loc[feature_row_index, 'rt_average'], feature_metadata.loc[feature_row_index, 'mz_average'])
            elif feature_label in ['ChEBI', 'PubChem', 'HMDB', 'LipidMAPS', 'Chemspider', 'inchi_key'] and (
                    'c1%s' % feature_label) in feature_metadata.columns:
                feature_column = self.build_feature_name_from_compound_id(feature_metadata.loc[feature_row_index,:], feature_label,
                                                                                feature_metadata.loc[feature_row_index,'ha_id'])
            else:
                feature_label = 'Feature Name'
                feature_column = feature_metadata.loc[feature_row_index,'Feature Name']

            metaboanalyst_data.insert(len(metaboanalyst_data.columns), feature_column,intensity_data[:,feature_row_index])

            #feature_column = feature_metadata.loc[feature_row_index,feature_label]
            #metaboanalyst_data.loc[:,feature_column] = intensity_data[:,feature_row_index]
            feature_row_index = feature_row_index + 1

        return metaboanalyst_metadata,metaboanalyst_data

    def load_npyc_dataset(self,sample_metadata,feature_metadata,intensity_data,assay_platform='MS',task_run_id=None):

        self.logger.info("Exporting data to allow nPYc dataset import")

        output_dir = "/tmp/phenomedb/queryfactory/%s/%s/" % (self.saved_query.id,task_run_id)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        unmasked_sample_metadata_file_path = self.output_files_for_download(type='sample_metadata',
                                                                                 file_key="",
                                                                                 dataframe=sample_metadata,
                                                                                 output_dir=output_dir, with_index=True,
                                                                                 with_header=True)

        unmasked_feature_metadata_file_path = self.output_files_for_download(type='feature_metadata',
                                                                                  file_key="",
                                                                                  dataframe=feature_metadata,
                                                                                  output_dir=output_dir,
                                                                                  with_index=True, with_header=True)

        unmasked_intensity_data_file_path = self.output_files_for_download(type='intensity_data',
                                                                                file_key="",
                                                                                dataframe=intensity_data,
                                                                                output_dir=output_dir)

        if not os.path.exists(unmasked_sample_metadata_file_path.replace(":", "_")) \
                or not os.path.exists(unmasked_feature_metadata_file_path.replace(":", "_")) \
                or not os.path.exists(unmasked_intensity_data_file_path.replace(":", "_")):
            raise Exception("The required files do not exist %s %s %s" % (unmasked_sample_metadata_file_path.replace(":", "_"),
                                                                          unmasked_feature_metadata_file_path.replace(":", "_"),
                                                                          unmasked_intensity_data_file_path.replace(":", "_")))
        self.logger.info("Loading nPYc dataset from %s" % output_dir)
        npyc_dataset = nPYc.MSDataset(unmasked_sample_metadata_file_path, fileType='csv export')
        #if assay_platform == 'MS':
        #    npyc_dataset = nPYc.MSDataset(unmasked_sample_metadata_file_path, fileType='csv export')
        #elif assay_platform == 'NMR':
        #    npyc_dataset = nPYc.NMRDataset(unmasked_sample_metadata_file_path, fileType='csv export')
        #else:
        #    raise Exception("Unknown assay_platform %s" % assay_platform)

        shutil.rmtree(output_dir)
        return npyc_dataset

    def apply_npyc_masks(self,sample_metadata,feature_metadata,intensity_data,sample_types=None,
                         assay_platform='MS',for_npyc=False,assay_roles=None,task_run_id=None):

        if (sample_types is not None and isinstance(sample_types, list) and len(sample_types) != 0) \
            or (assay_roles is not None and isinstance(assay_roles, list) and len(assay_roles) != 0):
            self.logger.info("Applying Masks %s %s" % (sample_types,assay_roles))
            self.npyc_dataset = self.load_npyc_dataset(sample_metadata=sample_metadata,
                                                       feature_metadata=feature_metadata,
                                                       intensity_data=intensity_data,
                                                       assay_platform=assay_platform,
                                                       task_run_id=None)
            self.npyc_dataset.updateMasks(filterFeatures=False, sampleTypes=sample_types, assayRoles=assay_roles)
            self.npyc_dataset.applyMasks()
            self.logger.info("Masks applied!")

            masked_sample_metadata = self.npyc_dataset.sampleMetadata.copy()
            masked_feature_metadata = self.npyc_dataset.featureMetadata.copy()
            masked_intensity_data = self.npyc_dataset.intensityData.copy()

        else:
            masked_sample_metadata = sample_metadata.copy()
            masked_feature_metadata = feature_metadata.copy()
            masked_intensity_data = intensity_data.copy()

        if not for_npyc and 'Metadata Available' in masked_sample_metadata:
            self.logger.info("Dropping the Metadata Available=TRUE column")
            masked_sample_metadata = masked_sample_metadata.drop(axis=1, columns='Metadata Available')

        self.logger.info("Masked data saved")
        return masked_sample_metadata,masked_feature_metadata,masked_intensity_data


    def transform_dataframe(self,type,combined_data=None,intensity_data=None,feature_metadata=None,
                            sample_metadata=None,metaboanalyst_metadata=None,metaboanalyst_data=None,
                            transform=None,scaling=None,sample_label=None,remove_empty_metadata_columns=True,
                            sample_orientation=None, feature_orientation=None,for_npyc=False,assay_roles=None,
                            exclude_features_not_in_all_projects=False,sample_types=None,assay_platform='MS',
                            metadata_bin_definition=None,columns_to_include=None,exclude_na_metadata_samples=False,
                            columns_to_exclude=None,include_metadata=True,include_harmonised_metadata=True,
                            only_metadata=None,only_harmonised_metadata=None,exclude_na_metadata_columns=False,
                            exclude_features_with_na_feature_values=True,drop_sample_column=False,task_run_id=None):

        if type == ['3 file format'] and (sample_metadata is None or intensity_data is None or feature_metadata is None):
            raise Exception("Sample Metadata, Feature Metadata, and Intensity Data must be set")
        elif type == 'metaboanalyst' and (metaboanalyst_data is None and metaboanalyst_metadata is None):
            raise Exception("Metaboanalyst_data and metaboanalyst_metadat must set")
        elif type == 'combined' and combined_data is None:
            raise Exception("combined_data must set")

        if not sample_label:
            sample_label = 'Sample ID'

        if not columns_to_include:
            columns_to_include = []
        if not columns_to_exclude:
            columns_to_exclude = []

        # 1. Apply feature exclusions and sample type and assay role masks
        if exclude_features_with_na_feature_values:
            i = 0
            features_to_exclude = []
            if type == '3 file format':
                while i < feature_metadata.shape[0]:
                    if np.isnan(intensity_data[:,i]).any():
                        features_to_exclude.append(i)
                    i = i + 1

                feature_metadata = feature_metadata.drop(index=features_to_exclude)
                intensity_data = np.delete(intensity_data, features_to_exclude, 1)

            elif type == 'metaboanalyst':
                while i < metaboanalyst_data.shape[1]:
                    if metaboanalyst_data.columns[i] != sample_label and metaboanalyst_data.iloc[:,i].isnull().values.any():
                        features_to_exclude.append(i)
                    i = i + 1
                metaboanalyst_data = metaboanalyst_data.drop(features_to_exclude,axis=1)

        if exclude_features_not_in_all_projects:
            p = 0
            features_to_remove = []
            while p < feature_metadata.shape[0]:
                feature_name = feature_metadata.loc[p,'feature_name']
                for project in sample_metadata['Project'].unique():
                    sample_indices = np.where(sample_metadata['Project'] == project)[0]
                    if np.all(intensity_data[sample_indices, p] == 0.00):
                        if p not in features_to_remove:
                            features_to_remove.append(p)
                p = p + 1
            intensity_data = np.delete(intensity_data.copy(), features_to_remove, 1)
            feature_metadata = feature_metadata.drop(index=features_to_remove).reset_index().drop(columns=['index'])
            self.logger.info("Removed the following features which are not consistent between projects %s" % features_to_remove )

      #  if assay_platform == 'NMR':
      #      if 'Delta PPM' not in sample_metadata.columns:
      #          sample_metadata['Delta PPM'] = 0
      #      if 'Line Width (Hz)' not in sample_metadata.columns:
      #          sample_metadata['Line Width (Hz)'] = 0

        #if assay_platform == 'MS':
        sample_metadata, feature_metadata, intensity_data = self.apply_npyc_masks(sample_metadata=sample_metadata,
                                                                                  feature_metadata=feature_metadata,
                                                                                intensity_data=intensity_data,
                                                                                  sample_types=sample_types,
                                                                                  assay_roles=assay_roles,
                                                                                  for_npyc=for_npyc,
                                                                                assay_platform=assay_platform,
                                                                                  task_run_id=None)

        # 2. Apply the transformations (scaling/transform)
        # Scale the intensities
        if type == '3 file format' and isinstance(intensity_data,np.ndarray) and scaling:
            if scaling not in ['uv', 'mc', 'pa',0,1,2,'med']:
                raise Exception("Scaling type not implemented/recognised: %s" % scaling)
            intensity_data = self.scaling_per_project_assay(sample_metadata,feature_metadata,intensity_data,scaling,assay_platform)

        # Transform the intensities
        if type == '3 file format' and isinstance(intensity_data, np.ndarray) and transform:
            if transform == 'log':
                scaled_intensity_data = np.log10(intensity_data + (1 - intensity_data.min()))
                intensity_data = scaled_intensity_data
                self.logger.info("intensity data log transformed")
            elif transform == 'sqrt':
                scaled_intensity_data = np.sqrt(intensity_data + (1 - intensity_data.min()))
                intensity_data = scaled_intensity_data
                self.logger.info("intensity data sqrt transformed")
            else:
                raise Exception("Unknown transform function %" % transform)

        # Exclude a sample metadata columns as required
        if type == '3 file format':
            metadata_dataframe = sample_metadata
        elif type == 'metaboanalyst':
            metadata_dataframe = metaboanalyst_metadata
        if type in ['3 file format','metaboanalyst']:
            output_dataframe = pd.DataFrame()

            for (colname, colval) in metadata_dataframe.iteritems():
                if colname == sample_label:
                    output_dataframe.insert(len(output_dataframe.columns), colname, colval.values)
                elif len(columns_to_exclude) > 0 and colname in columns_to_exclude:
                    # ignore these are they are specifically being ignored
                    pass

                elif remove_empty_metadata_columns and metadata_dataframe[colname].isnull().values.all():
                    pass

                elif len(columns_to_include) > 0 and colname in columns_to_include:
                    # include these (unique will be excluded later)
                    output_dataframe.insert(len(output_dataframe.columns), colname, colval.values)

                elif include_harmonised_metadata and re.search('h_metadata::', colname):
                    output_dataframe.insert(len(output_dataframe.columns), colname, colval.values)

                elif include_metadata and re.search('metadata::', colname):
                    output_dataframe.insert(len(output_dataframe.columns), colname, colval.values)

                elif len(columns_to_include) > 0 and colname not in columns_to_include:
                    # ignore these (unique will be excluded later)
                    pass

                elif only_metadata and not re.search('metadata::', colname):
                    # ignore these as we do not want any non-metadata columns
                    pass

                elif re.search('metadata::', colname) and only_harmonised_metadata and not re.search('h_metadata::',
                                                                                                     colname):
                    # ignore these as we only want the harmonised metadata (but keep any fields that not metadata::, ie sample_name)
                    pass

                elif re.search('metadata::', colname) and exclude_na_metadata_columns and metadata_dataframe[colname].isnull().values.any():
                    # ignore these as they have null values!
                    pass

                else:
                    output_dataframe.insert(len(output_dataframe.columns), colname, colval.values)

            samples_to_drop = []
            if exclude_na_metadata_samples:
                i = 0
                samples_to_drop = []
                while i < output_dataframe.shape[0]:
                    if output_dataframe.loc[i,:].isnull().values.any():
                        samples_to_drop.append(i)
                    i = i + 1

                output_dataframe = output_dataframe.drop(index=samples_to_drop)
            if type == '3 file format':
                if len(samples_to_drop) > 0:
                    intensity_data = np.delete(intensity_data, samples_to_drop, 1)
                sample_metadata = output_dataframe
            elif type == 'metaboanalyst':
                metaboanalyst_metadata = output_dataframe
                if len(samples_to_drop) > 0:
                    metaboanalyst_data = metaboanalyst_data.drop(index=samples_to_drop)

        # Add the metadata bins
        if metadata_bin_definition is not None and isinstance(metadata_bin_definition, dict):

            if type == 'combined':
                metadata_dataframe = combined_data
            elif type == '3 file format':
                metadata_dataframe = sample_metadata
            elif type == 'metaboanalyst_metadata':
                metadata_dataframe = metaboanalyst_metadata

            for label, definition in metadata_bin_definition.items():
                if definition['method'] == 'bin':
                    bins = [float(x) for x in definition['bins']]
                    metadata_dataframe[label] = pd.cut(metadata_dataframe.loc[:, definition['column']],
                                              bins, include_lowest=True).astype('str')
            metadata_dataframe = metadata_dataframe.where(pd.notnull(metadata_dataframe),None)
            if type == 'combined':
                combined_data = metadata_dataframe
            elif type == '3 file format':
                sample_metadata = metadata_dataframe
            elif type == 'metaboanalyst':
                metaboanalyst_metadata = metadata_dataframe

        # Format specific column drops
        if type == '3 file format':
            sample_metadata['Run Order'] = range(1, 1 + sample_metadata.shape[0])
            sample_metadata.insert(len(sample_metadata.columns), 'Metadata Available', 'TRUE')
            if 'Feature Name' not in feature_metadata.columns and 'feature_name' in feature_metadata.columns:
                feature_metadata.loc[:,'Feature Name'] = feature_metadata.loc[:,'feature_name']

        if type == 'metaboanalyst':
            metaboanalyst_metadata = metaboanalyst_metadata.rename(columns={sample_label:'Sample'})
            metaboanalyst_data = metaboanalyst_data.rename(columns={sample_label: 'Sample'})

            if drop_sample_column:
                metaboanalyst_metadata = metaboanalyst_metadata.drop('Sample',axis=1)
                metaboanalyst_data = metaboanalyst_data.drop('Sample', axis=1)

        if for_npyc and 'Correction Batch' not in sample_metadata.columns and 'Batch' in sample_metadata.columns:
            sample_metadata['Correction Batch'] = sample_metadata['Batch']
        elif for_npyc and 'Correction Batch' not in sample_metadata.columns:
            sample_metadata['Correction Batch'] = 1

        if type == '3 file format':

            if drop_sample_column:
                sample_metadata = sample_metadata.drop(sample_label,axis=1)

            return sample_metadata, feature_metadata, intensity_data
        elif type == 'metaboanalyst':
            return metaboanalyst_metadata, metaboanalyst_data
        elif type == 'combined':
            return combined_data


    def get_implemented_models(self):
        #models = list(self.join_routes.keys())
        #return models + ["CompoundClass"]
        return self.join_routes.keys()

    def output_files_for_download(self,type,file_key,dataframe,output_dir,with_header=False,with_index=False):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if type == 'combined':
            filepath = output_dir + "/%s_%s_combinedData.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_"))
        elif type == 'intensity_data':
            filepath = output_dir + "/%s_%s_intensityData.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("intensity_data_", ""))
        elif type == 'sample_metadata':
            filepath = output_dir + "/%s_%s_sampleMetadata.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("sample_metadata_", ""))
        elif type == 'feature_metadata':
            filepath = output_dir + "/%s_%s_featureMetadata.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("feature_metadata_", ""))
        elif type == 'metaboanalyst_data':
            filepath = output_dir + "/%s_%s_metaboanalyst_data.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("metaboanalyst_data_", ""))
        elif type == 'metaboanalyst_metadata':
            filepath = output_dir + "/%s_%s_metaboanalyst_metadata.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("metaboanalyst_metadata_", ""))
        elif type == 'feature_metadata':
            filepath = output_dir + "/%s_%s_featureMetadata.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("feature_metadata_", ""))
        elif type == 'feature_id_matrix':
            filepath = output_dir + "/%s_%s_featureIDMatrix.csv" % (
                self.saved_query.name.replace(" ", "_"), file_key.replace(":", "_").replace("feature_id_matrix_", ""))
        elif type == 'feature_id_combined_dataframe':
            filepath = output_dir + "/%s_%s_featureIDCombinedDataframe.csv" % (
                self.saved_query.name.replace(" ", "_"),
                file_key.replace(":", "_").replace("feature_id_combined_dataframe_", ""))
        else:
            raise Exception("Unknown dataframe type %s" % type)

        if isinstance(dataframe,(np.matrix,np.ndarray)):
            np.savetxt(filepath,dataframe,delimiter=',')
        else:
            pd.DataFrame(dataframe).to_csv(filepath, header=with_header, index=with_index,encoding='utf-8-sig')

        self.logger.info("Dataset exported: %s" % filepath)

        return filepath

    def scaling_per_project_assay(self,sample_metadata,feature_metadata,intensity_data,scaling,assay_platform='MS'):

        #1. chop up the matrix into projects and assays, and scale each seperately.

        self.logger.debug("scaling %s" % scaling)
        self.logger.debug("assay_platform %s" % assay_platform)
        #if assay_platform == 'NMR':

        #    if scaling in ['uv', 'mc', 'pa']:
        #        scaling = utils.get_pyc_scaling(scaling)

        #    if scaling in [0, 1, 2]:
        #        scaler = ChemometricsScaler(scaling)
        #        scaler.fit(intensity_data)
        #        output_intensity_matrix = scaler.transform(intensity_data, copy=True)
        #        self.logger.info('Intensity data scaled using %s' % scaling)
        #    elif scaling == 'med':
        #        output_intensity_matrix = intensity_data / (np.median(intensity_data, axis=0) + (1 - intensity_data.min()))
        #        self.logger.info('Intensity data scaled using %s' % scaling)
        #    else:
        #        raise Exception("Unknown scaling method %" % scaling)
        #else:

        output_intensity_matrix = intensity_data.copy()

        for project in sample_metadata['Project'].unique():

            sample_indices = np.where(sample_metadata['Project'] == project)[0]
            sample_intensities = intensity_data[sample_indices,:].copy()

            for assay in feature_metadata['assay'].unique():

                for annotation_method in feature_metadata['annotation_method'].unique():
                    self.logger.debug("scaling %s %s %s" % (project, assay,annotation_method))

                    feature_indices = np.where((feature_metadata['assay'] == assay) & (feature_metadata['annotation_method'] == annotation_method))[0]
                    if len(feature_indices) > 0:
                        feature_intensities = sample_intensities[:, feature_indices].copy()

                        if scaling in ['uv', 'mc', 'pa']:
                            scaling = utils.get_pyc_scaling(scaling)

                        if scaling in [0,1,2]:
                            scaler = ChemometricsScaler(scaling)
                            scaler.fit(feature_intensities)
                            scaled_intensities = scaler.transform(feature_intensities, copy=True)
                            self.logger.info('Intensity data scaled using %s' % scaling)
                        elif scaling == 'med':
                            scaled_intensities = feature_intensities / (np.median(feature_intensities,axis=0) + (1 - feature_intensities.min()))
                            self.logger.info('Intensity data scaled using %s' % scaling)
                        else:
                            raise Exception("Unknown scaling method %" % scaling)

                        self.logger.debug('scaled... reconstructing matrix')

                        s = 0
                        for sample_index in sample_indices:
                            f = 0
                            for feature_index in feature_indices:
                                output_intensity_matrix[sample_index,feature_index] = scaled_intensities[s,f]
                                f = f + 1
                            s = s + 1

        self.logger.debug('scaling complete')

        return output_intensity_matrix

    def output_files(self,type,key,combined_csv_path,output_dir):

        if combined_csv_path and type == 'combined':
            self.dataframes[key].to_csv(combined_csv_path, index=False)
            self.dataframe_csv_paths[key] = combined_csv_path
            self.logger.info("SavedQuery %s %s dataframe written to file %s" % (key, type, combined_csv_path))

        elif output_dir and key not in self.dataframe_csv_paths.keys():
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # if the path does not exist, write out the dataframe and set the path!
            # The type part of the key must be replaced, otherwise the npyc-toolbox dataset load wont work
            if type == 'combined':
                filepath = output_dir + "/%s_%s_combinedData.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_"))
            elif type == 'intensity_data':
                filepath = output_dir + "/%s_%s_intensityData.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("intensity_data_",""))
            elif type == 'sample_metadata':
                filepath = output_dir + "/%s_%s_sampleMetadata.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("sample_metadata_",""))
            elif type == 'feature_metadata':
                filepath = output_dir + "/%s_%s_featureMetadata.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("feature_metadata_",""))
            elif type == 'metaboanalyst_data':
                filepath = output_dir + "/%s_%s_metaboanalyst_data.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("metaboanalyst_data_",""))
            elif type == 'metaboanalyst_metadata':
                filepath = output_dir + "/%s_%s_metaboanalyst_metadata.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("metaboanalyst_metadata_",""))
            elif type == 'feature_metadata':
                filepath = output_dir + "/%s_%s_featureMetadata.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("feature_metadata_",""))
            elif type == 'feature_id_matrix':
                filepath = output_dir + "/%s_%s_featureIDMatrix.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("feature_id_matrix_", ""))
            elif type == 'feature_id_combined_dataframe':
                filepath = output_dir + "/%s_%s_featureIDCombinedDataframe.csv" % (
                    self.saved_query.name.replace(" ", "_"), key.replace(":", "_").replace("feature_id_combined_dataframe_", ""))
            else:
                raise Exception("Unknown dataframe type %s" % type)
            if type in ['sample_metadata', 'feature_metadata']:
                self.dataframes[key].to_csv(filepath)
            else:
                pd.DataFrame(self.dataframes[key]).to_csv(filepath, header=None, index=None)

            self.dataframe_csv_paths[key] = filepath

            self.logger.info("SavedQuery %s %s dataframe written to file %s" % (key,type,filepath))



class QueryFilter:
    """QueryFilter class. Class for storing filter objects to simplify generating queries.

        Example usage:
            AND filter:
            filter = QueryFilter("AND")
            sub_filter = QuerySubFilter("AND")
            subfilter.add_match(model="Project",property="name",operator="eq",value="PipelineTesting")
            cohort_query = CohortQuery()
            cohort_query.add_filter(filter)

            OR filter:
            filter = QueryFilter('OR')
            sub_filter = QuerySubFilter("AND")
            filter.add_match(model="Project",property="name",operator="eq",value="PipelineTesting")
            filter.add_match(model="Project",property="name",operator="eq",value="nPYc-toolbox-tutorials")
            cohort_query = CohortQuery()
            cohort_query.add_filter(filter)

            simple AND:
            filter = QueryFilter("AND",model="Project",property="name",operator="eq",value="PipelineTesting")
            
    :param filter_operator: The top-level filter operator, "AND" or "OR", defaults to "AND".
    :type filter_operator: str, optional
    :param filter_dict: The filter dictionary to use, defaults to None.
    :type filter_dict: dict, optional
    :param model: The model to match on, defaults to None.
    :type model: str, optional
    :param property: The property to match on, defaults to None.
    :type property: str, optional
    :param operator: The operator to use, defaults to None.
    :type operator: str, optional
    :param value: The value to match on, defaults to None.
    :type value: str, int, float, or list, optional
    """

    def __init__(self, filter_operator='AND', filter_dict=None, model=None, property=None, operator=None, value=None):

        self.sub_filters = []
        self.filter_operator = filter_operator

        if filter_dict:
            self.filter_operator = filter_dict['filter_operator']

            for sub_filter in filter_dict['sub_filters']:
                self.sub_filters.append(QuerySubFilter(sub_filter))

        elif model and property and operator and value:
            self.sub_filters.append(QuerySubFilter(model=model, property=property, operator=operator, value=value))

    def add_sub_filter(self, sub_filter=None, sub_filter_dict=None, sub_filter_operator='AND', model=None,
                       property=None, operator=None, value=None):
        """Add a subfilter to the filter. Either QuerySubFilter, or sub_filter_dict, or match properties.

        :param sub_filter: The QuerySubFilter to add, defaults to None.
        :type sub_filter: :class:`phenomedb.query_factory.QuerySubFilter`, optional
        :param sub_filter_dict: The sub_filter dictionary to add, defaults to None.
        :type sub_filter_dict: dict, optional
        :param sub_filter_operator: The sub_filter operator, 'AND' or 'OR', defaults to 'AND'.
        :type sub_filter_operator: str, optional
        :param model: The model to match on, defaults to None.
        :type model: str, optional
        :param property: The property to match on, defaults to None.
        :type property: str, optional
        :param operator: The operator to use, defaults to None.
        :type operator: str, optional
        :param value: The value to match on, defaults to None.
        :type value: str, int, float, or list, optional
        """

        if sub_filter:
            self.sub_filters.append(sub_filter)

        elif sub_filter_dict:
            self.sub_filters.append(QuerySubFilter(sub_filter_dict=sub_filter_dict))

        elif model and property and operator and value:
            self.sub_filters.append(
                QuerySubFilter(sub_filter_operator=sub_filter_operator, model=model, property=property,
                               operator=operator, value=value))

    def get_filter_dict(self):
        """Get the filter dictionary corresponding to this filter.

        :return: The filter dictionary.
        :rtype: dict
        """

        filter_dict = {'filter_operator': self.filter_operator,
                       'sub_filters': []}

        for sub_filter in self.sub_filters:
            filter_dict['sub_filters'].append(sub_filter.get_sub_filter_dict())

        return filter_dict

    def add_match(self, query_sub_filter_match=None, model=None, property=None, operator=None, value=None,
                  match_dict=None):
        """Add a match to the Filter.

        :param query_sub_filter_match: The QuerySubFilter + QueryMatch to add, defaults to None.
        :type query_sub_filter_match: dict, optional
        :param model: The model to match on, defaults to None.
        :type model: str, optional
        :param property: The property to match on, defaults to None.
        :type property: str, optional
        :param operator: The operator to use, defaults to None.
        :type operator: str, optional
        :param value: The value to match on, defaults to None.
        :type value: str, int, float, or list, optional
        :param match_dict: The match dictionary to add, defaults to None
        :type match_dict: dict, optional
        """

        if query_sub_filter_match and len(self.sub_filters) > 0:
            self.sub_filters[0].matches.append(query_sub_filter_match)

        elif match_dict:
            self.sub_filters[0].matches.append(QueryMatch(match_dict=match_dict))

        elif model and property and operator and value:
            self.sub_filters[0].matches.append(
                QueryMatch(model=model, property=property, operator=operator, value=value))


class QuerySubFilter:
    """
        QuerySubFilter class. Class for storing subfilter objects to simplify generating nested and/or queries.

        Example usage:
            AND filter:
                filter = QueryFilter(filter_operator="AND")
                sub_filter = QuerySubFilter(sub_filter_operator="AND")
                sub_filter.add_match(model="Project",property="name",operator="eq",value="PipelineTesting")
                filter.add_sub_filter(add_sub_filter)
                cohort_factory = SampleFactory()
                cohort_factory.add_filter(filter)

            OR filter:
                filter = QueryFilter(filter_operator='OR')
                sub_filter = QuerySubFilter(sub_filter_operator="AND")
                sub_filter.add_match(model="Project",property="name",operator="eq",value="PipelineTesting")
                sub_filter.add_match(model="Project",property="name",operator="eq",value="nPYc-toolbox-tutorials")
                filter.add_sub_filter(sub_filter)
                cohort_factory = SampleFactory()
                cohort_factory.add_filter(filter)

    :param sub_filter_operator: The sub_filter operator, 'AND' or 'OR', defaults to 'AND'.
    :type sub_filter_operator: str, optional
    :param model: The model to match on, defaults to None.
    :type model: str, optional
    :param property: The property to match on, defaults to None.
    :type property: str, optional
    :param operator: The operator to use, defaults to None.
    :type operator: str, optional
    :param value: The value to match on, defaults to None.
    :type value: str, int, float, or list, optional
    """

    def __init__(self, sub_filter_operator='AND', sub_filter_dict=None, model=None, property=None, operator=None,
                 value=None):

        self.matches = []
        self.sub_filter_operator = sub_filter_operator

        if sub_filter_dict:
            self.sub_filter_operator = sub_filter_dict['match_operator']

            for match in sub_filter_dict['matches']:
                self.matches.append(QueryMatch(match))

        elif model and property and operator and value:
            self.matches.append(QueryMatch(model=model, property=property, operator=operator, value=value))

    def add_match(self, query_sub_filter_match=None, model=None, property=None, operator=None, value=None,
                  match_dict=None):
        """Add a match to the QuerySubFilter.

        :param query_sub_filter_match: The QuerySubFilter + QueryMatch to add, defaults to None.
        :type query_sub_filter_match: dict, optional
        :param model: The model to match on, defaults to None.
        :type model: str, optional
        :param property: The property to match on, defaults to None.
        :type property: str, optional
        :param operator: The operator to use, defaults to None.
        :type operator: str, optional
        :param value: The value to match on, defaults to None.
        :type value: str, int, float, or list, optional
        :param match_dict: The match dictionary to add, defaults to None
        :type match_dict: dict, optional
        """

        if query_sub_filter_match:
            self.matches.append(query_sub_filter_match)

        elif match_dict:
            self.matches.append(QueryMatch(match_dict=match_dict))

        elif model and property and operator and value:
            self.matches.append(QueryMatch(model=model, property=property, operator=operator, value=value))

    def get_sub_filter_dict(self):
        """Get the sub_filter_dict from the QuerySubFilter.

        :return: sub_filter_dictionary
        :rtype: dict
        """

        sub_filter_dict = {'sub_filter_operator': self.sub_filter_operator,
                           'matches': []}

        for match in self.matches:
            sub_filter_dict['matches'].append(match.get_match_dict())

        return sub_filter_dict


class QueryMatch:
    """QueryMatch class. Class for building Match object to simplify generating queries.

    :param model: The model to match on, defaults to None.
    :type model: str, optional
    :param property: The property to match on, defaults to None.
    :type property: str, optional
    :param operator: The operator to use, defaults to None.
    :type operator: str, optional
    :param value: The value to match on, defaults to None.
    :type value: str, int, float, or list, optional
    :param match_dict: The match dictionary to add, defaults to None
    :type match_dict: dict, optional
    :raises Exception: If not all match properties are set.
    """

    def __init__(self, model=None, property=None, operator=None, value=None, match_dict=None):

        if match_dict:
            self.model = match_dict['model']
            self.property = match_dict['property']
            self.operator = match_dict['operator']
            self.value = match_dict['value']

        elif not model or not property or not operator or not value:

            raise Exception("Match added with missing params")

        else:

            self.model = model
            self.property = property
            self.operator = operator
            self.value = value

    def get_match_dict(self):
        """Get the match_dict from the QueryMatch.

        :return: the match_dictionary.
        :rtype: dict
        """

        return {
            "model": self.model,
            "property": self.property,
            "operator": self.operator,
            "value": self.value,
        }


class MetadataFilter(QuerySubFilter):
    """MetadataFilter class. Creates a sub_filter with 2 matches.

    :param harmonised_metadata_field_name: The name of the harmonised_metadata_field.
    :type harmonised_metadata_field_name: str
    :param operator: The operator to use, defaults to None.
    :type operator: str, optional
    :param value: The value to match on, defaults to None.
    :type value: str, int, float, or list, optional
    """

    def __init__(self, harmonised_metadata_field_name, operator=None, value=None):
        super().__init__()

        self.matches.append(QueryMatch(model='HarmonisedMetadataField', property='name', operator='eq',
                                       value=harmonised_metadata_field_name))

        # TODO: Identify the property type to match on. Via db lookup.
        self.matches.append(
            QueryMatch(model='MetadataValue', property='harmonised_numeric_value', operator=operator, value=value))


class ProjectRoleFilter(QuerySubFilter):

    def __init__(self, role_id):
        """The Role ID to add the project filter to.

        :param role_id: The Role ID to filter projects by.
        :type role_id: int
        """

        super().__init__()

        self.matches.append(QueryMatch(model='ProjectRole', property='role_id', operator='eq', value=role_id))
