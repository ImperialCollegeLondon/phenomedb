from phenomedb.task import Task
from phenomedb.models import *
from phenomedb.config import config
import redis
import os
from pathlib import Path
import pandas as pd
import pyarrow as pa
import json
import re
import requests
from sqlalchemy.dialects import postgresql
import sys

class CreateSavedQueryDataframeCache(Task):
    """Task to Create a SavedQuery Dataframe Cache.
    Takes a SavedQuery, and generates the cache for the dataframe

    :param saved_query_id: The ID of the SavedQuery, defaults to None
    :type saved_query_id: int, optional
    :param master_unit: The master unit to harmonise units against, defaults to 'mmol/L'
    :type master_unit: str, optional
    :param class_level: Query Aggregration class level (for Compounds), defaults to None
    :type class_level: str, optional
    :param class_type: Query Aggregration class type, defaults to None
    :type class_type: str, optional
    :param output_model: The output model of the query, defaults to 'AnnotatedFeature'
    :type output_model: str, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional

    """

    reset_generate_cache_on_fail = True

    def __init__(self,username=None,task_run_id=None,saved_query_id=None,class_level=None,class_type=None,
                output_model='AnnotatedFeature',master_unit=None,correction_type=None,db_env=None,db_session=None,
                 execution_date=None,reload_cache=True,pipeline_run_id=None,upstream_task_run_id=None):
        
        super().__init__(task_run_id=task_run_id,username=username,db_env=db_env,db_session=db_session,
                         execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)

        self.saved_query_id = saved_query_id

        if master_unit is not None:
            self.convert_units = True
        else:
            self.convert_units = False
        self.master_unit = master_unit
        self.output_model = output_model
        self.correction_type = correction_type
        self.reload_cache = reload_cache
        self.args['master_unit'] = master_unit
        self.args['saved_query_id'] = saved_query_id
        self.args['output_model'] = output_model
        self.args['class_level'] = class_level
        self.args['class_type'] = class_type
        self.args['correction_type'] = correction_type
        self.args['reload_cache'] = reload_cache

        self.get_class_name(self)

    def process(self):
        """Process method, loads the SavedQuery, QueryFactory, and generates the dataframe cache
        """        

        self.saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==self.saved_query_id).first()

        from phenomedb.query_factory import QueryFactory

        query_factory = QueryFactory(saved_query=self.saved_query,db_env=self.db_env)

        self.logger.info("QueryFactory QueryDict: %s" % query_factory.query_dict)
        self.logger.info("QueryFactory SQLAlchemy: %s" % query_factory.get_code_string())
        self.logger.info("QueryFactory query: %s" % query_factory.query)
        self.logger.info(
            "QueryFactory parameterised query: %s" % query_factory.query.statement.compile(dialect=postgresql.dialect(),
                                                                                           compile_kwargs={
                                                                                               "literal_binds": True}))

        #query_factory.load_dataframe(reload_cache=True,type='combined',output_model=self.output_model,
        #                             class_type=self.class_type,class_level=self.class_level,
        #                             convert_units=self.convert_units,master_unit=self.master_unit,
        #                             correction_type=self.correction_type,harmonise_annotations=False)

        #self.output = "Unharmonised %s dataframe cached" % query_factory.get_dataframe_key(type='combined',model=self.output_model,
        #                                                                      class_type=self.class_type,class_level=self.class_level,
        #                                                                      correction_type=self.correction_type,db_env=self.db_env,
        #                                                                      harmonise_annotations=False)

        query_factory.load_dataframe(reload_cache=self.reload_cache, type='combined', output_model=self.output_model,
                                     class_type=self.class_type, class_level=self.class_level,
                                     convert_units=self.convert_units, master_unit=self.master_unit,
                                     correction_type=self.correction_type, harmonise_annotations=True)

        self.output = "Harmonised %s dataframe cached" % query_factory.get_dataframe_key(type='combined',
                                                                                           model=self.output_model,
                                                                                           class_type=self.class_type,
                                                                                           class_level=self.class_level,
                                                                                           correction_type=self.correction_type,
                                                                                           db_env=self.db_env,
                                                                                           harmonise_annotations=True)

class CreateSavedQuerySummaryStatsCache(Task):
    """Task to Create a SavedQuery Summary Stats Cache.
    Takes a SavedQuery, and generates the cache for the summary stats

    :param saved_query_id: The ID of the SavedQuery, defaults to None
    :type saved_query_id: int, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param pipeline_run_id: The Pipeline run ID
    :type pipeline_run_id: str, optional

    """    

    def __init__(self,username=None,task_run_id=None,saved_query_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):
 
        self.saved_query_id = saved_query_id

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)
        self.args['saved_query_id'] = saved_query_id

        self.get_class_name(self)

    def process(self):
        """Process method. Loads the summary statistics and saves in Cache
        """        

        self.saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==self.saved_query_id).first()

        from phenomedb.query_factory import QueryFactory
        query_factory = QueryFactory(saved_query=self.saved_query,db_env=self.db_env)

        query_factory.load_summary_statistics()

        self.output = "SavedQuery %s:%s summary statistics cached" % (self.saved_query.id, self.saved_query.name)

class CreateTaskViewCache(Task):

    def __init__(self,username=None,caching_task_run_id=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):
        super().__init__(username=username, task_run_id=task_run_id, db_env=db_env, db_session=db_session,
                 execution_date=execution_date, pipeline_run_id=pipeline_run_id,
                 upstream_task_run_id=upstream_task_run_id)

        self.caching_task_run_id = caching_task_run_id
        self.get_class_name(self)

    def process(self):
        """Process method
        """

        if utils.is_number(self.caching_task_run_id):

            task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(float(self.caching_task_run_id))).first()

            login_url = config['WEBSERVER']['url'] + "login"
            login_data = dict(username=config['PIPELINES']['pipeline_manager_user'], password=config['PIPELINES']['pipeline_manager_password'])
            session = requests.session()
            response = session.post(login_url, data=login_data)

            session.get(task_run.get_url())

class Cache:
    '''
        The Cache object is an abstracted interface to the redis and file cache.

        Items in the cache are stored in redis for 24 hours, and on disk for 30 days.

        This means we reduce the memory footprint without losing the performance of the cache (ie not having to load from database).

        Methods to get, set, and expire objects
    '''

    cache_directory = config['DATA']['cache']
    file_cache_key = 'CacheFiles'
    context = pa.default_serialization_context()
    redis_cache = redis.Redis(host=config['REDIS']['host'],
                              port=config['REDIS']['port'],
                              #username=config['REDIS']['user'],
                              password=config['REDIS']['password'])

    def __init__(self):
        """Constructor
        """

        self.logger = utils.configure_logging('phenomedb.cache','phenomedb.log')

        Path(self.cache_directory).mkdir(parents=True, exist_ok=True)
        # If the file_cache_key does not exist, build it from the cache directory
        # The file cache is a list of which files exist on disk, so we don't have to look up everytime

        if not self.redis_cache.exists(self.file_cache_key) or not self.redis_cache.get(self.file_cache_key):
            self.generate_file_cache_list()
        else:
            self.load_file_cache_list()
        #self.generate_file_cache_list()

    def delete_test_keys(self):
        """Delete any key with TEST in the name
        """

        self.logger.debug('Delete test keys called')
        keys_for_deletion = []
        for key in self.redis_cache.keys():
            if re.search("TEST",key.decode('utf-8')):
                keys_for_deletion.append(key)
        for key in self.file_cache_list:
            if re.search("TEST", key):
                keys_for_deletion.append(key)
        for key in keys_for_deletion:
            self.delete(key)
        self.logger.info("Deleted following cache keys: %s" % keys_for_deletion)

    def delete_keys_by_regex(self,regex):
        """Delete any key that matches the regex

        :param regex: The regex to match on
        :type regex: str
        """

        self.logger.debug('Delete keys by regex %s' % regex)
        keys_for_deletion = []
        for key in self.redis_cache.keys():
            if re.search(regex, key.decode('utf-8')):
                keys_for_deletion.append(key)
        for key in self.file_cache_list:
            if re.search(regex, key):
                keys_for_deletion.append(key)
        for key in keys_for_deletion:
            self.delete(str(key))

    def get_keys_dict(self,include_task_cache=False,include_analysis_view_cache=False):
        """Builds a dictionary of the keys in the cache

        :param include_task_cache: Whether to include the task cache, defaults to False
        :type include_task_cache: bool, optional
        :param include_analysis_view_cache: Whether to include the analysis_view_cache, defaults to False
        :type include_analysis_view_cache: bool, optional
        :return: a dictionary of the keys in the cache
        :rtype: dict
        """

        all_keys = {}
        for key in self.redis_cache.keys():
            utf8_key = key.decode('utf-8')
            # if not all, ignore the Tasks
            include = True
            if re.search('^Task\w+',utf8_key) and include_task_cache is False:
                include = False
            elif re.search('analysis_view_table_row_', utf8_key) and include_analysis_view_cache is False:
                include = False

            if include is True:
                if utf8_key not in all_keys.keys():
                    all_keys[utf8_key] = {'redis':True}
                else:
                    all_keys[utf8_key]['redis'] = True

        for file_key in self.file_cache_list:
            key = file_key.replace("__","::").replace(".cache","")
            # if not include_task_cache, ignore the Tasks
            include = True
            if re.search('^Task\w+', file_key) and include_task_cache is False:
                include = False
            elif re.search('analysis_view_table_row_', file_key) and include_analysis_view_cache is False:
                include = False

            if include is True:
                if key not in all_keys.keys():
                    all_keys[key] = {'file':True}
                else:
                    all_keys[key]['file'] = True

        return all_keys

    def get_cache_keys_dataframe(self,include_task_cache=False,include_analysis_view_cache=False):
        """Get a dataframe of the keys in the cache (used to store a persistent record on disk)

        :param include_task_cache: Whether to include the task_cache, defaults to False
        :type include_task_cache: bool, optional
        :param include_analysis_view_cache: Whether to include the analysis_view_cache, defaults to False
        :type include_analysis_view_cache: bool, optional
        :return: a dataframe of the keys
        :rtype: :class:`pandas.DataFrame`
        """

        self.generate_file_cache_list()

        df = pd.DataFrame(columns=['key','redis','file'])

        all_keys = self.get_keys_dict(include_task_cache=include_task_cache,include_analysis_view_cache=include_analysis_view_cache)

        print(all_keys)

        for key, data in all_keys.items():
            if 'redis' in data.keys():
                redis = data['redis']
            else:
                redis = None
            if 'file' in data.keys():
                file = data['file']
            else:
                file = None
            row = {'key':key,'redis':redis,'file':file}
            df = df.append(row,ignore_index=True)

        return df

    def flushall(self,include_task_cache=False):
        """Flush/delete all the data

        :param include_task_cache: Whether to flush the task cache, defaults to False
        :type include_task_cache: bool, optional
        """

        self.logger.debug('Flush all called')

        self.redis_cache.flushall()

        import shutil
        folder = self.cache_directory
        for filename in os.listdir(folder):
            if include_task_cache is True or not re.search('^Task\w+',filename):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    self.logger.info('Failed to delete %s. Reason: %s' % (file_path, e))
                    raise

        self.generate_file_cache_list()

        db_session = db.get_db_session()
        for saved_query in db_session.query(SavedQuery).all():
            saved_query.cache_state = dict()
        db_session.flush()
        db_session.commit()
        db_session.close()
        self.logger.info("SavedQuery cache states reset")


    def load_file_cache_list(self):
        """Loads the file cache list from redis
        """        
        if self.redis_cache.exists(self.file_cache_key):
            self.file_cache_list = self.context.deserialize(self.redis_cache.get(self.file_cache_key))
        else:
            self.generate_file_cache_list()

        self.logger.debug("File cache lists: %s" % self.file_cache_list)

    def get(self,key):
        """Get an object from the cache. Checks Redis first, then the FileCache

        :param key: The key of the item to retrieve
        :type key: str
        :return: The object to return
        :rtype: object
        """

        self.logger.debug('Get called %s' % key)

        if self.redis_cache.exists(key):
            return self.context.deserialize(self.redis_cache.get(key))
        else:
            self.load_file_cache_list()
            # If the the key is in the file_cache_list, return it
            if self.key_filename(key) not in self.file_cache_list:
                self.generate_file_cache_list()

            if self.key_filename(key) in self.file_cache_list:
                return self.load_cache_from_file(key)
            # Else, return None (the cache does not exist on disk or in redis)
            else:
                self.logger.info("No item found in cache %s" % key)
                return None

    def set(self,key,value,ex=None):
        """Set an object in the cache.

        :param key: The key of the item to set.
        :type key: str
        :param value: The item to set
        :type value: object
        """

        self.logger.debug('Set called %s %s %s %s' % (key,value,type(value),ex))

        # This is a hack for now for misusing the ex parameter. Need to unfoorbar this.
        if ex == 'no-expiry':
            ex = None
        elif not ex:
            ex = 60*60*2
        elif not isinstance(ex,int):
            ex = 60*60*2


        # Write out to disk first (slow and more likely to fail, plus has better redundancy because if its not in redis, it will load from disk

        if isinstance(value, pd.DataFrame):

            if 'dataframe' not in key.lower():
                raise Exception("If caching a pandas DataFrame, then 'dataframe' or 'DataFrame' must be part of the key: %s \n columns: %s" % (key,value.columns))

            # write out a csv format file
            value.to_csv(str(Path(self.cache_directory + self.key_filename(key)).absolute()),index=False)
            self.redis_cache.set(key,self.context.serialize(value).to_buffer().to_pybytes(),ex=ex)

        else:
            # write out a binary format file
            serialized_value = self.context.serialize(value).to_buffer().to_pybytes()
            f = open(str(Path(self.cache_directory + self.key_filename(key)).absolute()), "wb")
            f.write(serialized_value)
            f.close()
            self.redis_cache.set(key,serialized_value,ex=ex)

        # Get the latest file cache list
        self.load_file_cache_list()

        if key not in self.file_cache_list:
            self.file_cache_list.append(key)
            self.redis_cache.set(self.file_cache_key,self.context.serialize(self.file_cache_list).to_buffer().to_pybytes())

    def key_filename(self,key):
        """Get the filename for the key

        :param key: The key of the item.
        :type key: str
        :return: The filename for the key
        :rtype: str
        """        
        return key.replace("::",'__') + ".cache"

    def delete(self,key):
        """Delete a key from the cache

        :param key: The key of the item
        :type key: str
        """

        self.logger.debug('Delete called %s' % key)

        # Remove it from the redis cache
        if self.redis_cache.exists(key):
            self.redis_cache.delete(key)

        self.load_file_cache_list()
        # Remove it from the file cache, and remove from the file_cache redis list
        if self.key_filename(key) in self.file_cache_list:
            file_path = str(Path(self.cache_directory + self.key_filename(key)).absolute())
            if os.path.exists(file_path):
                os.remove(file_path)
            self.file_cache_list.remove(self.key_filename(key))
            #self.redis_cache.set(self.file_cache_key,self.context.serialize(self.file_cache_list).to_buffer().to_pybytes())

        self.generate_file_cache_list()

    def exists(self,key):
        """Check whether the key exists in the cache

        :param key: The key of the item to check
        :type key: str
        :return: Whether the key exists in the cache
        :rtype: bool
        """

        self.logger.debug('Exists called %s' % key)

        if self.redis_cache.exists(key):
            return True
        else:
            self.load_file_cache_list()
            if self.key_filename(key) in self.file_cache_list:
                return True
            else:
                self.generate_file_cache_list()
                if self.key_filename(key) in self.file_cache_list:
                    return True
                else:
                    return False

    def load_cache_from_file(self,key):
        """Load the cache from the file

        :param key: The key of the item
        :type key: str
        :return: The object to return
        :rtype: object
        """

        self.logger.debug('Load cache from file called %s' % key)

        ex = config['REDIS']['memory_expired_seconds']
        if not isinstance(ex, int):
            ex = 86400

        try:

            if 'dataframe' in key.lower() and 'intensity_data' not in key.lower():

                value = pd.read_csv(str(Path(self.cache_directory + self.key_filename(key)).absolute()))
                self.logger.debug("Loaded from file cache %s %s" % (key,value))
                self.logger.debug("memory_expired_seconds %s" % config['REDIS']['memory_expired_seconds'])
                self.redis_cache.set(key,self.context.serialize(value).to_buffer().to_pybytes(),ex=ex)

            else:

                f = open(str(Path(self.cache_directory + self.key_filename(key)).absolute()), "rb")
                serialized_value = f.read()
                f.close()
                if isinstance(serialized_value,bytes):
                    self.redis_cache.set(key,serialized_value,ex=ex)
                    value = self.context.deserialize(serialized_value)
                    self.logger.debug("Loaded from file cache %s %s" % (key, value))
                else:
                    raise Exception("Unknown file cache data type: %s %s" % (key,type(serialized_value)))

            return value
        except Exception as err:
            bp = True
            raise Exception(err)

    def generate_file_cache_list(self):
        """Generate the file cache list and store in redis for quick reference
        """        

        # Get all the files in the cache directory
        files = (file for file in os.listdir(self.cache_directory)
                 if os.path.isfile(os.path.join(self.cache_directory, file)))

        # file keys is an array of the keys that exist on the disk - so we don't have to look up the keys from disk everytime
        file_keys = []
        for file in files:
            file_path = Path(self.cache_directory + file)
            if file not in file_keys:
                file_keys.append(file)

        self.redis_cache.set(self.file_cache_key,self.context.serialize(file_keys).to_buffer().to_pybytes())
        self.file_cache_list = file_keys

class RemoveUntransformedDataFromCache(Task):
    """Goes through all the task cache and removes the untransformed data from the output cache, which was causing bloat 

    :param lowest_finished: The lowest :class:`phenomedb.models.TaskRun` ID to start from, defaults to None
    :type lowest_finished: int, optional
    :param task_run_id: The TaskRun ID
    :type task_run_id: float, optional
    :param username: The username of the user running the job, defaults to None
    :type username: str, optional
    :param db_env: The db_env to use, 'PROD' or 'TEST', default 'PROD'
    :type db_env: str, optional
    :param db_session: The db_session to use
    :type db_session: object, optional
    :param execution_date: The date of execution, str format.
    :type execution_date: str, optional
    :param pipeline_run_id: The Pipeline run ID
    """

    def __init__(self,username=None,task_run_id=None,lowest_finished=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):

        super().__init__(task_run_id=task_run_id, username=username, db_env=db_env, db_session=db_session,
                         execution_date=execution_date, pipeline_run_id=pipeline_run_id,
                         upstream_task_run_id=upstream_task_run_id)

        self.lowest_finished = lowest_finished
        self.get_class_name(self)


    def process(self):
        import time

        task_run_query = self.db_session.query(TaskRun.id).filter(TaskRun.module_name.in_(['phenomedb.analysis',
                                                                                   'phenomedb.batch_correction',
                                                                                   'phenomedb.pipelines']))
        if self.lowest_finished is not None and utils.is_number(self.lowest_finished):
            task_run_query = task_run_query.filter(TaskRun.id < self.lowest_finished)

        task_run_ids = task_run_query.order_by(TaskRun.id.desc()).all()

        for task_run_id in task_run_ids:
            try:
                task_run = self.db_session.query(TaskRun).filter(TaskRun.id==task_run_id).first()
                if self.cache.exists(task_run.get_task_data_cache_key()):

                    task_run_data = self.cache.get(task_run.get_task_data_cache_key())
                    #output = dict(task_run.output)

                    # Just put the columns back in, not any missing rows!
                    updated = False
                    # put the missing columns back in!
                    if 'untransformed_intensity_data' in task_run_data.keys():
                        del(task_run_data['untransformed_intensity_data'])
                        updated = True

                    if 'untransformed_feature_metadata' in task_run_data.keys():
                        del(task_run_data['untransformed_feature_metadata'])
                        updated = True

                    if updated is True:
                        self.cache.set(task_run.get_task_data_cache_key(),task_run_data)
                        self.logger.info("%s updated" % task_run.id)
                    else:
                        self.logger.info("%s ignored" % task_run.id)

                    self.cache.redis_cache.delete(task_run.get_task_data_cache_key())
                else:
                    self.logger.info("%s no cache" % task_run.id)
            except Exception as err:
                self.logger.exception(err)
            time.sleep(0.4)

class MoveTaskOutputToCache(Task):
    """Move the task output to the cache. This was created to move the :class:`phenomedb.models.TaskRun` output to the cache, to free up database space and simplify data restore

    :param Task: _description_
    :type Task: _type_
    :raises Exception: _description_
    """

    task_output_sizes = {}

    def __init__(self, username=None, task_run_id=None, highest_finished=None, update_db=False, db_env=None, db_session=None,
                 execution_date=None, pipeline_run_id=None, upstream_task_run_id=None):
        super().__init__(task_run_id=task_run_id, username=username, db_env=db_env, db_session=db_session,
                         execution_date=execution_date, pipeline_run_id=pipeline_run_id,
                         upstream_task_run_id=upstream_task_run_id)

        self.highest_finished = highest_finished
        self.update_db = update_db

        self.get_class_name(self)
        self.args['highest_finished'] = highest_finished
        self.args['update_db'] = update_db

    def process(self):
        import time

        task_run_query = self.db_session.query(TaskRun.id).filter(TaskRun.output != None)#.filter(TaskRun.id <= 1146)
        if self.highest_finished is not None and utils.is_number(self.highest_finished):
            task_run_query = task_run_query.filter(TaskRun.id > self.highest_finished)

        task_run_ids = task_run_query.order_by(TaskRun.id.asc()).all()
        #task_run_ids = task_run_query.order_by(TaskRun.id.desc()).all()

        for task_run_id_struct in task_run_ids:
            task_run_id = task_run_id_struct[0]

            task_run = self.db_session.query(TaskRun).filter(TaskRun.id == task_run_id).first()

            if task_run.output is not None and (not self.cache.exists(task_run.get_task_output_cache_key()) or self.update_db is True):

                output = dict(task_run.output)

                self.cache.set(task_run.get_task_output_cache_key(),output)

                self.cache.redis_cache.delete(task_run.get_task_output_cache_key())

                if self.cache.get(task_run.get_task_output_cache_key()) != output:
                    raise Exception('Cache is not the same as expected %s != %s' % (self.cache.get(task_run.get_task_output_cache_key()),output))

                self.cache.redis_cache.delete(task_run.get_task_output_cache_key())

                self.logger.info("%s output created" % task_run_id)

                if self.update_db is True:
                    task_run.output = None
                    self.db_session.flush()
                    output_size_bytes = utils.total_size(output)
                    self.task_output_sizes[task_run_id] = {'task_run_id': task_run_id,
                                                           'output_size_bytes': output_size_bytes}

                    self.logger.info("TaskRun.output size %s" % self.task_output_sizes[task_run_id]['output_size_bytes'])

            else:
                self.logger.info("%s output exists or is None" % task_run_id)

            time.sleep(0.2)

        if self.update_db is True:
            df = pd.DataFrame.from_dict(self.task_output_sizes, orient='index')
            self.logger.info(self.task_output_sizes)
            self.logger.info(df)
            #df.to_csv(str(Path(config['DATA']['app_data'] + "/output/task_output_cache_differences.csv").absolute()),index=False)
