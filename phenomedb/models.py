from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base
import phenomedb.database as db
import phenomedb.utilities as utils
import enum
from sqlalchemy.dialects.postgresql.json import JSONB
from phenomedb.config import config
from phenomedb.exceptions import NoUnitConversionError, NotImplementedUnitConversionError
#from flask_appbuilder.security.sqla.models import Role
import requests
import urllib.parse

from rdkit import Chem
from rdkit.Chem import Crippen

Base = declarative_base(bind=db.prod_engine)

# Some enums are direct imports from nPYc
from nPYc.enumerations import *

# list of valid columns to extract from a compound 
# csv file; see test_data/standardized_compound_insert.csv
COMPOUND_BASIC_HEADINGS = ['name', 'inchi', 'chemical_formula', 'inchi_key', 'exact_mass']
COMPOUND_DB_HEADINGS = ['CAS','ChEBI','ChEMBL','ChemSpider','HMDB','LipidBank',
                        'LipidMAPS','MetaCyc','NPC Compound ID','NPCLIMS','PubChem CID','KEGG']
COMPOUND_ASSAY_HEADINGS = ['RPOS','LPOS','LNEG','RNEG','HPOS','LC-QqQ Bile Acids','LC-QqQ Amino Acids','LC-QqQ Tryptophan','LC-QqQ Oxylipins','Bruker IVDR']

#class Role(Base):
#    """User Roles - to be sychronized with the airflow database
#    """
#    __tablename__ = 'role'

#    id = Column(Integer, primary_key=True)
#    name = Column(String)
#    projects = relationship("ProjectRole")

#    def __repr__(self):
#        return "<Role(id=%s, name='%s')>" % (self.id, self.name)

#    def toString(self):
#        retstr = "<Class Role id :: " + str(self.id) + " :: name = " + self.name  +" >\n"
#        return retstr

class SavedQuery(Base):

    __tablename__ = 'saved_query'

    class Type(enum.Enum):
        preset = "preset"
        custom = "custom"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    json = Column(JSONB)
    project_short_label = Column(String)
    code_string = Column(String)
    sql = Column(String)
    created_by = Column(String)
    date_added = Column(DateTime)
    type = Column(Enum(Type))
    #role_id = Column(Integer,ForeignKey('role.id'))
    #role = relationship("Role")
    cache_state = Column(JSONB)

    def __repr__(self):
        return "<SavedQuery(id=%s, name='%s')>" %(self.id,self.name)

    def toString(self):
        "<SavedQuery ::  id :: "+str(self.id)+" :: "+self.name+" >"+" >"

    def load_query_dict_for_view(self):

        query_dict = self.json

        for filter in query_dict['filters']:
            for sub_filter in filter['sub_filters']:
                for match in sub_filter['matches']:
                    if isinstance(match['value'],list):
                        match_value = [ str(x) for x in match['value'] ]
                        match['display_value'] = ",".join(match_value).replace("'","")
                    else:
                        match['display_value'] = match['value']


        self.display_query_dict = query_dict

    def get_cache_csv_path_key(self,key):
        return "SavedQueryDataframeCSVPath::%s:%s" % (self.id,key)

    def get_cache_dataframe_key(self,key):
        return "SavedQueryDataframe::%s:%s" % (self.id,key)

    def get_cache_annotated_feature_id_key(self,key):
        return "SavedQueryAnnotatedFeatureIDDataframe::%s:%s" % (self.id,key)

    def get_cache_summary_stats_key(self):
        return "SavedQuerySummaryStats::%s" % (self.id)


class Pipeline(Base):

    __tablename__ = 'pipeline'

    id = Column(Integer,primary_key=True)
    name = Column(String)
    default_args = Column(JSONB)
    description = Column(String)
    start_date = Column(DateTime)
    date_created = Column(DateTime)
    schedule_interval = Column(String)
    hard_code_data = Column(Boolean)
    sequential = Column(Boolean)
    definition = Column(JSONB)
    task_order = Column(JSONB)
    pipeline_file_path = Column(String)
    username_created = Column(String)
    tags = Column(JSONB)
    #role_id = Column(Integer,ForeignKey('role.id'))
    #role = relationship('Role')
    deleted = Column(Boolean)
    max_active_runs = Column(Numeric)
    concurrency = Column(Numeric)

    def __repr__(self):
        return "<Pipeline(id=%s, name=%s)>" % (self.id, self.name)


class TaskRun(Base):

    __tablename__ = 'task_run'

    class Status(enum.Enum):
        created = "created"
        scheduled = "scheduled"
        started = "started"
        success = "success"
        error = "error"

    id = Column(Integer,primary_key=True)
    module_name = Column(String)
    class_name = Column(String)
    task_id = Column(String)
    pipeline_id = Column(Integer,ForeignKey('pipeline.id'))
    pipeline = relationship('Pipeline')
    pipeline_run_id = Column(String)
    upstream_task_run_id = Column(Integer)
    username = Column(String)
    args = Column(JSONB)
    output = Column(JSONB)
    status = Column(Enum(Status))
    reports = Column(JSONB)
    db_env = Column(String)
    execution_date = Column(String)
    datetime_started = Column(DateTime)
    datetime_finished = Column(DateTime)
    run_time = Column(Numeric)
    db_size_start = Column(Numeric)
    db_size_end = Column(Numeric)
    db_size_bytes = Column(Numeric)
    db_size_megabytes = Column(Numeric)
    saved_query_id = Column(Integer,ForeignKey('saved_query.id'))
    saved_query = relationship('SavedQuery')
    missing_import_datas = relationship('MissingImportData')
    created_by_add_task = Column(Boolean)

    def __repr__(self):
        if self.pipeline_id:
            return "<TaskRun(id=%s, pipeline_id=%s, module_name=%s, class_name=%s, status=%s)>" % (self.id, self.pipeline_id, self.module_name, self.class_name,self.status)
        else:
            return "<TaskRun(id=%s, module_name=%s, class_name=%s, status=%s)>" % (self.id, self.module_name, self.class_name,self.status)

    def get_url(self):
        return "%s/analysisview/analysisresult/%s" % (config['WEBSERVER']['url'],self.id)

    def get_log_url(self):
        if not self.pipeline and isinstance(self.class_name,str) and self.execution_date:
            return "%s/log?dag_id=%s&task_id=%s&execution_date=%s" % (
            config['WEBSERVER']['url'], self.class_name, self.class_name.lower(), urllib.parse.quote(self.execution_date))
        elif self.status in [TaskRun.Status.scheduled,TaskRun.Status.scheduled.value,TaskRun.Status.started,TaskRun.Status.started.value]:
            return "task run not started yet %s" % self.id
        elif self.pipeline and self.execution_date:
            return "%s/log?dag_id=%s&task_id=%s&execution_date=%s" % (
            config['WEBSERVER']['url'], self.pipeline.name, self.task_id, urllib.parse.quote(self.execution_date))
        else:
            return "Unknown log file location for task_run %s" % (self.id)

    def for_log(self):

        output = "%s \n" % str(self)
        if self.pipeline_id:
            output = "%s \n" % self.pipeline

        output = output + self.get_url() + "\n"
        output = output + self.get_log_url() + "\n"

        output = output + \
                 "pipeline_run_id: %s \n" % self.pipeline_run_id + \
                 "upstream_task_run_id: %s \n" % self.upstream_task_run_id + \
                 "args: %s \n" % self.args + \
                 "output: %s \n" % self.output + \
                 "status: %s \n" % self.status + \
                 "reports: %s \n" % self.reports + \
                 "datetime_started: %s \n" % self.datetime_started + \
                 "datetime_finished: %s \n" % self.datetime_finished + \
                 "username: %s \n" % self.username

        if self.datetime_started and self.datetime_finished:
            output = output + "\n task_length: %s \n" % (self.datetime_finished - self.datetime_started)

        return output

    def get_task_data_cache_key(self):
        return "TaskData::%s" % self.id

    def get_task_data(self,cache):
        if cache.exists(self.get_task_data_cache_key()):
            return cache.get(self.get_task_data_cache_key())
        else:
            return None

    def get_task_output_cache_key(self):
        return "TaskOutput::%s" % self.id

    def get_task_output(self,cache):
        if cache.exists(self.get_task_output_cache_key()):
            return cache.get(self.get_task_output_cache_key())
        else:
            return None

    def get_task_class_object(self):

        import importlib

        module = importlib.import_module(self.module_name)
        class_ = getattr(module, self.class_name)

        if not self.args:
            self.args = {}

        import inspect
        arg_spec = inspect.getfullargspec(class_)

        values_only_dict = {k: v for k, v in self.args.items() if v is not None and k in arg_spec[0]}

        if self.saved_query_id and 'saved_query_id' not in values_only_dict and 'saved_query_id' in arg_spec[0]:
            values_only_dict['saved_query_id'] = self.saved_query_id

        return class_(**values_only_dict)


class MissingImportData(Base):
    """MissingImportData
    """
    __tablename__ = 'missing_import_data'

    id = Column(Integer, primary_key=True)
    type = Column(String)
    value = Column(JSONB)
    comment = Column(String)
    task_run_id = Column(Integer, ForeignKey('task_run.id'))
    task_run = relationship("TaskRun", back_populates="missing_import_datas")

    def __repr__(self):
        return "<MissingImportData(type='%s', value='%s', comment='%s')>" % (self.type,self.value,self.comment)

class Unit(Base):
    """Unit
    """

    __tablename__ = 'unit'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)

    def __repr__(self):
        return "<Unit(id=%s, name='%s', description='%s')>" %(self.id, self.name, self.description)

    def toString(self):
        return "<Class Unit id :: " + str(self.id) + " :: " + self.name + " >"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)

    def convert(self,value,to,logger):

        converted = None

        if self.name == to:
            converted = value

        elif self.name == 'noUnit' \
                or self.name == '-/-':
            raise NoUnitConversionError('Cannot convert %s to %s' % (self.name,to))

        elif self.name == 'mg/dL' and to == 'g/dL':
            converted = value * 0.001

        elif self.name == 'g/dL' and to == 'mg/dL':
            converted = value * 1000

        elif self.name == 'mg/dL' and to == 'mmol/L':
            converted = value / 18

        elif self.name == 'mmol/L' and to == 'mg/dL':
            converted = value * 18

        elif self.name == 'nmol/L' and to == 'mmol/L':
            converted = value * 0.000001

        elif self.name == 'mmol/L' and to == 'nmol/L':
            converted = value * 1000000

        elif self.name == 'ng/mL' and to == 'mmol/L':
            converted = value * 0.001

        elif self.name == 'mmol/L' and to == 'ng/mL':
            converted = value * 1000

        elif self.name == 'nM' and to == 'mmol/L':
            converted = value * 0.000001

        elif self.name == 'mmol/L' and to == 'nM':
            converted = value * 1000000

        elif self.name == 'fg/µL' and to == 'mmol/L':
            converted = value * 0.000001

        elif self.name == 'mmol/L' and to == 'fg/µL':
            converted = value / 0.000001

        elif self.name == 'µM' and to == 'mmol/L':
            converted = value * 0.001

        else:
            raise NotImplementedUnitConversionError('Unit conversion has not been implemented: %s -> %s' % (self.name,to))

       # if dilution != 100:
       #     converted = converted * (100 / dilution)

        converted = utils.precision_round(converted,digits=len(str(value)))

        logger.info("Converted %s %s to %s %s" % (value,self.name,converted,to))

        return converted

class Laboratory(Base):

    __tablename__ = 'laboratory'

    id = Column(Integer,primary_key=True)
    name = Column(String)
    affiliation = Column(String)

    def __repr__(self):
        return "<Laboratory(id=%s, name='%s', affiliation='%s')>" % (self.id, self.name, self.affiliation)

class Project(Base):
    """Project represents the information about the project being analysed
    """

    __tablename__ = 'project'

    __searchfields__ = ['id','name','description','lims_id','project_folder_name']

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    lims_id = Column(Integer)
    project_folder_name = Column(String)
    date_added = Column(DateTime)
    subjects = relationship("Subject", backref="subject")
    #roles = relationship("ProjectRole")
    short_description = Column(String)
    persons = Column(JSONB)
    laboratory_id = Column(Integer,ForeignKey('laboratory.id'))
    laboratory = relationship("Laboratory", backref="laboratory")
    chart_colour = Column(String)

    def __repr__(self):
        return "<Project(id=%s, name='%s', description='%s', project_folder_name='%s')>" % (
            self.id, self.name, self.description, self.project_folder_name)

    def toString(self):
        retstr = "<Class Project id :: " + str(self.id) + " :: " + self.name + " >\n"
        for subject in self.subjects:
            retstr = retstr+subject.toString()

        return retstr

    def getCounts(self):
        retstr = "Project ID = " + str(self.id) + " :: " + self.name + "\n"
        retstr = retstr + "# Subjects = "+str(len(self.subjects))+"\n"

        events=0
        se_assay=0
        md_raw=0
        #md_cur=0
        annotated_features=0

        for subject in self.subjects:
            events+=subject.getCountEvents()
            se_assay+=subject.getCountAssays()
            md_raw+=subject.getCountMetadataValues()
            #md_cur=md_cur+subject.getCountMetaDataCurated()
            annotated_features+=subject.getCountAnnotatedFeatures()

        retstr = retstr + "# Samples = "+str(events)+"\n"
        retstr = retstr + "# SampleAssays = " + str(se_assay) + "\n"
        retstr = retstr + "# Metadata Value = "+str(md_raw)+"\n"
        #retstr = retstr + "# Metadata Curated = " + str(md_cur) + "\n"
        retstr = retstr + "# AnnotatedFeatures = " + str(annotated_features) + "\n"

        numbers={
            "text":retstr,
            "project_id":self.id,
            "subjects":len(self.subjects),
            "samples":events,
            "sample_assays":se_assay,
            "metadata_values":md_raw,
            "annotated_features":annotated_features}

        return numbers

    def getName(self):
        return self.name

#    @staticmethod
#    def get_project_for_role(db_session, role_id):
#        role=db_session.query(Role).filter(Role.id == role_id).first()
#        if (role.name == 'Admin'):
#            projects = db_session.query(Project).order_by(Project.name)
#        else:
#            projects = db_session.query(Project).join(ProjectRole).filter(ProjectRole.role_id == role_id).order_by(Project.name)
#        return projects

#    @staticmethod
#    def get_project_not_for_role(db_session,role_id):
#        role = db_session.query(Role).filter(Role.id == role_id).first()
#        if (role.name == 'Admin'):
#            return null
#        else:
#            allowedprojects = db_session.query(Project.id).join(ProjectRole).filter(ProjectRole.role_id == role_id)
#            projects = db_session.query(Project).filter(~Project.id.in_(allowedprojects)).order_by(Project.name)
#        return projects


    def build_search_index(self):
        return utils.flatten_model_for_search(self)

    def get_summary_cache_key(self):

        return ("ProjectSummary::%s" % self.id)

    def get_sample_matrix_assay_summary(self,db_session,reload_cache=False):

        from phenomedb.cache import Cache
        cache = Cache()

        if reload_cache:
            cache.delete(self.get_summary_cache_key())

        if cache.exists(self.get_summary_cache_key()):
            return cache.get(self.get_summary_cache_key())
        else:

            distinct_sample_matrices = []
            sample_matrices = db_session.query(Sample.sample_matrix).join(Subject,Project).filter(Project.id==self.id).distinct().all()
            for sample_matrix in sample_matrices:
                distinct_sample_matrices.append(sample_matrix[0])

            # breakdown by sample matrix
            sample_matrix_breakdown = {}
            for sample_matrix in distinct_sample_matrices:
                sample_matrix_breakdown[sample_matrix] = {}
                assays = db_session.query(Assay.name).join(SampleAssay,Sample,Subject,Project).filter(Project.id==self.id).filter(Sample.sample_matrix==sample_matrix).distinct().all()
                for assay in assays:
                    assay_name = assay[0]
                    sample_matrix_breakdown[sample_matrix][assay_name] = {}
                    sample_types = db_session.query(Sample.sample_type).join(Subject,Project).filter(Project.id==self.id).filter(Sample.sample_matrix==sample_matrix).distinct().all()
                    for sample_type in sample_types:
                        sample_type_value = sample_type[0].value
                        sample_matrix_breakdown[sample_matrix][assay_name][sample_type_value] = db_session.query(Sample.id) \
                            .join(SampleAssay,Subject,Project) \
                            .filter(Project.id==self.id,Assay.name==assay_name,Sample.sample_matrix==sample_matrix,Sample.sample_type==sample_type[0]) \
                            .group_by(Sample.id).count()

            cache.set(self.get_summary_cache_key(),sample_matrix_breakdown,ex=60*60*24*7)

        return sample_matrix_breakdown

#class ProjectRole(Base):
#    """ProjectRole is the relationship between roles and projects
#       Project IDs are linked with role names
#       this represents the right for that role to view the project with the ID
#    """

#    __tablename__ = 'project_role'

#    id = Column(Integer, primary_key=True)
#    role_id = Column(Integer, ForeignKey('role.id'))
#    project_id = Column(Integer, ForeignKey('project.id'))
#    project = relationship("Project", back_populates="roles")
#    role = relationship("Role", back_populates="projects")

#    def __repr__(self):
#        return "<ProjectRole(id=%s, role='%s', project_name='%s')>" % (self.id, self.role.name, self.project.name)

#    def toString(self):
#        retstr = "<Class ProjectRole id :: " + str(self.id) + " :: role = " + self.role.name + " :: project = " + self.project.name +" >\n"
#        return retstr


class Assay(Base):
    """Assay
    """

    __tablename__ = 'assay'

    __searchfields__ = '_all'

    class QuantificationType(enum.Enum):
        absolute = "absolute"
        relative = "relative"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    platform = Column(Enum(AnalyticalPlatform))
    targeted = Column(String)
    ms_polarity = Column(String)
    measurement_type = Column(String)
    long_name = Column(String)
    long_platform = Column(String)
    quantification_type = Column(Enum(QuantificationType))

    def __repr__(self):
        return "<Assay(id=%s, name='%s', platform='%s', targeted='%s')>" % (self.id, self.name, self.platform, self.targeted)

    def toString(self):
        return "<Class Assay id :: " + str(self.id) + " :: " + self.name + " >\n"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)

    def set_platform_from_long_platform(self,long_platform):

        if long_platform == 'mass spectrometry':
            self.platform = AnalyticalPlatform.MS
        elif long_platform == "nuclear magnetic resonance":
            self.platform = AnalyticalPlatform.NMR
        elif long_platform == 'NMR spectroscopy':
            self.platform = AnalyticalPlatform.NMR
        else:
            raise Exception('long platform not recognised: %s' % long_platform)



class Subject(Base):
    """Subject
    """

    __tablename__ = 'subject'

    __searchfields__ = '_all'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    project_id = Column(Integer, ForeignKey('project.id'))
    project = relationship("Project",  back_populates="subjects")
    samples = relationship("Sample")

    def __repr__(self):
        if self.project:
            return "<Subject(id=%s, name='%s', project_name='%s')>" % (self.id, self.name, self.project.name)
        else:
            return "<Subject(id=%s, name='%s'>" % (self.id, self.name)

    def toString(self):
        retstr = "<Class Subject id :: " + str(self.id) + " :: "+self.name+">\n"
        for event in self.samples:
            retstr = retstr + event.toString()

        return retstr

    def getCountEvents(self):
        se_num = 0
        for event in self.samples:
            se_num +=1
        return se_num

    def getCountAssays(self):
        se_num = 0
        for event in self.samples:
            se_num = se_num + event.getCountAssays()
        return se_num

    def getCountAnnotatedFeatures(self):
        se_num = 0
        for event in self.samples:
            se_num = se_num + event.getCountAnnotatedFeatures()
        return se_num

    def getCountMetadataValues(self):
        se_num = 0
        for event in self.samples:
            se_num = se_num + event.getCountMetadataValues()
        return se_num

    def build_search_index(self):
        return utils.flatten_model_for_search(self) + self.project.build_search_index()

class Sample(Base):
    """Sampling Event
    """
    __tablename__ = 'sample'

    __searchfields__ = '_all'


    id = Column(Integer, primary_key=True)
    name = Column(String)
    sampling_date = Column(DateTime)
    sample_type = Column(Enum(SampleType))
    assay_role = Column(Enum(AssayRole))
    sample_matrix = Column(String)
    biological_tissue = Column(String)
    subject_id = Column(Integer, ForeignKey('subject.id'))
    subject = relationship("Subject", back_populates="samples")
    sample_assays = relationship("SampleAssay")
    metadata_value = relationship("MetadataValue")
    sample_metadata = Column(JSONB)

    def __repr__(self):
        if self.subject:
            return "<Sample(id=%s, name='%s',sample_matrix='%s', sampling_date='%s', sample_type='%s', assay_role='%s', subject_name='%s')>" % (self.id, self.name,self.sample_matrix, self.sampling_date, self.sample_type, self.assay_role, self.subject.name)
        else:
            return "<Sample(id=%s, name='%s',sample_matrix='%s', sampling_date='%s', sample_type='%s', assay_role='%s')>" % (self.id, self.name,self.sample_matrix, self.sampling_date, self.sample_type, self.assay_role)

    def toString(self):
        retstr = "<Class Sample id :: " + str(self.id) + " :: " + self.name + ">\n"
        for assay in self.sample_assays:
            retstr = retstr + assay.toString()
        for md in self.metadata_value:
            retstr = retstr + md.toString()

        return retstr


    def getCountAssays(self):
        se_assays = 0
        for assay in self.sample_assays:
            se_assays +=1
        return se_assays

    def getCountAnnotatedFeatures(self):
        se_assay_annotated_features = 0
        for assay in self.sample_assays:
            se_assay_annotated_features += assay.getCountAnnotatedFeatures()
        return se_assay_annotated_features

    def getCountMetadataValues(self):
        return len(self.metadata_value)

    '''
    def getCountMetaDataValues(self):
        md_val = 0
        for md in self.metadata_value:
            md_val +=1
        
        return md_val
    '''

    @staticmethod
    def get_biological_tissue(sample_matrix):

        biological_tissue_map = {"plasma": "plasma",
                                 "stool": "faeces",
                                 "faecal extract": "faeces",
                                 "organic tissue": "unknown",
                                 "serum" : "serum",
                                 "organic tissue extract": "unknown",
                                 "mouse liver tissue" : "liver",
                                 "plasma bile acids": "plasma",
                                 "tissue section": "unknown",
                                 "mouse organic tissue extract": "unknown",
                                 "urine": "urine",
                                 "nasal swab extract": "nasal",
                                 "cell culture extract": "cell culture",
                                 "blood plasma": "plasma"}

        try:
            return biological_tissue_map[sample_matrix]
        except KeyError:
            return 'unknown'
            #raise NotImplementedError("sample matrix mapping does not exist - %s" % sample_matrix)


    def build_search_index(self):
        document = utils.flatten_model_for_search(self) + self.subject.build_search_index()
        for metadata_value in self.metadata_value:
            document = document + metadata_value.build_search_index()
        for sample_assay in self.sample_assays:
            document = document + sample_assay.build_search_index()
        return document



class SampleAssay(Base):
    """Sampling Event Assay
    """

    __tablename__ = 'sample_assay'

    __searchfields__ = '_all'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    sample_id = Column(Integer, ForeignKey('sample.id'))
    sample = relationship("Sample", back_populates="sample_assays")
    assay_id = Column(Integer, ForeignKey('assay.id'))
    assay = relationship("Assay", backref="sample_assays")
    acquired_time = Column(DateTime)
    raw_spectra_path = Column(String)
    processed_spectra_path = Column(String)
    excluded = Column(String)
    exclusion_details = Column(String)
    instrument = Column(String)
    sample_file_name = Column(String)
    sample_base_name = Column(String)
    expno = Column(String)
    position = Column(String)
    run_order = Column(Integer)
    batch = Column(String)
    correction_batch = Column(String)
    dilution = Column(Float)
    instrument_metadata = Column(JSONB)
    annotated_features = relationship("AnnotatedFeature")
    detector_voltage = Column(Float)
    assay_parameters = Column(JSONB)
    features = Column(JSONB)
    harmonised_features = Column(JSONB)

    def __repr__(self):
        if self.sample and self.assay:
            return "<SampleAssay(id=%s, sample_file_name='%s', run_date='%s', sample_id='%s, sample_name='%s', assay_name='%s')>" %(self.id, self.sample_file_name, self.acquired_time, self.sample_id, self.sample.name, self.assay.name)
        else:
            return "<SampleAssay(id=%s, sample_file_name='%s', run_date='%s')>" %(self.id, self.sample_file_name, self.acquired_time)

    def toString(self):
        retstr = "<Class SampleAssay id :: " + str(self.id) + " :: " + str(self.acquired_time) + ">\n"
        retstr = retstr + self.assay.toString()
        for annot in self.annotated_features:
            retstr = retstr + annot.toString()
        return retstr

    def getCountAnnotatedFeatures(self):
        num_anns=0
        for annot in self.annotated_features:
            num_anns+=1
        return num_anns

    def build_search_index(self):
        document = utils.flatten_model_for_search(self)
        for annotated_feature in self.annotated_features:
            document = document + annotated_feature.build_search_index()
        return document



class AnnotatedFeature(Base):
    """AnnotatedFeature
    """

    __tablename__ = 'annotated_feature'

    __searchfields__ = ['id','intensity','lod','uloq','lloq','confidence_level','source_file','comment']

    id = Column(Integer, primary_key=True)
    feature_metadata_id = Column(Integer,ForeignKey('feature_metadata.id'))
    feature_metadata = relationship("FeatureMetadata", back_populates="annotated_features")
    sample_assay_id = Column(Integer,ForeignKey('sample_assay.id'))
    sample_assay = relationship("SampleAssay")
    unit_id = Column(Integer,ForeignKey('unit.id'))
    unit = relationship("Unit")
    intensity = Column(Float)
    below_lloq = Column(Boolean)
    above_uloq = Column(Boolean)
    comment = Column(String)
    sr_corrected_intensity = Column(Float)
    ltr_corrected_intensity = Column(Float)

    def __repr__(self):
        if self.feature_metadata:
            return "<AnnotatedFeature(id=%s, sample_assay_id=%s, intensity=%s, feature_name=%s)>" %(self.id,self.sample_assay_id,self.intensity,self.feature_metadata.feature_name)
        else:
            return "<AnnotatedFeature(id=%s, sample_assay_id=%s, intensity=%s)>" %(self.id,self.sample_assay_id,self.intensity)

    def toString(self):
        return "<AnnotatedFeature(id=%s, sample_assay_id=%s, intensity=%s)>\n" %(self.id,self.sample_assay_id,self.intensity)

class HarmonisedDataset(Base):

    __tablename__ = 'harmonised_dataset'

    class Type(enum.Enum):
        LOESS_SR = "LOESS_SR"
        LOESS_LTR = "LOESS_LTR"
        COMBAT = "COMBAT"

    id = Column(Integer,primary_key=True)
    task_run_id = Column(Integer,ForeignKey('task_run.id'))
    task_run = relationship('TaskRun')
    type = Column(Enum(Type))
    parameters = Column(JSONB)
    username = Column(String)
    comment = Column(String)

    def __repr__(self):
        return "<HarmonisedDataset(id=%s,task_run_id=%s,type=%s)" % (self.id,self.task_run_id,self.type)

class HarmonisedAnnotatedFeature(Base):

    __tablename__ = 'harmonised_annotated_feature'

    id = Column(Integer,primary_key=True)
    annotated_feature_id = Column(Integer,ForeignKey('annotated_feature.id'))
    annotated_feature = relationship('AnnotatedFeature')
    intensity = Column(Numeric)
    mz = Column(Numeric)
    rt = Column(Numeric)
    harmonised_dataset_id = Column(Integer,ForeignKey('harmonised_dataset.id'))
    harmonised_dataset = relationship('HarmonisedDataset')
    unit_id = Column(Integer,ForeignKey('unit.id'))
    unit = relationship('Unit')
    below_lloq = Column(Boolean)
    above_uloq = Column(Boolean)

    def __repr__(self):
        return "<HarmonisedAnnotatedFeature(id=%s,annotated_feature_id=%s,intensity=%s,below_lloq=%s,above_uloq=%s)" % (self.id,self.annotated_feature_id,self.intensity,self.below_lloq,self.above_uloq)

class FeatureDataset(Base):

    __tablename__ = 'feature_dataset'

    class Type(enum.Enum):
        unified_csv = 'unified_csv'
        separate_csvs = 'separate_csvs'
        metabolights = 'metabolights'

    class CorrectionType(enum.Enum):
        LOESS_SR = 'SR'
        LOESS_LTR = 'LTR'

    id = Column(Integer,primary_key=True)
    name = Column(String)
    feature_extraction_params = Column(JSONB)
    annotation_params = Column(JSONB)
    filetype = Column(Enum(Type))
    unified_csv_filename = Column(String)
    intensity_data_filename = Column(String)
    sample_metadata_filename = Column(String)
    feature_metadata_filename = Column(String)
    assay_id = Column(Integer,ForeignKey('assay.id'))
    assay = relationship('Assay')
    project_id = Column(Integer,ForeignKey('project.id'))
    project = relationship("Project")
    sample_matrix = Column(String)
    sr_correction_parameters = Column(JSONB)
    sr_correction_task_run_id = Column(Integer,ForeignKey('task_run.id'))
    sr_correction_task_run = relationship('TaskRun',foreign_keys=[sr_correction_task_run_id])
    ltr_correction_parameters = Column(JSONB)
    ltr_correction_task_run_id = Column(Integer, ForeignKey('task_run.id'))
    ltr_correction_task_run = relationship('TaskRun',foreign_keys=[ltr_correction_task_run_id])
    saved_query_id = Column(Integer,ForeignKey('saved_query.id'))
    saved_query = relationship('SavedQuery')

    @staticmethod
    def get_dataset_name(project_name,assay_name,sample_matrix):
        return ('%s_%s_%s' % (project_name.lower(),assay_name.lower(),sample_matrix.lower())).replace(" ","_")

    def __repr__(self):
        return "<FeatureDataset(id=%s,name=%s,filetype=%s)" % (self.id,self.name,self.filetype)

class FeatureMetadata(Base):
    """Feature Metadata
    """

    __tablename__ = 'feature_metadata'

    __searchfields__ = ['id','intensity','lod','uloq','lloq','confidence_level','source_file','comment']

    id = Column(Integer, primary_key=True)
    annotation_id = Column(Integer,ForeignKey('annotation.id'))
    annotation = relationship("Annotation", back_populates="feature_metadatas")
    feature_dataset_id = Column(Integer,ForeignKey('feature_dataset.id'))
    feature_dataset = relationship("FeatureDataset", back_populates="feature_columns")
    rt_average = Column(Float)
    rt_min = Column(Float)
    rt_max = Column(Float)
    mz_average = Column(Float)
    mz_min = Column(Float)
    mz_max = Column(Float)
    feature_name = Column(String)
    lod = Column(Float)
    uloq = Column(Float)
    lloq = Column(Float)
    ion_id = Column(String)
    ion_type = Column(String)
    lower_reference_percentile = Column(Float)
    upper_reference_percentile = Column(Float)
    lower_reference_value = Column(Float)
    upper_reference_value = Column(Float)
    excluded = Column(Boolean)
    exclusion_details = Column(String)
    rsd_filter = Column(Boolean)
    variance_ratio_filter = Column(Boolean)
    correlation_to_dilution_filter = Column(Boolean)
    artifactual_filter = Column(Boolean)
    blank_filter = Column(Boolean)
    rsd_sp = Column(Float)
    rsd_ss_rsd_sp = Column(Float)
    correlation_to_dilution = Column(Float)
    blank_value = Column(Float)
    quantification_type = Column(Enum(QuantificationType))
    calibration_method = Column(Enum(CalibrationMethod))
    feature_filtering_pass = Column(Boolean)
    final_assessment_pass = Column(Boolean)
    final_assessment_rename = Column(String)
    comment = Column(String)
    annotation_parameters = Column(JSONB)
    annotation_version = Column(String)
    feature_metadata = Column(JSONB)
    annotated_features = relationship("AnnotatedFeature")
    date_imported = Column(DateTime)

    def __repr__(self):
        return "<FeatureMetadata(id=%s, feature_name=%s )>" % (self.id,self.feature_name)

    def toString(self):
        return "<Feature(id=%s)\n" %(self.id)

   # def build_search_index(self):
   #     return utils.flatten_model_for_search(self) + self.annotation_compound.build_search_index()


    #def build_search_index(self):
    #    return utils.flatten_model_for_search(self) + self.annotation_compound.build_search_index()


class AnnotationMethod(Base):
    """ AnnotationMethod
    """

    __tablename__ = 'annotation_method'

    __searchfields__ = '_all'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)

    def __repr__(self):
        return "<AnnotationMethod(name='%s',description='%s')>" %(self.name,self.description)

    def toString(self):
        return "<Class AnnotationMethod name :: " + str(self.name) + " >"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)


class Compound(Base):
    """Compound
    """

    __tablename__ = 'compound'

    __searchfields__ = '_all'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    chemical_formula = Column(String)
    monoisotopic_mass = Column(Float)
    inchi = Column(String, default='Unknown')
    inchi_key = Column(String, default='Unknown')
    iupac = Column(String)
    smiles = Column(String)
    log_p = Column(Float)

    def __repr__(self):
        return "<Compound(id=%s, name='%s', chemical_formula=%s, inchi_key=%s)>" % (self.id, self.name,self.chemical_formula,self.inchi_key)

    def toString(self):
        "<Class Compound id :: "+str(self.id)+" :: "+self.name+" :: "+self.inchi_key+" >"

    def get_inchi_key_backbone(self):
        inchi_split = self.inchi_key.split("-")
        return inchi_split[0]

    def build_search_index(self):

        document = utils.flatten_model_for_search(self)

        for external_db in self.external_dbs:
            document = document + external_db.build_search_index()

        for compound_class in self.compound_classes:
            document = document + compound_class.build_search_index()

        return document

    def set_inchi_key_from_rdkit(self):
        if self.inchi:
            try:
                my_chem = Chem.MolFromInchi(self.inchi)
                if my_chem:
                    self.inchi_key = Chem.inchi.MolToInchiKey(my_chem)
            except Exception as err:
                self.inchi_key = None
        else:
            self.inchi_key = None

    def set_log_p_from_rdkit(self):
        if self.inchi:
            try:
                my_chem = Chem.MolFromInchi(self.inchi)
                if my_chem:
                    self.log_p = Crippen.MolLogP(my_chem, includeHs=True)
            except Exception as err:
                self.log_p = None
        else:
            self.log_p = None

class CompoundClass(Base):
    """CompoundClass
    """

    class CompoundClassType(enum.Enum):
        isomer = "isomer"
        lipidmaps = "lipidmaps"
        refmet = "refmet"
        hmdb = "hmdb"
        classyfire = "classyfire"

    __tablename__ = 'compound_class'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    type = Column(Enum(CompoundClassType))
    inchi_key_backbone = Column(String)
    kingdom = Column(String)
    category = Column(String)
    main_class = Column(String)
    sub_class = Column(String)
    direct_parent = Column(String)
    intermediate_nodes = Column(JSONB)
    alternative_parents = Column(JSONB)
    molecular_framework = Column(String)
    substituents = Column(JSONB)
    ancestors = Column(JSONB)
    version = Column(String)

    def __repr__(self):
        return "<CompoundClass(id=%s, name='%s', type=%s, sub_class='%s')>" %(self.id, self.name, self.type, self.sub_class)

    def toString(self):
        "<Class CompoundClass id :: "+str(self.id)+" : :"+str(self.inchi_key_backbone)+" :: "+self.sub_class+" >"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)

class CompoundClassCompound(Base):
    """CompoundClassCompound
    """

    __tablename__ = 'compound_class_compound'

    id = Column(Integer, primary_key=True)
    compound_id = Column(Integer,ForeignKey('compound.id'))
    compound_class_id = Column(Integer,ForeignKey('compound_class.id'))
    compound = relationship("Compound", back_populates="compound_classes")
    compound_class = relationship("CompoundClass", back_populates="compounds")

    def __repr__(self):
        return "<CompoundClassCompound(id=%s, compound='%s', compound_class='%s')>" %(self.id, self.compound.name, self.compound_class.name)

    def toString(self):
        "<Class CompoundClassCompound id :: "+str(self.id)+">"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)


class ExternalDB(Base):
    """ExternalDB
    """

    __tablename__ = 'external_db'

    __searchfields__ = '_all'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)

    def __repr__(self):
        return "<ExternalDB(id=%s, name=%s, url=%s)>" %(self.id, self.name, self.url)

    def toString(self):
        "<Class ExternalDB id :: "+str(self.id)+" :: "+self.name+" >"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)


class CompoundExternalDB(Base):
    """CompoundExternalDB
    """

    __tablename__ = 'compound_external_db'

    id = Column(Integer, primary_key=True)
    compound_id = Column(Integer,ForeignKey('compound.id'))
    external_db_id = Column(Integer,ForeignKey('external_db.id'))
    database_ref = Column(String)
    # see end of file for declaration of these properties on Compound and ExternalDB
    compound = relationship("Compound", back_populates="external_dbs")
    external_db = relationship("ExternalDB", back_populates="compounds")

    def __repr__(self):
        if self.external_db:
            return "<CompoundExternalDB(compound_id=%s, external_db_name='%s', database_ref='%s')>" %(self.compound_id, self.external_db.name,self.database_ref)
        else:
            return "<CompoundExternalDB(compound_id=%s, database_ref='%s')>" %(self.compound_id, self.database_ref)

    def toString(self):
        return "<Class CompoundExternalDB id = "+str(self.id)+"has \n"+self.compound.toString()+"\n"+self.external_db.toString()+"\n>"

    def build_search_index(self):
        return utils.flatten_model_for_search(self)

class HarmonisedAnnotation(Base):
    """Annotation
    """

    __tablename__ = 'harmonised_annotation'

    class MultiCompoundOperator(enum.Enum):

        AND = "AND"
        ANDOR = "ANDOR"

    id = Column(Integer, primary_key=True)
    cpd_name = Column(String)
    cpd_id = Column(String)
    annotated_by = Column(String)
    confidence_score = Column(String)
    multi_compound_operator = Column(Enum(MultiCompoundOperator))
    latest_version = Column(String)
    annotation_method_id = Column(Integer,ForeignKey('annotation_method.id'))
    annotation_method = relationship("AnnotationMethod")
    assay_id = Column(Integer,ForeignKey('assay.id'))
    assay = relationship('Assay')
    annotations = relationship("Annotation")
    compounds = relationship("AnnotationCompound",backref='harmonised_annotations')

    def __repr__(self):
        if self.annotation_method and self.assay:
            return "<HarmonisedAnnotation(id=%s, cpd_name=%s, assay_name=%s, annotation_method_name=%s )>" %(self.id, self.cpd_name, self.assay.name, self.annotation_method.name)
        else:
            return "<HarmonisedAnnotation(id=%s, cpd_name=%s)>" %(self.id, self.cpd_name)

    def get_external_ids(self,db_session,type='KEGG'):

        if self.annotation_method.name == 'Bi-LISA':
            if self.cpd_name[2:] == 'TG':
                return ['C00422']
            elif self.cpd_name[2:] == 'CH':
                return ['C00187']
            elif self.cpd_name[2:] == 'FC':
                return ['C00187']
            elif self.cpd_name[2:] == 'PL':
                return ['C00865']
            else:
                return []
        else:
            kegg_entries = db_session.query(CompoundExternalDB).join(ExternalDB) \
                .filter(CompoundExternalDB.compound_id.in_([compound.id for compound in self.compounds]))\
                .filter(ExternalDB.name == type).all()
            return [kegg_entry.database_ref for kegg_entry in kegg_entries]

class Annotation(Base):
    """Annotation
    """

    __tablename__ = 'annotation'

    __searchfields__ = '_all'

    class MultiCompoundOperator(enum.Enum):

        AND = "AND"
        ANDOR = "ANDOR"

    id = Column(Integer, primary_key=True)
    version = Column(String)
    cpd_name = Column(String)
    cpd_id = Column(String)
    annotated_by = Column(String)
    confidence_score = Column(String)
    default_primary_ion_rt_seconds = Column(Numeric)
    default_primary_ion_mz = Column(Numeric)
    config = Column(JSONB)
    multi_compound_operator = Column(Enum(MultiCompoundOperator))
    harmonised_annotation_id = Column(Integer,ForeignKey('harmonised_annotation.id'))
    harmonised_annotation = relationship("HarmonisedAnnotation")
    feature_metadatas = relationship("FeatureMetadata")
    #compounds = relationship("AnnotationCompound")
    annotation_method_id = Column(Integer, ForeignKey('annotation_method.id'))
    annotation_method = relationship("AnnotationMethod")
    assay_id = Column(Integer, ForeignKey('assay.id'))
    assay = relationship('Assay')

    def __repr__(self):
        return "<Annotation(id=%s, cpd_name=%s, version=%s)>" %(self.id, self.cpd_name,self.version)

    #def toString(self):
    #    return "<Class AnnotationCompound id = "+str(self.id)+"has \n"+self.compound.toString()+"\n"+self.annotation_method.toString()+"\n>"

    def build_search_index(self,document=""):
        return document + utils.flatten_model_for_search(self) + self.compound.build_search_index() + self.annotation_method.build_search_index()


class AnnotationCompound(Base):

    __tablename__ = 'annotation_compound'

    id = Column(Integer, primary_key=True)
    compound_id = Column(Integer,ForeignKey('compound.id'))
    compound = relationship("Compound",back_populates="harmonised_annotations")
    harmonised_annotation_id = Column(Integer,ForeignKey('harmonised_annotation.id'))
    harmonised_annotation = relationship("HarmonisedAnnotation",back_populates="compounds")

    def __repr__(self):
        return "<AnnotationCompound(id=%s, compound_id=%s)>" %(self.id, self.compound_id)


class ChemicalStandardDataset(Base):

    __tablename__ = 'chemical_standard_dataset'

    id = Column(Integer, primary_key=True)
    collision_energy = Column(Float)
    acquired_date = Column(DateTime)
    source_file = Column(String)
    compound_id = Column(Integer, ForeignKey('compound.id'))
    assay_id = Column(Integer, ForeignKey('assay.id'))
    supplier = Column(String)
    concentration = Column(Float)
    mass = Column(Float)
    exhausted = Column(Boolean)
    ph = Column(Float)
    assigned_casrn = Column(String)
    lims_ids = Column(JSONB)

class ChemicalStandardPeakList(Base):

    __tablename__ = 'chemical_standard_peaklist'

    id = Column(Integer, primary_key=True)
    mz = Column(Float)
    rt_seconds = Column(Float)
    intensity = Column(Float)
    drift = Column(Float)
    peak_width = Column(Float)
    resolution = Column(Float)
    seed = Column(Integer)
    validated = Column(Boolean)
    ion = Column(String)
    chemical_standard_dataset_id = Column(Integer, ForeignKey('chemical_standard_dataset.id'))

class EvidenceType(Base):

    __tablename__ = 'evidence_type'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    json_format = Column(JSONB)

    def __repr__(self):
        return "<EvidenceType(id=%s, name='%s')>" %(self.id, self.name)

    def toString(self):
        "<Class EvidenceType id :: "+str(self.id)+" :: "+self.name+" >"

class AnnotationEvidence(Base):

    __tablename__ = 'annotation_evidence'

    id = Column(Integer, primary_key=True)
    evidence_type_id = Column(Integer,ForeignKey('evidence_type.id'))
    annotation_id = Column(Integer,ForeignKey('annotation.id'))

    json_data = Column(JSONB)
    comments = Column(String)
    analysed_by_user = Column(String)
    recorded_by_user = Column(String)
    validated_by_user = Column(String)
    date_analysed = Column(DateTime)
    date_recorded = Column(DateTime)
    date_validated = Column(DateTime)
    chemical_standard_dataset_id = Column(Integer,ForeignKey('chemical_standard_dataset.id'))
    chemical_standard_datasets = relationship("ChemicalStandardDataset")

    evidence_type = relationship("EvidenceType")
    annotation = relationship("Annotation")

    def __repr__(self):
        if self.evidence_type:
            return "<AnnotationEvidence(id=%s, evidence_type_name='%s')>" % (self.id, self.evidence_type.name)
        else:
            return "<AnnotationEvidence(id=%s)>" % (self.id)

    def toString(self):
        "<Class EvidenceRecord id :: "+str(self.id)+" :: "+self.evidence_type_id+" >"

class AnnotationEvidenceFileUpload(Base):

    __tablename__ = 'annotation_evidence_file_upload'

    id = Column(Integer, primary_key=True)
    annotation_evidence_id = Column(Integer,ForeignKey('annotation_evidence.id'))
    filepath = Column(String)
    filename = Column(String)
    description = Column(String)
    uploaded_by_user = Column(String)
    date_uploaded = Column(DateTime)

    annotation_evidence = relationship("AnnotationEvidence")

    def __repr__(self):
        return "<EvidenceRecordFileUpload(id=%s, filename='%s', evidence_record_id=%s)>" %(self.id, self.filename, self.annotation_evidence_id)

    def toString(self):
        "<Class EvidenceRecord id :: "+str(self.id)+" :: "+self.filename+" >"


class DataRepository(Base):

    __tablename__ = 'data_repository'

    id = Column(Integer,primary_key=True)
    name = Column(String)
    accession_number = Column(String)
    submission_date = Column(DateTime)
    public_release_date = Column(DateTime)
    project_id = Column(Integer,ForeignKey('project.id'))
    project = relationship('Project')

class Protocol(Base):

    __tablename__ = 'protocol'

    id = Column(Integer,primary_key=True)
    name = Column(String)
    type = Column(String)
    description = Column(String)
    uri = Column(String)
    version = Column(String)

#class SampleAssayProtocol(Base):


class ProtocolParameter(Base):
    __tablename__ = 'protocol_parameter'

    id = Column(Integer,primary_key=True)
    protocol_id = Column(Integer,ForeignKey('project.id'))
    name = Column(String)
    value = Column(String)
    ontology_ref_id = Column(Integer,ForeignKey('ontology_ref.id'))


class SampleAssayProtocol(Base):

    __tablename__ = 'sample_assay_protocol'

    id = Column(Integer, primary_key=True)
    protocol_id = Column(Integer,ForeignKey('protocol.id'))
    protocol = relationship("Protocol",back_populates="sample_assays")
    sample_assay_id = Column(Integer,ForeignKey('sample_assay.id'))
    sample_assay = relationship("SampleAssay",back_populates="protocols")

    def __repr__(self):
        return "<SampleAssayProtocol(id=%s, protocol_id=%s, sample_assay_id=%s)>" %(self.id, self.protocol_id,self.sample_assay_id)


class Publication(Base):

    __tablename__ = 'publication'

    id = Column(Integer,primary_key=True)
    pubmed_id = Column(String)
    doi = Column(String)
    author_list = Column(JSONB)
    title = Column(String)
    status = Column(String)
    project_id = Column(Integer,ForeignKey('project.id'))
    project = relationship('Project')

class OntologySource(Base):

    __tablename__ = 'ontology_source'

    id = Column(Integer,primary_key=True)
    name = Column(String)
    url = Column(String)
    version = Column(String)
    description = Column(String)

class OntologyRef(Base):

    __tablename__ = 'ontology_ref'

    id = Column(Integer,primary_key=True)
    ontology_source_id = Column(Integer,ForeignKey('ontology_source.id'))
    ontology_source = relationship('OntologySource')
    accession_number = Column(String)
    compound_class_kingdom_id = Column(Integer,ForeignKey('compound_class.id'))
    compound_class_kingdom = relationship('CompoundClass',foreign_keys=[compound_class_kingdom_id])
    compound_class_category_id = Column(Integer,ForeignKey('compound_class.id'))
    compound_class_category = relationship('CompoundClass',foreign_keys=[compound_class_category_id])
    compound_class_main_class_id = Column(Integer,ForeignKey('compound_class.id'))
    compound_class_main_class = relationship('CompoundClass',foreign_keys=[compound_class_main_class_id])
    compound_class_sub_class_id = Column(Integer,ForeignKey('compound_class.id'))
    compound_class_sub_class = relationship('CompoundClass',foreign_keys=[compound_class_sub_class_id])
    compound_class_direct_parent_id = Column(Integer,ForeignKey('compound_class.id'))
    compound_class_direct_parent = relationship('CompoundClass',foreign_keys=[compound_class_direct_parent_id])


class HarmonisedMetadataField(Base):
    """Metadata Harmonised Field
    """

    __tablename__ = 'harmonised_metadata_field'

    __searchfields__ = '_all'

    class HarmonisedMetadataFieldDatatype(enum.Enum):
        text = "text"
        numeric = "numeric"
        datetime = "datetime"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    unit_id = Column(Integer,ForeignKey('unit.id')) # FK To unit table
    unit = relationship("Unit", backref="unit")
    datatype = Column(Enum(HarmonisedMetadataFieldDatatype))
    ontology_ref_id = Column(Integer,ForeignKey('ontology_ref.id'))
    ontology_ref = relationship('OntologyRef')
    classes = Column(JSONB)

    def __repr__(self):
        return "<HarmonisedMetadataField(id=%s, name='%s', unit='%s', datatype='%s')>" %(self.id, self.name, self.unit, self.datatype)

    def toString(self):
        retstr = "<HarmonisedMetadataField(id=%s, name='%s', unit='%s')>\n" %(self.id, self.name, self.unit)
        return retstr

    def build_search_index(self):
        return utils.flatten_model_for_search(self)

class MetadataField(Base):

    __tablename__ = 'metadata_field'

    __searchfields__ = ['id','name']

    id = Column(Integer, primary_key=True)
    harmonised_metadata_field_id = Column(Integer,ForeignKey('harmonised_metadata_field.id'))
    name = Column(String)
    project_id = Column(Integer,ForeignKey('project.id'))
    project = relationship("Project")
    harmonised_metadata_field = relationship("HarmonisedMetadataField")

    def __repr__(self):
        if self.project:
            return "<MetadataField(id=%s, project_name='%s', name='%s')>" %(self.id, self.project.name, self.name)
        else:
            return "<MetadataField(id=%s, name='%s')>" %(self.id, self.name)


    def toString(self):
        retstr = "<MetadataField(id=%s, name='%s')>" %(self.id, self.name)+"\n"
        retstr = retstr + self.harmonised_metadata_field.toString()
        return retstr

    def build_search_index(self):
        return utils.flatten_model_for_search(self)

class MetadataValue(Base):

    __tablename__ = 'metadata_value'

    __searchfields__ = ['id','raw_value','harmonised_numeric_value','harmonised_text_value','harmonised_datetime_value']

    id = Column(Integer, primary_key=True)
    raw_value = Column(String)
    harmonised_numeric_value = Column(Float)
    harmonised_text_value = Column(String)
    harmonised_datetime_value = Column(DateTime)
    metadata_field_id = Column(Integer,ForeignKey('metadata_field.id'))
    sample_id = Column(Integer,ForeignKey('sample.id'))

    sample = relationship("Sample")
    metadata_field = relationship("MetadataField")

    def __repr__(self):
        if self.metadata_field:
            return "<MetadataValue(id=%s, project_name='%s', metadata_field_name='%s', raw_value='%s')>" %(self.id,self.metadata_field.project.name, self.metadata_field.name, self.raw_value)
        else:
            return "<MetadataValue(id=%s, raw_value='%s')>" %(self.id, self.raw_value)

    def toString(self):
        retstr = "<MetadataValue(id=%s, raw_value='%s')>" %(self.id, self.raw_value)+"\n"
        return retstr

    def build_search_index(self):
        return utils.flatten_model_for_search(self) + self.metadata_field.build_search_index()



'''
Relationship declarations
'''

Project.metadata_fields = relationship("MetadataField", back_populates="project")
Project.data_repositories = relationship("DataRepository", back_populates="project")
#Project.protocols = relationship("Protocol", back_populates="project")
Project.publications = relationship("Publication", back_populates="project")

FeatureDataset.feature_columns = relationship("FeatureMetadata",back_populates="feature_dataset")

AnnotatedFeature.harmonised_annotated_feature = relationship("HarmonisedAnnotatedFeature",back_populates='annotated_feature')
#HarmonisedDataset.task_runs = relationship("AnalysisResult",back_populates='harmonised_datasets')
#SavedQuery.harmonisation_datasets = relationship("CorrectionRun",back_populates='saved_query')
TaskRun.harmonised_dataset = relationship("HarmonisedDataset",back_populates='task_run')

Sample.metadata_values = relationship("MetadataValue", back_populates="sample")

Assay.harmonised_annotations = relationship("HarmonisedAnnotation",back_populates='assay')
AnnotationMethod.harmonised_annotations = relationship("HarmonisedAnnotation",back_populates='annotation_method')

MetadataField.metadata_values = relationship("MetadataValue", back_populates="metadata_field")

HarmonisedMetadataField.metadata_fields = relationship("MetadataField", back_populates="harmonised_metadata_field")

MetadataValue.samples = relationship("Sample", back_populates="metadata_value")

Compound.external_dbs = relationship("CompoundExternalDB", back_populates="compound")
ExternalDB.compounds = relationship("CompoundExternalDB", back_populates="external_db")

Compound.harmonised_annotations = relationship("AnnotationCompound", back_populates="compound")
HarmonisedAnnotation.compounds = relationship("AnnotationCompound", back_populates="harmonised_annotation")

Compound.compound_classes = relationship("CompoundClassCompound", back_populates="compound")
CompoundClass.compounds = relationship("CompoundClassCompound", back_populates="compound_class")

SampleAssay.protocols = relationship("SampleAssayProtocol", back_populates="sample_assay")
Protocol.sample_assays = relationship("SampleAssayProtocol", back_populates="protocol")

#ChemicalStandardDataset.annotation_evidences = relationship("AnnotationEvidence",back_populates='chemical_standard_dataset')
"""
AnnotationCompound.evidence_records = relationship("AnnotationCompoundConfigEvidenceRecord", back_populates="annotation_compound")
EvidenceRecord.annotation_compounds = relationship("AnnotationCompoundConfigEvidenceRecord", back_populates="evidence_record")
"""