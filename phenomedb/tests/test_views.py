import unittest
import sys
from pathlib import Path
import os
import sys, os
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])
import phenomedb.database as db
#import phenomedb.views as views
#import phenomedb.utilities as utils
from phenomedb.base_view import PhenomeDBBaseView
from flask import request
from sqlalchemy import Column
from phenomedb.config import config
import pytest

class TestViewAndUtilityMethods():
    
    #logger = utils.configure_logging(identifier='TEST', log_file='phenomedb_test.log')
    #views.test_session, views.test_engine = db.create_test_database_session()
    phenomedb_base_view = PhenomeDBBaseView()
    phenomedb_base_view.db_session = db.get_db_session(db_env="TEST")
    phenomedb_base_view.configure_logging(identifier="TESTVIEWS")
    

        
        
    def test_sql_to_dataframe(self,create_min_database,
                              create_pipeline_testing_project):
        print('test_sql_to_dataframe')
        df = self.phenomedb_base_view.sql_to_dataframe("SELECT * from project where id = :id", {"id":1})
        assert df.empty == False
        #self.assertFalse(df.empty, "Project 1 dataframe is empty")

    def test_execute_sql(self,create_min_database,
                         create_pipeline_testing_project):
        print('test_execute_sql')
        result = self.phenomedb_base_view.execute_sql("SELECT * from project where id = :id",{"id":1})
        print('Project 1', result)
        assert len(result) == 1
        #self.assertEqual(len(result), 1, "Failed to find project 1")
    
    def test_get_entity_as_df(self,create_min_database,
                              create_pipeline_testing_project):
        print('test_get_entity_as_df')
        table_name = 'project'
        id = 1
        df = self.phenomedb_base_view.get_entity_as_df(table_name, id)
        print('Project 1', df)
        assert df.empty == False
        #self.assertFalse(df.empty, "Project 1 dataframe is empty")
    
    def test_get_entity_as_dict(self,create_min_database,
                                create_pipeline_testing_project):
        print('test_get_entity_as_dict')
        table_name = 'project'
        id = 1
        relations = True
        d = self.phenomedb_base_view.get_entity_as_dict(table_name, id, relations)
        print('entity as dictionary', d)
        assert d['id'] == id
        #self.assertEqual(d['id'], id, "Project 1 dict id is not 1")
    
    def test_foreign_keys(self,create_min_database,
                          create_pipeline_testing_project):
        print('test_foreign_keys')
        table_name = 'chemical_standard_dataset'
        table_class = self.phenomedb_base_view.get_class_by_tablename(table_name)
       
        fk_col = self.phenomedb_base_view.foreign_keys(table_class)
        assert isinstance(fk_col['assay_id'], Column) == True
        assert isinstance(fk_col['aliquot_id'], Column) == True
        #self.assertIsInstance(fk_col['assay_id'], Column, 'no assay foreign key from chemical_standard_dataset')
        #self.assertIsInstance(fk_col['aliquot_id'], Column, 'no aliquot foreign key from chemical_standard_dataset')
    


    
