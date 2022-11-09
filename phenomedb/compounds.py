import numpy as np
import pandas as pd
from phenomedb.models import *
from phenomedb.task import Task
import requests
import json
from pathlib import Path
from phenomedb.config import config
import urllib.parse as urlparse
import time
import re
import xml.etree.ElementTree as ET
import zipfile
import os
import datetime
from phenomedb.exceptions import ROICleanCheckFail
from rdkit import Chem
from rdkit.Chem import Crippen
from phenomedb.exceptions import ValidationError

class CompoundTask(Task):
    """The CompoundTask base class. Used for CompoundTasks. Loads the lookup files to be used as a reference, 
    and has methods for checking various databases (KEGG,HMDB,REFMET,CHEBI,LIPIDMAPS,PUBCHEM,CHEMBL,CAS)

    :param Task: The Task base class
    :type Task: `phenomedb.task.Task`
    :raises Exception: [description]
    :raises Exception: [description]
    :raises Exception: [description]
    :raises Exception: [description]
    :return: The CompoundTask class
    :rtype: `phenomedb.compound.CompoundTask`
    """    

    row_warnings = []
    chemspider_request_count = 0

    def __init__(self,**kwargs):
        """Constructor. Sets the paths to the various database files.
        """        

        super().__init__(**kwargs)

        self.lipid_maps_file = str((Path(config['DATA']['compounds']) / 'LMSD.csv').absolute())
        self.kegg_file = str((Path(config['DATA']['compounds']) / 'kegg_parsed.csv').absolute())
        self.hmdb_file = str((Path(config['DATA']['compounds']) / 'hmdb_parsed.csv').absolute())
        self.refmet_file = str((Path(config['DATA']['compounds']) / 'refmet.csv').absolute())
        self.chebi_file = str((Path(config['DATA']['compounds']) / 'chebi.csv').absolute())
        #self.ivdr_lipoprotein_file = str((Path(config['DATA']['compounds']) / 'ivdr_lipoproteins.csv').absolute())

        if self.db_session:
            self.pubchem_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'PubChem CID').first()
            self.pubchem_external_db_id = self.pubchem_external_db_id[0]
            self.kegg_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'KEGG').first()
            self.kegg_external_db_id = self.kegg_external_db_id[0]
            self.lipid_maps_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'LipidMAPS').first()
            self.lipid_maps_external_db_id = self.lipid_maps_external_db_id[0]
            self.chebi_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'ChEBI').first()
            self.chebi_external_db_id = self.chebi_external_db_id[0]
            self.hmdb_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'HMDB').first()
            self.hmdb_external_db_id = self.hmdb_external_db_id[0]
            self.chembl_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'ChEMBL').first()
            self.chembl_external_db_id = self.chembl_external_db_id[0]
            self.cas_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'CAS').first()
            self.cas_external_db_id = self.cas_external_db_id[0]
            self.refmet_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'Refmet').first()
            self.refmet_external_db_id = self.refmet_external_db_id[0]
            self.chemspider_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'ChemSpider').first()
            self.chemspider_external_db_id = self.chemspider_external_db_id[0]
            self.lipid_maps = self.load_tabular_file(self.lipid_maps_file, dtype=str)
            self.kegg = self.load_tabular_file(self.kegg_file, dtype=str)
            self.hmdb = self.load_tabular_file(self.hmdb_file, dtype=str)
            self.refmet = self.load_tabular_file(self.refmet_file,
                                                 dtype={'refmet_name': str, 'super_class': str, 'main_class': str,
                                                        'sub_class': str, 'formula': str, 'exactmass': float,
                                                        'inchi_key': str, 'smiles': str, 'pubchem_cid': str})
            self.chebi = self.load_tabular_file(self.chebi_file, dtype=str)
            self.compound_ids_set = True
        else:
            self.compound_ids_set = False

        self.update_names = False

        self.annotation_compound_counts = {}

    def process(self):
        """Process method. Loads the data and then maps it.
        """        

        self.load_data()
        self.loop_and_map_data()

    def load_data(self):
        """Load the databases + the ExternalDB.ids
        """        

        if not self.compound_ids_set:
            self.lipid_maps = self.load_tabular_file(self.lipid_maps_file, dtype=str)
            self.kegg = self.load_tabular_file(self.kegg_file, dtype=str)
            self.hmdb = self.load_tabular_file(self.hmdb_file, dtype=str)
            self.refmet = self.load_tabular_file(self.refmet_file,
                                                 dtype={'refmet_name': str, 'super_class': str, 'main_class': str,
                                                        'sub_class': str, 'formula': str, 'exactmass': float,
                                                        'inchi_key': str, 'smiles': str, 'pubchem_cid': str})
            self.chebi = self.load_tabular_file(self.chebi_file, dtype=str)
            self.pubchem_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'PubChem CID').first()
            self.pubchem_external_db_id = self.pubchem_external_db_id[0]
            self.kegg_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'KEGG').first()
            self.kegg_external_db_id = self.kegg_external_db_id[0]
            self.lipid_maps_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'LipidMAPS').first()
            self.lipid_maps_external_db_id = self.lipid_maps_external_db_id[0]
            self.chebi_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'ChEBI').first()
            self.chebi_external_db_id = self.chebi_external_db_id[0]
            self.hmdb_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'HMDB').first()
            self.hmdb_external_db_id = self.hmdb_external_db_id[0]
            self.chembl_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'ChEMBL').first()
            self.chembl_external_db_id = self.chembl_external_db_id[0]
            self.cas_external_db_id = self.db_session.query(ExternalDB.id).filter(ExternalDB.name == 'CAS').first()
            self.cas_external_db_id = self.cas_external_db_id[0]
            self.refmet_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'Refmet').first()
            self.refmet_external_db_id = self.refmet_external_db_id[0]
            self.chemspider_external_db_id = self.db_session.query(ExternalDB.id).filter(
                ExternalDB.name == 'ChemSpider').first()
            self.chemspider_external_db_id = self.chemspider_external_db_id[0]

    def find_chebi(self,inchi):
        """Find a ChEBI based on inchi. If there are multiple InChIs in the row, 

        :param inchi: The InChI to search
        :type inchi: str
        :return: ChEBI ID
        :rtype: str
        """        

        inchi = inchi.strip()
        try:
            chebi_row = np.where(self.chebi.loc[:,'InChI'] == inchi)[0][0]
            chebi_id = self.chebi.loc[chebi_row,"CHEBI_ID"]
        except Exception:
            chebi_id = None

        return chebi_id

    def get_inchi_key_from_pubchem_or_hmdb(self,inchi,hmdb_id):
        """Get an inchi_key from an InChI via Pubchem or HMDB_ID

        :param inchi: The InChI to find the inchi_key.
        :type inchi: str
        :param hmdb_id: The HMDBID
        :type hmdb_id: int
        :return: The InChI Key
        :rtype: str
        """        

        pubchem_data = self.get_from_pubchem_api('inchi',inchi)

        inchi_key = ''
        if pubchem_data and "PC_Compounds" in pubchem_data:

            pubchem_compound = pubchem_data["PC_Compounds"][0]

            if pubchem_compound['id']:
                inchi_key = self.get_pubchem_prop(pubchem_compound,'InChIKey','Standard')

        if inchi_key != '':
            return inchi_key

        else:
            if str(hmdb_id) != 'nan':
                try:
                    hmdb_row = np.where(self.hmdb.loc[:,'HMDB Primary ID'] == hmdb_id.strip())[0][0]
                    inchi_key = self.hmdb.loc[hmdb_row,"inchi_key"]
                except Exception:
                    inchi_key = ''

        return inchi_key

    def loop_and_map_data(self):
        """Override this method in your CompoundTasks
        """        
        pass

    def get_from_pubchem_api(self,lookup_field,lookup_value):
        """Get from pubchem by lookup_field and lookup_value

        :param lookup_field: The field to search with
        :type lookup_field: str
        :param lookup_value: The value to search with
        :type lookup_value: str
        :return: the found record
        :rtype: dict
        """        

        url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/' + lookup_field + '/JSON/'

        response = requests.get(url,params={lookup_field.lower():lookup_value.strip()})

        if response.status_code != 200:
            self.log_info("Pubchem API failed for %s" % lookup_value)
            self.log_info("url %s" % url)
            return None
        else:
            return json.loads(response.content.decode("utf-8","ignore"))

    def get_pubchem_view_from_api(self,pubchem_cid):
        """Get a pubchem view record (more info) by pubchem_cid

        :param pubchem_cid: The Pubchem CID
        :type pubchem_cid: int
        :return: The found record
        :rtype: dict
        """        

        try:

            url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/' + str(pubchem_cid) + '/JSON/'

            response = requests.get(url)

            if response.status_code != 200:
                self.row_warnings.append("Pubchem VIEW API failed for %s" % pubchem_cid)
                self.row_warnings.append("url %s" % url)
                return None
            else:
                return json.loads(response.content.decode("utf-8","ignore"))
        except Exception as err:
            self.row_warnings.append(str(err))
            return None


    def get_pubchem_prop(self,pubchem_compound,label,name=None):
        """Get a pubchem property based on it's label and name

        :param pubchem_compound: The pubchem record
        :type pubchem_compound: dict
        :param label: The label to search for
        :type label: str
        :param name: The name to search for, defaults to None
        :type name: str, optional
        :return: The property
        :rtype: object
        """        

        if pubchem_compound is None:
            return None

        value = None

        for prop in pubchem_compound['props']:
            if prop['urn']['label'] == label:
                if 'name' in prop['urn'] and name != None:
                    if prop['urn']['name'] == name:
                        value = self.parse_pubchem_value(prop['value'])
                else:
                    value = self.parse_pubchem_value(prop['value'])

        return value

    def parse_pubchem_value(self,value_dict):
        """Parse a pubchem value into it's defined type.

        :param value_dict: The value dict of the record.
        :type value_dict: dict
        :return: The converted typed value (str, int, or float)
        :rtype: object
        """        

        if 'sval' in value_dict:
            return str(value_dict['sval'])

        if 'ival' in value_dict:
            return int(value_dict['ival'])

        if 'fval' in value_dict:
            return float(value_dict['fval'])

    def add_or_update_pubchem_from_api(self,compound):
        """Add or update pubchem info for a Compound.
        Updates all the Compound properties including mass, chemical_formula, IUPAC and smiles.

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        :return: The matching pubchem CID
        :rtype: str
        """        

        pubchem_data = None
        pubchem_cid = None

        if compound.inchi_key:
            pubchem_data = self.get_from_pubchem_api('inchikey',compound.inchi_key)
        elif compound.inchi:
            pubchem_data = self.get_from_pubchem_api('inchi',compound.inchi)

        if pubchem_data and "PC_Compounds" in pubchem_data:

            pubchem_compound = pubchem_data["PC_Compounds"][0]

            if pubchem_compound['id']:
                pubchem_cid = str(pubchem_compound['id']['id']['cid'])

            inchi = self.get_pubchem_prop(pubchem_compound,'InChI','Standard')

            if inchi and not compound.inchi:
                compound.inchi = inchi
            elif inchi and compound.inchi != inchi:
                self.row_warnings.append('inchi from pubchem is different!')

            inchi_key = self.get_pubchem_prop(pubchem_compound,'InChIKey','Standard')
            if inchi_key and not compound.inchi_key:
                compound.inchi_key = inchi_key
                self.row_warnings.append('inchi_key set from pubchem')
            elif inchi_key and compound.inchi_key != inchi_key:
                self.row_warnings.append('inchi_key from pubchem is different!')

            smiles = self.get_pubchem_prop(pubchem_compound,'SMILES','Canonical')
            if smiles and not compound.smiles:
                compound.smiles = smiles
                self.row_warnings.append('smiles set from pubchem')
            elif smiles and compound.smiles != smiles:
                self.row_warnings.append('smiles from pubchem is different!')

            iupac = self.get_pubchem_prop(pubchem_compound,'IUPAC','Preferred')
            if iupac and not compound.iupac:
                compound.iupac = iupac
                self.row_warnings.append('iupac set from pubchem')
            elif iupac and compound.iupac != iupac:
                self.row_warnings.append('iupac from pubchem is different!')

            chemical_formula = self.get_pubchem_prop(pubchem_compound,'Molecular Formula')
            if chemical_formula and not compound.chemical_formula:
                compound.chemical_formula = chemical_formula
                self.row_warnings.append('chemical_formula set from pubchem')
            elif chemical_formula and compound.chemical_formula != chemical_formula:
                self.row_warnings.append('chemical_formula from pubchem is different!')

            monoisotopic_mass = self.get_pubchem_prop(pubchem_compound,'Weight','MonoIsotopic')
            if monoisotopic_mass and not compound.monoisotopic_mass:
                compound.monoisotopic_mass = monoisotopic_mass
                self.row_warnings.append('monoisotopic_mass set from pubchem')
            elif monoisotopic_mass and compound.monoisotopic_mass != monoisotopic_mass:
                self.row_warnings.append('monoisotopic_mass from pubchem is different!')

        if pubchem_cid:
            pubchem_entry = self.db_session.query(CompoundExternalDB) \
                .filter(CompoundExternalDB.compound_id==compound.id) \
                .filter(CompoundExternalDB.external_db_id==self.pubchem_external_db_id) \
                .filter(CompoundExternalDB.database_ref==pubchem_cid).first()

            if not pubchem_entry:
                pubchem_entry = CompoundExternalDB(compound_id=compound.id,
                                                   external_db_id=self.pubchem_external_db_id,
                                                   database_ref=pubchem_cid)
                self.db_session.add(pubchem_entry)
            else:
                pubchem_entry.database_ref = pubchem_cid

        self.db_session.flush()
        self.logger.info("Pubchem CID found: %s" % pubchem_cid)
        return pubchem_cid

    def get_from_chemspider_by_inchi(self,inchi):

        from chemspipy import ChemSpider
        cs = ChemSpider(config['API_KEYS']['chemspider'])
        csids = cs.filter_results(cs.filter_inchi(inchi))

        if len(csids) == 1:
            return csids

    def get_from_chemspider_by_inchi_key(self,inchi_key):

        from chemspipy import ChemSpider
        cs = ChemSpider(config['API_KEYS']['chemspider'])
        csids = cs.filter_results(cs.filter_inchikey(inchi_key))

        self.chemspider_request_count = self.chemspider_request_count + 1

        if len(csids) == 1:
            return csids[0]
        else:
            return None

    def add_chemspider_if_missing(self,compound):

        chemspider_entry = self.db_session.query(CompoundExternalDB) \
            .filter(CompoundExternalDB.compound_id == compound.id) \
            .filter(CompoundExternalDB.external_db_id == self.chemspider_external_db_id).first()

        if not chemspider_entry:
            chemspider_id = self.get_from_chemspider_by_inchi_key(compound.inchi_key)

            if chemspider_id:
                chemspider_entry = CompoundExternalDB(external_db_id=self.chemspider_external_db_id,
                                                 compound_id=compound.id,
                                                 database_ref=chemspider_id)
                self.db_session.add(chemspider_entry)
                self.db_session.flush()
        return chemspider_entry

    def add_or_update_chebi(self,compound):
        """Add or update chebi based on a Compound

        :param compound: Compound to add or update ChEBI for, defaults to None
        :type compound: `phenomedb.models.Compound`, optional
        :raises Exception: [description]
        :return: Found ChEBI id
        :rtype: str
        """

        try:
            chebi_row = np.where(self.chebi.loc[:,'InChI'] == compound.inchi)[0][0]
            chebi_id = self.chebi.loc[chebi_row,"CHEBI_ID"]
        except Exception:
            chebi_id = None

        chebi_entry = self.db_session.query(CompoundExternalDB) \
            .filter(CompoundExternalDB.compound_id==compound.id) \
            .filter(CompoundExternalDB.external_db_id==self.chebi_external_db_id).first()

        if chebi_id:
            if not chebi_entry:

                chebi_entry = CompoundExternalDB(compound_id=compound.id,
                                                 external_db_id=self.chebi_external_db_id,
                                                 database_ref=chebi_id)
                self.db_session.add(chebi_entry)
                self.row_warnings.append('ChEBI added')

            elif chebi_entry.database_ref != chebi_id:

                other_chebi_entry = self.db_session.query(CompoundExternalDB) \
                    .filter(CompoundExternalDB.compound_id==compound.id) \
                    .filter(CompoundExternalDB.external_db_id==self.chebi_external_db_id) \
                    .filter(CompoundExternalDB.database_ref==chebi_id).first()

                if not other_chebi_entry:
                    chebi_entry.database_ref = chebi_id
                    self.row_warnings.append('ChEBI updated')

        self.db_session.flush()

        return chebi_id


    def update_name_to_refmet(self,compound,lookup_field=None,lookup_value=None):
        """Updata the compound name to refmet. Optionally use a lookup_field. Defaults to Compound.inchi_key

        :param compound: The Compound to update the name for.
        :type compound: `phenomedb.models.Compound`
        :param lookup_field: The field to use for searching, defaults to None
        :type lookup_field: str, optional
        :param lookup_value: The value to use for searching, defaults to None
        :type lookup_value: str, optional
        :return: refmet_name
        :rtype: str
        """        

        if not lookup_field:
            lookup_field = 'inchi_key'

        if not lookup_value:
            lookup_value = compound.inchi_key

        try:
            refmet_row = np.where(self.refmet.loc[:,lookup_field] == lookup_value)[0][0]
            refmet_name = self.refmet.loc[refmet_row,"refmet_name"]
            super_class = self.refmet.loc[refmet_row,"super_class"]
            main_class = self.refmet.loc[refmet_row,"main_class"]
            sub_class = self.refmet.loc[refmet_row,"sub_class"]

            if str(sub_class).lower() == 'nan':
                sub_class = None

        except Exception:
            refmet_name = None

        # Updates the compound name to the refmet name
       # if refmet_name and compound.name != refmet_name:
       #     try:
       #         compound.name = refmet_name
       #         self.db_session.flush()
       #         self.row_warnings.append('Compound name updated to refmet name')
       #     except Exception as err:
       #         self.logger.exception(err)
       #         self.logger.info("Refmet name update failed - perhaps there is a name clash %s %s" % (compound,refmet_name))

        if refmet_name:

            refmet_entry = self.db_session.query(CompoundExternalDB).filter(CompoundExternalDB.external_db_id==self.refmet_external_db_id,
                                                                            CompoundExternalDB.compound_id==compound.id).first()

            if not refmet_entry and refmet_name:
                refmet_entry = CompoundExternalDB(external_db_id=self.refmet_external_db_id,
                                                  compound_id=compound.id,
                                                  database_ref=refmet_name)
                self.db_session.add(refmet_entry)
                self.db_session.flush()
                self.row_warnings.append('refmet entry added')

            if refmet_entry and refmet_entry.database_ref != refmet_name:

                other_refmet_entry = self.db_session.query(CompoundExternalDB).filter(CompoundExternalDB.external_db_id==self.refmet_external_db_id) \
                    .filter(CompoundExternalDB.compound_id==compound.id) \
                    .filter(CompoundExternalDB.database_ref==refmet_name).first()

                if not other_refmet_entry:
                    refmet_entry.database_ref = refmet_name
                    self.db_session.flush()
                    self.row_warnings.append('existing refmet entry updated')

            refmet_group = self.db_session.query(CompoundClass) \
                .filter(CompoundClass.sub_class==sub_class) \
                .filter(CompoundClass.type==CompoundClass.CompoundClassType.refmet) \
                .first()

            if not refmet_group:

                refmet_group = CompoundClass(name="",
                                             type = CompoundClass.CompoundClassType.refmet,
                                             category = super_class,
                                             main_class = main_class,
                                             sub_class = sub_class,
                                             )

                self.db_session.add(refmet_group)
                self.db_session.flush()

            compound_class_compound = self.db_session.query(CompoundClassCompound) \
                .filter(CompoundClassCompound.compound_class_id==refmet_group.id) \
                .filter(CompoundClassCompound.compound_id==compound.id) \
                .first()

            if not compound_class_compound:
                refmet_group_compound = CompoundClassCompound(compound_class_id=refmet_group.id,
                                                              compound_id=compound.id)
                self.db_session.add(refmet_group_compound)
                self.db_session.flush()

            self.logger.info("Refmet name found: %s" % refmet_name)

        return refmet_name


    def add_or_update_kegg(self,compound,pubchem_cid=None,kegg_id=None):
        """Add or update KEGG using pubchem_cid or kegg_id

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        :param pubchem_cid: The Pubchem CID to use for searching, defaults to None
        :type pubchem_cid: str, optional
        :param kegg_id: The KEGG ID to use for searching, defaults to None
        :type kegg_id: str, optional
        :return: kegg_id
        :rtype: str
        """        

        if not pubchem_cid and not kegg_id:
            self.row_warnings.append("KEGG lookup failed, no pubchem or kegg id")
            return None

        kegg_entry = self.db_session.query(CompoundExternalDB) \
            .filter(CompoundExternalDB.compound_id==compound.id) \
            .filter(CompoundExternalDB.external_db_id==self.kegg_external_db_id).first()

        kegg_row = None

        if not kegg_id and pubchem_cid:

            try:
                kegg_row = np.where(self.kegg.loc[:,'Pubchem CID'] == pubchem_cid)[0][0]
                kegg_id = self.kegg.loc[kegg_row,"KEGG"]
            except Exception:
                kegg_id = None

        if kegg_id:
            if not kegg_entry:

                kegg_entry = CompoundExternalDB(compound_id=compound.id,
                                                external_db_id=self.kegg_external_db_id,
                                                database_ref=kegg_id)
                self.db_session.add(kegg_entry)
                self.db_session.flush()
                self.row_warnings.append('kegg entry added')

            elif kegg_entry.database_ref != kegg_id:

                other_kegg_entry = self.db_session.query(CompoundExternalDB) \
                    .filter(CompoundExternalDB.compound_id==compound.id) \
                    .filter(CompoundExternalDB.external_db_id==self.kegg_external_db_id) \
                    .filter(CompoundExternalDB.database_ref==kegg_id).first()

                if not other_kegg_entry:
                    kegg_entry.database_ref = kegg_id
                    self.db_session.flush()
                    self.row_warnings.append('kegg entry updated')

        self.logger.info("kegg_id found: %s" % kegg_id)

        return kegg_id

    def add_or_update_hmdb(self,compound,lookup_field=None,lookup_value=None):
        """Add or update HMDB ID + Groups using Compound.inchi_key or a lookup field

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        :param lookup_field: The search field, defaults to None
        :type lookup_field: str, optional
        :param lookup_value: The search value, defaults to None
        :type lookup_value: str, optional
        :return: HMDB ID
        :rtype: str
        """        

        if not lookup_field:
            lookup_field = 'inchi_key'

        if not lookup_value:
            lookup_value = compound.inchi_key

        hmdb_entry = self.db_session.query(CompoundExternalDB) \
            .filter(CompoundExternalDB.compound_id==compound.id) \
            .filter(CompoundExternalDB.external_db_id==self.hmdb_external_db_id).first()

        hmdb_row = None
        hmdb_id = None
        kingdom = None
        category = None
        main_class = None
        sub_class = None
        direct_parent = None

        try:
            hmdb_row = np.where(self.hmdb.loc[:,lookup_field] == lookup_value)[0][0]
            hmdb_id = self.hmdb.loc[hmdb_row,"HMDB Primary ID"]
            kingdom = self.hmdb.loc[hmdb_row,"kingdom"]
            category = self.hmdb.loc[hmdb_row,"super_class"]
            main_class = self.hmdb.loc[hmdb_row,"class"]
            sub_class = self.hmdb.loc[hmdb_row,"sub_class"]
            direct_parent = self.hmdb.loc[hmdb_row,"direct_parent"]

        except Exception:
            hmdb_id = None

        if hmdb_id:
            if not hmdb_entry:

                hmdb_entry = CompoundExternalDB(compound_id=compound.id,
                                                external_db_id=self.hmdb_external_db_id,
                                                database_ref=hmdb_id)
                self.db_session.add(hmdb_entry)
                self.db_session.flush()
                self.row_warnings.append('HMDB entry added')

            elif hmdb_entry.database_ref != hmdb_id:

                other_hmdb_entry = self.db_session.query(CompoundExternalDB) \
                    .filter(CompoundExternalDB.compound_id==compound.id) \
                    .filter(CompoundExternalDB.external_db_id==self.hmdb_external_db_id) \
                    .filter(CompoundExternalDB.database_ref==hmdb_id).first()

                if not other_hmdb_entry:
                    hmdb_entry.database_ref = hmdb_id
                    self.db_session.flush()
                    self.row_warnings.append('HMDB entry updated')

            hmdb_class = self.db_session.query(CompoundClass) \
                .filter(CompoundClass.kingdom==kingdom) \
                .filter(CompoundClass.category==category) \
                .filter(CompoundClass.main_class==main_class) \
                .filter(CompoundClass.sub_class==sub_class) \
                .filter(CompoundClass.direct_parent==direct_parent) \
                .filter(CompoundClass.type==CompoundClass.CompoundClassType.hmdb) \
                .first()

            if not hmdb_class:

                hmdb_class = CompoundClass(name="",
                                           type = CompoundClass.CompoundClassType.hmdb,
                                           kingdom=kingdom,
                                           category = category,
                                           main_class = main_class,
                                           sub_class = sub_class,
                                           direct_parent= direct_parent,
                                           )

                self.db_session.add(hmdb_class)
                self.db_session.flush()

            compound_class_compound = self.db_session.query(CompoundClassCompound) \
                .filter(CompoundClassCompound.compound_class_id==hmdb_class.id) \
                .filter(CompoundClassCompound.compound_id==compound.id) \
                .first()

            if not compound_class_compound:
                hmdb_group_compound = CompoundClassCompound(compound_class_id=hmdb_class.id,
                                                            compound_id=compound.id)
                self.db_session.add(hmdb_group_compound)
                self.db_session.flush()

        self.logger.info("hmdb_id found: %s" % hmdb_id)

        return hmdb_id

    def add_or_update_lipid_maps(self,compound,lookup_field=None,lookup_value=None):
        """Add or update LipidMAPS IDs and Groups.

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        :param lookup_field: The search field to use, defaults to None
        :type lookup_field: str, optional
        :param lookup_value: The search value, defaults to None
        :type lookup_value: str, optional
        :return: LipidMAPs ID
        :rtype: str
        """        

        if not lookup_field:
            lookup_field = 'inchi_key'

        if not lookup_value:
            lookup_value = compound.inchi_key

        lipid_maps_entry = self.db_session.query(CompoundExternalDB) \
            .filter(CompoundExternalDB.compound_id==compound.id) \
            .filter(CompoundExternalDB.external_db_id==self.lipid_maps_external_db_id).first()

        lm_row = None
        lm_id = None

        try:
            lm_row = np.where(self.lipid_maps.loc[:,lookup_field] == lookup_value)[0][0]
            lm_id = self.lipid_maps.loc[lm_row,"regno"]
            category = self.lipid_maps.loc[lm_row,"core"]
            main_class = self.lipid_maps.loc[lm_row,"main_class"]
            sub_class = self.lipid_maps.loc[lm_row,"sub_class"]
            direct_parent = self.lipid_maps.loc[lm_row,"class_level4"]

            if str(category).lower() == 'nan':
                category = None

            if str(main_class).lower() == 'nan':
                main_class = None

            if str(sub_class).lower() == 'nan':
                sub_class = None

            if str(direct_parent).lower() == 'nan':
                direct_parent = None


        except Exception:
            lm_id = None
            lm_row = None

        if lm_id:
            if not lipid_maps_entry:

                lipid_maps_entry = CompoundExternalDB(compound_id=compound.id,
                                                      external_db_id=self.lipid_maps_external_db_id,
                                                      database_ref=lm_id)
                self.db_session.add(lipid_maps_entry)
                self.db_session.flush()
                self.logger.info("LipidMAPS added: %s" % lm_id)

            elif lipid_maps_entry.database_ref != lm_id:

                other_lipid_maps_entry = self.db_session.query(CompoundExternalDB) \
                    .filter(CompoundExternalDB.compound_id==compound.id) \
                    .filter(CompoundExternalDB.external_db_id==self.lipid_maps_external_db_id) \
                    .filter(CompoundExternalDB.database_ref==lm_id).first()

                if not other_lipid_maps_entry:
                    lipid_maps_entry.database_ref = lm_id
                    self.db_session.flush()
                    self.logger.info("LipidMAPS updated: %s" % lm_id)



            lipidmaps_group = self.db_session.query(CompoundClass) \
                .filter(CompoundClass.category==category) \
                .filter(CompoundClass.main_class==main_class) \
                .filter(CompoundClass.sub_class==sub_class) \
                .filter(CompoundClass.direct_parent==direct_parent) \
                .filter(CompoundClass.type==CompoundClass.CompoundClassType.lipidmaps) \
                .first()

            if not lipidmaps_group:

                lipidmaps_group = CompoundClass(name="",
                                                type = CompoundClass.CompoundClassType.lipidmaps,
                                                category = category,
                                                main_class = main_class,
                                                sub_class = sub_class,
                                                direct_parent = direct_parent
                                                )

                self.db_session.add(lipidmaps_group)
                self.db_session.flush()

            compound_class_compound = self.db_session.query(CompoundClassCompound) \
                .filter(CompoundClassCompound.compound_class_id==lipidmaps_group.id) \
                .filter(CompoundClassCompound.compound_id==compound.id) \
                .first()

            if not compound_class_compound:
                compound_class_compound = CompoundClassCompound(compound_class_id=lipidmaps_group.id,
                                                                compound_id=compound.id)
                self.db_session.add(compound_class_compound)
                self.db_session.flush()

            # Add ontology here

            ontology_source = self.db_session.query(OntologySource).filter(OntologySource.name=='LipidMAPS class').first()

            if not ontology_source:
                ontology_source = OntologySource(name='LipidMAPS class',
                                                 description='LipidMAPS class lookup',
                                                 url='https://www.lipidmaps.org/data/structure/LMSDSearch.php?Mode=ProcessClassSearch&LMID=')
                self.db_session.add(ontology_source)
                self.db_session.flush()

            # Repeat for other ontologies including LMID -> compound_external_db_id
            if category:
                self.add_or_update_ontology_ref(ontology_source,self.get_lipid_maps_reference(category),'compound_class_category_id',lipidmaps_group.id)
            if main_class:
                self.add_or_update_ontology_ref(ontology_source,self.get_lipid_maps_reference(main_class),'compound_class_main_class_id',lipidmaps_group.id)
            if sub_class:
                self.add_or_update_ontology_ref(ontology_source,self.get_lipid_maps_reference(sub_class),'compound_class_sub_class_id',lipidmaps_group.id)
            if direct_parent:
                self.add_or_update_ontology_ref(ontology_source,self.get_lipid_maps_reference(direct_parent),'compound_class_direct_parent_id',lipidmaps_group.id)


        self.logger.info("lipid_maps id found: %s" % lm_id)

        return lm_id

    def add_or_update_ontology_ref(self,ontology_source,accession_number,field,model_id):
        """Add or update an ontology ref

        :param ontology_source: The OntologySource
        :type ontology_source: `phenomedb.models.OntologySource`
        :param accession_number: The accession number for the ontology
        :type accession_number: str
        :param field: The model field to map the ontology to
        :type field: str
        :param model_id: The ID of the mapped model
        :type model_id: int
        """        

        evaluated_field = eval('OntologyRef.' + field)

        ontology_ref = self.db_session.query(OntologyRef).filter(OntologyRef.ontology_source_id==ontology_source.id,
                                                                 evaluated_field==model_id).first()

        if not ontology_ref:
            ontology_ref = OntologyRef(ontology_source_id=ontology_source.id,
                                       accession_number=accession_number)
            setattr(ontology_ref,field,model_id)
            self.db_session.add(ontology_ref)
            self.db_session.flush()

        else:
            ontology_ref.accession_number = accession_number
            self.db_session.flush()


    def get_lipid_maps_reference(self,value):
        """Get the lipid maps ontology reference from the ID

        :param value: The LipidMAPS ID to strip the ontology reference from
        :type value: str
        :return: The LipidMAPS ontology reference
        :rtype: str
        """        
        try:
            splitted = value.strip().split('[')
            return splitted[1].strip().replace(']','')
        except Exception as err:
            self.logger.exception(err)
            return None

    def get_classyfire_reference(self,value):
        """Get the Classyfire ontology reference

        :param value: The Classyfire ID to get the reference from
        :type value: str
        :return: The Classyfire ontology reference
        :rtype: str
        """        

        try:
            splitted = value.strip().split(':')
            return "C" + splitted[1]
        except Exception as err:
            self.logger.exception(err)
            return None

    def add_or_update_chembl(self,compound):
        """Add of update ChEMBL for compound

        :param compound: Compound to update
        :type compound: `phenomedb.models.Compound`
        :return: ChEMBL ID
        :rtype: str
        """

        chembl_id = None
        if compound.inchi_key:

            url = "https://www.ebi.ac.uk/chembl/api/data/molecule/" + compound.inchi_key + "/?format=json"

            response = requests.get(url)

            if response.status_code != 200:
                return None

            chembl_data = json.loads(response.content.decode("utf-8","ignore"))

            if 'molecule_chembl_id' in chembl_data:
                chembl_id = chembl_data['molecule_chembl_id']

            chembl_entry = self.db_session.query(CompoundExternalDB) \
                .filter(CompoundExternalDB.compound_id==compound.id) \
                .filter(CompoundExternalDB.external_db_id==self.chembl_external_db_id).first()

            if chembl_id:
                if not chembl_entry:

                    chembl_entry = CompoundExternalDB(compound_id=compound.id,
                                                      external_db_id=self.chembl_external_db_id,
                                                      database_ref=chembl_id)
                    self.db_session.add(chembl_entry)
                    self.db_session.flush()
                    self.logger.info("chembl updated: %s" % chembl_id)

                elif chembl_entry.database_ref != chembl_id:

                    other_chembl_entry = self.db_session.query(CompoundExternalDB) \
                        .filter(CompoundExternalDB.compound_id==compound.id) \
                        .filter(CompoundExternalDB.external_db_id==self.chembl_external_db_id) \
                        .filter(CompoundExternalDB.database_ref==chembl_id).first()
                    if not other_chembl_entry:
                        chembl_entry.database_ref = chembl_id
                        self.db_session.flush()
                        self.logger.info("chembl updated: %s" % chembl_id)

        return chembl_id

    def add_cas_from_hmdb(self,compound,lookup_field=None,lookup_value=None):
        """Add CAS from HMDB for a Compound. Uses Compound.inchi_key by default

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        :param lookup_field: The search field, defaults to None
        :type lookup_field: str, optional
        :param lookup_value: The search value, defaults to None
        :type lookup_value: str, optional
        :return: CAS
        :rtype: str
        """        

        if not lookup_field:
            lookup_field = 'inchi_key'

        if not lookup_value:
            lookup_value = compound.inchi_key

        cas_entry = self.db_session.query(CompoundExternalDB) \
            .filter(CompoundExternalDB.compound_id==compound.id) \
            .filter(CompoundExternalDB.external_db_id==self.cas_external_db_id).first()

        if not cas_entry:

            hmdb_row = None
            cas_id = None

            try:
                hmdb_row = np.where(self.hmdb.loc[:,lookup_field] == lookup_value)[0][0]
                cas_id = self.hmdb.loc[hmdb_row,"cas_registry_number"]

            except Exception:
                cas_id = None

            if cas_id:

                cas_entry = CompoundExternalDB(compound_id=compound.id,
                                               external_db_id=self.cas_external_db_id,
                                               database_ref=cas_id)
                self.db_session.add(cas_entry)
                self.db_session.flush()
                self.logger.info("cas added: %s" % cas_id)

        else:

            cas_id = cas_entry.database_ref
            self.logger.info("cas updated: %s" % cas_id)

        self.logger.info("cas found: %s" % cas_id)

        return cas_id

    def get_or_add_compound_external_db(self,compound,external_db_name,database_ref):
        """Get or add CompoundExternalDB.

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        :param external_db_name: The name of the db to update
        :type external_db_name: str
        :param database_ref: The database ref to add
        :type database_ref: str
        """        

        database_ref = str(database_ref).strip()

        external_db = self.db_session.query(ExternalDB).filter(ExternalDB.name==external_db_name).first()

        compound_external_db = self.db_session.query(CompoundExternalDB).filter(CompoundExternalDB.external_db_id==external_db.id,
                                                                                CompoundExternalDB.compound_id==compound.id)
        if not compound_external_db:
            compound_external_db = CompoundExternalDB(external_db_id=external_db.id,
                                                      compound_id=compound.id,
                                                      database_ref=database_ref)
            self.db_session.add(compound_external_db)
            self.db_session.flush()

    def update_annotation(self,cpd_name,feature_dict,version):
        """Update a compound annotation with the config to store. Used for adding the ion types from a ROI row

        :param cpd_name: The name of the annotated compound
        :type cpd_name: str
        :param feature_dict: The config dictionary
        :type feature_dict: dict
        :param version: The version of the Annotation
        :type version: str
        """        
        # Updates the caf once the remaining cpd_rows have been processed (adding the other ion types)

        # get the annotation by cpd_name and assay and annotation_method

        annotation = self.db_session.query(Annotation) \
            .filter(Annotation.assay_id==self.assay.id,
                    Annotation.cpd_name==cpd_name,
                    Annotation.annotation_method_id==self.annotation_method.id,
                    Annotation.version==version).first()

        if annotation:
            annotation.config = feature_dict
        else:
            self.log_info("no Annotation matching %s" % cpd_name)
        self.db_session.flush()

    def add_stereo_group(self,compound):
        """Add the stereo group for the compound

        :param compound: The compound to add
        :type compound: `phenomedb.models.Compound`
        """        

        if not compound.inchi_key or compound.inchi_key == 'Unknown':
            return

        inchi_key_backbone = compound.get_inchi_key_backbone()

        # Adding the stereo group (inchi_key_backbone)
        stereo_group = self.db_session.query(CompoundClass) \
            .filter(CompoundClass.inchi_key_backbone==inchi_key_backbone) \
            .filter(CompoundClass.type==CompoundClass.CompoundClassType.isomer.value) \
            .first()

        if not stereo_group:
            stereo_group = CompoundClass(name="",
                                         inchi_key_backbone=inchi_key_backbone,
                                         type=CompoundClass.CompoundClassType.isomer.value)
            self.db_session.add(stereo_group)
            self.db_session.flush()

        compound_class_compound = self.db_session.query(CompoundClassCompound) \
            .filter(CompoundClassCompound.compound_class_id==stereo_group.id) \
            .filter(CompoundClassCompound.compound_id==compound.id) \
            .first()

        if not compound_class_compound:
            stereo_group_compound = CompoundClassCompound(compound_class_id=stereo_group.id,
                                                          compound_id=compound.id)
            self.db_session.add(stereo_group_compound)
            self.db_session.flush()

    def add_or_update_classyfire(self,compound):
        """Add or update the Classyfire references and classes

        :param compound: The Compound to update
        :type compound: `phenomedb.models.Compound`
        """        

        classyfire = self.get_from_classyfire(compound.inchi_key)

        if classyfire:
            if 'kingdom' in classyfire and classyfire['kingdom'] and 'name' in classyfire['kingdom']:
                kingdom = classyfire['kingdom']['name']
            else:
                kingdom = None
            if 'superclass' in classyfire and classyfire['superclass'] and 'name' in classyfire['superclass']:
                super_class = classyfire['superclass']['name']
            else:
                super_class = None
            if 'class' in classyfire and classyfire['class'] and 'name' in classyfire['class']:
                main_class = classyfire['class']['name']
            else:
                main_class = None
            if 'subclass' in classyfire and classyfire['subclass'] and 'name' in classyfire['subclass']:
                sub_class = classyfire['subclass']['name']
            else:
                sub_class = None
            if 'direct_parent' in classyfire and classyfire['direct_parent'] and 'name' in classyfire['direct_parent']:
                direct_parent = classyfire['direct_parent']['name']
            else:
                direct_parent = None

            classyfire_group = self.db_session.query(CompoundClass) \
                .filter(CompoundClass.kingdom==kingdom) \
                .filter(CompoundClass.category==super_class) \
                .filter(CompoundClass.main_class==main_class) \
                .filter(CompoundClass.sub_class==sub_class) \
                .filter(CompoundClass.direct_parent==direct_parent) \
                .filter(CompoundClass.intermediate_nodes==classyfire['intermediate_nodes']) \
                .filter(CompoundClass.alternative_parents==classyfire['alternative_parents']) \
                .filter(CompoundClass.molecular_framework==classyfire['molecular_framework']) \
                .filter(CompoundClass.substituents==classyfire['substituents']) \
                .filter(CompoundClass.ancestors==classyfire['ancestors']) \
                .filter(CompoundClass.type==CompoundClass.CompoundClassType.classyfire) \
                .first()

            if not classyfire_group:

                classyfire_group = CompoundClass(name="",
                                                 type = CompoundClass.CompoundClassType.classyfire,
                                                 kingdom=kingdom,
                                                 category=super_class,
                                                 main_class=main_class,
                                                 sub_class=sub_class,
                                                 direct_parent=direct_parent,
                                                 intermediate_nodes=classyfire['intermediate_nodes'],
                                                 alternative_parents=classyfire['alternative_parents'],
                                                 molecular_framework=classyfire['molecular_framework'],
                                                 substituents=classyfire['substituents'],
                                                 ancestors=classyfire['ancestors']
                                                 )

                self.db_session.add(classyfire_group)
                self.db_session.flush()

            compound_class_compound = self.db_session.query(CompoundClassCompound) \
                .filter(CompoundClassCompound.compound_class_id==classyfire_group.id) \
                .filter(CompoundClassCompound.compound_id==compound.id) \
                .first()

            if not compound_class_compound:
                compound_class_compound = CompoundClassCompound(compound_class_id=classyfire_group.id,
                                                                compound_id=compound.id)
                self.db_session.add(compound_class_compound)
                self.db_session.flush()

            # Add ontology here

            ontology_source = self.db_session.query(OntologySource).filter(OntologySource.name=='LipidMAPS class').first()

            if not ontology_source:
                ontology_source = OntologySource(name='LipidMAPS class',
                                                 description='LipidMAPS class lookup',
                                                 url='https://www.lipidmaps.org/data/structure/LMSDSearch.php?Mode=ProcessClassSearch&LMID=')
                self.db_session.add(ontology_source)
                self.db_session.flush()

            # Repeat for other ontologies including LMID -> compound_external_db_id
            if kingdom:
                self.add_or_update_ontology_ref(ontology_source,self.get_classyfire_reference(classyfire['kingdom']['chemont_id']),'compound_class_kingdom_id',classyfire_group.id)
            if super_class:
                self.add_or_update_ontology_ref(ontology_source,self.get_classyfire_reference(classyfire['superclass']['chemont_id']),'compound_class_category_id',classyfire_group.id)
            if main_class:
                self.add_or_update_ontology_ref(ontology_source,self.get_classyfire_reference(classyfire['class']['chemont_id']),'compound_class_main_class_id',classyfire_group.id)
            if sub_class:
                self.add_or_update_ontology_ref(ontology_source,self.get_classyfire_reference(classyfire['subclass']['chemont_id']),'compound_class_sub_class_id',classyfire_group.id)
            if direct_parent:
                self.add_or_update_ontology_ref(ontology_source,self.get_classyfire_reference(classyfire['direct_parent']['chemont_id']),'compound_class_direct_parent_id',classyfire_group.id)

    def get_from_pubchem(self,inchi_key):
        """Get from pubchem by inchi_key

        :param inchi_key: The inchi_key to search by
        :type inchi_key: str
        :return: The pubchem result
        :rtype: dict
        """        

        pubchem_result = self.get_from_pubchem_api('inchikey',inchi_key)

        if pubchem_result and "PC_Compounds" in pubchem_result:

            pubchem_compound = pubchem_result["PC_Compounds"][0]

            if pubchem_compound['id']:
                pubchem_data = {}
                pubchem_data['pubchem_cid'] = str(pubchem_compound['id']['id']['cid'])

                pubchem_data['inchi'] = self.get_pubchem_prop(pubchem_compound,'InChI','Standard')
                pubchem_data['inchi_key'] = self.get_pubchem_prop(pubchem_compound,'InChIKey','Standard')
                pubchem_data['smiles'] = self.get_pubchem_prop(pubchem_compound,'SMILES','Canonical')
                pubchem_data['iupac'] = self.get_pubchem_prop(pubchem_compound,'IUPAC','Preferred')
                pubchem_data['chemical_formula'] = self.get_pubchem_prop(pubchem_compound,'Molecular Formula')
                pubchem_data['monoisotopic_mass'] = self.get_pubchem_prop(pubchem_compound,'Weight','MonoIsotopic')
                return pubchem_data
        else:
            return None

    def get_cas_from_pubchem(self,pubchem_data):
        """Get CAS from pubchem

        :param pubchem_data: The pubchem record
        :type pubchem_data: dict
        :return: The pubchem record
        :rtype: dict
        """        

        pubchem_result = self.get_pubchem_view_from_api(pubchem_data['pubchem_cid'])

        cas_entries = []

        if pubchem_result and "Record" in pubchem_result:

            try:
                for section in pubchem_result['Record']['Section']:
                    if section['TOCHeading'] == 'Names and Identifiers':
                        for names_and_identifier_section in section['Section']:
                            if names_and_identifier_section['TOCHeading'] == 'Other Identifiers':
                                for other_identifer_section in names_and_identifier_section['Section']:
                                    if other_identifer_section['TOCHeading'] == 'CAS':
                                        for information in other_identifer_section['Information']:
                                            cas_entries.append(information['Value']['StringWithMarkup'][0]['String'])
                                        break
            except:
                self.row_warnings.append("CAS not found in pubchem")

        else:
            self.row_warnings.append("Pubchem not found")

        pubchem_data['cas_entries'] = cas_entries

        return pubchem_data


    def get_from_chebi(self,inchi):
        """Get from ChEBI by inchi

        :param inchi: The InChI
        :type inchi: str
        :return: The ChEBI ID
        :rtype: str
        """        
        try:
            chebi_row = np.where(self.chebi.loc[:,'InChI'] ==inchi)[0][0]
            chebi_id = self.chebi.loc[chebi_row,"CHEBI_ID"]
        except Exception:
            chebi_id = None

        return chebi_id

    def get_from_chembl(self,inchi_key):
        """Get from ChEMBL by inchi_key

        :param inchi_key: The InChI Key
        :type inchi_key: str
        :return: ChEMBL ID
        :rtype: str
        """        

        try:

            url = "https://www.ebi.ac.uk/chembl/api/data/molecule/" + inchi_key + "/?format=json"

            response = requests.get(url)

            if response.status_code != 200:
                return None
            else:
                return json.loads(response.content.decode("utf-8","ignore"))

        except Exception as err:

            self.row_warnings.append(str(err))

            return None


    def get_from_kegg(self,pubchem_cid):
        """Get from Kegg

        :param pubchem_cid: The Pubchem CID
        :type pubchem_cid: int
        :return: kegg id
        :rtype: str
        """        

        try:
            kegg_row = np.where(self.kegg.loc[:,'Pubchem CID'] == pubchem_cid)[0][0]
            kegg_id = self.kegg.loc[kegg_row,"KEGG"]
        except Exception:
            kegg_id = None

        return kegg_id

    def get_from_hmdb(self,inchi_key):
        """Get from HMDB row by inchi_key

        :param inchi_key: The InChI key to search by
        :type inchi_key: str
        :return: The HMDB dataset row number
        :rtype: int
        """        

        try:
            hmdb_row = np.where(self.hmdb.loc[:,'inchi_key'] == inchi_key)[0][0]
        except Exception:
            hmdb_row = None
        return hmdb_row

    def get_from_refmet(self,subrow,inchi_key=None):
        """Get from refmet by subrow or inchi_key

        :param subrow: The row of the ROI file 
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key, defaults to None
        :type inchi_key: str, optional
        :return: The row number of the refmet database
        :rtype: int
        """        

        refmet_row = None

        if inchi_key:
            try:
                refmet_row = np.where(self.refmet.loc[:,'inchi_key'] == inchi_key)[0][0]
            except Exception:
                refmet_row = None
        else:

            refmet_rows = self.refmet[(self.refmet.loc[:,'formula'] == subrow['chemicalFormula']) \
                                   & (self.refmet.loc[:,'exactmass'] >= utils.round_decimals_up(subrow['Monoisotopic_mass'],4))
                                   & (self.refmet.loc[:,'exactmass'] <= utils.round_decimals_down(subrow['Monoisotopic_mass'],4))]
            if len(refmet_rows) == 1:
                refmet_row = refmet_rows[0][0]
            elif len(refmet_rows) > 1:
                self.logger.info('multiple refmet rows matched %s %s' % (subrow['chemicalFormula'], subrow['Monoisotopic_mass']))
            else:
                self.logger.info('no refmet rows matched %s %s' % (subrow['chemicalFormula'], subrow['Monoisotopic_mass']))
                refmet_row = None

        return refmet_row

    def get_from_lipidmaps(self,inchi_key):
        """Get from lipidmaps by inchi_key

        :param inchi_key: The InChI Key to search by
        :type inchi_key: str
        :return: The row number from lipidmaps dataset
        :rtype: int
        """        

        try:
            lm_row = np.where(self.lipid_maps.loc[:,'inchi_key'] == inchi_key)[0][0]
        except:
            lm_row = None

        return lm_row

    def get_from_classyfire(self,inchi_key):
        """Get content from classyfire

        :param inchi_key: InChI key to search with
        :type inchi_key: str
        :return: data from classyfire
        :rtype: dict
        """        

        try:
            r = requests.get("http://classyfire.wishartlab.com/entities/%s.json" % inchi_key,
                            headers={"Content-Type":"application/json"})

            if r.status_code != 200:
                self.logger.info("CLASSYFIRE failed %s" % r.content)
                return None

            else:
                return json.loads(r.content.decode("utf-8","ignore"))
        except Exception as err:
            self.logger.exception(err)
            return None

    def generate_inchi_key(self,inchi):
        """Generate inchi_key using RDKit

        :param inchi: InChI for compound
        :type inchi: str
        :return: InChI key for compound
        :rtype: str
        """      
        try:  
            my_chem = Chem.MolFromInchi(inchi)
            return Chem.inchi.MolToInchiKey(my_chem)
        except Exception as err:
            self.logger.exception(err)
            return None

    def calculate_log_p(self,inchi):
        """Calculate logP using RDKit

        :param inchi: InCHI for compound
        :type inchi: str
        :return: logP
        :rtype: float
        """        
        try:
            my_chem = Chem.MolFromInchi(inchi)
            return Crippen.MolLogP(my_chem,includeHs=False)
        except Exception as err:
            self.logger.exception(err)
            return None

    def build_subrows(self,row):
        """Take a row from an ROI file and create sub row, where each sub row contains the info for 1 compound. Required because ROI files can contain 'Annotation' information that maps to multiple 'Compounds' (ie unique InChIs)

        :param row: The row to split into multiple rows.
        :type row: `pandas.Series`
        """

        multi_columns = []
        subrows = {}

        if re.search('and\/or', row['cpdName']):
            cpd_name_splitter = ' and/or '
        elif re.search('\|',row['cpdName']):
            cpd_name_splitter = ' | '
        else:
            cpd_name_splitter = None

        if not cpd_name_splitter:
            subrows[row['cpdName']] = row.copy()

        else:
            cpd_names = row['cpdName'].split(cpd_name_splitter)
            i = 0
            for cpd_name in cpd_names:
                further_splitter = None
                if re.search('\|',cpd_name):
                    further_splitter = " | "
                elif re.search('\;', cpd_name):
                    further_splitter = ";"
                if further_splitter:
                    further_split = cpd_name.split(further_splitter)
                    if len(further_split) == 1:
                        cpd_name = further_split[0].strip()
                    elif len(further_split) == 2:
                        cpd_name = further_split[1].strip()

                cpd_names[i] = cpd_name
                subrows[cpd_name] = row.copy()
                i = i + 1

            for column, type in self.roi_dtypes.items():

                if column in row:

                    # if it has a |, then split them into sub entries
                    if type == str and row[column] is not None and re.search('\|',row[column]):
                        sub_entries = row[column].split(' | ')

                        multi_columns.append(column)

                    # Otherwise, just use the whole cell value
                    else:
                        sub_entries = [row[column]]

                    # construct the sub rows
                    i = 0
                    while i < len(cpd_names):
                        cpd_name = cpd_names[i]
                        if column in multi_columns and len(sub_entries) > i:
                            subrows[cpd_name][column] = sub_entries[i]
                        else:
                            subrows[cpd_name][column] = sub_entries[0]
                            break
                        i = i + 1

        self.annotation_compound_counts[row['cpdName']] = len(subrows)

        return subrows, multi_columns

class CleanROIFile(CompoundTask):
    """Clean an ROI file. Takes ROI file, checks IDs from source, adds missing fields, writes out to log file

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    :raises Exception: [description]
    :raises ROICleanCheckFail: [description]
    :raises ROICleanCheckFail: [description]
    :raises ROICleanCheckFail: [description]
    :raises ROICleanCheckFail: [description]
    
    """    
    
    roi_dtypes = {'cpdID':str,'cpdName':str,'feature':pd.Int64Dtype(),'ion':str,'purpose':str,'IonID':str,'Commentsformanualrevision':str,'rt':float,'rt_minutes':float,
                  'mz':float,'mzMin':float,'mzMax':float,'rtMin':float,'rtMax':float,'Monoisotopic_mass':float,'chemicalFormula':str,'measuredMZ':float,
                  'ppmError':float,'npcStandardID':str,'npcFeatureID':str,'sn1':str,'sn2':str,'logPALOGPS':float,'logPChemAxon':float,'logPRDKit':float,
                  'HMDBClass':str,'HMDBSubClass':str,'HMDBDirectParent':str,'HMDBID':str,
                  'LmapsCategory':str,'LmapsMainclass':str,'LMapsSubclass':str,'LMapsID':str,'KEGGPathway':str,'KEGGID':str,'chemspiderID':str,'PubChemID':str,'IUPAC':str,'CAS':str,'ChEBIID':str,
                  'InChI':str,'InChIKey':str,'confidenceScore':str,'MSIAnnotationLevel':str,'complexityScore':str,'urine':str,'plasma':str,'serum':str,
                  'breastMilk':str,'gastric':str,'dueodenal':str,'faecal':str,'liver':str,'originalMatrix':str,'annotatedBy':str,'validationFiles':str,'ISOriginalFiles':str,'changeLog':str}

    fields_to_ignore = ['Monoisotopic_mass']

    def __init__(self,roi_file=None,roi_dtypes=None,assay_name=None,merged_file=None,replace_fields=False,pipeline_run_id=None,
                 replace_missing=False,fields_to_replace=[],fields_to_ignore=[],cpds_to_replace=[],cpds_to_ignore=[],username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None):
        """Constructor

        :param roi_file: The path to the ROI file, defaults to None
        :type roi_file: str
        :param assay_name: The name of the assay, must match an Assay.name in the database, defaults to None
        :type assay_name: str
        :param merged_file: The file path with the merged names, defaults to None
        :type merged_file: str, optional
        :param replace_fields: Set to True to replace fields, defaults to False
        :type replace_fields: bool, optional
        :param replace_missing: Set to True to replace missing values, defaults to False
        :type replace_missing: bool, optional
        :param fields_to_replace: List of fields to replace, defaults to [], ('all')
        :type fields_to_replace: list, optional
        :param fields_to_ignore: List of fields to not replace, defaults to [], ('none')
        :type fields_to_ignore: list, optional
        :param cpds_to_replace: List of cpdIDs to replace, defaults to [], ('all')
        :type cpds_to_replace: list, optional
        :param cpds_to_ignore: List of cpdIDs to not replace, defaults to [], ('none')
        :type cpds_to_ignore: list, optional
        """        

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id)
        self.roi_file = str(Path(roi_file).absolute())
        self.assay_name = assay_name
        self.replace_fields = replace_fields
        self.replace_missing = replace_missing
        self.row_warnings = []
        self.merged_file = merged_file
        self.fields_to_ignore = self.fields_to_ignore + fields_to_ignore

        if len(fields_to_replace) > 0:
            self.fields_to_replace = fields_to_replace
        else:
            self.fields_to_replace = self.roi_dtypes.keys()

        self.cpds_to_ignore = cpds_to_ignore
        self.cpds_to_replace = cpds_to_replace

        if roi_dtypes:
            self.roi_dtypes = roi_dtypes

        self.args['roi_file'] = roi_file
        self.args['roi_dtypes'] = roi_dtypes
        self.args['assay_name'] = assay_name
        self.args['replace_fields'] = replace_fields
        self.args['replace_missing'] = replace_missing
        self.args['merged_file'] = merged_file
        self.args['fields_to_ignore'] = fields_to_ignore
        self.args['fields_to_replace'] = fields_to_replace
        self.args['cpds_to_replace'] = cpds_to_replace
        self.args['cpds_to_ignore'] = cpds_to_ignore

        self.get_class_name(self)

        self.log_info("Assay: %s, file: %s" % (assay_name,  self.roi_file ))

    def get_assay(self):
        """Get assay 

        :raises Exception: [description]
        """        

        self.assay = self.db_session.query(Assay).filter(Assay.name==self.assay_name).first()

        if not self.assay:
            raise Exception("Unknown assay name: " + self.assay_name)

    def process(self):
        """ Main method
        """        

        self.get_assay()
        super().process()

    def load_data(self):
        """Loads the necessary files
        """        

        super().load_data()

        self.roi_dataset = self.load_tabular_file(self.roi_file,dtype=self.roi_dtypes,na_values=['na'])
        self.roi_dataset['consistencyWarnings'] = ''

        if self.replace_fields or self.replace_missing:
            self.roi_dataset['changeLog'] = ""

        if (self.replace_fields or self.replace_missing) and len(self.cpds_to_replace) == 0:
            self.cpds_to_replace = self.roi_dataset.loc[:,'cpdName'].to_dict()

        if self.merged_file:
            self.merged_names = self.load_tabular_file(self.merged_file)

        self.annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name=="PPR").first()

    def loop_and_map_data(self):
        """Loop and map dataset
        """        

        self.remove_whitespace_and_weird_characters()
        index = 0
        while index < self.roi_dataset.shape[0]:

            print("Checking %s/%s" % (index,self.roi_dataset.shape[0]))

            row = self.roi_dataset.iloc[index,:]
            row = row.where(pd.notnull(row), None)

            if 'purpose' in self.roi_dtypes.keys():
                if 'purpose' in row and row['purpose'] != 'primary':
                    index = index + 1
                    continue

            row = self.check_fields(row)

            self.roi_dataset.iloc[index,:] = row

            time.sleep(1)

            index = index + 1

        if self.replace_fields or self.replace_missing:
            filename = 'phenomedb_cleaned_'+os.path.basename(self.roi_file)
        else:
            filename = 'phenomedb_warnings_'+os.path.basename(self.roi_file)

        self.logger.info("Number of chemspider requests %s" % self.chemspider_request_count)

        self.roi_dataset.to_csv(config['DATA']['app_data']+"output/"+filename,index=False)

        for index, row in self.roi_dataset.iterrows():
            self.logger.info('%s \n %s' % (row['cpdName'],row['consistencyWarnings']))

    def remove_whitespace_and_weird_characters(self):
        """Remove whitespace and strip commonly used weird characters
        """        

        for column, type in self.roi_dtypes.items():
            if type == str:
                self.roi_dataset[column] = self.roi_dataset[column].str.strip().replace('†','')

    def check_fields(self,row):
        """Check the fields for a row. Adds warnings, and replaces if settings specify to

        :param row: The row from the Dataframe
        :type row: `pandas.Series`
        :return: The row from the Dataframe
        :rtype: `pandas.Series`
        """        

        subrows, multi_columns = self.build_subrows(row)

        for cpd_name, subrow in subrows.items():
            self.row_warnings = []
            self.row_changes = []
            if not subrow['InChI'] and not subrow['InChIKey'] and 'refmet_name' in self.roi_dtypes.keys():
                subrow,inchi_key = self.check_refmet(subrow)
                if inchi_key:
                    self.row_warnings.append('InChIKey found in refmet by formula and mass search')

            elif subrow['InChI'] and not subrow['InChIKey']:
                try:
                    inchi_key = self.generate_inchi_key(subrow['InChI'])
                except Exception as err:
                    self.logger.info(str(err))
                    inchi_key = None

                if inchi_key:
                    self.row_warnings.append("InChIKey calculated using RDKIT %s " % inchi_key)
                    subrow = self.check_field(inchi_key,'InChIKey',subrow)
                    if 'refmet_name' in self.roi_dtypes.keys():
                        subrow,refmet_inchi_key = self.check_refmet(subrow,inchi_key=inchi_key)
                else:
                    self.row_warnings.append('unable to create inchi_key from %s' % subrow['InChI'])

            else:
                inchi_key = subrow['InChIKey']
                if 'refmet_name' in self.roi_dtypes.keys():
                    subrow,refmet_inchi_key = self.check_refmet(subrow,inchi_key=inchi_key)

            if inchi_key:

                pubchem_data = None
                if 'PubChemID' in self.roi_dtypes.keys():
                    pubchem_data,subrow = self.check_pubchem(subrow,inchi_key)
                if 'ChEBIID' in self.roi_dtypes.keys():
                    subrow = self.check_chebi(subrow)
                if pubchem_data:
                    if "KEGGID" in self.roi_dtypes.keys():
                        subrow = self.check_kegg(subrow,pubchem_data['pubchem_cid'])
                    if "CAS" in self.roi_dtypes.keys():
                        subrow = self.check_cas(subrow,pubchem_data)
                if 'HMDBID' in self.roi_dtypes.keys():
                    subrow = self.check_hmdb(subrow,inchi_key)
                if "ChEMBLID" in self.roi_dtypes.keys():
                    subrow = self.check_chembl(subrow,inchi_key)
                if "LMapsID" in self.roi_dtypes.keys():
                    subrow = self.check_lipidmaps(subrow,inchi_key)
                if "classyfireSuperclass" in self.roi_dtypes.keys():
                    subrow = self.check_classyfire(subrow,inchi_key)
                if "chemspiderID" in self.roi_dtypes.keys():
                    subrow = self.check_chemspider(subrow,inchi_key)

            else:
                self.row_warnings.append('No InChI, InChIKey, or found refmet InChIKey')

            if row['InChI'] and 'logPRDKit' in self.roi_dtypes.keys():
                subrow = self.check_logP_RDKit(subrow)
            if self.merged_file:
                subrow = self.check_merged_file(subrow)
            subrow['consistencyWarnings'] = "\n".join(self.row_warnings)
            self.logger.info('Consistency warnings: %s: %s' % (cpd_name,subrow['consistencyWarnings']))
            if not subrow['changeLog']:
                subrow['changeLog'] = ''
            if self.replace_fields or self.replace_missing:
                subrow['changeLog'] = "%s Changed: %s \n %s" % (subrow['changeLog'],os.path.basename(self.roi_file),"\n".join(self.row_changes))
            subrows[cpd_name] = subrow

        # rebuild the row from the subrow

        ref_subrow = subrow.copy()

        for column,existing_value in row.iteritems():
            if column not in multi_columns:
                row[column] = ref_subrow[column]
            else:
                i = 0
                value = ''
                for cpd_name, subrow in subrows.items():
                    if i == 0 or i == len(subrows.keys()) - 2:
                        value = value + str(subrow[column]) + " | "
                    else:
                        value = value + str(subrow[column])
                    i = i + 1
                row[column] = value

        return row

    def check_field(self,found_value,field_name,subrow):
        """Check an individual field's value and update if specified to

        :param found_value: The value of the property found via DB lookup
        :type found_value: object
        :param field_name: The name of the field to check
        :type field_name: str
        :param subrow: The subrow containing the fields
        :type subrow: `pandas.Series`
        :raises ROICleanCheckFail: [description]
        :raises ROICleanCheckFail: [description]
        :raises ROICleanCheckFail: [description]
        :raises ROICleanCheckFail: [description]
        :return: The subrow containing the fields
        :rtype: `pandas.Series`
        """        

        missing_entries = []
        correct_entries = []

        try:
            if not subrow[field_name]:
                if isinstance(found_value,list):
                    missing_entries = found_value
                raise ROICleanCheckFail('%s original: None, found: %s' % (field_name,found_value))

            elif subrow[field_name] and not found_value:
                raise ROICleanCheckFail('%s original :%s, found: %s' % (field_name,subrow[field_name],found_value))

            elif isinstance(found_value,list):
                for value in found_value:
                    if value not in subrow[field_name]:
                        missing_entries.append(value)
                    else:
                        correct_entries.append(value)
                if len(missing_entries) > 0:
                    raise ROICleanCheckFail('%s original: %s, missing: %s' % (field_name,subrow[field_name],missing_entries))

            elif found_value != subrow[field_name]:
                raise ROICleanCheckFail('%s original: %s, found: %s' % (field_name,subrow[field_name],found_value))

            else:
                return subrow

        except ROICleanCheckFail as err:

            entries = correct_entries + missing_entries
            self.row_warnings.append(str(err))

            # Replaces fields that are different
            if self.replace_fields\
                    and found_value is not None\
                    and field_name in self.fields_to_replace\
                    and field_name not in self.fields_to_ignore\
                    and subrow['cpdName'] in self.cpds_to_replace.values()\
                    and subrow['cpdName'] not in self.cpds_to_ignore:

                self.row_changes.append('%s %s -> %s' % (field_name, subrow[field_name], found_value))

                if isinstance(found_value,list) and len(entries) > 0:
                    subrow[field_name] = " & ".join(entries)

                else:
                    subrow[field_name] = found_value

            # Only replaces those where the ROI field is missing
            elif self.replace_missing \
                    and subrow[field_name] is None\
                    and found_value is not None \
                    and field_name in self.fields_to_replace \
                    and field_name not in self.fields_to_ignore \
                    and subrow['cpdName'] in self.cpds_to_replace.values() \
                    and subrow['cpdName'] not in self.cpds_to_ignore:

                self.row_changes.append('%s %s -> %s' % (field_name, subrow[field_name], found_value))

                if isinstance(found_value,list) and len(entries) > 0:
                    subrow[field_name] = " & ".join(entries)

                else:
                    subrow[field_name] = found_value

        return subrow

    def check_chemspider(self, subrow, inchi_key):
        """Check found chemspider against the chemspider.

        Only works for those without IDs

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to use to search ChEMBL
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """

        if not subrow['chemspiderID']:
            chemspider = self.get_from_chemspider_by_inchi_key(inchi_key)

            if chemspider:
                subrow = self.check_field(chemspider, 'chemspiderID', subrow)

            else:
                self.row_warnings.append("no chemspider record")

        return subrow

    def check_chembl(self,subrow,inchi_key):
        """Check found ChEMBL against the ChEMBLID

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to use to search ChEMBL
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        chembl = self.get_from_chembl(inchi_key)

        if chembl and isinstance(chembl,dict) and 'molecule_chembl_id' in chembl:
            subrow = self.check_field(chembl['molecule_chembl_id'],'ChEMBLID',subrow)

        else:
            self.row_warnings.append("no chembl record")

        return subrow


    def check_merged_file(self,subrow):
        """Checked the mergedName against the merged_file

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        # check for the cpdID in the cpdID1 column
        try:
            merged_row = np.where(self.merged_names.loc[:,'cpdID1'] == subrow['cpdID'])[0][0]
        except:
            merged_row = None
        # if not, check cpdID2, then cpdID3.
        if not merged_row:
            try:
                merged_row = np.where(self.merged_names.loc[:,'cpdID2'] == subrow['cpdID'])[0][0]
            except:
                merged_row = None
        if not merged_row:
            try:
                merged_row = np.where(self.merged_names.loc[:,'cpdID3'] == subrow['cpdID'])[0][0]
            except:
                merged_row = None
        # get the related cpdName for that row, then check that against mergedName in the subrow
        if merged_row:
            subrow = self.check_field(self.merged_names.loc[merged_row,'cpdName'],'mergedName',subrow)
        else:
            self.row_warnings.append('mergedName not found')

        return subrow

    def check_cas(self,subrow,pubchem_data):
        """Check the CAS number from pubchem against the row data

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param pubchem_data: The pubchem record
        :type pubchem_data: dict
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        if pubchem_data:
            pubchem_data = self.get_cas_from_pubchem(pubchem_data)

            if 'cas_entries' in pubchem_data:
                subrow = self.check_field(pubchem_data['cas_entries'],'CAS',subrow)


        return subrow


    def check_logP_RDKit(self,subrow):
        """Check the logP calculated in RDKit against the one in the ROI file

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        try:
            log_p = self.calculate_log_p(subrow['InChI'])
            if log_p:
                subrow = self.check_field(log_p,'logPRDKit',subrow)
            else:
                self.row_warnings.append('log_p not calculated from rdkit')
        except Exception as err:
            self.logger.exception(err)

        return subrow

    def check_pubchem(self,subrow,inchi_key):
        """[summary]

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to search with
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        pubchem_data = self.get_from_pubchem(inchi_key)
        if pubchem_data:
            if 'InChI' in self.roi_dtypes.keys():
                subrow = self.check_field(pubchem_data['inchi'],'InChI',subrow)
            if 'InChIKey' in self.roi_dtypes.keys():
                subrow = self.check_field(pubchem_data['inchi_key'],'InChIKey',subrow)
            if 'IUPAC' in self.roi_dtypes.keys():
                subrow = self.check_field(pubchem_data['iupac'],'IUPAC',subrow)
            if 'chemicalFormula' in self.roi_dtypes.keys():
                subrow = self.check_field(pubchem_data['chemical_formula'],'chemicalFormula',subrow)
            if 'Monoisotopic_mass' in self.roi_dtypes.keys():
                subrow = self.check_field(pubchem_data['monoisotopic_mass'],'Monoisotopic_mass',subrow)
        else:
            self.row_warnings.append('No found pubchem')

        return pubchem_data, subrow

    def check_chebi(self,subrow):
        """Check ChEBI using the InChI

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        chebi_id = self.get_from_chebi(subrow['InChI'])
        if chebi_id:
            subrow = self.check_field(chebi_id,'ChEBIID',subrow)
        else:
            self.row_warnings.append('No found chebi')

        return subrow

    def check_kegg(self,subrow,pubchem_cid):
        """Check KEGG using pubchem id

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param pubchem_cid: The Pubchem CID to search KEGG with
        :type pubchem_cid: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        kegg_id = self.get_from_kegg(pubchem_cid)
        if kegg_id:
            subrow = self.check_field(kegg_id,'KEGGID',subrow)
        else:
            self.row_warnings.append('No found kegg')

        return subrow

    def check_hmdb(self,subrow,inchi_key):
        """Check HMDB using inchi_key

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to use to search HMDB
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        hmdb_row = self.get_from_hmdb(inchi_key)
        if hmdb_row is not None:
            subrow = self.check_field(self.hmdb.loc[hmdb_row,"HMDB Primary ID"],'HMDBID',subrow)
            subrow = self.check_field(self.hmdb.loc[hmdb_row,"class"],'HMDBClass',subrow)
            subrow = self.check_field(self.hmdb.loc[hmdb_row,"sub_class"],'HMDBSubClass',subrow)
            subrow = self.check_field(self.hmdb.loc[hmdb_row,"direct_parent"],'HMDBDirectParent',subrow)
            #subrow = self.check_field(self.hmdb.loc[hmdb_row,"cas_registry_number"],'CAS',subrow)
        else:
            self.row_warnings.append('No found hmdb')

        return subrow

    def check_refmet(self,subrow,inchi_key=None):
        """Check refmet using inchi_key or mass range

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to use to search REFMET
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        refmet_row = self.get_from_refmet(subrow,inchi_key=inchi_key)
        if refmet_row is not None:
            subrow = self.check_field(self.refmet.loc[refmet_row,"refmet_name"],'refmetName',subrow)
            subrow = self.check_field(self.refmet.loc[refmet_row,"super_class"],'refmetSuperClass',subrow)
            subrow = self.check_field(self.refmet.loc[refmet_row,"main_class"],'refmetMainClass',subrow)
            subrow = self.check_field(self.refmet.loc[refmet_row,"sub_class"],'refmetSubClass',subrow)

            if not inchi_key and self.refmet.loc[refmet_row,"inchi_key"]:
                inchi_key = self.refmet.loc[refmet_row,"inchi_key"]
        else:
            self.row_warnings.append('No found refmet')

        return subrow, inchi_key

    def check_lipidmaps(self,subrow,inchi_key):
        """Check the lipidmaps fields

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to use to search lipidmaps
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        lipidmaps_row = self.get_from_lipidmaps(inchi_key)
        if lipidmaps_row is not None:
            subrow = self.check_field(self.lipid_maps.loc[lipidmaps_row,"regno"],'LMapsID',subrow)
            subrow = self.check_field(self.lipid_maps.loc[lipidmaps_row,"core"],'LmapsCategory',subrow)
            subrow = self.check_field(self.lipid_maps.loc[lipidmaps_row,"main_class"],'LmapsMainclass',subrow)
            subrow = self.check_field(self.lipid_maps.loc[lipidmaps_row,"sub_class"],'LMapsSubclass',subrow)
            #subrow = self.check_field(self.lipid_maps.loc[lipidmaps_row,"class_level4"],'LMapsDirectparent',subrow)
        else:
            self.row_warnings.append('No found lipidmaps')

        return subrow

    def check_classyfire(self,subrow,inchi_key):
        """Check classyfire fields

        :param subrow: The subrow containing the data
        :type subrow: `pandas.Series`
        :param inchi_key: The InChI Key to use to search CLASSYFIRE
        :type inchi_key: str
        :return: The subrow containing the data
        :rtype: `pandas.Series`
        """        

        classyfire = self.get_from_classyfire(inchi_key)

        if classyfire:
            if classyfire['superclass']:
                subrow = self.check_field(classyfire['superclass']['name'],'classyfireSuperclass',subrow)
            if classyfire['class']:
                subrow = self.check_field(classyfire['class']['name'],'classyfireClass',subrow)
            if classyfire['subclass']:
                subrow = self.check_field(classyfire['subclass']['name'],'classyfireSubclass',subrow)
            if classyfire['direct_parent']:
                subrow = self.check_field(classyfire['direct_parent']['name'],'classyfireDirectparent',subrow)

        else:
            self.row_warnings.append('No found classyfire')
        return subrow


class ImportROICompounds(CompoundTask):
    """Import ROI Compounds

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    pubchem_rest_base = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/'

    roi_dtypes = {'cpdID':str,'cpdName':str,'feature':pd.Int64Dtype(),'ion':str,'purpose':str,'IonID':str,'Commentsformanualrevision':str,'rt':float,'rt_minutes':float,
                  'mz':float,'mzMin':float,'mzMax':float,'rtMin':float,'rtMax':float,'Monoisotopic_mass':float,'chemicalFormula':str,'measuredMZ':float,
                  'ppmError':float,'npcStandardID':str,'npcFeatureID':str,'sn1':str,'sn2':str,'logPALOGPS':float,'logPChemAxon':float,'logPRDKit':str,'mergedName':str,
                  'refmetName':str,'refmetSuperClass':str,'refmetMainClass':str,'refmetSubClass':str,'classyfireSuperclass':str,'classyfireClass':str,'classyfireSubclass':str,'classyfireDirectparent':str,
                  'HMDBClass':str,'HMDBSubClass':str,'HMDBDirectParent':str,'HMDBID':str,
                  'LmapsCategory':str,'LmapsMainclass':str,'LMapsSubclass':str,'LMapsID':str,'KEGGPathway':str,'KEGGID':str,'chemspiderID':str,'PubChemID':str,'IUPAC':str,'CAS':str,'ChEBIID':str,
                  'ChEMBLID':str,'InChI':str,'InChIKey':str,'confidenceScore':str,'MSIAnnotationLevel':str,'complexityScore':str,'urine':str,'plasma':str,'serum':str,
                  'breastMilk':str,'gastric':str,'dueodenal':str,'faecal':str,'liver':str,'originalMatrix':str,'annotatedBy':str,'validationFiles':str,'ISOriginalFiles':str,'changeLog':str,
                  'consistencyWarnings':str}

    def __init__(self,roi_file=None,assay_name=None,roi_version=None,update_names=False,task_run_id=None,username=None,pipeline_run_id=None,upstream_task_run_id=None,
                 na_values=None,na_none=None,db_env=None,db_session=None,execution_date=None,missing_lipid_classes=False):
        """Constructor

        :param roi_file: Path to ROI file, defaults to None
        :type roi_file: str
        :param assay_name: Assay name, must exist in database Assay.name, defaults to None
        :type assay_name: str
        :param roi_version: The version of the ROI file, defaults to None
        :type roi_version: str, optional
        :param update_names: Set to True to update names to refmet, defaults to False
        :type update_names: bool, optional
        """        

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)
        self.roi_file = str(Path(roi_file).absolute())
        self.assay_name = assay_name
        self.roi_version = roi_version
        self.update_names = update_names
        self.na_none = na_none
        self.na_values = na_values
        self.missing_lipid_classes = missing_lipid_classes
        self.args['roi_file'] = roi_file
        self.args['assay_name'] = assay_name
        self.args['roi_version'] = roi_version
        self.args['update_names'] = update_names
        self.args['na_none'] = na_none
        self.args['na_values'] = na_values
        self.args['missing_lipid_classes'] = missing_lipid_classes

        self.get_class_name(self)

        self.log_info("Assay: %s, version: %s, file: %s" % (assay_name, self.roi_version, self.roi_file ))

    def process(self):
        """Main method
        """        

        self.get_assay()
        super().process()

    def load_data(self):
        """Loads data 
        """        

        super().load_data()

        self.roi_dataset = self.load_tabular_file(self.roi_file,dtype=self.roi_dtypes,replace_na_with_none=self.na_none,na_values=self.na_values)

        self.annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name=="PPR").first()

    def loop_and_map_data(self):
        """Loop and map the data
        """        

        compound_feature_configs = {}

        for index, row in self.roi_dataset.iterrows():

            row = row.where(pd.notnull(row), None)

            # If any of these are empty, ignore the row entirely
            if row['cpdID'] == '' or not row['cpdID'] or not row['cpdName']:
                continue
            else:
                cpd_id = row['cpdID']

            cpd_name = row['cpdName'].strip()
            ion_id = row['IonID'].strip()

            if cpd_name == 'Symmetric | Asymmetric Dimethylarginine':
                bp = True

            if row['purpose'] == 'primary' and row["InChI"] and not self.missing_lipid_classes:
                self.import_row(row)
                time.sleep(1)
            elif not row['InChI'] or row['InChI'] in ['Unknown','na'] and self.missing_lipid_classes:
                self.import_row(row)

            self.db_session.flush()

        #for cpd_name,feature_dict in compound_feature_configs.items():
        #    self.update_annotation(cpd_name,feature_dict,self.roi_version)

    def import_row(self,row):
        """Imports a row from the file.

        1. Breaks the row into subrows and imports seperately.
        2. Finds or adds Annotation + harmonised annotation
        3. Adds compounds + identifiers
        4. Adds groups

        :param row: The row from the ROI dataframe
        :type row: `pandas.Series`
        :return: The row from the ROI dataframe
        :rtype: `pandas.Series`
        """        

        self.row_warnings = []

        subrows, multi_columns = self.build_subrows(row)

        #1. Get the annotation (if exists).

        # Get or add harmonised_annotation

        cpd_name = row['cpdName'].strip().replace('†','')
        cpd_id = row['cpdID'].strip().replace('†','')
        if self.assay.name in ['LPOS','LNEG'] and re.search('\|',cpd_name):
            multi_compound_operator = Annotation.MultiCompoundOperator.AND
        elif re.search('\|',cpd_name) or (self.assay.name in ['LPOS','LNEG'] and re.search('and\/or',cpd_name)):
            multi_compound_operator = Annotation.MultiCompoundOperator.ANDOR
        else:
            multi_compound_operator = None

        if self.assay.name in ['LPOS','LNEG'] and multi_compound_operator:
            bp = True

        annotation = self.db_session.query(Annotation).join(HarmonisedAnnotation) \
            .filter(func.lower(func.replace(Annotation.cpd_name," ","")) == func.lower(func.replace(cpd_name," ",""))) \
            .filter(Annotation.version == self.roi_version) \
            .filter(Annotation.cpd_id == cpd_id) \
            .filter(Annotation.annotation_method_id == self.annotation_method.id).first()
            #.filter(HarmonisedAnnotation.assay_id == self.assay.id).first()

        if not annotation:

            harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
                HarmonisedAnnotation.assay_id == self.assay.id,
                HarmonisedAnnotation.annotation_method_id == self.annotation_method.id,
                HarmonisedAnnotation.cpd_id == cpd_id).first()
                #func.lower(func.replace(HarmonisedAnnotation.cpd_name," ","")) == func.lower(func.replace(cpd_name," ",""))).first()

            if not harmonised_annotation:

                harmonised_annotation = self.db_session.query(HarmonisedAnnotation).filter(
                    HarmonisedAnnotation.assay_id == self.assay.id,
                    HarmonisedAnnotation.annotation_method_id == self.annotation_method.id,
                    func.lower(func.replace(HarmonisedAnnotation.cpd_name," ","")) == func.lower(func.replace(cpd_name," ",""))).first()

            if not harmonised_annotation:
                if multi_compound_operator:
                    multi_compound_operator = multi_compound_operator.value
                self.logger.info("No matching harmonised_annotation! %s" % cpd_name)
                harmonised_annotation = HarmonisedAnnotation(assay_id=self.assay.id,
                                                             annotation_method_id=self.annotation_method.id,
                                                             cpd_id=cpd_id,
                                                             cpd_name=cpd_name,
                                                             confidence_score=row['confidenceScore'],
                                                             latest_version=self.roi_version,
                                                             multi_compound_operator=multi_compound_operator)
                self.db_session.add(harmonised_annotation)
                self.db_session.flush()
                harmonised_annotation_id = harmonised_annotation.id

            elif multi_compound_operator:
                harmonised_annotation.multi_compound_operator = multi_compound_operator.value
                harmonised_annotation_id = harmonised_annotation.id
                self.logger.info("Matched harmonised_annotation! %s" % harmonised_annotation)
            else:
                harmonised_annotation_id = harmonised_annotation.id

            self.db_session.flush()

            annotated_by = None
            confidence_score = None
            if row['annotatedBy'] and isinstance(row['annotatedBy'],str):
                annotated_by = row['annotatedBy'].strip()
            if row['confidenceScore'] and isinstance(row['confidenceScore'],str):
                confidence_score = row['confidenceScore'].strip()

            annotation = Annotation(cpd_name=cpd_name,
                                    harmonised_annotation_id=harmonised_annotation_id,
                                    cpd_id=cpd_id,
                                    multi_compound_operator=multi_compound_operator,
                                    version=self.roi_version,
                                    config=utils.serialise_unserialise(self.clean_data_for_jsonb(row)),
                                    annotated_by=annotated_by,
                                    confidence_score=confidence_score,
                                    default_primary_ion_rt_seconds=row['rt'],
                                    default_primary_ion_mz=row['mz'])
            self.db_session.add(annotation)
            self.db_session.flush()

        for cpd_name, subrow in subrows.items():
            if subrow['purpose'] == 'primary':
                self.add_or_update_compound_from_subrow(subrow,annotation)

        self.logger.info('Import warnings: %s:%s' % (annotation,'\n'.join(self.row_warnings)))

        return row


    def add_or_update_compound_from_subrow(self,row,annotation):
        """Add or update compound from subrow

        :param row: The row from the ROI dataframe
        :type row: `pandas.Series`
        :param annotation: The Annotation object
        :type annotation: `phenomedb.models.Annotation`
        """        

        if row['InChI']:
            inchi = row['InChI'].strip().replace('†','')
        else:
            inchi = None
        if row['InChIKey']:
            inchi_key = row['InChIKey'].strip().replace('†','').replace('�','')
        else:
            inchi_key = None
        if row['chemicalFormula']:
            chemical_formula = row['chemicalFormula'].strip().replace('†','')
        else:
            chemical_formula = None
        if row['Monoisotopic_mass']:
            monoisotopic_mass = row['Monoisotopic_mass']
        else:
            monoisotopic_mass = None
        if 'logPRDKit' in row and row['logPRDKit']:
            log_p = float(row['logPRDKit'])
        else:
            log_p = None
        if row['IUPAC']:
            iupac = row['IUPAC'].strip().replace('†','')
        else:
            iupac = None
        #if row['SMILES']:
        #    smiles = row['SMILES'].strip().replace('†','')
        #else:
        smiles = None

        if 'mergedName' in row and row['mergedName']:
            sub_cpd_name = row['mergedName'].strip().replace('†','')
        elif row['cpdName']:
            sub_cpd_name = row['cpdName'].strip().replace('†','')
        else:
            sub_cpd_name = None

        self.add_or_update_compound(row,annotation,inchi,inchi_key,chemical_formula,monoisotopic_mass,log_p,iupac,smiles,sub_cpd_name=sub_cpd_name)


    def add_or_update_compound(self,row,annotation,inchi,inchi_key,chemical_formula,monoisotopic_mass,log_p,iupac,smiles,sub_cpd_name=None):
        """Adds or updates a compound

        :param row: The row from the ROI dataframe
        :type row: `pandas.Series`
        :param annotation: The Annotation object
        :type annotation: `phenomedb.models.Annotation`
        :param inchi: The InChI for the Compound
        :type inchi: str
        :param inchi_key: The InChI Key for the Compound
        :type inchi_key: str
        :param chemical_formula: The chemical formula for the Compound
        :type chemical_formula: str
        :param monoisotopic_mass: The monoisotopic_mass of the Compound
        :type monoisotopic_mass: float
        :param log_p: The logP (partition coefficient) of the Compound
        :type log_p: float
        :param iupac: The IUPAC identifier of the Compound
        :type iupac: str
        :param smiles: The SMILES string of the Compound
        :type smiles: str
        :param sub_cpd_name: The split cpd_name of the Annotation, defaults to None
        :type sub_cpd_name: str, optional
        :return: The Compound
        :rtype: `phenomedb.models.Compound`
        """

        if inchi:
            compound = self.db_session.query(Compound).filter(Compound.inchi==inchi).first()
            cpd_name = sub_cpd_name

        elif inchi_key:
            compound = self.db_session.query(Compound).filter(Compound.inchi_key==inchi_key).first()
            cpd_name = sub_cpd_name

        elif self.assay.name in ['LPOS','LNEG']:

            compound = self.db_session.query(Compound).filter(Compound.name==sub_cpd_name).first()
            cpd_name = sub_cpd_name

        else:
            compound = self.db_session.query(Compound).filter(Compound.name==annotation.harmonised_annotation.cpd_name).first()

            cpd_name = annotation.harmonised_annotation.cpd_name

            if not compound \
                and (re.search('_1$',annotation.harmonised_annotation.cpd_name) \
                    or re.search('_2$',annotation.harmonised_annotation.cpd_name) \
                    or re.search('_3$',annotation.harmonised_annotation.cpd_name)):

                compound = self.db_session.query(Compound).filter(Compound.name==annotation.harmonised_annotation.cpd_name[:-2]).first()

        if inchi_key == 'QWYFHHGCZUCMBN-SECBINFHSA-N':
            bp = True

        if not compound:
            # Set them from the ROI fields first, and then if any are None, calculate or retrieve them
            compound = Compound(name=cpd_name,
                                inchi=inchi,
                                inchi_key=inchi_key,
                                chemical_formula=chemical_formula,
                                monoisotopic_mass=monoisotopic_mass,
                                log_p=log_p,
                                iupac=iupac,
                                smiles=smiles
                                )
            self.db_session.add(compound)

        else:
            compound.inchi = inchi
            compound.inchi_key = inchi_key
            compound.chemical_formula = chemical_formula
            compound.monoisotopic_mass = monoisotopic_mass
            compound.log_p = log_p
            compound.iupac = iupac
            compound.smiles = smiles

        self.logger.info("Compound added/updated %s" % compound)

        self.db_session.flush()

        if compound.inchi not in [None,'Unknown'] and compound.inchi_key in [None,'Unknown']:
            compound.set_inchi_key_from_rdkit()

        if compound.inchi not in [None,'Unknown'] and (compound.log_p == '' or not compound.log_p):
            compound.set_log_p_from_rdkit()


        annotation_compound = self.db_session.query(AnnotationCompound).filter(AnnotationCompound.compound_id==compound.id,
                                                                               AnnotationCompound.harmonised_annotation_id==annotation.harmonised_annotation.id).first()

        if not annotation_compound:
            annotation_compound = AnnotationCompound(harmonised_annotation_id=annotation.harmonised_annotation.id,
                                                     compound_id=compound.id)
            self.db_session.add(annotation_compound)
            self.db_session.flush()

        if compound.inchi != 'Unknown':
            pubchem_cid = self.add_or_update_pubchem_from_api(compound)
            chebi_id = self.add_or_update_chebi(compound)
            refmet_name = self.update_name_to_refmet(compound)
            kegg_id = self.add_or_update_kegg(compound, pubchem_cid=pubchem_cid, kegg_id=row['KEGGID'])
            hmdb_id = self.add_or_update_hmdb(compound)
            lm_id = self.add_or_update_lipid_maps(compound)
            chembl_id = self.add_or_update_chembl(compound)
            self.add_or_update_classyfire(compound)
        else:
            kegg_id = self.add_or_update_kegg(compound, kegg_id=row['KEGGID'])
            self.add_or_update_lipid_maps_classes(compound,row)

        self.db_session.flush()

        return compound


    def add_or_update_lipid_maps_classes(self,compound,row):

        if row['LMapsID']:
            lipidmaps_id = row['LMapsID']
        else:
            lipidmaps_id = None
        if row['LmapsCategory']:
            category = row['LmapsCategory']
        else:
            category = None
        if row['LmapsMainclass']:
            main_class = row['LmapsMainclass']
        else:
            main_class = None
        if row['LMapsSubclass']:
            sub_class = row['LMapsSubclass']
        else:
            sub_class = None

        if lipidmaps_id:
            lipid_maps_entry = self.db_session.query(CompoundExternalDB) \
                .filter(CompoundExternalDB.compound_id == compound.id) \
                .filter(CompoundExternalDB.external_db_id == self.lipid_maps_external_db_id).first()
            if lipid_maps_entry:
                lipid_maps_entry.database_ref = lipidmaps_id

            else:
                lipid_maps_entry = CompoundExternalDB(compound_id=compound.id,
                                                      external_db_id=self.lipid_maps_external_db_id,
                                                      database_ref=lipidmaps_id)
                self.db_session.add(lipid_maps_entry)
            self.db_session.flush()

        if category and main_class and sub_class:
            lipidmaps_group = self.db_session.query(CompoundClass) \
                .filter(CompoundClass.category == category) \
                .filter(CompoundClass.main_class == main_class) \
                .filter(CompoundClass.sub_class == sub_class) \
                .filter(CompoundClass.type == CompoundClass.CompoundClassType.lipidmaps) \
                .first()

            if not lipidmaps_group:
                lipidmaps_group = CompoundClass(name="",
                                                type=CompoundClass.CompoundClassType.lipidmaps,
                                                category=category,
                                                main_class=main_class,
                                                sub_class=sub_class
                                                )

                self.db_session.add(lipidmaps_group)
                self.db_session.flush()

            compound_class_compound = self.db_session.query(CompoundClassCompound) \
                .filter(CompoundClassCompound.compound_class_id == lipidmaps_group.id) \
                .filter(CompoundClassCompound.compound_id == compound.id) \
                .first()

            if not compound_class_compound:
                compound_class_compound = CompoundClassCompound(compound_class_id=lipidmaps_group.id,
                                                                compound_id=compound.id)
                self.db_session.add(compound_class_compound)
                self.db_session.flush()

            # Add ontology here

            ontology_source = self.db_session.query(OntologySource).filter(
                OntologySource.name == 'LipidMAPS class').first()

            if not ontology_source:
                ontology_source = OntologySource(name='LipidMAPS class',
                                                 description='LipidMAPS class lookup',
                                                 url='https://www.lipidmaps.org/data/structure/LMSDSearch.php?Mode=ProcessClassSearch&LMID=')
                self.db_session.add(ontology_source)
                self.db_session.flush()

            # Repeat for other ontologies including LMID -> compound_external_db_id
            if category:
                self.add_or_update_ontology_ref(ontology_source, self.get_lipid_maps_reference(category),
                                                'compound_class_category_id', lipidmaps_group.id)
            if main_class:
                self.add_or_update_ontology_ref(ontology_source, self.get_lipid_maps_reference(main_class),
                                                'compound_class_main_class_id', lipidmaps_group.id)
            if sub_class:
                self.add_or_update_ontology_ref(ontology_source, self.get_lipid_maps_reference(sub_class),
                                                'compound_class_sub_class_id', lipidmaps_group.id)


    def validate(self):

        compound_df = self.load_tabular_file(self.roi_file,dtype=self.roi_dtypes,na_values=self.na_values,replace_na_with_none=self.na_none)
        index = 0
        while index < compound_df.shape[0]:

            annotation = None

            annotation_cpd_name = compound_df.loc[index,'cpd_name'].strip().replace('†', '')
            annotations = self.db_session.query(Annotation).filter(Annotation.cpd_name==annotation_cpd_name,
                                                        Annotation.version==self.roi_version).all()
            if len(annotations) == 0:
                raise ValidationError('Expected Annotation missing %s v%s' % (annotation_cpd_name,self.roi_version))

            elif len(annotations) > 1:
                raise ValidationError('More than 1 expected Annotations %s v%s' % (annotation_cpd_name,self.roi_version))

            else:
                annotation = annotations[0]

            if annotation:
                if len(annotation.compounds) != self.annotation_compound_counts[annotation_cpd_name]:
                    raise ValidationError("Different number of compounds for Annotation than expected cpd_name:%s expected:%s actual:%s" % (annotation_cpd_name,len(annotation.compounds),self.annotation_compound_counts[annotation_cpd_name]))

            index = index + 1


class ImportBrukerBiLISACompounds(CompoundTask):
    """Import the Bruker BILISA Lipoprotein fractions. The file is in test_data/compounds/
    These are imported as Annotations, not Compounds, as they represent centrifuged fractions of lipoproteins, not individual compounds.

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    template_dtypes = {'Matrix': str,
                       'Analyte': str,
                       'Name': str,
                       'Unit': str
                       }

    assay_name = "NOESY"

    def __init__(self,bilisa_file=None,version=None,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):
        """Constructor

        :param ivdr_version: The version of the annotations, defaults to None
        :type ivdr_version: str, optional
        """        

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)

        self.version = version
        self.bilisa_file = bilisa_file
        self.args['version'] = version
        self.args['bilisa_file'] = bilisa_file

        self.get_class_name(self)

        self.log_info("Assay: %s, version: %s" % (self.assay_name, self.version ))

    def load_data(self):
        """Loads the annotation method and then assay. The 
        """        

        super().load_data()

        self.lipoproteins = self.load_tabular_file(self.bilisa_file)

        self.annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name=="Bi-LISA").first()

        self.assay = self.db_session.query(Assay).filter(Assay.name==self.assay_name).first()

    def loop_and_map_data(self):
        """Loop and map data
        """        

        for index, row in self.lipoproteins.iterrows():

            self.add_annotation(row)

        self.db_session.flush()

    def add_annotation(self,row):
        """Add Annotation

        :param row: The row from the file
        :type row: `pandas.Series`
        """        

        cpd_name = row['Feature Name'].strip()
        matrix = row['Matrix'].strip()
        analyte = row['Analyte'].strip()
        unit = row['Unit'].strip()

        config = {'matrix':matrix,'analyte':analyte,'unit':unit}

        annotation = self.db_session.query(Annotation) \
            .filter(Annotation.assay_id==self.assay.id,
                    Annotation.cpd_name==cpd_name,
                    Annotation.annotation_method_id==self.annotation_method.id).first()

        if not annotation:
            annotation = Annotation(assay_id=self.assay.id,
                                     annotation_method_id=self.annotation_method.id,
                                     cpd_name=cpd_name,
                                     version=self.version,
                                     config=config,
                                     cpd_id=cpd_name)
            self.db_session.add(annotation)
            self.db_session.flush()
        else:
            annotation.cpd_id = cpd_name
            annotation.config = config
        
        harmonised_annotation = self.db_session.query(HarmonisedAnnotation) \
            .filter(HarmonisedAnnotation.assay_id==self.assay.id,
                    HarmonisedAnnotation.cpd_name==cpd_name,
                    HarmonisedAnnotation.cpd_id == cpd_name,
                    HarmonisedAnnotation.annotation_method_id==self.annotation_method.id).first()

        if not harmonised_annotation:
            harmonised_annotation = HarmonisedAnnotation(assay_id=self.assay.id,
                                                 annotation_method_id=self.annotation_method.id,
                                                 cpd_name=cpd_name,
                                                 cpd_id=cpd_name)
            self.db_session.add(harmonised_annotation)
            self.db_session.flush()

        annotation.harmonised_annotation_id = harmonised_annotation.id
        self.db_session.flush()



class ImportBrukerBiQuantCompounds(CompoundTask):
    """Import Bruker BI-QUANT Compounds.

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    assay_name = "NOESY"

    def __init__(self,version=None,biquant_compounds_file=None,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):
        """Constructor method

        :param ivdr_version: The version of the annotation config file, defaults to None
        :type ivdr_version: str, optional
        :param biquant_compounds_file: The path to the BIQUANT compound config file, defaults to None
        :type biquant_compounds_file: str, optional
        """        

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)

        self.version = version
        self.biquant_compounds_file = biquant_compounds_file
        self.args['version'] = version
        self.args['biquant_compounds_file'] = biquant_compounds_file

        self.get_class_name(self)

    def load_data(self):
        """load the data
        """        

        super().load_data()

        self.urine_annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name == "Bi-Quant-U").first()
        self.plasma_annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name == "Bi-Quant-P").first()

        self.assay = self.db_session.query(Assay).filter(Assay.name==self.assay_name).first()

        self.biquant_compounds = self.load_tabular_file(self.biquant_compounds_file,dtype={'cpdID':str,'cpdName':str,'InChI':str,'AnnotationMethod':str})

    def loop_and_map_data(self):
        """Loop and map data
        """        

        for index, row in self.biquant_compounds.iterrows():

            self.add_compound_and_mappings(row)
            time.sleep(3)

        self.db_session.flush()

    def add_compound_and_mappings(self,row):
        """Add compound and mappings

        :param row: The row from the file
        :type row: `pandas.Series`
        """

        cpd_id = row['cpdID'].strip()
        cpd_name = row['cpdName'].strip()
        inchi = row['InChI'].strip()
        annotation_method = row['AnnotationMethod'].strip()

        compound = self.db_session.query(Compound).filter(Compound.inchi==inchi).first()

        if not compound:

            inchi_key = self.generate_inchi_key(inchi)
            log_p = self.calculate_log_p(inchi)

            monoisotopic_mass = None
            chemical_formula = None
            iupac = None
            smiles = None

            pubchem_data = self.get_from_pubchem_api('inchikey',inchi_key)

            if pubchem_data and "PC_Compounds" in pubchem_data:

                number_of_matched_compounds = len(pubchem_data["PC_Compounds"])
                if(number_of_matched_compounds > 1):
                    self.logger.info('Pubchem returned more than 1 compound: '+inchi)

                pubchem_compound = pubchem_data["PC_Compounds"][0]

                # check pubchem cid
                if pubchem_compound['id']:
                    pubchem_cid = pubchem_compound['id']['id']['cid']
                else:
                    pubchem_cid = None

                #inchi_key = self.get_pubchem_prop(pubchem_compound,'InChIKey','Standard')
                smiles = self.get_pubchem_prop(pubchem_compound,'SMILES','Canonical')
                iupac = self.get_pubchem_prop(pubchem_compound,'IUPAC','Preferred')
                chemical_formula = self.get_pubchem_prop(pubchem_compound,'Molecular Formula')
                monoisotopic_mass = self.get_pubchem_prop(pubchem_compound,'Weight','MonoIsotopic')

                if not monoisotopic_mass:
                    bp = True

            compound = self.db_session.query(Compound).filter(Compound.inchi_key==inchi_key).first()

            if not compound:

                compound = Compound(name=cpd_name,
                                    inchi=inchi,
                                    inchi_key=inchi_key,
                                    monoisotopic_mass=monoisotopic_mass,
                                    chemical_formula=chemical_formula,
                                    iupac=iupac,
                                    smiles=smiles,
                                    log_p=log_p)

                self.db_session.add(compound)
                self.db_session.flush()

        pubchem_cid = self.add_or_update_pubchem_from_api(compound)
        refmet_name = self.update_name_to_refmet(compound=compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
        lm_id = self.add_or_update_lipid_maps(compound=compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
        chebi_id = self.add_or_update_chebi(compound=compound)
        hmdb_id = self.add_or_update_hmdb(compound=compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
        chembl_id = self.add_or_update_chembl(compound=compound)
        cas_id = self.add_cas_from_hmdb(compound=compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
        self.add_or_update_classyfire(compound)
        chemspider = self.add_chemspider_if_missing(compound)

        if pubchem_cid:
            kegg_id = self.add_or_update_kegg(compound=compound,pubchem_cid=pubchem_cid)

        if annotation_method == 'Bi-Quant-U':
            annotation_method_id = self.urine_annotation_method.id
        elif annotation_method == 'Bi-Quant-P':
            annotation_method_id = self.plasma_annotation_method.id


        annotation = self.db_session.query(Annotation) \
            .filter(Annotation.assay_id==self.assay.id,
                    Annotation.cpd_name==cpd_name,
                    Annotation.annotation_method_id==annotation_method_id,
                    Annotation.version==self.version).first()

        if not annotation:
            annotation = Annotation(assay_id=self.assay.id,
                                     annotation_method_id=annotation_method_id,
                                     cpd_name=cpd_name,
                                    cpd_id=cpd_id,
                                    version=self.version)
            self.db_session.add(annotation)
            self.db_session.flush()

        else:
            annotation.cpd_id = cpd_id

        harmonised_annotation = self.db_session.query(HarmonisedAnnotation) \
            .filter(HarmonisedAnnotation.assay_id == self.assay.id,
                    HarmonisedAnnotation.cpd_name == cpd_name,
                    HarmonisedAnnotation.cpd_id == cpd_name,
                    HarmonisedAnnotation.annotation_method_id == annotation_method_id).first()

        if not harmonised_annotation:
            harmonised_annotation = HarmonisedAnnotation(assay_id=self.assay.id,
                                                         annotation_method_id=annotation_method_id,
                                                         cpd_name=cpd_name,
                                                         cpd_id=cpd_name)
            self.db_session.add(harmonised_annotation)
            self.db_session.flush()

        annotation.harmonised_annotation_id = harmonised_annotation.id
        self.db_session.flush()

        annotation_compound = self.db_session.query(AnnotationCompound) \
            .filter(AnnotationCompound.compound_id==compound.id) \
            .filter(AnnotationCompound.harmonised_annotation_id==harmonised_annotation.id).first()

        if not annotation_compound:
            annotation_compound = AnnotationCompound(compound_id=compound.id,
                                                      harmonised_annotation_id=harmonised_annotation.id)
            self.db_session.add(annotation_compound)
            self.db_session.flush()

        self.db_session.flush()

class ImportCompoundsFromCSV(CompoundTask):

    methods = ["RPOS_PPR", "LPOS_PPR", "LNEG_PPR", "RNEG_PPR", "HPOS_PPR", "BANEG_PPR", "LC-QqQ Bile Acids_TargetLynx",
               "LC-QqQ Amino Acids_TargetLynx", "LC-QqQ Tryptophan_TargetLynx", "LC-QqQ Oxylipins_TargetLynx",
               "NOESY_BI-QUANT", "NOESY_BI-LISA"]

    def __init__(self,input_file=None,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)
        self.input_file = input_file
        self.args['input_file'] = input_file

    def load_data(self):

        self.dataset = self.load_tabular_file(self.input_file)

    def loop_and_map_data(self):

        row_index = 0
        while row_index < len(self.dataset.iloc[:,0]):

            if self.dataset.loc[row_index,'inchi']:
                compound = self.db_session.query(Compound).filter(Compound.inchi==self.dataset.loc[row_index,'inchi']).first()
            #else:
            #    compound = self.db_session.query(Compound).filter(Compound.name == self.dataset.loc[row_index, 'name'],
            #                                                      Compound.chemical_formula == self.dataset.loc[row_index, 'chemical_formula']
            #                                                      ).first()
                if not compound:
                    compound = Compound(inchi=self.dataset.loc[row_index,'inchi'],
                                        inchi_key=self.dataset.loc[row_index,'inchi_key'],
                                        chemical_formula=self.dataset.loc[row_index, 'chemical_formula'],
                                        name=self.dataset.loc[row_index, 'name'],
                                        iupac=self.dataset.loc[row_index, 'iupac'],
                                        smiles=self.dataset.loc[row_index, 'smiles'],
                                        )
                    self.db_session.add(compound)

                if not compound.log_p:
                    compound.set_log_p_from_rdkit()

                self.db_session.flush()

                self.add_or_update_pubchem_from_api(compound)
                self.add_or_update_chembl(compound)
                self.add_or_update_chebi(compound)
                self.add_or_update_hmdb(compound)
                self.add_or_update_kegg(compound)
                self.add_cas_from_hmdb(compound)
                self.add_or_update_classyfire(compound)
                self.add_or_update_lipid_maps(compound)

                for method in self.methods:

                    if method in self.dataset.columns:
                        cpd_name = self.dataset.loc[row_index,method]
                        splitted = method.split("_")
                        assay_name = splitted[0]
                        annotation_method_name = splitted[1]
                        assay = self.db_session.query(Assay).filter(Assay.name==assay_name).first()
                        annotation_method = self.db_session.query(AnnotationMethod).filter(AnnotationMethod.name==annotation_method_name).first()
                        annotation = self.db_session.query(Annotation).filter(Annotation.assay_id==assay.id,
                                                                              Annotation.annotation_method_id==annotation_method.id,
                                                                              Annotation.cpd_name==cpd_name).first()
                        if not annotation:
                            annotation = Annotation(assay_id=assay.id,
                                                    annotation_method=annotation_method.id,
                                                    cpd_name=cpd_name)
                            self.db_session.add(annotation)
                            self.db_session.flush()

                        annotation_compound = self.db_session.query(AnnotationCompound).filter(AnnotationCompound.annotation_id==annotation.id,
                                                                                              AnnotationCompound.compound_id==compound.id).first()

                        if not annotation_compound:
                            annotation_compound = AnnotationCompound(compound_id=compound.id,
                                                                     annotation_id=annotation.id)
                            self.db_session.add(annotation_compound)
                            self.db_session.flush()


            row_index = row_index + 1

class ExportCompoundsToCSV(CompoundTask):
    """Export Compounds To CSV Class

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    column_headers = ["name","chemical_formula","monoisotopic_mass","inchi","inchi_key","iupac","smiles","CAS","ChEBI",
                      "ChEMBL","ChemSpider","HMDB","LipidMAPS","LipidMapsSubClass","LipidBank","KEGG","PubChem CID"]

    default_methods = ["RPOS_PPR","LPOS_PPR","LNEG_PPR","RNEG_PPR","HPOS_PPR","BANEG_PPR","LC-QqQ Bile Acids_TargetLynx","LC-QqQ Amino Acids_TargetLynx","LC-QqQ Tryptophan_TargetLynx","LC-QqQ Oxylipins_TargetLynx","NOESY_BI-QUANT","NOESY_BI-LISA"]

    def __init__(self,methods=None,username=None,task_run_id=None,output_file_path=None,annotation_config_field=None,db_env=None,
                 db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):
        """Constructor

        :param methods: List of methods to export Compounds from, defaults to None
        :type methods: list, optional
        """        

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)

        self.args['methods'] = methods
        self.args['output_file_path'] = output_file_path
        self.args['annotation_config_field'] = annotation_config_field

        if methods and not isinstance(methods,list):
            raise Exception('methods must be a list')
        elif methods and isinstance(methods,list):
            self.column_headers = self.column_headers + methods
        else:
            self.column_headers = self.column_headers + self.default_methods
            methods = self.default_methods

        self.annotation_config_field = annotation_config_field
        if isinstance(self.annotation_config_field,str):
            for method in methods:
                self.column_headers.append(method + "_" + self.annotation_config_field)

        if output_file_path:
            self.output_file_path = output_file_path


        self.get_class_name(self)

    def build_row(self,compound):
        """Build a row from a Compound

        :param compound: Compound to build a row from
        :type compound: `phenomedb.models.Compound`
        """        

        harmonised_annotations = self.db_session.query(HarmonisedAnnotation).join(Annotation,AnnotationCompound) \
            .filter(AnnotationCompound.compound_id==compound.id) \
            .all()

        if len(harmonised_annotations) > 0:

            append_row = False

            row_dict = {'name': compound.name,
                        'chemical_formula': compound.chemical_formula,
                        'monoisotopic_mass': compound.monoisotopic_mass,
                        'inchi': compound.inchi,
                        'inchi_key': compound.inchi_key,
                        'iupac': compound.iupac,
                        'smiles': compound.smiles,
                        }

#            lipidclass = self.db_session.join

            for compound_external_db in compound.external_dbs:
                if compound_external_db.external_db is not None:
                    if compound_external_db.external_db.name in self.column_headers:
                        row_dict[compound_external_db.external_db.name] = compound_external_db.database_ref

            for harmonised_annotation in harmonised_annotations:
                col_name = harmonised_annotation.assay.name + "_" + harmonised_annotation.annotation_method.name
                if col_name in self.column_headers:
                    row_dict[col_name] = harmonised_annotation.cpd_name
                    append_row = True
                    if isinstance(self.annotation_config_field,str) and harmonised_annotation.assay.platform.name == 'MS' and harmonised_annotation.assay.targeted == 'N':
                        if len(harmonised_annotation.annotations) > 0:
                            row_dict[col_name + "_" + self.annotation_config_field] = self.find_in_config(self.annotation_config_field,harmonised_annotation,0)

            if append_row:
                self.dataset = self.dataset.append(pd.Series(row_dict),ignore_index=True)

    def find_in_config(self,field_name,harmonised_annotation,depth):

        annotation = harmonised_annotation.annotations[depth]
        if annotation.config is not None:
            if isinstance(annotation.config,dict):
                config_dict = dict(annotation.config)
            elif isinstance(annotation.config,str):
                #config_dict = json.load(annotation.config)
                config_dict = {}
                config_array = annotation.config.split("\n")
                for config_element in config_array:
                    if re.search(field_name,config_element):
                        config_dict[field_name] = config_element.replace(" ","").replace(field_name,"")
                        break
            else:
                raise Exception("Unknown type %s" % type(annotation.config))
            if field_name in config_dict.keys():
                field_value = config_dict[field_name]
            else:
                raise Exception("Field not found %s" % field_name)
        elif len(harmonised_annotation.annotations) == depth + 2:
            field_value = self.find_in_config(field_name,harmonised_annotation,depth+1)
        else:
            field_value = None
        return field_value

    def build_dataset(self):
        """Build the dataset from the compounds
        """        

        self.compounds = self.db_session.query(Compound).order_by(Compound.name).all()

        #index = []
        #for compound in self.compounds:
        #    index.append(compound.id)

        self.dataset = pd.DataFrame(data=None,columns=self.column_headers)

        for compound in self.compounds:

            self.build_row(compound)

    def process(self):
        """Export all the compounds in the db
        """

        # Get all the compounds - for each compound write out

        self.build_dataset()

        if not self.output_file_path:
            self.output_file_path = '%soutput/phenomedb_compound_export_%s.csv' % (config['DATA']['APP_DATA'],datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S'))

        self.dataset.to_csv(self.output_file_path,index=False)



class ParseHMDBXMLtoCSV(CompoundTask):
    """Parse HMDB XML to CSV, used for simpler lookups

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    def __init__(self,input_file_path=None,output_file_path=None,hmdb_type=None,username=None,task_run_id=None,pipeline_run_id=None,upstream_task_run_id=None):
        """Constructor

        :param input_file_path: The input HMDB file path, defaults to None
        :type input_file_path: str, optional
        :param output_file_path: The output HMDB file path , defaults to None
        :type output_file_path: str, optional
        :param hmdb_type: The class of metabolites to parse, defaults to None
        :type hmdb_type: str, optional
        """        

        super().__init__(username=username,task_run_id=task_run_id,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)

        if input_file_path:
            self.input_file_path = str(Path(input_file_path).absolute())
        else:
            self.input_file_path = None

        if output_file_path:
            self.output_file_path = str(Path(output_file_path).absolute())
        else:
            self.output_file_path = config['DATA']['compounds'] + "/hmdb_parsed.csv"

        if hmdb_type:
            self.hmdb_type = hmdb_type
        else:
            self.hmdb_type = 'hmdb_metabolites'

        self.args['input_file_path'] = input_file_path
        self.args['output_file_path'] = output_file_path
        self.args['hmdb_type'] = hmdb_type
        self.get_class_name(self)

    def reset_found_fields(self):
        """Resets the fields when they are found

        :return: found field dictionary
        :rtype: dict
        """        

        return {'name':False,'accession':False,'accession_2':False,'accession_3':False,'accession_4':False,
                'accession_5':False,'accession_6':False,'accession_7':False,'accession_8':False,'accession_9':False,'kingdom':False,
                'accession_10':False,'inchi':False,'inchikey':False,'cas_registry_number':False,"SMILES":False,'direct_parent':False,'super_class':False,'class':False,'sub_class':False}

    def download_file(self):
        """Downloads the HMDB file
        """        
        
        zip_file = self.hmdb_type + '.zip'
        r = requests.get('https://hmdb.ca/system/downloads/current/' + self.hmdb_type + ".zip",stream=True)
        self.zip_path = '/tmp/' + zip_file

        with open(self.zip_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=1024):
                fd.write(chunk)

        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall('/tmp')

        self.input_file_path = '/tmp/' + self.hmdb_type + '.xml'


    def process(self):
        """Main method. Downloads file or uses cache, then loops and builds a CSV
        """

        if not self.input_file_path:
            self.download_file()

        metabolite_number = 0

        df = pd.DataFrame(columns=['HMDB Primary ID','InChI','inchi_key','common_name','cas_registry_number','SMILES','kingdom','direct_parent','super_class','class','sub_class','hmdb_id_2','hmdb_id_3','hmdb_id_4','hmdb_id_5','hmdb_id_6','hmdb_id_7','hmdb_id_8','hmdb_id_9','hmdb_id_10'])

        #found_fields = {'name':False,'accession':False,'secondary_accession':False,'InChI':False,'InChIKey':False}
        found_fields = self.reset_found_fields()
        #total_metabolites = 10
        total_metabolites = 150000

        for event, elem in ET.iterparse(self.input_file_path, events=("start", "end")):

            #¢if metabolite_number == 2 and elem.tag == '{http://www.hmdb.ca}inchi':
            #if metabolite_number == 532:
            #    bp = True

            # primary accession
            if elem.tag == "{http://www.hmdb.ca}accession" and not found_fields['accession'] and elem.text:
                df.loc[metabolite_number,'HMDB Primary ID'] = elem.text
                found_fields['accession'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession'] and not found_fields['accession_2'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_2'] = elem.text
                found_fields['accession_2'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_2'] and not found_fields['accession_3'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_3'] = elem.text
                found_fields['accession_3'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_3'] and not found_fields['accession_4'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_4'] = elem.text
                found_fields['accession_4'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_4'] and not found_fields['accession_5'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_5'] = elem.text
                found_fields['accession_5'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_5'] and not found_fields['accession_6'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_6'] = elem.text
                found_fields['accession_6'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_6'] and not found_fields['accession_7'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_7'] = elem.text
                found_fields['accession_7'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_7'] and not found_fields['accession_8'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_8'] = elem.text
                found_fields['accession_8'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_8'] and not found_fields['accession_9'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_9'] = elem.text
                found_fields['accession_9'] = True
            elif elem.tag == "{http://www.hmdb.ca}accession" and found_fields['accession_9'] and not found_fields['accession_10'] and elem.text:
                df.loc[metabolite_number,'hmdb_id_10'] = elem.text
                found_fields['accession_10'] = True

            elif elem.tag == "{http://www.hmdb.ca}inchi" and not found_fields['inchi'] and elem.text:
                df.loc[metabolite_number,'InChI'] = elem.text
                found_fields['inchi'] = True
                print(elem.text)
            elif elem.tag == "{http://www.hmdb.ca}inchikey" and not found_fields['inchikey'] and elem.text:
                df.loc[metabolite_number,'inchi_key'] = elem.text
                found_fields['inchikey'] = True

            elif elem.tag == "{http://www.hmdb.ca}name" and event and not found_fields['name'] and elem.text:
                df.loc[metabolite_number,'common_name'] = elem.text
                found_fields['name'] = True

            elif elem.tag == "{http://www.hmdb.ca}inchi" and not found_fields['inchi'] and elem.text:
                df.loc[metabolite_number,'InChI'] = elem.text
                found_fields['inchi'] = True

            elif elem.tag == "{http://www.hmdb.ca}smiles" and not found_fields['SMILES'] and elem.text:
                df.loc[metabolite_number,'SMILES'] = elem.text
                found_fields['SMILES'] = True

            elif elem.tag == "{http://www.hmdb.ca}cas_registry_number" and not found_fields['cas_registry_number'] and elem.text:
                df.loc[metabolite_number,'cas_registry_number'] = elem.text
                found_fields['cas_registry_number'] = True

            elif elem.tag == "{http://www.hmdb.ca}direct_parent" and not found_fields['direct_parent'] and elem.text:
                df.loc[metabolite_number,'direct_parent'] = elem.text
                found_fields['direct_parent'] = True

            elif elem.tag == "{http://www.hmdb.ca}super_class" and not found_fields['super_class'] and elem.text:
                df.loc[metabolite_number,'super_class'] = elem.text
                found_fields['super_class'] = True

            elif elem.tag == "{http://www.hmdb.ca}kingdom" and not found_fields['kingdom'] and elem.text:
                df.loc[metabolite_number,'kingdom'] = elem.text
                found_fields['kingdom'] = True

            elif elem.tag == "{http://www.hmdb.ca}class" and not found_fields['class'] and elem.text:
                df.loc[metabolite_number,'class'] = elem.text
                found_fields['class'] = True

            elif elem.tag == "{http://www.hmdb.ca}sub_class" and not found_fields['sub_class'] and elem.text:
                df.loc[metabolite_number,'sub_class'] = elem.text
                found_fields['direct_parent'] = True

            elif elem.tag == "{http://www.hmdb.ca}metabolite" and event == "end":
                metabolite_number = metabolite_number + 1
                found_fields = self.reset_found_fields()
                print("Parsing metabolite: " + str(metabolite_number) + "/" + str(total_metabolites))

            elem.clear()

            if metabolite_number > total_metabolites:
                break

        df.to_csv(self.output_file_path)
        print("File written: " + self.output_file_path)


class ParseKEGGtoPubchemCIDTask(CompoundTask):
    """This task parses KEGG and builds a dataframe of KEGGID -> Pubchem CID lookups

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    kegg_rest_base_url = "http://rest.kegg.jp/conv/pubchem/cpd:"
    kegg_brite_download_base_url = "https://www.genome.jp/kegg-bin/download_htext?htext=br"
    kegg_brite_codes = {
        'Compounds with biological roles': '08001',
        'Lipids':'08002',
        'Phytochemical compounds':'08003',
        'Glycosides':'08021',
        'Bioactive peptides':'08005',
        'Endocrine disrupting compounds':'08006',
        'Pesticides':'08007',
        'Carcinogens':'08008',
        'Natural toxins':'08009',
        'Target-based classification of compounds':'08010',
    }
    pubchem_rest_base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/sid/"
    kegg_compound_ids = []

    output = pd.DataFrame(columns=['KEGG','Pubchem SID','Pubchem CID'])

    def __init__(self,output_file_path=None, compound_type=None, test=False,task_run_id=None,username=None,pipeline_run_id=None,upstream_task_run_id=None):

        super().__init__(username=username,task_run_id=task_run_id,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)
        self.output_file_path = str(Path(output_file_path).absolute())

        if compound_type:
            if compound_type not in self.kegg_brite_codes.keys():
                raise Exception("compound_type not in allowed list - " + str(self.kegg_brite_codes.keys()))
            self.compound_type = compound_type
        else:
            self.compound_type = None

        self.test = test

        self.args['output_file_path'] = output_file_path
        self.args['compound_type'] = compound_type
        self.args['test'] = test
        self.get_class_name(self)

    def process(self):
        """Main method
        """        

        # KEGG returns pubchem SID.
        # Use Pubchem SID to find Pubchem CID

        #"https://www.genome.jp/kegg-bin/download_htext?htext=br08001.keg&format=json&filedir="
        # for each brite entry, get the json, parse this, loop over each compound.
        # check if the compound has already been parsed. if not.
        # get the pubchem sid.
        # then lookup pubchem cid

        self.extract_kegg_ids()
        total = len(self.kegg_compound_ids)
        index = 0
        for kegg_id in self.kegg_compound_ids:
            try:
                pubchem_sid = self.get_pubchem_sid(kegg_id)
                pubchem_cid = self.get_pubchem_cid(pubchem_sid)
                print(str(index) + "/" + str(total) + " KEGG:" + str(kegg_id) + " Pubchem SID:" + str(pubchem_sid) + " Pubchem CID:" + str(pubchem_cid))
            except Exception as err:
                print("KEGG:" + str(kegg_id))
                print(err)

            self.output.loc[index,"KEGG"] = kegg_id
            self.output.loc[index,"Pubchem SID"] = pubchem_sid
            self.output.loc[index,"Pubchem CID"] = pubchem_cid

            time.sleep(0.1)

            index += 1

        self.output.to_csv(self.output_file_path)
        print("File written: " + self.output_file_path)

    def extract_kegg_ids(self):
        """Extracts the KEGG IDs from the brite codes
        """        

        if self.compound_type:
            self.parse_kegg_compound_class(self.kegg_brite_codes[self.compound_type])
        else:
            for compound_type,brite_code in self.kegg_brite_codes.items():
                self.parse_kegg_compound_class(brite_code)

        self.kegg_compound_ids.sort()

    def parse_kegg_compound_class(self,brite_code):
        """Parse a KEGG compound class by brite code

        :param brite_code: The code to search with
        :type brite_code: str
        """        

        url = self.kegg_brite_download_base_url + brite_code + ".keg&format=json&filedir="
        response_json = requests.get(url).content.decode("utf-8").strip('\n\t')
        try:
            response = json.loads(response_json.decode("utf-8","ignore"))
        except Exception as err:
            self.logger.exception(err)
            response = None
        if response:
            self.loop_into_brite_fields(response)

    def loop_into_brite_fields(self,element):
        """Recurse into brite fields to extract all required parameters

        :param element: element to recurse into
        :type element: object
        """        

        if isinstance(element, dict) and 'children' in element:
            self.loop_into_brite_fields(element['children'])
            if self.test:
                return
        elif isinstance(element, dict) and 'name' in element:
            self.extract_and_set_compound_id(element['name'])
            if self.test:
                # exit out once one is processed
                return
        elif isinstance(element, list):
            for elem in element:
                self.loop_into_brite_fields(elem)
                if self.test:
                    return

    def extract_and_set_compound_id(self,name):
        """Extract KEGG ID from name

        :param name: KEGG element name
        :type name: str
        """        

        split_list = name.split(" ")
        kegg_id = split_list[0]

        if kegg_id not in self.kegg_compound_ids and kegg_id.find("C") == 0:
            self.kegg_compound_ids.append(kegg_id)

    def get_pubchem_sid(self,kegg_id):
        """Get pubchem SID from kegg id

        :param kegg_id: KEGG ID
        :type kegg_id: str
        :return: Pubchem SID
        :rtype: str
        """        

        try:
            url = self.kegg_rest_base_url + str(kegg_id)
            response = str(requests.get(url).content)
            response_split = response.split("pubchem:")
            raw_sid = response_split[1]
            regmatch = re.search("[0-9]+", raw_sid)
            pubchem_sid = raw_sid[regmatch.start():regmatch.end()]
            return pubchem_sid
        except Exception as err:
            self.logger.exception(err)
            return None
        

    def get_pubchem_cid(self,pubchem_sid):
        """Get pubchem CID from pubchem SID

        :param kegg_id: Pubchem SID
        :type kegg_id: str
        :return: Pubchem CID
        :rtype: str
        """        
        try:
            url = self.pubchem_rest_base_url + str(pubchem_sid) + "/json"
            response = requests.get(url).content
            response_json = json.loads(response.decode("utf-8","ignore"))
            pubchem_cid = None
            if "PC_Substances" in response_json:
                if len(response_json['PC_Substances']) > 0:
                    substance = response_json['PC_Substances'][0]
                    for compound in substance['compound']:
                        if 'id' in compound:
                            if 'id' in compound['id']:
                                if 'cid' in compound['id']['id']:
                                    pubchem_cid = str(compound['id']['id']['cid'])

            return pubchem_cid
        except Exception as err:
            self.logger.exception(err)
            return None


class UpdateCompoundRefs(CompoundTask):
    """Update the Compound properties and external references from the InChI lookups

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """    

    def __init__(self,username=None,task_run_id=None,pipeline_run_id=None,upstream_task_run_id=None):
        """Constructor
        """        

        super().__init__(username=username,task_run_id=task_run_id,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)
        self.get_class_name(self)

    def load_data(self):
        """Load the data
        """        

        super().load_data()
        self.compounds = self.db_session.query(Compound).filter(Compound.inchi_key != "Unknown") \
            .order_by('id').all()

    def loop_and_map_data(self):
        """Loop over compounds and update the references
        """        
        
        count = 0
        total = len(self.compounds)

        for compound in self.compounds:

            print("Compound " + str(count) + "/" + str(total))
            print(str(compound))

            pubchem_cid = self.add_or_update_pubchem_from_api(compound,lookup_field='inchi',lookup_term=compound.inchi)
            refmet_name = self.update_name_to_refmet(compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
            refmet_name = self.add_or_update_refmet_name(compound,inchi_key=compound.inchi_key)
            lm_id = self.add_or_update_lipid_maps(compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
            chebi_id = self.add_or_update_chebi(compound)
            hmdb_id = self.add_or_update_hmdb(compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
            chembl_id = self.add_or_update_chembl(compound)
            cas_id = self.add_cas_from_hmdb(compound,lookup_field='inchi_key',lookup_value=compound.inchi_key)
            cas_id = self.add_or_update_classyfire(compound)

            if pubchem_cid:
                kegg_id = self.add_or_update_kegg(compound=compound,pubchem_cid=pubchem_cid)

            count = count + 1


class AddMissingClassyFireClasses(CompoundTask):
    """Update the Compound properties and external references from the InChI lookups

    :param CompoundTask: The Base CompoundTask
    :type CompoundTask: `phenomedb.compounds.CompoundTask`
    """

    def __init__(self, username=None, task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):
        """Constructor
        """

        super().__init__(username=username, task_run_id=task_run_id,db_env=db_env,
                         db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)
        self.get_class_name(self)

    def load_data(self):
        """Load the data
        """

        super().load_data()
        # Get the compounds with no classyfire classes
        self.compounds = self.db_session.query(Compound).all()

    def loop_and_map_data(self):
        """Loop over compounds and update the references
        """

        count = 0
        total = len(self.compounds)

        for compound in self.compounds:

            print("Compound " + str(count) + "/" + str(total))
            print(str(compound))

            self.add_or_update_classyfire(compound)

            time.sleep(5)
            count = count + 1


class ImportStandardsV1(CompoundTask):

    def __init__(self,standards_file=None,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,pipeline_run_id=None,upstream_task_run_id=None):

        self.standards_file = standards_file

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,pipeline_run_id=pipeline_run_id,upstream_task_run_id=upstream_task_run_id)

    def load_data(self):

        super().load_data()

        self.standards = self.load_tabular_file(self.standards_file)

    def loop_and_map_data(self):
        row_index = 0
        while row_index < self.standards.shape[0]:
            compound = None
            row = self.standards.iloc[row_index,:]
            print(row_index)
            print(row)
            if row['inchi'] != 'Unknown':
                compound = self.db_session.query(Compound).filter(Compound.inchi==row['inchi']).first()

            if not compound:
                compound = self.db_session.query(Compound).filter(Compound.name==row['name']).first()

            if not compound:
                inchi = None
                if row['inchi'] and row['inchi'] != 'Unknown':
                    inchi = row['inchi']
                compound = Compound(name=row['name'],
                                    inchi=inchi,
                                    monoisotopic_mass=row['monoisotopic_mass'],
                                    smiles=row['smiles']
                            )
                if inchi:
                    compound.set_inchi_key_from_rdkit()
                if compound.inchi_key:
                    compound.set_log_p_from_rdkit()
                self.db_session.add(compound)
                self.db_session.flush()

                self.add_or_update_pubchem_from_api(compound)
                self.add_or_update_chebi(compound)
                self.add_or_update_chembl(compound)
                self.add_or_update_hmdb(compound)
                self.add_or_update_kegg(compound)
                self.add_or_update_lipid_maps(compound)
                self.add_or_update_classyfire(compound)

            assay = self.db_session.query(Assay).filter(Assay.name==row['name-2']).first()

            if not assay:
                print(row['name-2'])
                break
            chemical_standard_dataset = self.db_session.query(ChemicalStandardDataset).filter(ChemicalStandardDataset.compound_id==compound.id,
                                                                                              ChemicalStandardDataset.source_file==row['source_file']).first()

            if not chemical_standard_dataset:
                acquired_date = None
                if row['acquired_date']:
                    acquired_date = utils.get_date(row['acquired_date'])
                chemical_standard_dataset = ChemicalStandardDataset(collision_energy=row['collision_energy'],
                                                                acquired_date=acquired_date,
                                                                source_file=row['source_file'],
                                                                supplier=row['supplier'],
                                                                exhausted=row['exhausted'],
                                                                ph=row['ph'],
                                                                assay_id=assay.id,
                                                                compound_id=compound.id)

                self.db_session.add(chemical_standard_dataset)
                self.db_session.flush()

            chemical_standard_peaklist = self.db_session.query(ChemicalStandardPeakList).filter(ChemicalStandardPeakList.chemical_standard_dataset_id==chemical_standard_dataset.id,
                                                                                                ChemicalStandardPeakList.mz==row['mz'],
                                                                                                ChemicalStandardPeakList.rt_seconds==row['rt_seconds'])

            if not chemical_standard_peaklist:
                chemical_standard_peaklist = ChemicalStandardPeakList(mz=row['mz'],
                                                                      rt_seconds=row['rt_seconds'],
                                                                      intensity=row['intensity'],
                                                                      drift=row['drift'],
                                                                      peak_width=row['peak_width'],
                                                                      resolution=row['resolution'],
                                                                      seed=row['seed'],
                                                                      validated=row['validated'],
                                                                      ion=row['ion'],
                                                                      chemical_standard_dataset_id=chemical_standard_dataset.id)
                self.db_session.add(chemical_standard_peaklist)
                self.db_session.flush()

            row_index = row_index + 1

#class FixClassyFireClasses(CompoundTask):

   # def process(self):

    #    compounds = self.db_session.query(Compound).filter(Compound.inchi.not_in(['Unknown',None]).all()

     #   for compound in compounds:c

