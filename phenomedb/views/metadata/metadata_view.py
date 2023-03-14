import os, sys, json, logging
from datetime import datetime
from pprint import pprint

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config


# PhenomeDB imports
import phenomedb.database as db
#import phenomedb.views as dao
import phenomedb.utilities as utils
from phenomedb.models import *

# Flask imports
from flask import Blueprint, request, jsonify, make_response, redirect, url_for
#from flask_admin import BaseView, expose
from flask_appbuilder import BaseView as AppBuilderBaseView
from flask_appbuilder import expose, has_access

from flask.logging import default_handler

# Airflow imports:
from airflow.plugins_manager import AirflowPlugin


VIEW_NAME = "metadata"


from phenomedb.base_view import *

class MetadataView(PhenomeDBBaseView):

    def __init__(self):

        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)

    def get_default_data(self, data_dict):       
        try:               
            # get data to populate dropdowns
            data_dict["projects"] = self.execute_sql("select id, name from project")
            data_dict["units"] = self.execute_sql("select id, name from unit")
            data_dict["harmonised"] = self.execute_sql("select id, name from harmonised_metadata_field")
            data_dict["harmonised_metadata_field_datatype"] = HarmonisedMetadataField.HarmonisedMetadataFieldDatatype
        except Exception as e:
            data_dict["error"] = str(e)       
        return data_dict
    
    @expose("/")
    @has_access
    def list(self, data_dict={}):
        self.set_db_session(request)
        data = self.get_default_data(data_dict)
        self.db_session.close()
        return self.render_template( "metadata/metadata.html", data=data)

    @expose("/json")
    @has_access
    def index_json(self):
        self.set_db_session(request)
        data_dict = {}         
        data = self.get_default_data(data_dict)
        self.db_session.close()
        return jsonify(data)              
     
        

    def get_metadata_values_by_field(self,metadata_field_id):
        """
        Get metadata values for field
        :param metadata_field_id: which particular field
        :return list of dicts
        """
        metadata_vals = []
        self.logger.debug("Getting values for metadata field %s", metadata_field_id)
        try:

            results = self.db_session.query(MetadataValue.id, MetadataValue.raw_value, MetadataValue.sample_id, MetadataValue.raw_value) \
                .filter(MetadataValue.metadata_field_id==metadata_field_id) \
                .all()

            for row in results:
                metadata_vals.append(dict(zip(row.keys(), row)))

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return metadata_vals

    def delete_metadata_field(self,metadata_field_id):
        """
        Delete metadata field
        :param field_id: which particular field
        """

        try:
            # delete will cascade to the field values in MetadataValue
            self.db_session.query(MetadataField) \
                .filter(MetadataField.id==metadata_field_id) \
                .delete()
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

  
    @expose("/metadata_fields/json/", methods=["GET"])
    @has_access
    def get_metadata_fields(self):
        """
        called via ajax request from UI to populate metadata harmonisation view
        selected project id is optionally passed via queriestring param
        """
        self.set_db_session(request)
        rows = []
        try:
            project_id = request.args.get("project_id")  
            rows = self.get_project_metadata_fields(project_id)
            sample_count = self.db_session.query(Sample)\
                .join(Subject, Sample.subject_id == Sample.id)\
                .filter(Subject.project_id == int(float(project_id))).count()
            self.logger.debug(sample_count)
        except Exception as e: 
            return self.handle_json_error(e)
        self.db_session.close()
        data = {'rows':rows,'sample_count':sample_count}
        return json.dumps(data)

    @expose("/metadata_vals/json/", methods=["GET"])
    @has_access
    def get_metadata_values(self):
        """
        called via ajax request from UI to populate metadata harmonisation view
        """
        self.set_db_session(request)
        data = {}
        data['rows'] = []
       
        try:         
            field_id = request.args.get("id")
            rows = self.get_metadata_values_by_field(field_id)

            harmonised_metadata_field_value_name = self.get_harmonised_metadata_field_value_name(field_id)

            sql = "SELECT metadata_field_id, metadata_value_id,raw_value, " \
                    + harmonised_metadata_field_value_name + \
                    ", sample_matrix, sample, subject from v_project_subject_sample_metadata \
            WHERE metadata_field_id = :metadata_field_id"

            data['rows'] = self.execute_sql(sql,{"metadata_field_id" : field_id})
            data['harmonised_metadata_field_value_name'] = harmonised_metadata_field_value_name
            response_body = jsonify(utils.convert_to_json_safe(data))
        except Exception as e: 
            return self.handle_json_error(e)

        self.db_session.close()
             
        return make_response(response_body, 200)

    def get_harmonised_metadata_field_value_name(self,field_id):
        '''
            Class method to generated the harmonised field datatype name to simplify the view
        :param field_id:
        :return:
        '''

        harmonised_metadata_field = self.db_session.query(HarmonisedMetadataField.datatype) \
            .join(MetadataField).filter(MetadataField.id==field_id).first()

        if harmonised_metadata_field:
            self.logger.debug("HarmonisedMetadataFieldDatatype: " + str(harmonised_metadata_field.datatype.value))
            harmonised_metadata_field_value_name = 'harmonised_' + harmonised_metadata_field.datatype.value + "_value"
        else:
            self.logger.debug("HarmonisedMetadataFieldDatatype: None ")
            harmonised_metadata_field_value_name = 'harmonised_text_value'

        return harmonised_metadata_field_value_name


    def override_metadata_harmonised_value(self,value_id,request_body):
        '''
            Class method to inject the harmonised field datatype value into the request body
        :param field_id:
        :param request_body:
        :return:
        '''

        harmonised_metadata_field = self.db_session.query(HarmonisedMetadataField.datatype) \
            .join(MetadataField,MetadataValue).filter(MetadataValue.id==value_id).first()

        self.logger.debug(harmonised_metadata_field)

        if harmonised_metadata_field:
            key = 'harmonised_' + harmonised_metadata_field.datatype.value + "_value"
            self.logger.debug("Got field %s", harmonised_metadata_field)
            if harmonised_metadata_field.datatype.value == 'text':
                request_body[key] = str(request_body['harmonised_value'])
                self.logger.debug(key + " casted to str for " + str(request_body['harmonised_value']))

            elif harmonised_metadata_field.datatype.value == 'numeric':

                if utils.isint(request_body['harmonised_value']):
                    request_body[key] = int(request_body['harmonised_value'])
                    self.logger.debug(key + " casted to integer for " + str(request_body['harmonised_value']))

                elif utils.isfloat(request_body['harmonised_value']):
                    request_body[key] = float(request_body['harmonised_value'])
                    self.logger.debug(key + " casted to float for " + str(request_body['harmonised_value']))

                else:
                    raise Exception('Unable to cast to numeric value: ' + request_body['harmonised_value'])

            elif harmonised_metadata_field.datatype.value == 'datetime':
                request_body[key] = datetime.strptime(request_body['harmonised_value'], '%Y-%m-%d %H:%M:%S')
                self.logger.debug(key + " casted to datetime for " + str(request_body['harmonised_value']))

            else:
                raise Exception('Unknown metadata harmonised field datatype - field_id:' + str(harmonised_metadata_field.id))

            del request_body['harmonised_value']
        else:
            raise Exception('Unknown metadata harmonised field datatype - field_id:' + str(harmonised_metadata_field))

        return request_body

    def handle_json_error(self, e):
        response_body = {}
        self.logger.exception(e)
        error_msg = getattr(e, "message", repr(e))
        #self.logger.error(error_msg)
        response_body["error"] = error_msg
        self.db_session.close()
        return make_response(response_body, 400)
    
    @expose("/metadata_raw", methods=["DELETE"])
    @has_access
    def delete_raw_field(self):
        self.set_db_session(request)
        try:
            request_body = request.get_json()           
            field_id = request_body["field_id"] 
            self.logger.debug("delete %s", field_id)
            self.delete_metadata_field(field_id)
        except Exception as e:
            self.logger.exception(e)
            print(e)
            return self.handle_json_error(e)
        self.db_session.close()
        return make_response(jsonify({"success":True}), 200)  
                              
    @expose("/harmonised", methods=["POST"])
    @has_access
    def insert_harmonised_field(self):
        '''
        this handles a form submission, not ajax request
        '''
        self.set_db_session(request)
        data = {}
        try:        
            entity_dict = self.flask_form_to_ORM_dict(request.form)  
            self.logger.debug("Got new harmonised field %s to insert", entity_dict)
            self.insert_entity("harmonised_metadata_field", entity_dict)  
            data['user_msg'] = ["New field added." ]         
        except Exception as e:      
            self.logger.error("Error inserting field %s", str(e))
            data['error'] = str(e)
        self.db_session.close()
        return self.list(data_dict=data)

    @expose("/harmonised", methods=["PUT"])
    @has_access
    def curate_field_value(self):
        self.set_db_session(request)
        data = {}        
        try:
            request_body = request.get_json()           
            value_id = request_body["id"]
            self.logger.debug("update %s", request_body)
            request_body = self.override_metadata_harmonised_value(value_id,request_body)
            self.logger.debug("update %s", request_body)
            self.update_entity("metadata_value", request_body)  
        except Exception as e: 
            return self.handle_json_error(e)
        self.db_session.close()
        return make_response(request_body, 200) 
                                     
    @expose("/assign", methods=["POST"])
    @has_access
    def assign_harmonised_field(self):
        self.set_db_session(request)
        data = {}        
        try:        
            data["project_id"] = request.form.get("project_id")
            entity_dict = self.flask_form_to_ORM_dict(request.form)  
            self.logger.debug("assigning metadata_field %s", entity_dict)
            self.update_entity("metadata_field", entity_dict)             
                         
        except Exception as e:  
            data['error'] = str(e)
            self.logger.error("Error assigning field %s", str(e))
        self.db_session.close()
        return self.list(data)

    @expose("/insert_unit", methods=["POST"])
    @has_access
    def insert_unit(self):
        '''
        this handles a form submission, not ajax request
        '''
        self.set_db_session(request)
        data = {}
        try:
            entity_dict = self.flask_form_to_ORM_dict(request.form)
            self.logger.debug("Got new unit %s to insert", entity_dict)
            self.insert_entity("unit", entity_dict)
            data['user_msg'] = ["New unit added." ]
        except Exception as e:
            self.logger.error("Error inserting field %s", str(e))
            data['error'] = str(e)
        self.db_session.close()
        return self.list(data_dict=data)
 
                              
    
"""
BLUEPRINT
template_folder is where the html files for this module live
static_folder is the same for all modules; contains eg css and js libraries
static_url_path maps the physical path in static_folder to this value, eg
http://localhost:8080/static/phenomedb/phenomedb.css
"""
metadata_bp = Blueprint(
        VIEW_NAME, __name__,
        template_folder="../templates",
        static_folder="../templates/static",
        static_url_path="/static/phenomedb")

"""
Create the view class
"category" parameter is the item on the Airflow menu bar,
"name" parameter is the item in that menu
"""
#metadata_view = MetadataHarmonisationView(category="PhenomeDB", name="Metadata Harmonisation")
v_appbuilder_view = MetadataView()
v_appbuilder_package = {"name": "Metadata",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}


class MetadataPlugin(AirflowPlugin):
   
    name = VIEW_NAME
    # the variables called flask_blueprints and admin_views 
    # are inherited AirflowPlugin properties
    flask_blueprints = [metadata_bp]
    #admin_views = [metadata_view]
    appbuilder_views = [v_appbuilder_package]
    
    

