API
===

To access the PhenomeDB API on a local docker installation go to: :link:`http://localhost:5001/custom/`.

The username and password will be the same as your $AIRFLOW_ADMIN_USER and $AIRFLOW_ADMIN_PASSWORD

To view the OpenAPI/Swagger documentation for the API, go to: :link:`http://localhost:5001/custom/swagger/v1`

Implemented API Import endpoints:

* import/samplemanifest
* import/brukerivdrannotations
* import/peakpantherannotations

More can be implemented using these as examples.

To use the API with Python:

.. code-block:: python

    import json
    import requests
    
    data = {"username": "admin","password": "testpass",'refresh':True}
    
    session = requests.session()
    
    login_url = "http://localhost:5001/custom/api/v1/security/login"
    refresh_url = "https://localhost:5001/custom/api/v1/security/refresh"
    
    # Login and set the JWT tokens
    r = session.post(login_url,json=data)
    access_token = json.loads(r.content)['access_token']
    refresh_token = json.loads(r.content)['refresh_token']
    
    print(access_token)
    print(refresh_token)
    
    # Import a sample manifest -
    data = {"project_name":"PipelineTesting",
            "sample_manifest_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET_sampleManifest.xlsx',
            "columns_to_ignore":[],
            "username": "admin"}
    
    r = self.session.post('http://localhost:5001/custom/api/v1/import/samplemanifest',
                          json=data,
                          headers={'Authorization': 'Bearer '+ access_token})
    
    # Import the peak panther data
    data = {"project_name":"PipelineTesting",
            "feature_metadata_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET P LPOS PeakPantheR_featureMetadata.csv',
            "sample_metadata_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET P LPOS PeakPantheR_sampleMetadata_SMALL.csv',
            "intensity_data_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET P LPOS PeakPantheR_intensityData.csv',
            "batch_corrected_data_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET P LPOS PeakPantheR_intensityData_batchcorrected.csv',
            "ppr_annotation_parameters_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET_P_LPOS_annotationParameters_summary.csv',
            "ppr_mz_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET_P_LPOS_PPR_mz.csv',
            "ppr_rt_csv_path": '/opt/phenomedb_app/phenomedb/data/test/DEVSET_P_LPOS_PPR_rt_with_extra_paths.csv',
            "sample_matrix": "plasma",
            "assay_name": "LPOS",
            "run_batch_correction": False,
            "username": "admin"}
    
    r = session.post('http://localhost:5001/custom/api/v1/import/peakpanther',
    json=data,
    headers={'Authorization': 'Bearer '+access_token})
    print(r.content)
    
    # Refresh the JWT token (if access token expires)
    r = session.post(refresh_url,headers={"Authorization": "Bearer " + refresh_token})
    access_token = json.loads(r.content)['access_token']
    refresh_token = json.loads(r.content)['refresh_token']