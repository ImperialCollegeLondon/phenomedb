alter table assay rename column annotated_feature_type to measurement_type;

alter table sample_assay add column name text;

CREATE INDEX sample_assay_name_index ON sample_assay (name);

alter table sample_assay alter column sample_file_name drop not null;

DROP TABLE if exists sample_assay_features CASCADE;
CREATE TABLE sample_assay_features (
                              id serial PRIMARY KEY,
                              sample_assay_id integer REFERENCES sample_assay on delete cascade,
                              features JSONB,
                              harmonised_features JSONB,
                              CONSTRAINT unq_sample_assay_features UNIQUE ( sample_assay_id )
);