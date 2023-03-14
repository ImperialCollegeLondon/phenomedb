import os, sys, json, logging
from datetime import datetime
from pprint import pprint

#BROWSER = "phenomedb_browser"
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.config import config


# PhenomeDB imports
import phenomedb.database as db
#import phenomedb.views as dao
#import phenomedb.utilities as utils
from phenomedb.models import *

# Flask imports
from flask import Blueprint, request, jsonify, make_response, flash
#from flask_admin import BaseView, expose
from flask_appbuilder import BaseView as AppBuilderBaseView
from flask_appbuilder import expose, has_access
from flask.logging import default_handler

# Airflow imports:
from airflow.plugins_manager import AirflowPlugin

VIEW_NAME = "phenomedb_browser"

from phenomedb.base_view import *

class PhenomeDBBrowserView(PhenomeDBBaseView):

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)

    @expose('/')
    @has_access
    def list(self):
        self.set_db_session(request)
        data = {}
        try:   
            data['tables'] = self.get_table_names()
        except Exception as e:
            data['error'] = str(e)
        self.db_session.close()
        return self.render_template(
            "phenomedb_browser/tables.html", data=data)

    @expose("/fields/json/", methods=["GET"])
    @has_access
    def get_table_fields(self):
        """
        called via ajax request from UI to populate insert to table view
        """
        self.set_db_session(request)
        rows = []
        try: 
            table_name = request.args.get("table")  
            rows = self.get_table_columns(table_name)        
        except Exception as e: 
            return self.handle_json_error(e)
        self.db_session.close()
        return json.dumps(rows)

    @expose('/entity/insert', methods=["POST"])
    @has_access
    def insert_entity_view(self):
        self.set_db_session(request)
        data = {}       
        try:
            # this is an insert of a new record
            table = request.form.get("entity_name")
            entity_dict = self.flask_form_to_ORM_dict(request.form)
            # remove table name before insert
            entity_dict.pop("entity_name", None)
            id = self.insert_entity(table, entity_dict)
            flash("Successful insert to " + table)
            data['table'] = table
            data['entity'] = self.get_entity_as_dict(table, id, False)    
        except Exception as e:
            self.logger.error(str(e))
            data['error'] = str(e)

        self.db_session.close()
        return self.render_template("phenomedb_browser/entity.html", data=data)
    
    @expose('/entity/<table>/<id>', methods=["POST", "GET"])
    @has_access
    def entity(self, table, id):
        self.set_db_session(request)
        data = {}
        data['table'] = table   
        try:
            if request.method=="POST":     
                # this is an update for existing record
                self.logger.debug("Processing update to %s %s", table, id)
                entity_dict = self.flask_form_to_ORM_dict(request.form)  
                self.update_entity(table, entity_dict)
                flash(table + " successfully updated")
                
        except Exception as e:
            data['error'] = str(e)
         
        data['entity'] = self.get_entity_as_dict(table, id, False)

        self.db_session.close()
        return self.render_template("phenomedb_browser/entity.html", data=data)
                     
    def create_link_to_entity (self, table, df): 
        '''
        Make a column of html anchor tags out of each id in the dataframe
        '''  
        open_link = '<a href="entity/' + table + '/'
        close_link = '"><span class="glyphicon glyphicon-zoom-in"/></a>' 
        return [(open_link + str(x) + close_link) for x in df['id']]
     
    def handle_json_error(self, e):
        response_body = {}
        error_msg = getattr(e, "message", repr(e))
        self.logger.error(error_msg)  
        response_body["error"] = error_msg    
        return make_response(response_body, 400)
                                
    @expose('/table/json/')
    @has_access
    def get_table_json(self):
        '''
        Populates a jQuery DataTable; called via ajax request from UI. 
        It expects a query parameter called 'table', eg: 
        http://localhost:8080/admin/phenomedbbrowserview/table/json/?table=project
        Optional param 'ro' means the link to drill down to the row won't display.
        '''
        self.set_db_session(request)
        json_data = None
        try:
            table = request.args.get("table")  
            read_only = request.args.get("ro")
            self.logger.debug("Getting rows from %s", table)

            df = self.sql_to_dataframe("SELECT * FROM " + table)
            if not df.empty and not read_only:
                df['View'] = self.create_link_to_entity(table, df)
                # Put the view link at the beginning
                cols = list(df.columns.values)         
                re_cols = cols[-1:] + cols[:-1]         
                df = df[re_cols] 

            json_data = df.to_json(orient="split")
        except Exception as e: #this happens, be graceful
            error_msg = getattr(e, 'message', repr(e))
            self.logger.debug(str(e))
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]}) 
            
        d = json.loads(json_data)["data"]
        c = json.loads(json_data)["columns"]

        self.db_session.close()
        return jsonify(table_data = d, columns = [{"title": str(col)} for col in c])
                              

'''
BLUEPRINT
template_folder is where the html files for this module live
static_folder is the same for all modules; contains eg css and js libraries
static_url_path maps the physical path in static_folder to this value, eg
http://localhost:8080/static/phenomedb/phenomedb.css
'''
browser_bp = Blueprint(
        VIEW_NAME, __name__,
        template_folder='../templates',
        static_folder='../templates/static',
        static_url_path='/static/phenomedb')

'''
Create the view class
'category' parameter is the item on the Airflow menu bar,
'name' parameter is the item in that menu
'''
#browser_view = PhenomeDBBrowserView(category="PhenomeDB", name="SQL Browser")

v_appbuilder_view = PhenomeDBBrowserView()
v_appbuilder_package = {"name": 'SQL Browser',
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}


class PhenomeDBBrowserPlugin(AirflowPlugin):
   
    name = VIEW_NAME
    # the variables called flask_blueprints and admin_views 
    # are inherited AirflowPlugin properties
    flask_blueprints = [browser_bp]
    #admin_views = [browser_view]
    appbuilder_views = [v_appbuilder_package]
    
    

