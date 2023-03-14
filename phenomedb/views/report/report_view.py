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
import ast


VIEW_NAME = "report"

class ReportView(PhenomeDBBaseView):

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)


    @expose('/')
    @has_access
    def list(self):
        return self.render_template("report/list.html", data={})

    @expose('/table/json/')
    @has_access
    def get_table_json(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.set_db_session(request)
        json_data = json.dumps({"data":[[""]], "columns":[""]})
        try:
            df = self.get_result_rows(request)
            # make a link out of the display name column
            if not df.empty:
                index = 0
                print(df)
                while index < df.shape[0]:
                    id = int(float(df.loc[index,'id']))
                    reports = ast.literal_eval(df.loc[index,'reports'])
                    report_string = ""
                    for report_name,report_location in reports.items():
                        report_string = "%s <a href='%s'>%s</a>" % (report_string, url_for(".viewreport",id=id,report_name=report_name),report_name)
                        self.logger.info(report_string)
                    df.loc[index,'reports'] = report_string
                    if 'status' in df.columns and df.loc[index,'status'] in ['started', 'success', 'error']:
                        task_run = self.db_session.query(TaskRun).filter(TaskRun.id == id).first()
                        df.loc[index, 'status'] = '<a href="' + task_run.get_log_url() + '">' + df.loc[index,'status'] + '</a>'
                    index = index + 1
                if 'saved_query_id' in df.columns:
                    df['saved_query_id'] = [
                        ''.join(['<a href="' + url_for("QueryFactoryView.advanced_saved_query_editor") + '?id=', str(x),'"/>', str(x), '</a>']) for x in df['saved_query_id']]
                json_data = df.to_json(orient="split")

        except Exception as e: #this happens, be graceful
            error_msg = getattr(e, 'message', repr(e))
            self.logger.debug(str(e))
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]})

        d = json.loads(json_data)["data"]
        c = json.loads(json_data)["columns"]

        self.db_session.close()
        # response is formatted for display in a DataTable:
        return jsonify(table_data = d, columns = [{"title": str(col)} for col in c])


    def get_result_rows(self,request):
        """
        Fetch compounds plus a count of related datasets
        :return: result as a pandas dataframe
        """
        df = None
        try:
            if 'saved_query_id' in request.args:
                df = self.sql_to_dataframe("select id, status, reports, args from task_run where reports is not null and saved_query_id = %s" % request.args.get('saved_query_id'))
            else:
                df = self.sql_to_dataframe("select id, status, saved_query_id, reports, username from task_run where reports is not null")
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df


    @expose('/viewreport/<id>/<report_name>',methods=['GET'])
    @has_access
    def viewreport(self,id,report_name):

        self.set_db_session(request)

        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==id).first()

        html_file = None

        self.logger.info("report_name: %s" % report_name)

        report_folder = task_run.reports[report_name]

        if not os.path.exists(report_folder):
            report_folder = config['DATA']['app_data'] + ('/task_runs/task_run_%s/reports/%s/' % (task_run.id,report_name))

        self.logger.info(report_folder)

        for file in os.listdir(report_folder):
            self.logger.info(file)
            if re.search('html$',file):
                html_file = file
                break

        if not html_file:
            #html_file = os.listdir(report_folder)[0]
            raise Exception("No report .html found!")

        file = open(report_folder + '/' + html_file, 'r')
        filedata = file.read()
        file.close()
        self.db_session.close()
        return filedata.replace('graphics/', (url_for('.servereportstatic',id=task_run.id,report_name=report_name) + '?file='))

        #file = open(report_folder + '/' + html_file, 'w')
        #file.write(filedata)
        #file.close()
        #os.chmod(report_folder + '/' + html_file, 755)
        #self.db_session.close()

 #       return send_from_directory(report_folder,html_file)

    @expose('/servereportstatic/<id>/<report_name>',methods=['GET'])
    @has_access
    def servereportstatic(self,id,report_name):

        self.logger.info(request.args)

        if 'report_name' in request.args:
            report_name = request.args.get('report_name')
        # to do: add role_id to task_run table and check user has correct role access for results

        if 'file' in request.args:
            file = request.args.get('file')
            self.logger.info("file: %s" % file)
        else:
            raise Exception('file not set')

        folder_path = config['DATA']['app_data'] + ('/task_runs/task_run_%s/reports/%s/graphics/' % (id,report_name))
        self.logger.info("folder_path: %s" % folder_path)
        if not os.path.exists(folder_path):
            raise Exception("Folder does not exists: %s" % folder_path)

        return send_from_directory(folder_path,file)

    @expose('/downloadpdfreport/<task_run_id>/<report_name>', methods=['GET'])
    @has_access
    def downloadpdfreport(self, task_run_id, report_name):

        self.logger.info(request.args)
        self.set_db_session(request)
        # to do: add role_id to task_run table and check user has correct role access for results
        folder_path = config['DATA']['app_data'] + ('task_runs/task_run_%s/' % (task_run_id))
        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==task_run_id).first()
        task_run_output = task_run.get_task_output(self.cache)
        if report_name in task_run_output.keys():
            return send_from_directory(folder_path, os.path.basename(task_run_output['pdf_report']))


analysis_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder='../templates',
    static_folder='../templates/static',
    static_url_path='/static/phenomedb')

#compound_view = CompoundView(category="PhenomeDB", name="Compounds")

v_appbuilder_view = ReportView()
v_appbuilder_package = {"name": "Reports",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}

appbuilder_mitem = {"name": "Reports",
                    "category": "PhenomeDB",
                    "category_icon": "fa-th",
                    "href": "/reportview/"}

class ReportPlugin(AirflowPlugin):

    name = VIEW_NAME

    # flask_blueprints and admin_views are AirflowPlugin properties
    flask_blueprints = [analysis_bp]
    #admin_views = [compound_view]
    #admin_views = []
    appbuilder_views = [v_appbuilder_package]
    #appbuilder_menu_items = [appbuilder_mitem]
