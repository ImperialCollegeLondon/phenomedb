import os,sys

from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.decorators import permission_name, has_access_api
from flask_appbuilder.api import ModelRestApi
from . import appbuilder
if os.environ['PHENOMEDB_PATH'] not in sys.path:
    sys.path.append(  os.environ['PHENOMEDB_PATH'])

from phenomedb.models import *
from phenomedb.config import config

class Project(ModelRestApi):
    resource_name = 'project'
    datamodel = SQLAInterface(Project)
    class_permission_name = "ModelAPI"

class Subject(ModelRestApi):
    resource_name = 'subject'
    datamodel = SQLAInterface(Subject)
    class_permission_name = "ModelAPI"

class Laboratory(ModelRestApi):
    resource_name = 'laboratory'
    datamodel = SQLAInterface(Laboratory)
    class_permission_name = "ModelAPI"

class Sample(ModelRestApi):
    resource_name = 'sample'
    datamodel = SQLAInterface(Sample)
    class_permission_name = "ModelAPI"

class AnnotationMethod(ModelRestApi):
    resource_name = 'annotation_method'
    datamodel = SQLAInterface(AnnotationMethod)
    class_permission_name = "ModelAPI"

class Annotation(ModelRestApi):
    resource_name = 'annotation'
    datamodel = SQLAInterface(Annotation)
    class_permission_name = "ModelAPI"

class AnnotatedFeature(ModelRestApi):
    resource_name = 'annotated_feature'
    datamodel = SQLAInterface(AnnotatedFeature)
    class_permission_name = "ModelAPI"

class HarmonisedAnnotatedFeature(ModelRestApi):
    resource_name = 'harmonised_annotated_feature'
    datamodel = SQLAInterface(HarmonisedAnnotatedFeature)
    class_permission_name = "ModelAPI"

class HarmonisedDataset(ModelRestApi):
    resource_name = 'harmonised_dataset'
    datamodel = SQLAInterface(HarmonisedDataset)
    class_permission_name = "ModelAPI"

class Assay(ModelRestApi):
    resource_name = 'assay'
    datamodel = SQLAInterface(Assay)
    class_permission_name = "ModelAPI"

class SampleAssay(ModelRestApi):
    resource_name = 'sample_assay'
    datamodel = SQLAInterface(SampleAssay)
    class_permission_name = "ModelAPI"

class FeatureDataset(ModelRestApi):
    resource_name = 'feature_dataset'
    datamodel = SQLAInterface(FeatureDataset)
    class_permission_name = "ModelAPI"

class FeatureMetadata(ModelRestApi):
    resource_name = 'feature_metadata'
    datamodel = SQLAInterface(FeatureMetadata)
    class_permission_name = "ModelAPI"

class Compound(ModelRestApi):
    resource_name = 'compound'
    datamodel = SQLAInterface(Compound)
    class_permission_name = "ModelAPI"

class ExternalDB(ModelRestApi):
    resource_name = 'external_db'
    datamodel = SQLAInterface(ExternalDB)
    class_permission_name = "ModelAPI"

class CompoundExternalDB(ModelRestApi):
    resource_name = 'compound_external_db'
    datamodel = SQLAInterface(CompoundExternalDB)
    class_permission_name = "ModelAPI"

class CompoundClass(ModelRestApi):
    resource_name = 'compound_class'
    datamodel = SQLAInterface(CompoundClass)
    class_permission_name = "ModelAPI"

class CompoundClassCompound(ModelRestApi):
    resource_name = 'compound_class_compound'
    datamodel = SQLAInterface(CompoundClassCompound)
    class_permission_name = "ModelAPI"

class MetadataField(ModelRestApi):
    resource_name = 'metadata_field'
    datamodel = SQLAInterface(MetadataField)
    class_permission_name = "ModelAPI"

class HarmonisedMetadataField(ModelRestApi):
    resource_name = 'harmonised_metadata_field'
    datamodel = SQLAInterface(HarmonisedMetadataField)
    class_permission_name = "ModelAPI"

class MetadataValue(ModelRestApi):
    resource_name = 'metadata_value'
    datamodel = SQLAInterface(MetadataValue)
    class_permission_name = "ModelAPI"

class AnnotationCompound(ModelRestApi):
    resource_name = 'annotation_compound'
    datamodel = SQLAInterface(AnnotationCompound)
    class_permission_name = "ModelAPI"

class Unit(ModelRestApi):
    resource_name = 'unit'
    datamodel = SQLAInterface(Unit)
    class_permission_name = "ModelAPI"

class TaskRun(ModelRestApi):
    resource_name = 'task_run'
    datamodel = SQLAInterface(TaskRun)
    class_permission_name = "ModelAPI"

class Pipeline(ModelRestApi):
    resource_name = 'pipeline'
    datamodel = SQLAInterface(Pipeline)
    class_permission_name = "ModelAPI"

#class SavedQuery(ModelRestApi):
#    resource_name = 'saved_query'
#    datamodel = SQLAInterface(SavedQuery)
#    class_permission_name = "ModelAPI"

class MissingImportData(ModelRestApi):
    resource_name = 'missing_import_data'
    datamodel = SQLAInterface(MissingImportData)
    class_permission_name = "ModelAPI"


appbuilder.add_api(Project)
appbuilder.add_api(Subject)
appbuilder.add_api(Sample)
appbuilder.add_api(Assay)
appbuilder.add_api(AnnotationMethod)
appbuilder.add_api(SampleAssay)
appbuilder.add_api(FeatureMetadata)
appbuilder.add_api(FeatureDataset)
appbuilder.add_api(AnnotatedFeature)
appbuilder.add_api(HarmonisedDataset)
appbuilder.add_api(HarmonisedAnnotatedFeature)
appbuilder.add_api(Annotation)
appbuilder.add_api(AnnotationCompound)
appbuilder.add_api(Compound)
appbuilder.add_api(ExternalDB)
appbuilder.add_api(CompoundExternalDB)
appbuilder.add_api(CompoundClass)
appbuilder.add_api(CompoundClassCompound)
appbuilder.add_api(MetadataField)
appbuilder.add_api(HarmonisedMetadataField)
appbuilder.add_api(MetadataValue)
appbuilder.add_api(Unit)
appbuilder.add_api(TaskRun)
appbuilder.add_api(Pipeline)
#appbuilder.add_api(SavedQuery)
appbuilder.add_api(MissingImportData)
