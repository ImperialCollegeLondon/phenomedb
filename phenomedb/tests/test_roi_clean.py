import pytest
from pathlib import Path
import sys
import os
import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.compounds import *
from phenomedb.config import config

class TestROIClean:
    """Test/apply ROI file cleaner
    """

    merged_file = config["DATA"]['compounds'] + 'roi_merged_names.xlsx'

    fields_to_replace = ['ChEBIID','InChIKey','chemspiderID','LmapsCategory','LmapsMainclass','LMapsSubclass','LMapsID','logPRDKit']
    replace_missing = True

    roi_dtypes = {
        'cpdID':str,
        'cpdName':str,
        'feature':pd.Int64Dtype(),
        'ion':str,
        'IonID':str,
        'rt':float,
        'rt_minutes':float,
        'mz':float,
        'mzMin':float,
        'mzMax':float,
        'rtMin':float,
        'rtMax':float,
        'Monoisotopic_mass':float,
        'chemicalFormula':str,
        'HMDBClass':str,
        'HMDBSubClass':str,
        'HMDBDirectParent':str,
        'HMDBID':str,
        'LmapsCategory':str,
        'LmapsMainclass':str,
        'LMapsSubclass':str,
        'LMapsID':str,
        'KEGGID':str,
        'chemspiderID':str,
        'PubChemID':str,
        'ChEBIID':str,
        'InChI':str,
        'InChIKey':str,
        'MSIAnnotationLevel':str,
        'logPRDKit':str}
    def test_hpos_roi_clean(self):

       assay_file = config["DATA"]['compounds'] + 'HPOS_ROI_V_3_1_0.csv'

       task = CleanROIFile(assay_name='HPOS',roi_file=assay_file,replace_missing=self.replace_missing,fields_to_replace=self.fields_to_replace)
       task.run()

    def test_rpos_roi_clean(self):

       assay_file = config["DATA"]['compounds'] + 'RPOS_ROI_V_3_1_0.csv'

       task = CleanROIFile(assay_name='RPOS',roi_file=assay_file,replace_missing=self.replace_missing,fields_to_replace=self.fields_to_replace)
       task.run()

    def test_rneg_roi_clean(self):

       assay_file = config["DATA"]['compounds'] + 'RNEG_ROI_V_3_1_0.csv'

       task = CleanROIFile(assay_name='RNEG',roi_file=assay_file,replace_missing=self.replace_missing,fields_to_replace=self.fields_to_replace)
       task.run()

#    def test_lneg_roi_clean(self):

#       assay_file = config["DATA"]['compounds'] + 'LNEG_ROI_V_5_1_0.csv'

#       task = CleanROIFile(assay_name='LNEG',roi_file=assay_file,roi_dtypes=self.roi_dtypes,replace_missing=self.replace_missing,fields_to_replace=self.fields_to_replace)
#       task.run()

#    def test_lpos_roi_clean(self):

#       assay_file = config["DATA"]['compounds'] + 'LPOS_ROI_V_5_1_0.csv'

#       task = CleanROIFile(assay_name='LPOS',roi_file=assay_file,roi_dtypes=self.roi_dtypes,replace_missing=self.replace_missing,fields_to_replace=self.fields_to_replace)
#       task.run()

   # def test_baneg_roi_clean(self):

   #    assay_file = config["DATA"]['compounds'] + 'BANEG_ROI_V_4_0_0.csv'

   #    task = CleanROIFile(assay_name='BANEG',roi_file=assay_file,replace_missing=True,merged_file=self.merged_file)
   #    task.run()