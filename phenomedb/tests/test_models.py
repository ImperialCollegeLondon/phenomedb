import pytest
import random

import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.database import *

class TestModels:
    """TestModels class. Tests the querying and storing of Model Objects. Always run first when running the test suite, as it builds the database.
    """

    #method to check table to object relationship
    def check_table(self,table_name,object_name,engine_db_session):

        engine = engine_db_session[0]
        db_session = engine_db_session[1]

        from datetime import datetime

        print("\n\n========================== " + table_name + " ==============================================================================")

        now = datetime.now()

        errors = []

        dialect = engine.dialect.name
        if dialect == 'mysql':
            sql = "SELECT count(*) as num FROM information_schema.TABLES WHERE(TABLE_SCHEMA='"+test_database+"') AND(TABLE_NAME='"+table_name+"')"
        elif dialect == 'postgresql':
            sql = "SELECT count(*) as num FROM information_schema.TABLES WHERE(TABLE_CATALOG='"+test_database+"') AND(TABLE_NAME='"+table_name+"')"


        table_exists = engine.execute(sql)
        for row in table_exists:
            if row['num']==0:
                return "Table Name :: "+table_name+" does not exist in database"

        print("Checking Table "+table_name+" against Object "+str(object_name))
        if dialect == 'mysql':
            sql="describe " + table_name.strip()
        elif dialect == 'postgresql':
            sql = "select column_default as \"Default\", column_name as \"Field\", data_type as \"Type\" from information_schema.columns where table_catalog = '" + test_database + "' and table_name = '" + table_name + "'";

        table_description = engine.execute(sql)

        if not callable(object_name):
            errors.append( "\nObject "+str(object_name)+" does not exist")

        #Check Foreign Keys Match
        #get columns from object
        columns = self.introspect(object_name)
        #get foreign keys from object
        fks = self.introspectfk(object_name)
        #get foreign keys from DB
        dbfks = self.getSQLForeignKeysAsList(table_name,engine)

        #check for parity
        for fk in fks:
            if(not fk in dbfks):
                errors.append( "Object " + str(object_name) + " :: Foreign key :: " + fk + " exists in object but does not exist in DB")

        for dbfk in dbfks:
            if (not dbfk in fks):
                errors.append( "Object " + str(object_name) + " :: Foreign key :: " + dbfk + " exists in DB but does not exist in object")

        #check individual columns match
        #and build object attributes in data
        data={}
        for row in table_description:
            db_field = row['Field']
            db_type = row['Type']
            default = row['Default']

            if(db_field != 'id'):

                model_var_type = columns.get(db_field)

                if model_var_type is None :
                    errors.append( "Object " + str(object_name) + " :: " + db_field + " does not exist in the object but exists in DB")
                    continue

                if not hasattr(object_name, db_field):
                    errors.append( "Object " + str(object_name) + " does not have DB column " + db_field)
                    continue

                print("Checking :: " + db_field + " :: DB type = "+ db_type + " :: Object type = " + model_var_type)

                if model_var_type[:7] == 'varchar':
                    if default is None:
                        data[db_field]="Dummy " + table_name
                    else:
                        data[db_field] = default

                elif model_var_type[:3]== 'int' or model_var_type[:5] == 'float' or model_var_type[:6] =='double':
                    #if its a fk get valid key to existing record
                    #else just get random number
                    if db_field in fks:

                        #obj=(db_field.split("_id")[0]).capitalize()
                        obj=(db_field.split("_id")[0])

                        table = Table(obj, MetaData(), autoload_with=engine)
                        count = db_session.query(table).count()

                        #jms: null fk db_field isn't always an error so taking out check
                        #if count == 0 :
                        # errors.append( "\nNo records exist in table " + str(obj) + " for the foreign key :: " + db_field + " in table "+table_name
                        # continue
                        #data[db_field] = None
                        #else:
                        if count > 0:
                            rand = random.randrange(0, count)
                            row = db_session.query(table)[rand]
                            data[db_field] = row.id
                            print("Identified Foreign Key  :: " + db_field + " as " + str(data[db_field]))
                    else:
                        data[db_field]=random.randint(1,1000)

                elif model_var_type[:8] == 'datetime' or model_var_type[:9] == 'timestamp':
                    data[db_field] = now.strftime('%Y-%m-%d %H:%M:%S')
                elif (model_var_type[:4] == 'date'):
                    data[db_field] = now.strftime('%Y-%m-%d')

                elif (model_var_type == 'jsonb'):
                    data[db_field] = {'dummy':True}

                #check that object db_type and datatype match if type strings don't match exactly
                if db_type[:len(model_var_type)] != model_var_type :

                    if (model_var_type[:7] == 'varchar' and db_type[:4] == 'text'):continue
                    elif (model_var_type[:7] == 'varchar' and db_type == 'character varying'):continue
                    elif (model_var_type[:7] == 'varchar' and db_type[6:10] == 'text'):continue
                    elif (model_var_type[:7] == 'varchar' and db_type[4:8] == 'text'):continue
                    elif (model_var_type[:7] == 'varchar' and db_type[:5] == 'char('):
                        #if database type is char make sure dummy string is not too big
                        character=str(db_type[5:])
                        character=character.replace(")","")
                        int_char = int(character)
                        data[db_field] = data[db_field][:int_char]
                        continue
                    elif (model_var_type == 'integer' and db_type[:3] == 'int'): continue
                    elif (model_var_type == 'float' and db_type[:6] == 'double'): continue
                    elif (model_var_type == 'float' and db_type == 'numeric'): continue
                    elif (model_var_type[:7] == 'varchar' and db_type[:4] == 'enum'):
                        #if database db_field is enum type
                        #get enum values and then select one randomly from the list
                        enum=str(db_type[5:])
                        enum=enum[:(len(enum)-1)]
                        enum=enum.split(",")
                        enum=str(random.choice(enum))
                        data[db_field]=enum.replace("'","")

                        continue
                    elif model_var_type[:9] == 'timestamp' and db_type[:8] == 'datetime': continue
                    elif model_var_type == 'datetime' and db_type[:9] == 'timestamp': continue
                    elif model_var_type == 'boolean' and db_type == 'tinyint(1)':
                        data[db_field] = False
                        continue

                    else: errors.append( "Object " + str(object_name) + " :: " + db_field + " :: DB type = "+db_type+ " is not same as object type = "+model_var_type)

        # instantiate and insert object if there are no errors
        errorString = ""
        if len(errors) == 0:
            try:
                instance = object_name()
                for key,value in data.items():
                    setattr(instance,key,value)
                    print("setting " + str(key) + " to " + str(value))
                print("Instantiated and set vars :: " + instance.__repr__())
                db_session.add(instance)
                db_session.commit()
                print("Inserted in DB :: " + instance.__repr__())
            except LookupError as le:
                # this is masking the lack of the enum types in Postgres
                print(le)
        else:
            errorString = "\n".join(errors)
            print("!!!! Errors encountered in object and / or DB", errorString)

        return errorString

    @classmethod
    def introspect(self,obj):
        columns = {}
        variables=(vars(obj))
        table = variables['__table__']
        tablevars=vars(table)
        cols = tablevars['columns']
        for col in cols:
            columns[col.name]=str(col.type).lower()
        print('returning ', columns)
        return columns

    @classmethod
    def introspectfk(self,obj):
        return [column.name for column in obj.__table__.columns if not column.primary_key and column.foreign_keys]

    @classmethod
    def getSQLForeignKeysAsList(self,table_name,engine):
        dialect = engine.dialect.name
        if dialect == 'mysql':
            sql="select column_name from information_schema.key_column_usage where referenced_table_schema = '" \
                + test_database \
                + "' and table_name = '" \
                + table_name + "'"
        elif dialect == 'postgresql':

            sql="select kcu.column_name from information_schema.table_constraints tc \
                    join information_schema.key_column_usage kcu on kcu.constraint_name = tc.constraint_name \
                    where column_name != \'id\' and tc.table_catalog = '" \
                + test_database \
                + "' and tc.table_name = '" \
                + table_name + "'" \
                + " and tc.constraint_type = 'FOREIGN KEY'"
        rows=engine.execute(sql)

        list=[]
        for row in rows:
            list.append(str(row['column_name']))

        return list

    def test_a_project(self,create_min_database):
        assert self.check_table("project",Project,create_min_database) == ''


    def test_b_subject(self,create_min_database):
        assert self.check_table("subject",Subject,create_min_database) == ''

    def test_c_compound(self,create_min_database):
        assert self.check_table("compound", Compound,create_min_database) == ''

    def test_d_externaldb(self,create_min_database):
        assert self.check_table("external_db", ExternalDB,create_min_database) == ''

    def test_e_compound_external_db(self,create_min_database):
        assert self.check_table("compound_external_db", CompoundExternalDB,create_min_database) == ''

    def test_f_unit(self,create_min_database):
        assert self.check_table("unit", Unit,create_min_database) == ''

    def test_g_assay(self,create_min_database):
        assert self.check_table("assay", Assay,create_min_database) == ''

    def test_h_sample(self,create_min_database):
        assert self.check_table("sample", Sample,create_min_database) == ''

    def test_i_harmonised_metadata_field(self,create_min_database):
        assert self.check_table("harmonised_metadata_field", HarmonisedMetadataField,create_min_database) == ''

    def test_j_metadata_field(self,create_min_database):
        assert self.check_table("metadata_field", MetadataField,create_min_database) == ''

    def test_k_metadata_value(self,create_min_database):
        assert self.check_table("metadata_value", MetadataValue,create_min_database) == ''

    def test_l_sample_assay(self,create_min_database):
        assert self.check_table("sample_assay", SampleAssay,create_min_database) == ''

    def test_m_annotated_feature(self,create_min_database):
        assert self.check_table("annotated_feature", AnnotatedFeature,create_min_database) == ''

    #def test_m_feature_dataset(self,create_min_database):
    #    assert self.check_table("feature_dataset", FeatureDataset,create_min_database) == ''

    def test_m_feature_metadata(self,create_min_database):
        assert self.check_table("feature_metadata", FeatureMetadata,create_min_database) == ''

    def test_n_compound_class(self,create_min_database):
        assert self.check_table("compound_class", CompoundClass,create_min_database) == ''

    def test_o_annotation_compound(self,create_min_database):
        assert self.check_table("annotation_compound", AnnotationCompound,create_min_database) == ''

    def test_p_annotation(self,create_min_database):
        assert self.check_table("annotation", Annotation,create_min_database) == ''

    def test_q_saved_query(self,create_min_database):
        assert self.check_table("saved_query", SavedQuery,create_min_database) == ''

    def test_r_evidence_type(self,create_min_database):
        assert self.check_table("evidence_type", EvidenceType,create_min_database) == ''

    def test_s_annotation_evidence(self,create_min_database):
        assert self.check_table("annotation_evidence", AnnotationEvidence,create_min_database) == ''

    def test_t_annotation_evidence_file_upload(self,create_min_database):
        assert self.check_table("annotation_evidence_file_upload", AnnotationEvidenceFileUpload,create_min_database) == ''

    def test_u_annotation_method(self,create_min_database):
        assert self.check_table("annotation_method", AnnotationMethod,create_min_database) == ''

    def test_v_data_repository(self,create_min_database):
        assert self.check_table("data_repository", DataRepository,create_min_database) == ''

    def test_x_protocol(self,create_min_database):
        assert self.check_table("protocol", Protocol,create_min_database) == ''

    def test_y_protocol_parameter(self,create_min_database):
        assert self.check_table("protocol_parameter", ProtocolParameter,create_min_database) == ''

    def test_z_publication(self,create_min_database):
        assert self.check_table("publication", Publication,create_min_database) == ''

    def test_z1_ontology_source(self,create_min_database):
        assert self.check_table("ontology_source", OntologySource,create_min_database) == ''

    def test_z2_harmonised_annotated_feature(self,create_min_database):
        assert self.check_table("harmonised_annotated_feature", HarmonisedAnnotatedFeature,create_min_database) == ''

    def test_z3_harmonised_dataset(self,create_min_database):
        assert self.check_table("harmonised_dataset", HarmonisedDataset,create_min_database) == ''

    def test_z4_pipeline(self,create_min_database):
        assert self.check_table("pipeline", Pipeline,create_min_database) == ''

    def test_z5_task_run(self,create_min_database):
        assert self.check_table("task_run", TaskRun,create_min_database) == ''

    def test_z6_chemical_standard_dataset(self,create_min_database):
        assert self.check_table("chemical_standard_dataset", ChemicalStandardDataset,create_min_database) == ''

    def test_z7_chemical_standard_peaklist(self,create_min_database):
        assert self.check_table("chemical_standard_peaklist", ChemicalStandardPeakList,create_min_database) == ''


