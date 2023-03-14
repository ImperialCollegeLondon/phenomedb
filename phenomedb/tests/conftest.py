import pytest

#import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])

import phenomedb.database as db
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from phenomedb.config import config
from phenomedb.query_factory import *

import datetime
import zipfile
import requests
import json
import importlib

DB_ENV = "TEST"
PROJECT_NAME = "PipelineTesting"
LAB_NAME = "TestLab"
LAB_AFFILIATION = "TestUniversity"
USERNAME = config['PIPELINES']['pipeline_manager_user']

@pytest.fixture(scope="module")
def create_min_database():

    engine = create_engine(db.test_database_connection_string, echo=False, execution_options={
        "isolation_level": "AUTOCOMMIT"
    })

    engine = db.test_engine
    # modifications here to work with both MySQL and Postgres
    if database_exists(engine.url):
        drop_database(engine.url)
        print("dropped database", engine.url)
    create_database(engine.url)
    print("created database", engine.url)
    db_session = db.get_test_database_session()

    create_test_db(engine,db_session)

    return engine, db_session


def create_test_db(engine,db_session):

    print("Setting Up Database " + config['DB']['test'])

    try:

        sql_file = open(config['DB']['create_script'], 'r', encoding='utf-8-sig')
        run_sql_script(sql_file,engine)
        sql_file.close()

#        print("Importing data")

#        sql_file = open(config['DB']['create_script'], 'r', encoding='utf-8-sig')
#        run_sql_script(sql_file,engine)
#        sql_file.close()

#        print("Built " + config['DB']['test'] +" from scripts")

    except Exception as e:
        print("Exiting with error", e)
        exit()

def run_sql_script(sql_file,engine):
    # Create an empty command string
    statement = ""

    # Iterate over all lines in the sql file
    count = 0
    for line in sql_file:
        count = count + 1
        line=line.rstrip()
        #print(str(count) + " [LINE]:", line)
        if line == '' or line.startswith('--') or line.startswith("#") or line.startswith("/"):  # ignore sql comment lines
            #print(str(count) + " [COMMENT] Ignoring Comment: %s" % line)
            continue
        if (not line.endswith(';')):  # keep appending lines that don't end in ';'
            statement = statement + line
            #print(str(count) + " [APPENDING]:", statement)
        else:  # when you get a line ending in ';' then exec statement and reset for next statement
            statement = statement + line
            #print (str(count) + " [EXECUTE] Executing SQL statement: %s" % (statement))
            try:
                #escape percent sign which causes problems
                statement=statement.replace("%","%%")
                statement=str(statement)

                engine.execute(statement)

            except Exception as e:
                print ("[WARN] Error during execute statement : \n%s" % (str(statement)))
                #print("WARNING")
                print(e.__str__())

            statement = ""

@pytest.fixture(scope="module")
def create_pipeline_testing_project():

    from phenomedb.task import CreateProject

    task = CreateProject(project_name=PROJECT_NAME,
                         project_folder_name='pipeline_testing',
                         description="The test project",
                         username=USERNAME,
                         db_env=DB_ENV)
    task.run()

def create_project(project_name):

    from phenomedb.task import CreateProject
    task = CreateProject(project_name=project_name,
                         project_folder_name='pipeline_testing',
                         description="The test project",
                         db_env=DB_ENV,
                         username=USERNAME)
    task.run()

@pytest.fixture(scope="module")
def create_age_sex_harmonised_fields():

    from phenomedb.task import CreateHarmonisedMetadataField
    task = CreateHarmonisedMetadataField(name='Age',
                                         unit_name='Years',
                                         datatype='numeric',
                                         unit_description='Years (ie age)',
                                         username=USERNAME,
                                         db_env=DB_ENV)
    task.run()

    task = CreateHarmonisedMetadataField(name='Sex',
                                         unit_name='noUnit',
                                         datatype='text',
                                         unit_description='noUnit',
                                         username=USERNAME,
                                         db_env=DB_ENV)
    task.run()

@pytest.fixture(scope="module")
def create_lab():

    from phenomedb.task import CreateLab

    task = CreateLab(lab_name=LAB_NAME,
                     lab_affiliation=LAB_AFFILIATION,
                     username=USERNAME,
                     db_env=DB_ENV)
    task.run()

@pytest.fixture(scope="module")
def create_nmr_assays():

    from phenomedb.task import CreateAssay

    task = CreateAssay(assay_name="NOESY",
                       platform='NMR',
                       targeted="N",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV
                       )
    task.run()

    task = CreateAssay(assay_name="CPMG",
                       platform='NMR',
                       targeted="N",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="JRES",
                       platform='NMR',
                       targeted="N",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

@pytest.fixture(scope="module")
def create_ms_assays():

    from phenomedb.task import CreateAssay

    task = CreateAssay(assay_name="HPOS",
                       platform='MS',
                       targeted="N",
                       ms_polarity="+ve",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="LPOS",
                       platform='MS',
                       targeted="N",
                       ms_polarity="+ve",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="LNEG",
                       platform='MS',
                       targeted="N",
                       ms_polarity="-ve",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="RPOS",
                       platform='MS',
                       targeted="N",
                       ms_polarity="+ve",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="RNEG",
                       platform='MS',
                       targeted="N",
                       ms_polarity="-ve",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="BANEG",
                       platform='MS',
                       targeted="N",
                       ms_polarity="-ve",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="LC-QqQ Tryptophan",
                       platform='MS',
                       targeted="Y",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="LC-QqQ Bile Acids",
                       platform='MS',
                       targeted="Y",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="LC-QqQ Amino Acids",
                       platform='MS',
                       targeted="Y",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

    task = CreateAssay(assay_name="LC-QqQ Oxylipins",
                       platform='MS',
                       targeted="Y",
                       ms_polarity="NA",
                       laboratory_name=LAB_NAME,
                       username=USERNAME,
                       db_env=DB_ENV)
    task.run()

@pytest.fixture(scope="module")
def create_annotation_methods():

    from phenomedb.task import CreateAnnotationMethod

    task = CreateAnnotationMethod(annotation_method_name="Bi-Quant-P",
                                  description='Bruker IVDR BI-QUANT on NMR',
                                  username=USERNAME,
                                  db_env=DB_ENV)
    task.run()

    task = CreateAnnotationMethod(annotation_method_name="Bi-Quant-U",
                                  description='Bruker IVDR BI-QUANT on NMR',
                                  username=USERNAME,
                                  db_env=DB_ENV)
    task.run()

    task = CreateAnnotationMethod(annotation_method_name="Bi-LISA",
                                  description='Bruker IVDR BI-LISA on NMR',
                                  username=USERNAME,
                                  db_env=DB_ENV)
    task.run()

    task = CreateAnnotationMethod(annotation_method_name="TargetLynx",
                                  description='Waters TargetLynx LC_MS',
                                  username=USERNAME,
                                  db_env=DB_ENV)
    task.run()

    task = CreateAnnotationMethod(annotation_method_name="PPR",
                                  description='PeakPantheR RT-match on untargeted LC-MS',
                                  username=USERNAME,
                                  db_env=DB_ENV)
    task.run()


@pytest.fixture(scope="module")
def import_devset_sample_manifest():

    from phenomedb.imports import ImportSampleManifest

    task = ImportSampleManifest(project_name=PROJECT_NAME,
                                sample_manifest_path=config['DATA']['test_data'] + 'DEVSET_sampleManifest.xlsx',
                                columns_to_ignore=['Further Sample info?'],
                                username=USERNAME,
                                db_env=DB_ENV)
    output = task.run()
    return output

def import_devset_project_sample_manifest(project_name):

    from phenomedb.imports import ImportSampleManifest

    task = ImportSampleManifest(project_name=project_name,
                                sample_manifest_path=config['DATA']['test_data'] + 'DEVSET_sampleManifest.xlsx',
                                columns_to_ignore=['Further Sample info?'],
                                username=USERNAME,
                                db_env=DB_ENV)

    return task.run()

@pytest.fixture(scope="module")
def import_devset_datalocations_nmr():

    from phenomedb.imports import ImportDataLocations

    task = ImportDataLocations(project_name=PROJECT_NAME,
                               data_locations_path=config['DATA']['test_data'] + 'DEVSET_datalocations_NMR.csv',
                               sample_matrix="plasma",
                               assay_platform="NMR",
                               assay_name="NOESY",
                               username=USERNAME,
                               db_env=DB_ENV)

    return task.run()

def import_devset_project_datalocations_ba_plasma(project_name):

    from phenomedb.imports import ImportDataLocations

    task = ImportDataLocations(project_name=project_name,
                               data_locations_path= config['DATA']['test_data'] + 'DEVSET_plasma_BA_dataset_locations.csv',
                               sample_matrix="Plasma",
                               assay_name="LC-QqQ Bile Acids",
                               assay_platform='MS',
                               username=USERNAME,
                               db_env=DB_ENV)

    return task.run()

@pytest.fixture(scope="module")
def import_devset_ivdr_biquant_annotations():

    from phenomedb.imports import ImportBrukerIVDRAnnotations

    task = ImportBrukerIVDRAnnotations(project_name=PROJECT_NAME,
                                       username=USERNAME,
                                       annotation_method="Bi-Quant-P",
                                       unified_csv_path=config['DATA']['test_data'] + 'DEVSET_P_BIQUANTv2_combinedData.csv',
                                       sample_matrix="plasma",
                                       db_env=DB_ENV)

    return task.run()

def import_devset_project_ivdr_biquant_annotations(project_name):

    from phenomedb.imports import ImportBrukerIVDRAnnotations

    task = ImportBrukerIVDRAnnotations(project_name=project_name,
                                       username=USERNAME,
                                       annotation_method="Bi-Quant-P",
                                       unified_csv_path=config['DATA']['test_data'] + 'DEVSET_P_BIQUANTv2_combinedData.csv',
                                       sample_matrix="plasma",
                                       db_env=DB_ENV
                                       )

    return task.run()

@pytest.fixture(scope="module")
def import_devset_ivdr_bilisa_annotations():

    from phenomedb.imports import ImportBrukerIVDRAnnotations

    task = ImportBrukerIVDRAnnotations(project_name=PROJECT_NAME,
                                       username=USERNAME,
                                       annotation_method="Bi-LISA",
                                       unified_csv_path=config['DATA']['test_data'] + 'DEVSET_P_BILISA_combinedData.csv',
                                       sample_matrix="plasma",
                                       db_env=DB_ENV
                                       )

    output = task.run()
    return output

def import_devset_project_ivdr_bilisa_annotations(project_name):

    from phenomedb.imports import ImportBrukerIVDRAnnotations

    task = ImportBrukerIVDRAnnotations(project_name=project_name,
                                       username=USERNAME,
                                       annotation_method="Bi-LISA",
                                       unified_csv_path=config['DATA']['test_data'] + 'DEVSET_P_BILISA_combinedData.csv',
                                       sample_matrix="plasma",
                                       db_env=DB_ENV
                                       )

    return task.run()

@pytest.fixture(scope="module")
def import_devset_lpos_peakpanther_annotations():

    from phenomedb.imports import ImportPeakPantherAnnotations

    task = ImportPeakPantherAnnotations(project_name=PROJECT_NAME,
                                        username=USERNAME,
                                        feature_metadata_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_featureMetadata.csv',
                                        sample_metadata_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_sampleMetadata_SMALL.csv',
                                        intensity_data_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_intensityData.csv',
                                        batch_corrected_data_csv_path=config['DATA']['test_data'] + 'DEVSET P LPOS PeakPantheR_intensityData_batchcorrected.csv',
                                        ppr_annotation_parameters_csv_path=config['DATA']['test_data'] + 'DEVSET_P_LPOS_annotationParameters_summary.csv',
                                        ppr_mz_csv_path=config['DATA']['test_data'] + 'DEVSET_P_LPOS_PPR_mz.csv',
                                        #ppr_rt_csv_path=config['DATA']['test_data'] + 'DEVSET_P_LPOS_PPR_rt.csv',
                                        ppr_rt_csv_path=config['DATA']['test_data'] + 'DEVSET_P_LPOS_PPR_rt_with_extra_paths.csv',
                                        sample_matrix="plasma",
                                        assay_name="LPOS",
                                        run_batch_correction=False,
                                        db_env=DB_ENV
                                       )

    return task.run()

def import_devset_project_lpos_peakpanther_annotations(project_name,validate=True):
    from phenomedb.imports import ImportPeakPantherAnnotations

    task = ImportPeakPantherAnnotations(project_name=project_name,
                                        username=USERNAME,
                                        feature_metadata_csv_path=config['DATA'][
                                                                      'test_data'] + 'DEVSET P LPOS PeakPantheR_featureMetadata.csv',
                                        sample_metadata_csv_path=config['DATA'][
                                                                     'test_data'] + 'DEVSET P LPOS PeakPantheR_sampleMetadata_SMALL.csv',
                                        intensity_data_csv_path=config['DATA'][
                                                                    'test_data'] + 'DEVSET P LPOS PeakPantheR_intensityData.csv',
                                        batch_corrected_data_csv_path=config['DATA'][
                                                                          'test_data'] + 'DEVSET P LPOS PeakPantheR_intensityData_batchcorrected.csv',
                                        ppr_annotation_parameters_csv_path=config['DATA'][
                                                                               'test_data'] + 'DEVSET_P_LPOS_annotationParameters_summary.csv',
                                        ppr_mz_csv_path=config['DATA']['test_data'] + 'DEVSET_P_LPOS_PPR_mz.csv',
                                        ppr_rt_csv_path=config['DATA'][
                                                            'test_data'] + 'DEVSET_P_LPOS_PPR_rt_with_extra_paths.csv',
                                        sample_matrix="plasma",
                                        assay_name="LPOS",
                                        db_env=DB_ENV,
                                        validate=validate,
                                        run_batch_correction=False
                                        )

    return task.run()

@pytest.fixture(scope="module")
def import_devset_bile_acid_targeted_annotations():

    from phenomedb.imports import ImportTargetLynxAnnotations

    task = ImportTargetLynxAnnotations(project_name=PROJECT_NAME,
                                        username=USERNAME,
                                        unified_csv_path = config['DATA']['test_data'] + 'DEVSET BileAcid Plasma_combinedData.csv',
                                        sop = 'BileAcidMS',
                                        sop_version = 1.0,
                                        assay_name = 'LC-QqQ Bile Acids',
                                        sample_matrix = 'plasma',
                                       db_env=DB_ENV
                                        )

    return task.run()

def import_devset_project_bile_acid_targeted_annotations(project_name):

    from phenomedb.imports import ImportTargetLynxAnnotations

    task = ImportTargetLynxAnnotations(project_name=project_name,
                                       username=USERNAME,
                                       unified_csv_path = config['DATA']['test_data'] + 'DEVSET BileAcid Plasma_combinedData.csv',
                                       sop = 'BileAcidMS',
                                       sop_version = 1.0,
                                       assay_name = 'LC-QqQ Bile Acids',
                                       sample_matrix = 'plasma',
                                        db_env=DB_ENV
                                       )

    return task.run()


@pytest.fixture(scope="session")
def get_api_access_token():
    data = {"username": config['PIPELINES']['pipeline_manager_user'],"password":config['PIPELINES']['pipeline_manager_password'],"provider": 'ldap'}

    session = requests.session()
    r = session.post('http://localhost:5000/custom/api/v1/security/login', json=data)
    response = json.loads(r.content)
    response = {}
    print(response)
    if 'access_token' in response:
        access_token = response['access_token']

    else:
        data = {"username": 'admin',
                "password": 'testpass',
                "provider": 'db'}

        session = requests.session()
        r = session.post('http://localhost:5000/custom/api/v1/security/login', json=data)
        response = json.loads(r.content)
        print(response)
        access_token = response['access_token']

    return access_token

@pytest.fixture(scope="module")
def create_saved_queries():
    project_name = 'PipelineTesting2'
    create_project(project_name)
    import_devset_project_sample_manifest(project_name)
    import_devset_project_ivdr_bilisa_annotations(project_name)

    query_factory = QueryFactory(query_name='test_query_bilisa',query_description='test description',db_env='TEST')
    query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
    query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='Bi-LISA'))
    query_factory.add_filter(query_filter=QueryFilter(model='Assay', property='name', operator='eq', value='NOESY'))
    query_factory.save_query()
#    query_factory.load_dataframe(reload_cache=True,output_model='AnnotatedFeature')

    query_factory = QueryFactory(query_name='test_query_bilisa_2_projects',query_description='test description',db_env='TEST')
    query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='in',value=['PipelineTesting','PipelineTesting2']))
    query_factory.add_filter(query_filter=QueryFilter(model='Assay', property='name', operator='eq', value='NOESY'))
    query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod',property='name',operator='eq',value='Bi-LISA'))
    query_factory.save_query()
#    query_factory.load_dataframe(reload_cache=True,output_model='AnnotatedFeature')

    query_factory = QueryFactory(query_name='test_query_lpos',query_description='test description',db_env='TEST')
    query_factory.add_filter(query_filter=QueryFilter(model='Project',property='name',operator='eq',value='PipelineTesting'))
    query_factory.add_filter(query_filter=QueryFilter(model='Assay',property='name',operator='eq',value='LPOS'))
    query_factory.add_filter(query_filter=QueryFilter(model='AnnotationMethod', property='name', operator='eq', value='PPR'))
    query_factory.save_query()
#    query_factory.load_dataframe(reload_cache=True,output_model='AnnotatedFeature')

@pytest.fixture(scope="function")
def delete_test_cache():

    cache = Cache()
    cache.delete_keys_by_regex('TEST')

@pytest.fixture(scope="function")
def delete_saved_queries():
    #db_session = db.get_test_database_session()
    #db_session.query(SavedQuery).delete()
    #db_session.commit()
    pass

@pytest.fixture(scope="module")
def import_lcms_untargeted():

    from phenomedb.imports import ImportLCMSUntargeted

    task = ImportLCMSUntargeted(project_name=PROJECT_NAME,
                                       username=USERNAME,
                                       dataset_path = config['DATA']['test_data'] + 'DEVSET U RPOS xcms.csv',
                                       assay_name = 'RPOS',
                                       sample_matrix = 'urine',
                                        sample_metadata_path = config['DATA']['test_data'] + 'DEVSET U RPOS Basic CSV.csv',
                                        db_env=DB_ENV
                                       )

    return task.run()

@pytest.fixture(scope="module")
def npc_setup():

    from phenomedb.pipelines import NPCSetup

    task = NPCSetup(db_env=DB_ENV,add_pipelines=False)
    return task.run()

@pytest.fixture(scope="session")
def add_single_task_pipelines():

    from phenomedb.pipelines import GenerateSingleTaskPipelines

    task = GenerateSingleTaskPipelines(db_env=DB_ENV)
    return task.run()

@pytest.fixture(scope="module")
def import_compounds():
    config_file = config['DATA']['config'] + "npc-setup.json"
    with open(config_file) as json_file:
        npc_config = json.load(json_file)

    module = importlib.import_module('phenomedb.compounds')

    for args in npc_config['compounds']:
        task_class = args['task_class']
        del args['task_class']
        if 'roi_file' in args.keys():
            args['roi_file'] = config['DATA']['compounds'] + args['roi_file']
        elif 'bilisa_compounds_file' in args.keys():
            args['bilisa_compounds_file'] = config['DATA']['compounds'] + args['bilisa_compounds_file']
        elif 'biquant_compounds_file' in args.keys():
            args['biquant_compounds_file'] = config['DATA']['compounds'] + args['biquant_compounds_file']
        elif 'targetlynx_compounds_file' in args.keys():
            args['targetlynx_compounds_file'] = config['DATA']['compounds'] + args['targetlynx_compounds_file']

        args['db_env'] = 'TEST'

        class_ = getattr(module, task_class)

        if args['assay_name'] == 'HPOS':
            bp = True

        task_instance = class_(**args)

        task_instance.run()

@pytest.fixture(scope="module")
def dummy_harmonise_annotations():

    db_session = db.get_test_database_session()
    unharmonised_annotations = db_session.query(Annotation).filter(Annotation.harmonised_annotation_id==None).all()

    for annotation in unharmonised_annotations:
        harmonised_annotation = None
        harmonised_annotation = db_session.query(HarmonisedAnnotation).filter(HarmonisedAnnotation.annotation_method_id==annotation.annotation_method_id)\
                                        .filter(HarmonisedAnnotation.cpd_name==annotation.cpd_name)\
                                        .filter(HarmonisedAnnotation.assay_id==annotation.assay_id).first()
        if not harmonised_annotation:
            harmonised_annotation = HarmonisedAnnotation(cpd_name=annotation.cpd_name,
                                                         cpd_id=annotation.cpd_name,
                                                         assay_id=annotation.assay_id,
                                                         annotation_method_id=annotation.annotation_method_id)
            db_session.add(harmonised_annotation)
            db_session.flush()

        annotation.harmonised_annotation_id = harmonised_annotation.id

    db_session.flush()
    db_session.commit()
    db_session.close()