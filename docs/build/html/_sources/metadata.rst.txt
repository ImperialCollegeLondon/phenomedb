.. _metadata:

phenomedb.metadata
==================

Metadata in PhenomeDB generally refers to clinical or sample-level variables, such as age, sex, BMI, etc.

As the purpose of PhenomeDB is to be able to integrate and stratify data across multiple projects or studies, this metadata must be harmonised prior to it usage.

The process for harmonisation of metadata is:

1. Import the metadata using the ImportMetadata task, specifying any columns you wish to ignore (for example sensitive data).
2. The ImportMetadata task imports the data to the metadata_field and metadata_value tables.
3. Create or identity existing Harmonised Metadata Fields for the fields you wish to harmonise.
4. For each metadata field, run the CurateMetadata task, selecting either an in-built metadata curation function, or define a python lambda that will curate the raw value to the required curated/harmonised value.

Once harmonised, the fields can then be used in integration and stratification queries via the QueryFactory.

Overview of the HarmoniseMetadataField task
-------------------------------------------

.. figure:: ./_images/curate-metadata-task.png
  :width: 600
  :alt: PhenomeDB HarmoniseMetadataField task

  The HarmoniseMetadataField architecture, with methods for harmonising types, names, and values

.. automodule:: phenomedb.metadata
   :members:
