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


VIEW_NAME = "batch_correction"

class BatchCorrectionView(PhenomeDBBaseView):

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)


    @expose('/')
    @has_access
    def list(self):
        return self.render_template("batch_correction/list.html", data={})

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

                df['id'] = [''.join(['<a href="' + url_for(".correcteddataset",id=x) + '"', '"/>', x, '</a>']) for x in df['id']]
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


    def get_result_rows(self,request):
        """
        Fetch compounds plus a count of related datasets
        :return: result as a pandas dataframe
        """
        df = None
        try:
            if 'saved_query_id' in request.args:
                df = self.sql_to_dataframe("select fd.* from feature_dataset fd inner join saved_query sq on fd.saved_query_id = sq.id and sq.id = %s" % request.args.get('saved_query_id'))
            else:
                df = self.sql_to_dataframe("select fd.* from feature_dataset fd inner join saved_query sq on fd.saved_query_id = sq.id where fd.sr_correction_parameters is not null or fd.ltr_correction_parameters is not null")
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df

    @expose('/correcteddataset/<id>',methods=['GET'])
    @has_access
    def correcteddataset(self,id):

        self.set_db_session(request)

        harmonised_dataset = self.db_session.query(HarmonisedDataset).filter(HarmonisedDataset.id==id).first()

        if not harmonised_dataset:
            self.logger.error('No harmonisation_dataset_id with id %s' % id)
            flash('No harmonisation_dataset_id with id %s' % id)
            return redirect(url_for(".list"))

        corrected_annotated_features = self.db_session.query(HarmonisedAnnotatedFeature).filter(HarmonisedAnnotatedFeature.harmonised_dataset_id==id).first()

        if not corrected_annotated_features:
            self.logger.error('No corrected annotated_features with harmonisation_dataset_id %s' % id)
            flash('No corrected annotated_features with harmonisation_dataset_id %s' % id)
            return redirect(url_for(".list"))

        return self.render_template_to_html_or_json('batch_correction/corrected_dataset.html',data={'corrected_annotated_features':corrected_annotated_features})

    @expose('/dashboard/<id>',methods=['GET'])
    @has_access
    def dashboard(self,id):

        self.set_db_session(request)

        saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==id).first()

        feature_dataset = self.db_session.query(FeatureDataset).filter(
            FeatureDataset.saved_query_id==saved_query.id).first()

        sr_committed_batch_correction_task_run = self.db_session.query(TaskRun).filter(
            TaskRun.id==feature_dataset.sr_correction_task_run_id).first()

        ltr_committed_batch_correction_task_run = self.db_session.query(TaskRun).filter(
            TaskRun.id == feature_dataset.ltr_correction_task_run_id).first()

        uncommitted_batch_correction_task_runs = self.db_session.query(TaskRun).filter(TaskRun.saved_query_id==id,
                                                                                        TaskRun.class_name=='RunNPYCBatchCorrection').order_by(TaskRun.id.desc()).all()
                                                                                           #TaskRun.id!=feature_dataset.ltr_correction_task_run_id)\

        sr_uncommitted_batch_correction_task_runs = []
        ltr_uncommitted_batch_correction_task_runs = []

        for uncommitted_batch_correction_task_run in uncommitted_batch_correction_task_runs:
            if 'correction_type' in uncommitted_batch_correction_task_run.args:
                if uncommitted_batch_correction_task_run.args['correction_type'] == "SR":
                    sr_uncommitted_batch_correction_task_runs.append(uncommitted_batch_correction_task_run)
                elif uncommitted_batch_correction_task_run.args['correction_type'] == "LTR":
                    ltr_uncommitted_batch_correction_task_runs.append(uncommitted_batch_correction_task_run)
                else:
                    self.logger.info("Unknown correction task %s" % uncommitted_batch_correction_task_run)

        self.logger.info("Uncommitted SR correction task runs %s" % sr_uncommitted_batch_correction_task_runs)
        self.logger.info("Uncommitted LTR correction task runs %s" % ltr_uncommitted_batch_correction_task_runs)

        return self.render_template('batch_correction/dashboard.html',data={'sr_committed_batch_correction_task_run':sr_committed_batch_correction_task_run,
                                                                            'sr_uncommitted_batch_correction_task_runs': sr_uncommitted_batch_correction_task_runs,
                                                                            'ltr_committed_batch_correction_task_run': ltr_committed_batch_correction_task_run,
                                                                            'ltr_uncommitted_batch_correction_task_runs': ltr_uncommitted_batch_correction_task_runs,
                                                                            'saved_query':saved_query,
                                                                            'feature_dataset':feature_dataset})


    @expose('/runbatchcorrection/',methods=['POST'])
    @has_access
    def runbatchcorrection(self):

        self.set_db_session(request)

        if 'task_run_id' in request.form:
            task_run_id = request.form.get('task_run_id')
        else:
            raise Exception('task_run_id not set')

        # to do: add role_id to task_run table and check user has correct role access for results

        if 'params' in request.args:
            params = request.args.get('params')
        else:
            raise Exception('params not set')

        if 'saved_query_id' not in params:
            raise Exception('params.saved_query_id not set')

        pipeline = PipelineFactory(pipeline_name='RunBatchCorrection',db_env=self.db_env)
        pipeline.run_pipeline(run_config={utils.clean_task_id('run_batch_correction'):params})

        return jsonify(data={'Pipeline Name:' + pipeline.name})

    @expose('/savebatchcorrection/',methods=['POST'])
    @has_access
    def savebatchcorrection(self):

        self.set_db_session(request)

        if 'task_run_id' in request.form:
            task_run_id = request.form.get('task_run_id')
        else:
            raise Exception('task_run_id not set')

        pipeline = PipelineFactory(pipeline_name='SaveBatchCorrection',db_env=self.db_env)
        pipeline.run_pipeline(run_config = {utils.clean_task_id('savebatchcorrection'): {'correction_data_task_run_id': task_run_id}})

        return jsonify(data={'success': True})

    #@app.after_request
    #def add_header(r):
    #    """
    #    Add headers to both force latest IE rendering engine or Chrome Frame,
    #    and also to cache the rendered page for 10 minutes.
    #    """
    #    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    #    r.headers["Pragma"] = "no-cache"
    #    r.headers["Expires"] = "0"
    #    r.headers['Cache-Control'] = 'public, max-age=0'
    #    return r

analysis_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder='../templates',
    static_folder='../templates/static',
    static_url_path='/static/phenomedb')

v_appbuilder_view = BatchCorrectionView()
v_appbuilder_package = {"name": "Batch Correction",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}

appbuilder_mitem = {"name": "Batch Correction",
                    "category": "PhenomeDB",
                    "category_icon": "fa-th",
                    "href": "/batchcorrection/"}

#class BatchCorrectionPlugin(AirflowPlugin):

    #name = VIEW_NAME

    #flask_blueprints = [analysis_bp]
    #appbuilder_views = [v_appbuilder_package]
