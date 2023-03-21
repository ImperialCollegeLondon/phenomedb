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

VIEW_NAME = "annotation_view"

class AnnotationView(PhenomeDBBaseView):

    def __init__(self):


        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)
        # all fields for table:
        self.DISPLAY_FIELDS = [{"label": "Project", "name" : "project"},
                                  {"label": "Sample", "name" : "sample_name"},
                                  {"label": "Assay", "name" : "assay"},
                                  {"label": "Annotation method", "name" : "annotation_method"},
                                  {"label": "CPD", "name" : "cpd_name"},
                                  {"label": "Intensity", "name" : "intensity"},
                                  {"label": "Unit", "name" : "unit"},
                                  {"label": "Retention time", "name" : "rt"},
                                  {"label": "M/Z", "name" : "mz"},
                                  {"label": "LOD", "name" : "lod"},
                                  {"label": "LLOQ", "name" : "lloq"},
                                  {"label": "ULOQ", "name" : "uloq"},
                                   ]

        """
        See also annotations.html for the map with the operators in
        """
        self.FILTERS = [
                        {"label":"Project", "type":"text", "data": "project", "search":{}}, 
                        {"label":"Sample", "type":"text", "data": "sample_name", "search":{}}, 
                        {"label":"Assay", "type":"text", "data":"assay", "search":{}},
                        {"label":"Annotation method", "type":"text", "data":"annotation_method","search":{}},
                        {"label":"Compound", "type":"text", "data":"compound","search":{}},
                        {"label":"CPD name", "type":"text", "data":"cpd_name","search":{}}, 
                        {"label":"Chemical formula", "type":"text", "data": "chemical_formula", "search":{}},
                        {"label":"InChI", "type":"text", "data":"inchi","search":{}},
                        {"label":"InChi key", "type":"text", "data":"inchi_key","search":{}}  ,                  
                        {"label":"Sample matrix", "type":"text", "data": "sample_matrix", "search":{}}, 
                        {"label":"Monoisotopic mass", "type":"number", "data":"monoisotopic_mass","search":{}},
                        {"label":"Intensity", "type":"number", "data":"intensity","search":{}},
                        {"label":"LOD", "type":"number", "data":"lod","search":{}},
                        {"label":"LLOQ", "type":"number", "data":"lloq","search":{}},
                        {"label":"ULOQ", "type":"number", "data":"uloq","search":{}},
                        {"label":"Retention time", "type":"number", "data":"retention_time","search":{}},
                        {"label":"M/Z", "type":"number", "data":"mz","search":{}},                       
                        {"label":"Sample type", "type":"text", "data": "sample_type", "search":{}}, 
                        {"label":"Assay role", "type":"text", "data": "assay_role", "search":{}},                     
                        {"label":"Biological tissue", "type":"text", "data": "biological_tissue", "search":{}}, 
                        {"label":"Sample file name", "type":"text", "data": "sample_file_name", "search":{}}, 
                        {"label":"Batch", "type":"text", "data": "batch", "search":{}}, 
                        {"label":"Quantification type", "type":"text", "data": "quantification_type", "search":{}}, 
                        {"label":"Calibration method", "type":"text", "data": "calibration_method", "search":{}}, 
                        {"label":"Platform", "type":"text", "data": "platform", "search":{}}, 
                        {"label":"Targeted", "type":"text", "data": "targeted", "search":{}}, 
                        {"label":"MS Polarity", "type":"text", "data": "ms_polarity", "search":{}}

                       
                        ] 

        
        sql_fields = [x["name"] for x in self.DISPLAY_FIELDS]
        self.SEARCH = "select sample_id, compound_id, " + ",".join(sql_fields) + " from v_annotations "
        self.SEARCH_COUNT = "select count(*) from v_annotations "
                         
    @expose("/")
    @has_access
    def list(self):
        self.set_db_session(request)
        data = {}
        data["display"] = self.DISPLAY_FIELDS
        data["filters"] = self.FILTERS
        #self.logger.debug(data["filters"])
        data['unharmonised_annotations'] = self.db_session.query(Annotation) \
                                                .join(FeatureMetadata) \
                                                .join(AnnotatedFeature) \
                                                .join(SampleAssay) \
                                                .filter(Annotation.harmonised_annotation_id==None) \
                                                .order_by(SampleAssay.assay_id,Annotation.cpd_id).all()

        feature_datasets = {}
        for unharmonised_annotation in data['unharmonised_annotations']:
            feature_datasets[unharmonised_annotation.id] = self.db_session.query(FeatureDataset).join(FeatureMetadata).join(Annotation).filter(Annotation.id==unharmonised_annotation.id).all()
        data['feature_datasets'] = feature_datasets

        data['harmonised_annotations'] = self.db_session.query(HarmonisedAnnotation) \
                                                .order_by(HarmonisedAnnotation.assay_id,
                                                          HarmonisedAnnotation.cpd_id,
                                                          HarmonisedAnnotation.cpd_name)\
                                                .all()
        return self.render_template("annotation/annotations.html", data=data)

    @expose("/harmonise_annotations", methods=["POST"])
    @has_access
    def harmonise_annotations(self):
        self.set_db_session(request)
        annotation_ids = json.loads(request.form['annotation_ids'])
        harmonised_annotation_id = request.form['harmonised_annotation_id']
        annotations = self.db_session.query(Annotation).filter(Annotation.id.in_(annotation_ids)).all()
        msg = "Annotations harmonised to "
        for annotation in annotations:
            annotation.harmonised_annotation_id = harmonised_annotation_id
        self.db_session.commit()
        msg = "Annotations harmonised: %s to %s:%s" % (annotation_ids,
                                                       annotations[0].harmonised_annotation.assay.name,
                                                       annotations[0].harmonised_annotation.cpd_name)
        self.logger.info(msg)
        flash(msg)
        self.db_session.close()

        return jsonify(success=True)

    @expose("/delete_harmonised_annotation", methods=["POST"])
    @has_access
    def delete_harmonised_annotation(self):
        self.set_db_session(request)

        harmonised_annotation_id = request.form['harmonised_annotation_id']
        self.db_session.query(HarmonisedAnnotation).filter(HarmonisedAnnotation.id==harmonised_annotation_id).delete()
        self.db_session.commit()
        msg = "Deleted harmonised annotation! %s" % harmonised_annotation_id
        self.logger.info(msg)
        flash(msg)
        self.db_session.close()
        return jsonify(success=True)
        
    @expose("/annotations/json", methods=["GET","POST"])
    @has_access
    def get_annotations_json(self):

        self.set_db_session(request)

        model = {}   
        
       
        dt_json = request.get_json().get("dt_args")
        # custom dict contains the filter arguments
        filter_json = request.get_json().get("custom")
      
        draw = dt_json["draw"]
        start = dt_json["start"]
        length = dt_json["length"]
        order = dt_json["order"][0]["column"]
        order_dir = dt_json["order"][0]["dir" ]        
        search_term = dt_json["search"]["value" ]
        
        #columns = dt_json["columns"]
        columns = filter_json
        
        #pprint(columns)
        self.logger.debug("Got global search %s", search_term)  
        if order:
            order_by = int(order) + 1 
            order = str(order_by) + " " + order_dir
        else:
            order = "2 desc" 
        
        if not start:
            start = 0
        
        if not length:
            length = 25

        try :

            if len(search_term) > 0:
                sql, params = self.build_global_search_filter(search_term)
            else:
                sql, params = self.build_sql_by_column(columns)
             
            count_all = self.execute_sql(self.SEARCH_COUNT)            
          
            count_filtered = self.execute_sql(self.SEARCH_COUNT + sql, params)
            
            df = self.filter_fields(self.SEARCH + sql, start, length, order, params )  

            if len(df) > 0:
                model["recordsTotal"] = count_all[0]["count"]
                model["recordsFiltered"] = count_filtered[0]["count"]
            else:
                model["recordsTotal"] = 0
                model["recordsFiltered"] = 0
               
            json_data = df.to_json(orient="records")
                         
        except Exception as e:
            error_msg = getattr(e, "message", repr(e))
            self.logger.error(error_msg)
            json_data = json.dumps({"data":[[error_msg]], "columns":["Error"]})

        if draw:
            model["draw"] = draw
        else:
            model["draw"] = 1 
        d = json.loads(json_data)
        model["data"] = d
        #return json.dumps(model)
        return jsonify(model)
    
      
    def filter_fields(self, sql_base, offset, limit, order_by, params={}):
        
        sql = sql_base
        
        if order_by:
            sql = sql + " order by " + order_by
        if limit and  limit > 0: # limit of -1 = "all"
            sql = sql + " limit " + str(limit)
        if offset:
            sql = sql + " offset " + str(offset)        
        
        self.logger.debug( "FINAL sql " + sql )
        self.logger.debug( "PARAMS %s ", params)
        return self.sql_to_dataframe(sql, params)
    
    def build_global_search_filter(self, search_term):

        
        search_term = "%" + search_term + "%"
        
        params = { "term": search_term }
        
        # this is just a convenience for looping on OR next
        sql = "WHERE sample_id::text ILIKE :term"
        
        for col in self.DISPLAY_FIELDS:            
            sql += " OR " + col["name"] + "::text ILIKE :term"

        return (sql,params)
        
    def build_sql_by_column(self, columns):
        '''
        See self.FILTERS for 'columns' structure
        Filters will have been added in columns["search"] dict
        '''
        sql = "WHERE sample_id is not null"
        params = {}
        
        for col in columns:
            
            val = col["search"]["value"].strip()
            
            if len(val) == 0:
                continue
            
            operator = col["search"]["condition"]
            datatype = col["search"]["type"]
            
            
            self.logger.debug("value %s", val)
            
            if "in" == operator:      
                val_list = [x.strip() for x in val.split(",")]
                if "number" == datatype:                       
                    val_list = [float(x) for x in val_list]
                sql += " AND " + col["data"] + " = ANY(:" + col["data"] + ")"
                params[col["data"]] = val_list
                
            elif "not in" == operator:
                
                val_list = [x.strip() for x in val.split(",")]
                if "number" == datatype:                       
                    val_list = [float(x) for x in val_list]
                sql += " AND NOT " + col["data"] + " = ANY(:" + col["data"] + ")"
                params[col["data"]] = val_list
                
            elif "<>" == operator:
                val_list = [x.strip() for x in val.split(":")]
                
                if len(val_list) == 2: # or what?                    
                    sql += " AND " + col["data"] + ">" + " :" + col["data"] + "_low"
                    sql += " AND " + col["data"] + "<" + " :" + col["data"] + "_high"
                    params[col["data"] + "_low"] = val_list[0]
                    params[col["data"] + "_high"] = val_list[1]
            else:
                sql += " AND " + col["data"] + " " + operator + " :" + col["data"]
                if "number" == datatype:   
                    val = float(val)
                params[col["data"]] = val
        self.logger.debug("sql %s", sql)  
        self.logger.debug("params %s", params)  
        return (sql,params)
        

annotation_bp = Blueprint(
    VIEW_NAME, __name__,
    template_folder="../templates",
    static_folder="../templates/static",
    static_url_path="/static/phenomedb")

v_appbuilder_view = AnnotationView()
v_appbuilder_package = {"name": "Annotations",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}


#class AnnotationPlugin(AirflowPlugin):

#    name = VIEW_NAME
#    flask_blueprints = [annotation_bp]
#    appbuilder_views = [v_appbuilder_package]



