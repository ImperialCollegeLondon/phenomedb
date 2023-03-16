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


.. automodule:: phenomedb.query_factory
   :members:
