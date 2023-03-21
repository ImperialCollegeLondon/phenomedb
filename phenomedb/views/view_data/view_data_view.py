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
from flask import Blueprint, request, jsonify, make_response, redirect, url_for, flash
#from flask_admin import BaseView, expose
from flask_appbuilder import BaseView as AppBuilderBaseView
from flask_appbuilder import expose

from flask.logging import default_handler

# Airflow imports:
from airflow.plugins_manager import AirflowPlugin

VIEW_NAME = "view_data"


from phenomedb.base_view import *

class ViewData(PhenomeDBBaseView):

    def __init__(self):

        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)
        

    @expose("/")
    def list(self):
        ''' Index view - show options for searching data
        '''
        return self.render_template("view_data/search.html")

    @expose("/search",  methods=["GET","POST"])
    def search(self):
        ''' Index view - show options for searching data
        '''
      
        self.set_db_session(request)

        search_term = request.form["search_term"].strip()
        
        search_cats = {Project:           ["Projects", "Project"],
                      Subject:            ["Subjects", "Subject"],
                      Sample :     ["Sampling Events", "Sample"],
                      SampleAssay: ["Sample Event Assays", "SampleAssay"],
                      Annotation: ["Assay Annotations", "Annotation"],
                      Compound:           ["Compounds","Compound"]}
                      
        search_results = {}
        try:
            if len(search_term) > 0:
                with SearchClient("127.0.0.1", 1491, "password") as querycl:
    
                    for model, bucket in search_cats.items():
                    
                        result_header = bucket[0]
                        
                        model_object = bucket[1]
                        ids = querycl.query("main", model_object, search_term)
                        if len(ids) > 0:
                            entity_list = self.db_session.query(model).filter(model.id.in_(ids)).all()
                            as_dicts  = self.get_entities_as_dicts(entity_list) 
                            search_results[result_header] = entity_list
                        else:
                            search_results[result_header] = []
        except Exception as e:
            self.logger.error("Error searching %s", str(e))
        #self.logger.debug(search_results)
        return self.render_template( "view_data/search_results.html",data=search_results)


    @expose("/sample/<id>", methods=["GET"])
    def sample(self,id):
        ''' Index view - show options for searching data
        '''
        data = {}
        assay_annotations = []
        self.set_db_session(request)

        sample = self.db_session.query(Sample).filter(Sample.id == id).first()
        if sample:
            
            data['sample'] = sample
            data['metadata'] = self.execute_sql("select name, raw_value, harmonised_name, " \
                                            "coalesce(harmonised_text_value::text, '') as harmonised_text_value, " \
                                            "coalesce(harmonised_numeric_value::text, '') as harmonised_numeric_value, " \
                                            "coalesce(harmonised_datetime_value::text, '') as harmonised_datetime_value " \
                                            "from v_project_subject_sample_metadata where sample_id = :id", 
                                            {"id" : id})
            
            for assay in sample.sample_assays:
                assay_id = assay.id
                temp = self.execute_sql("select * from v_annotation_methods_summary where sample_assay_id = :id", {"id":assay_id})
             
                
                

        else:          
            flash("No such sampling event! (" + str(id) + ")")
            return self.list()
       
        return self.render_template( "view_data/sample.html",data=data)

    @expose("/xcms_features/<id>", methods=["GET"])
    def xcms_features(self,id):

        data = {}
        self.set_db_session(request)
        sample = self.db_session.query(Sample).filter(Sample.id == id).first()
        data['sample'] = sample
        return self.render_template( "view_data/sample.html",data=data)

    @expose('/get_annotations/', methods=["GET"])
    def get_annotations(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.set_db_session(request)

        json_data = json.dumps({"data":[[""]], "columns":[""]})
        try:

            if 'sample_id' in request.args:
                sample_id = request.args.get('sample_id')

                df = self.sql_to_dataframe("select * from v_annotations where sample_id = " + sample_id)
            else:
                df = self.sql_to_dataframe("select * from v_annotations")

            self.logger.debug("Got " + str(len(df)) + " annotations")
            # make a link out of the display name column
            if not df.empty:
                '''
                df['sample_id'] = [
                    ''.join(['<a href="' + url_for("ViewData.sample",id=x) + '"/>', y, '</a>']) for x, y in zip(df['sample_id'], df['sample_id'])]
                '''
                df['compound'] = [
                    ''.join(['<a href="' + url_for("CompoundView.compound",id=x) + '"/>', y, '</a>']) for x, y in zip(df['compound_id'], df['compound'])]

                df['cpd_name'] = [
                    ''.join(['<a href="' + url_for("CompoundView.annotation_compound",id=x) + '"/>', y, '</a>']) for x, y in zip(df['annotation_compound_id'], df['cpd_name'])]

                df.drop(columns=['compound_id','annotation_compound_id','sample_id'],inplace=True)

            json_data = df.to_json(orient="split")
                
        except Exception as e: #this happens, be graceful
            error_msg = getattr(e, 'message', repr(e))
            self.logger.debug(str(e))
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]})

        d = json.loads(json_data)["data"]
        c = ['Assay annotation', 'Annotation ID', 'Assay', 'Method',
             'Compound', 'CPD', 'InChI', 'InChI key', 'Monoisotopic mass',
             'Intensity', 'Unit', 'LOD', 'LLOQ', 'ULOQ']
       
        self.db_session.close()
        # response is formatted for display in a DataTable:
        return make_response(jsonify(table_data = d, columns = [{"title": str(col)} for col in c]))


"""
BLUEPRINT
template_folder is where the html files for this module live
static_folder is the same for all modules; contains eg css and js libraries
static_url_path maps the physical path in static_folder to this value, eg
http://localhost:8080/static/phenomedb/phenomedb.css
"""
view_data_bp = Blueprint(
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
v_appbuilder_view = ViewData()
v_appbuilder_package = {"name": "View Data",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}


#class ViewDataPlugin(AirflowPlugin):

 #   name = VIEW_NAME
 #   flask_blueprints = [view_data_bp]
 #   appbuilder_views = [v_appbuilder_package]



