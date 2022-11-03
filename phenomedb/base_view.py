from flask_appbuilder import BaseView as AppBuilderBaseView
import pandas as pd
import logging
import phenomedb.database as db
from sqlalchemy import text
from sqlalchemy.orm import class_mapper
from phenomedb.models import Base
from flask import request, make_response, render_template_string, jsonify
import os
from phenomedb.config import config
from phenomedb.cache import Cache

class PhenomeDBBaseView(AppBuilderBaseView):
    """The base view for all PhenomeDB views, for common methods and db_session usage.
       Extends the :class:`flask_appbuilder.BaseView`.

    """    


    def __init__(self):
        super().__init__()
        self.cache = Cache()

    def set_db_session(self,request):
        """Set the db_session. If db_env is in the get params, set it.

        :param request: The flask request object.
        :type request: :class:`flask.request`
        """        
        
        db_env = db.DB_PROD
        if 'db_env' in request.form.keys():
            db_env = request.form.get('db_env')
        
        self.logger.debug("REQUEST %s", request)
        self.set_db(db_env)

    def render_template_to_html_or_json(self,template,data={}):

        if 'render_json' in request.form.keys():
            self.render_json = request.form.get('render_json')
        else:
            self.render_json = False

        if self.render_json:
            html = render_template_string(template,data=data)
            data = {'html':html,'render_json':True}
            return jsonify(data)
        else:
            return self.render_template(template, data=data)

    def set_db(self, db_env):
        """Set the db using the db_env

        :param db_env: "PROD", "BETA", or "TEST", default "PROD"
        :type db_env: str
        """        
       # alternative to using request
       # e.g. self.set_db( database.DB_TEST )
        self.db_session = db.get_db_session(db_env)
        self.db_env = db_env
        self.logger.debug("db_env = "+ self.db_env)

    def configure_logging(self,identifier='phenomedb', log_file='phenomedb.log', level=logging.DEBUG):
        """Setup a logger.

        :param identifier: an identifier for your messages in the log, defaults to 'phenomedb'.
        :type identifier: str, optional
        :param log_file: file to log to at location specified in config.ini; (will create this dir if necessary), defaults to 'phenomedb.log'.
        :type log_file: str, optional
        :param level: log level, logging.INFO, logging.ERROR, logging.WARNING, defaults to logging.DEBUG.
        :type level: int, optional
        :return: the logger.
        :rtype: :class:`logging.logger`
        """  
        self.logger = None
        try:

            self.logger = logging.getLogger(identifier)

            log_dir =  config['LOGGING']['dir']
            log_file = os.path.join(log_dir, log_file)

            os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(log_file, mode="a", encoding="utf-8", delay=False)

            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            fh.setFormatter(formatter)

            self.logger.addHandler(fh)
            self.logger.setLevel(level)
            #print("Initialised " + identifier + " to log to", log_file)
        except OSError as e:
            print('Error configuring logging', e)

    
    def handle_json_error(self, e):
        """Handle a json error.

        :param e: The error message dictionary.
        :type e: dict
        :return: The response 400.
        :rtype: :class:`flask.response`
        """        
        response_body = {}
        error_msg = getattr(e, "message", repr(e))
        self.logger.error(error_msg)  
        response_body["error"] = error_msg
        self.db_session.close()
        return make_response(response_body, 400)
    
    def get_all_by_model(self, table_name):
        """Get all records by table_name.

        :param table_name: The name of the table to query.
        :type table_name: str
        :return: The list of model records.
        :rtype: list
        """        
      
        result = None
        try:
            table_class = self.get_class_by_tablename(table_name)
            result = self.db_session.query(table_class).all()
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return result

    def execute_sql(self,sql,params={}):
        """Execute an SQL statement

        :param sql: The SQL statement.
        :type sql: str
        :param params: The SQL parameters, defaults to {}.
        :type params: dict, optional
        :return: List of result row dictionaries.
        :rtype: list
        """        
        results = []

        try:
            result = self.db_session.execute(sql,params).fetchall()
            results = [dict(zip(r.keys(),r)) for r in result]
            #for r in result:
            #results.append(dict(zip(r.keys(), r)))
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return results


    def sql_to_dataframe(self,sql, params={}):
        """Execute an sql statement and return as pandas dataframe.

        :param sql: The SQL statement.
        :type sql: str
        :param params: The SQL parameters, defaults to {}.
        :type params: dict, optional
        :return: Pandas dataframe of results.
        :rtype: :class:`pandas.DataFrame`
        """        
        df = pd.DataFrame()
        
        try:
            stmt = text(sql)
            df = pd.read_sql(sql=stmt, params=params,con=self.db_session.connection())

            for col in df.columns:
                df[col] = df[col].astype(str).replace('nan','')

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df

    def get_entity_as_df(self,table_name, id):
        """Fetch a single row from a table.

        :param table_name: The name of the table.
        :type table_name: str
        :param id: The entity id.
        :type id: int
        :return: Pandas dataframe of results.
        :rtype: :class:`pandas.DataFrame`
        """        
        df = pd.DataFrame()
        try:
            table_class = self.get_class_by_tablename(table_name)
            stmt = self.db_session.query(table_class) \
                .filter_by(id=id) \
                .statement

            df = pd.read_sql(sql = stmt, con=self.db_session.connection())
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return df

    def get_entity_as_dict(self,table_name, entity_id, with_relations=False):
        """Represent a SQLAlchemy mapped table object and optionally its related table entries as a dictionary of column:value mappings

        :param table_name: The name of the table.
        :type table_name: str
        :param id: The entity id.
        :type id: int
        :param with_relations: add top-level related entities to result, defaults to False
        :type with_relations: bool, optional
        :return: Results as dictionary
        :rtype: dict
        """        
        
        table_class = self.get_class_by_tablename(table_name)
        entity_dict = {}
        try:
            entity = self.db_session.query(table_class) \
                .filter_by(id=int(entity_id)) \
                .one()
            self.logger.debug("entity is a %s", type(entity))
            entity_dict = self.attribute_dict(entity)
            if with_relations:
                entity_dict["relations"] = self.relationship_dict(entity)

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return entity_dict


    def get_entities_as_dicts(self,entity_list):
        """Convert a SQLAlchemy result list of objects into a list of dictionaries for ease of use in the web interface  - note no related entities

        :param entity_list: Results list of query.
        :type entity_list: list
        :return: list of dictionaries.
        :rtype: list
        """        

        result = []
        for entity in entity_list:
            table_map = self.attribute_dict(entity)
            result.append(table_map)
        return result

    def get_table_columns(self,table_name):
        """Get the columns of a table.

        :param table_name: The table name.
        :type table_name: str
        :return: Dictionary of attribute names and types.
        :rtype: dict
        """        
        table_class = self.get_class_by_tablename(table_name)
        #logger.debug('cols %s', table_class.__table__.columns)
        attr_dict = {}
        for col in table_class.__table__.columns:
            attr_dict[col.name] = str(col.type)
        #return table_class.__table__.columns.keys()
        return attr_dict


    def get_table_names(self):
        """Get a list of all tables in database

        :return: list of table names.
        :rtype: list
        """        
        
        metadata = Base.metadata
        flat_list = [t.name for t in metadata.sorted_tables]
        # need extra step to sort alphabetically 
        flat_list.sort()
        return flat_list

    def get_class_by_tablename(self,table_name):
        """Get model class by table name.

        :param table_name: The name of the table.
        :type table_name: str
        :return: The related model class reference.
        :rtype: :class:`phenomedb.models.*`
        """        
        
        for item in Base._decl_class_registry.values():
            if hasattr(item, '__tablename__') and item.__tablename__ == table_name:
                return item

    def attribute_dict(self,orm_object):
        """get an ORM object"s (eg a phenomedb.models.Project) attributes and return as dict

        :param orm_object: The model object.
        :type orm_object: :class:`phenomedb.models.*`
        :return: The dictionary version of the model.
        :rtype: dict
        """

        attr_dict = {}

        if orm_object:
        #print("type of entity is", type(entity))
            mapper = class_mapper(orm_object.__class__)

            #date = datetime.strptime("28-03-2017", "%d-%m-%Y")
            #form_data.add("date", "{:%Y-%m-%d %H:%M:%S}".format(date))

            for col in mapper.columns.keys():
                self.logger.debug("col key is %s", col)
                col_value = getattr(orm_object, col)
                #if isinstance(col_value, datetime):
                #col_value = col_value.strftime("%d/%m/%Y %H:%M")
                attr_dict[col] = col_value

        return attr_dict

    def relationship_dict(self,orm_object):
        """Get an ORM object"s related entities and return as dict

        :param orm_object: The model object.
        :type orm_object: :class:`phenomedb.models.*`
        :return: The attribute dictionary plus related entities.
        :rtype: dict
        """        
        relations_dict = {}
        #print("type of entity is", type(entity))
        mapper = class_mapper(orm_object.__class__)
        for name, relation in mapper.relationships.items():
            related_entity = getattr(orm_object, name)
            if relation.uselist:
                relations_dict[name] = self.get_entities_as_dicts(related_entity)
            else:
                relations_dict[name] = self.attribute_dict(related_entity)
        #logger.debug("got relations %s", relations_dict)
        return relations_dict

    def foreign_keys(self,cl, key_name=None):
        """Finds the foreign key columns in an ORM class.

        :param cl: The model class.
        :type cl: :class:`phenomedb.models.*`
        :param key_name: optionally specify the key to find, defaults to None
        :type key_name: str, optional
        :return: The column name/value pairs as a dictionary.
        :rtype: dict
        """        
        
        fk_dict = {}
        mapper = class_mapper(cl)
        if key_name is None:
            fk_dict = dict((column.name, column) for column in mapper.columns if column.foreign_keys)
        else:
            fk_dict = dict((column.name, column) for column in mapper.columns if column.foreign_keys and column.name==key_name)
        return fk_dict

    def get_relations_by_fk(self,table_name, key_name, key_value, with_relations=False):
        """Get the table rows where the key==value

        :param table_name: The table name.
        :type table_name: str
        :param key_name: The id field to link on, eg "compound_id"
        :type key_name: str
        :param key_value: a value for the key id
        :type key_value: int
        :param with_relations: include the first level related entities in the result, defaults to False
        :type with_relations: bool, optional
        :return: The list of results.
        :rtype: list
        """        
        
        results_list = []
        try:
            table_class = self.get_class_by_tablename(table_name)
            #print("type of table class is", type(table_class))
            fk_col = self.foreign_keys(table_class)

            results = self.db_session.query(table_class) \
                .filter(fk_col[key_name] == key_value) \
                .all()

            self.logger.debug("relations_by_fk: got %d results for %s" % (len(results), table_name))
            for r in results:
                map = self.attribute_dict(r)
                if with_relations:
                    map["relations"] = self.relationship_dict(r)
                results_list.append(map)

            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

        return results_list
    
    
 
  
    def flask_form_to_ORM_dict(self,form):
        """Takes a request.form object and returns a dictionary, having removed the csrf_token.

        :param form: the flask request.form object.
        :type form: :class:`Flask.request.Form`
        :return: The form key/value pairs as a dictionary.
        :rtype: dict
        """        
        entity_dict = {}

        for key in form.keys():
            val = form.get(key)
            # putting this check here to get round the problem of
            # database null values being converted to string "None":

            if val and val != "None":
                entity_dict[key] = form.get(key)

        # remove flask"s form security token
        if 'csrf_token' in entity_dict.keys():
            entity_dict.pop("csrf_token")

        if "db_env" in entity_dict.keys():
            entity_dict.pop("db_env")
        self.logger.debug("Form after cleaning to update %s", entity_dict)

        return entity_dict

    
    """
    def insert_lipids(self,file_name):

        df = pd.read_csv(file_name)

        report = ["Lipid import from {}".format(file_name)]
        new_compounds = []
        old_compounds = []
        skipped_compounds = []
        new_db_refs = []
        new_compound_assay_refs = []

        # get rid of pandas NaNs cos MySQL can"t cope
        values = {"exact_mass": 0, "inchi_key": "", "inchi": "", "chemical_formula": ""}
        df.fillna(value=values,inplace=True)

        headings = list(df.columns.values)

        # filter out the columns into compound properties, external dbs, assay names:
        valid_headings, ext_refs, compound_assay_headings, unused_headings = self.check_compound_properties(headings)

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
                        self.logger.debug("Missing inchi key and display name for %s",name)
                        continue

                    chemical_formula = str(record["chemical_formula"]).strip().replace("{","").replace("}","").replace("_","").replace("^","")
                    exact_mass = round(record["exact_mass"],7)
                    inchi = record["inchi"].strip()

                    if inchi == "Unknown":
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.name==name) \
                            .first()
                    else:
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.inchi_key==inchi_key) \
                            .first()
                    if not compound:
                        compound = Compound(name=name,
                                            inchi=inchi,
                                            inchi_key=inchi_key,
                                            exact_mass=exact_mass,
                                            chemical_formula=chemical_formula)
                        self.db_session.add(compound)
                        self.db_session.flush()

                    inchi_key_backbone = compound.get_inchi_key_backbone()

                    stereo_group = self.db_session.query(CompoundClass) \
                        .filter(CompoundClass.inchi_key_backbone==inchi_key_backbone) \
                        .filter(CompoundClass.exact_mass==compound.exact_mass) \
                        .filter(CompoundClass.type==CompoundClass.CompoundClassType.isomer) \
                        .first()
                    if not stereo_group:
                        self.logger.debug("Adding compound group %s %s",inchi_key_backbone,exact_mass)
                        stereo_group = CompoundClass(name="",
                                                     inchi_key_backbone=inchi_key_backbone,
                                                     exact_mass=compound.exact_mass,
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


                except Exception as e:
                    skipped_compounds.append(name)
                    self.logger.debug("Exception: for %s: %s", record["name"], e)
                    continue

            self.db_session.commit()

            # get the external database refs
            self.logger.debug("Getting external database references")
            for record in records:
                try:

                    stereo_group = None
                    compound = None
                    name = record["name"]
                    compound_inchi_key = record["inchi_key"]

                    if not name and not compound_inchi_key:
                        self.logger.debug("Compound name missing")
                        continue

                    if compound_inchi_key == "Unknown":
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.name==name) \
                            .first()
                    else:
                        compound = self.db_session.query(Compound) \
                            .filter(Compound.inchi_key==compound_inchi_key) \
                            .first()

                    if not compound:
                        self.logger.debug("Compound missing for inchi_key %s ", compound_inchi_key)

                    inchi_key_backbone = compound.get_inchi_key_backbone()

                    stereo_group = self.db_session.query(CompoundClass) \
                        .filter(CompoundClass.inchi_key_backbone==inchi_key_backbone) \
                        .filter(CompoundClass.exact_mass==compound.exact_mass) \
                        .filter(CompoundClass.type==CompoundClass.CompoundClassType.isomer) \
                        .first()

                    if not stereo_group:
                        self.logger.debug("Stereo compound group missing for inchi_key_backbone %s ", inchi_key_backbone)
                        continue

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

                    for cah in compound_assay_headings:
                        feature_name = str(record[cah["assay_name"]]).strip()

                        if feature_name and feature_name != "No result" and feature_name != "nan":

                            # CompoundAssay
                            c_ass = self.db_session.query(CompoundAssay).filter(CompoundAssay.compound_id==compound.id) \
                                .filter(CompoundAssay.feature_name==feature_name) \
                                .filter(CompoundAssay.cpd_name==feature_name) \
                                .first()
                            if not c_ass:
                                c_ass = CompoundAssay(compound_id=compound.id, assay_id=cah["assay_id"], feature_name=feature_name,cpd_name=feature_name)
                                self.db_session.add(c_ass)
                                session.flush()
                                self.logger.debug("%s CompoundAssay feature_name %s for %s inserted", cah["assay_name"], feature_name, name)
                                new_compound_assay_refs.append(name)
                            else:
                                self.logger.debug("%s CompoundAssay feature_name %s for %s exists already", cah["assay_name"], feature_name, name)


                except Exception as e:
                    self.logger.debug("Can't add external_db or assay ref for %s", record["inchi_key"])
                    self.logger.debug("Error: %s", str(e))
                    self.db_self.db_session.rollback()

            self.db_session.commit()

        #report.append("Updated " + ", ".join(old_compounds))
        report.append("Updated {} compounds".format(len(old_compounds)))
        #report.append("Inserted " + ", ".join(new_compounds))
        report.append("Inserted {} compounds".format(len(new_compounds)))
        #report.append("Skipped " + ", ".join(skipped_compounds))
        report.append("Inserted {} external database references".format(len(new_db_refs)))
        report.append("Inserted {} compound assays".format(len(new_compound_assay_refs)))
        report.append("{} compounds could not be inserted due to errors".format(len(skipped_compounds)))
        return report
    """
 
 
    def delete_rows_by_id(self,table_class, ids):
        """Delete rows from a table by id.

        :param table_class: The table name.
        :type table_class: str
        :param ids: A list of ids to delete.
        :type ids: list
        """        
        #table_class = utils.get_class_by_tablename(table_name)
        try:

            self.db_session.query(table_class) \
                .filter(table_class.id.in_(ids)) \
                .delete(synchronize_session='fetch')
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise



    def get_project_metadata_fields(self,project_id):
        """Get the metadata fields for a project.

        :param project_id: The id of the project.
        :type project_id: int
        :return: A list of dictionary metadata_fields for the project.
        :rtype: list
        """        
        
        metadata_vals = []
        try:

            stmt = text("SELECT * from v_metadata_fields WHERE project_id = :project_id") \
                .bindparams(project_id=project_id)

            results = self.db_session.execute(stmt)
            for row in results:
                metadata_vals.append(dict(zip(row.keys(), row)))
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        return metadata_vals


    def insert_entity(self, table_name, value_dict):
        """Create a new row in a table.

        :param table_name: The name of the table.
        :type table_name: str
        :param value_dict: A dictionary containing correctly mapped values.
        :type value_dict: dict
        :return: The newly inserted id.
        :rtype: int
        """        
        
        id = None

        try:
            table_class = self.get_class_by_tablename(table_name)
            print("inserting new row in", table_name)
            # create an instance and populate
            entity = table_class(**value_dict)
            # insert with ORM magic
            self.db_session.add(entity)
            self.db_session.commit()
            id = entity.id
            print("new row has id", id)
        except:
            self.db_session.rollback()
            raise

        return id

    def delete_entity(self,table_name, id):
        """Delete a row from a table.

        :param table_name: The name of the table.
        :type table_name: str
        :param id: The id of the row to delete.
        :type id: int
        """        
        
        try:
            table_class = self.get_class_by_tablename(table_name)

            entity = self.db_session.query(table_class).filter_by(id=id).one()
            self.db_session.delete(entity)
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise

    def update_entity(self,table_name, update_dict):
        """Update a single row in a table.

        :param table_name: The name of the table.
        :type table_name: str
        :param update_dict: The dictionary of the new values, including the id.
        :type update_dict: dict
        """        
        id = int(update_dict["id"])

        try :
            table_class = self.get_class_by_tablename(table_name)
            # set up the row to update:
            entity_query = self.db_session.query(table_class).filter_by(id=id)
            r = entity_query.first()
            print('entity to update', r)
            # do the update based on the dictionary
            entity_query.update(update_dict)
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
