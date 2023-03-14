import os, sys, json, logging, http
from datetime import datetime
from pprint import pprint
import pandas as pd
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, make_response, redirect, url_for, flash, send_from_directory
from flask_appbuilder import expose, has_access
from flask.logging import default_handler

if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config

import phenomedb.database as db
import phenomedb.utilities as utils
from phenomedb.models import *
from phenomedb.base_view import *

from sqlalchemy.exc import IntegrityError
# this is only Airflow specific part:
from airflow.plugins_manager import AirflowPlugin

VIEW_NAME = "compound"
# log file directory is configured in config.ini

UPLOAD_DIRECTORY = 'phenomedb/uploads/'

ALLOWED_EXTENSIONS = {'txt', 'csv'}

class CompoundView(PhenomeDBBaseView):

    def __init__(self):
        super().__init__()
        self.configure_logging(identifier=VIEW_NAME)

  
    @expose('/')
    @has_access
    def list(self):
        return self.render_template(
            "compound/compounds.html", data={})
    
    def get_data_for_annotation_evidence(self, annotation_id):
        
        evidence = []
        annotation_compound = {}
          
        annotation_compound_evidence = self.execute_sql("SELECT * from v_annotation_evidence_records where annotation_id = :id", {"id":annotation_id})
       
        if len(annotation_compound_evidence) > 0:
            first_row = annotation_compound_evidence[0]
            annotation_method_keys = ('compound_id', 'compound_name', 'annotation_method_id', 'annotation_compound_id', 'annotation_method_name', 'cpd_name', 'secondary_compound_id')
           
            annotation_compound = {x: first_row[x] for x in annotation_method_keys if x in first_row}
            for result in annotation_compound_evidence:
                annotation_evidence_id = result["annotation_evidence_id"]
                if annotation_evidence_id:
                    file_uploads = self.execute_sql("SELECT * from annotation_evidence_file_upload where annotation_evidence_id = :id", {"id":annotation_evidence_id})
                    """
                     making the file list explicitly JSON is a hack to make
                    them parseable by Javascript on the UI
                    """
                    result["files"] = json.dumps(file_uploads, default=str)
                    # remove annotation_method info from evidence rows
                    for a in annotation_method_keys:
                        del result[a]                   
                    evidence.append(result) 
       
        self.logger.debug("compound annotation_method is %s", annotation_compound)
        self.logger.debug("evidence %s", evidence)   
        return (annotation_compound, evidence)
    
    @expose("/evidence/remove", methods=["POST"])
    @has_access
    def remove_annotation_evidence(self):

        self.set_db_session(request)
        try:
           
            annotation_evidence_id = request.form["annotation_evidence_id"]
            annotation_id = request.form["annotation_id"]
                  
            self.db_session.query(AnnotationEvidence) \
                .filter(AnnotationEvidence.id==annotation_evidence_id) \
                .delete()
            self.db_session.commit() 
            flash("Evidence deleted")     
        except Exception as e: 
            self.logger.error("Error deleting %s", str(e))
            flash("Error deleting " + str(e))
            self.db_session.rollback()
        self.db_session.close()  
        return redirect(url_for("CompoundView.annotation",id=annotation_id))
     
    @expose('/evidence/download', methods=['GET'])
    @has_access
    def download_evidence_file(self):
         
        error_string = ""
        annotation_evidence_file_upload_id = request.args["id"]
        annotation_id = request.args["annotation_id"]
        # get document details from the record itself
        self.set_db_session(request)
        erfu = self.db_session.query(AnnotationEvidenceFileUpload) \
                            .filter(AnnotationEvidenceFileUpload.id==annotation_evidence_file_upload_id) \
                            .first()
        self.db_session.close()
        
        if erfu:
            download_file = os.path.join(erfu.filepath, erfu.filename)
            if os.path.isfile(download_file):
                return send_from_directory(erfu.filepath, filename=erfu.filename, as_attachment=True)
            else:   
                error_string = "File not found"                 
               
        else:
            error_string = "Evidence record not found"
            
        self.logger.debug(error_string)
        flash(error_string)
        return redirect(url_for("CompoundView.annotation",id=annotation_id))
                                       
    
    @expose('/evidence/upload', methods=['POST'])
    @has_access
    def upload_annotation_evidence(self):
        self.set_db_session(request)       
        
        annotation_evidence_id = request.form["annotation_evidence_id"]
        annotation_id = request.form["annotation_id"]
        
        files = request.files.getlist("id_file")
        filenames = []
        
        try:
            for file in files:
                file_name = secure_filename(file.filename)                                                                                           
                if not os.path.exists(UPLOAD_DIRECTORY):
                    os.makedirs(UPLOAD_DIRECTORY)
    
                new_file = os.path.join(UPLOAD_DIRECTORY, file_name)
                filenames.append(file_name)
               
                file.save(new_file)                             
                self.logger.debug("Evidence file uploaded to %s", os.path.abspath(UPLOAD_DIRECTORY) )
                evidence_file_record = AnnotationEvidenceFileUpload()
                evidence_file_record.filename = file_name
                evidence_file_record.filepath = os.path.abspath(UPLOAD_DIRECTORY)
                evidence_file_record.description = "test"
                evidence_file_record.date_uploaded = datetime.today().strftime("%Y-%m-%d")
                evidence_file_record.uploaded_by_user = "me"
                evidence_file_record.annotation_evidence_id = annotation_evidence_id
                self.db_session.add(evidence_file_record)
                self.db_session.commit()
                flash("Uploaded files: {}".format(", ".join(filenames))) 
        except Exception as e: 
            self.logger.error(e)          
            flash('Error: ' + str(e))
       
        self.db_session.close()
        return redirect(url_for("CompoundView.annotation",id=annotation_id))


    @expose('/evidence/update', methods=['POST'])
    @has_access
    def update_annotation_evidence(self):
        self.set_db_session(request)
        """
        The same html form is used to delete records, so remove any extra fields
        """
        entity_dict = self.flask_form_to_ORM_dict(request.form)
        annotation_id = entity_dict["annotation_id"]
        #annotation_compound_annotation_evidence_id = entity_dict.pop("annotation_compound_annotation_evidence_id")
        self.logger.debug("updating evidence %s", entity_dict)
        self.update_entity('annotation_evidence', entity_dict)
        flash("record updated")
        self.db_session.close()
        return redirect(url_for("CompoundView.annotation",id=annotation_id))


    @expose('/evidence/insert', methods=['POST'])
    @has_access
    def insert_annotation_evidence(self):
        data = {}
        self.set_db_session(request)
        try:        
            entity_dict = self.flask_form_to_ORM_dict(request.form)
            self.logger.debug("Inserting evidence %s", entity_dict)
            annotation_id = entity_dict["annotation_id"]
            # create new AnnotationEvidence
            annotation_evidence_id = self.insert_entity( "annotation_evidence", entity_dict)
            self.logger.debug("new evidence has id %s", annotation_id)
            flash("Evidence added.")
            
            data["annotation"], data["evidence"] = self.get_data_for_annotation_evidence(annotation_id)
            self.db_session.close()
        
        except Exception as e:
            self.logger.exception(e)
            flash("error " + str(e) )   
                
        return redirect(url_for("CompoundView.annotation", id = annotation_id))

    @expose('/harmonised_annotation/<id>', methods=['GET'])
    def harmonised_annotation(self,id):
        self.set_db_session(request)
        data = {}
        data["harmonised_annotation"] = self.db_session.query(HarmonisedAnnotation).filter(HarmonisedAnnotation.id == int(float(id))).first()
        template = self.render_template("compound/harmonised_annotation.html", data=data)
        self.db_session.close()
        return template
    
    @expose('/compound/<compound_id>/annotation/<annotation_id>', methods=['GET'])
    @has_access
    def annotation(self, compound_id,annotation_id):
        data = {}      
        self.set_db_session(request)
        data["compound"] = self.db_session.query(Compound).filter(Compound.id==compound_id).first()
        data["annotation"] = self.db_session.query(Annotation).filter(Annotation.id==annotation_id).first()
        data["annotation_evidence"], data["evidence"] = self.get_data_for_annotation_evidence(annotation_id)
        data["evidence_types"] = self.execute_sql("SELECT * from evidence_type")
        template = self.render_template("compound/annotation.html", data=data)
        self.db_session.close()
        return template

    @expose('/compound', methods=['GET','POST'])
    @has_access
    def insert_compound(self):
        self.set_db_session(request)

        data = {'compound':None}
        table = 'compound'
        html = "compound/compound.html"    
        if request.method == 'POST':
            try:        
                entity_dict = self.flask_form_to_ORM_dict(request.form)
                self.logger.debug("Inserting compound %s", entity_dict)
                id = self.insert_entity( table, entity_dict)
                self.logger.debug("new compound has id %s", id)              
                data['user_msg'] = ["Compound successfully inserted."]
                data['compound'] = self.get_entity_as_dict(table, id, False)

            except Exception as e:
                self.logger.error(e)
                data['error'] = str(e)
        else:
            # get db heaadings and annotation_methods to fill in
            data['external_dbs'] = self.get_external_dbs()
            data['annotation_methods'] = self.get_annotation_methods()
            data['columns'] = self.get_table_columns("compound")
            html = "compound/new_compound.html"

        self.db_session.close()
        return self.render_template(html, data=data)
    
    @expose('/compound/<id>', methods=['GET','POST'])
    @has_access
    def compound(self, id):
        
        self.set_db_session(request)
        data = {}
        try:
            if request.method=="POST":     
                # do an update; split the two tables out from the form 
                entity_dict, ext_refs = self.flask_form_to_compound_update(request.form)
                # external database entries are referenced by 'db_' + their id
                self.update_entity('compound', entity_dict)
                
                for entry in ext_refs:
                    try:
                        self.logger.debug("Inserting ext_refs %s", entry)
                        self.insert_entity("compound_external_db", entry)
                    except IntegrityError as ie:
                        # database prevents a non-unique insert
                        self.logger.debug("Not inserting duplicate external db reference %s", entry['database_ref'])
                flash("Compound successfully updated")

            self.logger.debug("about to get datasets for compound id %s", id)
            data = self.get_datasets_peaklists_for_compound(id)
            #self.logger.debug("Compound before is %s", data)
            
            data['external_dbs'] = self.format_compound_external_dbs(id)
            #data['compound_class_annotation_methods'] = self.get_compound_class_annotation_methods(id)
            data['annotation_methods'] = self.get_annotation_compounds(id)
            data['groups'] = self.get_compound_classes(id)
           
            #sql = "SELECT * from aliquot WHERE compound_id = :id"
            #data['aliquots'] = self.execute_sql(sql,{"id" : id})
            data['compound_id'] = id

            
        except Exception as e:
            self.logger.exception(e)
            data['error'] = str(e)
        
        #self.logger.debug("Data is %s", data)
        self.db_session.close()
        return self.render_template("compound/compound.html", data=data)
    
    
    @expose('/compounds', methods=['POST'])
    @has_access
    def insert_compound_by_file(self):
        self.logger.debug("in insert_compound_by_file with request %s", request)
        self.set_db_session(request)
        data = {}
                
        error = None

        # build map of form variables to send back to populate page
        for item in request.form:
            data[item] = request.form[item]
            
        if 'id_file' not in request.files:
            error = 'No file selected to upload.'
        else:         
            file = request.files['id_file']
            data['id_file'] = file
        
            if file.filename == '':
                error = 'No file selected to upload.'
            else:    
                if file and self.allowed_file(file.filename):                             
                    try:
                        # check and save the file
                        file_name = secure_filename(file.filename)                                                           
                                         
                        if not os.path.exists(UPLOAD_DIRECTORY):
                            os.makedirs(UPLOAD_DIRECTORY)
            
                        new_file = os.path.join(UPLOAD_DIRECTORY, file_name)
                        file.save(new_file)                             
                        user_dir_abs = os.path.abspath(UPLOAD_DIRECTORY) 
                        self.logger.debug("Compounds file uploaded to %s", user_dir_abs)
                        # do insert/update and return a report to UI
                        data['user_msg'] = self.insert_multiple_compounds(new_file)

                    except Exception as e: 
                        self.logger.exception(e)
                        error = 'Error: ' + str(e)
                else:
                    error = "Wrong file type; please upload a plain text csv file with a valid extension."
           
        if error is not None:
            data['user_msg'] = [error]

        self.db_session.close()
        return self.render_template("compound/compounds.html", data=data)

    
        
    @expose('compound/<id>/group/<group_id>', methods=['GET','POST'])
    @has_access
    def compound_class(self, id, group_id):
        self.set_db_session(request)
        data = {}
        data["compound_id"] = id
        data["group_id"] = group_id
        data = self.get_compound_class_data(data)
        self.db_session.close()
        return self.render_template("compound/compound_class.html", data=data)

    @expose("/compound/group/compound/delete", methods=["POST"])
    @has_access
    def delete_compound_class_compound(self):
        self.set_db_session(request)
        data = {}
        self.logger.debug("Request %s", request.form)          
        id = request.form["compound_id"]
        group_id = request.form["compound_class_id"]     
        ids = request.form.getlist('remove_compound_class')
        try:     
            if ids is not None and len(ids) > 0:           
                self.delete_rows_by_id(CompoundClassCompound, ids)
                flash("Compounds(s) removed from group")  
            else:
                flash("No compounds selected to remove" )     
        except Exception as e:      
            self.logger.error("Error removing compound from group %s", str(e))
            data['error'] = str(e)
        data["compound_id"] = id
        data["group_id"] = group_id
        data = self.get_compound_class_data(data)
        self.db_session.close()
        return self.render_template("compound/compound_class.html", data=data)
    
    @expose("/compound/group/annotation_method/delete", methods=["POST"])
    @has_access
    def delete_compound_class_annotation_method(self):
        self.set_db_session(request)
        data = {}
        self.logger.debug("Request %s", request.form)          
        id = request.form["compound_id"]
        group_id = request.form["compound_class_id"]     
        ids = request.form.getlist('remove_annotation_method_group')

        data["compound_id"] = id
        data["group_id"] = group_id
        data = self.get_compound_class_data(data)
        self.db_session.close()
        return self.render_template("compound/compound_class.html", data=data)
    

    @expose('/add_compound_to_group', methods=['POST'])
    @has_access
    def add_compound_to_group(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.set_db_session(request)
        data = {}
        error = None
        try:
            if 'compound_id' in request.form and 'compound_class_id' in request.form:
                data['user_msg'] = self.add_compound_to_compound_class(request.form['compound_id'],request.form['compound_class_id'])

        except Exception as e:
            self.logger.exception(e)
            error = 'Error: ' + str(e)

        if error is not None:
            data['user_msg'] = [error]


        self.db_session.close()
        return jsonify(data)

    def get_compound_class_data(self, data_dict):
        self.set_db_session(request)
        try:
            group_id = data_dict['group_id']
            data_dict['group'] = self.get_compound_class(group_id)
            data_dict['annotation_methods'] = self.get_annotation_methods()
            #data_dict['group_annotation_methods'] = self.get_compound_class_annotation_methods(group_id)
            data_dict['group_compounds'] = self.get_compound_class_compounds(group_id)
           
        except Exception as e:
            self.logger.exception(e)
            data_dict['error'] = str(e)
        self.logger.debug("compound_class data is %s", data_dict)
        return data_dict
    
    def allowed_file(self, filename):
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
                  
    def flask_form_to_compound_update(self, form): 
        """
        Takes a request.form object and returns two update objects
        having removed the 'csrf_token'
        :param form: a Flask request.form object
        :return: the compound and compound_external_dbs list of key/value pairs for update
        """
        compound_dict = {}
        ext_refs = []
 
        for key in form.keys(): 
            val = form.get(key)
            # putting this check here to get round the problem of 
            # database null values being converted to string 'None':
            if val and val != 'None':     
                # if key starts with 'db_' it's an external db ref
                if key.startswith('db_'):               
                    # could be several in one string so split them out
                    vals = val.split(',')
                    self.logger.debug("Got multiples %s", vals)
                    for v in vals:
                        ext_refs_dict = {}   
                        ext_refs_dict['compound_id'] = form.get('id')
                        ext_refs_dict['external_db_id'] = int(key[3:])
                        ext_refs_dict['database_ref'] = v.strip()
                        ext_refs.append(ext_refs_dict)
                else:
                    compound_dict[key] = val
        
        compound_dict.pop("csrf_token")
            
        return compound_dict, ext_refs
  

    def format_compound_external_dbs(self, id):
        # merge all external dbs with values for this compound
        existing = self.get_compound_ext_refs(id)
          
        all = self.get_external_dbs()
        for db in all:
            db['database_refs'] = []
            db['links'] = []
            for e in existing:
                if e['db_id']==db['db_id']:
                    db_ref = e['database_ref']
                    db_url = db['url']
                    link = db_url.replace('{}', db_ref)
                    map = {}
                    map['link'] = link
                    map['ref'] = db_ref
                    db['links'].append(map)
                    db['database_refs'].append(db_ref)
                    print(link)
                   
        return all
    
    def format_annotation_compounds(self, id):
       
        all = self.get_annotation_compounds(id)
        return all
                                            
    def get_compound_references(self, id):              
        # format a compound's related external dbs and datasets
        entity_list = self.get_relations_by_fk('compound_external_db', 'compound_id', id, with_relations=True )
             
        external_dbs = []
        for entity in entity_list:
            # format external db reference for display
            map = entity['relations']['external_db']
            db_ref = entity['database_ref']
            db_url = entity['relations']['external_db']['url']
            map['link'] = db_url.replace('{}', db_ref)
           
            entity.update(map)
            external_dbs.append(entity)          
              
        return external_dbs
      
    @expose('/chemical_standard_dataset/<id>')
    @has_access
    def chemical_standard_dataset(self, id):
        self.set_db_session(request)
        data = {}
        try:       
            data = self.get_peaklists_for_dataset(id)
        except Exception as e:
            print(e)
            data['error'] = str(e)

        self.db_session.close()
        return self.render_template(
            "compound/chemical_standard_dataset.html", data=data)
     
    @expose('/table/json/')
    @has_access
    def get_table_json(self):
        '''
        Called via ajax javascript request in UI
        '''
        self.set_db_session(request)
        json_data = json.dumps({"data":[[""]], "columns":[""]})   
        try:
            
            df = self.get_compounds_with_ds_counts()
            # make a link out of the display name column
            if not df.empty:

                df['name'] = [
                    ''.join(['<a href="' + url_for(".compound",id=x) + '"', '"/>', y, '</a>']) for x, y in zip(df['id'], df['name'])]
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

    def get_peaklists_for_dataset(self,chemical_standard_dataset_id):
        """
        Queries database for dataset related peaklists
        :return: a dictionary containing all the data fields which are
        required to populate the chemical_standard_dataset view
        """
        data = {}
        try:

            compound_cols = ["id", "name"]
            peaklist_cols = ["mz", "intensity", "rt_seconds"]
            dataset_cols = ["chemical_standard_dataset_id", "source_file","ionisation","collision_energy","acquired_date"]

            stmt2 = self.db_session.query(Compound, ChemicalStandardDataset.id.label("chemical_standard_dataset_id"), ChemicalStandardDataset.acquired_date,
                                   ChemicalStandardDataset.collision_energy,
                                  ChemicalStandardDataset.source_file, ChemicalStandardPeakList.id.label("chemical_standard_peaklist_id"), ChemicalStandardPeakList.rt_seconds,
                                  ChemicalStandardPeakList.mz, ChemicalStandardPeakList.intensity) \
                .select_from(ChemicalStandardDataset) \
                .filter(ChemicalStandardDataset.id==chemical_standard_dataset_id) \
                .outerjoin(Compound) \
                .outerjoin(ChemicalStandardPeakList) \
                .statement

            peaklists = pd.read_sql(sql=stmt2, con=session.connection())
            if not peaklists.empty:
                data["chemical_standard_dataset"] = peaklists[dataset_cols].iloc[0].to_dict()
                data["compound"] = peaklists[compound_cols].iloc[0].to_dict()
                chemical_standard_peaklist = peaklists[peaklist_cols]

                data["chemical_standard_peaklist"] = chemical_standard_peaklist.to_dict(orient="list")


        except:
            self.db_session.rollback()
            raise

        return data

    
    def get_datasets_peaklists_for_compound(self,compound_id):
        
        """
        Queries database for related datasets and peaklists
        :return: a dictionary containing all the data fields
        required to populate the compound view
        """

        data = {}
        try:
            params = {"id" : compound_id}
            stmt2 = text("SELECT * from v_compound_with_peaklists WHERE id = :id")
            self.logger.debug("Getting datasets/peaks for compound %s", stmt2)
            peaklists = pd.read_sql(sql=stmt2, params=params, con=self.db_session.connection())

            self.logger.debug(peaklists.columns)

            if not peaklists.empty:

                compound_cols = ["id", "name", "chemical_formula", "monoisotopic_mass", "inchi", "inchi_key","iupac","smiles","log_p"]
                dataset_cols = ["chemical_standard_dataset_id","source_file","collision_energy","acquired_date"]
                peaklist_cols = ["mz", "intensity", "rt_seconds"]

                data["compound"] = peaklists[compound_cols].iloc[0].to_dict()

                no_datasets = peaklists["chemical_standard_dataset_id"].isnull().all()

                data["chemical_standard_datasets"] = []
                if not no_datasets:

                    ms_datasets = peaklists["chemical_standard_dataset_id"].unique().tolist()
                    self.logger.debug("unique chemical_standard_dataset ids %s",ms_datasets)
                    for i in ms_datasets:
                        chemical_standard_dataset = peaklists[peaklists.chemical_standard_dataset_id==i][dataset_cols]

                        if not chemical_standard_dataset.empty:
                            # this step is necessary because columns containing nulls
                            # are coerced to floats by pandas, so must restore them

                            chemical_standard_dataset = chemical_standard_dataset.astype({"chemical_standard_dataset_id":"int32"})

                            chemical_standard_peaklist = peaklists[peaklists.chemical_standard_dataset_id==i][peaklist_cols]

                            peaks = chemical_standard_peaklist.to_dict(orient="list")

                            dataset = chemical_standard_dataset.to_dict(orient="records")[0]
                            dataset.update(peaks)
                            data["chemical_standard_datasets"].append(dataset)

        except:
            self.db_session.rollback()
            raise

        return data


    def check_external_dbs(self,names_list):

        """
        Check existing databases against input list
        :return: list of dicts of matching external dbs we have
        """
        all_dbs = self.get_external_dbs()
        database_refs = []
        for row in all_dbs:
            if row["db_name"].upper() in (name.upper() for name in names_list):
                database_refs.append(row)

        self.logger.debug("Valid database refs are %s", database_refs)
        return database_refs

    def check_annotation_methods(self,names_list):

        """
        Check existing annotation_method names against input list
        :return: list of dicts of id/name of annotation_methods
        """
        all_annotation_methods = self.get_annotation_methods()
        valid_annotation_methods = []
        for row in all_annotation_methods:
            if row["annotation_method_name"].upper() in (name.upper() for name in names_list):
                valid_annotation_methods.append(row)

        return valid_annotation_methods


    def check_compound_properties(self,headings):
        base_headings = []
        unused_headings = []
        db_headings = []
        annotation_compound_headings = []

        for heading in headings:
            # master list is in phenomedb.models:
            if heading in COMPOUND_BASIC_HEADINGS:
                base_headings.append(heading)
            elif heading in COMPOUND_ASSAY_HEADINGS:
                annotation_compound_headings.append(heading)
            elif heading in COMPOUND_DB_HEADINGS:
                db_headings.append(heading)

            else:
                unused_headings.append(heading)

        db_headings = self.check_external_dbs(db_headings)
        annotation_compound_headings = self.check_annotation_methods(annotation_compound_headings)

        self.logger.debug("Base headings are %s", base_headings)
        self.logger.debug("DB headings are %s", db_headings)
        self.logger.debug("Compound AnnotationMethod headings are %s", annotation_compound_headings )
        self.logger.debug("Other headings are %s", unused_headings )
        return base_headings, db_headings, annotation_compound_headings, unused_headings


    def add_compound_to_compound_class(self,compound_id,compound_class_id):

        self.logger.debug("Trying to adding CompoundClassCompound")

        try:
            compound_class_compound = self.db_session.query(CompoundClassCompound).filter(CompoundClassCompound.compound_id==compound_id,CompoundClassCompound.compound_class_id==compound_class_id).first()

            if compound_class_compound:
                raise('CompoundClassCompound exists! compound:' + str(compound_id) + ' compound_class: ' + str(compound_class_id))
            else:
                compound_class_compound = CompoundClassCompound(compound_id=compound_id,compound_class_id=compound_class_id)
                self.db_session.add(compound_class_compound)
                self.db_session.flush()
                self.logger.debug("CompoundClassCompound added!")
        except:
            self.db_session.rollback()

        self.db_session.commit()

    def remove_compound_from_compound_class(self,compound_id,compound_class_id):

        self.logger.debug("Trying to remove a CompoundClassCompound")

        try:
            compound_class_compound = self.db_session.query(CompoundClassCompound) \
                .filter(CompoundClassCompound.compound_id==compound_id,CompoundClassCompound.compound_class_id==compound_class_id) \
                .first()

            if compound_class_compound:
                self.db_session.delete(compound_class_compound)
            else:
                raise("No CompoundClassCompound")
        except:
            self.db_session.rollback()
            raise

        self.db_session.commit()


    def insert_multiple_compounds(self,file_name):
        """
        Takes an uploaded CSV (possibly CTS service lookup)
        to add to database
        :param file_name: a csv file containing compounds
        :return: a report on how it all went (a list)
        """

        df = pd.read_csv(file_name)

        report = ["Compound import from {}".format(file_name)]
        new_compounds = []
        old_compounds = []
        skipped_compounds = []
        new_db_refs = []
        new_annotation_compound_refs = []

        # get rid of pandas NaNs cos MySQL can"t cope
        values = {"monoisotopic_mass": 0, "inchi_key": "", "inchi": "", "chemical_formula": ""}
        df.fillna(value=values,inplace=True)

        headings = list(df.columns.values)

        # filter out the columns into compound properties, external dbs, annotation_method names:
        valid_headings, ext_refs, annotation_compound_headings, unused_headings = self.check_compound_properties(headings)

        if unused_headings:
            report.append("Disregarded columns in input: {}".format(unused_headings))

        if len(valid_headings) != len(COMPOUND_BASIC_HEADINGS):
            raise Exception("File is missing one or more required compound properties " + str(COMPOUND_BASIC_HEADINGS))
        else:
            records = df.to_dict("records")

            for record in records:
                #logger.debug("Raw %s", record)
                try:

                    name = record["name"].strip()
                    inchi_key = record["inchi_key"].strip()

                    # name and inchi_key form the unique key in the database so one or both must be present
                    if len(name) == 0 and len(inchi_key) == 0:
                        skipped_compounds.append(name)
                        self.logger.debug("Missing inchi_key or name for %s",name)
                        continue

                    chemical_formula = str(record["chemical_formula"]).strip().replace("{","").replace("}","").replace("_","").replace("^","")
                    monoisotopic_mass = round(float(record["monoisotopic_mass"]),7)
                    inchi = record["inchi"].strip()

                    if inchi_key == "Unknown" and name != "":
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.name==name) \
                            .first()
                    elif inchi_key != "Unknown":
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.inchi_key==inchi_key) \
                            .first()

                    if not compound:
                        compound = Compound(name=name,
                                            inchi=inchi,
                                            inchi_key=inchi_key,
                                            monoisotopic_mass=monoisotopic_mass,
                                            chemical_formula=chemical_formula)
                        self.db_session.add(compound)
                        self.db_session.flush()

                    if inchi_key != "Unknown":

                        inchi_key_backbone = compound.get_inchi_key_backbone()

                        stereo_group = self.db_session.query(CompoundClass) \
                            .filter(CompoundClass.inchi_key_backbone==inchi_key_backbone) \
                            .filter(CompoundClass.type==CompoundClass.CompoundClassType.isomer) \
                            .first()
                        if not stereo_group:

                            self.logger.debug("Adding compound group %s %s",inchi_key_backbone)
                            stereo_group = CompoundClass(name="",
                                                         inchi_key_backbone=inchi_key_backbone,
                                                         type=CompoundClass.CompoundClassType.isomer)
                            self.db_session.add(stereo_group)
                            self.db_session.flush()

                        compound_class_compound = self.db_session.query(CompoundClassCompound) \
                            .filter(CompoundClassCompound.compound_id==compound.id) \
                            .filter(CompoundClassCompound.compound_class_id==stereo_group.id) \
                            .first()

                        if not compound_class_compound:
                            compound_class_compound = CompoundClassCompound(compound_id=compound.id,
                                                                            compound_class_id=stereo_group.id)
                            self.db_session.add(compound_class_compound)
                            self.db_session.flush()


                    '''if record["LipidMaps Category"].strip() != "" and record["LipidMaps Main Class"].strip() != "" and record["LipidMaps Sub Class"].strip() != "":
                        lipid_maps_group = self.db_session.query(CompoundClass) \
                            .filter(CompoundClass.type==CompoundClass.CompoundClassType.lipidmaps) \
                            .filter(CompoundClass.sub_class==record["LipidMaps Sub Class"].strip()) \
                            .filter(CompoundClass.lipidmaps_4==record["LipidMaps Class 4"].strip()) \
                            .first()
    
                        if not lipid_maps_group:
    
                            lipid_maps_group = CompoundClass(type==CompoundClass.CompoundClassType.lipidmaps,'''


                except Exception as e:
                    skipped_compounds.append(name)
                    self.logger.debug("Exception: for %s: %s", record["name"], e)
                    continue

            self.db_session.commit()

            session_rollback = False

            # get the external database refs
            self.logger.debug("Getting external database references")
            for record in records:
                try:
                    if record['name'] == "":
                        break
                    stereo_group = None
                    compound = None
                    name = record["name"].strip()
                    inchi_key = record["inchi_key"].strip()

                    if not name and not inchi_key:
                        self.logger.debug("All missing for inchi_key %s, name %s", inchi_key,name)
                        continue

                    if inchi_key == "Unknown" and name != "":
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.name==name) \
                            .first()
                    elif inchi_key != "Unknown":
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.inchi_key==inchi_key) \
                            .first()

                    if not compound:
                        self.logger.debug("Compound missing for inchi_key %s, name %s ", inchi_key,name)

                    inchi_key_backbone = compound.get_inchi_key_backbone()

                    for ed in ext_refs:
                        database_ref = str(record[ed["db_name"]]).strip().rstrip(".0")
                        #logger.debug("Got external db ref %s", database_ref)
                        if database_ref and database_ref != "No result" and database_ref != "nan":

                            ced = self.db_session.query(CompoundExternalDB).filter(CompoundExternalDB.compound_id==compound.id) \
                                .filter(CompoundExternalDB.external_db_id==ed["db_id"]) \
                                .filter(CompoundExternalDB.database_ref==database_ref) \
                                .first()
                            if not ced:
                                ced = CompoundExternalDB(compound_id=compound.id, external_db_id=ed["db_id"], database_ref=database_ref)
                                self.db_session.add(ced)
                                self.db_session.flush()
                                self.logger.debug("%s database ref %s for %s inserted", ed["db_name"], database_ref, name)
                                new_db_refs.append(name)
                            else:
                                self.logger.debug("%s ref %s for %s exists already", ed["db_name"], database_ref, name)

                    for cah in annotation_compound_headings:
                        feature_name = str(record[cah["annotation_method_name"]]).strip()

                        if feature_name and feature_name != "No result" and feature_name != "nan":

                            c_ass = self.db_session.query(AnnotationCompound).filter(AnnotationCompound.compound_id==compound.id) \
                                .filter(AnnotationCompound.feature_name==feature_name) \
                                .filter(AnnotationCompound.cpd_name==feature_name) \
                                .first()
                            if not c_ass:
                                c_ass = AnnotationCompound(compound_id=compound.id, annotation_method_id=cah["annotation_method_id"], feature_name=feature_name,cpd_name=feature_name)
                                self.db_session.add(c_ass)
                                self.db_session.flush()
                                self.logger.debug("%s AnnotationCompound feature_name %s for %s inserted", cah["annotation_method_name"], feature_name, name)
                                new_annotation_compound_refs.append(name)
                            else:
                                self.logger.debug("%s AnnotationCompound feature_name %s for %s exists already", cah["annotation_method_name"], feature_name, name)


                except Exception as e:
                    self.logger.debug("Can't add external_db or annotation_method ref for %s", record["inchi_key"])
                    self.logger.debug("Error: %s", str(e))
                    self.db_session.rollback()
                    session_rollback = True


            self.db_session.commit()


        report.append("Updated {} compounds".format(len(old_compounds)))
        report.append("Inserted {} compounds".format(len(new_compounds)))
        report.append("{} compounds could not be inserted due to errors".format(len(skipped_compounds)))
        if not session_rollback:
            report.append("Inserted {} external database references".format(len(new_db_refs)))
            report.append("Inserted {} compound annotation_methods".format(len(new_annotation_compound_refs)))
        else:
            report.append('Transaction commit failed, no annotation_method mappings or external db references added!')

        return report


 
    def get_external_dbs(self):
        """
        get all external databases with name mapping as shown
        :return: the result as list of dicts
        """
        results = []
        try:
            row = self.db_session.query(ExternalDB.id.label("db_id"), ExternalDB.name.label("db_name"), ExternalDB.url).all()
            for r in row:
                results.append(dict(zip(r.keys(), r)))

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results
    
    def get_annotation_methods(self):
        """
        get all annotation_method name mapping as shown
        :return: the result as list of dicts
        """
        results = []
        other = []
        try:
            row = self.db_session.query(AnnotationMethod.id.label("annotation_method_id"), AnnotationMethod.name.label("annotation_method_name")).all()
            for r in row:
                results.append(dict(zip(r.keys(), r)))
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results

    def get_compound_ext_refs(self,compound_id):
        """
        get the external databases for a given compound id
        :param: the compound id
        :return: the result as list of dicts
        """

        results = []
        try:
            row = self.db_session.query(CompoundExternalDB.database_ref, ExternalDB.id.label("db_id"), ExternalDB.name.label("db_name"), ExternalDB.url) \
                .filter(Compound.id==int(compound_id)) \
                .join(ExternalDB) \
                .join(CompoundExternalDB.compound) \
                .all()
            for r in row:
                results.append(dict(zip(r.keys(), r)))

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results


    def get_compound_class_compounds(self,group_id):
        """
        get the compounds for a given group id
        :param: the compounds
        :return: the result as list of dicts
        """
        results = []

        try:
            row = self.db_session.query(CompoundClassCompound.id,Compound.id.label("compound_id"), Compound.name, Compound.inchi, Compound.inchi_key, Compound.monoisotopic_mass) \
                .filter(CompoundClassCompound.compound_class_id==int(group_id)) \
                .join(CompoundClassCompound) \
                .all()
            for r in row:
                results.append(dict(zip(r.keys(), r)))

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results

    def get_annotation_compounds(self,compound_id):
        """
        get the annotation_methods for a given compound id
        :param: the compound id
        :return: the result as list of dicts
        """

        results = []
        try:
            annotation_methods = self.db_session.query(Annotation.id,
                                                       Annotation.cpd_name,
                                                        Annotation.multi_compound_operator,
                                                       Annotation.version.label('version'),
                                                       HarmonisedAnnotation.assay_id,
                                                       Assay.name.label("assay_name"),
                                                       AnnotationMethod.id.label("annotation_method_id"),
                                                       AnnotationMethod.name.label("annotation_method_name"),
                                                       AnnotationMethod.name.label("annotation_method_name")) \
                .join(HarmonisedAnnotation,HarmonisedAnnotation.id==Annotation.harmonised_annotation_id) \
                .join(AnnotationMethod,AnnotationMethod.id==HarmonisedAnnotation.annotation_method_id) \
                .join(Assay,Assay.id==HarmonisedAnnotation.assay_id) \
                .join(AnnotationCompound) \
                .filter(AnnotationCompound.compound_id==int(compound_id)).all()

            self.logger.debug("annotation_methods :" + str(annotation_methods))

            for r in annotation_methods:
                results.append(dict(zip(r.keys(), r)))

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results

    def get_compound_class(self,compound_class_id):
        result = None
        try:
            compound_class = self.db_session.query(CompoundClass) \
                .filter(CompoundClass.id==compound_class_id) \
                .first()

            return compound_class
        except:
            raise


    def get_compound_classes(self,compound_id):
        """
        get the compound_classes for a given compound id
        :param: the compound id
        :return: the result as list of dicts
        """
        results = []
        try:
            compound_classes = self.db_session.query(Compound.id.label("compound_id"), CompoundClass.id.label("compound_class_id"),
                                            CompoundClass.inchi_key_backbone, CompoundClass.name, CompoundClass.type,
                                            CompoundClass.category,
                                            CompoundClass.main_class,
                                            CompoundClass.sub_class) \
                .join(CompoundClassCompound,CompoundClassCompound.compound_class_id==CompoundClass.id) \
                .join(Compound,CompoundClassCompound.compound_id==Compound.id) \
                .filter(Compound.id==int(compound_id)) \
                .all()
            for r in compound_classes:
                results.append(dict(zip(r.keys(), r)))

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results
    
    def get_compounds_with_ds_counts(self):
        """
        Fetch compounds plus a count of related datasets
        :return: result as a pandas dataframe
        """
        df = None
        try:

            df = self.sql_to_dataframe("select * from v_compound_with_dataset_counts")
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df

compound_bp = Blueprint(
            VIEW_NAME, __name__,
            template_folder='../templates',
            static_folder='../templates/static',
            static_url_path='/static/phenomedb')
                      
v_appbuilder_view = CompoundView()
v_appbuilder_package = {"name": "Compounds",
                        "category": "PhenomeDB",
                        "view": v_appbuilder_view}

appbuilder_mitem = {"name": "Compounds",
                    "category": "PhenomeDB",
                    "category_icon": "fa-th",
                    "href": "/compoundview/"}

class CompoundPlugin(AirflowPlugin):
   
    name = VIEW_NAME
    
    # flask_blueprints and admin_views are AirflowPlugin properties
    flask_blueprints = [compound_bp]
    #admin_views = [compound_view]
    #admin_views = []
    appbuilder_views = [v_appbuilder_package]
    #appbuilder_menu_items = [appbuilder_mitem]
