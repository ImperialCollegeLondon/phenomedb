phenomedb.query_factory
=======================

Creating queries can be done either via the Query Factory view or the QueryFactory Python API. In PhenomeDB Queries are created by chaining QueryFilter objects containing boolean operators and QueryMatches, which specifying the fields and comparison operators and values. An overview of this can be seen below. With the collection of QueryFilters and QueryMatches, the QueryFactory then calculates/transpiles the query definition into an SQLAlchemy query, and executes the query. The QueryFactory can then construct a combined-format and 3-file format dataset of the results, and store them in the PhenomeDB Cache, an extended version of Redis that enables file-system persistency of objects. Generating the dataframes can currently take a long time depending on the number of records the query returns, for this reason once the query has been defined the user should run the CreateSavedQueryDataframeCache task to execute the query and set it into the cache. This can be run manually via the interface or via the QueryFactory UI.

.. figure:: ./_images/query-filters-overview.png
  :width: 600
  :alt: PhenomeDB QueryFactory QueryFilters and QueryMatches

  The QueryFilter and QueryMatch architecture. Multiple QueryFilters can be added, each with AND or OR boolean operators. Each QueryFilter can have multiple QueryMatches, targeting a specific Model.property, with a specific comparison operator and value.

An example of using these to construct a query is shown below.

.. code-block:: python

    # Instantiate the QueryFactory
    query_factory = QueryFactory(query_name='Users under 40', query_description='test description')

    # Add a filter with the match properties added in the constructor (default 'AND')
    query_factory.add_filter(model='Project', property='name', operator='eq', value='My Project')

    # Create another filter with the match properties added in the constructor
    filter = QueryFilter(model='HarmonisedMetadataField',property='name',operator='eq', value='Age')

    # Add another match to the filter
    filter.add_match(model='MetadataValue',property='harmonised numeric value',operator='lt', value=40)

    # Add the filter to the query factory (default 'AND')
    query_factory.add_filter(query_filter=filter)

    #4. Save the query in the SavedQuery data model
    query_factory.save_query()

    #5. Generate the summary statistics
    query_factory.calculate_summary_statistics()

    #6. Execute the query, build the 3-file format, load into cache, and return dataframes
    intensity_data = query_factory.load_dataframe('intensity_data',harmonise_annotations=True)
    sample_metadata = query_factory.load_dataframe('sample_metadata',harmonise_annotations=True)
    feature_metadata = query_factory.load_dataframe('feature_metadata',harmonise_annotations=True)

To simplify querying HarmonisedMetadataFields, the following MetadataFilter can be used

.. code-block:: python

    # Instantiate the QueryFactory
    query factory = QueryFactory(query_name='Users under 40', query_description='test description')

    # Add a filter with the match properties added in the constructor (default 'AND')
    query factory.add_filter(QueryFilter(model='Project',property='name',operator='eq',value='My Project'))

    # Add a Metadata filter with the match properties added in the constructor (default 'AND')
    query factory.add_filter(MetadataFilter('Age','lt',value=40))

    #4. Save the query in the SavedQuery data model
    query factory.save_query()

    #5. Generate the summary statistics
    query_factory.calculate_summary_statistics()

    #6. Execute the query, build the 3-file format, load into cache, and return dataframes
    intensity_data = query_factory.load_dataframe('intensity_data',harmonise_annotations=True)
    sample_metadata = query_factory.load_dataframe('sample_metadata',harmonise_annotations=True)
    feature_metadata = query_factory.load_dataframe('feature_metadata',harmonise_annotations=True)


SavedQueries can be created and explored using the QueryFactory user interface. Through the interface the summary statistics for the query can be visually explored to assess the composition of the generated cohort. Once you are happy with the composition you should then execute the CreateSavedQueryDataframeCache task for the SavedQuery to build the query dataframes and store them in the Cache.

.. figure:: ./_images/query-ui-create.png
  :width: 650
  :alt: PhenomeDB QueryFactory UI create

  Creating a SavedQuery using the UI.

.. figure:: ./_images/query-summary-stats-example.png
  :width: 500
  :alt: PhenomeDB QueryFactory summary stats

  The QueryFactory summary stats output.

.. figure:: ./_images/query-ui-generate-cache-buttons.png
  :width: 650
  :alt: PhenomeDB generate cache

  Buttons to trigger a CreateSavedQueryDataframe task via the QueryFactory UI

.. figure:: ./_images/query-ui-download-dataframe.png
  :width: 500
  :alt: PhenomeDB QueryFactory download options

  QueryFactory options for downloading a dataframe. Options include the ability to bin harmonised metadata fields, include or exclude specific columns, and specify the output format.


Query dict structure:

.. code-block:: python

  query_dict = { 'model': str
                  'joins':[str,str],
                  'filters': [{ 'filter_operator': str,
                                'matches': [{  'model': str,
                                                'property': str,
                                                "operator": str,
                                                'value': str, float, list
                                            }]
                              }]
                }

query_dict['model']: The model object to return
query_dict['joins']: The list of models to join
query_dict['filters'] : The list of 'filters'.
query_dict['filters']['filter_operator]: The type of filter - 'AND', 'OR'
query_dict['filters']['matches']: A list of 'matches'
query_dict['filters']['matches']['model']: The name of the model to match against.
query_dict['filters']['matches']['property']: The name of the property to match against.
query_dict['filters']['matches']['operator']: The operator to use - 'eq','not_eq','gt','lt','gte','lte','between','not_between','in','not_in','like','not_like','ilike','not_ilike'
query_dict['filters']['matches']['value']: The value to match on. Must be of expected type - ie str, float, [0,1] (for between) or [0,N] (for in or in)

Example usage:

Creating and saving new query with the following structure:

.. code-block:: python
      
  query_dict = { 'model': 'Sample',
                  'joins':['Subject','Project','MetadataValue','MetadataField','HarmonisedMetadataField'],
                  'filters': [{
                      'filter_operator': 'OR',
                      'matches': [{
                              'model': 'Project',
                              'property':'name',
                              'operator': 'eq',
                              'value': 'PipelineTesting',
                      }]
                  },{
                  'filter_operator': 'AND',
                  'matches': [{
                          'model': 'HarmonisedMetadataField',
                          'property': 'name',
                          "operator": 'eq',
                          'value': 'Age',
                      },
                      {
                          'model': 'MetadataValue',
                          'property': 'harmonised_numeric_value',
                          "operator": 'in',
                          'value': ["30","35","40"]
                      }]
                  }]
                }

  query_factory = CohortQuery()

  filter = QueryFilter(filter_operator='AND')
  filter.add_match(model='Project',property='name',operator='eq',value='PipelineTesting')
  query_factory.add_filter(query_filter=filter)

  filter = QueryFilter(filter_operator='AND')
  filter.add_match(model='HarmonisedMetadataField',property='name',operator='eq',value='Age')
  filter.add_match(model='MetadataValue',property='harmonised_numeric_value',operator='in',value=[30,40,50])
  query_factory.add_filter(query_filter=filter)

  query = query_factory.save()

  query_retrieved_from_db = db_session.query(CohortQuery).filter(CohortQuery.id==query.id).first()
  query_factory_retrieved = CohortQuery(query=query_retrieved_from_db)
  rows = query_factory_retrieved.get_query_rows()


Example queries and query_dicts:

All Samples from PipelineTesting project

.. code-block:: python

  query = db_session.query(Sample).join(Subject,Project).filter(Project.name=='PipelineTesting')

  query_dict = {  'model': 'Sample',
                  'joins':['Subject','Project'],
                  'filters': [{
                                  'filter_operator': 'AND',
                                  'matches': [{
                                              'model': 'Project',
                                              'property': 'name',
                                              "operator": 'eq',
                                              'value': 'PipelineTesting',
                                          }]
                              }]
                }

All from every project NOT PipelineTesting

.. code-block:: python

  query = db_session.query(Sample).join(Subject,Project).filter(Project.name != 'PipelineTesting')

  query_dict = {  'model': 'Sample',
                  'joins':['Subject','Project'],
                  'filters': [{
                                  'filter_operator': 'AND',
                                  'matches': [{
                                              'model': 'Project',
                                              'property': 'name',
                                              "operator": 'not_eq',
                                              'value': 'PipelineTesting',
                                          }]
                              }]
                }


All "Plasma" samples

.. code-block:: python

  query = db_session.query(Sample).filter(Sample.sample_type=='Plasma')

  query_dict = { 'model': 'Sample',
                  'joins':[],
                  'filters': [{
                                  'filter_operator': 'AND',
                                  'matches': [{
                                              'model': 'Sample',
                                              'property': 'sample_type',
                                              "operator": 'eq',
                                              'value': 'Plasma',
                                          }]
                            }]
                }


All "HPOS" samples

.. code-block:: python

  query = db_session.query(Sample).join(SampleAssay,Assay).filter(Assay.name=='HPOS')

  query_dict = {  'model': 'Sample',
                  'joins':['SampleAssay','Assay'],
                  'filters': [{
                                  'filter_operator': 'AND',
                                  'matches': [{
                                              'model': 'Assay',
                                              'property': 'name',
                                              "operator": 'eq',
                                              'value': 'HPOS',
                                          }]
                              }]
                }

All samples with subjects between ages 30 and 40

.. code-block:: python

  query = db_session.query(Sample).join(MetadataValue,MetadataField,HarmonisedMetadataField)\
      .filter(HarmonisedMetadataField.name=='Age')\
      .filter(MetadataValue.harmonised_numeric_value.between(30,40))

  query_dict = {  'model': 'Sample',
                  'joins':['MetadataValue','MetadataField','HarmonisedMetadataField'],
                  'filters': [{
                                  'filter_operator': 'AND',
                                  'matches': [{
                                              'model': 'HarmonisedMetadataField',
                                              'property': 'name',
                                              "operator": 'eq',
                                              'value': 'Age',
                                          }]
                              },
                              {
                                  'filter_operator': 'AND',
                                  'matches': [{
                                              'model': 'MetadataValue',
                                              'property': 'harmonised_numeric_value',
                                              "operator": 'between',
                                              'value': [30,40]
                                          }]
                              }]
                }

All samples with 'Glucose' annotations, with intensity > 0.3

.. code-block:: python

  query = db_session.query(Sample)\
      .join(SampleAssay,AnnotatedFeature,Annotation,AnnotationCompound,Compound)\
      .filter(Compound.name=='Glucose')\
      .filter(AnnotatedFeature.intensity > 0.3)

  query_dict = { 'model': 'Sample',
                  'joins':['SampleAssay','AnnotatedFeature','Annotation','AnnotationCompound','Compound'],
                  'filters': [{ 'filter_operator': 'AND',
                              'matches': [{
                                            'model': 'Compound',
                                            'property': 'name',
                                            "operator": 'eq',
                                            'value': 'Glucose',
                                        }]
                              },
                              { 'filter_operator': 'AND',
                                'matches': [{
                                              'model': 'AnnotatedFeature',
                                              'property': 'intensity',
                                              "operator": 'gt',
                                              'value': 0.3
                                            }]
                              },
                            ]}
                }

All samples with Pubchem CID 16217534 annotations, with intensity > 0.3

.. code-block:: python

  query = db_session.query(Sample)\
      .join(SampleAssay,AnnotatedFeature,Annotation,AnnotationCompound,Compound,CompoundExternalDB,ExternalDB)\
      .filter(ExternalDB.name=='PubChem CID')\
      .filter(CompoundExternalDB.database_ref=='16217534')\
      .filter(AnnotatedFeature.intensity > 0.3)


  query_dict = { 'model': 'Sample',
                  'joins':['SampleAssay','AnnotatedFeature','Annotation','AnnotationCompound','Compound'
                          'CompoundExternalDB','ExternalDB'],
                'filters': [{ 'filter_operator': 'AND',
                              'matches': [{
                                            'model': 'ExternalDB',
                                            'property': 'name',
                                            "operator": 'eq',
                                            'value': 'PubChem CID',
                                        }]
                              },
                              { 'filter_operator': 'AND',
                                'matches': [{
                                              'model': 'CompoundExternalDB',
                                              'property': 'database_ref',
                                              "operator": 'eq',
                                              'value': '16217534',
                                            }]

                              },
                              { 'filter_operator': 'AND',
                                'matches': [{
                                              'model': 'AnnotatedFeature',
                                              'property': 'intensity',
                                              "operator": 'gt',
                                              'value': 0.3,
                                            }]

                              },
                            ]}
                }


All samples from PipelineTesting project OR nPYc-toolbox-tutorials

.. code-block:: python

  query = db_session.query(Sample).join(Subject,Project).filter(Project.name=='PipelineTesting' | Project.name=='nPYc-toolbox-tutorials')

  query_dict = { 'model': 'Sample',
                  'joins':['Subject','Project'],
                  'filters': [{
                                  'filter_operator': 'OR',
                                  'matches': [{
                                                  'model': 'Project',
                                                  'property': 'name',
                                                  "operator": 'eq',
                                                  'value': 'PipelineTesting',
                                                },
                                                {
                                                  'model': 'Project',
                                                  'property': 'name',
                                                  "operator": 'eq',
                                                  'value': 'nPYc-toolbox-tutorials',
                                                }]
                              }]
                }

All from PipelineTesting project OR nPYc-toolbox-tutorials and with annotations with Pubchem CID ref IN ('16217534', '3082637')

.. code-block:: python

  query = db_session.query(Sample).join(Subject,Project,SampleAssay,AnnotatedFeature,\
      Annotation,AnnotationCompound,Compound,CompoundExternalDB,ExternalDB)\
      .filter(Project.name=='PipelineTesting' | Project.name=='nPYc-toolbox-tutorials')\
      .filter(ExternalDB.name=='PubChem CID' & CompoundExternalDB.database_ref.in_(['16217534','3082637'])

  query_dict = { 'model': 'Sample',
                  'joins':['Subject','Project','SampleAssay','Annotation','AnnotatedFeature',\
                          'AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                  'filters': [{
                                  'filter_operator': 'OR',
                                  'matches': [{
                                                  'model': 'Project',
                                                  'property':'name',
                                                  "operator": 'eq',
                                                  'value': 'PipelineTesting',
                                                },
                                                {
                                                  'model': 'Project',
                                                  'property': 'name',
                                                  "operator": 'eq',
                                                  'value': 'nPYc-toolbox-tutorials'
                                                }]
                              },{
                                'filter_operator': 'AND',
                                  'matches': [{
                                                  'model': 'ExternalDB'
                                                  'property': 'name',
                                                  "operator": 'eq',
                                                  'value': 'PubChem CID',
                                                },
                                                {
                                                  'model': 'CompoundExternalDB'
                                                  'property': 'database_ref',
                                                  "operator": 'in',
                                                  'value': ['16217534','3082637']
                                                }]
                              }]
                }

All annotations that a not PubChem CID ('16217534', '3082637')

.. code-block:: python

  query = db_session.query(Sample).join(SampleAssay, Annotation,AnnotatedFeature,\
      AnnotationCompound,Compound,CompoundExternalDB,ExternalDB)\
      .filter(ExternalDB.name=='PubChem CID' & ~CompoundExternalDB.database_ref.in_(['16217534','3082637'])

  query_dict = {
                  'model': 'Sample',
                  'joins':['SampleAssay','Annotation','AnnotatedFeature',\
                          'AnnotationCompound','Compound','CompoundExternalDB','ExternalDB'],
                  'filters': [{
                                  'matches': [{
                                                  'model': 'ExternalDB'
                                                  'property': 'name',
                                                  "operator": 'eq',
                                                  'value': 'PubChem CID',
                                                },
                                                {
                                                  'model': 'CompoundExternalDB'
                                                  'property': 'database_ref',
                                                  "operator": 'not_in',
                                                  'value': ['16217534','3082637']
                                                }]
                              }]
                }


.. automodule:: phenomedb.query_factory
   :members:
