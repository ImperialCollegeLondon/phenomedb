import os

import pytest
from pathlib import Path
import sys
sys.path.insert(0,str(Path("../../").absolute()))
from phenomedb.query_factory import *
from phenomedb.cache import *
import phenomedb.database as db
import redis
import pandas as pd

class TestQueryFactory():

    project_name = "PipelineTesting"

    def test_aaa_sql_injection(self,create_min_database):

        query = ";insert into project (name,description,date_added) values('test_sql_injection','test sql injection',now());"

        query_factory = QueryFactory(query_name='test query',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value=query))
        query_factory.generate_and_execute_query()

        db_session = db.get_test_database_session()
        assert db_session.query(Project).filter(Project.name=='test_sql_injection').count() == 0

    def test_zzz_test_redis_dataframe(self,create_min_database,
                                    delete_test_cache,
                                    delete_saved_queries,
                                    create_lab,
                                    create_pipeline_testing_project,
                                    create_ms_assays,
                                    create_annotation_methods,
                                    import_devset_sample_manifest,
                                    import_devset_bile_acid_targeted_annotations,
                                      dummy_harmonise_annotations):

        query_factory = QueryFactory(query_name='test_zzz_test_redis_dataframe',query_description='test description',project_short_label='test',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='TargetLynx'))

        cache = redis.Redis(host=config['REDIS']['host'],port=config['REDIS']['port'],password=config['REDIS']['password'])
        query_factory.save_query()
        combined_key, sample_metadata_key, feature_metadata_key, intensity_data_key = query_factory.set_three_file_format_keys(
            output_model='AnnotatedFeature', correction_type="SR", harmonise_annotations=True)

        assert cache.exists(combined_key) == 0
        assert cache.exists(sample_metadata_key) == 0
        assert cache.exists(feature_metadata_key) == 0
        assert cache.exists(intensity_data_key) == 0

        intensity_data = query_factory.load_dataframe(output_model='AnnotatedFeature', type='intensity_data',correction_type='SR',
                                                       harmonise_annotations=True,reload_cache=True,save_cache=True)
        #assert cache.exists(combined_key) == 1
        #assert cache.exists(intensity_data_key) == 1

        #assert combined_key in query_factory.dataframes.keys()
        #assert intensity_data_key in query_factory.dataframes.keys()

        feature_metadata = query_factory.load_dataframe(output_model='AnnotatedFeature', type='feature_metadata',harmonise_annotations=True)
        sample_metadata = query_factory.load_dataframe(output_model='AnnotatedFeature', type='sample_metadata',harmonise_annotations=True)
        #assert cache.exists(sample_metadata_key) == 1
        #assert cache.exists(feature_metadata_key) == 1
        #assert sample_metadata_key in query_factory.dataframes.keys()
        #assert feature_metadata_key in query_factory.dataframes.keys()

        sample_metadata, feature_metadata, intensity_data_scaled = query_factory.transform_dataframe(type='3 file format',sample_metadata=sample_metadata,
                                                                                            feature_metadata=feature_metadata,
                                                                                            intensity_data=intensity_data,scaling='uv')

        #assert intensity_data is not None
        #assert intensity_data_scaled is not None

        cache.delete(sample_metadata_key)
        cache.delete(feature_metadata_key)
        cache.delete(intensity_data_key)
        cache.delete(combined_key)

    def test_z_test_cache_task(self,create_min_database,
                                    delete_test_cache,
                                    delete_saved_queries,
                                    create_lab,
                                    create_pipeline_testing_project,
                                    create_ms_assays,
                                    create_annotation_methods,
                                    import_devset_sample_manifest,
                                    import_devset_bile_acid_targeted_annotations,
                                    dummy_harmonise_annotations                               ):

        query_factory = QueryFactory(query_name='test_z_test_cache_task',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='TargetLynx'))

        cache = redis.Redis(host=config['REDIS']['host'],port=config['REDIS']['port'],password=config['REDIS']['password'])

        # If the query is a SavedQuery, there should be an id and a key in the redis cache
        saved_query = query_factory.save_query()

        task = CreateSavedQueryDataframeCache(output_model='AnnotatedFeature',username=config['TEST']['username'],saved_query_id=saved_query.id,db_env='TEST')
        output = task.run()


        saved_query_factory = QueryFactory(saved_query=saved_query,db_env='TEST')
        df = saved_query_factory.load_dataframe(output_model='AnnotatedFeature')

        assert df.empty != True
        assert saved_query_factory.saved_query.id != None
        key = saved_query_factory.get_dataframe_key(type='combined',model='AnnotatedFeature',db_env="TEST")
        cache_key = saved_query_factory.saved_query.get_cache_dataframe_key(key)
        assert cache.exists(cache_key) == True
        cache.delete(cache_key)

    def test_a1(self,create_min_database,
                    create_pipeline_testing_project):

        query_dict = {'model': 'SampleAssay',
                      'joins': ['Sample', 'MetadataValue', 'MetadataField', 'HarmonisedMetadataField'],
                      'filters': [{'filter_operator': 'OR',
                                   'filter_preset': 'Metadata',
                                   'sub_filters': [{'sub_filter_operator': 'AND',
                                                    'matches': [{'model': 'HarmonisedMetadataField',
                                                                 'property': 'name',
                                                                 'operator': 'eq',
                                                                 'value': 'Age',
                                                                 'datatype': 'VARCHAR'},
                                                                {'model': 'MetadataValue',
                                                                 'property': 'harmonised_numeric_value',
                                                                 'operator': 'in',
                                                                 'value': [20, 40],
                                                                 'datatype': 'numeric'},
                                                                {'model': 'HarmonisedMetadataField',
                                                                 'property': 'name',
                                                                 'operator': 'eq',
                                                                 'value': 'Sex',
                                                                 'datatype': 'VARCHAR'},
                                                                {'model': 'MetadataValue',
                                                                 'property': 'harmonised_text_value',
                                                                 'operator': 'eq',
                                                                 'value': 'Male',
                                                                 'datatype': 'text'}
                                                                ]
                                                    },
                                                   {'sub_filter_operator': 'AND',
                                                    'matches': [{'model': 'HarmonisedMetadataField',
                                                                 'property': 'name',
                                                                 'operator': 'eq',
                                                                 'value': 'Age',
                                                                 'datatype': 'VARCHAR'},
                                                                {'model': 'MetadataValue',
                                                                 'property': 'harmonised_numeric_value',
                                                                 'operator': 'between',
                                                                 'value': [60,80],
                                                                 'datatype': 'numeric'},
                                                                {'model': 'HarmonisedMetadataField',
                                                                 'property': 'name',
                                                                 'operator': 'eq',
                                                                 'value': 'Sex',
                                                                 'datatype': 'VARCHAR'},
                                                                {'model': 'MetadataValue',
                                                                'property': 'harmonised_text_value',
                                                                 'operator': 'eq',
                                                                 'value': 'Female',
                                                                 'datatype': 'text'}
                                                                ]
                                                    }]}]}
        expected_code_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(MetadataValue).join(MetadataField).filter(or_(and_(HarmonisedMetadataField.name=="Age",MetadataValue.harmonised_numeric_value.in_([20,40]),HarmonisedMetadataField.name=="Sex",MetadataValue.harmonised_text_value=="Male"),and_(HarmonisedMetadataField.name=="Age",MetadataValue.harmonised_numeric_value.between(60,80),HarmonisedMetadataField.name=="Sex",MetadataValue.harmonised_text_value=="Female"))).group_by(SampleAssay.id).order_by(SampleAssay.id)'
        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.generate_and_execute_query()
        print(query_factory.get_code_string())
        assert expected_code_string == query_factory.get_code_string()

    def test_build_query_dict_simple(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_query_dict = { 'model': 'SampleAssay',
                                'joins': ['Sample','Subject','Project'],
                                'filters': [{
                                    'filter_operator': 'AND',
                                    'sub_filters': [{
                                                    'sub_filter_operator': "AND",
                                                    'matches': [{
                                                                'model': 'Project',
                                                                'property':'name',
                                                                'operator': 'eq',
                                                                'value': 'PipelineTesting',
                                                    }]
                                    }]
                                }]
                             }


        query_factory = QueryFactory(db_env='TEST')
        filter = QueryFilter(filter_operator='AND')
        sub_filter = QuerySubFilter(sub_filter_operator='AND')
        sub_filter.add_match(QueryMatch(model='Project',property='name',operator='eq',value='PipelineTesting'))
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)
        query_factory.calculate_joins()
        assert expected_query_dict == query_factory.query_dict

    def test_build_query_dict_multi(self,create_min_database,
                                    create_pipeline_testing_project):

        query_factory = QueryFactory(db_env='TEST')
        filter = QueryFilter(filter_operator='AND')
        sub_filter = QuerySubFilter(sub_filter_operator='AND')
        sub_filter.add_match(QueryMatch(model='Project',property='name',operator='eq',value='PipelineTesting'))
        sub_filter.add_match(QueryMatch(model='HarmonisedMetadataField',property='name',operator='eq',value='Age'))
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)

        filter = QueryFilter(filter_operator='AND')
        sub_filter = QuerySubFilter(sub_filter_operator='OR')
        sub_filter.add_match(QueryMatch(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=["30","31","32"]))
        sub_filter.add_match(QueryMatch(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=["50","51","52"]))
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)
        query_factory.calculate_joins()

        expected_output = { 'model': 'SampleAssay',
                            'joins': ['Sample','Subject','Project','MetadataValue','MetadataField','HarmonisedMetadataField'],
                            'filters': [{
                                'filter_operator': 'AND',
                                'sub_filters': [{
                                                'sub_filter_operator': 'AND',
                                                'matches': [{
                                                            'model': 'Project',
                                                            'property':'name',
                                                            'operator': 'eq',
                                                            'value': 'PipelineTesting',
                                                            },{
                                                            'model': 'HarmonisedMetadataField',
                                                            'property':'name',
                                                            'operator': 'eq',
                                                            'value': 'Age',
                                                }]
                                }]
                            },{
                                'filter_operator': 'AND',
                                'sub_filters': [{
                                                'sub_filter_operator': 'OR',
                                                'matches': [{
                                                            'model': 'MetadataValue',
                                                            'property': 'harmonised_numeric_value',
                                                            "operator": 'in',
                                                            'value': ["30","31","32"]
                                                        },{
                                                            'model': 'MetadataValue',
                                                            'property': 'harmonised_numeric_value',
                                                            "operator": 'in',
                                                            'value': ["50","51","52"]
                                                }]
                                }]
                            }]
                        }

        
        assert expected_output == query_factory.query_dict

    def test_build_query_string_A1_eq(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).filter(Project.name=="PipelineTesting").group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                        'joins': ['Sample','Subject','Project'],
                        'filters': [{
                                        'filter_operator': 'AND',
                                        'sub_filters': [{
                                                        'sub_filter_operator': 'AND',
                                                        'matches': [{
                                                            'model': 'Project',
                                                            'property':'name',
                                                            'operator': 'eq',
                                                            'value': 'PipelineTesting',
                                                        }]
                                        }]
                         }]
                    }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_A2_not_eq(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).filter(Project.name!="PipelineTesting").group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins': ['Sample','Subject','Project'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'Project',
                                   'property':'name',
                                   'operator': 'not_eq',
                                   'value': 'PipelineTesting',
                               }]
                           }]
                       }]
                       }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_A3_gt_multi_filter_and(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(MetadataValue).join(MetadataField).filter(HarmonisedMetadataField.name=="Age").filter(MetadataValue.harmonised_numeric_value>30).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins': ['Sample','MetadataValue','MetadataField','HarmonisedMetadataField'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'HarmonisedMetadataField',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'Age',
                               }]
                           }],
                       },{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'MetadataValue',
                                   'property': 'harmonised_numeric_value',
                                   "operator": 'gt',
                                   'value': 30,
                               }]
                           }]
                       }]
                    }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_A4_gte_single_filter_and(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(MetadataValue).join(MetadataField).filter(and_(HarmonisedMetadataField.name=="Age",MetadataValue.harmonised_numeric_value>=30)).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins': ['Sample','MetadataValue','MetadataField','HarmonisedMetadataField'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'HarmonisedMetadataField',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'Age',
                               },{
                                   'model': 'MetadataValue',
                                   'property': 'harmonised_numeric_value',
                                   "operator": 'gte',
                                   'value': 30,
                               }]
                           }],
                       }]
                    }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_A5_lt_single_filter_or(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(MetadataValue).join(MetadataField).filter(or_(HarmonisedMetadataField.name=="Age",MetadataValue.harmonised_numeric_value<30)).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins': ['Sample','MetadataValue','MetadataField','HarmonisedMetadataField'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'OR',
                               'matches': [{
                                   'model': 'HarmonisedMetadataField',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'Age',
                               },{
                                   'model': 'MetadataValue',
                                   'property': 'harmonised_numeric_value',
                                   "operator": 'lt',
                                   'value': 30,
                               }]
                           }],
                       }]
                       }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_A6_lte_multi_filter(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(MetadataValue).join(MetadataField).filter(and_(Project.name=="PipelineTesting",and_(HarmonisedMetadataField.name=="Age",MetadataValue.harmonised_numeric_value<=30))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins': ['Sample','MetadataValue','MetadataField','HarmonisedMetadataField'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                                   'sub_filter_operator': 'AND',
                                   'matches': [{
                                       'model': 'Project',
                                       'property': 'name',
                                       "operator": 'eq',
                                       'value': 'PipelineTesting',
                                    }],
                                },{

                                    'sub_filter_operator': 'AND',
                                    'matches': [{
                                       'model': 'HarmonisedMetadataField',
                                       'property': 'name',
                                       "operator": 'eq',
                                       'value': 'Age',
                                    },{
                                       'model': 'MetadataValue',
                                       'property': 'harmonised_numeric_value',
                                       "operator": 'lte',
                                       'value': 30,
                                   }]
                            }],
                       }]
                    }


        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()


    def test_build_query_string_A7_between(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(MetadataValue).join(MetadataField).filter(and_(HarmonisedMetadataField.name=="Age",MetadataValue.harmonised_numeric_value.between(30,40))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = {  'model': 'SampleAssay',
                        'joins':['Sample','MetadataValue','MetadataField','HarmonisedMetadataField'],
                        'filters': [{
                            'filter_operator': 'AND',
                            'sub_filters': [{
                                'sub_filter_operator': 'AND',
                                'matches': [{
                                    'model': 'HarmonisedMetadataField',
                                    'property': 'name',
                                    "operator": 'eq',
                                    'value': 'Age',
                                },{
                                    'model': 'MetadataValue',
                                    'property': 'harmonised_numeric_value',
                                    "operator": 'between',
                                    'value': [30,40],
                                }]
                            }],
                        }]

                    }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_A8_not_between(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(MetadataValue).join(MetadataField).filter(and_(HarmonisedMetadataField.name=="Age",not_(MetadataValue.harmonised_numeric_value.between(30,40)))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = {  'model': 'SampleAssay',
                        'filters': [{
                            'filter_operator': 'AND',
                            'sub_filters': [{
                                'sub_filter_operator': 'AND',
                                'matches': [{
                                    'model': 'HarmonisedMetadataField',
                                    'property': 'name',
                                    "operator": 'eq',
                                    'value': 'Age',
                                },{
                                    'model': 'MetadataValue',
                                    'property': 'harmonised_numeric_value',
                                    "operator": 'not_between',
                                    'value': [30,40],
                                }]
                            }],
                        }]
                        }

        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()


    def test_build_query_string_A9_in(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(AnnotatedFeature,AnnotatedFeature.sample_assay_id==SampleAssay.id).join(FeatureMetadata,AnnotatedFeature.feature_metadata_id==FeatureMetadata.id).join(Annotation,FeatureMetadata.annotation_id==Annotation.id).join(HarmonisedAnnotation,Annotation.harmonised_annotation_id==HarmonisedAnnotation.id).join(AnnotationCompound,HarmonisedAnnotation.annotation_compound_id==AnnotationCompound.id).join(Compound,AnnotationCompound.compound_id==Compound.id).join(CompoundExternalDB).filter(or_(Project.name=="PipelineTesting",Project.name=="nPYc-toolbox-tutorials")).filter(and_(ExternalDB.name=="PubChem CID",CompoundExternalDB.database_ref.in_(["16217534","3082637"]))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins':['Sample','Subject','Project','AnnotatedFeature','FeatureMetadata','Annotation', \
                                'HarmonisedAnnotation','AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                       'filters': [{
                                'filter_operator': 'AND',
                                'sub_filters': [{
                                            'sub_filter_operator': 'OR',
                                            'matches': [{
                                                'model': 'Project',
                                                'property': 'name',
                                                "operator": 'eq',
                                                'value': 'PipelineTesting',
                                            },{
                                                'model': 'Project',
                                                'property': 'name',
                                                "operator": 'eq',
                                                'value': 'nPYc-toolbox-tutorials',
                                            }]
                                      }],
                                },{
                                   'filter_operator': 'AND',
                                   'sub_filters': [{
                                       'sub_filter_operator': 'AND',
                                       'matches': [{
                                           'model': 'ExternalDB',
                                           'property': 'name',
                                           "operator": 'eq',
                                           'value': 'PubChem CID',
                                       },{
                                           'model': 'CompoundExternalDB',
                                           'property': 'database_ref',
                                           "operator": 'in',
                                           'value': ["16217534","3082637"]
                                       }]
                                }],
                            }]
                        }



        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_B1_not_in(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(AnnotatedFeature,AnnotatedFeature.sample_assay_id==SampleAssay.id).join(FeatureMetadata,AnnotatedFeature.feature_metadata_id==FeatureMetadata.id).join(Annotation,FeatureMetadata.annotation_id==Annotation.id).join(HarmonisedAnnotation,Annotation.harmonised_annotation_id==HarmonisedAnnotation.id).join(AnnotationCompound,HarmonisedAnnotation.annotation_compound_id==AnnotationCompound.id).join(Compound,AnnotationCompound.compound_id==Compound.id).join(CompoundExternalDB).filter(or_(Project.name=="PipelineTesting",Project.name=="nPYc-toolbox-tutorials")).filter(and_(ExternalDB.name=="PubChem CID",not_(CompoundExternalDB.database_ref.in_(["16217534","3082637"])))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins':['Sample','Subject','Project','AnnotatedFeature','FeatureMetadata','Annotation', \
                                'HarmonisedAnnotation','AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'OR',
                               'matches': [{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'PipelineTesting',
                               },{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'nPYc-toolbox-tutorials',
                               }]
                           }],
                       },{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'ExternalDB',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'PubChem CID',
                               },{
                                   'model': 'CompoundExternalDB',
                                   'property': 'database_ref',
                                   "operator": 'not_in',
                                   'value': ["16217534","3082637"]
                               }]
                           }],
                       }]
                       }



        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_B2_like_and_ilike(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(AnnotatedFeature,AnnotatedFeature.sample_assay_id==SampleAssay.id).join(FeatureMetadata,AnnotatedFeature.feature_metadata_id==FeatureMetadata.id).join(Annotation,FeatureMetadata.annotation_id==Annotation.id).join(HarmonisedAnnotation,Annotation.harmonised_annotation_id==HarmonisedAnnotation.id).join(AnnotationCompound,HarmonisedAnnotation.annotation_compound_id==AnnotationCompound.id).join(Compound,AnnotationCompound.compound_id==Compound.id).join(CompoundExternalDB).filter(or_(Project.name=="PipelineTesting",Project.name.like("nPYc-toolbox-tutorials"))).filter(and_(ExternalDB.name.ilike("pubchem cid"),not_(CompoundExternalDB.database_ref.in_(["16217534","3082637"])))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins':['Sample','Subject','Project','SampleAssay','AnnotatedFeature','FeatureMetadata','Annotation', \
                                'HarmonisedAnnotation','AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'OR',
                               'matches': [{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'PipelineTesting',
                               },{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'like',
                                   'value': 'nPYc-toolbox-tutorials',
                               }]
                           }],
                       },{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'ExternalDB',
                                   'property': 'name',
                                   "operator": 'ilike',
                                   'value': 'pubchem cid',
                               },{
                                   'model': 'CompoundExternalDB',
                                   'property': 'database_ref',
                                   "operator": 'not_in',
                                   'value': ["16217534","3082637"]
                               }]
                           }],
                       }]
                       }


        query_factory = QueryFactory(query_dict=query_dict,db_env='TEST')
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_B3_not_like_and_not_ilike(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(AnnotatedFeature,AnnotatedFeature.sample_assay_id==SampleAssay.id).join(FeatureMetadata,AnnotatedFeature.feature_metadata_id==FeatureMetadata.id).join(Annotation,FeatureMetadata.annotation_id==Annotation.id).join(HarmonisedAnnotation,Annotation.harmonised_annotation_id==HarmonisedAnnotation.id).join(AnnotationCompound,HarmonisedAnnotation.annotation_compound_id==AnnotationCompound.id).join(Compound,AnnotationCompound.compound_id==Compound.id).join(CompoundExternalDB).filter(or_(Project.name=="PipelineTesting",not_(Project.name.like("nPYc-toolbox-tutorials")))).filter(and_(not_(ExternalDB.name.ilike("pubchem cid")),not_(CompoundExternalDB.database_ref.in_(["16217534","3082637"])))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins':['Sample','Subject','Project','SampleAssay','AnnotatedFeature','FeatureMetadata','Annotation',\
                                'HarmonisedAnnotation','AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'OR',
                               'matches': [{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'PipelineTesting',
                               },{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'not_like',
                                   'value': 'nPYc-toolbox-tutorials',
                               }]
                           }],
                       },{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'ExternalDB',
                                   'property': 'name',
                                   "operator": 'not_ilike',
                                   'value': 'pubchem cid',
                               },{
                                   'model': 'CompoundExternalDB',
                                   'property': 'database_ref',
                                   "operator": 'not_in',
                                   'value': ["16217534","3082637"]
                               }]
                           }],
                       }]
                       }


        query_factory = QueryFactory(query_dict=query_dict)
        query_factory.build_query_string()

        assert str(expected_string) == str(query_factory.get_code_string())


    def test_build_query_string_B5_and_or(self,create_min_database,
                                     create_pipeline_testing_project):

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(AnnotatedFeature,AnnotatedFeature.sample_assay_id==SampleAssay.id).join(FeatureMetadata,AnnotatedFeature.feature_metadata_id==FeatureMetadata.id).join(Annotation,FeatureMetadata.annotation_id==Annotation.id).join(HarmonisedAnnotation,Annotation.harmonised_annotation_id==HarmonisedAnnotation.id).join(AnnotationCompound,HarmonisedAnnotation.annotation_compound_id==AnnotationCompound.id).join(Compound,AnnotationCompound.compound_id==Compound.id).join(CompoundExternalDB).filter(or_(Project.name=="PipelineTesting",not_(Project.name.like("nPYc-toolbox-tutorials")))).filter(and_(not_(ExternalDB.name.ilike("pubchem cid")),not_(CompoundExternalDB.database_ref.in_(["16217534","3082637"])))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins':['Sample','Subject','Project','SampleAssay','AnnotatedFeature','FeatureMetadata','Annotation',\
                                'HarmonisedAnnotation','AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'OR',
                               'matches': [{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'PipelineTesting',
                               },{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'not_like',
                                   'value': 'nPYc-toolbox-tutorials',
                               }]
                           }],
                       },{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'ExternalDB',
                                   'property': 'name',
                                   "operator": 'not_ilike',
                                   'value': 'pubchem cid',
                               },{
                                   'model': 'CompoundExternalDB',
                                   'property': 'database_ref',
                                   "operator": 'not_in',
                                   'value': ["16217534","3082637"]
                               }]
                           }],
                       }]
                       }


        query_factory = QueryFactory(query_dict=query_dict)
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_build_query_string_B6_or_and(self,create_min_database,
                                     create_pipeline_testing_project):

        #From PipelineTesting
        #Where (annotation.lod > x and compound.name in (list))
        #Or (annotation.lod > y and compound.name in (list)

        #.filter(Project.name=='PipelineTesting',Project.name=="AIRWAVE")
        #.filter(or_(and_(Annotation.lod > 5,Compound.name.in("Glucose","Glutamine"))),
        #           (and_(Annotation.lod > 8,Compound.name.in("Tryptophan")))

        expected_string = 'db_session.query(SampleAssay).join(Sample,SampleAssay.sample_id==Sample.id).join(Subject,Sample.subject_id==Subject.id).join(Project,Subject.project_id==Project.id).join(AnnotatedFeature,AnnotatedFeature.sample_assay_id==SampleAssay.id).join(FeatureMetadata,AnnotatedFeature.feature_metadata_id==FeatureMetadata.id).join(Annotation,FeatureMetadata.annotation_id==Annotation.id).join(HarmonisedAnnotation,Annotation.harmonised_annotation_id==HarmonisedAnnotation.id).join(AnnotationCompound,HarmonisedAnnotation.annotation_compound_id==AnnotationCompound.id).filter(Project.name=="PipelineTesting").filter(or_(and_(FeatureMetadata.lod>0.5,Compound.name.in_(["Glucose","Glutamine"])),and_(FeatureMetadata.lod>0.8,Compound.name.in_(["Tryptophan"])))).group_by(SampleAssay.id).order_by(SampleAssay.id)'

        query_dict = { 'model': 'SampleAssay',
                       'joins': [],
                       'filters': [{
                           'filter_operator': 'AND',
                           'preset': None,
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                   'model': 'Project',
                                   'property': 'name',
                                   "operator": 'eq',
                                   'value': 'PipelineTesting',
                               }]
                           }],
                       },{
                           'filter_operator': 'OR',
                           'preset': None,
                           'sub_filters': [{
                                   'sub_filter_operator': 'AND',
                                   'matches': [{
                                       'model': 'FeatureMetadata',
                                       'property': 'lod',
                                       "operator": 'gt',
                                       'value': 0.5,
                                    },{
                                       'model': 'Compound',
                                       'property': 'name',
                                       "operator": 'in',
                                       'value': ["Glucose","Glutamine"]
                                    }]
                                },{
                                   'sub_filter_operator': 'AND',
                                   'matches': [{
                                       'model': 'FeatureMetadata',
                                       'property': 'lod',
                                       "operator": 'gt',
                                       'value': 0.8,
                                   },{
                                       'model': 'Compound',
                                       'property': 'name',
                                       "operator": 'in',
                                       'value': ["Tryptophan"]
                                   }]
                               }],
                       }]
                    }


        query_factory = QueryFactory(query_dict=query_dict)
        query_factory.build_query_string()

        assert expected_string == query_factory.get_code_string()

    def test_execute_query(self,create_min_database,
                                     create_pipeline_testing_project):

        query_dict = { 'model': 'SampleAssay',
                       'joins':['Sample','Subject','Project','MetadataValue','MetadataField','HarmonisedMetadataField'],
                       'filters': [{
                           'filter_operator': 'AND',
                           'sub_filters': [{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                           'model': 'Project',
                                           'property': 'name',
                                           "operator": 'eq',
                                           'value': 'PipelineTesting',

                                        }],
                            },{
                               'sub_filter_operator': 'AND',
                               'matches': [{
                                           'model': 'HarmonisedMetadataField',
                                           'property': 'name',
                                           "operator": 'eq',
                                           'value': 'Age',
                                            },{
                                           'model': 'MetadataValue',
                                           'property': 'harmonised_numeric_value',
                                           "operator": 'in',
                                           'value': ["30","35","40"],
                                       }]
                            }],
                       }]
                     }


        #query_factory = SampleFactory(query_dict=query_dict,db_session=self.db_session)
        query_factory = QueryFactory(query_dict=query_dict)
        rows = query_factory.get_query_rows()

        assert isinstance(rows,list) == True

    def test_build_save_retrieve_and_execute_query(self,create_min_database,
                                                   delete_saved_queries,
                                                    create_pipeline_testing_project):

        query_factory = QueryFactory(query_name='test_build_save_retrieve_and_execute_query',query_description='test description',db_env='TEST')
        filter = QueryFilter('AND')
        sub_filter = QuerySubFilter('AND')
        sub_filter.add_match(model='Project',property='name',operator='eq',value='PipelineTesting')
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)
        filter = QueryFilter('AND')
        sub_filter = QuerySubFilter('AND')
        sub_filter.add_match(model='HarmonisedMetadataField',property='name',operator='eq',value='Age')
        sub_filter.add_match(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=["30","35","40"])
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)
        query_factory.save_query()

        query_factory_retrieved = QueryFactory(saved_query=query_factory.saved_query,db_env='TEST')

        rows = query_factory_retrieved.get_query_rows()

        assert isinstance(rows,list) == True

    def test_build_query_constructor(self,create_min_database,
                                     create_pipeline_testing_project):
        '''
            Tests the SampleFactory QueryFilters

            Builds a query looking for subjects ages 30,35, & 40 from the PipelineTesting project

            Starting with a 'raw' construction that allows for greatest flexibility, and then subsequent contracted versions that use constructor shortcuts to the underlying code.

            The simplified versions have less flexibility but are suitable for simple 'AND' queries, and can be used for top-level 'OR'.

        :return:
        '''

        query_factory = QueryFactory(query_name='test query',query_description='test description',db_env='TEST')
        filter = QueryFilter('AND')
        sub_filter = QuerySubFilter('AND')
        sub_filter.add_match(model='Project',property='name',operator='eq',value='PipelineTesting')
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)
        filter = QueryFilter('AND')
        sub_filter = QuerySubFilter('AND')
        sub_filter.add_match(model='HarmonisedMetadataField',property='name',operator='eq',value='Age')
        sub_filter.add_match(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=["30","35","40"])
        filter.add_sub_filter(sub_filter=sub_filter)
        query_factory.add_filter(query_filter=filter)
        query_factory.generate_query()
        query_dict_one = query_factory.query_dict


        query_factory = QueryFactory(query_name='test query',query_description='test description',db_env='TEST')
        filter = QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting')
        query_factory.add_filter(query_filter=filter)
        filter = QueryFilter(model='HarmonisedMetadataField',property='name',operator='eq',value='Age')
        filter.add_match(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=["30","35","40"])
        query_factory.add_filter(query_filter=filter)
        query_factory.generate_query()
        assert query_dict_one == query_factory.query_dict


        query_factory = QueryFactory(query_name='test query',query_description='test description',db_env='TEST')
        query_factory.add_filter(model='Project',property='name',operator='eq',value='PipelineTesting')
        filter = QueryFilter(model='HarmonisedMetadataField',property='name',operator='eq',value='Age')
        filter.add_match(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=["30","35","40"])
        query_factory.add_filter(query_filter=filter)
        query_factory.generate_query()
        assert query_dict_one == query_factory.query_dict


        # The order matters in this unit test

        query_factory = QueryFactory(query_name='test query',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=MetadataFilter('Age','in',value=["30","35","40"]))
        query_factory.generate_query()

        assert query_dict_one == query_factory.query_dict


    def test_join_calculator_A1_simple(self,create_min_database,
                                     create_pipeline_testing_project):

        input_query_dict = { 'model': 'SampleAssay',
                               'joins': [],
                               'filters': [{
                                   'filter_operator': 'AND',
                                   'sub_filters': [{
                                       'sub_filter_operator': 'AND',
                                       'matches': [{
                                           'model': 'Project',
                                           'property': 'name',
                                           "operator": 'eq',
                                           'value': 'PipelineTesting',
                                       }],
                                   }]
                                }]
                               }

        query_factory = QueryFactory(query_dict=input_query_dict)
        query_factory.calculate_joins()

        expected_output = { 'model': 'SampleAssay',
                            'joins': ['Sample','Subject','Project'],
                            'filters': [{
                                'filter_operator': 'AND',
                                'sub_filters': [{
                                    'sub_filter_operator': 'AND',
                                    'matches': [{
                                        'model': 'Project',
                                        'property': 'name',
                                        "operator": 'eq',
                                        'value': 'PipelineTesting',

                                    }],
                                }]
                            }]
                            }

        assert expected_output == query_factory.query_dict

    def test_join_calculator_A2_multi(self,create_min_database,
                                     create_pipeline_testing_project):

        input_query_dict = { 'model': 'SampleAssay',
                             'joins': [],
                             'filters': [{
                                    'filter_operator': 'AND',
                                     'sub_filters': [{
                                         'sub_filter_operator': 'AND',
                                         'matches': [{
                                             'model': 'Project',
                                             'property': 'name',
                                             "operator": 'eq',
                                             'value': 'PipelineTesting',

                                              }],
                                        }]
                                    },{
                                    'filter_operator': 'AND',
                                     'sub_filters': [{
                                         'sub_filter_operator': 'AND',
                                         'matches': [{
                                             'model': 'HarmonisedMetadataField',
                                             'property': 'name',
                                             "operator": 'eq',
                                             'value': 'Age',
                                         },{
                                             'model': 'MetadataValue',
                                             'property': 'harmonised_numeric_value',
                                             "operator": 'not_in',
                                             'value': ["30","31","32"]
                                         }],
                                     }]
                                }]
                             }

        query_factory = QueryFactory(query_dict=input_query_dict)
        query_factory.calculate_joins()

        expected_output = { 'model': 'SampleAssay',
                             'joins': ['Sample','Subject','Project','MetadataValue','MetadataField','HarmonisedMetadataField'],
                            'filters': [{
                                'filter_operator': 'AND',
                                'sub_filters': [{
                                    'sub_filter_operator': 'AND',
                                    'matches': [{
                                        'model': 'Project',
                                        'property': 'name',
                                        "operator": 'eq',
                                        'value': 'PipelineTesting',

                                    }],
                                }]
                            },{
                                'filter_operator': 'AND',
                                'sub_filters': [{
                                    'sub_filter_operator': 'AND',
                                    'matches': [{
                                        'model': 'HarmonisedMetadataField',
                                        'property': 'name',
                                        "operator": 'eq',
                                        'value': 'Age',
                                    },{
                                        'model': 'MetadataValue',
                                        'property': 'harmonised_numeric_value',
                                        "operator": 'not_in',
                                        'value': ["30","31","32"]
                                    }],
                                }]
                            }]
                            }

        assert expected_output == query_factory.query_dict

    def test_aab_build_devset_lpos_dataframe(self,create_min_database,
                                                 create_lab,
                                                create_pipeline_testing_project,
                                                 create_ms_assays,
                                                 create_annotation_methods,
                                                import_devset_sample_manifest,
                                                import_devset_lpos_peakpanther_annotations,
                                             dummy_harmonise_annotations):

        query_factory = QueryFactory(output_model='AnnotatedFeature',query_name='test query lpos',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod', property='name', operator='eq', value='PPR'))
        query_factory.save_query()
        df = query_factory.load_dataframe(output_model='AnnotatedFeature',reload_cache=True)
        assert df.empty is False


    def test_ab_build_devset_biquant_dataframe(self,create_min_database,
                                                create_lab,
                                                create_pipeline_testing_project,
                                                create_nmr_assays,
                                                create_annotation_methods,
                                                import_devset_sample_manifest,
                                                import_devset_ivdr_biquant_annotations,
                                               dummy_harmonise_annotations):

        query_factory = QueryFactory(output_model='AnnotatedFeature',query_name='test query biquant',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='Bi-Quant-P'))
        query_factory.save_query()
        df = query_factory.execute_and_build_dataframe(output_model='AnnotatedFeature',harmonise_annotations=True)
        assert df.empty is False

    def test_aaac_build_devset_bilisa_dataframe(self,create_min_database,
                                                create_lab,
                                                create_pipeline_testing_project,
                                                create_nmr_assays,
                                                create_annotation_methods,
                                                import_devset_sample_manifest,
                                                import_devset_ivdr_bilisa_annotations,
                                                dummy_harmonise_annotations):

        query_factory = QueryFactory(output_model='AnnotatedFeature',query_name='test query bilisa',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='Bi-LISA'))
        query_factory.save_query()        
        df = query_factory.execute_and_build_dataframe(output_model='AnnotatedFeature',harmonise_annotations=True)
        assert df.empty is False

    def test_aaad_build_devset_targetlynx_dataframe(self,create_min_database,
                                                create_lab,
                                                create_pipeline_testing_project,
                                                create_ms_assays,
                                                create_annotation_methods,
                                                import_devset_sample_manifest,
                                                import_devset_bile_acid_targeted_annotations,
                                                dummy_harmonise_annotations):

        query_factory = QueryFactory(output_model='AnnotatedFeature',query_name='test query',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='TargetLynx'))
        #query_factory.add_filter(
        #    query_filter=QueryFilter(model='Assay', property='name', operator='eq', value='LC-QqQ Amino Acids'))
        #df = query_factory.execute_and_build_dataframe(csv_path=config['DATA']['test_data'] + 'devset_ba_targeted_query_factory_dataframe.csv')
        df = query_factory.execute_and_build_dataframe(output_model='AnnotatedFeature')
        assert df.empty != True



    def test_summary_stats(self,create_min_database,
                                delete_test_cache,
                                create_pipeline_testing_project,
                               create_lab,
                               create_nmr_assays,
                               create_ms_assays,
                               create_annotation_methods,
                               import_devset_sample_manifest,
                               import_devset_lpos_peakpanther_annotations,
                               import_devset_bile_acid_targeted_annotations,
                               import_devset_ivdr_biquant_annotations,
                               import_devset_ivdr_bilisa_annotations,
                           dummy_harmonise_annotations
                           ):

        input_query_dict = { 'model': 'SampleAssay',
                             'joins': [],
                             'filters': [{
                                 'filter_operator': 'AND',
                                 'sub_filters': [{
                                     'sub_filter_operator': 'AND',
                                     'matches': [{
                                         'model': 'Project',
                                         'property': 'name',
                                         "operator": 'eq',
                                         'value': 'PipelineTesting',

                                     }],
                                 }]
                             }]
                            }

        query_factory = QueryFactory(query_dict=input_query_dict,db_env='TEST')
        query_factory.load_summary_statistics()

        #expected_stats = {
        #                    'assays': ['NOESY', 'LPOS', 'LC-QqQ Bile Acids'],
        #                    'number_of_compounds': 297,
        #                    'number_of_annotations': 22925,
        #                    'number_of_sample_assays': 232,
        #                    'number_samples': 81,
        #                    'number_subjects': 9,
        #                    'projects': ['PipelineTesting']
        #                }

        expected_stats = {'assay_counts': {'NOESY': 94, 'LPOS': 153, 'LC-QqQ Bile Acids': 68},
                          'number_of_annotations': 383,
                          'number_of_annotated_features': 31557,
                          'number_of_sample_assays': 315,
                          'number_samples': 169,
                          'number_subjects': 9,
                          'project_counts': {'PipelineTesting': 315},
                          'sample_matrix_counts': {'plasma': 315},
                          'sample_type_counts': {SampleType.ProceduralBlank: 3, SampleType.StudySample: 223, SampleType.StudyPool: 75, SampleType.ExternalReference: 14} }

        expected_stats = {'assay_counts': {'LC-QqQ Bile Acids': 70, 'LPOS': 64, 'NOESY': 115},
                         'metadata_counts_harmonised_datetime': {},
                         'metadata_counts_harmonised_datetime_by_project': {},
                         'metadata_counts_harmonised_numeric': {},
                         'metadata_counts_harmonised_numeric_by_project': {},
                         'metadata_counts_harmonised_text': {},
                         'metadata_counts_harmonised_text_by_project': {},
                         'metadata_counts_raw': {'Age': {'10': 29,
                                                         '20': 29,
                                                         '30': 29,
                                                         '40': 45,
                                                         '50': 47,
                                                         '70': 22},
                                                 'Class': {'DevSet1': 29,
                                                           'DevSet1v2': 45,
                                                           'DevSet1v3': 47,
                                                           'DevSet2': 29,
                                                           'DevSet2v3': 22,
                                                           'DevSet3': 29},
                                                 'DOB': {'1945-01-01 00:00:00': 22,
                                                         '1965-01-01 00:00:00': 47,
                                                         '1975-01-01 00:00:00': 45,
                                                         '1985-01-01 00:00:00': 29,
                                                         '1995-01-01 00:00:00': 29,
                                                         '2005-01-01 00:00:00': 29},
                                                 'Gender': {'F': 96, 'M': 105}},
                         'min_annotated_feature_count': 1249,
                         'number_of_annotated_features': 25552,
                         'number_of_sample_assays': 249,
                         'number_samples': 126,
                         'number_subjects': 8,
                         'project_counts': {'PipelineTesting': 249},
                         'sample_matrix_counts': {'plasma': 249},
                         'sample_type_counts': {'External Reference': 10,
                                                'Study Pool': 38,
                                                'Study Sample': 201}}
        assert expected_stats == query_factory.summary

    def test_limit_offset(self,create_min_database,
                                create_pipeline_testing_project):

        query_factory = QueryFactory(query_name='test query',query_description='test description',db_env='TEST')
        query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
        results = query_factory.generate_and_execute_query(limit=25,offset=0)
        assert results != None


    def test_multiple_harmonised_metadata_fields(self):

        db_session = db.get_db_session()

        subquery = db_session.query(SampleAssay.id).join(Sample, Subject, Project, Assay, AnnotatedFeature,
                                                         FeatureMetadata, Annotation, HarmonisedAnnotation,
                                                         AnnotationMethod, MetadataValue, MetadataField,
                                                         HarmonisedMetadataField).filter(
            Project.name == "FINGER").filter(Assay.name == "LNEG").filter(AnnotationMethod.name.in_(["PPR"])).filter(
            Sample.sample_matrix.in_(["plasma", "serum"])).filter(
            and_(HarmonisedMetadataField.name == "Timepoint", MetadataValue.harmonised_numeric_value == 1)).group_by(SampleAssay).subquery()

        count = db_session.query(SampleAssay).join(Sample, MetadataValue, MetadataField, HarmonisedMetadataField)\
            .filter(SampleAssay.id.in_(subquery)).count()

       #count = db_session.query(SampleAssay).join(Sample, MetadataValue, MetadataField,
       #                                            HarmonisedMetadataField).filter(
       #     and_(HarmonisedMetadataField.name == "Sex", MetadataValue.harmonised_text_value == 'Male')).filter(
       #     SampleAssay.id.in_(subquery)).order_by(SampleAssay.id).count()

        pass
    
#    def test_faster_build(self):
#
#        '''-- get the sample_ids and the harmonised_annotation_ids
#
#            loop over the sample ids, for each run the following
#
#            select *
#            from annotated_feature af
#            inner join feature_metadata f on af.feature_metadata_id = f.id
#            inner join annotation a on a.id = f.annotation_id
#            inner join harmonised_annotation ha on ha.id = a.harmonised_annotation_id
#            where af.sample_assay_id = 157
#            and harmonised_annotation_id in ['']
#            order by harmonised_annotation_id;
#
#            '''
#
#        db_session = db.get_db_session()
#        import datetime
#        start = datetime.datetime.now()
#        print(start)
#
#        query_factory = QueryFactory(saved_query_id=1)
#        query_factory.generate_query()
#        sample_assays = query_factory.execute_query()
#        query_factory.generate_query(output_model='HarmonisedAnnotation')
#        harmonised_annotations = query_factory.execute_query()
#        harmonised_annotation_ids = [harmonised_annotation.id for harmonised_annotation in harmonised_annotations]
#        sample_assay_ids = []
#        combined_temp = pd.DataFrame()
#        for sample_assay in sample_assays:
#            query = db_session.query(AnnotatedFeature.intensity,AnnotatedFeature.sr_corrected_intensity,HarmonisedAnnotation.id).join(FeatureMetadata,Annotation,HarmonisedAnnotation)\
#            .filter(AnnotatedFeature.sample_assay_id==sample_assay.id)\
#            .filter(HarmonisedAnnotation.id.in_(harmonised_annotation_ids))
#            intensity_row_table = pd.read_sql(query.statement, query.session.bind)
#
#            #combined_temp.loc[sample_assay.sample.id,(harmonised_annotation_ids)] = intensity_row
#            sample_assay_ids.append(sample_assay.id)
#        print(datetime.datetime.now())
#        harmonised_fields = db_session.query(HarmonisedMetadataField).all()
#        for harmonised_field in harmonised_fields:
#            query = db_session.query(MetadataValue.sample_id,MetadataValue.harmonised_text_value).join(Sample,MetadataField,SampleAssay) \
#                .filter(SampleAssay.id.in_(sample_assay_ids)) \
#                .filter(MetadataField.harmonised_metadata_field_id == harmonised_field.id)\
#                .order_by(MetadataValue.sample_id)
#            sample_metadata_column_table = pd.read_sql(query.statement, query.session.bind)
#
#        metadata_fields = db_session.query(MetadataField).all()
#        for metadata_field in metadata_fields:
#            query = db_session.query(MetadataValue.sample_id, MetadataValue.raw_value).join(Sample,
#                                                                                            MetadataField,
#                                                                                            SampleAssay) \
#                .filter(SampleAssay.id.in_(sample_assay_ids)) \
#                .filter(MetadataField.id == metadata_field.id) \
#                .order_by(MetadataValue.sample_id)
#            sample_metadata_column_table = pd.read_sql(query.statement, query.session.bind)
#
#        query = db_session.query(Sample).join(SampleAssay).filter(SampleAssay.id.in_(sample_assay_ids))
#        sample_data = pd.read_sql(query.statement, query.session.bind)
#
#        # construct the dataframe using the sample_metadata_columns (sample_id as key)
#        # construct the dataframe using
#
#        print("SampleAssay by SampleAssay")
#        print(datetime.datetime.now() - start)
#
#        start = datetime.datetime.now()
#
#        query_factory = QueryFactory(saved_query_id=133)
#        query_factory.generate_query()
#        sample_assays = query_factory.execute_query()
#        query_factory.generate_query(output_model='HarmonisedAnnotation')
#        harmonised_annotations = query_factory.execute_query()
#        harmonised_annotation_ids = []
#       # harmonised_annotation_ids = [harmonised_annotation.id for harmonised_annotation in harmonised_annotations]
#        sample_assay_ids = [sample_assay.id for sample_assay in sample_assays]
#        combined_temp = pd.DataFrame()
#        for harmonised_annotation in harmonised_annotations:
#            query = db_session.query(AnnotatedFeature.intensity, AnnotatedFeature.sr_corrected_intensity,
#                                     HarmonisedAnnotation.id).join(FeatureMetadata, Annotation, HarmonisedAnnotation) \
#                .filter(AnnotatedFeature.sample_assay_id.in_(sample_assay_ids)) \
#                .filter(HarmonisedAnnotation.id == harmonised_annotation.id)
#            intensity_row_table = pd.read_sql(query.statement, query.session.bind)
#
#            # combined_temp.loc[sample_assay.sample.id,(harmonised_annotation_ids)] = intensity_row
#            harmonised_annotation_ids.append(harmonised_annotation.id)
#
#        harmonised_fields = db_session.query(HarmonisedMetadataField).all()
#        for harmonised_field in harmonised_fields:
#            query = db_session.query(MetadataValue.sample_id, MetadataValue.harmonised_text_value).join(Sample,
#                                                                                                        MetadataField,
#                                                                                                        SampleAssay) \
#                .filter(SampleAssay.id.in_(sample_assay_ids)) \
#                .filter(MetadataField.harmonised_metadata_field_id == harmonised_field.id) \
#                .order_by(MetadataValue.sample_id)
#            sample_metadata_column_table = pd.read_sql(query.statement, query.session.bind)
#
#        metadata_fields = db_session.query(MetadataField).all()
#        for metadata_field in metadata_fields:
#            query = db_session.query(MetadataValue.sample_id, MetadataValue.raw_value).join(Sample,
#                                                                                                        MetadataField,
#                                                                                                        SampleAssay) \
#                .filter(SampleAssay.id.in_(sample_assay_ids)) \
#                .filter(MetadataField.id == metadata_field.id) \
#                .order_by(MetadataValue.sample_id)
#            sample_metadata_column_table = pd.read_sql(query.statement, query.session.bind)
#
#        query = db_session.query(Sample).join(SampleAssay).filter(SampleAssay.id.in_(sample_assay_ids))
#        sample_data = pd.read_sql(query.statement,query.session.bind)
#
#        # construct the dataframe using the sample_metadata_columns (sample_id as key)
#        # construct the dataframe using
#
#        print("HarmonisedAnnotation by HarmonisedAnnotation")
#        print( datetime.datetime.now() - start)
#
#        start = datetime.datetime.now()
#
#        query_factory = QueryFactory(saved_query_id=133)
#        query_factory.generate_query(output_model='AnnotatedFeature')
#        annotated_features = query_factory.execute_query()
#        query_factory.build_annotated_feature_dataframe(correction_type='SR')
#
#        print("AnnotatedFeature by AnnotatedFeature")
#        print(datetime.datetime.now() - start)
#
#