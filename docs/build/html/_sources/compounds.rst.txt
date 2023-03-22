phenomedb.compounds
===================

PhenomeDB enables the storage of annotation metadata such as chemical references and classes, and has a data model and import processes capable of harmonising annotations to their analytical specificity.

The minimum information required for import is compound name (as annotated) and InChI (if available). If the specificity of the annotation is low, multiple compounds and InChIs can be recorded per annotation. With this minimum information, PhenomeDB can lookup and record the following external references and classes and make them queryable and reportable.

Databases: PubChem, ChEBI, ChEMBL, ChemSpider, LipidMAPS, HMDB

Classes: LipidMAPS, HMDB, ClassyFIRE

.. figure:: ./_images/compound-task-overview.png
  :width: 600
  :alt: PhenomeDB ImportCompoundTask overview

  The ImportCompoundTask overview, which looks up compound metadata and populates the database

Compound metadata can be imported from PeakPantheR region-of-interest files (ROI) files for LC-MS annotations. Recent versions for these can be found in ./phenomedb/data/compounds/.

To import the ROI compound data use the tasks ImportROICompounds and ImportROILipids

IVDr annotation metadata can be imported using ImportBrukerBiLISACompounds and ImportBrukerBiQuantCompounds,. The source data are available in ./phenomedb/data/compounds/

Once imported, compounds and compound classes can be explored using the Compound View UI.

.. figure:: ./_images/compound-list-view.png
  :width: 600
  :alt: PhenomeDB Compound List View

  The Compound List View, showing a searchable, paginated table of imported compounds

.. figure:: ./_images/compound-view-example.png
  :width: 600
  :alt: PhenomeDB Compound View

  The Compound View, showing the imported information for one compound, with links to external databases

.. list-table:: Title
   :widths: 50 50
   :header-rows: 1


.. automodule:: phenomedb.compounds
   :members:
