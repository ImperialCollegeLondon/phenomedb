alter table assay rename column annotated_feature_type to measurement_type;

alter table sample_assay add column name text;

CREATE INDEX sample_assay_name_index ON sample_assay (name);

