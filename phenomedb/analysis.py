from abc import abstractmethod
from phenomedb.task import Task
from phenomedb.models import *
import datetime
from phenomedb.query_factory import *
from phenomedb.utilities import configure_logging
import re
import numpy as np
import pandas as pd
import json
from jinja2 import Template
from jinja2 import Environment, FileSystemLoader
import pathlib
from pyChemometrics.ChemometricsPCA import ChemometricsPCA
from pyChemometrics.ChemometricsScaler import ChemometricsScaler
import subprocess
import nPYc


class AnalysisTask(Task):
    
    for_npyc = True
    columns_to_include = ['Project','Unique Batch','Unique Correction Batch','Run Order','Acquired Time']
    sample_types = None
    assay_roles = None

    def __init__(self,query_factory=None,saved_query_model='AnnotatedFeature',saved_query_id=None,task_run_id=None,username=None,correction_type=None,
                 exclude_na_metadata_samples=False,exclude_na_metadata_columns=False,output_dir=None,db_env=None,db_session=None,execution_date=None,
                 columns_to_exclude=None,exclude_one_factor_columns=False,columns_to_include=None,class_level=None,class_type=None,
                 only_harmonised_metadata=False,only_metadata=False,scaling=None,transform=None,reload_cache=False,validate=True,aggregate_function=None,
                 harmonise_annotations=False,upstream_task_run_id=None,exclude_samples_with_na_feature_values=False,include_metadata=False,
                exclude_features_with_na_feature_values=False,include_default_columns=True,include_harmonised_metadata=True,drop_sample_column=False,
                 exclude_features_not_in_all_projects=False,sample_types=None,assay_roles=None,pipeline_run_id=None):
        """The base AnalysisTask Task. Extend this Task to create your own methods.

        :param query_factory: QueryFactory, a handle to the :class:`phenomedb.query_factory.QueryFactory`
        object that defined the cohort, defaults to None
        :type query_factory: :class:`phenomedb.query_factory.QueryFactory`, optional
        :param saved_query_model: The output model of the query, defaults to 'AnnotatedFeature'
        :type saved_query_model: str, optional
        :param saved_query_id: SavedQuery.id of the query, (typical usage), defaults to None
        :type saved_query_id: int, optional
        :param task_run_id: The TaskRun.id, defaults to None
        :type task_run_id: int, optional
        :param username: The username of the user running the task, defaults to None
        :type username: str, optional
        :param correction_type: The CorrectionType to pass to the Query (e.g. SR, LTR), defaults to None
        :type correction_type: str, optional
        :param exclude_na_metadata_samples: Whether to exclude samples that have na values for their metadata columns, defaults to False
        :type exclude_na_metadata_samples: bool, optional
        :param exclude_na_metadata_columns: Whether to exclude metadata columns that have na values, defaults to False
        :type exclude_na_metadata_columns: bool, optional
        :param output_dir: Output directory for function, defaults to None
        :type output_dir: str, optional
        :param db_env: Database environment, 'PROD','BETA','TEST', defaults to None
        :type db_env: str, optional
        :param db_session: Database session, defaults to None
        :type db_session: object, optional
        :param execution_date: Datetime of execution, defaults to None
        :type execution_date: :class:`DateTime.DateTime`, optional
        :param columns_to_exclude: Which columns to exclude, defaults to None
        :type columns_to_exclude: list, optional
        :param exclude_one_factor_columns: Exclude columns with only one factor, defaults to False
        :type exclude_one_factor_columns: bool, optional
        :param columns_to_include: Which columns to include, defaults to None
        :type columns_to_include: list, optional
        :param class_level: Query Aggregration class level (for Compounds), defaults to None
        :type class_level: str, optional
        :param class_type: Query Aggregration class type, defaults to None
        :type class_type: str, optional
        :param only_harmonised_metadata: Only include harmonised metadata fields, defaults to False
        :type only_harmonised_metadata: bool, optional
        :param only_metadata: Only include metadata fields, defaults to False
        :type only_metadata: bool, optional
        :param scaling: Which scaling to use, 'pa', 'uv', 'med', defaults to None
        :type scaling: str, optional
        :param transform: Which transformation to use, 'log', 'sqrt', defaults to None
        :type transform: str, optional
        :param reload_cache: Whether to reload the cache for the Query, defaults to False
        :type reload_cache: bool, optional
        :param validate: Whether to validate the Task by running the validate() method, defaults to True
        :type validate: bool, optional
        :param aggregate_function: Which Query aggregration function to use (mean, median, sum, avg), defaults to None
        :type aggregate_function: str, optional
        :param harmonise_annotations: Whether to use harmonised annotations, defaults to False
        :type harmonise_annotations: bool, optional
        :param upstream_task_run_id: The upstream TaskRun.id, defaults to None
        :type upstream_task_run_id: int, optional
        :param exclude_samples_with_na_feature_values: Exclude samples with na feature values, defaults to False
        :type exclude_samples_with_na_feature_values: bool, optional
        :param include_metadata: Whether to include metadata or not, defaults to False
        :type include_metadata: bool, optional
        :param exclude_features_with_na_feature_values: Exclude features with na feature values, defaults to False
        :type exclude_features_with_na_feature_values: bool, optional
        :param include_default_columns: Whether to include default columns, defaults to True
        :type include_default_columns: bool, optional
        :param include_harmonised_metadata: Whether to include harmonised metadata, defaults to True
        :type include_harmonised_metadata: bool, optional
        :param drop_sample_column: Drop the sample column, defaults to False
        :type drop_sample_column: bool, optional
        :param exclude_features_not_in_all_projects: Exclude features not in all projects, defaults to False
        :type exclude_features_not_in_all_projects: bool, optional
        :param sample_types: SampleTypes to include (StudySample, StudyReference, ExternalReference), defaults to None
        :type sample_types: list, optional
        :param assay_roles: AssayRoles to include (Assay, LinearityReference, PrecisionReference), defaults to None
        :type assay_roles: list, optional
        :param pipeline_run_id: The TaskRun.pipeline_run_id, defaults to None
        :type pipeline_run_id: int, optional
        """    

        if not sample_types and self.sample_types is None:
            self.sample_types = [SampleType.StudySample,SampleType.StudyPool,SampleType.ExternalReference]
        elif sample_types:
            self.sample_types = sample_types

        if not assay_roles and self.assay_roles is None:
            self.assay_roles = [AssayRole.Assay,AssayRole.PrecisionReference,AssayRole.LinearityReference]
        elif assay_roles:
            self.assay_roles = assay_roles

        if isinstance(self.sample_types,list):
            for idx,sample_type in enumerate(self.sample_types):
                self.sample_types[idx] = utils.get_npyc_enum_from_value(sample_type)

        if isinstance(self.assay_roles,list):
            for idx,assay_role in enumerate(self.assay_roles):
                self.assay_roles[idx] = utils.get_npyc_enum_from_value(assay_role)

        if not columns_to_include:
            columns_to_include = []
        if not columns_to_exclude:
            columns_to_exclude = []

        super().__init__(username=username,task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,
                         validate=validate,upstream_task_run_id=upstream_task_run_id,pipeline_run_id=pipeline_run_id)

        self.query_factory = query_factory
        self.saved_query_model = saved_query_model
        self.saved_query_id = saved_query_id
        self.correction_type = correction_type
        self.exclude_samples_with_na_feature_values = exclude_samples_with_na_feature_values
        self.exclude_features_with_na_feature_values = exclude_features_with_na_feature_values
        self.exclude_na_metadata_samples = exclude_na_metadata_samples
        self.exclude_na_metadata_columns = exclude_na_metadata_columns
        self.columns_to_exclude = columns_to_exclude
        self.exclude_one_factor_columns = exclude_one_factor_columns
        self.drop_sample_column = drop_sample_column
        self.exclude_features_not_in_all_projects = exclude_features_not_in_all_projects
        # add them to the default ones
        if columns_to_include is not None and len(columns_to_include) > 0 and include_default_columns:
            for column_to_include in columns_to_include:
                if column_to_include not in self.columns_to_include:
                    self.columns_to_include.append(column_to_include.strip())
        elif columns_to_include is not None and len(columns_to_include) > 0 and not include_default_columns:
            self.columns_to_include = columns_to_include
        # overrides them to specify no columns - which means all columns!
        elif columns_to_include is not None and len(columns_to_include) == 0 and len(self.columns_to_include) == 0:
            self.columns_to_include = []

        self.include_harmonised_metadata = include_harmonised_metadata
        self.only_harmonised_metadata = only_harmonised_metadata
        self.include_metadata = include_metadata
        self.only_metadata = only_metadata
        self.reload_cache = reload_cache
        self.transform = transform
        self.scaling = scaling
        self.output_dir = output_dir
        self.class_level = class_level
        self.class_type = class_type
        self.aggregate_function = aggregate_function

        self.intensity_data_key = None
        self.feature_metadata_key = None
        self.sample_metadata_key = None
        self.saved_query = None

        self.harmonise_annotations = harmonise_annotations
        if harmonise_annotations:
            self.args['harmonise_annotations'] = harmonise_annotations

        if include_harmonised_metadata:
            self.args['include_harmonised_metadata'] = include_harmonised_metadata
            
        if only_harmonised_metadata:
            self.args['only_harmonised_metadata'] = only_harmonised_metadata
            
        if only_metadata:
            self.args['only_metadata'] = only_metadata

        if correction_type:
            self.args['correction_type'] = correction_type
        if reload_cache:
            self.args['reload_cache'] = reload_cache
        if aggregate_function:
            self.args['aggregate_function'] = aggregate_function
        if class_type:
            self.args['class_type'] = class_type
        if class_level:
            self.args['class_level'] = class_level
        if saved_query_model:
            self.args['saved_query_model'] = saved_query_model
        if scaling:
            self.args['scaling'] = scaling
        if transform:
            self.args['transform'] = transform
        if exclude_one_factor_columns:
            self.args['exclude_one_factor_columns'] = exclude_one_factor_columns
        if drop_sample_column:
            self.args['drop_sample_column'] = drop_sample_column
        if saved_query_id:
            self.args['saved_query_id'] = saved_query_id
        if sample_types:
            self.args['sample_types'] = sample_types
        if assay_roles:
            self.args['assay_roles'] = assay_roles

        self.results = {}

    def process(self):
        """Main process method. Runs load_data(), run_analysis(), save_results()
        """        

        self.load_data()

        self.run_analysis()

        self.save_results()

    def load_data(self):
        """Load data method. Takes the query factory or saved_query_id and loads the dataframes

        :raises Exception: If no QueryFactory or SavedQuery object
        """

        if not self.db_session:
            self.get_db_session(db_env=self.db_env)

        self.logger.info('Loading data.......')

        self.dataframe = pd.DataFrame()

        if self.upstream_task_run_id:
            self.load_data_from_upstream()
        else:
            self.load_data_from_query_factory()

        # For AnalysisTasks that have their data cache deleted
        if self.task_run_id and not self.task_run:
            self.task_run = self.db_session.query(TaskRun).filter(TaskRun.id == self.task_run_id).first()
        if self.task_run:
            self.cache.set(self.task_run.get_task_data_cache_key(),
                           utils.convert_to_json_safe(self.clean_data_for_jsonb(self.data)), ex=86400)

        self.logger.info(".....done")

    def load_data_from_upstream(self):

        self.upstream_task_run = self.db_session.query(TaskRun).filter(TaskRun.id==self.upstream_task_run_id).first()

        if not self.cache.exists(self.upstream_task_run.get_task_data_cache_key()):
            raise Exception('The upstream task run cache does not exist!! Please re-run the pipeline from the previous task: %s' % self.upstream_task_run_id)

        upstream_data = self.upstream_task_run.get_task_data(self.cache)
        upstream_output = self.upstream_task_run.get_task_output(self.cache)

        self.data = upstream_output

        # Just put the columns back in, not any missing rows!

        # put the missing columns back in!
        if 'sample_metadata' in upstream_output.keys() and 'untransformed_sample_metadata' in upstream_data.keys():
            self.logger.info("Found upstream sample metadata")
            sample_metadata = pd.DataFrame.from_dict(upstream_output['sample_metadata'])
            sample_metadata = sample_metadata.where(pd.notnull(sample_metadata), None)
            untransformed_sample_metadata = pd.DataFrame.from_dict(upstream_data['untransformed_sample_metadata'])
            untransformed_sample_metadata = untransformed_sample_metadata.where(pd.notnull(untransformed_sample_metadata), None)

            if sample_metadata.shape[1] != untransformed_sample_metadata.shape[1] and sample_metadata.shape[0] == \
                    untransformed_sample_metadata.shape[0]:
                # rows match but not columns, so iterate over the columns and add them
                p = 0
                while p < len(untransformed_sample_metadata.columns):
                    column = untransformed_sample_metadata.columns[p]
                    if column not in sample_metadata.columns:
                        sample_metadata[column] = untransformed_sample_metadata[column]
                    p = p + 1
            elif sample_metadata.shape != untransformed_sample_metadata.shape:
                # rows and/or columns do not match, so iterate over them all
                if 'Sample File Name' in sample_metadata.columns and 'Sample File Name' in sample_metadata.columns:
                    lookup_key = 'Sample File Name'
                elif 'Sample ID' in sample_metadata.columns and 'Sample ID' in sample_metadata.columns:
                    lookup_key = 'Sample ID'
                else:
                    lookup_key = None

                # add the missing columns
                missing_columns = []
                p = 0
                while p < len(untransformed_sample_metadata.columns):
                    column = untransformed_sample_metadata.columns[p]
                    if column not in sample_metadata.columns:
                        sample_metadata[column] = None
                        missing_columns.append(column)
                    p = p + 1

                # make the column order the same
                sample_metadata = sample_metadata[untransformed_sample_metadata.columns]

                if lookup_key:
                    i = 0
                    while i < sample_metadata.shape[0]:
                        # upstream_data['untransformed_sample_metadata']
                        try:
                            # try and match the row index. if it matches, overwrite the sample metadata missing columns
                            untransformed_row_index = \
                            np.where(untransformed_sample_metadata.loc[:, lookup_key] == sample_metadata.loc[
                                str(i), lookup_key])[0][0]
                            sample_metadata.loc[str(i), missing_columns] = untransformed_sample_metadata.loc[
                                str(untransformed_row_index), missing_columns]
                        except Exception as err:
                            # if it doesn't exist, do nothing!
                            pass
                        i = i + 1
            self.data['sample_metadata'] = utils.convert_to_json_safe(self.clean_data_for_jsonb(sample_metadata.to_dict()))
        else:
            self.logger.info("Did not find upstream sample metadata!")

    def load_data_from_query_factory(self):

        self.args['saved_query_id'] = self.saved_query_id

        self.saved_query = self.db_session.query(SavedQuery).filter(SavedQuery.id==self.saved_query_id).first()

        self.query_factory = QueryFactory(saved_query=self.saved_query,db_env=self.db_env)

        combined_key, sample_metadata_key, feature_metadata_key, intensity_data_key = self.query_factory.set_three_file_format_keys(
            output_model=self.saved_query_model, class_type=self.class_type, class_level=self.class_level,
            aggregate_function=self.aggregate_function, correction_type=self.correction_type,
            harmonise_annotations=self.harmonise_annotations)
        intensity_data = self.query_factory.load_dataframe(type='intensity_data',
                                          reload_cache=self.reload_cache,
                                          output_dir=self.output_dir,
                                          output_model=self.saved_query_model,
                                          class_type=self.class_type,
                                          class_level=self.class_level,
                                          aggregate_function=self.aggregate_function,
                                          correction_type=self.correction_type,
                                          harmonise_annotations=self.harmonise_annotations)

        sample_metadata = self.query_factory.load_dataframe(type='sample_metadata',
                                          reload_cache=False,
                                          output_dir=self.output_dir,
                                          output_model=self.saved_query_model,
                                          class_type=self.class_type,
                                          class_level=self.class_level,
                                          aggregate_function=self.aggregate_function,
                                          correction_type=self.correction_type,
                                          harmonise_annotations=self.harmonise_annotations)

        feature_metadata = self.query_factory.load_dataframe(type='feature_metadata',
                                                            reload_cache=False,
                                                            output_dir=self.output_dir,
                                                            output_model=self.saved_query_model,
                                                            class_type=self.class_type,
                                                            class_level=self.class_level,
                                                            aggregate_function=self.aggregate_function,
                                                            correction_type=self.correction_type,
                                                            harmonise_annotations=self.harmonise_annotations)

        #self.data['untransformed_feature_metadata'] = feature_metadata
        self.data['untransformed_sample_metadata'] = sample_metadata
        #self.data['untransformed_intensity_data'] = intensity_data

        unique_assays = feature_metadata.loc[:,'assay'].unique()
        if len(unique_assays) == 1 and unique_assays[0] == 'NOESY':
            assay_platform = 'NMR'
        else:
            assay_platform = 'MS'

        if self.task_run:
            task_run_id = self.task_run.id
        elif self.task_run_id:
            task_run_id = self.task_run_id
        else:
            task_run_id = None

        sample_metadata, feature_metadata, intensity_data = self.query_factory.transform_dataframe(
                                                                type = '3 file format',
                                                                sample_metadata = sample_metadata,
                                                                feature_metadata = feature_metadata,
                                                                intensity_data = intensity_data,
                                                                scaling=self.scaling,
                                                                transform=self.transform,
                                                                for_npyc=self.for_npyc,
                                                                sample_types=self.sample_types,
                                                                assay_roles=self.assay_roles,
                                                                include_harmonised_metadata=self.include_harmonised_metadata,
                                                                only_harmonised_metadata=self.only_harmonised_metadata,
                                                                include_metadata=self.include_metadata,
                                                                only_metadata=self.only_metadata,
                                                                columns_to_include=self.columns_to_include,
                                                                columns_to_exclude=self.columns_to_exclude,
                                                                assay_platform=assay_platform,
                                                                #drop_sample_column=self.drop_sample_column,
                                                                exclude_features_with_na_feature_values=self.exclude_features_with_na_feature_values,
                                                                exclude_features_not_in_all_projects=self.exclude_features_not_in_all_projects,
                                                                task_run_id=task_run_id)

        self.data['query_factory_dict'] = self.query_factory.query_dict
       # combined_dataframe = self.query_factory.dataframes[combined_key]
       # for colname, colvalue in combined_dataframe.iteritems():
       #     if np.issubdtype(combined_dataframe.dtypes[colname],np.datetime64):
       #         combined_dataframe.loc[:,colname] = combined_dataframe.loc[:,colname].dt.strftime('%Y-%m-%d %H:%M:%S')
       # combined_dataframe = combined_dataframe.where(pd.notnull(combined_dataframe), None)
       # self.data['combined_data'] = combined_dataframe.to_dict()
        for colname, colvalue in sample_metadata.iteritems():
            if np.issubdtype(sample_metadata.dtypes[colname],np.datetime64):
                sample_metadata.loc[:,colname] = sample_metadata.loc[:,colname].dt.strftime('%Y-%m-%d %H:%M:%S')
        sample_metadata = sample_metadata.where(pd.notnull(sample_metadata), None)
        self.data['sample_metadata'] = sample_metadata.to_dict()
        self.data['intensity_data'] = intensity_data.tolist()
        for colname, colvalue in feature_metadata.iteritems():
            if np.issubdtype(feature_metadata.dtypes[colname],np.datetime64):
                feature_metadata.loc[:,colname] = feature_metadata.loc[:,colname].dt.strftime('%Y-%m-%d %H:%M:%S')
        feature_metadata = feature_metadata.where(pd.notnull(feature_metadata), None)
        self.data['feature_metadata'] = feature_metadata.to_dict()


    def is_unique(self, colvalue):
        return (colvalue[0] == colvalue).all(0)

    def run_analysis(self):
        """Runs the analysis. Override this method
        """        
        pass

    def save_results(self):
        """Save the results into AnalysisResult database table
        """        

        self.logger.info("Saving results.....")

        if self.task_run:
            args = dict(self.task_run.args)
            self.task_run.args = args
            self.db_session.flush()

        self.results = utils.convert_to_json_safe(self.clean_data_for_jsonb(self.results))
        self.saved_output = self.results
        self.output = self.results

        # For tasks that adapt their data during the task
        if self.task_run_id and not self.task_run:
            self.task_run = self.db_session.query(TaskRun).filter(TaskRun.id == self.task_run_id).first()
        if self.task_run:
            self.cache.set(self.task_run.get_task_data_cache_key(), utils.convert_to_json_safe(self.clean_data_for_jsonb(self.data)), ex=86400)

        self.logger.info("Done")

class RunPCA(AnalysisTask):
    """RunPCA. Run a PCA using the pyChemometrics PCA function.

    Scaling is done by ChemometricsScaler() as part of the model, NOT the QueryFactory Scaler

    Uses SampleType masks. Masks can be specified if required.

    :param AnalysisTask: The AnalysisTask base class.
    :type AnalysisTask: `phenomedb.analysis.AnalysisTask`
    """

    columns_to_include = []
    assay_roles = [AssayRole.PrecisionReference, AssayRole.Assay]

    def __init__(self,max_components=10,scaling=None,transform=None,minQ2=0.05,username=None,task_run_id=None,db_env=None,harmonise_annotations=True,
                 db_session=None,execution_date=None,query_factory=None,saved_query_id=None,correction_type=None,reload_cache=False,
                 validate=True,saved_query_model='AnnotatedFeature',class_level=None,class_type=None,aggregate_function=None,upstream_task_run_id=None,
                 include_harmonised_metadata=True,exclude_features_not_in_all_projects=True,sample_types=None,assay_roles=None,pipeline_run_id=None):
        """The init method for the RunPCA.

        :param max_components: The max number of Principle Components, defaults to 10
        :type max_components: int, optional_run
        :param scaling: Which kind of scaling to use, 'mc': mean-centred, 'uv': univariate, 'pa': pareto. defaults to 'uv'
        :type scaling: str, optional
        :param minQ2: minQ2 for number of PC optimisation, defaults to 0.05
        :type minQ2: float, optional
        :param username: Username of user running analysis, defaults to None
        :type username: str, optional
        :param query_factory: The AnnotatedFeatureFactory object to load results from, defaults to None
        :type query_factory: `phenomedb.query_factory.AnnotatedFeatureFactory`, optional
        :param saved_query_id: The ID of the SavedQuery to load results from, defaults to None
        :type saved_query_id: int, optional
        :param annotations_only: Use only those annotated_features with annotations, defaults to False
        :type annotations_only: bool, optional
        """        

        super().__init__(query_factory=query_factory,saved_query_id=saved_query_id,task_run_id=task_run_id,transform=transform,
                         username=username,db_env=db_env,db_session=db_session,execution_date=execution_date,scaling=scaling,
                         correction_type=correction_type,validate=validate,saved_query_model=saved_query_model,exclude_features_with_na_feature_values=True,
                         class_level=class_level,class_type=class_type,aggregate_function=aggregate_function,include_harmonised_metadata=include_harmonised_metadata,
                        harmonise_annotations=harmonise_annotations,reload_cache=reload_cache,upstream_task_run_id=upstream_task_run_id,pipeline_run_id=pipeline_run_id,
                         exclude_features_not_in_all_projects=exclude_features_not_in_all_projects,sample_types=sample_types,assay_roles=assay_roles)

        self.max_components = max_components
        self.scaling = scaling
        self.minQ2 = minQ2

        self.args['max_components'] = max_components
        self.args['scaling'] = scaling
        self.args['minQ2'] = minQ2
        self.args['correction_type'] = correction_type

        self.get_class_name(self)

        self.logger.info('ARGS: %s' % self.args)


    def run_analysis(self):
        """Run the PCA analysis using the specified options.
        """

        intensity_data = np.matrix(self.data['intensity_data'])

        self.max_components = min(intensity_data.shape)
        self.logger.info("Updated max components to min(intensity_data.shape) %s" % self.max_components)

        self.PCAmodel = ChemometricsPCA(ncomps=self.max_components)#, scaler=ChemometricsScaler(self.pyc_scaling))

        #PCAmodel._npyc_dataset_shape = {'NumberSamples': self.intensity_data.shape[0], 'NumberFeatures': self.intensity_data.shape[1]}

        self.PCAmodel.fit(intensity_data)
        scree_cv = self.PCAmodel._screecv_optimize_ncomps(intensity_data, total_comps=self.max_components, stopping_condition=self.minQ2)

        self.PCAmodel.ncomps = scree_cv['Scree_n_components']
        if self.PCAmodel.ncomps == 1:
            scree_cv = self.PCAmodel._screecv_optimize_ncomps(intensity_data, total_comps=2, stopping_condition=-100000)
            self.PCAmodel.ncomps = scree_cv['Scree_n_components']

        self.PCAmodel.fit(intensity_data)
        self.PCAmodel.cvParameters = scree_cv
        self.PCAmodel.cvParameters['total_comps'] = self.max_components
        self.PCAmodel.cvParameters['stopping_condition'] = self.minQ2

        # Cross-validation
        self.PCAmodel.cross_validation(intensity_data, press_impute=False)

        t2 = self.PCAmodel.hotelling_T2(alpha=self.minQ2,comps=range(self.PCAmodel.ncomps))

        loadings_with_features = {}
        loadings_with_feature_ids = {}
        sorted_loadings_features = []
        sorted_loadings_feature_ids = []
        sorted_loadings = []
        feature_metadata = pd.DataFrame.from_dict(self.data['feature_metadata'])
        loadings_feature_names = feature_metadata['feature_name'].tolist()
        loadings_feature_ids = feature_metadata['feature_id'].tolist()
        component = 0
        for loadings in self.PCAmodel.loadings:
            sorted_loadings.append(sorted(loadings.tolist()))
            zip_obj = zip(loadings.tolist(), loadings_feature_names)
            loadings_with_features[component] = dict(zip_obj)
            zip_obj = zip(loadings.tolist(), loadings_feature_ids)
            loadings_with_feature_ids[component] = dict(zip_obj)
            sorted_loadings_features.append([])
            sorted_loadings_feature_ids.append([])
            for loading in sorted_loadings[component]:
                sorted_loadings_features[component].append(loadings_with_features[component][loading])
                sorted_loadings_feature_ids[component].append(loadings_with_feature_ids[component][loading])
            component = component + 1

        self.results = {'ncomps':self.PCAmodel.ncomps,
                        'scores':self.PCAmodel.scores,
                        'loadings':self.PCAmodel.loadings,
                        'loadings_feature_names': loadings_feature_names,
                        'loadings_feature_ids': loadings_feature_ids,
                        'sorted_loadings':sorted_loadings,
                        'sorted_loadings_features': sorted_loadings_features,
                        'sorted_loadings_feature_ids': sorted_loadings_feature_ids,
                        'model_parameters':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.PCAmodel.modelParameters)),
                        'cv_parameters':utils.convert_to_json_safe(self.clean_data_for_jsonb(self.PCAmodel.cvParameters)),
                        't2': t2.tolist()}

class RAnalysisTask(AnalysisTask):

    r_code = None
    r_script_path = None
    #r_script_folder = config['R']['script_directory']
    r_template = None
    for_npyc = False

    def __init__(self,query_factory=None,saved_query_id=None,username=None,task_run_id=None,scaling=None,transform=None,db_env=None,db_session=None,execution_date=None,
                 exclude_na_metadata_samples=False,exclude_na_metadata_columns=False,reload_cache=False,columns_to_include=None,
                 columns_to_exclude=None,exclude_one_factor_columns=True,only_harmonised_metadata=True,only_metadata=False,drop_sample_column=False,
                 class_level=None,aggregate_function=None,class_type=None,saved_query_model='AnnotatedFeature',correction_type=None,
                 harmonise_annotations=False,upstream_task_run_id=None,exclude_samples_with_na_feature_values=False,include_metadata=False,
                exclude_features_with_na_feature_values=False,include_default_columns=True,include_harmonised_metadata=True,
                 exclude_features_not_in_all_projects=False,sample_types=None,assay_roles=None,pipeline_run_id=None):
        """Init method

        :param query_factory: The query factory, defaults to None
        :type query_factory: `phenomedb.query_factory.QueryFactory`, optional
        :param saved_query_id: The ID of the SavedQuery, defaults to None
        :type saved_query_id: int, optional
        :param username: The username of the user running the task, defaults to None
        :type username: str, optional
        """

        if not columns_to_include:
            columns_to_include = []
        if not columns_to_exclude:
            columns_to_exclude = []

        super().__init__(query_factory=query_factory,saved_query_id=saved_query_id,username=username,task_run_id=task_run_id,
                         exclude_na_metadata_samples=exclude_na_metadata_samples,db_env=db_env,db_session=db_session,execution_date=execution_date,
                         exclude_na_metadata_columns=exclude_na_metadata_columns,
                         columns_to_exclude=columns_to_exclude,
                         exclude_features_not_in_all_projects=exclude_features_not_in_all_projects,
                         exclude_one_factor_columns=exclude_one_factor_columns,
                         only_harmonised_metadata=only_harmonised_metadata,
                         only_metadata=only_metadata,include_harmonised_metadata=include_harmonised_metadata,
                         reload_cache=reload_cache,include_metadata=include_metadata,
                         columns_to_include=columns_to_include,include_default_columns=include_default_columns,
                         scaling=scaling,
                         transform=transform,
                         class_level=class_level,
                         aggregate_function=aggregate_function,
                         class_type=class_type,
                         saved_query_model=saved_query_model,
                         correction_type=correction_type,
                         harmonise_annotations=harmonise_annotations,
                         upstream_task_run_id=upstream_task_run_id,
                         drop_sample_column=drop_sample_column,
                         exclude_samples_with_na_feature_values=exclude_samples_with_na_feature_values,
                         exclude_features_with_na_feature_values=exclude_features_with_na_feature_values,
                         sample_types=sample_types,
                         assay_roles=self.assay_roles,
                         pipeline_run_id=pipeline_run_id
                         )


    def run_analysis(self):

        self.build_script_path()
        self.render_template()
        self.write_out_script()
        self.run_R_script()
        self.load_results()

    def build_script_path(self):

        class_name = self.get_class_name(self)
        #datestr = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"

        self.job_name = "%s_TR%s_%s" % (self.task_run.class_name,self.saved_query_id,self.task_run.execution_date)

        job_path = '/tmp/phenomedb/r_jobs/' + self.job_name
        self.r_script_path = job_path + "/script.R"
        self.job_folder = job_path + "/"
        self.output_folder = self.job_folder + "output/"

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)


    def render_template(self):

        template_data = self.method_specific_steps()

        template_data['base_template'] = 'base.r'
        template_data['r_exec_path'] = config['R']['exec_path']
        template_data['job_folder'] = self.job_folder
        template_data['output_folder'] = self.output_folder

        parent_folder = str(pathlib.Path(__file__).parent.absolute())
        f = open(parent_folder + "/r_templates/" + self.r_template, "r")
        #t = Template(f.read())
        t = Environment(loader=FileSystemLoader(parent_folder + '/r_templates/')).from_string(f.read())
        self.r_code = t.render(template_data)
        self.logger.info('R code: \n %s' % self.r_code)
        f.close()

    def method_specific_steps(self):

        return {}

    def write_out_script(self):

        f = open(self.r_script_path, "w")
        f.write(self.r_code)
        f.close()
        
    def run_R_script(self):

        try:
            self.logger.info('Running R script: %s' % self.r_script_path)
            #cmd = ['R', 'CMD', 'BATCH','--no-save', self.r_script_path]
            cmd = ['Rscript','--no-save', self.r_script_path]
            x = subprocess.check_output(cmd,universal_newlines=True,cwd=self.job_folder)
            self.logger.info(x)
            self.r_output = self.read_R_out_file()
            self.args['r_output'] = self.r_output.replace("'\n'","").replace("'","")
            self.logger.info(self.r_output)

        except Exception as err:
            self.r_output = self.read_R_out_file()
            self.logger.error(self.r_output)
            self.logger.exception(err)
            self.output = "R script failed: %s %s %s" % (self.r_script_path,err,self.r_output)
            raise Exception("R script failed: %s %s %s" % (self.r_script_path,err,self.r_output))

    def load_results(self):

        results_file_path = self.output_folder + "results.json"
        if os.path.exists(results_file_path):
            with open(results_file_path) as json_file:
                results = json.load(json_file)
                if isinstance(results,list) and len(results) == 1:
                    if isinstance(results[0],str):
                        self.results = json.loads(results[0])
                    else:
                        self.results = results[0]
                else:
                    if isinstance(results,str):
                        self.results = json.loads(results)
                    else:
                        self.results = results
        else:
            self.logger.info("No results? %s" % results_file_path)
            self.results = None

    def read_R_out_file(self):


        r_out_path = self.r_script_path + "out"

        if os.path.exists(r_out_path):
            f = open(r_out_path,'r')
            output = f.read()
            f.close()
            return output
        else:
            return 'No R output file: %s' % r_out_path


class RunXCMS(RAnalysisTask):

    r_template = 'xcms.r'

    def __init__(self, username=None, task_run_id=None,db_env=None, db_session=None, execution_date=None,upstream_task_run_id=None,pipeline_run_id=None,
                 chromatography=None,metabolights_study_id=None,lab=None,input_dir=None,sample_matrix=None,centwave_prefilter=None,centwave_peakwidth=None,
                centwave_mzdiff = None,centwave_snthresh = None,centwave_ppm = None,centwave_noise = None,centwave_mzCenterFun = None,
                 centwave_integrate = None, peakdensity_minFraction = None,peakdensity_minSamples = None,peakdensity_bw = None,peakdensity_binSize = None):

        super().__init__(username=username,
                         task_run_id=task_run_id,
                         db_env=db_env, db_session=db_session,
                         execution_date=execution_date,
                         upstream_task_run_id=upstream_task_run_id,
                         pipeline_run_id=pipeline_run_id)
        
        if not metabolights_study_id and not input_dir:
            raise Exception("Either metabolights_study_id or input_dir must be specified")
        else:
            self.metabolights_study_id = metabolights_study_id
            self.input_dir = input_dir
        with open(config['DATA']['config'] + "xcms_defaults.json", "r") as read_file:
            self.default_params = json.load(read_file)

        if chromatography is None:
            raise Exception("chromatography cannot be None")

        if chromatography.strip().upper() in ['H','HILIC',"HPOS","HNEG"]:
            self.chromatography = 'H'
        elif chromatography.strip().upper() in ['L','LIPID',"LPOS","LNEG"]:
            self.chromatography = 'L'
        elif chromatography.strip().upper() in ['R','REVERSED PHASE',"RPOS","RNEG","REVERSED"]:
            self.chromatography = 'R'
        elif chromatography.strip().upper() in ['BA','BANEG',"BAPOS"]:
            self.chromatography = 'BA'
        else:
            raise Exception("Unrecognised chromatography %s must be one of H, R, L, or BA" % chromatography)

        if sample_matrix is None:
            raise Exception("sample_matrix cannot be None")

        if sample_matrix.strip().upper() in ['S','SERUM']:
            self.sample_matrix = 'S'
        elif sample_matrix.strip().upper() in ['P','PLASMA']:
            self.sample_matrix = 'P'
        elif sample_matrix.strip().upper() in ['U',"URINE"]:
            self.sample_matrix = 'U'
        else:
            raise Exception("Unrecognised sample_matrix %s must be one of S, P, or U" % sample_matrix)

        if isinstance(centwave_prefilter,list):
            self.centwave_prefilter = centwave_prefilter
        elif centwave_prefilter is None:
            self.centwave_prefilter = self.default_params[self.chromatography]['centwave_prefilter']

        if isinstance(centwave_peakwidth,list):
            self.centwave_peakwidth = centwave_peakwidth
        elif centwave_peakwidth is None:
            self.centwave_peakwidth = self.default_params[self.chromatography]['centwave_peakwidth']

        if centwave_mzdiff is None:
            self.centwave_mzdiff = self.default_params[self.chromatography]['centwave_mzdiff']
        else:
            self.centwave_mzdiff = centwave_mzdiff

        if centwave_snthresh is None:
            self.centwave_snthresh = self.default_params[self.chromatography]['centwave_snthresh']
        else:
            self.centwave_snthresh = centwave_snthresh

        if centwave_ppm is None:
            self.centwave_ppm = self.default_params[self.chromatography]['centwave_ppm']
        else:
            self.centwave_ppm = centwave_ppm

        if centwave_noise is None:
            self.centwave_noise = self.default_params[self.chromatography]['centwave_noise']
        else:
            self.centwave_noise = centwave_noise

        if centwave_mzCenterFun is None:
            self.centwave_mzCenterFun = self.default_params[self.chromatography]['centwave_mzCenterFun']
        else:
            self.centwave_mzCenterFun = centwave_mzCenterFun

        if centwave_integrate is None:
            self.centwave_integrate = self.default_params[self.chromatography]['centwave_integrate']
        else:
            self.centwave_integrate = centwave_integrate

        if peakdensity_minFraction is None:
            self.peakdensity_minFraction = self.default_params[self.chromatography]['peakdensity_minFraction']
        else:
            self.peakdensity_minFraction = peakdensity_minFraction

        if peakdensity_minSamples is None:
            self.peakdensity_minSamples = self.default_params[self.chromatography]['peakdensity_minSamples']
        else:
            self.peakdensity_minSamples = peakdensity_minSamples

        if peakdensity_bw is None:
            self.peakdensity_bw = self.default_params[self.chromatography]['peakdensity_bw']
        else:
            self.peakdensity_bw = peakdensity_bw

        if peakdensity_binSize is None:
            self.peakdensity_binSize = self.default_params[self.chromatography]['peakdensity_binSize']
        else:
            self.peakdensity_binSize = peakdensity_binSize

        self.lab = lab
        self.args['lab'] = lab
        self.args['sample_matrix'] = sample_matrix
        self.args['input_dir'] = input_dir
        self.args['metabolights_study_id'] = metabolights_study_id
        self.args["centwave_prefilter"] = centwave_prefilter
        self.args["centwave_peakwidth"] = centwave_peakwidth
        self.args["centwave_mzdiff"] = centwave_mzdiff
        self.args["centwave_snthresh"] = centwave_snthresh
        self.args["centwave_ppm"] = centwave_ppm
        self.args["centwave_noise"] = centwave_noise
        self.args["centwave_mzCenterFun"] = centwave_mzCenterFun
        self.args["centwave_mzCenterFun"] = centwave_mzCenterFun
        self.args["peakdensity_minFraction"] = peakdensity_minFraction
        self.args["peakdensity_minSamples"] = peakdensity_minSamples
        self.args["peakdensity_bw"] = peakdensity_bw
        self.args["peakdensity_binSize"] = peakdensity_binSize

        self.get_class_name(self)

    def load_data(self):
        if self.metabolights_study_id and not self.input_dir:
            self.input_dir = config['DATA']['app_data'] + "metabolights/%s" % self.metabolights_study_id
            self.download_files_from_metabolights(self.metabolights_study_id,prefixes=['i','m','a','s'],suffixes=['mzml'])


    def method_specific_steps(self):

        # 1. Write out data to /tmp/phenomedb/R_jobs/<self.job_name>/input/

        # 2. Load vars into template_data

        template_data = {'parse_IPC_project_folder_path' : config['R']['parse_IPC_project_folder_path']}

        template_data['sample_matrix'] = self.sample_matrix
        template_data['input_dir'] = self.input_dir
        template_data["centwave_prefilter"] = self.centwave_prefilter
        template_data["centwave_peakwidth"] = self.centwave_peakwidth
        template_data["centwave_mzdiff"] = self.centwave_mzdiff
        template_data["centwave_snthresh"] = self.centwave_snthresh
        template_data["centwave_ppm"] = self.centwave_ppm
        template_data["centwave_noise"] = self.centwave_noise
        template_data["centwave_mzCenterFun"] = self.centwave_mzCenterFun
        template_data["centwave_mzCenterFun"] = self.centwave_mzCenterFun
        template_data["peakdensity_minFraction"] = self.peakdensity_minFraction
        template_data["peakdensity_minSamples"] = self.peakdensity_minSamples
        template_data["peakdensity_bw"] = self.peakdensity_bw
        template_data["peakdensity_binSize"] = self.peakdensity_binSize
        template_data['output_path'] = self.output_folder + "xcms_output.csv"
        template_data['lab'] = self.lab

        return template_data

    def load_results(self):

        super().load_results()
        shutil.copy(self.output_folder + "xcms_output.csv",config['DATA']['app_data'] + "output/%s_xcms_output.csv" % self.task_run.id)

class RunPCPR2(RAnalysisTask):

    columns_to_include = ['Unique Batch']
    for_npyc = False
    sample_types = [SampleType.StudySample]
    r_template = 'pc-pr2.r'

    def __init__(self,query_factory=None,saved_query_id=None,username=None,task_run_id=None,pct_threshold=0.95,db_env=None,db_session=None,execution_date=None,
                 exclude_na_metadata_samples=True,exclude_na_metadata_columns=True,columns_to_exclude=None,columns_to_include=None,
                 scaling=None,transform=None,only_harmonised_metadata=True,reload_cache=False,only_metadata=False,include_metadata=False,assay_roles=None,
                 correction_type=None,aggregate_function=None,class_level=None,class_type=None,saved_query_model='AnnotatedFeature',sample_types=None,pipeline_run_id=None,
                 harmonise_annotations=True,upstream_task_run_id=None,include_harmonised_metadata=True,exclude_features_not_in_all_projects=True):

        if not columns_to_include:
            columns_to_include = []
        if not columns_to_exclude:
            columns_to_exclude = ['Unique Run Order']

        super().__init__(query_factory=query_factory,saved_query_id=saved_query_id,username=username,task_run_id=task_run_id,
                         exclude_na_metadata_samples=exclude_na_metadata_samples,db_env=db_env,db_session=db_session,execution_date=execution_date,
                         exclude_na_metadata_columns=exclude_na_metadata_columns,
                         columns_to_exclude=columns_to_exclude,
                         exclude_one_factor_columns=True,
                         exclude_samples_with_na_feature_values=True,
                         exclude_features_with_na_feature_values=True,
                         only_harmonised_metadata=only_harmonised_metadata,include_harmonised_metadata=include_harmonised_metadata,
                         reload_cache=reload_cache,
                         scaling=scaling,transform=transform,
                         only_metadata=only_metadata,include_metadata=include_metadata,
                         columns_to_include=columns_to_include,
                         class_level=class_level,
                         aggregate_function=aggregate_function,
                         class_type=class_type,
                         saved_query_model=saved_query_model,
                         correction_type=correction_type,include_default_columns=False,
                         harmonise_annotations=harmonise_annotations,
                         exclude_features_not_in_all_projects=exclude_features_not_in_all_projects,
                         upstream_task_run_id=upstream_task_run_id,
                         sample_types=sample_types,
                         assay_roles=assay_roles,
                         pipeline_run_id=pipeline_run_id)

        self.pct_threshold = pct_threshold

        self.args['pct_threshold'] = pct_threshold
        self.args['exclude_na_metadata_samples'] = exclude_na_metadata_samples
        self.args['exclude_na_metadata_columns'] = exclude_na_metadata_columns
        self.args['columns_to_exclude'] = self.columns_to_exclude
        self.args['include_harmonised_metadata'] = only_harmonised_metadata
        self.args['include_metadata'] = only_harmonised_metadata
        self.args['only_harmonised_metadata'] = only_harmonised_metadata
        self.args['only_metadata'] = only_metadata
        self.args['columns_to_include'] = columns_to_include
        self.args['reload_cache'] = reload_cache
        self.args['scaling'] = scaling

        self.get_class_name(self)

    def method_specific_steps(self):

        # 1. Write out data to /tmp/phenomedb/R_jobs/<self.job_name>/input/

        intensity_file_path = self.job_folder + "intensity.csv"
        #pd.DataFrame(self.query_factory.intensity_data).to_csv(intensity_file_path,header=False,index=False)
        intensity_data = np.matrix(self.data['intensity_data'])
        pd.DataFrame(intensity_data).to_csv(intensity_file_path,index=False)

        sample_metadata_file_path = self.job_folder + "sample_metadata.csv"
        #self.query_factory.dataframes[self.sample_metadata_key].to_csv(sample_metadata_file_path,index=False)
        sample_metadata = dict(self.data['sample_metadata'])

        # Strip out the unwanted columns

        for colname in self.data['sample_metadata'].keys():
            if colname in self.columns_to_include \
                or (re.search('h_metadata::', colname) and self.include_harmonised_metadata) \
                    or (re.search('metadata::', colname) and self.include_metadata):
                pass
            elif colname not in self.columns_to_include or colname in self.columns_to_exclude:
                del sample_metadata[colname]

            if colname in sample_metadata.keys() and self.exclude_one_factor_columns:
                series = pd.Series(self.data['sample_metadata'][colname])
                if self.is_unique(series.values):
                    del sample_metadata[colname]

        self.stripped_sample_metadata = pd.DataFrame.from_dict(sample_metadata)

        self.stripped_sample_metadata.to_csv(sample_metadata_file_path, index=False)

        # 2. Load vars into template_data

        template_data = {'intensity_data_file_path': intensity_file_path,
                        'sample_metadata_file_path': sample_metadata_file_path,
                         'pct_threshold':self.pct_threshold}

        return template_data

    def load_results(self):

        #self.results = self.load_tabular_file(self.output_folder + 'results.json').to_dict()

        results_file_path = self.output_folder + "results.json"
        if os.path.exists(results_file_path):
            with open(results_file_path) as json_file:
                results = json.load(json_file)
                if isinstance(results,list) and len(results) == 1:
                    if isinstance(results[0],str):
                        self.results = json.loads(results[0])
                    else:
                        self.results = results[0]
                else:
                    if isinstance(results,str):
                        self.results = json.loads(results)
                    else:
                        self.results = results
                self.add_Z_order()
        else:
            self.logger.info("No results? %s" % results_file_path)
            self.results = None

    def add_Z_order(self):

        self.results['Z_order'] = []
        for colname, colvalue in self.stripped_sample_metadata.iteritems():
            self.results['Z_order'].append(colname)

        self.results['Z_order'].append('R2')

class NPYCTask(AnalysisTask):

    for_npyc = True
    npyc_dataset = None
    assay_platform = 'MS'

    def process(self):

        self.load_data()
        self.load_npyc_dataset()
        self.run_analysis()

    def load_npyc_dataset(self):
        sample_metadata = pd.DataFrame.from_dict(self.data['sample_metadata'])
        intensity_data = np.matrix(self.data['intensity_data'])
        feature_metadata = pd.DataFrame.from_dict(self.data['feature_metadata'])
        self.npyc_dataset = self.query_factory.load_npyc_dataset(sample_metadata,feature_metadata,intensity_data,self.assay_platform)

class RunNPYCReport(NPYCTask):

    for_npyc = True

    def __init__(self,username=None,task_run_id=None,db_env=None,db_session=None,execution_date=None,saved_query_id=None,
                 correction_type=None,report_name=None,comment=None,samples_to_exclude=None,exclude_on='Run Order',
                 exclusion_comments=None,reload_cache=False,scaling=None,aggregate_function=None,class_level=None,transform=None,
                 class_type=None,saved_query_model='AnnotatedFeature',harmonise_annotations=False,upstream_task_run_id=None,
                 exclude_features_not_in_all_projects=False,sample_types=None,assay_roles=None,pipeline_run_id=None):

        output_dir = '/tmp/phenomedb/npyc-datasets/sq' + str(saved_query_id)
        columns_to_include = ['Sample File Name','Acquired Time','Batch','Unique Run Order','SampleType','AssayRole','Sample ID']

        if not samples_to_exclude:
            samples_to_exclude = []
        if not exclusion_comments:
            exclusion_comments = {}

        super().__init__(saved_query_id=saved_query_id,correction_type=correction_type,username=username,scaling=scaling,transform=transform,
                         task_run_id=task_run_id,db_env=db_env,db_session=db_session,execution_date=execution_date,assay_roles=assay_roles,
                         reload_cache=reload_cache,output_dir=output_dir,columns_to_include=columns_to_include,sample_types=sample_types,pipeline_run_id=pipeline_run_id,
                         aggregate_function=aggregate_function, class_level=class_level,class_type=class_type, saved_query_model=saved_query_model,
                         harmonise_annotations=harmonise_annotations,upstream_task_run_id=upstream_task_run_id,exclude_features_not_in_all_projects=exclude_features_not_in_all_projects)

        self.samples_to_exclude = samples_to_exclude
        self.exclude_on = exclude_on
        self.exclusion_comments = exclusion_comments
        self.comment = comment

        self.report_name = report_name

        self.report_folder = None
        if correction_type and correction_type not in [FeatureDataset.CorrectionType.LOESS_SR,FeatureDataset.CorrectionType.LOESS_SR.value,
                                                       FeatureDataset.CorrectionType.LOESS_LTR,FeatureDataset.CorrectionType.LOESS_LTR.value]:
            raise Exception("Correction Type must be None, SR, or LTR")
        else:
            self.correction_type = correction_type

        self.args['saved_query_id'] = self.saved_query_id
        self.args['username'] = self.username
        self.args['report_name'] = self.report_name
        self.args['samples_to_exclude'] = self.samples_to_exclude
        self.args['exclusion_comments'] = self.exclusion_comments
        self.args['exclude_on'] = self.exclude_on
        self.args['comment'] = self.comment
        self.args['scaling'] = scaling
        self.args['correction_type'] = correction_type
        self.get_class_name(self)

    def load_data(self):

        super().load_data()

        #self.npyc_dataset = self.load_npyc_dataset()

        self.report_folder = config['DATA']['app_data'] + (
                "task_runs/task_run_%s/reports/%s/" % (self.task_run.id, self.report_name))

    def run_analysis(self):

        if self.samples_to_exclude and self.exclude_on:
            if isinstance(self.exclusion_comments,list) and len(self.samples_to_exclude) == len(self.exclusion_comments):
                for i in self.samples_to_exclude:
                    self.npyc_dataset.excludeSamples(self.samples_to_exclude[i],on=self.exclude_on,message=self.exclusion_comments[i])
            elif isinstance(self.exclusion_comments,list):
                self.npyc_dataset.excludeSamples(self.samples_to_exclude,on=self.exclude_on,message=self.exclusion_comments[0])
            else:
                self.npyc_dataset.excludeSamples(self.samples_to_exclude,on=self.exclude_on,message=self.exclusion_comments)

        self.results = {}
        super().save_results()
        self.task_run.reports = {self.report_name: self.report_folder}
        self.db_session.flush()

        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)

        if self.report_name in ['multivariate_report','multivariate report']:
            self.pca_model = nPYc.multivariate.exploratoryAnalysisPCA(self.npyc_dataset)#,scaling=self.scaling)
            nPYc.reports.multivariateReport(self.npyc_dataset, self.pca_model, destinationPath=self.report_folder)
        else:
            nPYc.reports.generateReport(self.npyc_dataset, self.report_name, destinationPath=self.report_folder)

class RunWilcoxonRankTest(RAnalysisTask):

    #sample_types = [SampleType.StudySample]

    def __init__(self, saved_query_one=None, saved_query_two=None, username=None, task_run_id=None, reload_cache=False, scaling=None,
                 transform=None, upstream_task_run_id=None, pipeline_run_id=None,
                 include_harmonised_metadata=True, db_env=None, db_session=None, execution_date=None,
                 correction_type=None, exclude_features_not_in_all_projects=True,
                 harmonise_annotations=True):
        super().__init__(correction_type=correction_type, saved_query_id=saved_query_one,
                         username=username,task_run_id=task_run_id, exclude_samples_with_na_feature_values=False, db_env=db_env,
                         upstream_task_run_id=upstream_task_run_id, pipeline_run_id=pipeline_run_id,
                         db_session=db_session, execution_date=execution_date, scaling=scaling, transform=transform,
                         exclude_features_with_na_feature_values=False,
                         include_harmonised_metadata=include_harmonised_metadata,
                         exclude_features_not_in_all_projects=exclude_features_not_in_all_projects,
                         exclude_na_metadata_samples=False, exclude_one_factor_columns=False, reload_cache=reload_cache,
                         harmonise_annotations=harmonise_annotations)

        self.saved_query_one = saved_query_one
        self.args['saved_query_one'] = saved_query_one
        self.saved_query_two = saved_query_two
        self.args['saved_query_two'] = saved_query_two
        self.get_class_name(self)

    def method_specific_steps(self):

        query_one_features = pd.DataFrame.from_dict(self.data['feature_metadata'])
        query_one_intensities = np.matrix(self.data['intensity_data'])
        query_one_dataframe = pd.DataFrame(columns=query_one_features['harmonised_annotation_id'])
        i = 0
        while i < query_one_features.shape[0]:
            query_one_dataframe[query_one_features['harmonised_annotation_id']] = query_one_intensities[i,:]
            i = i + 1

        query_factory_two = QueryFactory(saved_query_id=self.saved_query_two)
        query_two_intensities = query_factory_two.load_dataframe('intensity_data',
                                                                 harmonise_annotations=self.harmonise_annotations,
                                                                 correction_type=self.correction_type)
        query_two_features = query_factory_two.load_dataframe('feature_metadata',
                                                              harmonise_annotations=self.harmonise_annotations,
                                                              correction_type=self.correction_type)
        query_two_dataframe = pd.DataFrame(columns=query_two_features['harmonised_annotation_id'])

        i = 0
        while i < query_two_intensities.shape[0]:
            query_two_dataframe[query_two_features['harmonised_annotation_id']] = query_two_intensities[i,:]
            i = i + 1

        self.query_one_file_path = self.job_folder + "query_one.csv"
        query_one_dataframe.to_csv(self.query_one_file_path, index=False)
        self.query_two_file_path = self.job_folder + "query_two.csv"
        query_two_dataframe.to_csv(self.query_two_file_path, index=False)

        template_data = {'query_one_file_path': self.query_one_file_path,
                         'query_two_file_path': self.query_one_file_path}
        return template_data


class RunMWAS(RAnalysisTask):

    r_code = None
    r_script_path = None
    r_template = 'MWAS.r'
    sample_types = [SampleType.StudySample]

    def __init__(self,query_factory=None,saved_query_id=None,username=None,task_run_id=None,comment=None,model_Y_variable=None,
                 model_X_variables=None,reload_cache=False,method='linear',correction_type=None,scaling=None,transform=None,upstream_task_run_id=None,pipeline_run_id=None,
                 include_harmonised_metadata=True,db_env=None,db_session=None,execution_date=None,multiple_correction='BH',features_to_include=None,
                 bootstrap=False,save_models=False,exclude_features_not_in_all_projects=True,harmonise_annotations=True,model_Y_ci=None,model_Y_min=None,model_Y_max=None):
        """Init method

        :param query_factory: The query factory, defaults to None
        :type query_factory: `phenomedb.query_factory.QueryFactory`, optional
        :param saved_query_id: The ID of the SavedQuery, defaults to None
        :type saved_query_id: int, optional
        :param username: The username of the user running the task, defaults to None
        :type username: str, optional
        """
        if model_X_variables and isinstance(model_X_variables,list):
            columns_to_include = model_X_variables
        else:
            columns_to_include = []
        super().__init__(query_factory=query_factory,correction_type=correction_type,saved_query_id=saved_query_id,username=username,columns_to_include=columns_to_include,
                         task_run_id=task_run_id,exclude_samples_with_na_feature_values=False,db_env=db_env,upstream_task_run_id=upstream_task_run_id,pipeline_run_id=pipeline_run_id,
                         db_session=db_session,execution_date=execution_date,scaling=scaling,transform=transform,sample_types=self.sample_types,
                         exclude_features_with_na_feature_values=False,include_harmonised_metadata=include_harmonised_metadata,exclude_features_not_in_all_projects=exclude_features_not_in_all_projects,
                         exclude_na_metadata_samples=False,exclude_one_factor_columns=False,reload_cache=reload_cache,harmonise_annotations=harmonise_annotations)

        self.comment = comment
        self.method = method
        self.model_Y_variable = model_Y_variable
        self.model_X_variables = model_X_variables
        self.multiple_correction = multiple_correction
        self.bootstrap = bootstrap
        self.save_models = save_models
        self.args['method'] = method
        self.args['model_Y_variable'] = model_Y_variable
        self.args['model_X_variables'] = model_X_variables
        self.args['multiple_correction'] = multiple_correction
        self.args['bootstrap'] = bootstrap
        self.args['save_models'] = save_models

        self.model_Y_ci = model_Y_ci
        self.args['model_Y_ci'] = model_Y_ci
        self.model_Y_min = model_Y_min
        self.args['model_Y_min'] = model_Y_min
        self.model_Y_max = model_Y_max
        self.args['model_Y_max'] = model_Y_max
        self.features_to_include = features_to_include
        self.args['features_to_include'] = features_to_include
        self.get_class_name(self)


    def method_specific_steps(self):

        # 1. Write out data to /tmp/phenomedb/R_jobs/<self.job_name>/<files>

        # 2. Load vars into template_data

        feature_metadata = pd.DataFrame.from_dict(self.data['feature_metadata'])
        sample_metadata = pd.DataFrame.from_dict(self.data['sample_metadata'])
        intensity_data = np.matrix(self.data['intensity_data'])
        Y_min = None
        Y_max = None
        if self.model_Y_min is not None and utils.is_number(self.model_Y_min):
            Y_min = float(self.model_Y_min)
        if self.model_Y_max is not None and utils.is_number(self.model_Y_max):
            Y_max = float(self.model_Y_max)
        if self.model_Y_ci is not None and utils.is_number(self.model_Y_ci):
            self.model_Y_ci = float(self.model_Y_ci)
            min_Y = sample_metadata[self.model_Y_variable].min()
            max_Y = sample_metadata[self.model_Y_variable].max()
            range_Y = max_Y - min_Y
            ci_range_Y = (range_Y - (range_Y * self.model_Y_ci)) / 2
            Y_min = min_Y + ci_range_Y
            Y_max = max_Y - ci_range_Y
        if Y_min is not None and Y_max is None:
            Y_max = sample_metadata[self.model_Y_variable].max()
        elif Y_max is not None and Y_min is None:
            Y_min = sample_metadata[self.model_Y_variable].min()
        if Y_min is not None and Y_max is not None:
            samples_to_drop = []
            i = 0
            while i < sample_metadata.shape[0]:
                Y = sample_metadata.loc[i,self.model_Y_variable]
                if Y < Y_min or Y > Y_max:
                    samples_to_drop.append(i)
                i = i + 1
            self.logger.info("Dropping %s samples that outside min and max range %s %s" % (len(samples_to_drop),Y_min,Y_max))
            sample_metadata = sample_metadata.drop(index=samples_to_drop)
            sample_metadata.reset_index(drop=True, inplace=True)
            intensity_data = np.delete(intensity_data, samples_to_drop, 0)
            self.data['sample_metadata'] = sample_metadata.to_dict()

        mwas_data = pd.DataFrame()
        mwas_data.loc[:, 'Sample'] = sample_metadata.loc[:, 'Sample ID']

        features_to_drop = []
        feature_row_index = 0
        while feature_row_index < feature_metadata.shape[0]:

            if str(feature_row_index) in feature_metadata.index:
                feature_index = str(feature_row_index)
            else:
                feature_index = feature_row_index

            if self.features_to_include is None \
                or (isinstance(self.features_to_include, list) \
                and (feature_metadata.loc[feature_index,'harmonised_annotation_id'] in self.features_to_include \
                    or str(feature_metadata.loc[feature_index,'harmonised_annotation_id']) in self.features_to_include)):
                mwas_data.insert(len(mwas_data.columns),
                                 feature_metadata.loc[feature_index, 'harmonised_annotation_id'],
                                 intensity_data[:, feature_row_index])
            else:
                #feature_metadata = sample_metadata.drop(index=samples_to_drop)
                #sample_metadata.reset_index(drop=True, inplace=True)
                #intensity_data = np.delete(intensity_data, samples_to_drop, 0)
                features_to_drop.append(feature_index)
            feature_row_index = feature_row_index + 1

        feature_metadata = feature_metadata.drop(index=features_to_drop)
        feature_metadata.reset_index(drop=True, inplace=True)
        intensity_data = np.delete(intensity_data, features_to_drop, 1)
        self.logger.info("Dropped the following feature indexes: %s" % features_to_drop)
        self.data['intensity_data'] = intensity_data.tolist()
        self.data['feature_metadata'] = feature_metadata.to_dict()

        mwas_data = mwas_data.drop('Sample', axis=1)

        #self.data['intensity_data'] = intensity_data.tolist()
        #self.data['feature_metadata'] = feature_metadata.tolist()

        self.sample_metadata_file_path = self.job_folder + "sample_metadata.csv"
        sample_metadata.to_csv(self.sample_metadata_file_path, index=False)
        self.data_file_path = self.job_folder + "mwas_data.csv"
        mwas_data.to_csv(self.data_file_path, index=False)

        template_data = {'model_Y_variable': self.model_Y_variable,
                         'model_X_variables': self.model_X_variables,
                         'data_file_path': self.data_file_path,
                         'sample_metadata_file_path': self.sample_metadata_file_path,
                         'method': self.method,
                          'multiple_correction': self.multiple_correction,
                         'bootstrap':self.bootstrap,
                         'save_models':self.save_models}

        self.parameters = template_data

        return template_data

    def save_results(self):
        """Save the results into HarmonisedAnnotatedFeature database table
        """

        self.logger.info("Saving results.....")

        results = {'mwas_results':self.results['mwastable']}
        if 'mwasestimates' in self.results.keys() or '':
            results['mwas_estimates'] = self.results['mwasestimates']
        if 'mwassummaries' in self.results.keys():
            results['mwas_summaries'] = self.results['mwassummaries']
        self.results = results
        super().save_results()
        self.logger.info("Save complete...!")