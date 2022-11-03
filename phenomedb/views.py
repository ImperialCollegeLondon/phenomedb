
import json, os, time, datetime, sys, fnmatch
import glob
import pandas as pd
import phenomedb.database as db
from pprint import pprint
from phenomedb.base_view import PhenomeDBBaseView
from phenomedb.models import EvidenceRecord, EvidenceType, Project
from phenomedb.tasks.imports.import_sample_manifest import ImportSampleManifest
from phenomedb.tasks.imports.import_data_locations import ImportDataLocations

from phenomedb.tasks.imports.ivdr_import_task_basic_csv import IVDRImportTaskBasicCSV
from phenomedb.tasks.imports.import_targetlynx_annotations import ImportTargetLynxAnnotations
from phenomedb.tasks.imports.import_peakpanther_annotations import ImportPeakPantherAnnotations
from phenomedb.tasks.imports.import_bruker_ivdr_annotations import ImportBrukerIVDRAnnotations
from phenomedb.models import *
from phenomedb import utilities as utils
import logging
from sonic import SearchClient


    

def get_compound_assay_evidence(base_view):
    """Get the compound assay evidence

    :param base_view: the phenomedb base view class.
    :type base_view: :class:`phenomedb.base_view.PhenomeDBBaseView`
    :return: The compound and compound_assay data.
    :rtype: dict
    """    
    
    data = {}
    data["compound"] = base_view.execute_sql("SELECT id, name from compound where id = :id", {"id":1595})
   
    data['compound_assay'] = base_view.execute_sql( "SELECT * from v_annotation_compound_config_evidence_records WHERE id = :id", {"id":48} )
    return data

def compound_assay(base_view, id): 
    """Get the annotation_compound_config evidence by annotation_compound_config.id

    :param base_view: the phenomedb base view class.
    :type base_view: :class:`phenomedb.base_view.PhenomeDBBaseView`
    :param id: the annotation_compound_config.
    :type id: integer
    :return: The evidence dictionary.
    :rtype: dict
    """    
       
    data = {} 
    compound_assay_evidence = base_view.execute_sql("SELECT * from v_annotation_compound_config_evidence_records where annotation_compound_config_id = :id", {"id":id})
    print(len(compound_assay_evidence))
    evidence=[]
    if len(compound_assay_evidence) > 0:
        first_row = compound_assay_evidence[0]
        assay_keys = ('compound_id', 'compound_name', 'assay_id', 'compound_assay_id', 'assay_name', 'cpd_name', 'feature_name', 'secondary_compound_id')
       
        compound_assay = {x: first_row[x] for x in assay_keys if x in first_row}
        for result in compound_assay_evidence:
            evidence_record_id = result["evidence_record_id"]
            if evidence_record_id:
                file_uploads = base_view.execute_sql("SELECT * from evidence_record_file_upload where evidence_record_id = :id", {"id":evidence_record_id}) 
               
            
                result["files"] = json.dumps(file_uploads, default=str)
                for a in assay_keys:
                    del result[a]                   
                evidence.append(result) 
    data['evidence'] = evidence
    return data
                
def insert_evidence_record(json_object, type_id):
    """Insert an evidence record

    :param json_object: The json object containing the model values.
    :type json_object: dict
    :param type_id: the :class:`phenomedb.models.EvidenceType` id.
    :type type_id: integer
    """    
    # test jsonb      
    er = EvidenceRecord()   
    er.evidence_type_id = type_id
    er.analysed_by_user ="Jazz"
    er.validated_by_user = "Chris"
    er.recorded_by_user = "Gordon"
    er.date_analysed = "2021-01-20"
    er.comments = "this is a test"
    er.json_data = json_object
    
    # insert to evidence_record
    db_session = db.get_db_session()
    db_session.add(er)
    db_session.commit()
    
    for a in db_session.query(EvidenceRecord).all():
        print(a.json_data)
    for a in db_session.query(EvidenceRecord).filter(EvidenceRecord.json_data.contains([{"one": 1}])).all():  
        pprint(a.json_data) 

def look_for_directories():
    """Function to recursively look for :class:`phenomedb.models.SampleAssay` assay base names.
    """    
    rds_base_path = '/Volumes/jms3/projects'
    
    session = db.get_db_session()
    projects = session.query(Project).all()
    project_list = []
    
    for project in projects:
        print('--------------------------------------------')
        if os.path.isdir(rds_base_path):
            project_dir = os.path.join(rds_base_path, project.project_folder_name)
            if os.path.isdir(project_dir):
                project_dict = {}
                project_dict["project_id"] = project.id
                project_dict["project_name"] = project.name
                project_dict["project_rds_folder"] = project.project_folder_name
               
            
                result = session.execute("select * from v_sample_assays_by_project where project_id = :id ",
                                         {"id": project.id}).fetchall()
                base_names = [base_name for id, base_name in result]
                if len(base_names) > 0:                         
                   
                    #project_dict["sample_base_names"] = base_names
                    project_dict["sample_base_name_count"] = len(base_names)
                    report = {}
                    for b in base_names:
                        matched_files = []
                        print("looking for", b)
                        
                        search_path = os.path.join(project_dir, "/live/study data/analytical/raw/")
                        for parent, dir, files in os.walk(search_path):
                            for name in files:
            
                                if fnmatch.fnmatch(name.lower(), b.lower() ):
                                    print("------------------------------------------------------------>",os.path.join(parent, name))
                                    matched_files.append(os.path.join(parent, name))
                        
                        """
                        pat = "/live/Study Data/Analytical/raw/**/"
                        dir_pattern = project_dir + pat + b
                        files = glob.glob(dir_pattern, recursive=True)  
                        for f in files:
                            print("found", f)
                            matched_files.append(f)
                        """
                        report[b] = matched_files
                            
                    project_dict["matched_files_count"] = len(matched_files)
                    project_dict["matched_files"] = report
                else:
                    print("No data locations found in project")   
                project_list.append(project_dict)
        else:
            project_list.append(project.name) 
    
    if not os.path.isdir(rds_base_path):
        print("RDS drive unavailable")
        project_list.sort()
        pprint(project_list)     
    else:    
        #df = pd.DataFrame.from_dict(project_list)
        #df.to_csv("/Users/jms3/Desktop/rds_project_files.csv")
        pprint(project_list)
 
def import_project(project):
    """Import a project + sample manifest.

    :param project: dictionary containing the project['name'] and the project['manifest'].
    :type project: dict
    """    

    db_session = db.get_db_session()
    project_name= project['name']
    sample_manifest_path = project['manifest']

    project = db_session.query(Project).filter(Project.name==project_name).first()
    print("loading project", project)
    if project is None:
        print("making new project")
        project = Project(name = project_name,
                                description = None,
                                lims_id = None,
                                project_folder_name = None,
                                date_added = datetime.datetime.now())

        db_session.add(project)
        db_session.commit()
                   
    task = ImportSampleManifest(project_name,sample_manifest_path)
    task.run(db_session=db_session)
    db_session.close()
       
def load_datalocations(project):
    """Load the datalocations.

    :param project: dictionary containing the project['name'] and the project['data_locations'].
    :type project: dict
    """    
    db_session = db.get_db_session()
    count = 0
    if project["data_locations"]:
        for s in project["sample_types"]:
            print("loading", s)
            print("file", project["data_locations"][count])
            task = ImportDataLocations(project_name=project["name"],
                                       data_locations_path=project["data_locations"][count],
                                       sample_matrix=s,
                                       assay_platform="NMR")
            count = count + 1
            output = task.run(db_session=db_session)

            print(output)
    db_session.close()


    
def walk(top, match_str, max_depth ):
    """Recursively search the folders for the match_str, up to a max_depth.

    :param top: The start folder path.
    :type top: str
    :param match_str: The string to match.
    :type match_str: str
    :param max_depth: The max search depth.
    :type max_depth: int
    :yield: The matching folder/file.
    :rtype: str
    """    
    
    dirs, nondirs, matched = [], [], []
    
    for entry in os.scandir(top):   
        (dirs if entry.is_dir() else nondirs).append(entry.path)
        
        fname = os.path.basename(entry.path).lower()
        
        if fnmatch.fnmatch(fname.lower(), match_str ):
            matched.append(entry.path)
            
    yield top, dirs, nondirs, matched
    if max_depth > 1:
        for path in dirs:
            for x in walk(path, match_str, max_depth-1):
                yield x

def attribute_dict(orm_object):
    """Convert a model object into a dictionary

    :param orm_object: The :class:`phenomedb.models.*` model.
    :type orm_object: :class:`phenomedb.models.*`
    :return: The converted dictionary.
    :rtype: dict
    """    

    #print("type of entity is", type(entity))
    mapper = class_mapper(orm_object.__class__)

    attr_dict = {}

    for col in mapper.columns.keys():
        
        col_value = getattr(orm_object, col)

        attr_dict[col] = col_value

    return attr_dict
    
def get_entities_as_dicts(entity_list):
    """Convert list of models into a list of attribute_dicts.

    :param entity_list: The list of :class:`phenomedb.models.*` models.
    :type entity_list: list
    :return: The list of converted attribute_dicts.
    :rtype: list
    """    

    result = []
    for entity in entity_list:
        table_map = attribute_dict(entity)
        result.append(table_map)
    return result
    
def search(search_term):
    """Search against the Sonic search index.

    :param search_term: The term to search.
    :type search_term: str
    :return: The matching models for the search.
    :rtype: list
    """    

    db_session = db.get_db_session()

    search_cats = {Compound:        ["Compounds", "Compound", "CompoundView.compound"],
                  Sample :   ["Sampling Events", "Sample", "ViewData.sample"],
                  ChemicalStandardPeakList:        ["Standards", "ChemicalStandardPeakList", "CompoundView.chemical_standard_dataset"],
                  Annotation:      ["Annotations", "Annotation","CompoundView.chemical_standard_dataset"]
                  }
                      
    search_results = {}
    if len(search_term) > 0:
        with SearchClient("127.0.0.1", 1491, "password") as querycl:

            for model, bucket in search_cats.items():
                
                result_header = bucket[0]
                
                model_object = bucket[1]
                ids = querycl.query("main", model_object, search_term)
                if len(ids) > 0:
                    
 
                    entity_list = db_session.query(model).filter(model.id.in_(ids)).all()
                    as_dicts  = get_entities_as_dicts(entity_list) 
                    search_results[model_object] = {"label":result_header,"entities":entity_list}
                else:
                    search_results[model_object] = []
    
    return search_results
       

def sample_event(id):
    """Get the Sample by id.

    :param id: the :class:`phenomedb.models.Sample` id.
    :type id: int
    """    
    
    data = {}
    db_session = db.get_db_session()


    sample = db_session.query(Sample).filter(Sample.id == id).first()
    if sample:
        
        data['sample'] = sample
        data['assays'] = sample.sample_assays
        
        for assay in sample.sample_assays:
            assay_id = assay.id
            print("assay id is ", assay_id)
            temp = db_session.execute("select * from annotated_feature where sample_assay_id = :id",
                                        {"id": assay_id}).fetchall()
            
            pprint(temp)

def count_annotations(base_view):
    """Count the annotations

    :param base_view: The PhenomeDB base view.
    :type base_view: :class:`phenomedb.base_view.PhenomeDBBaseView`
    :return: The number of the annotation_run records.
    :rtype: int
    """    

    sql = "select count(*) from v_annotations "  
    count_all = base_view.execute_sql(sql)
    return count_all

def build_sql_by_column(columns):
    """Build SQL by column.

    :param columns: The list of column definitions.
    :type columns: list
    :return: The SQL and params, ready for execute.
    :rtype: tuple
    """    

    sql = "select * from v_annotations where sample_id is not null"
    params = {}
    
    for col in columns:
        pprint(col)
        if len(col["search"]["value"]) == 0:
            continue
        sql += " AND " + col["data"] + " " + col["search"]["condition"] + " :" + col["data"]
        params[col["data"]] = col["search"]["value"]


    return (sql,params)
    
def build_global_search_filter(base_view, search_term):
    """Build the global search filter for annotations.

    :param base_view: The PhenomeDB base view.
    :type base_view: :class:`phenomedb.base_view.PhenomeDBBaseView`
    :param search_term: The term to search for.
    :type search_term: str
    :return: The list of annotations.
    :rtype: list
    """    

    search_term = '%' + search_term + "%"
    sql = "select * from v_annotations WHERE sample_id::text ILIKE :term "
    params = {}
    ANNOTATION_FIELDS = ["assay", "annotation_method", "compound", "inchi", "inchi_key", 
                                "cpd_name", "monoisotopic_mass", "intensity","lod", "lloq", "uloq"]
    for col in ANNOTATION_FIELDS:            
        sql += " OR " + col + "::text ILIKE :term"
        
    params["term"] = search_term
    pprint(sql)
    pprint(params)
    result = base_view.execute_sql(sql, params)
    return result
    
if __name__ == "__main__":
     
    testing = { 'name': 'PipelineTesting',
               'manifest': os.path.join("../test_data/sample_manifests/DEVSET_sampleManifest.xlsx"),
               'data_locations': ["../test_data/NMR/PipelineTesting_IVDr Urine Method_CPC-NMR01_70 COMPLETE_data_locations (6).csv",
                                  "../test_data/targeted MS/devset_plasma_dataset_locations.csv",
                                  "../test_data/untargeted MS/ToFO5_69_POS_data_locations.csv"],
               'sample_types' : ["Plasma", "Urine"],
               'sample_matrix':"Urine",
               'unified_csv_path' : "../test_data/untargeted MS/devset U LPOS peakPantheR_combinedData.csv"

               }
    
    everest = {'name':'EVEREST', 
               'manifest': os.path.join("../test_data/sample_manifests/Ph Ce Version minus Xs with box positions.xlsx"),
               'sample_types' : None,
               'data_locations': None}
    keunplt = {'name':'KeunPlt', 
               'manifest': os.path.join("../test_data/sample_manifests/ACtox_EK.xls"),
               'sample_types' : None,
               'data_locations': None}
    airwave = {'name':'AIRWAVE', 
               'manifest': os.path.join("../test_data/sample_manifests/New AIRWAVE sample manifest.xlsx"),
               'sample_types' : None,
               'data_locations': None,
               'annotation_method_name':"Bruker IVDR BiQuant",
               'unified_csv_path' : os.path.join("../test_data/NMR/AIRWAVE_P_BIQUANTv2_combinedData_truncated.csv"),
               'sample_matrix':"Plasma"
               
               }
    mars = {'name': 'MARS', 
            'manifest': os.path.join("../test_data/sample_manifests/PCDOC.014_MARS project_updated.xls"),
            'sample_types' : None,
            'data_locations': None}
    behive = {'name': 'BEHIVE', 
              'manifest': os.path.join("../test_data/sample_manifests/BEHIVE Reformated 310717.xls"),
              'sample_types' : None,
              'data_locations': None
              }
    polygut = {'name': 'PolyGut', 
              'manifest': os.path.join("../test_data/sample_manifests/PolyGut_deblinded_PT.xls"),
              'sample_types' : ["Plasma", "Urine"],
              'data_locations': ["../test_data/NMR/data_locations_PolyGut_NMR_Plasma","../test_data/NMR/data_locations_PolyGut_NMR_Urine"]}

    guthorm = {'name': 'GutHorm', 
              'manifest': os.path.join("../test_data/sample_manifests/GutHorm.xls"),
              'sample_types' : ["Plasma", "Urine"],
              'data_locations': ["../test_data/NMR/data_locations_GutHorm_NMR_Plasma","../test_data/NMR/data_locations_GutHorm_NMR_Urine"]}


    #ans = search("acid")

    #import_project(airwave)
    #load_datalocations(airwave)
    #load_datalocations(testing)
    #loadAnnotations(testing)

    #sample_event(3)
    """
                                       
    look_for_directories()

    import_project(polygut)
    load_datalocations(polygut)
    import_project(guthorm)
    load_datalocations(guthorm)
    """
    view_class = PhenomeDBBaseView()  
    view_class.configure_logging("test-jms")
    view_class.set_db(db.DB_PROD)  
        
 
    

    data = [{'data': 'assay',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': 'a'},
              'searchable': True},
             {'data': 'annotation_method',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': 's'},
              'searchable': True},
             {'data': 'compound',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': 'd'},
              'searchable': True},
             {'data': 'inchi',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': 'f'},
              'searchable': True},
             {'data': 'inchi_key',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': ''},
              'searchable': True},
             {'data': 'cpd_name',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': ''},
              'searchable': True},
             {'data': 'monoisotopic_mass',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': ''},
              'searchable': True},
             {'data': 'intensity',
              'name': '',
              'orderable': True,
              'search': {'condition': 'equal to', 'regex': False, 'value': ''},
              'searchable': True}
             ]

    
    #sql, params = build_sql_by_column(data)
    
    #result = build_global_search_filter(view_class,'XKBJVQHMEXMFDZ-AREMUKBSSA-N')
    #pprint(len(result))
    df = pd.DataFrame()
        
    db_session = db.get_db_session()
    stmt = text("select * from v_annotations_no_group_by")
    df = pd.read_sql(sql=stmt, params={}, con=db_session.connection())

    pprint(df.columns)



    
   
