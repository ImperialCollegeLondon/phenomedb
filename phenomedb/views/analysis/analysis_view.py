import os, sys, json, logging
from datetime import datetime
from pprint import pprint

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config

# PhenomeDB imports
import phenomedb.database as db
import phenomedb.utilities as utils
from phenomedb.models import *
# Flask imports
from flask import Blueprint, request, jsonify, make_response, redirect, url_for, flash
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
from phenomedb.pipeline_factory import PipelineFactory
from copy import deepcopy
import ast
import re

VIEW_NAME = "analysis"

class AnalysisView(PhenomeDBBaseView):

    unique_kegg_ids = []

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)


    @expose('/')
    @has_access
    def list(self):
        self.set_db_session(request)
        saved_queries = self.db_session.query(SavedQuery).order_by(SavedQuery.name).all()
        tasks = PipelineFactory.get_tasks_from_json(modules_to_include=['phenomedb.analysis','phenomedb.batch_correction','phenomedb.pipelines'])
        #self.logger.info("Task list: %s" % tasks)
        self.db_session.close()
        return self.render_template(
            "analysis/analysis.html", data={'saved_queries':saved_queries,'tasks':tasks})

    @expose('/table/json/')
    @has_access
    def get_table_json(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.logger.info("Called AnalysisView.get_table_json %s" % request.args)

        self.set_db_session(request)
        json_data = json.dumps({"data":[[""]], "columns":[""]})
        try:
            df = self.get_result_rows(request)
            # make a link out of the display name column
            if not df.empty:
                index = 0
                df['delete'] = None
                self.logger.info("Loading analysis table rows...")
                while(index < df.shape[0]):

                    cache_row = None
                    key = 'analysis_view_table_row_' + df.loc[index, 'id']
                    if not df.loc[index,'status'] != 'success':
                        if self.cache.exists(key):
                            cache_row = self.cache.get(key)
                            #self.logger.info("loaded row from cache %s" % key)

                    if cache_row is None:

                        # rebuild cache
                        if 'class_name' in request.args and request.args.get('class_name') == 'RunNPYCBatchCorrection':
                            df.loc[index,'class_name'] = '<a href="' + url_for("BatchCorrectionView.dashboard",id=int(float(df.loc[index,'saved_query_id']))) + '">' + df.loc[index,'class_name'] + '</a>'
                        status = None
                        if 'status' in df.loc[index,:] and df.loc[index,'status'] in ['started','success','error']:
                            status = df.loc[index,'status']
                            task = self.db_session.query(TaskRun).filter(TaskRun.id == int(float(df.loc[index,'id']))).first()
                            df.loc[index,'status'] = '<a href="' + task.get_log_url() + '">' + df.loc[index,'status'] + '</a>'

                        if 'reports' in df.loc[index,:] and df.loc[index,'reports'] is not None and df.loc[index,'reports'] != {}:
                            #self.logger.info(df.loc[index, 'reports'])
                            reports = ast.literal_eval(df.loc[index, 'reports'])
                            #self.logger.info(reports)
                            if isinstance(reports,dict):
                                id = int(float(df.loc[index, 'id']))
                                report_string = ""
                                for report_name, report_location in reports.items():
                                    report_string = "%s <a href='%s'>%s</a>" % (
                                    report_string, url_for("ReportView.viewreport", id=id, report_name=report_name), report_name)
                                df.loc[index, 'reports'] = report_string
                                #self.logger.info("Reports: " % report_string)

                        df.loc[index, 'delete'] = '<a href="' + url_for(".delete_task_run",id=df.loc[index, 'id']) + '"/>delete</a>'

                        df.loc[index, 'id'] = '<a href="' + url_for(".analysisresult", id=df.loc[index,'id']) + '"/>' + df.loc[index,'id'] + '</a>'

                        if df.loc[index,'saved_query_id'] is not None and str(df.loc[index,'saved_query_id']) != '':
                            if df.loc[index,'saved_query_id'] == 'new':
                                df.loc[index,'saved_query_id'] = '<a href="' + url_for("QueryFactoryView.advanced_saved_query_editor") + '?id=new">' + str(int(float(df.loc[index,'saved_query_id']))) + '</a>'
                            elif df.loc[index,'saved_query_id'] is not None and str(df.loc[index,'saved_query_id']) != 'None':
                                df.loc[index,'saved_query_id'] = '<a href="' + url_for("QueryFactoryView.advanced_saved_query_editor") + '?id=' + str(int(float(df.loc[index,'saved_query_id']))) + '">' + str(int(float(df.loc[index,'saved_query_id']))) + '</a>'

                        if status == 'success':
                            self.cache.set(key,df.loc[index,:],ex='no-expiry')
                            #self.logger.info("set row into cache %s" % key)

                    else:
                        # set from cache
                        df.loc[index,:] = cache_row

                    index = index + 1

                json_data = df.to_json(orient="split")
                self.logger.info("...analysis table rows loaded")

        except Exception as e: #this happens, be graceful
            self.logger.exception(e)
            error_msg = getattr(e, 'message', repr(e))
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]})

        d = json.loads(json_data)["data"]
        c = json.loads(json_data)["columns"]

        #self.db_session.close()
        # response is formatted for display in a DataTable:
        return jsonify(table_data = d, columns = [{"title": str(col)} for col in c])


    def get_result_rows(self,request):
        """
        Fetch compounds plus a count of related datasets
        :return: result as a pandas dataframe
        """
        df = None
        try:
            if 'task_run_id' in request.args:
                df = self.sql_to_dataframe("select * from task_run where id = %s" % request.args.get('task_run_id'))
            elif 'saved_query_id' in request.args:
                df = self.sql_to_dataframe("select id, status, saved_query_id, class_name, args, datetime_started, username from task_run where saved_query_id = %s" % request.args.get('saved_query_id'))
            elif 'saved_query_id' in request.args and 'class_name' in request.args:
                df = self.sql_to_dataframe("select id, status, saved_query_id, class_name, args, datetime_finished, username from task_run where saved_query_id = %s and class_name = '%s'" % (request.args.get('saved_query_id'),request.args.get('class_name')))
            elif 'class_name' in request.args:
                df = self.sql_to_dataframe("select id, status, saved_query_id, class_name, args, datetime_finished, username from task_run where class_name = '%s'" % request.args.get('class_name'))
            else:
                df = self.sql_to_dataframe("select task_run.id, task_run.status, task_run.saved_query_id, saved_query.name as query_name,task_run.class_name,task_run.args,task_run.datetime_finished,task_run.reports from task_run left join saved_query on task_run.saved_query_id = saved_query.id where task_run.module_name = 'phenomedb.analysis' or task_run.module_name = 'phenomedb.batch_correction' or task_run.module_name = 'phenomedb.pipelines'")

        except:
            raise
        return df

    @expose('/analysisresult/<id>',methods=['GET'])
    @has_access
    def analysisresult(self,id):

        self.set_db_session(request)

        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(float(id))).first()
        if task_run.status == [TaskRun.Status.created,TaskRun.Status.scheduled,TaskRun.Status.started]:
            flash('Task %s %s is not yet finished' % (task_run.class_name,task_run.task_id))
            return redirect(url_for(".list"))

        self.logger.info("TaskRun args %s" % task_run.args.keys())
        self.logger.info("TaskRun %s" % task_run)
        if task_run.pipeline:
            self.logger.info("TaskRun pipeline %s" % task_run.pipeline)

        task_data = None
        set_cache_control = False
        task_run_output = None

        if task_run.status in [TaskRun.Status.success,TaskRun.Status.success.value]:

            if self.cache.exists(task_run.get_task_data_cache_key()):
                task_data = self.cache.get(task_run.get_task_data_cache_key())
            else:
                task = task_run.get_task_class_object()
                if hasattr(task,'load_data'):
                    task.load_data()
                if hasattr(task,'data'):
                    self.logger.info("%s %s",task.data.keys(),type(task.data))
                    self.cache.set(task_run.get_task_data_cache_key(),task.data,ex=60*60*24)
                    task_data = task.data
            set_cache_control = True

            task_run_output = task_run.get_task_output(self.cache)
            #print("TaskRun output %s" % task_run_output)

        if task_data:
            #self.logger.debug("Task.data %s" % task_data)
            self.logger.debug("Task.data.keys() %s" % task_data.keys())
            self.logger.debug("Task.data['sample_metadata'].keys() %s" % task_data['sample_metadata'].keys())
            self.logger.debug("Task.data['feature_metadata'].keys() %s" % task_data['feature_metadata'].keys())
            #self.logger.debug("len(Task.data['intensity_data']) %s" % len(task_data['intensity_data']))

        if not task_run:
            self.logger.error('No analysis result with id %s' % id)
            flash('No analysis result with id %s' % id)
            return redirect(url_for(".list"))

        projects = self.db_session.query(Project).all()
        project_colours = {}
        for project in projects:
            project_colours[project.name] = project.chart_colour

        tasks = PipelineFactory.get_tasks_from_json()
        #self.logger.debug(tasks)
        class_task_spec = tasks[('%s.%s'%(task_run.module_name.replace("phenomedb.",''),task_run.class_name))]
        params = json.loads(class_task_spec['params'])

        saved_queries = self.db_session.query(SavedQuery).order_by(SavedQuery.name).all()

        data = {'task_run': task_run,'task_run_output': task_run_output, 'task_data': task_data, 'project_colours': project_colours,
                'task_spec': class_task_spec, 'task_params': params,
                'saved_queries': saved_queries}

        if task_data and 'sample_metadata' in task_data.keys():
            allowed_columns = ['Project', 'Unique Batch', 'Run Order','SampleType','AssayRole','Sample ID']
            harmonised_metadata_fields = self.db_session.query(HarmonisedMetadataField).all()
            for harmonised_metadata_field in harmonised_metadata_fields:
                allowed_columns.append("h_metadata::%s" % harmonised_metadata_field.name)

            sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])
            trimmed_metadata = pd.DataFrame()
            p = 0
            while p < len(sample_metadata.columns):
                column = sample_metadata.columns[p]
                if column in allowed_columns:
                    trimmed_metadata[column] = sample_metadata.loc[:,column]
                p = p + 1
            trimmed_metadata = trimmed_metadata.where(pd.notnull(trimmed_metadata), None)
            data['sample_metadata'] = trimmed_metadata.to_dict()
        #self.logger.debug(data['task_spec'])

        #print(data['task_run'].output['intensity_data']);

        if 'upstream_task_run_id' in task_run.args.keys() and task_run.args['upstream_task_run_id'] is not None:
            data['upstream_task_run'] = self.db_session.query(TaskRun).filter(TaskRun.id==int(float(task_run.args['upstream_task_run_id']))).first()

        if task_run.class_name == 'RunPCA':
            template = 'analysis/pca.html'
            data = self.load_pca_data(data)
        elif task_run.class_name == 'RunPCPR2':
            template = 'analysis/pcpr2.html'
        elif task_run.class_name == 'RunDBnormCorrection':
            template = 'analysis/dbnorm.html'
        elif task_run.class_name == 'RunMWAS' and task_run.status in [TaskRun.Status.success, TaskRun.Status.success.value]:
            data = self.load_mwas_features(data,request)
            projects = self.db_session.query(Project).all()
            data['project_colours'] = {}
            for project in projects:
                data['project_colours'][project.name] = project.chart_colour
            template = 'analysis/mwas.html'
            #data['get_params'] = request.args
        elif task_run.class_name == 'RunBatchCorrectionAssessmentPipeline':
            template = 'analysis/batch_correction_assessment_pipeline.html'
            data = self.load_batch_correction_assessment_pipeline(data)
        elif task_run.class_name == 'IntegratedAnalysisPipeline':
            data = self.load_integrated_pipeline_data(data)
            projects = self.db_session.query(Project).all()
            data['project_colours'] = {}
            for project in projects:
                data['project_colours'][project.name] = project.chart_colour
            template = 'analysis/integrated_analysis_pipeline.html'
            #data['get_params'] = request.args
        else:
            template = 'analysis/default.html'
            #self.logger.error('Unknown analysis class %s' % task_run.class_name)
            #flash('Unknown analysis class %s' % task_run.class_name)
            #return redirect(url_for(".list"))

#        template = self.render_template_to_html_or_json(template,data=data)
        r = make_response(self.render_template_to_html_or_json(template,data=data))
        if set_cache_control:
            r.headers['Cache-Control'] = 'max-age=600'
        return r

    def load_pca_data(self,data):
        title = 'TR:%s %s' % (data['task_run'].id,data['task_run'].saved_query.name)
        if 'scaling' in data['task_run'].args.keys() and data['task_run'].args['scaling'] is not None:
            title = "%s %s" % (title,data['task_run'].args['scaling'])
        else:
            title = "%s no scaling" % (title)
        if 'transform' in data['task_run'].args.keys() and data['task_run'].args['transform'] is not None:
            title = "%s %s" % (title,data['task_run'].args['transform'])
        else:
            title = "%s untransformed" % (title)
        if 'upstream_task_run_id' in data['task_run'].args.keys() and data['task_run'].args['upstream_task_run_id'] is not None:
            title = "%s %s" % (title,data['upstream_task_run'].class_name)
        data['title_base'] = title
        return data

    def load_batch_correction_assessment_pipeline(self,data):
        pcpr2 = {}
        pcpr2_fields = ['R2']
        mwas_tasks = []
        task_run_map = {}
        self.logger.info("task_run_output: %s" % data['task_run_output'])
        if isinstance(data['task_run_output'],dict):
            if 'task_run_ids' in data['task_run_output'].keys():
                task_runs = self.db_session.query(TaskRun).filter(TaskRun.id.in_(data['task_run_output']['task_run_ids'])).all()
                for task_run in task_runs:
                    task_run_map[task_run.task_id] = task_run.id
                    task_run_output = task_run.get_task_output(self.cache)
                    if task_run_output is not None:
                        if task_run.class_name == 'RunPCPR2' and 'pR2' in task_run_output.keys() and 'Z_order' in task_run_output:
                            pcpr2[task_run.task_id] = {'task_run_id': task_run.id}
                            i = 0
                            for z_order in task_run_output['Z_order']:
                                if z_order not in pcpr2_fields:
                                    pcpr2_fields.append(z_order)
                                pcpr2[task_run.task_id][z_order] = utils.precision_round(task_run_output['pR2'][i],3)
                                i = i + 1
                        elif task_run.class_name == 'RunMWAS':
                            mwas_tasks.append(str(task_run.id))

        data['task_run_map'] = task_run_map
        if len(mwas_tasks) > 0:
            data['mwas_compare_url'] = "%s/analysisview/analysisresult/%s?compare=%s" % (config['WEBSERVER']['url'], mwas_tasks.pop(0), ",".join(mwas_tasks))
        else:
            data['mwas_compare_url'] = ""
        data['pcpr2'] = pcpr2
        data['pcpr2_fields'] = pcpr2_fields
        self.logger.debug(data['pcpr2_fields'])
        self.logger.debug(data['pcpr2'])
        data['saved_query'] = self.db_session.query(SavedQuery).filter(SavedQuery.id==data['task_run'].saved_query_id).first()
        data['saved_query_name'] = data['saved_query'].name
        if data['task_run'].pipeline:
            data['pipeline_task_order'] = data['task_run'].pipeline.task_order
        else:
            data['pipeline_task_order'] = list(task_run_map.keys())

        return data

    def load_integrated_pipeline_data(self,data):

        data['pipeline'] = self.db_session.query(Pipeline).filter(Pipeline.name=='batch_correction_assessment_pipeline').first()

        task_run_table = pd.DataFrame.from_dict(data['task_run_output']['task_run_table'])
        data['saved_query_names'] = task_run_table.loc[:,'query_name'].to_dict()
        data['saved_query_mwas_compare'] = {}
        all_mwas = []
        i = 0
        while i < task_run_table.shape[0]:
            mwas_tasks = []
            p = 0
            while p < task_run_table.shape[1]:
                if re.search('mwas', task_run_table.columns[p]):
                    mwas_tasks.append(str(task_run_table.iloc[i, p]))
                p = p + 1

            mwas_compare_url = "%s/analysisview/analysisresult/%s?compare=%s" % (config['WEBSERVER']['url'], mwas_tasks.pop(0), ",".join(mwas_tasks))
            all_mwas = all_mwas + mwas_tasks
            data['saved_query_mwas_compare'][task_run_table.iloc[:, i].index.values[0]] = mwas_compare_url
            i = i + 1

        data['all_mwas_compare'] = "%s/analysisview/analysisresult/%s?compare=%s" % (config['WEBSERVER']['url'], all_mwas.pop(0), ",".join(all_mwas))

    #    data['task_ids'] = {}
    #    dataframe = pd.DataFrame.from_dict(data['task_run'].output['task_run_table']).transpose()
    #    data['task_ids'] = dataframe.index
        return data


    def load_mwas_features(self,data,request):
        fdr_n = None
        if 'fdr_n' in request.args:
            fdr_n = int(float(request.args['fdr_n']))
        dataframe = pd.DataFrame.from_dict(data['task_run_output']['mwas_results'])
        mwas_summaries = None
        if 'mwas_summaries' in data['task_run_output'].keys():
            mwas_summaries = data['task_run_output']['mwas_summaries']
        dataframe = self.build_mwas_table(dataframe,mwas_summaries=mwas_summaries,fdr_n=fdr_n,for_display=True)
        dataframe = dataframe.sort_values('log_adjusted_pvalues',ascending=True)
        dataframe = dataframe.reset_index()
        dataframe = dataframe.drop('index', axis=1)
        dataframe = dataframe.drop('_row', axis=1)
        data['n_features'] = dataframe.shape[1]
        if fdr_n:
            data['fdr_n'] = fdr_n
        else:
            data['fdr_n'] = data['n_features']
        data['n_significant_features'] = len(dataframe[(dataframe['adjusted_pvalues']<0.05)])
        data['n_features'] = dataframe.shape[0]
        mean_values = dataframe[(dataframe['adjusted_pvalues'] < 0.05)].mean()
        data['mean_significant_pvalue'] = utils.precision_round(mean_values['adjusted_pvalues'],type='str')
        min_values = dataframe[(dataframe['adjusted_pvalues'] < 0.05)].min()
        data['min_significant_pvalue'] = utils.precision_round(min_values['adjusted_pvalues'],type='str')
        max_values = dataframe[(dataframe['adjusted_pvalues'] < 0.05)].max()
        data['max_significant_pvalue'] = utils.precision_round(max_values['adjusted_pvalues'],type='str')
        data['mwas_table'] = dataframe.transpose().to_dict()
        data['other_mwas_task_runs'] = self.db_session.query(TaskRun).filter(TaskRun.class_name=='RunMWAS')\
            .filter(TaskRun.status==TaskRun.Status.success) \
            .filter(TaskRun.id != data['task_run'].id) \
            .order_by(TaskRun.id.desc()).all()
        sample_metadata = pd.DataFrame.from_dict(data['task_data']['sample_metadata'])
        data['n_samples'] = sample_metadata.shape[0]
        data['bonferroni_cutoff'] = utils.precision_round(0.05 / fdr_n)
        model_Y_variable = data['task_run'].args['model_Y_variable']
        data['min_y'] = sample_metadata[model_Y_variable].min()
        data['max_y'] = sample_metadata[model_Y_variable].max()
        data['n_features'] = pd.DataFrame.from_dict(data['task_data']['feature_metadata']).shape[0]
        data['unique_kegg_ids'] = self.unique_kegg_ids
        data['unique_kegg_ids_escaped'] = "&#13;&#10;".join(self.unique_kegg_ids)
        return data

    @expose('/load_task_run_for_MWAS/', methods=['POST'])
    @has_access
    def load_task_run_for_MWAS(self):
        request_data = request.get_json()
        self.set_db_session(request)
        if 'task_run_1_id' in request_data.keys() and 'task_run_2_id' in request_data.keys():

            fdr_n = None
            if 'fdr_n' in request_data.keys():
                fdr_n = int(float(request_data['fdr_n']))


            task_run_1_id = int(float(request_data['task_run_1_id']))
            task_run_2_id = int(float(request_data['task_run_2_id']))

            task_run_1 = self.db_session.query(TaskRun).filter(TaskRun.id == task_run_1_id).first()
            task_run_2 = self.db_session.query(TaskRun).filter(TaskRun.id == task_run_2_id).first()

            task_run_1_dataframe = pd.DataFrame.from_dict(task_run_1.output['mwas_results'])
            task_run_2_dataframe = pd.DataFrame.from_dict(task_run_2.output['mwas_results'])

            task_run_1_dataframe = self.build_mwas_table(task_run_1_dataframe,fdr_n=fdr_n)
            task_run_1_dataframe = task_run_1_dataframe.sort_values('log_adjusted_pvalues', ascending=True)
            task_run_2_dataframe = self.build_mwas_table(task_run_2_dataframe,fdr_n=fdr_n)
            task_run_2_dataframe = task_run_2_dataframe.sort_values('log_adjusted_pvalues', ascending=True)
            filtered_coefficients = pd.DataFrame(columns=[task_run_1_id, task_run_2_id])

            i = 0
            while i < task_run_1_dataframe.shape[0]:
                # find the corresponding row in the adjusted p-value table
                try:
                    # adjusted_pvalues.loc[adjusted_pvalues['harmonised_annotation_id'] == harmonised_annotation.id].index[0]
                    row_index = task_run_2_dataframe.loc[
                        task_run_2_dataframe.loc[:, 'cpd_id'] == task_run_1_dataframe.loc[i, 'cpd_id']].index[0]
                    filtered_coefficients.loc[i, task_run_1_id] = task_run_1_dataframe.loc[i, 'log_adjusted_pvalues']
                    filtered_coefficients.loc[i, task_run_2_id] = task_run_2_dataframe.loc[row_index, 'log_adjusted_pvalues']

                except:
                    pass

                i = i + 1

            filtered_coefficients = filtered_coefficients.where(pd.notnull(filtered_coefficients), None)
            correlation = filtered_coefficients.astype(float).corr(method='spearman')
            correlation = correlation.iloc[0, 1]
            filtered_coefficients.loc[:, 'harmonised_annotation_id'] = task_run_1_dataframe.loc[:,'harmonised_annotation_id']
            task_run_2_dataframe = task_run_2_dataframe.where(pd.notnull(task_run_2_dataframe), None)
            data = {}
            #data['task_run_2_dataframe'] = task_run_2_dataframe.transpose().to_dict()
            data['correlation'] = correlation
            #data['coefficients'] = filtered_coefficients.to_dict()
            data['mwas_table'] = task_run_2_dataframe.transpose().to_dict()
            template_data = {'mwas_table': task_run_2_dataframe.transpose().to_dict(),'task_run':task_run_2}
            data['task_run_2_table'] = self.render_template('analysis/mwas_table.html', data=template_data)
            data['success'] = True

            #self.logger.debug(json.dumps(data))
            #return jsonify(json.dumps(data))
            self.db_session.close()
            return jsonify(data)
        else:
            self.db_session.close()
            return jsonify({'success':False})

    @expose('/load_multi_task_runs_for_MWAS/', methods=['POST'])
    @has_access
    def load_multi_task_runs_for_MWAS(self):
        request_data = request.get_json()
        self.logger.info("request_data %s" % request_data)
        self.set_db_session(request)
        saved_query_map = {}
        saved_query_names = {}
        task_id_map = {}
        broken_task_runs = {}
        significant_harmonised_annotations = []
        if 'task_run_ids' in request_data.keys():

            task_run_ids = list(map(int, request_data['task_run_ids']))

            fdr_n = None
            if 'fdr_n' in request_data.keys():
                fdr_n = int(float(request_data['fdr_n']))

            order_by_id = None
            if 'taskrun-id-order' in request_data.keys():
                order_by_id = int(float(request_data['taskrun-id-order']))

            show_sig_in_only_one = False
            if 'show-sig-in-only-one'in request_data.keys() and request_data['show-sig-in-only-one'] is True:
                show_sig_in_only_one = True
            self.logger.info('show_sig_in_only_one %s' % show_sig_in_only_one)

            task_runs = self.db_session.query(TaskRun).filter(TaskRun.id.in_(task_run_ids)).all()
            mwas_summary = {}
            mwas_tables = {}
            task_run_dict = {}
            methods = {}
            adjusted_pvalues = pd.DataFrame(columns=['harmonised_annotation_id'])
            adjusted_pvalue_columns = []
            method_saved_query_map = {}
            for task_run in task_runs:
                try:
                    task_run_output = task_run.get_task_output(self.cache)
                    if task_run_output is not None:
                        self.logger.info("TaskRun %s %s %s:" % (task_run.id,task_run.args,task_run_output.keys()))
                    if 'method' in task_run.args.keys():
                        method = task_run.args['method']
                    else:
                        method = 'linear'
                    methods[task_run.id] = method
   #                 if method not in method_saved_query_map.keys():
   #                     method_saved_query_map[method] = {}
   #                 if task_run.saved_query_id not in method_saved_query_map[method].keys():
   #                     method_saved_query_map[task_run.saved_query_id] = []
   #                 method_saved_query_map[task_run.saved_query_id].append(task_run.id)
                    saved_query_map[task_run.id] = task_run.saved_query.id
                    saved_query_names[task_run.saved_query.id] = task_run.saved_query.name
                    task_id_map[task_run.id] = task_run.task_id

                    task_run_dict[task_run.id] = task_run
                    task_run_dataframe = pd.DataFrame.from_dict(task_run_output['mwas_results'])
                    #task_run_dataframe["harmonised_annotation_id"] = None
                    task_run_dataframe["harmonised_annotation_id"] = None
                    task_run_dataframe["assay"] = None
                    task_run_dataframe["annotation_method"] = None
                    task_run_dataframe["cpd_id"] = None
                    task_run_dataframe["cpd_name"] = None
                    task_run_dataframe["aic"] = None

                    if 'tr_%s_adjusted_pvalues' % task_run.id not in adjusted_pvalue_columns:
                        adjusted_pvalue_columns.append('tr_%s_adjusted_pvalues' % task_run.id)
                    if 'tr_%s_pvalues' % task_run.id not in adjusted_pvalue_columns:
                        adjusted_pvalue_columns.append('tr_%s_pvalues' % task_run.id)
                    # recalculate the fdr_n if set
                    if fdr_n is not None and utils.is_number(fdr_n):
                        task_run_dataframe.loc[:, 'adjusted_pvalues'] = task_run_dataframe.loc[:, 'pvalues'] * fdr_n
                    i = 0
                    while i < task_run_dataframe.shape[0]:
                        harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
                            HarmonisedAnnotation.id == int(
                                float(task_run_dataframe.loc[i, "_row"].replace('X', "")))).first()
                        task_run_dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
                        task_run_dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
                        task_run_dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
                        task_run_dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
                        task_run_dataframe.loc[i, "annotation_method"] = "%s" % (
                            harmonised_annotation.annotation_method.name)
                        if method == 'linear' and 'mwas_summaries' in task_run_output.keys():
                            task_run_dataframe.loc[i, "aic"] = task_run_output['mwas_summaries'][task_run_dataframe.loc[i, "_row"]]['aic'][0]
                        # find the corresponding row in the adjusted p-value table
                        try:
                            row_index = adjusted_pvalues.loc[
                                adjusted_pvalues['harmonised_annotation_id'] == harmonised_annotation.id].index[0]
                        except:
                            row_index = len(adjusted_pvalues)
                            adjusted_pvalues.loc[row_index, 'harmonised_annotation_id'] = harmonised_annotation.id

                        adjusted_pvalues.loc[row_index, task_run.id] = task_run_dataframe.loc[i, 'adjusted_pvalues']
                        if task_run_dataframe.loc[i,'adjusted_pvalues'] < 0.05:
                            if harmonised_annotation not in significant_harmonised_annotations:
                                significant_harmonised_annotations.append(harmonised_annotation)

                        i = i + 1
                    task_run_dataframe = task_run_dataframe.set_index('harmonised_annotation_id')

                    task_run_dataframe['sign'] = np.sign(task_run_dataframe["estimates"])
                    task_run_dataframe.loc[:, "log_adjusted_pvalues"] = -1 * task_run_dataframe.loc[:, 'sign'] * np.log10(
                        task_run_dataframe.loc[:, 'adjusted_pvalues'])
                    task_run_dataframe.loc[:, "log_pvalues"] = -1 * task_run_dataframe.loc[:,'sign'] * np.log10(task_run_dataframe.loc[:, 'pvalues'])
                    task_run_dataframe.loc[:, "log_pvalues"] = task_run_dataframe.loc[:,"log_pvalues"].replace(np.inf, 40)
                    task_run_dataframe.loc[:, "log_pvalues"] = task_run_dataframe.loc[:, "log_pvalues"].replace(-np.inf,-40)
                    #task_run_dataframe.loc[:, "log_adjusted_pvalues"] = np.log10( task_run_dataframe.loc[:, 'adjusted_pvalues'])
                    task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:,
                                                                        "log_adjusted_pvalues"].replace(np.inf, 40)
                    task_run_dataframe.loc[:, "log_adjusted_pvalues"] = task_run_dataframe.loc[:,
                                                                        "log_adjusted_pvalues"].replace(-np.inf, -40)

                    mwas_tables[task_run.id] = task_run_dataframe.where(pd.notnull(task_run_dataframe), None)

                    #mwas_summary[task_run.id] =
                    summary = {}
                    summary['n_significant_features'] = len(task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)])
                    mean_values = task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)].mean()
                    summary['mean_significant_pvalue'] = utils.precision_round(mean_values['adjusted_pvalues'],type='str')
                    min_values = task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)].min()
                    summary['min_significant_pvalue'] = utils.precision_round(min_values['adjusted_pvalues'],type='str')
                    max_values = task_run_dataframe[(task_run_dataframe['adjusted_pvalues'] < 0.05)].max()
                    summary['max_significant_pvalue'] = utils.precision_round(max_values['adjusted_pvalues'],type='str')
                    task_data = self.cache.get(task_run.get_task_data_cache_key())
                    sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])
                    summary['n_samples'] = sample_metadata.shape[0]
                    model_Y_variable = task_run.args['model_Y_variable']
                    summary['min_y'] = sample_metadata[model_Y_variable].min()
                    summary['max_y'] = sample_metadata[model_Y_variable].max()
                    summary['n_features'] = pd.DataFrame.from_dict(task_data['feature_metadata']).shape[0]
                    mwas_summary[task_run.id] = summary
                except Exception as err:
                    self.logger.exception(err)
                    self.logger.info("TaskRun failed %s" % task_run.id)
                    broken_task_runs[task_run.id] = str(err)
            adjusted_pvalues = adjusted_pvalues.set_index('harmonised_annotation_id')

            unfiltered_table = pd.DataFrame(
                   columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
            all_indices = adjusted_pvalues.index.to_list()
            i = 0
            while i < len(all_indices):
                harmonised_annotation_id = str(all_indices[i])

                for task_run_id, task_run_dataframe in mwas_tables.items():
                    task_run_label = 'tr_%s' % task_run_id
                    if harmonised_annotation_id in task_run_dataframe.index:
                        mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                        if harmonised_annotation_id not in unfiltered_table.index:
                            row = {}
                            row['harmonised_annotation_id'] = harmonised_annotation_id
                            row['assay'] = mwas_row['assay']
                            row['annotation_method'] = mwas_row['annotation_method']
                            row['cpd_id'] = mwas_row['cpd_id']
                            row['cpd_name'] = mwas_row['cpd_name']
                            unfiltered_table = unfiltered_table.append(pd.Series(row, name=harmonised_annotation_id))
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates"] = utils.precision_round(
                            mwas_row['estimates'])
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_estimates_str"] = utils.precision_round(
                            mwas_row['estimates'], type='str')
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = utils.precision_round(
                            mwas_row['pvalues'])
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_pvalues_str"] = utils.precision_round(
                            mwas_row['pvalues'], type='str')
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_log_pvalues"] = utils.precision_round(
                            mwas_row['log_pvalues'])
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_log_pvalues_str"] = utils.precision_round(
                            mwas_row['log_pvalues'], type='str')
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = utils.precision_round(
                            mwas_row[
                                'adjusted_pvalues'])
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = utils.precision_round(
                            mwas_row['adjusted_pvalues'], type='str')
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = utils.precision_round(
                            mwas_row[
                                'log_adjusted_pvalues'])
                        unfiltered_table.loc[
                            harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = utils.precision_round(
                            mwas_row['log_adjusted_pvalues'], type='str')
                        if methods[task_run_id] == 'linear':
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_aic"] = utils.precision_round(
                                mwas_row['aic'])
                            unfiltered_table.loc[
                                harmonised_annotation_id, task_run_label + "_aic_str"] = utils.precision_round(
                                mwas_row['aic'], type='str')
                    else:
                        if harmonised_annotation_id not in unfiltered_table.index:
                            row = {}
                            harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(HarmonisedAnnotation.id==int(float(harmonised_annotation_id))).first()
                            row['harmonised_annotation_id'] = harmonised_annotation_id
                            row['assay'] = harmonised_annotation.assay.name
                            row['annotation_method'] = harmonised_annotation.annotation_method.name
                            row['cpd_id'] = harmonised_annotation.cpd_id
                            row['cpd_name'] = harmonised_annotation.cpd_name
                            unfiltered_table = unfiltered_table.append(pd.Series(row, name=harmonised_annotation_id))
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_estimates_str"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_pvalues_str"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = None
                        unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = None
                        if methods[task_run_id] == 'linear':
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_aic"] = None
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + "_aic_str"] = None
                i = i + 1

            unfiltered_table = unfiltered_table.where(pd.notnull(unfiltered_table), None)

            significant_in_all_pvalues = adjusted_pvalues[(adjusted_pvalues[adjusted_pvalues.columns] < 0.05).all(axis=1)]
            significant_in_all_table = pd.DataFrame(
                columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
            significant_in_all_index_list = significant_in_all_pvalues.index.to_list()

            i = 0
            while i < len(significant_in_all_index_list):
                harmonised_annotation_id = str(significant_in_all_index_list[i])

                for task_run_id, task_run_dataframe in mwas_tables.items():
                    task_run_label = 'tr_%s' % task_run_id
                    mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()

                    if harmonised_annotation_id not in significant_in_all_table.index:
                        row = {}
                        row['harmonised_annotation_id'] = harmonised_annotation_id
                        row['assay'] = mwas_row['assay']
                        row['annotation_method'] = mwas_row['annotation_method']
                        row['cpd_id'] = mwas_row['cpd_id']
                        row['cpd_name'] = mwas_row['cpd_name']
                        significant_in_all_table = significant_in_all_table.append(pd.Series(row, name=harmonised_annotation_id))

                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_estimates"] = utils.precision_round(mwas_row['estimates'])
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_estimates_str"] = utils.precision_round(
                        mwas_row['estimates'],type='str')
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_pvalues"] = utils.precision_round(mwas_row['pvalues'])
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_pvalues_str"] = utils.precision_round(
                        mwas_row['pvalues'],type='str')
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_log_pvalues"] = utils.precision_round(mwas_row['log_pvalues'])
                    significant_in_all_table.loc[
                        harmonised_annotation_id, task_run_label + "_log_pvalues_str"] = utils.precision_round(
                        mwas_row['log_pvalues'], type='str')
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues"] = utils.precision_round(mwas_row[
                        'adjusted_pvalues'])
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_adjusted_pvalues_str"] = utils.precision_round(
                        mwas_row['adjusted_pvalues'],type='str')
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues"] = utils.precision_round(mwas_row[
                        'log_adjusted_pvalues'])
                    significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_log_adjusted_pvalues_str"] = utils.precision_round(
                        mwas_row['log_adjusted_pvalues'],type='str')
                    if methods[task_run_id] == 'linear':
                        significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_aic"] = utils.precision_round(mwas_row['aic'])
                        significant_in_all_table.loc[harmonised_annotation_id, task_run_label + "_aic_str"] = utils.precision_round(mwas_row['aic'],type='str')

                i = i + 1

            significant_in_all_table = significant_in_all_table.where(pd.notnull(significant_in_all_table), None)

            significant_in_some = adjusted_pvalues[(adjusted_pvalues[adjusted_pvalues.columns] < 0.05).any(axis=1)]
            significant_in_some_and_not_all = significant_in_some[
                (np.isnan(significant_in_some[adjusted_pvalues.columns])).any(axis=1)]

            if show_sig_in_only_one is True:
                significant_in_only_one = {}
                for task_run_id in task_run_ids:
                    significant_in_only_one[task_run_id] = None
                i = 0
                while i < significant_in_some.shape[0]:
                    if significant_in_some.iloc[i, :].isnull().sum() == 1:
                        task_run_id = significant_in_some.iloc[i, :].notnull().index[0]
                        harmonised_annotation_id = str(significant_in_some.index[i])
                        task_run_label = 'tr_%s' % task_run_id
                        adjusted_pvalue = unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_adjusted_pvalues']
                        if adjusted_pvalue is not None and adjusted_pvalue < 0.05:
                            if significant_in_only_one[task_run_id] is None:
                                significant_in_only_one[task_run_id] = pd.DataFrame()
                            if harmonised_annotation_id not in significant_in_only_one[task_run_id].index:
                                row = {}
                                row['harmonised_annotation_id'] = harmonised_annotation_id
                                row['assay'] = unfiltered_table.loc[harmonised_annotation_id, 'assay']
                                row['annotation_method'] = unfiltered_table.loc[harmonised_annotation_id, 'annotation_method']
                                row['cpd_id'] = unfiltered_table.loc[harmonised_annotation_id, 'cpd_id']
                                row['cpd_name'] = unfiltered_table.loc[harmonised_annotation_id, 'cpd_name']
                                row['saved_query_id'] = task_run_dict[task_run_id].saved_query_id
                                row['saved_query_name'] = task_run_dict[task_run_id].saved_query.name
                                significant_in_only_one[task_run_id] = significant_in_only_one[task_run_id].append(
                                    pd.Series(row, name=harmonised_annotation_id))
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "estimates"] = \
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_estimates']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "estimates_str"] = \
                                unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_estimates_str']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "pvalues"] = \
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_pvalues']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "pvalues_str"] = \
                                unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_pvalues_str']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "log_pvalues"] = \
                                unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_log_pvalues']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "log_pvalues_str"] = \
                                unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_log_pvalues_str']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "adjusted_pvalues"] = \
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_adjusted_pvalues']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "adjusted_pvalues_str"] = \
                                unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_adjusted_pvalues_str']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "log_adjusted_pvalues"] = \
                            unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_log_adjusted_pvalues']
                            significant_in_only_one[task_run_id].loc[harmonised_annotation_id, "log_adjusted_pvalues_str"] = \
                                unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_log_adjusted_pvalues_str']

                            if methods[task_run_id] == 'linear':
                                significant_in_only_one[task_run_id].loc[
                                    harmonised_annotation_id, "_aic"] = \
                                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_aic']
                                significant_in_only_one[task_run_id].loc[
                                    harmonised_annotation_id, "_aic_str"] = \
                                    unfiltered_table.loc[harmonised_annotation_id, task_run_label + '_aic_str']

                    i = i + 1

                self.logger.info('significant_in_only_one')
                self.logger.info(significant_in_only_one)

            significant_in_some_and_not_all_dict = {}
            p = 0
            while p < significant_in_some_and_not_all.shape[1]:
                task_run_id = significant_in_some_and_not_all.columns[p]
                significant_rows = significant_in_some_and_not_all.loc[~np.isnan(significant_in_some_and_not_all[task_run_id])]
                    #~np.isnan(significant_in_some_and_not_all[task_run_id] & (significant_in_some_and_not_all[task_run_id] < 0.05))), task_run_id]
                index_list = significant_rows.index.to_list()

                if len(index_list) > 0:

                    significant_in_some_table = pd.DataFrame(
                        columns=['harmonised_annotation_id', 'assay', 'annotation_method', 'cpd_id', 'cpd_name'])
                    i = 0
                    while i < len(index_list):
                        harmonised_annotation_id = str(index_list[i])

                        task_run_dataframe = mwas_tables[task_run_id]
                        mwas_row = task_run_dataframe.loc[harmonised_annotation_id, :].to_dict()
                        if harmonised_annotation_id not in significant_in_some_table.index:
                            row = {}
                            row['harmonised_annotation_id'] = harmonised_annotation_id
                            row['assay'] = mwas_row['assay']
                            row['annotation_method'] = mwas_row['annotation_method']
                            row['cpd_id'] = mwas_row['cpd_id']
                            row['cpd_name'] = mwas_row['cpd_name']
                            significant_in_some_table = significant_in_some_table.append(
                                pd.Series(row, name=harmonised_annotation_id))

                        significant_in_some_table.loc[harmonised_annotation_id, "estimates"] = utils.precision_round(mwas_row['estimates'])
                        significant_in_some_table.loc[harmonised_annotation_id, "pvalues"] = utils.precision_round(mwas_row['pvalues'])
                        significant_in_some_table.loc[harmonised_annotation_id, "log_pvalues"] = utils.precision_round(mwas_row['log_pvalues'])
                        significant_in_some_table.loc[harmonised_annotation_id, "adjusted_pvalues"] = utils.precision_round(mwas_row[
                            'adjusted_pvalues'])
                        significant_in_some_table.loc[harmonised_annotation_id, "log_adjusted_pvalues"] = utils.precision_round(mwas_row[
                            'log_adjusted_pvalues'])
                        if methods[task_run_id] == 'linear':
                            significant_in_some_table.loc[harmonised_annotation_id, "aic"] = utils.precision_round(mwas_row['aic'])

                        i = i + 1

                        #if 'taskrun-metabolite-filter' in request_data.keys() and request_data['taskrun-metabolite-filter'] == 'somenull':
                        #    significant_in_some[significant_in_some[adjusted_pvalue_columns].isnull().any(axis=1)]

                    significant_in_some_and_not_all_dict[task_run_id] = significant_in_some_table

                p = p + 1


            data = {}
            data['n_consistent_features'] = significant_in_all_table.shape[0]
            data['mwas_summary'] = mwas_summary
            data['saved_query_map'] = saved_query_map
            data['task_id_map'] = task_id_map
            data['saved_query_names'] = saved_query_names
            #data['method_saved_query_map'] = method_saved_query_map
            self.logger.info("significant_in_all_table table: %s" % significant_in_all_table)
            self.logger.info(order_by_id)
            all_kegg_ids = []
            if len(significant_harmonised_annotations) > 0:
                for harmonised_annotation in significant_harmonised_annotations:
                    kegg_ids = harmonised_annotation.get_external_ids(db_session=self.db_session,type='KEGG')
                    for kegg_id in kegg_ids:
                        if kegg_id not in all_kegg_ids:
                            all_kegg_ids.append(kegg_id)
            data['all_kegg_ids'] = all_kegg_ids
            data['all_kegg_ids_string'] = "\r\n".join(all_kegg_ids)
            if order_by_id:
                self.logger.info(significant_in_all_table.columns)
                sort_column = 'tr_%s_adjusted_pvalues' % order_by_id
                self.logger.info(sort_column)
                if sort_column in significant_in_all_table.columns:
                    sorted_table = significant_in_all_table.sort_values(by=sort_column)
                    transposed_table = sorted_table.transpose()
                    data['significant_in_all_table'] = transposed_table.to_dict()
            else:
                transposed_table = significant_in_all_table.transpose()
                data['significant_in_all_table'] = transposed_table.to_dict()
            if 'filtered_table' not in data.keys():
                data['filtered_table'] = None

            if 'taskrun-metabolite-filter' in request_data.keys() and request_data['taskrun-metabolite-filter'] == 'somenull':
                unfiltered_table = unfiltered_table[unfiltered_table[adjusted_pvalue_columns].isnull().any(axis=1)]
                self.logger.info("unfiltered table is filtered to show only those that are null in some")

            if order_by_id:
                self.logger.info(unfiltered_table.columns)
                sort_column = 'tr_%s_log_adjusted_pvalues' % order_by_id
                self.logger.info(sort_column)
                if sort_column in unfiltered_table.columns:
                    sorted_table = unfiltered_table.sort_values(by=sort_column)
                    data['metabolite_order'] = sorted_table.index.to_list()
                    self.logger.info("metabolite_order %s" % data['metabolite_order'])
                    transposed_table = sorted_table.transpose()
                    data['unfiltered_table'] = transposed_table.to_dict()
                self.logger.info(unfiltered_table)
            else:
                data['metabolite_order'] = unfiltered_table.index.to_list()
                transposed_table = unfiltered_table.transpose()
                data['unfiltered_table'] = transposed_table.to_dict()

                    #data['filtered_table'] = filtered_table.sort_values(sort_column).transpose().to_dict()
            if 'unfiltered_table' not in data.keys():
                data['unfiltered_table'] = None
            data['task_run_ids'] = request_data['task_run_ids']
            task_labels = []
            task_labels_short = []
            task_saved_query_project_short_labels = []
            for task_run_id in data['task_run_ids']:
                task_run_id = int(float(task_run_id))
                try:
                    task_run_args = task_run_dict[task_run_id].args
                    if 'method' in task_run_args.keys():
                        method = task_run_args['method']
                    else:
                        method = 'linear'
                    task_label = ("%s %s %s %s" % (task_run_id,saved_query_names[saved_query_map[task_run_id]],task_id_map[task_run_id],method)).replace('None ', '')
                    task_labels_short.append(("%s %s %s" % (task_run_id,task_run_dict[task_run_id].saved_query.project_short_label,method)).replace('None ', ''))
                    task_saved_query_project_short_labels.append(task_run_dict[task_run_id].saved_query.project_short_label)
                    if len(task_label) > 30:
                        if len(task_label) > 60:
                            split_length = 30
                        else:
                            split_length = round(len(task_label) / 2)
                        substrings = task_label.split(' ')
                        task_label_rebuilt = ""
                        current_position = 0
                        unbroken_position = 0
                        for substring in substrings:
                            if current_position == 0:
                                task_label_rebuilt = substring
                            else:
                                task_label_rebuilt = task_label_rebuilt + " " + substring
                            reset_broken_position = False
                            if unbroken_position + len(substring) > split_length:
                                task_label_rebuilt = task_label_rebuilt + "<br>"
                                reset_broken_position = True
                            current_position = current_position + len(substring)
                            if reset_broken_position:
                                unbroken_position = 0
                            else:
                                unbroken_position = unbroken_position + len(substring)
                        task_labels.append(task_label_rebuilt)
                    else:
                        task_labels.append(task_label)
                except Exception as err:
                    task_labels.append("%s" % task_run_id)
                    self.logger.exception(err)
            data['task_labels'] = task_labels
            data['task_labels_short'] = task_labels_short
            data['task_saved_query_project_short_labels'] = task_saved_query_project_short_labels
            data['methods'] = methods
            data['table_key'] = 'filtered_table'
            data['significant_in_only_one'] = []
            if show_sig_in_only_one is True:
                for task_run_id, table in significant_in_only_one.items():
                    if table is not None:
                        data['mwas_summary'][task_run.id]['n_sig_only_in_this_cohort'] = table.shape[0]
                        # sort_column = 'tr_%s_log_adjusted_pvalues' % task_run_id
                        sort_column = 'log_adjusted_pvalues'
                        table = table.where(pd.notnull(table), None)
                        self.logger.info("table columns %s" % table.columns)
                        if sort_column in table.columns:
                            self.logger.info('significant_in_only_one %s ordering by %s' % (task_run_id, sort_column))
                            table = table.sort_values(sort_column)
                        template_data = {'mwas_table': table.transpose().to_dict(), 'task_run': task_run_dict[task_run_id]}
                        self.logger.debug('template_data')
                        self.logger.debug(template_data)
                        data['significant_in_only_one'].append(
                            self.render_template('analysis/mwas_table.html', data=template_data))
                    else:
                        data['mwas_summary'][task_run.id]['n_sig_only_in_this_cohort'] = 0
            data['mwas_consistent_table'] = self.render_template('analysis/mwas_table_multi.html', data=data)
            data['table_key'] = 'unfiltered_table'
            data['mwas_unfiltered_table'] = self.render_template('analysis/mwas_table_multi.html', data=data)
            if 'show-sig-in-some-not-all' in request_data.keys():
                show_sig_in_some = request_data['show-sig-in-some-not-all']
            else:
                show_sig_in_some = False
            if show_sig_in_some:
                data['mwas_significant_in_some_but_not_all_tables'] = []
                for task_run_id, mwas_dict in significant_in_some_and_not_all_dict.items():
                    template_data = {'mwas_table': mwas_dict, 'task_run': task_run_dict[task_run_id]}
                    data['mwas_significant_in_some_but_not_all_tables'].append(self.render_template('analysis/mwas_table.html', data=template_data))
            #self.logger.debug(data)
            data['broken_task_runs'] = broken_task_runs
            data['success'] = True
            self.db_session.close()
            return jsonify(data)
        else:
            self.db_session.close()
            return jsonify({'success': False})

    def build_mwas_table(self, dataframe,mwas_summaries=None,fdr_n=None,for_display=False):

        unique_kegg_ids = []

        dataframe["harmonised_annotation_id"] = None
        dataframe["assay"] = None
        dataframe["annotation_method"] = None
        dataframe["cpd_id"] = None
        dataframe["cpd_name"] = None
        dataframe['sign'] = np.sign(dataframe["estimates"])
        dataframe['opposite_sign'] = None
        dataframe['kegg_ids'] = None
        if fdr_n is not None and utils.is_number(fdr_n):
            dataframe.loc[:, 'adjusted_pvalues'] = dataframe.loc[:, 'pvalues'] * fdr_n
        i = 0
        while i < dataframe.shape[0]:
            harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
                HarmonisedAnnotation.id == int(float(dataframe.loc[i, "_row"].replace('X', "")))).first()
            dataframe.loc[i, "harmonised_annotation_id"] = "%s" % (harmonised_annotation.id)
            dataframe.loc[i, "cpd_id"] = "%s" % (harmonised_annotation.cpd_id)
            dataframe.loc[i, "cpd_name"] = "%s" % (harmonised_annotation.cpd_name)
            dataframe.loc[i, "assay"] = "%s" % (harmonised_annotation.assay.name)
            dataframe.loc[i, "annotation_method"] = "%s" % (harmonised_annotation.annotation_method.name)
            if mwas_summaries is not None:
                dataframe.loc[i, "aic"] = mwas_summaries[dataframe.loc[i, "_row"]]['aic'][0]

            if dataframe.loc[i,'sign'] < 0:
                dataframe.loc[i,'opposite_sign'] = 1
            else:
                dataframe.loc[i, 'opposite_sign'] = -1
            if for_display and dataframe.loc[i, 'adjusted_pvalues'] < 0.05:
                kegg_ids = harmonised_annotation.get_external_ids(db_session=self.db_session, type='KEGG')
                dataframe.loc[i, 'kegg_ids'] = ",".join(kegg_ids)
                if len(kegg_ids) > 0:
                    for kegg_id in kegg_ids:
                        if kegg_id not in unique_kegg_ids:
                            unique_kegg_ids.append(kegg_id)
                self.logger.info('kegg_ids %s' % kegg_ids)

            i = i + 1

        dataframe.loc[:,"log_adjusted_pvalues"] = dataframe.loc[:,'opposite_sign'] * np.log10(dataframe.loc[:,'adjusted_pvalues'])
        dataframe.loc[:,"log_adjusted_pvalues"] = dataframe.loc[:,"log_adjusted_pvalues"].replace(np.inf, 40)
        dataframe.loc[:,"log_adjusted_pvalues"] = dataframe.loc[:,"log_adjusted_pvalues"].replace(-np.inf, -40)

        i = 0
        while i < dataframe.shape[0]:
            try:
                if not pd.isnull(dataframe.loc[i, "adjusted_pvalues"]):
                    dataframe.loc[i, "adjusted_pvalues"] = utils.precision_round(dataframe.loc[i, "adjusted_pvalues"])
                    dataframe.loc[i, "adjusted_pvalues_str"] = utils.precision_round(dataframe.loc[i, "adjusted_pvalues"],type='str')
                    dataframe.loc[i, "pvalues"] = utils.precision_round(dataframe.loc[i, "pvalues"])
                    dataframe.loc[i, "pvalues_str"] = utils.precision_round(dataframe.loc[i, "pvalues"],type='str')
                    dataframe.loc[i, "log_pvalues"] = utils.precision_round(-np.log10(dataframe.loc[i, 'pvalues']))
                    dataframe.loc[i, "log_pvalues_str"] = utils.precision_round(dataframe.loc[i, "log_pvalues"], type='str')
                    dataframe.loc[i, "estimates"] = utils.precision_round(dataframe.loc[i, "estimates"])
                    dataframe.loc[i, "estimates_str"] = utils.precision_round(dataframe.loc[i, "estimates"],type='str')
                    dataframe.loc[i, "log_adjusted_pvalues"] = utils.precision_round(dataframe.loc[i, "log_adjusted_pvalues"])
                    dataframe.loc[i, "log_adjusted_pvalues_str"] = utils.precision_round(
                        dataframe.loc[i, "log_adjusted_pvalues"],type='str')
                    if mwas_summaries is not None:
                        dataframe.loc[i, "aic"] = utils.precision_round(dataframe.loc[i, "aic"])
                        dataframe.loc[i, "aic_str"] = utils.precision_round(dataframe.loc[i, "aic"],type='str')
                else:
                    dataframe.loc[i, "adjusted_pvalues"] = 1
                    dataframe.loc[i, "pvalues"] = 1
                    dataframe.loc[i, "estimates"] = 0
                    dataframe.loc[i, "log_adjusted_pvalues"] = 0
                    dataframe.loc[i, "log_pvalues"] = 0
                    dataframe.loc[i, "adjusted_pvalues_str"] = '1'
                    dataframe.loc[i, "pvalues_str"] = '1'
                    dataframe.loc[i, "log_pvalues_str"] = '0'
                    dataframe.loc[i, "estimates_str"] = '0'
                    dataframe.loc[i, "log_adjusted_pvalues_str"] = '0'
                    if mwas_summaries is not None:
                        dataframe.loc[i, "aic"] = 0
                        dataframe.loc[i, "aic_str"] = '0'
            except Exception as err:
                self.logger.exception(err)
                self.logger.debug(dataframe.loc[i])
                raise Exception(err)
            i = i + 1

        #self.unique_kegg_ids = list(unique_kegg_ids)
        self.unique_kegg_ids.extend(kegg_id for kegg_id in unique_kegg_ids if kegg_id not in self.unique_kegg_ids)

        return dataframe.where(pd.notnull(dataframe), None)

    @expose('/load_features_for_MWAS_validation_plot', methods=['POST'])
    def load_features_for_MWAS_validation_plot(self):
        request_data = request.get_json()
        self.set_db_session(request)
        data = {}
        hardcoded_bmi_classes = ['(18.5, 25.0]','(25.0, 30.0]']
        if 'task_run_id' in request_data.keys() and 'harmonised_annotation_id' in request_data.keys():
            harmonised_annotation_id = request_data['harmonised_annotation_id']
            harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
                HarmonisedAnnotation.id == int(float(harmonised_annotation_id))).first()
            task_run = self.db_session.query(TaskRun).filter(TaskRun.id == int(float(request_data['task_run_id']))).first()
            task_data = self.cache.get(task_run.get_task_data_cache_key())
            task_run_output = task_run.get_task_output(self.cache)
            feature_metadata = pd.DataFrame.from_dict(task_data['feature_metadata'])
            sample_metadata = pd.DataFrame.from_dict(task_data['sample_metadata'])
            model_y_variable = task_run.args['model_Y_variable']
            feature_row = int(feature_metadata.loc[feature_metadata.loc[:, 'harmonised_annotation_id'] == int(
                harmonised_annotation_id)].index[0])
           # if 'mwas_estimates' in task_run_output.keys() and 'mwas_summaries' in task_run_output.keys():
           #     data['feature_estimates'] = task_run_output['mwas_estimates'][("X%s" % harmonised_annotation_id)]
           #     data['feature_summary'] = task_run_output['mwas_summaries'][("X%s" % harmonised_annotation_id)]
            intensity_data = np.matrix(task_data['intensity_data'])
            output_dataframe = pd.DataFrame(columns=['Y', 'feature intensity'])
            #output_dataframe = output_dataframe.where(pd.notnull(output_dataframe), None)
            self.logger.debug('TaskRun.arg keys %s' % task_run.args.keys())
            y_axis_label = ''
            if 'scaling' in task_run.args.keys() and task_run.args['scaling'] != None:
                y_axis_label = y_axis_label + " " + task_run.args['scaling']
            if 'transform' in task_run.args.keys() and task_run.args['transform'] != None:
                y_axis_label = y_axis_label + " " + task_run.args['transform']
            data['y_axis_label'] = y_axis_label + " " + harmonised_annotation.cpd_name + " intensity"
            data['saved_query_name'] = task_run.saved_query.name
            data['cpd_id'] = harmonised_annotation.cpd_id
            data['task_run_id'] = str(task_run.id)
            data['cpd_name'] = harmonised_annotation.cpd_name
            data['Y_label'] = model_y_variable
            data['X_labels'] = task_run.args['model_X_variables']
            output_dataframe.loc[:, 'Y'] = sample_metadata.loc[:, model_y_variable].astype(float)
            output_dataframe.loc[:,'project'] = sample_metadata.loc[:, 'Project']
            output_dataframe.loc[:, 'feature intensity'] = intensity_data[:, feature_row]
            output_dataframe = output_dataframe.where(pd.notnull(output_dataframe), None)
            #output_dataframe = output_dataframe.sort_values("Y")
            # main plot (no separation)
            data['std'] = output_dataframe.groupby("Y").apply(np.std).transpose().to_dict()
            #data['median'] = output_dataframe.groupby("Y").apply(np.median).transpose().to_dict()
            data['mean'] = output_dataframe.groupby("Y").apply(np.mean).transpose().to_dict()
            data['Y_intensity'] = output_dataframe.sort_values("Y").transpose().to_dict()
            if 'model_X_variables' in task_run.args.keys():
                model_x_variables = list(task_run.args['model_X_variables'])
            else:
                model_x_variables = []
            grouped_data = {}
            harmonised_metadata_fields = {}
            X_variables_to_plot = []
            X_variables_to_plot = []
            for model_x_variable in model_x_variables:
                if re.search('h_metadata::', model_x_variable):
                    X_variables_to_plot.append(model_x_variable)
            # Individual plots (seperated by 1 metadata field)
            for model_x_variable in X_variables_to_plot:
                self.logger.info("model_x_variable: %s" % model_x_variable)

                grouped_data[model_x_variable] = {}
                output_dataframe.loc[:, model_x_variable] = sample_metadata.loc[:, model_x_variable]
                harmonised_metadata_fields[model_x_variable] = self.db_session.query(HarmonisedMetadataField).filter(
                    HarmonisedMetadataField.name == model_x_variable.replace("h_metadata::", "")).first()
                self.logger.info(harmonised_metadata_fields)
                try:
                    if harmonised_metadata_fields[model_x_variable].datatype in [
                        HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric,
                        HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric.value] \
                            and harmonised_metadata_fields[model_x_variable].classes is not None:
                        class_column = model_x_variable + "_class"
                        output_dataframe[class_column] = pd.cut(output_dataframe.loc[:, model_x_variable],
                                                                [float("-inf")] + harmonised_metadata_fields[model_x_variable].classes + [
                                                                    float("inf")],
                                                                include_lowest=True).astype('str')
                    else:
                        class_column = model_x_variable
                    if class_column != model_y_variable:
                        for group in output_dataframe[class_column].unique():
                            if group != 'nan' and group is not None:
                                # if((model_x_variable != 'h_metadata::BMI') or (group in hardcoded_bmi_classes)):
                                grouped_data[model_x_variable][group] = {}
                                filtered_dataframe = output_dataframe[output_dataframe[class_column] == group].dropna(
                                    axis=0)
                                # filtered_dataframe['Y'] = filtered_dataframe['Y'].astype(float)
                                grouped_data[model_x_variable][group]['std'] = filtered_dataframe.groupby("Y").apply(
                                    np.std).transpose().to_dict()
                                grouped_data[model_x_variable][group]['mean'] = filtered_dataframe.groupby("Y").apply(
                                    np.mean).transpose().to_dict()
                                # grouped_data[model_x_variable][group]['median'] = filtered_dataframe.groupby("Y").apply(
                                #    np.median).transpose().to_dict()
                                grouped_data[model_x_variable][group][
                                    'Y_intensities'] = filtered_dataframe.transpose().to_dict()

                except Exception as err:
                    self.logger.exception(err)
                    self.logger.debug(model_x_variable)
                    self.logger.debug(harmonised_metadata_fields)
                    raise err

            # Seperate plots (seperated by 2 metadata fields)
            seperate_plot_variables = []
            self.logger.debug(X_variables_to_plot)
            self.logger.debug(model_y_variable)
            if len(X_variables_to_plot) > 1:
                i = 0
                while i < len(X_variables_to_plot):
                    if X_variables_to_plot[i] != model_y_variable:
                        seperate_plot_variables.append(i)
                    i = i + 1
                self.logger.debug(seperate_plot_variables)
                i = 0
                while (i + 1) < len(seperate_plot_variables):
                    var_one = X_variables_to_plot[seperate_plot_variables[i]]
                    var_two = X_variables_to_plot[seperate_plot_variables[i + 1]]
                    combined_key = var_one + ":" + var_two
                    grouped_data[combined_key] = {}
                    if harmonised_metadata_fields[var_one].datatype in [
                        HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric,
                        HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric.value] and harmonised_metadata_fields[var_one].classes is not None:
                        var_one_class_column = var_one + "_class"
                    else:
                        var_one_class_column = var_one
                    if harmonised_metadata_fields[var_two].datatype in [
                        HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric,
                        HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric.value] and harmonised_metadata_fields[var_two].classes is not None:
                        var_two_class_column = var_two + "_class"
                    else:
                        var_two_class_column = var_two
                    var_one_groups = output_dataframe[var_one_class_column].unique()
                    var_two_groups = output_dataframe[var_two_class_column].unique()
                    for var_one_group in var_one_groups:
                        if var_one_group != 'nan' and var_one_group is not None:
                            if ((var_one != 'h_metadata::BMI') or (var_one_group in hardcoded_bmi_classes)):
                                for var_two_group in var_two_groups:
                                    if var_two_group != 'nan' and var_two_group is not None:
                                        if ((var_two != 'h_metadata::BMI') or (var_two_group in hardcoded_bmi_classes)):
                                            group_key = str(var_one_group) + ":" + str(var_two_group)
                                            grouped_data[combined_key][group_key] = {}
                                            filtered_dataframe = output_dataframe[
                                                (output_dataframe[var_one_class_column] == var_one_group) & (
                                                            output_dataframe[var_two_class_column] == var_two_group)].dropna(axis=0)
                                            grouped_data[combined_key][group_key]['std'] = filtered_dataframe.groupby("Y").apply(
                                                np.std).transpose().to_dict()
                                            grouped_data[combined_key][group_key]['mean'] = filtered_dataframe.groupby("Y").apply(
                                                np.mean).transpose().to_dict()
                                            grouped_data[combined_key][group_key][
                                                'Y_intensities'] = filtered_dataframe.transpose().to_dict()

                    i = i + 2

            data['grouped_data'] = grouped_data
            data['Y_range'] = [output_dataframe.loc[:,'Y'].min() - 1,output_dataframe.loc[:, 'Y'].max() + 1]
            data['intensity_range'] = [output_dataframe.loc[:, 'feature intensity'].min() - 0.1, output_dataframe.loc[:, 'feature intensity'].max() + 0.1]
            data['success'] = True
            #self.logger.info("data: %s" % data)
            self.db_session.close()
            return jsonify(data)
        else:
            return jsonify({"success":False})

    @expose('/delete_task_run/<id>',methods=['GET'])
    def delete_task_run(self,id):
        self.set_db_session(request)

        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(float(id))).first()
        if self.cache.exists(task_run.get_task_data_cache_key()):
            self.cache.delete(task_run.get_task_data_cache_key())
        # delete the airflow logs
        self.db_session.query(TaskRun).filter(TaskRun.id == int(float(id))).delete()

        self.db_session.commit()
        flash('TaskRun deleted! %s' % id)
        self.db_session.close()
        return redirect(url_for(".list"))

    @expose('/download_feature_metadata')
    def download_feature_metadata(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args:
            task_run_id = request.args.get('id')
            if utils.is_number(task_run_id):
                task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(task_run_id)).first()
                if task_run and task_run.args and 'feature_metadata' in task_run.args:
                    if not os.path.exists('/tmp/phenomedb/'):
                        os.makedirs('/tmp/phenomedb/')
                    feature_metadata_csv_path = '/tmp/phenomedb/task_run_' + str(task_run.id) + '_feature_metadata.csv'
                    df = pd.DataFrame.from_dict(task_run.args['feature_metadata'])
                    df.to_csv(feature_metadata_csv_path,index=None)
                    print(feature_metadata_csv_path)
                    self.db_session.close()
                    if os.path.exists(feature_metadata_csv_path):
                        return send_file(feature_metadata_csv_path, as_attachment=True)
                    else:
                        raise Exception("Expected file does not exist! %s" % feature_metadata_csv_path)
                else:
                    raise Exception("No task_run with id: " + str(task_run))

        self.db_session.close()

    @expose('/download_sample_metadata')
    def download_sample_metadata(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args:
            task_run_id = request.args.get('id')
            if utils.is_number(task_run_id):
                task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(task_run_id)).first()
                if task_run and task_run.args and 'sample_metadata' in task_run.args:
                    if not os.path.exists('/tmp/phenomedb/'):
                        os.makedirs('/tmp/phenomedb/')
                    sample_metadata_csv_path = '/tmp/phenomedb/task_run_' + str(task_run.id) + '_sample_metadata.csv'
                    df = pd.DataFrame.from_dict(task_run.args['sample_metadata'])
                    df.to_csv(sample_metadata_csv_path,index=None)
                    self.db_session.close()
                    if os.path.exists(sample_metadata_csv_path):
                        return send_file(sample_metadata_csv_path, as_attachment=True)
                    else:
                        raise Exception("Expected file does not exist! %s" % sample_metadata_csv_path)
                else:
                    raise Exception("No task_run with id: " + str(task_run))

        self.db_session.close()

    @expose('/download_intensity_data')
    def download_intensity_data(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args:
            task_run_id = request.args.get('id')
            if utils.is_number(task_run_id):
                task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(task_run_id)).first()
                if task_run and task_run.args and 'intensity_data' in task_run.args:
                    if not os.path.exists('/tmp/phenomedb/'):
                        os.makedirs('/tmp/phenomedb/')
                    intensity_data_csv_path = '/tmp/phenomedb/task_run_' + str(task_run.id) + '_intensity_data.csv'
                    df = pd.DataFrame(np.matrix(task_run.args['intensity_data']))
                    df.to_csv(intensity_data_csv_path,index=None)
                    self.db_session.close()
                    if os.path.exists(intensity_data_csv_path):
                        return send_file(intensity_data_csv_path, as_attachment=True)
                    else:
                        raise Exception("Expected file does not exist! %s" % intensity_data_csv_path)
                else:
                    raise Exception("No task_run with id: " + str(task_run))

    @expose('/download_results')
    def download_results(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args:
            task_run_id = request.args.get('id')
            if utils.is_number(task_run_id):
                task_run = self.db_session.query(TaskRun).filter(TaskRun.id==int(task_run_id)).first()
                task_run_output = task_run.get_task_output(self.cache)
                if task_run and task_run_output:
                    if not os.path.exists('/tmp/phenomedb/'):
                        os.makedirs('/tmp/phenomedb/')
                    results_json_path = '/tmp/phenomedb/task_run_' + str(task_run.id) + '_results.json'
                    f = open(results_json_path,'w')
                    f.write(json.dumps(task_run_output))
                    f.close()
                    self.db_session.close()
                    if os.path.exists(results_json_path):
                        return send_file(results_json_path, as_attachment=True)
                    else:
                        raise Exception("Expected file does not exist! %s" % results_json_path)
                else:
                    raise Exception("No task_run with id: " + str(task_run))

    @expose('/download_task_run_data')
    def download_task_run_data(self):

        self.set_db_session(request)
        self.logger.debug(request.args)
        data = {}
        if 'id' in request.args and 'task_run_data_type' in request.args and 'property' in request.args and 'format' in request.args:
            task_run_id = request.args.get('id')
            task_run_data_type = request.args.get('task_run_data_type')
            property = request.args.get('property')
            format = request.args.get('format')
            if task_run_data_type not in ['args', 'data', 'output']:
                raise Exception("Unknown task_run_datatype %s must be one of %s" % (task_run_data_type, ['args', 'data', 'output']))

            if utils.is_number(task_run_id):
                task_run = self.db_session.query(TaskRun).filter(TaskRun.id == int(task_run_id)).first()
                if task_run:
                    task_run_output = task_run.get_task_output(self.cache)
                    if not os.path.exists('/tmp/phenomedb/'):
                        os.makedirs('/tmp/phenomedb/')
                    filepath = '/tmp/phenomedb/task_run_%s_%s_%s.csv' % (task_run.id, task_run_data_type,property)

                    if task_run_data_type == 'data':
                        if not self.cache.exists(task_run.get_task_data_cache_key()):
                            raise Exception("Cache does not exist - please reload page!")
                        data_dict = self.cache.get(task_run.get_task_data_cache_key())
                    elif task_run_data_type == 'args' and task_run.args is not None:
                        data_dict = dict(task_run.args)
                    elif task_run_data_type == 'output' and task_run_output is not None:
                        data_dict = dict(task_run_output)
                    else:
                        data_dict = {}
                    self.logger.debug(type(data_dict))
                    self.logger.debug(data_dict.keys())

                    if property in ['sample_metadata','feature_metadata','intensity_data']:
                        if property in data_dict:
                            data = data_dict[property]
                        else:
                            raise Exception("Unexpected field")
                        if format == 'table' and re.search('intensity_data', property) and isinstance(data, list):
                            df = pd.DataFrame(np.matrix(data))
                            df.to_csv(filepath, header=None, index=None)
                        elif format == 'table':
                            df = pd.DataFrame.from_dict(data)
                            df.to_csv(filepath, index=None)

                    elif property == 'combined':
                        if 'sample_metadata' in data_dict.keys() \
                                and 'feature_metadata' in data_dict.keys() \
                                and 'intensity_data' in data_dict.keys():
                            intensity_data = np.matrix(data_dict['intensity_data'])
                            feature_metadata = pd.DataFrame.from_dict(data_dict['feature_metadata'])
                            sample_metadata = pd.DataFrame.from_dict(data_dict['sample_metadata'])
                        else:
                            raise Exception("Necessary fields do not exist")

                        df = utils.build_combined_dataframe_from_seperate(intensity_data,sample_metadata,feature_metadata)
                        df.to_csv(filepath, index=None)

                    print(filepath)
                    self.db_session.close()
                    if os.path.exists(filepath):
                        return send_file(filepath, as_attachment=True)
                    else:
                        raise Exception("Expected file does not exist! %s" % filepath)
                else:
                    raise Exception("No task_run with id: " + str(task_run))

        self.db_session.close()



analysis_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder='../templates',
    static_folder='../templates/static',
    static_url_path='/static/phenomedb')

#compound_view = CompoundView(category="PhenomeDB", name="Compounds")

v_appbuilder_view = AnalysisView()
v_appbuilder_package = {"name": "Analysis",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}

#appbuilder_mitem = {"name": "Analysis",
#                    "category": "PhenomeDB",
#                    "category_icon": "fa-th",
#                    "href": "/analysis/"}

appbuilder_mitems = {"name": "PhenomeDB docs",
                    "category": "Docs",
                    "category_icon": "fa-th",
                    "href": "https://phenomedb.readthedocs.io/"}

class AnalysisPlugin(AirflowPlugin):

    name = VIEW_NAME

    # flask_blueprints and admin_views are AirflowPlugin properties
    flask_blueprints = [analysis_bp]
    #admin_views = [compound_view]
    #admin_views = []
    appbuilder_views = [v_appbuilder_package]
#    appbuilder_menu_items = [appbuilder_mitem]
