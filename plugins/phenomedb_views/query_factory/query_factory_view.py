import os, sys, json, logging
from werkzeug.utils import secure_filename
from flask import Blueprint, flash, request, jsonify, make_response, redirect, url_for, render_template_string,session
from flask_appbuilder import expose, has_access
from dateutil import parser
import datetime
#from flask_appbuilder.security.sqla.models import User

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config
from sqlalchemy import inspect
from phenomedb.models import *
from phenomedb.base_view import *
from nPYc.enumerations import *
import re

from phenomedb.query_factory import QueryFactory,MetadataFilter,QuerySubFilter,QueryFilter
from flask import send_file

from jinja2 import Template
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.properties import ColumnProperty
# this is only Airflow specific part:
from airflow.plugins_manager import AirflowPlugin

VIEW_NAME = "query_factory"

class QueryFactoryView(PhenomeDBBaseView):

    model_table_map = {
        'Compound':'compound',
        'CompoundClass': 'compound_class',
        'CompoundAssay': 'compound_assay',
        "CompoundExternalDB": "compound_external_db",
        "ExternalDB": "external_db",
        "Annotation": "annotation"
    }

    def __init__(self):
        super().__init__()
        self.configure_logging()

    # holder for external dbs with cts; wait to initialize
    g_cts_lookups = None

    @expose('/')
    @has_access
    def list(self):
        return self.render_template(
            "query_factory/saved_queries.html", data={})

    @expose('/projectsummaries')
    @has_access
    def project_summaries(self):

        return self.render_template(
            "query_factory/project_summaries.html")

    @expose('/table/json/')
    @has_access
    def get_table_json(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.set_db_session(request)
        json_data = json.dumps({"data":[[""]], "columns":[""]})
        try:
            if 'project_summaries' in request.args:
                df = self.get_project_summary_table()
            else:
                df = self.get_saved_queries()
            # make a link out of the display name column
            if not df.empty:

                if 'name' in df.columns:
                    df['name'] = [
                        ''.join(['<a href="' + url_for("QueryFactoryView.advanced_saved_query_editor") + '?id=', str(x),'"/>', y, '</a>']) for x, y in zip(df['id'], df['name'])]
                if 'json' in df.columns:
                    df['json'] = [ str(x) for x in df['json']]

                json_data = df.to_json(orient="split")

        except Exception as e: #this happens, be graceful
            error_msg = getattr(e, 'message', repr(e))
            self.logger.debug(str(e))
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]})

        d = json.loads(json_data)["data"]
        c = json.loads(json_data)["columns"]

        self.db_session.close()
        # response is formatted for display in a DataTable:
        return make_response(jsonify(table_data = d, columns = [{"title": str(col)} for col in c]))

    def get_project_summary_table(self):

        df = None
        try:
            df = self.sql_to_dataframe("select p.name as project, s.sample_matrix, a.name as assay,s.sample_type, count(s.id) as sample_counts from project p inner join subject su on su.project_id = p.id inner join sample s on su.id = s.subject_id inner join sample_assay sa on s.id = sa.sample_id inner join assay a on a.id = sa.assay_id group by p.name,s.sample_matrix,s.sample_type,a.name order by p.name,s.sample_matrix,a.name,s.sample_type")
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df

    def get_saved_queries(self):
        """
        Fetch compounds plus a count of related datasets
        :return: result as a pandas dataframe
        """
        df = None
        try:

            df = self.sql_to_dataframe("select * from saved_query")
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df

    @expose('/edit/', methods=["GET"])
    @has_access
    def advanced_saved_query_editor(self):

        self.set_db_session(request)
        data = {}

        data['match_model_options'] = self.get_all_filter_fields()
        data['units'] = self.db_session.query(Unit).all()
        data['models'] = {}
        if 'id' in request.args:
            saved_query_id = request.args.get('id')
            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                if saved_query:
                    saved_query.load_query_dict_for_view()
                    data['saved_query'] = saved_query
                    query_factory = QueryFactory(saved_query=saved_query)
                    self.logger.info(saved_query.cache_state)
                    if not saved_query.cache_state:
                        saved_query.cache_state = {}
                    data['annotated_feature_cache_raw'] = False
                    data['annotated_feature_cache_sr_corrected'] = False
                    data['annotated_feature_cache_ltr_corrected'] = False
                    for key in saved_query.cache_state.keys():
                        #if not self.cache.exists(saved_query.get_cache_dataframe_key(key)) and cache_state[key] == 'exists':
                        #    del cache_state[key]

                        if re.search("combined::AnnotatedFeature", key) and key in saved_query.cache_state.keys():
                            if re.search("SR",key) and key in saved_query.cache_state.keys():
                                data['annotated_feature_cache_sr_corrected'] = saved_query.cache_state[key]
                            elif re.search("LTR", key) and key in saved_query.cache_state.keys():
                                data['annotated_feature_cache_ltr_corrected'] = saved_query.cache_state[key]
                            else:
                                data['annotated_feature_cache_raw'] = saved_query.cache_state[key]

                    #saved_query.cache_state = cache_state

                    #self.db_session.commit()
                    data['harmonised_metadata_fields'] = self.db_session.query(HarmonisedMetadataField).all()
                    data['external_dbs'] = self.db_session.query(ExternalDB).all()
                    data['task_runs_with_output'] = self.db_session.query(TaskRun).filter(TaskRun.saved_query_id==saved_query.id)\
                        .filter(TaskRun.module_name=='phenomedb.batch_correction') \
                        .filter(TaskRun.status == TaskRun.Status.success) \
                        .all()


                else:
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        template = self.render_template(
            "query_factory/advanced_saved_query_editor.html", data=data)
        self.db_session.close()
        return template

    def get_all_filter_fields(self):
        """
            get all the filter field options
        :return:
        """

        field_options = {}
        for model in SavedQuery.registry._class_registry.values():

            if hasattr(model, '__tablename__'):
                field_options[model.__name__] = {}
                mapper = inspect(model)
                for column in model.__table__.columns:
                    field_options[model.__name__][column.name] = column.type

        return field_options

    @expose('/get_filter_html')
    @has_access
    def get_saved_query_filter_html(self):

        self.set_db_session(request)
        data = {}

        data['match_model_options'] = self.get_all_filter_fields()

        self.db_session.close()
        return self.render_template(
            "query_factory/filter.html",data=data)

    @expose('/get_saved_query_subfilter_html')
    @has_access
    def get_saved_query_subfilter_html(self):

        self.set_db_session(request)
        data = {}

        data['match_model_options'] = self.get_all_filter_fields()

        self.db_session.close()
        return self.render_template(
            "query_factory/sub_filter.html",data=data)

    @expose('/get_match_html')
    @has_access
    def get_saved_query_match_html(self):

        self.set_db_session(request)
        data = {}

        data['match_model_options'] = self.get_all_filter_fields()

        self.db_session.close()
        return self.render_template(
            "query_factory/match.html",data=data)

    @expose('/save_query',methods=["POST"])
    @has_access
    def save_query(self):

        self.set_db_session(request)
        data = {}
        try:

            print(request.form)
            self.logger.debug(request.form)

            saved_query_id = request.form['saved_query_id']
            role_id = request.form['role_id']
            if str(role_id) == '0':
                role_id = None

            name = request.form['name']
            description = request.form['description']
            project_short_label = request.form['project_short_label']
            type = request.form['type']

            if name == '':
                raise Exception("A suitable name must be set")
            if description == '':
                raise Exception("A suitable description must be set")

            filters = self.parse_filters(request.form)

            if utils.is_number(saved_query_id):
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
            elif saved_query_id == 'copy':
                name = name + "_copy"
                description = description + "_copy"
                saved_query_id = None
            else:
                saved_query_id = None

            self.logger.info("Filters: %s" % filters)

            query_factory = QueryFactory(saved_query_id=saved_query_id,filters=filters,query_name=name,project_short_label=project_short_label,
                                               role_id=role_id,query_description=description,db_session=self.db_session)
            saved_query = query_factory.save_query(type=type)

            saved_query_id = saved_query.id
            flash('Query Saved!')
            query_factory.delete_cache()

            return jsonify(saved_query_id=saved_query_id)

        except Exception as err:
            self.logger.exception(err)
            self.db_session.rollback()
            flash(str(err))
            data['error'] = str(err)

            self.db_session.close()
            return jsonify(error=str(err))

    def parse_filters(self,form):

        filters = json.loads(form['filters'])

        self.logger.debug("Request filters %s", filters)

        for filter in filters:
            if not filter:
                continue
            for sub_filter in filter['sub_filters']:
                for match in sub_filter['matches']:
                    self.logger.debug('match value: ' + str(match['value']) + " " + str(type(match['value'])))

                    if match['value'] == '':
                        raise Exception("Filter match value empty - " + str(match))
                    if match['property'] == '':
                        raise Exception("Operator not selected" + str(match))
                    if match['operator'] == '':
                        raise Exception("Operator not selected" + str(match))
                    if match['model'] == '':
                        raise Exception("Model not selected" + str(match))
                    if match['datatype'] == '':
                        raise Exception("Datatype not set" + str(match))

                    if isinstance(match['value'],list):
                        self.logger.debug("list detected")
                        for value in match['value']:
                            value = self.parse_value(value,match['datatype'])

                    elif (re.search(r',',match['value']) and match['property'] != 'inchi') or match['operator'] in ['in','not_in']:
                        match['value'] = match['value'].split(",")
                        self.logger.debug("csv detected - converted to list")

                        for value in match['value']:
                            value = self.parse_value(value,match['datatype'])

                    else:
                        match['value'] = self.parse_value(match['value'],match['datatype'])

        self.logger.debug("Parsed filters %s", filters)

        return filters

    def parse_value(self,value,datatype):

        self.logger.debug("Parsing value: " + str(value) + " - " +str(datatype))

        if datatype in ["VARCHAR",'text']:
            return str(value)

        elif datatype in ["FLOAT","INTEGER",'numeric'] and utils.is_number(value):
            if utils.isint(value):
                return int(value)
            else:
                return float(value)

        elif datatype in ["FLOAT","INTEGER",'numeric'] and not utils.is_number(value):
            raise Exception("Datatype is " + datatype + ", value cannot be " + str(value))

        elif datatype in ['DATETIME','datetime']:
            parsed_value = parser.parse(value)

            if not isinstance(parsed_value,datetime.datetime):
                raise Exception('Datetime unrecognised')

        else:
            return value

    @expose('/get_summary',methods=["POST"])
    def get_summary(self):

        self.set_db_session(request)
        try:
            saved_query_id = request.form['saved_query_id']
            data = {}

            filters = self.parse_filters(request.form)

            if utils.is_number(saved_query_id):
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
            else:
                saved_query = None

            saved_query_factory = QueryFactory(saved_query=saved_query,filters=filters,db_session=self.db_session)
            data['saved_query_summary_stats'] = saved_query_factory.load_summary_statistics()
            projects = self.db_session.query(Project).all()
            data['project_colours'] = {}
            for project in projects:
                data['project_colours'][project.name] = project.chart_colour
            template = self.render_template(
                "query_factory/summary.html",data=data)
            self.db_session.close()

            return template

        except Exception as err:
            self.logger.exception(err)
            self.db_session.close()
            return str(err)

    @expose('/delete_saved_query')
    def delete_saved_query(self):

        self.set_db_session(request)
        try:

            id = request.args.get('id')
            saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(id)).delete()
            self.db_session.commit()
            flash('Query ' + str(id) + ' deleted!')

        except Exception as err:
            self.db_session.close()
            flash('Query not recognised')
            return str(err)

        return redirect(url_for("QueryFactoryView.list"))

    @expose('/simple_query_builder')
    def simple_query_builder(self):
        """ The saved_query builder is a simplified user interface to the QueryFactory API
            The user builds a constrained query on the basis commonly-required filters,
            including projects, sample_types, assays, metadata, and compounds

        :return:
        """

        self.set_db_session(request)
        data = {}

        data['match_model_options'] = self.get_all_filter_fields()
        data["projects"] = self.execute_sql("select id, name from project order by name")
        data["sample_types"] = SampleType
        data["sample_matrices"] = self.execute_sql("select distinct sample_matrix from sample order by sample_matrix")
        data["assays"] = self.execute_sql("select name from assay group by name order by name")
        data["annotation_methods"] = self.execute_sql("select name from annotation_method group by name order by name")
        data["harmonised_metadata_fields"] = self.execute_sql("select id, name, datatype from harmonised_metadata_field")
        data["external_dbs"] = self.execute_sql("select name from external_db")

        data['external_dbs_list'] = []
        for field in data['external_dbs']:
            data['external_dbs_list'].append(field['name'])

        data["internal_compound_identifiers"] = {
                                                     'Compound.name': 'compound name',
                                                     'Compound.inchi': 'inchi',
                                                     'Compound.inchi_key': 'inchi key',
                                                     'Compound.chemical_formula': 'chemical formula',
                                                     'Compound.monoisotopic_mass': 'exact mass',
                                                     'CompoundClass.inchi_key_backbone': 'inchi_key_backbone',
                                                     'CompoundClass.category': 'lipid maps category',
                                                     'CompoundClass.main_class': 'lipid maps main class',
                                                     'CompoundClass.lipidmaps_sub_group': 'lipid maps subgroup',
                                                 }
        data['models'] = {}
        if 'id' in request.args:
            saved_query_id = request.args.get('id')
            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                if saved_query:
                    saved_query.load_query_dict_for_view()
                    data['saved_query'] = saved_query
                    data['preset_filters'] = self.parse_preset_filters(saved_query.json)
                    query_factory = QueryFactory(saved_query=saved_query)
                    models = query_factory.get_implemented_models()
                    for model in models:
                        data['models'][model] = {}
                        if self.cache.exists(saved_query.get_cache_dataframe_key(output_model='AnnotatedFeature')):
                            data['models'][model]['cache_state'] = 'exists'
                        elif model in saved_query.generating_cache:
                            data['models'][model]['cache_state'] = 'generating'
                        else:
                            data['models'][model]['cache_state'] = 'none'
                        print(data['models'][model]['cache_state'])
                else:
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        self.db_session.close()
        return self.render_template(
            "query_factory/simple_query_builder.html", data=data)

    def parse_preset_filters(self,query_dict):

        #if filter['filter_preset'] in ['Projects','SampleTypes','Assays','Species','Samples']:

        preset_filters = {}

        for filter in query_dict['filters']:
            if 'filter_preset' in filter.keys():

                filter_preset = filter['filter_preset']

                if filter_preset in ['Projects','SampleTypes','Assays','Samples','AnnotationMethods']:

                    preset_filters[filter_preset] = {}

                    sub_filter = filter['sub_filters'][0]
                    match = sub_filter['matches'][0]

                    if filter_preset == 'Samples':
                        preset_filters[filter_preset]['csv_values'] = ",".join(match['value'])
                    else:
                        preset_filters[filter_preset]['values'] = match['value']

                elif filter_preset == 'Metadata':
                    preset_filters[filter_preset] = []
                    for sub_filter in filter['sub_filters']:
                        matches = sub_filter['matches']

                        print(matches)

                        i = 0
                        p = 1
                        while p < len(matches):

                            print("i = " + str(i))
                            print("p = " + str(p))

                            #Every 2 matches make up 1 row in view
                            metadata_field = {'name': matches[i]['value'],
                                              'operator': matches[i]['operator'],
                                              'datatype': matches[i]['datatype']}

                            metadata_field['values'] = matches[p]['value']

                            if isinstance(matches[p]['value'],list):
                                metadata_field['csv_values'] = ','.join(matches[p]['value'])
                            else:
                                metadata_field['csv_values'] = matches[p]['value']

                            print(matches[i])
                            print(matches[p])
                            print(metadata_field)

                            harmonised_metadata_field = self.db_session.query(HarmonisedMetadataField) \
                                .filter(HarmonisedMetadataField.name==metadata_field['name']).first()

                            metadata_field['metadata_values'] = self.get_metadata_values(harmonised_metadata_field)

                            preset_filters[filter_preset].append(metadata_field)

                            i = i + 2
                            p = p + 2

                    print(preset_filters[filter_preset])

                elif filter_preset == 'Compounds':
                    preset_filters[filter_preset] = []
                    for sub_filter in filter['sub_filters']:
                        matches = sub_filter['matches']
                        i = 0
                        p = 1
                        skip_next = False
                        while i < len(matches):

                            if skip_next:
                                skip_next = False
                                i = i + 1
                                p = p + 1
                                if i >= len(matches):
                                    break

                            compound_field = {'model': matches[i]['model'],
                                              'property': matches[i]['property']}

                            if compound_field['model'] == 'ExternalDB':
                                # Overwrite the name and values
                                compound_field['name'] = matches[i]['model'] + "." + matches[i]['value']
                                compound_field['external_db_field'] = matches[i]['value']
                                compound_field['values'] = matches[p]['value']
                                compound_field['datatype'] = "VARCHAR"
                                compound_field['operator'] = matches[p]['operator']
                                skip_next = True
                            else:
                                compound_field['name'] = matches[i]['model'] + "." + matches[i]['property']
                                compound_field['values'] = matches[i]['value']
                                compound_field['datatype'] = matches[i]['datatype']
                                compound_field['operator'] = matches[i]['operator']

                            if isinstance(compound_field['values'],list):
                                compound_field['csv_values'] = ','.join(compound_field['values'])
                            else:
                                compound_field['csv_values'] = compound_field['values']

                            print(compound_field)

                            compound_field['compound_values'] = []

                            if compound_field['model'] == 'ExternalDB':
                                external_db = self.db_session.query(ExternalDB.id).filter(ExternalDB.name==matches[i]['value']).first()
                                dropdown_values = self.execute_sql("select database_ref from compound_external_db" +
                                                                    " where external_db_id = " + str(external_db.id) +
                                                                    "group by database_ref order by database_ref")


                                for dropdown_value in dropdown_values:
                                    compound_field['compound_values'].append(dropdown_value['database_ref'])

                            else:
                                dropdown_values = self.execute_sql("select " + compound_field['property'] + " from " + self.model_table_map[compound_field['model']] +
                                                                   " group by " + compound_field['property'] + " order by " + compound_field['property'])


                                for dropdown_value in dropdown_values:
                                    compound_field['compound_values'].append(str(dropdown_value[compound_field['property']]))


                            preset_filters[filter_preset].append(compound_field)
                            i = i + 1
                            p = p + 1

#        print(preset_filters)
        return preset_filters


    @expose('/get_simple_query_builder_metadata_html')
    def get_simple_query_builder_metadata_html(self):

        self.set_db_session(request)
        data = {}

        data["harmonised_metadata_fields"] = self.execute_sql("select id, name,datatype from harmonised_metadata_field")

        print(data)
        self.db_session.close()

        if 'sub_filter' in request.args:
            return self.render_template(
                "query_factory/metadata_sub_filter.html",data=data)
        else:
            return self.render_template(
                "query_factory/metadata_filter.html",data=data)


    @expose('/get_simple_query_builder_metadata_values')
    def get_simple_query_builder_metadata_values(self):

        self.set_db_session(request)
        data = {}

        if 'harmonised_field_name' not in request.args:
            raise Exception("No harmonised field name in request")

        if 'operator' not in request.args:
            raise Exception("No operator in request")

        harmonised_field_name = request.args.get('harmonised_field_name')
        operator = request.args.get('operator')

        harmonised_metadata_field = self.db_session.query(HarmonisedMetadataField) \
            .filter(HarmonisedMetadataField.name==harmonised_field_name).first()

        metadata_values = self.get_metadata_values(harmonised_metadata_field)

        data['datatype'] = harmonised_metadata_field.datatype.value
        data['metadata_values'] = metadata_values

        if operator in ['in','not_in','between','not_between']:
            data['multiple'] = True

        self.db_session.close()
        return self.render_template(
            "query_factory/metadata_values_dropdown.html",data=data)

    def get_metadata_values(self,harmonised_metadata_field):

        metadata_values = []

        if harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.text:
            metadata_values = [v.harmonised_text_value for v in self.db_session.query(MetadataValue.harmonised_text_value) \
                .join(MetadataField,HarmonisedMetadataField) \
                .filter(HarmonisedMetadataField.id==harmonised_metadata_field.id) \
                .distinct()]

        elif harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.numeric:
            metadata_values = [v.harmonised_numeric_value for v in self.db_session.query(MetadataValue.harmonised_numeric_value) \
                .join(MetadataField,HarmonisedMetadataField) \
                .filter(HarmonisedMetadataField.id==harmonised_metadata_field.id) \
                .distinct()]


        elif harmonised_metadata_field.datatype == HarmonisedMetadataField.HarmonisedMetadataFieldDatatype.datetime:
            metadata_values = [v.harmonised_datetime_value for v in self.db_session.query(MetadataValue.harmonised_datetime_value) \
                .join(MetadataField,HarmonisedMetadataField) \
                .filter(HarmonisedMetadataField.id==harmonised_metadata_field.id) \
                .distinct()]

        return metadata_values

    @expose('/get_simple_query_builder_compound_html')
    def get_simple_query_builder_compound_html(self):

        self.set_db_session(request)
        data = {}

        data["external_dbs"] = self.execute_sql("select name from external_db")

        self.db_session.close()

        if 'sub_filter' in request.args:
            return self.render_template(
                "query_factory/compound_sub_filter.html",data=data)
        else:
            return self.render_template(
                "query_factory/compound_filter.html",data=data)



    @expose('/get_simple_query_builder_compound_identifier_values')
    def get_simple_query_builder_compound_identifier_values(self):

        self.set_db_session(request)
        data = {}

        if 'compound_identifier' not in request.args:
            raise Exception("No compound_identifier in request")

        if 'operator' not in request.args:
            raise Exception("No operator in request")

        compound_identifier = request.args.get('compound_identifier')
        operator = request.args.get('operator')

        model,table,property = self.get_model_field(compound_identifier)
        #if model in ['compound','compound_class','compound_assay',"compound_external_db","annotation"]:

        if model == 'ExternalDB':
            external_db = self.db_session.query(ExternalDB.id).filter(ExternalDB.name==property).first()
            dropdown_values = self.execute_sql("select database_ref from compound_external_db" +
                                               " where external_db_id = " + str(external_db.id) +
                                               " group by database_ref order by database_ref")

            model = 'CompoundExternalDB'
            property = "database_ref"

        else:
            dropdown_values = self.execute_sql("select " + property + " from " + table +
                                               " group by " + property + " order by " + property)

        data['dropdown_values'] = []

        for dropdown_value in dropdown_values:
            data['dropdown_values'].append(dropdown_value[property])

        if operator in ['in','not_in','between','not_between']:
            data['multiple'] = True

        data['datatype'] = self.get_property_type(model,property)
        print(data['datatype'])

        if operator in ['in','not_in','between','not_between']:
            data['multiple'] = True

        self.db_session.close()
        return self.render_template(
            "query_factory/compound_values_dropdown.html",data=data)

    def get_model_field(self,compound_identifier):

        model_field = compound_identifier.split('.')

        self.logger.debug("model_field %s" % model_field)
        print("model_field %s" % model_field)
        self.logger.debug("model_table_map %s" % self.model_table_map)
        print("model_table_map %s" % self.model_table_map)

        if self.model_table_map[model_field[0]] not in ['compound','compound_class','compound_assay',"external_db","annotation"]:
            raise Exception ("Model unrecognised: " + model_field[0])

        if model_field[1] not in ['chemical_formula','monoisotopic_mass','inchi',"inchi_key","inchi_key_backbone",
                                  'category_id','main_class_id','sub_class_id','HMDB',
                                   'KEGG','LipidMAPS','PubChem CID','ChemSpider','MetaCyc','ChEBI','ChEMBL','LipidBank','CAS',
                                  'database_ref','feature_name','cpd_name','value','lod','lloq','uloq','quantification_type',
                                  'calibration_method','confidence_score']:
            raise Exception ("Property unrecognised:" + model_field[1])

        return model_field[0],self.model_table_map[model_field[0]],model_field[1]


    def get_property_type(self,model_name,property):

        datatype = None
        for model in Base._decl_class_registry.values():
            if hasattr(model, '__tablename__') and model.__tablename__ == self.model_table_map[model_name]:
                mapper = inspect(model)
                for column in model.__table__.columns:
                    if column.name == property:
                        datatype = column.type
                        break
        return datatype

    @expose('/download_dataframe')
    def download_dataframe(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args and 'model' in request.args:
            saved_query_id = request.args.get('id')
            model = request.args.get('model')
            class_level = None
            class_type = None
            aggregate_function = None
            harmonise_annotations = False
            if 'harmonise_annotations' in request.args:
                if request.args.get('harmonise_annotations') == 'True':
                    harmonise_annotations = True
            if 'class_level' in request.args and 'class_type' in request.args and 'aggregate_function' in request.args:
                class_level = request.args.get('class_level')
                class_type = request.args.get('class_type')
                aggregate_function = request.args.get('aggregate_function')
            correction_type = None
            if 'correction_type' in request.args:
                if request.args.get('correction_type') in ['SR','LTR']:
                    correction_type = request.args.get('correction_type')

            self.logger.info("request.args" % request.args)

            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                if saved_query:
                    query_factory = QueryFactory(saved_query=saved_query)
                    key = query_factory.get_dataframe_key(type='combined', model=model,
                                                        aggregate_function=aggregate_function,harmonise_annotations=harmonise_annotations,
                                                        class_level=class_level, class_type=class_type,correction_type=correction_type)
                    query_factory.load_dataframe(type='combined',combined_csv_path=('/tmp/%s_%s_saved_query_dataframe.csv' % (key,saved_query.id)),
                                                 output_model=model,class_type=class_type,class_level=class_level,harmonise_annotations=harmonise_annotations,
                                                 aggregate_function=aggregate_function,correction_type=correction_type)
                    self.db_session.close()
                    return send_file(query_factory.dataframe_csv_paths[key], as_attachment=True, mimetype='text/csv')
                else:
                    self.db_session.close()
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        self.db_session.close()

    @expose('/download_intensity_csv')
    def download_intensity_csv(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args and 'model' in request.args:
            saved_query_id = request.args.get('id')
            model = request.args.get('model')
            class_level = None
            class_type = None
            aggregate_function = None
            correction_type = None
            scaling = None
            harmonise_annotations = False
            if 'harmonise_annotations' in request.args:
                if request.args.get('harmonise_annotations') == 'True':
                    harmonise_annotations = True
            if 'correction_type' in request.args:
                if request.args.get('correction_type') in ['SR', 'LTR']:
                    correction_type = request.args.get('correction_type')
            if 'class_level' in request.args and 'class_type' in request.args and 'aggregate_function' in request.args:
                class_level = request.args.get('class_level')
                class_type = request.args.get('class_type')
                aggregate_function = request.args.get('aggregate_function')
            if 'scaling' in request.args:
                scaling = utils.get_scaling_text(request.args.get('scaling'))
            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                if saved_query:
                    query_factory = QueryFactory(saved_query=saved_query)
                    key = query_factory.get_dataframe_key(type='intensity_data',model=model,class_type=class_type,
                                                          class_level=class_level,aggregate_function=aggregate_function,
                                                          correction_type=correction_type,scaling=scaling,harmonise_annotations=harmonise_annotations)
                    query_factory.load_dataframe(type='intensity_data',output_dir='/tmp/phenomedb/downloads',output_model=model,
                                                 class_type=class_type,class_level=class_level,aggregate_function=aggregate_function
                                                 ,correction_type=correction_type,scaling=scaling,harmonise_annotations=harmonise_annotations)
                    #query_factory.build_intensity_data_sample_metadata_and_feature_metadata(output_dir='/tmp/phenomedb/npyc-datasets/',output_model=model,class_type=class_type,class_level=class_level)
                    self.db_session.close()
                    return send_file(query_factory.dataframe_csv_paths[key], as_attachment=True,mimetype='text/csv')
                else:
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        self.db_session.close()

    @expose('/download_sample_metadata_csv')
    def download_sample_metadata_csv(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args and 'model' in request.args:
            saved_query_id = request.args.get('id')
            model = request.args.get('model')
            correction_type = None
            if 'correction_type' in request.args:
                if request.args.get('correction_type') in ['SR', 'LTR']:
                    correction_type = request.args.get('correction_type')
            class_level = None
            class_type = None
            aggregate_function = None
            if 'class_level' in request.args and 'class_type' in request.args and 'aggregate_function' in request.args:
                class_level = request.args.get('class_level')
                class_type = request.args.get('class_type')
                aggregate_function = request.args.get('aggregate_function')
            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                if saved_query:
                    query_factory = QueryFactory(saved_query=saved_query)
                    key = query_factory.get_dataframe_key(type='sample_metadata',model=model,class_level=class_level,
                                                          class_type=class_type,aggregate_function=aggregate_function,correction_type=correction_type)
                    query_factory.load_dataframe(type='sample_metadata',output_dir='/tmp/phenomedb/downloads', output_model=model, class_type=class_type,
                                                 class_level=class_level, aggregate_function=aggregate_function,correction_type=correction_type)
                    self.db_session.close()
                    return send_file(query_factory.dataframe_csv_paths[key], as_attachment=True,mimetype='text/csv')
                else:
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        self.db_session.close()

    @expose('/download_feature_metadata_csv_path')
    def download_feature_metadata_csv_path(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args and 'model' in request.args:
            saved_query_id = request.args.get('id')
            model = request.args.get('model')
            class_level = None
            class_type = None
            aggregate_function = None
            correction_type = None
            harmonise_annotations = False
            if 'harmonise_annotations' in request.args:
                if request.args.get('harmonise_annotations') == 'True':
                    harmonise_annotations = True
            if 'correction_type' in request.args:
                if request.args.get('correction_type') in ['SR', 'LTR']:
                    correction_type = request.args.get('correction_type')
            if 'class_level' in request.args and 'class_type' in request.args and 'aggregate_function' in request.args:
                class_level = request.args.get('class_level')
                class_type = request.args.get('class_type')
                aggregate_function = request.args.get('aggregate_function')
            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                if saved_query:
                    query_factory = QueryFactory(saved_query=saved_query)
                    key = query_factory.get_dataframe_key(type='feature_metadata', model=model, class_level=class_level,harmonise_annotations=harmonise_annotations,
                                                        class_type=class_type, aggregate_function=aggregate_function,correction_type=correction_type)
                    query_factory.load_dataframe(type='feature_metadata', output_dir='/tmp/phenomedb/downloads', output_model=model, class_type=class_type,
                                                 class_level=class_level, aggregate_function=aggregate_function,correction_type=correction_type,harmonise_annotations=harmonise_annotations)
                    self.db_session.close()
                    return send_file(query_factory.dataframe_csv_paths[key], as_attachment=True)
                else:
                    self.db_session.close()
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        self.db_session.close()

    @expose('/download_file')
    def download_file(self):

        self.set_db_session(request)
        data = {}
        if 'id' in request.args and 'm' in request.args:
            saved_query_id = request.args.get('id')
            model = request.args.get('m')
            file_type = request.args.get('ft')
            convert_units = False
            master_unit = None
            class_level = None
            class_type = None
            aggregate_function = None
            correction_type = None
            harmonise_annotations = False
            columns_to_include = None
            for_npyc = False
            sample_orientation = None
            sample_label = None
            feature_orientation = None
            feature_label = None
            transform = None
            scaling = None
            metadata_bin_definition = None
            task_run_id = None
            if 'tr' in request.args:
                task_run_id = True
            if 'ha' in request.args:
                if request.args.get('ha') == 'True':
                    harmonise_annotations = True
            if 'npyc' in request.args:
                if request.args.get('npyc') == 'True':
                    for_npyc = True
            #if 'ba' in request.args:
            #    if request.args.get('ba') == 'True':
            #        biomerak = True
            if 'cu' in request.args:
                convert_units = True
                master_unit = request.args.get('cu')
            if 'ft' in request.args:
                if request.args.get('ft') in ['SR', 'LTR']:
                    correction_type = request.args.get('ft')
            if 'cl' in request.args and 'ct' in request.args and 'af' in request.args:
                class_level = request.args.get('cl')
                class_type = request.args.get('ct')
                aggregate_function = request.args.get('af')
            if 'so' in request.args:
                sample_orientation = request.args.get('so')
            if 'cti' in request.args:
                columns_to_include = request.args.get('cti').split(",")
            if 'sl' in request.args:
                sample_label = request.args.get('sl')
            if 'fo' in request.args:
                feature_orientation = request.args.get('fo')
            if 'fl' in request.args:
                feature_label = request.args.get('fl')
            if 'mbin' in request.args:
                metadata_bin_definition = json.loads(request.args.get('mbin').replace('"m":','"method":').replace('"c":','"column":').replace('"b":','"bins":'))
            if 's' in request.args:
                scaling = request.args.get('scaling')
            if 't' in request.args:
                transform = request.args.get('transform')

            if utils.is_number(saved_query_id) and saved_query_id != 'new':
                saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id == int(saved_query_id)).first()
                if saved_query:

                    if file_type not in ['combined', 'sample_metadata', 'feature_metadata', 'intensity_data',
                                         'metaboanalyst_data', 'metaboanalyst_metadata']:
                        raise Exception('File type not recognised! %s' % file_type)

                    query_factory = QueryFactory(saved_query=saved_query)

                    output_dir = '/tmp/phenomedb/downloads'

                    if task_run_id:
                        task_run = self.db_session.query(TaskRun).filter(TaskRun.id==task_run_id).first()
                        if not task_run:
                            raise Exception('Task Run does not exist! %s' % task_run_id)
                        if task_run.status != TaskRun.Status.success:
                            raise Exception('Task Run is not completed %s' % task_run.status)
                        task_run_output = task_run.get_task_output(self.cache)
                        if 'sample_metadata' in task_run_output.keys() and 'feature_metadata' in task_run_output.keys() and 'intensity_data' in task_run_output.keys():
                            if file_type in ['sample_metadata','feature_metadata','intensity_data']:
                                raise NotImplementedError('Not yet implemented')
                            elif file_type in ['metaboanalyst_data','metaboanalyst_metadata']:
                                raise NotImplementedError('Not yet implemented')

                    elif file_type in ['combined']:
                        combined_data = query_factory.load_dataframe(type='combined',
                                             output_model=model, class_type=class_type,
                                             class_level=class_level, aggregate_function=aggregate_function,
                                             correction_type=correction_type,convert_units=convert_units,master_unit=master_unit,
                                             harmonise_annotations=harmonise_annotations)
                        combined_data = query_factory.transform_dataframe(type='combined',
                                             #sample_orientation=sample_orientation,
                                             #feature_orientation=feature_orientation,
                                             transform=transform, scaling=scaling,
                                             metadata_bin_definition=metadata_bin_definition,
                                            combined_data=combined_data,columns_to_include=columns_to_include)
                        file_key = query_factory.combined_key + "_transformed"

                        file_path = query_factory.output_files_for_download(type=file_type,
                                                                            file_key=file_key,
                                                                            dataframe=combined_data,
                                                                            output_dir=output_dir,with_header=True)

                    elif file_type in ['sample_metadata','feature_metadata','intensity_data']:
                        intensity_data = query_factory.load_dataframe(type='intensity_data',
                                             output_model=model, class_type=class_type,
                                             class_level=class_level, aggregate_function=aggregate_function,
                                             correction_type=correction_type,convert_units=convert_units,master_unit=master_unit,
                                             harmonise_annotations=harmonise_annotations)
                        feature_metadata = query_factory.load_dataframe(type='feature_metadata',
                                                                      output_model=model, class_type=class_type,
                                                                      class_level=class_level,
                                                                      aggregate_function=aggregate_function,
                                                                      correction_type=correction_type,
                                                                      convert_units=convert_units,
                                                                      master_unit=master_unit,
                                                                      harmonise_annotations=harmonise_annotations)
                        sample_metadata = query_factory.load_dataframe(type='sample_metadata',
                                                                      output_model=model, class_type=class_type,
                                                                      class_level=class_level,
                                                                      aggregate_function=aggregate_function,
                                                                      correction_type=correction_type,
                                                                      convert_units=convert_units,
                                                                      master_unit=master_unit,
                                                                      harmonise_annotations=harmonise_annotations)
                        sample_metadata, feature_metadata, intensity_data = query_factory.transform_dataframe(type='3 file format',
                              #               sample_orientation=sample_orientation,
                                            sample_label=sample_label,
                                            # feature_orientation=feature_orientation,
                                            for_npyc=for_npyc,include_harmonised_metadata=True,include_metadata=True,
                                             transform=transform, scaling=scaling,columns_to_include=columns_to_include,
                                             metadata_bin_definition=metadata_bin_definition,sample_metadata=sample_metadata,
                                             feature_metadata=feature_metadata,intensity_data=intensity_data )
                        if file_type == 'sample_metadata':
                            dataframe_for_export = sample_metadata
                            file_key = query_factory.sample_metadata_key + "_transformed"
                            with_header = True
                            if for_npyc:
                                with_index = True
                            else:
                                with_index = None
                        elif file_type == 'feature_metadata':
                            dataframe_for_export = feature_metadata
                            file_key = query_factory.feature_metadata_key + "_transformed"
                            with_header = True
                            if for_npyc:
                                with_index = True
                            else:
                                with_index = False
                        elif file_type == 'intensity_data':
                            dataframe_for_export = intensity_data
                            file_key = query_factory.intensity_data_key + "_transformed"
                            with_header = None
                            with_index = None


                        file_path = query_factory.output_files_for_download(type=file_type,
                                                                            file_key=file_key,
                                                                            dataframe=dataframe_for_export,
                                                                            output_dir=output_dir,
                                                                            with_header=with_header,
                                                                            with_index=with_index)

                    elif file_type in ['metaboanalyst_data','metaboanalyst_metadata']:
                        metaboanalyst_data = query_factory.load_dataframe(type='metaboanalyst_data',
                                                                         output_model=model,
                                                                          class_type=class_type,
                                                                         class_level=class_level,
                                                                          feature_label=feature_label,
                                                                          sample_label=sample_label,
                                                                          aggregate_function=aggregate_function,
                                                                         correction_type=correction_type,
                                                                          convert_units=convert_units,
                                                                          master_unit=master_unit,
                                                                         harmonise_annotations=harmonise_annotations)
                        metaboanalyst_metadata = query_factory.load_dataframe(type='metaboanalyst_metadata',
                                                                      output_model=model, class_type=class_type,
                                                                      class_level=class_level,
                                                                      feature_label=feature_label,
                                                                      sample_label=sample_label,
                                                                      aggregate_function=aggregate_function,
                                                                      correction_type=correction_type,
                                                                      convert_units=convert_units,
                                                                      master_unit=master_unit,
                                                                      harmonise_annotations=harmonise_annotations)

                        metaboanalyst_data,metaboanalyst_metadata = query_factory.transform_dataframe(type='metaboanalyst',
                             #                                            sample_orientation=sample_orientation,
                             #                                            feature_orientation=feature_orientation,
                                                                         transform=transform, scaling=scaling,
                                                                         metadata_bin_definition=metadata_bin_definition,
                                                                        metaboanalyst_metadata=metaboanalyst_metadata,
                                                                         metaboanalyst_data=metaboanalyst_data,
                                                                        columns_to_include=columns_to_include,only_harmonised_metadata=True )
                        output_dir = '/tmp/phenomedb/downloads'
                        if file_type == 'metaboanalyst_metadata':
                            dataframe_for_export = metaboanalyst_metadata
                            file_key = query_factory.metaboanalyst_metadata_key + "_transformed"
                            file_path = query_factory.output_files_for_download(type=file_type,
                                                                                file_key=file_key,
                                                                                dataframe=dataframe_for_export,
                                                                                output_dir=output_dir, with_header=True)

                        elif file_type == 'metaboanalyst_data':
                            dataframe_for_export = metaboanalyst_data
                            file_key = query_factory.metaboanalyst_data_key + "_transformed"
                            file_path = query_factory.output_files_for_download(type=file_type,
                                                                                file_key=file_key,
                                                                                dataframe=dataframe_for_export,
                                                                                output_dir=output_dir, with_header=True)

                            #if feature_orientation == 'rows':
                            #    with_header = True
                            #elif feature_orientation == 'columns':
                            #    with_header = True



                    self.db_session.close()
                    return send_file(file_path, as_attachment=True)
                else:
                    self.db_session.close()
                    raise Exception("No saved_query with id: " + str(saved_query_id))

        self.db_session.close()

    @expose('/generate-dataframe-cache',methods=["POST"])
    def generate_dataframe_cache(self):
        self.set_db_session(request)
        data = {}
        try:
            if 'saved_query_id' in request.form and 'model' in request.form:
                saved_query_id = request.form['saved_query_id']
                model = request.form['model']
                correction_type = None
                if 'correction_type' in request.form:
                    if request.form['correction_type'] in ['SR','LTR']:
                        correction_type = request.form['correction_type']

                if utils.is_number(saved_query_id) and saved_query_id != 'new':
                    saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                    if saved_query:

                        if 'PIPELINES' in config and 'pipeline_manager' in config['PIPELINES'] and config['PIPELINES']['pipeline_manager'] == "apache-airflow":
                            import phenomedb.airflow.database as db
                            db_session = db.get_airflow_db_session()
                        else:
                            db_session = self.db_session
                        #db_session = self.db_session
                        #if 'user_id' in session:
                        #    user = db_session.query(User).filter(User.id==session['user_id']).first()
                        #    username = user.username
                        #else:
                        #    username = saved_query.created_by

                        #self.logger.info('username: %s' % username)
                        #print('username: %s' % username)

                        from phenomedb.pipeline_factory import PipelineFactory
                        run_config = {'createsavedquerydataframecache':{'saved_query_id':saved_query_id,'username':None,'master_unit':'mmol/L','output_model':model}}

                        if correction_type:
                            run_config['createsavedquerydataframecache']['correction_type'] = correction_type

                        pipeline = PipelineFactory(pipeline_name='CreateSavedQueryDataframeCache')
                        pipeline.run_pipeline(run_config=run_config)
                        query_factory = QueryFactory()
                        key = query_factory.get_dataframe_key(type='combined',model=model,correction_type=correction_type)
                        self.logger.info("key: %s" % key)
                        if saved_query.cache_state:
                            cache_state = dict(saved_query.cache_state)
                        else:
                            cache_state = {}
                        if key not in cache_state.keys():
                            cache_state[key] = 'generating'
                        saved_query.cache_state = cache_state
                        self.db_session.commit()
                        self.db_session.close()
                        return jsonify({'success':'true'})
                    else:
                        raise Exception("No saved_query with id: " + str(saved_query_id))
                else:
                    raise Exception("saved_query_id is not a number")
            else:
                raise Exception("No saved_query_id in post")
        except Exception as err:
            self.db_session.close()
            self.logger.exception(err)
            return jsonify({'error':str(err)})

    @expose('/check_cache',methods=["POST"])
    def check_cache(self):

        self.set_db_session(request)
        data = {}
        try:
            if 'saved_query_id' in request.form:
                saved_query_id = request.form['saved_query_id']
                self.logger.info("Saved Query ID: %s" % saved_query_id)
                if utils.is_number(saved_query_id) and saved_query_id != 'new':
                    saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
                    if saved_query:
                        query_factory = QueryFactory(saved_query=saved_query)
                        if not saved_query.cache_state:
                            cache_state = {}
                        else:
                            cache_state = dict(saved_query.cache_state)
                        data['cache_state'] = cache_state
                        self.db_session.close()
                        return jsonify(data)
                    else:
                        raise Exception("No saved_query with id: " + str(saved_query_id))
                else:
                    raise Exception("saved_query_id is not a number: " + str(saved_query_id))
            else:
                raise Exception("No saved_query_id in post")
        except Exception as err:
            self.db_session.close()
            self.logger.exception(err)
            return jsonify({'error':str(err),'cache_exists':'no'})

    @expose('/clear_cache', methods=["GET"])
    def clear_cache(self):
        self.set_db_session(request)
        saved_query_id = request.args.get('id')
        self.logger.info(saved_query_id)
        saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==int(saved_query_id)).first()
        if saved_query:
            if saved_query.cache_state:
                cache_state = dict(saved_query.cache_state)
                for key,state in saved_query.cache_state.items():
                    if state == 'exists':
                        self.cache.delete(key)
                    del cache_state[key]
                saved_query.cache_state = cache_state
                self.logger.info(saved_query.cache_state)
            self.cache.delete_keys_by_regex(('SavedQuery\w+::%s:' % saved_query.id))
            self.db_session.commit()
            self.db_session.close()
            return jsonify({'success': 'true'})
        else:
            return jsonify({'error': 'true'})


saved_query_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder='../templates',
    static_folder='../templates/static',
    static_url_path='/static/phenomedb')

#compound_view = CompoundView(category="PhenomeDB", name="Compounds")

v_appbuilder_view = QueryFactoryView()
v_appbuilder_package = {"name": "Query Factory",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}

appbuilder_mitem = {"name": "Query Factory",
                    "category": "PhenomeDB",
                    "category_icon": "fa-th",
                    "href": "/query_factory/"}

class QueryFactoryPlugin(AirflowPlugin):

    name = VIEW_NAME

    # flask_blueprints and admin_views are AirflowPlugin properties
    flask_blueprints = [saved_query_bp]
    #admin_views = [compound_view]
    #admin_views = []
    appbuilder_views = [v_appbuilder_package]
    #appbuilder_menu_items = [appbuilder_mitem]
