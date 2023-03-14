import unittest
from pathlib import Path
import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.compounds import *
from phenomedb.config import config

class TestCompounds():
    """Test Compound Parsers
    """

    input_file = config['DATA']['compounds'] + '/tmp/hmdb.xml'
    output_file = config['DATA']['compounds'] + '/tmp/hmdb.csv'

    def test_hmdb_parse(self):
        """Test ParseHMDBXMLtoCSV works as expected
        """        

        output_file = '/tmp/hmdb.csv'

        task = ParseHMDBXMLtoCSV(output_file_path=output_file,hmdb_type='sweat_metabolites')
        task.run()

        assert os.path.exists(output_file) == True

        if os.path.exists(output_file):
            os.remove(output_file)

        if os.path.exists('/tmp/sweat_metabolites.zip'):
            os.remove('/tmp/sweat_metabolites.zip')

        if os.path.exists('/tmp/sweat_metabolites.xml'):
            os.remove('/tmp/sweat_metabolites.xml')

    def test_kegg_parse(self):
        """Test ParseKEGGtoPubchemCIDTask works as expected
        """        

        output_file = '/tmp/kegg_parsed.csv'
        task = ParseKEGGtoPubchemCIDTask(output_file_path=output_file,compound_type='Glycosides',test=True)
        task.run()

        assert os.path.exists(output_file) == True

        if os.path.exists(output_file):
            os.remove(output_file)

    def test_compound_export(self):

        output_file = '/tmp/all_compounds.csv'
        task = ExportCompoundsToCSV(output_file_path=output_file,annotation_config_field='npcStandardID')
        task.run()

        output_file = '/tmp/test_compound_export.csv'
        methods = ["LC-QqQ Bile Acids-TargetLynx","LC-QqQ Amino Acids-TargetLynx","LC-QqQ Tryptophan-TargetLynx","LC-QqQ Oxylipins-TargetLynx"]
        task = ExportCompoundsToCSV(output_file_path=output_file,methods=methods)
        task.run()

        assert os.path.exists(output_file) == True

        if os.path.exists(output_file):
            os.remove(output_file)

        output_file = '/tmp/targetlynx_compounds.csv'
        methods = ["LC-QqQ Bile Acids-TargetLynx","LC-QqQ Amino Acids-TargetLynx","LC-QqQ Tryptophan-TargetLynx","LC-QqQ Oxylipins-TargetLynx"]

        task = ExportCompoundsToCSV(output_file_path=output_file,methods=methods)
        task.run()

        output_file = '/tmp/biquant_compounds.csv'
        methods = ["NOESY-BI-QUANT"]

        task = ExportCompoundsToCSV(output_file_path=output_file,methods=methods)
        task.run()


    def test_import_standards_v1(self,create_min_database,create_lab,create_ms_assays):

        standards_file = config['DATA']['compounds'] + "standards_v1.csv"

        task = ImportStandardsV1(standards_file=standards_file,db_env='PROD')
        task.run()

    def test_import_compounds(self):
                              #npc_setup,
                          #import_compounds):


        config_file = config['DATA']['config'] + "npc-setup.json"
        if not os.path.exists(config_file):
            raise Exception("NPC-setup source file missing %s" % config_file)

        with open(config_file) as json_file:
            npc_config = json.load(json_file)

        for args in npc_config['compounds']:
            task_class = args['task_class']
            del args['task_class']
            if 'roi_file' in args.keys():
                args['roi_file'] = config['DATA']['compounds'] + args['roi_file']
            elif 'bilisa_file' in args.keys():
                args['bilisa_file'] = config['DATA']['compounds'] + args['bilisa_file']
            elif 'biquant_compounds_file' in args.keys():
                args['biquant_compounds_file'] = config['DATA']['compounds'] + args['biquant_compounds_file']
            elif 'targetlynx_compounds_file' in args.keys():
                args['targetlynx_compounds_file'] = config['DATA']['compounds'] + args['targetlynx_compounds_file']

            #if task_class == 'ImportROICompounds':
                #task = ImportROICompounds(**args)
                #output = task.run()
                #assert 'validation_error' not in output
            if task_class == 'ImportBrukerBiQuantCompounds':
                task = ImportBrukerBiQuantCompounds(**args)
                output = task.run()
                assert 'validation_error' not in output
            elif task_class == 'ImportBrukerBiLISACompounds':
              #  task = ImportBrukerBiLISACompounds(**args)
              #  output = task.run()
                pass
              #  assert 'validation_error' not in output

    def test_import_missing_lipid_maps_classes(self):

        config_file = config['DATA']['config'] + "npc-setup.json"
        with open(config_file) as json_file:
            npc_config = json.load(json_file)

        for args in npc_config['compounds']:
            task_class = args['task_class']
            del args['task_class']
            if 'roi_file' in args.keys():
                args['roi_file'] = config['DATA']['compounds'] + args['roi_file']
            args['missing_lipid_classes'] = True
            if task_class == 'ImportROICompounds' and args['assay_name'] in ['LPOS','LNEG']:
                task = ImportROICompounds(**args)
                output = task.run()
                assert 'validation_error' not in output

        #args = {'standards_file': config['DATA']['compounds'] + npc_config["standards"]["v1_file"]}

    def test_find_missing_classyfire_classes(self):

        task = AddMissingClassyFireClasses()
        task.run()
        pass