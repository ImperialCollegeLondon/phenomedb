import os, sys, json, logging
from datetime import datetime
from pprint import pprint

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config

# PhenomeDB imports
import phenomedb.database as db
import phenomedb.utilities as utils
from phenomedb.pipeline_factory import PipelineFactory
from phenomedb.models import *
# Flask imports
from flask import Blueprint, request, jsonify, make_response, redirect, url_for, flash, render_template_string,send_from_directory#,app,after_this_request
#from flask_admin import BaseView, expose, has_access
from flask_appbuilder import BaseView as AppBuilderBaseView
from flask_appbuilder import expose, has_access
from flask.logging import default_handler
# Airflow imports:
from airflow.plugins_manager import AirflowPlugin
from phenomedb.base_view import *
import pandas as pd
import numpy as np
from flask import send_file
import re


VIEW_NAME = "cache"

class CacheView(PhenomeDBBaseView):

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)


    @expose('/')
    @has_access
    def list(self):
        return self.render_template("cache/list.html", data={})

    @expose('/table/json/')
    @has_access
    def get_table_json(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.set_db_session(request)
        json_data = json.dumps({"data":[[""]], "columns":[""]})
        try:

            #df = pd.DataFrame(columns=['key','redis','file','delete'])

            self.logger.info("getting all_keys")

            #df = self.cache.get_all_keys_dataframe()
            df = self.cache.get_cache_keys_dataframe(include_task_cache=True,include_analysis_view_cache=True)
            i = 0
            while i < df.shape[0]:
                df.loc[i,'delete'] = '<a href="%s?key=%s">Delete</a>' % (url_for('CacheView.delete'),df.loc[i,'key'])
                i = i + 1

            self.logger.info("df %s" % df)

            #df = self.get_result_rows(request)
            # make a link out of the display name column
            #if not df.empty:

            #    df[''] = [''.join(['<a href="' + url_for(".delete",id=x) + '"', '"/>', x, '</a>']) for x in df['id']]
                #df['saved_query_id'] = [''.join([
                #    '<a href="' + url_for("QueryFactoryView.advanced_saved_query_editor") + '?id=' +
                #    (str(int(float(x))) if x is not None and x is not '' else 'new'  ) + '"', '"/>',
                #    (str(int(float(x))) if x is not None and x is not '' else 'None'  ), '</a>']) for x in df['saved_query_id']]
            json_data = df.to_json(orient="split")

        except Exception as e: #this happens, be graceful
            error_msg = getattr(e, 'message', repr(e))
            self.logger.debug(str(e))
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]})

        d = json.loads(json_data)["data"]
        c = json.loads(json_data)["columns"]

        # response is formatted for display in a DataTable:
        return jsonify(table_data = d, columns = [{"title": str(col)} for col in c])

    @expose('/delete_analysis_view_table_cache/')
    @has_access
    def delete_analysis_view_table_cache(self):
        self.cache.delete_keys_by_regex('analysis_view_table_row_')
        return redirect(url_for('CacheView.list'))

    @expose('/delete/')
    @has_access
    def delete(self):
        if 'key' in request.args:
            self.cache.delete(request.args.get('key'))
        return redirect(url_for('CacheView.list'))

    @expose('/deleteall/<type>/')
    @has_access
    def deleteall(self,type):
        if type == 'redis':
            self.logger.info('redis cache flushed')
            self.cache.redis_cache.flushall()
        else:
            self.logger.info('redis and file cache flushed and saved queries reset. (Not task files)' )
            self.cache.flushall(include_task_cache=False)
        return redirect(url_for('CacheView.list'))

    @expose('/refresh/')
    @has_access
    def refresh(self):

        self.cache.generate_file_cache_list()
        return redirect(url_for('CacheView.list'))

cache_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder='../templates',
    static_folder='../templates/static',
    static_url_path='/static/phenomedb')

#compound_view = CompoundView(category="PhenomeDB", name="Compounds")

v_appbuilder_view = CacheView()
v_appbuilder_package = {"name": "Cache",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}

appbuilder_mitem = {"name": "Cache",
                    "category": "PhenomeDB",
                    "category_icon": "fa-th",
                    "href": "/batchcorrection/"}

class CachePlugin(AirflowPlugin):

    name = VIEW_NAME

    # flask_blueprints and admin_views are AirflowPlugin properties
    flask_blueprints = [cache_bp]
    #admin_views = [compound_view]
    #admin_views = []
    appbuilder_views = [v_appbuilder_package]
    #appbuilder_menu_items = [appbuilder_mitem]
