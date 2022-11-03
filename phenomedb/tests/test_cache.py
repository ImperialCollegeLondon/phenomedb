import cache
import pytest
from pathlib import Path
import deepdiff
import sys, os
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config
from phenomedb.cache import *
from phenomedb.query_factory import *
import pandas as pd
import numpy as np
import redis
import pyarrow as pa

class TestCache:
    """TestCache class. Tests the output of the cache task classes with test configurations
    """

    cache_directory = config['DATA']['app_data'] + '/cache/'
    redis_cache = redis.Redis(host=config['REDIS']['host'],port=config['REDIS']['port'],password=config['REDIS']['password'])

    def test_cache(self,delete_test_cache):
        """Tests the Cache initialises correctly 
        """        

        #1. initialise cache
        cache = Cache()

        # Check the cache directory exists
        assert os.path.exists(self.cache_directory)

        # Check if the file_cache_list is in redis
        assert self.redis_cache.exists(cache.file_cache_key)

        # Check the file_cache_list has loaded correctly
        assert cache.file_cache_list is not None

    def test_set_dataframe_cache(self,delete_test_cache):
        """Test setting and getting a dataframe in the cache
        """

        df_dict = {'col1':['col1_row1','col1_row2'],'col2':['col2_row1','col2_row2']}

        df = pd.DataFrame.from_dict(df_dict)

        cache = Cache()

        test_key = 'test_dataframe'
        cache.set(test_key,df)

        # Check the file cache has been created
        assert os.path.exists(str(Path(self.cache_directory + cache.key_filename(test_key))))

        # Check if the redis cache exists
        assert self.redis_cache.exists(test_key)

        # Check that the set and got dataframe->to_dict() is the same as the original
        assert df.equals(cache.get(test_key))

        # Check the file cache list has been updated in the Cache object and redis
        assert self.redis_cache.exists(cache.file_cache_key)
        assert test_key in cache.file_cache_list

        context = pa.default_serialization_context()
        file_cache_list = context.deserialize(self.redis_cache.get(cache.file_cache_key))
        assert test_key in file_cache_list

        # test cache.exists method
        assert cache.exists(test_key)

        # delete the key from redis and try again
        self.redis_cache.delete(test_key)
        assert df.equals(cache.get(test_key))

        assert cache.get(test_key) is not None

        # delete the key from both redis and the file cache
        cache.delete(test_key)

        # Todo: test the file and redis cache are deleted
        file_cache_list = context.deserialize(self.redis_cache.get(cache.file_cache_key))
        assert test_key not in file_cache_list

        assert not os.path.exists(str(Path(self.cache_directory + cache.key_filename(test_key))))

        assert not self.redis_cache.exists(test_key)

    def test_dictionary(self,delete_test_cache):

        dict = {'col1':['col1_row1','col1_row2'],'col2':['col2_row1','col2_row2']}

        cache = Cache()
        cache.delete_test_keys()

        test_key = 'test_dict'
        cache.set(test_key,dict)

        # Check the file cache has been created
        assert os.path.exists(str(Path(self.cache_directory + cache.key_filename(test_key))))

        # Check if the redis cache exists
        assert self.redis_cache.exists(test_key)

        # Check that the set and got dataframe->to_dict() is the same as the original
        assert deepdiff.DeepDiff(dict,cache.get(test_key)) == {}

        # Check what happens when the redis cache is deleted and its loaded from file

        cache.set(test_key,dict)
        self.redis_cache.delete(test_key)
        assert deepdiff.DeepDiff(dict,cache.get(test_key)) == {}

        assert cache.get(test_key) is not None

    def test_matrix(self,delete_test_cache):

        list = [['col1_row1','col1_row2'],['col2_row1','col2_row2']]
        matrix = np.matrix(list)
        cache = Cache()
        cache.delete_test_keys()

        test_key = 'test_matrix'
        cache.set(test_key,matrix)

        # Check the file cache has been created
        assert os.path.exists(str(Path(self.cache_directory + cache.key_filename(test_key))))

        # Check if the redis cache exists
        assert self.redis_cache.exists(test_key)

        # Check that the set and got dataframe->to_dict() is the same as the original
        assert pd.DataFrame(matrix).equals(pd.DataFrame(cache.get(test_key)))

        # Check what happens when the redis cache is deleted and its loaded from file

        cache.set(test_key,matrix)
        self.redis_cache.delete(test_key)
        assert pd.DataFrame(matrix).equals(pd.DataFrame(cache.get(test_key)))
        cache.delete(test_key)

    def test_setting_dataframe_without_dataframe_in_key(self,delete_test_cache):

        df_dict = {'col1':['col1_row1','col1_row2'],'col2':['col2_row1','col2_row2']}

        df = pd.DataFrame.from_dict(df_dict)

        cache = Cache()

        test_key = 'test_key'
        try:
            cache.set(test_key,df)
            assert False
        except Exception as err:
            assert str(err) == "If caching a pandas DataFrame, then 'dataframe' or 'DataFrame' must be part of the key: %s \n columns: %s" % (test_key,df.columns)


    def test_generate_query_factory_cache(self,delete_test_cache,create_min_database,create_ms_assays,create_annotation_methods):

        from .conftest import import_devset_project_lpos_peakpanther_annotations

        import_devset_project_lpos_peakpanther_annotations("PipelineTesting",validate=False)

        query_factory = QueryFactory(query_name='test_query_lpos', query_description='test description', db_env='TEST')
        query_factory.add_filter(
            query_filter=QueryFilter(model='Project', property='name', operator='eq', value='PipelineTesting'))
        query_factory.add_filter(query_filter=QueryFilter(model='Assay', property='name', operator='eq', value='LPOS'))
        saved_query = query_factory.save_query()

        task = CreateSavedQueryDataframeCache(saved_query_id=saved_query.id,db_env='TEST')
        output = task.run()
        dataframe_cache_key = saved_query.get_cache_dataframe_key(
            query_factory.get_dataframe_key(type='combined',model='AnnotatedFeature',db_env='TEST',harmonise_annotations=True))
        assert output is not None
        cache = Cache()
        assert cache.exists(dataframe_cache_key)

        self.redis_cache.delete(dataframe_cache_key)

        assert cache.get(dataframe_cache_key) is not None

    def test_load_from_file(self):

        query_factory = QueryFactory(saved_query_id=69)
        combined = query_factory.load_dataframe('combined',harmonise_annotations=True,correction_type='SR')
        pass

    def test_get_task_view_cache(self):

        db_session = db.get_db_session()
        import requests
        session = requests.session()
        login_url = "https://phenomedb.npc.ic.ac.uk/login/"
        response = session.get(login_url)
        # var csrfToken = \'IjY2NjFhY2E0OWQ5N2NjMWM3MWZhZjczYjFjZDEyMzJmOTAyYjAzNzUi.You0YQ.rLh0ZA16QG7AsWmLYFgZqb76F4g\';
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            if re.search('csrfToken',content):
                content_array = re.split("csrfToken",content)
                csrf_split = re.split('\'\;',content_array[1])
                csrf_token = csrf_split[0].replace(" = '","")
        login_data = dict(username=config['HPC']['username'], password=config['HPC']['password'],csrf_token=csrf_token)
        response = session.post(login_url, data=login_data)

        task_runs = db_session.query(TaskRun).filter(TaskRun.id.in_([8693,3300,3381,3462,3543])).all()
        cache = Cache()
        for task_run in task_runs:
            task_run_output = task_run.get_task_output(cache)
            if task_run_output is not None:
                if 'task_run_ids' in task_run_output.keys():
                    sub_task_runs = db_session.query(TaskRun).filter(TaskRun.id.in_(task_run_output['task_run_ids'])).all()
                    for sub_task_run in sub_task_runs:
                        sub_task_run_output = sub_task_run.get_task_output(cache)
                        if sub_task_run_output is not None:
                            #if sub_task_run.class_name == 'RunPCA':
                            print('https://phenomedb.npc.ic.ac.uk/analysisview/analysisresult/%s' % sub_task_run.id)
                            r = session.get('https://phenomedb.npc.ic.ac.uk/analysisview/analysisresult/%s' % sub_task_run.id )
                            if r.status_code != 200:
                                response = session.get(login_url)
                                # var csrfToken = \'IjY2NjFhY2E0OWQ5N2NjMWM3MWZhZjczYjFjZDEyMzJmOTAyYjAzNzUi.You0YQ.rLh0ZA16QG7AsWmLYFgZqb76F4g\';
                                if response.status_code == 200:
                                    content = response.content.decode('utf-8')
                                    if re.search('csrfToken', content):
                                        content_array = re.split("csrfToken", content)
                                        csrf_split = re.split('\'\;', content_array[1])
                                        csrf_token = csrf_split[0].replace(" = '", "")
                                login_data = dict(username=config['username'],password=config['HPC']['password'], csrf_token=csrf_token)
                                response = session.post(login_url, data=login_data)

    def test_clear_nginx_cache(self):
        task_run_id = 3381
        utils.clear_task_view_cache(task_run_id)

    def test_model_cache(self):
        db_session = db.get_db_session()
        task_run = db_session.query(TaskRun).filter(TaskRun.id==478).first()
        output = task_run.get_task_output()
        data = task_run.get_task_data()
        pass

# def test_cache_exists(self):

   #     cache = Cache()
   #     prod_db_session = db.get_db_session()
   #     saved_query = prod_db_session.query(SavedQuery).filter(SavedQuery.id==2).first()
   #     assert cache.exists(saved_query.get_cache_dataframe_key(saved_query.get_dataframe_key('combined',model='AnnotatedFeature')))