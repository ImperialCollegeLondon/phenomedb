
--------------------------------------
-- TABLE unit
--------------------------------------
DROP TABLE IF EXISTS unit CASCADE;
CREATE TABLE unit (
                      id serial PRIMARY KEY,
                      name text NOT NULL,
                      description text NOT NULL
);


--------------------------------------
-- TABLE saved_query
--------------------------------------
DROP TABLE if exists saved_query CASCADE;
CREATE TABLE saved_query (
                             id serial PRIMARY KEY,
                             name text NOT NULL,
                             description text NOT NULL,
                             project_short_label text NOT NULL,
                             json jsonb NOT NULL,
                             code_string text,
                             sql text,
                             created_by text,
                             date_added timestamp,
                             type text NOT NULL,
                             cache_state jsonb not null default '{}'::jsonb,
                             constraint unq_query_name unique(name)
);


--------------------------------------
-- TABLE pipeline
--------------------------------------
drop table if exists pipeline;
create table pipeline (
                          id serial primary key,
                          name text,
                          description text,
                          definition jsonb,
                          default_args jsonb,
                          task_order jsonb,
                          tags jsonb,
                          start_date timestamp,
                          date_created timestamp,
                          schedule_interval text,
                          hard_code_data boolean,
                          pipeline_file_path text,
                          sequential boolean,
                          username_created text,
                          max_active_runs numeric,
                          concurrency numeric,
                          deleted boolean default False,
                          constraint unq_pipeline_name unique(name)
);

--------------------------------------
-- TABLE task_run
--------------------------------------
drop table if exists task_run;
create table task_run (
                          id serial primary key,
                          module_name text,
                          class_name text,
                          task_id text,
                          pipeline_id integer references pipeline ON DELETE CASCADE,
                          pipeline_run_id text,
                          upstream_task_run_id integer,
                          args jsonb,
                          output jsonb,
                          execution_date text,
                          datetime_started timestamp,
                          datetime_finished timestamp,
                          run_time numeric,
                          db_size_start numeric,
                          db_size_end numeric,
                          db_size_bytes numeric,
                          db_size_megabytes numeric,
                          username text,
                          status text,
                          saved_query_id integer references saved_query ON DELETE SET NULL,
                          reports jsonb,
                          db_env text,
                          created_by_add_task boolean default False
);

--------------------------------------
-- TABLE missing_import_data
--------------------------------------
DROP TABLE if exists missing_import_data CASCADE;
CREATE TABLE missing_import_data (
                                     id serial PRIMARY KEY,
                                     task_run_id integer REFERENCES task_run ON DELETE CASCADE,
                                     type text DEFAULT NULL,
                                     value jsonb DEFAULT NULL,
                                     comment text DEFAULT NULL
);


--------------------------------------
-- TABLE laboratory
--------------------------------------
DROP TABLE IF EXISTS laboratory CASCADE;
CREATE TABLE laboratory (
                            id serial PRIMARY KEY,
                            name text UNIQUE,
                            affiliation text
);

--------------------------------------
-- TABLE project
--------------------------------------
DROP TABLE IF EXISTS project CASCADE;
CREATE TABLE project (
                         id serial PRIMARY KEY,
                         name text UNIQUE,
                         description text,
                         lims_id integer,
                         date_added timestamp NOT NULL,
                         project_folder_name text,
                         short_description text,
                         laboratory_id integer REFERENCES laboratory ON DELETE CASCADE,
                         persons JSONB,
                         chart_colour text
);



--------------------------------------
-- TABLE subject
--------------------------------------
DROP TABLE if exists subject CASCADE;
CREATE TABLE subject (
                         id serial PRIMARY KEY,
                         name text NOT NULL,
                         project_id integer REFERENCES project ON DELETE CASCADE
);

--------------------------------------
-- TABLE sample
--------------------------------------
DROP TABLE if exists sample CASCADE;
CREATE TABLE sample (
                        id serial PRIMARY KEY,
                        name text NOT NULL,
                        sampling_date timestamp,
                        sample_type text DEFAULT 'StudySample',
                        subject_id integer REFERENCES subject ON DELETE CASCADE,
                        assay_role text DEFAULT 'Assay',
                        sample_matrix text,
                        biological_tissue text,
                        sample_metadata JSONB,
                        CONSTRAINT unq_sample UNIQUE ( subject_id, name, sample_type, assay_role, sample_matrix )
);

---------------------------------------------------------------
-- TABLE assay
--------------------------------------
DROP TABLE IF EXISTS assay CASCADE;
CREATE TABLE assay (
                       id serial PRIMARY KEY,
                       name text UNIQUE,
                       platform text DEFAULT 'Other',
                       targeted text DEFAULT 'N',
                       ms_polarity text DEFAULT 'NA',
                       measurement_type text DEFAULT 'NA',
                       long_name text,
                       long_platform text,
                       quantification_type text DEFAULT 'Unknown'
);
---------------------------------------------------------------
-- TABLE annotation_method
--------------------------------------
DROP TABLE if exists annotation_method CASCADE;
CREATE TABLE annotation_method (
                                   id serial PRIMARY KEY,
                                   name text NOT NULL,
                                   description text
);

---------------------------------------------------------------
-- TABLE compound
--------------------------------------
DROP TABLE IF EXISTS compound CASCADE;
CREATE TABLE compound (
                          id serial PRIMARY KEY,
                          name text,
                          inchi text,
                          inchi_key text,
                          chemical_formula text,
                          monoisotopic_mass numeric,
                          iupac text,
                          smiles text,
                          log_p numeric,
                          CONSTRAINT unq_compound UNIQUE ( inchi_key, name ),
                          CONSTRAINT inchi_key_length CHECK (length(inchi_key) < 28)
);


---------------------------------------------------------------
-- TABLE external_db
--------------------------------------
DROP TABLE IF EXISTS external_db CASCADE;
CREATE TABLE external_db (
                             id serial PRIMARY KEY,
                             name text NOT NULL,
                             url text NOT NULL
);

---------------------------------------------------------------
-- TABLE compound_external_db
--------------------------------------
DROP TABLE IF EXISTS compound_external_db CASCADE;
CREATE TABLE compound_external_db (
                                      id serial PRIMARY KEY,
                                      compound_id integer REFERENCES compound ON DELETE CASCADE,
                                      external_db_id integer REFERENCES external_db ON DELETE CASCADE,
                                      database_ref text NOT NULL,
                                      CONSTRAINT unq_compound_ref UNIQUE (compound_id, external_db_id, database_ref)
);

--------------------------------------
-- TABLE compound_class
--------------------------------------
DROP TABLE if exists compound_class CASCADE;
CREATE TABLE compound_class(
                                id SERIAL PRIMARY KEY,
                                name text,
                                description text,
                                inchi_key_backbone text,
                                type text,
                                kingdom text,
                                category text,
                                main_class text,
                                sub_class text,
                                intermediate_nodes jsonb,
                                direct_parent text,
                                alternative_parents jsonb,
                                molecular_framework text,
                                substituents jsonb,
                                ancestors jsonb,
                                version text,
                                CONSTRAINT unq_compound_class_ref UNIQUE (inchi_key_backbone,type,kingdom,category,main_class,sub_class,intermediate_nodes,direct_parent,version)
);

-------------------------------------
-- TABLE compound_class_compound
--------------------------------------
DROP TABLE if exists compound_class_compound CASCADE;
CREATE TABLE compound_class_compound (
                                         id SERIAL PRIMARY KEY,
                                         compound_id integer REFERENCES compound ON DELETE CASCADE,
                                         compound_class_id integer REFERENCES compound_class ON DELETE CASCADE,
                                         CONSTRAINT unq_compound_class_compound_ref UNIQUE (compound_id,compound_class_id)
);

--------------------------------------
-- TABLE harmonised_annotation
--------------------------------------
DROP TABLE if exists harmonised_annotation CASCADE;
CREATE TABLE harmonised_annotation (
                                     id SERIAL PRIMARY KEY,
                                     cpd_name text,
                                     cpd_id text,
                                     annotated_by text,
                                     confidence_score text,
                                     latest_version text,
                                     annotation_method_id integer REFERENCES annotation_method ON DELETE CASCADE,
                                     assay_id integer REFERENCES assay on DELETE CASCADE,
                                     multi_compound_operator text default null,
                                     CONSTRAINT unq_harmonised_compound_annotation_ref UNIQUE (annotation_method_id,cpd_name,assay_id)
);

--------------------------------------
-- TABLE annotation
--------------------------------------
DROP TABLE if exists annotation CASCADE;
CREATE TABLE annotation (
                                     id SERIAL PRIMARY KEY,
                                     version text,
                                     cpd_name text,
                                     cpd_id text,
                                     annotated_by text,
                                     confidence_score text,
                                     default_primary_ion_rt_seconds numeric,
                                     default_primary_ion_mz numeric,
                                     config jsonb,
                                     annotation_method_id integer REFERENCES annotation_method ON DELETE CASCADE,
                                     assay_id integer REFERENCES assay on DELETE CASCADE,
                                     harmonised_annotation_id integer REFERENCES harmonised_annotation ON DELETE CASCADE,
                                     multi_compound_operator text default null,
                                     CONSTRAINT unq_compound_annotation_ref UNIQUE (assay_id,annotation_method_id,cpd_name,cpd_id,version)
);

--------------------------------------
-- TABLE annotation_compound
--------------------------------------
DROP TABLE if exists annotation_compound CASCADE;
CREATE TABLE annotation_compound (
                                  id SERIAL PRIMARY KEY,
                                  compound_id integer REFERENCES compound ON DELETE CASCADE,
                                  harmonised_annotation_id integer REFERENCES harmonised_annotation ON DELETE CASCADE,
                                  CONSTRAINT unq_annotation_compound_ref UNIQUE (compound_id,harmonised_annotation_id)
);



--------------------------------------
-- TABLE sample_assay
--------------------------------------
DROP TABLE if exists sample_assay CASCADE;
CREATE TABLE sample_assay (
                              id serial PRIMARY KEY,
                              name text,
                              sample_id integer REFERENCES sample ON DELETE CASCADE,
                              assay_id integer REFERENCES assay ON DELETE CASCADE,
                              acquired_time timestamp,
                              raw_spectra_path text,
                              processed_spectra_path text,
                              excluded text,
                              exclusion_details text,
                              instrument text,
                              sample_file_name text,
                              sample_base_name text,
                              position text,
                              expno text,
                              run_order integer,
                              batch text,
                              correction_batch text,
                              dilution numeric,
                              detector_voltage numeric,
                              instrument_metadata JSONB,
                              assay_parameters JSONB,
                              features JSONB,
                              harmonised_features JSONB,
                              CONSTRAINT unq_sample_assay UNIQUE ( sample_id, assay_id, sample_file_name, sample_base_name )
);

DROP TABLE if exists sample_assay_features CASCADE;
CREATE TABLE sample_assay_features (
                              id serial PRIMARY KEY,
                              sample_assay_id integer REFERENCES sample_assay on delete cascade,
                              features JSONB,
                              harmonised_features JSONB,
                              CONSTRAINT unq_sample_assay_features UNIQUE ( sample_assay_id )
);

--------------------------------------
-- TABLE feature_dataset
--------------------------------------
DROP TABLE if exists feature_dataset CASCADE;
CREATE TABLE feature_dataset (
                                 id serial PRIMARY KEY,
                                 name text,
                                 feature_extraction_params jsonb,
                                 annotation_params jsonb,
                                 filetype text,
                                 unified_csv_filename text,
                                 intensity_data_filename text,
                                 sample_metadata_filename text,
                                 feature_metadata_filename text,
                                 assay_id integer REFERENCES assay,
                                 project_id integer REFERENCES project,
                                 sample_matrix text,
                                 sr_correction_parameters jsonb,
                                 sr_correction_task_run_id integer REFERENCES task_run,
                                 ltr_correction_parameters jsonb,
                                 ltr_correction_task_run_id integer REFERENCES task_run,
                                 saved_query_id integer REFERENCES saved_query,
                                 CONSTRAINT unq_feature_dataset UNIQUE (project_id,assay_id,sample_matrix)
);

--------------------------------------
-- TABLE feature_metadata
--------------------------------------
DROP TABLE if exists feature_metadata CASCADE;
CREATE TABLE feature_metadata (
                            id bigserial PRIMARY KEY,
                            feature_name text,
                            annotation_id integer REFERENCES annotation on DELETE SET NULL,
                            feature_dataset_id integer REFERENCES feature_dataset ON DELETE CASCADE,
                            rt_average numeric,
                            rt_min numeric,
                            rt_max numeric,
                            mz_average numeric,
                            mz_min numeric,
                            mz_max numeric,
                            lod numeric,
                            lloq numeric,
                            uloq numeric,
                            ion_type text,
                            ion_id text,
                            lower_reference_percentile numeric,
                            upper_reference_percentile numeric,
                            lower_reference_value numeric,
                            upper_reference_value numeric,
                            rsd_filter boolean,
                            variance_ratio_filter boolean,
                            correlation_to_dilution_filter boolean,
                            blank_filter boolean,
                            artifactual_filter boolean,
                            excluded boolean,
                            exclusion_details text,
                            rsd_sp numeric default null,
                            rsd_ss_rsd_sp numeric default null,
                            correlation_to_dilution numeric default null,
                            blank_value numeric default null,
                            quantification_type text DEFAULT 'QuantOther',
                            calibration_method text DEFAULT 'NoCalibration',
                            feature_filtering_pass boolean,
                            final_assessment_pass boolean,
                            final_assessment_rename text default null,
                            comment text default null,
                            annotation_parameters jsonb default null,
                            annotation_version text default null,
                            feature_metadata jsonb default null,
                            date_imported timestamp,
                            CONSTRAINT unq_feature_metadata UNIQUE (feature_name,feature_dataset_id)
);

--------------------------------------
-- TABLE annotated_feature
--------------------------------------
DROP TABLE if exists annotated_feature CASCADE;
CREATE TABLE annotated_feature (
                             id bigserial PRIMARY KEY,
                             intensity numeric,
                             below_lloq boolean,
                             above_uloq boolean,
                             sample_assay_id integer REFERENCES sample_assay ON DELETE CASCADE,
                             feature_metadata_id integer REFERENCES feature_metadata ON DELETE CASCADE,
                             unit_id integer REFERENCES unit,
                             comment text,
                             sr_corrected_intensity numeric,
                             ltr_corrected_intensity numeric,
                             CONSTRAINT unq_annotated_feature_ref UNIQUE (sample_assay_id,feature_metadata_id)
);


--------------------------------------
-- TABLE harmonised_dataset
--------------------------------------
create table harmonised_dataset(
                                   id serial primary key,
                                   task_run_id integer REFERENCES task_run on DELETE CASCADE,
                                   type text,
                                   username text,
                                   parameters jsonb,
                                   comment text
);

--------------------------------------
-- TABLE harmonised_annotated_feature
--------------------------------------
create table harmonised_annotated_feature (
                                              id serial primary key,
                                              annotated_feature_id integer REFERENCES annotated_feature on DELETE CASCADE,
                                              intensity numeric,
                                              below_lloq boolean,
                                              above_uloq boolean,
                                              rt numeric,
                                              mz numeric,
                                              harmonised_dataset_id integer REFERENCES harmonised_dataset on DELETE CASCADE,
                                              unit_id integer REFERENCES unit
);


--------------------------------------
-- TABLE chemical_standard_dataset
--------------------------------------
DROP TABLE IF EXISTS chemical_standard_dataset CASCADE;
CREATE TABLE chemical_standard_dataset (
                            id serial PRIMARY KEY,
                            collision_energy numeric,
                            acquired_date timestamp,
                            source_file text,
                            compound_id integer REFERENCES compound,
                            assay_id integer REFERENCES assay,
                            supplier text,
                            concentration numeric,
                            mass numeric,
                            exhausted boolean default false,
                            ph numeric,
                            assigned_casrn text,
                            lims_ids jsonb
);
--------------------------------------
-- TABLE chemical_standard_peaklist
--------------------------------------
DROP TABLE IF EXISTS chemical_standard_peaklist CASCADE;
CREATE TABLE chemical_standard_peaklist (
                            id serial PRIMARY KEY,
                            mz numeric NOT NULL,
                            rt_seconds numeric NOT NULL,
                            intensity numeric,
                            drift numeric,
                            peak_width numeric,
                            resolution numeric,
                            seed integer NOT NULL DEFAULT 0,
                            validated boolean DEFAULT false,
                            ion text,
                            chemical_standard_dataset_id integer REFERENCES chemical_standard_dataset ON DELETE CASCADE
);


--------------------------------------
-- TABLE evidence_type
--------------------------------------
DROP TABLE if exists evidence_type CASCADE;
CREATE TABLE evidence_type (
                               id serial PRIMARY KEY,
                               name text NOT NULL,
                               description text NOT NULL,
                               json_format jsonb,
                               CONSTRAINT unq_evidence_type UNIQUE (name)
);

--------------------------------------
-- TABLE evidence_record
--------------------------------------
DROP TABLE if exists annotation_evidence CASCADE;
CREATE TABLE annotation_evidence (
                                 id serial PRIMARY KEY,
                                 evidence_type_id integer REFERENCES evidence_type ON DELETE CASCADE,
                                 annotation_id integer REFERENCES annotation ON DELETE CASCADE,
                                 json_data jsonb NOT NULL,
                                 comments text,
                                 analysed_by_user text,
                                 recorded_by_user text,
                                 validated_by_user text,
                                 date_analysed timestamp,
                                 date_recorded timestamp,
                                 date_validated timestamp,
                                 chemical_standard_dataset_id integer references chemical_standard_dataset
);


--------------------------------------
-- TABLE evidence_record_file_upload
--------------------------------------
DROP TABLE if exists annotation_evidence_file_upload CASCADE;
CREATE TABLE annotation_evidence_file_upload (
                                             id serial PRIMARY KEY,
                                             annotation_evidence_id integer REFERENCES annotation_evidence ON DELETE CASCADE,
                                             filepath text NOT NULL,
                                             filename text,
                                             description text,
                                             uploaded_by_user text,
                                             date_uploaded timestamp
);

--------------------------------------
-- TABLE ontology_source
--------------------------------------
DROP TABLE if exists ontology_source CASCADE;
CREATE TABLE ontology_source (
                                 id serial PRIMARY KEY,
                                 name text,
                                 url text,
                                 version text,
                                 description text
);

--------------------------------------
-- TABLE ontology_ref
--------------------------------------
DROP TABLE if exists ontology_ref CASCADE;
CREATE TABLE ontology_ref (
                              id serial PRIMARY KEY,
                              ontology_source_id integer REFERENCES ontology_source ON DELETE CASCADE,
                              accession_number text,
                              compound_class_kingdom_id integer REFERENCES compound_class ON DELETE CASCADE,
                              compound_class_category_id integer REFERENCES compound_class ON DELETE CASCADE,
                              compound_class_main_class_id integer REFERENCES compound_class ON DELETE CASCADE,
                              compound_class_sub_class_id integer REFERENCES compound_class ON DELETE CASCADE,
                              compound_class_direct_parent_id integer REFERENCES compound_class ON DELETE CASCADE
);

--------------------------------------
-- TABLE metadata_harmonised_field
--------------------------------------
DROP TABLE if exists harmonised_metadata_field CASCADE;
CREATE TABLE harmonised_metadata_field (
                                           id serial PRIMARY KEY,
                                           name text UNIQUE,
                                           unit_id integer REFERENCES unit ON DELETE SET NULL,
                                           datatype text NOT NULL,
                                           classes jsonb,
                                           ontology_ref_id integer REFERENCES ontology_ref ON DELETE SET NULL,
                                           CONSTRAINT unq_harmonised_metadata_field UNIQUE( name, unit_id )
);
--------------------------------------
-- TABLE metadata_field
--------------------------------------
DROP TABLE if exists metadata_field CASCADE;
CREATE TABLE metadata_field (
                                id serial PRIMARY KEY,
                                name text NOT NULL,
                                project_id integer REFERENCES project ON DELETE CASCADE,
                                harmonised_metadata_field_id integer REFERENCES harmonised_metadata_field ON DELETE SET NULL,
                                CONSTRAINT unq_metadata_field UNIQUE ( name, project_id )
);
--------------------------------------
-- TABLE metadata_value
--------------------------------------
DROP TABLE if exists metadata_value CASCADE;
CREATE TABLE metadata_value (
                                id serial PRIMARY KEY,
                                raw_value text DEFAULT NULL,
                                sample_id integer REFERENCES sample ON DELETE CASCADE,
                                harmonised_numeric_value numeric DEFAULT NULL,
                                harmonised_text_value text DEFAULT NULL,
                                harmonised_datetime_value timestamp DEFAULT NULL,
                                metadata_field_id integer REFERENCES metadata_field ON DELETE CASCADE,
                                CONSTRAINT unq_metadata_value UNIQUE ( sample_id, metadata_field_id )
);

--------------------------------------
-- TABLE data_repository
--------------------------------------
DROP TABLE if exists data_repository CASCADE;
CREATE TABLE data_repository (
                                 id serial PRIMARY KEY,
                                 name text,
                                 accession_number text,
                                 submission_date timestamp,
                                 public_release_date timestamp,
                                 project_id integer REFERENCES project on DELETE CASCADE
);

--------------------------------------
-- TABLE protocol
--------------------------------------
DROP TABLE if exists protocol CASCADE;
CREATE TABLE protocol (
                          id serial PRIMARY KEY,
                          name text,
                          type text,
                          description text,
                          uri text,
                          version text
);

--------------------------------------
-- TABLE protocol_parameter
--------------------------------------
DROP TABLE if exists protocol_parameter CASCADE;
CREATE TABLE protocol_parameter (
                          id serial PRIMARY KEY,
                          protocol_id integer REFERENCES protocol on DELETE CASCADE,
                          name text,
                          value text,
                          ontology_ref_id integer REFERENCES ontology_ref on DELETE SET NULL
);

--------------------------------------
-- TABLE publication
--------------------------------------
Create table publication(
                            id serial primary key,
                            pubmed_id text,
                            doi text,
                            author_list jsonb,
                            title text,
                            status text,
                            project_id integer REFERENCES project on DELETE CASCADE
);

--------------------------------------
-- TABLE sample_assay_protocol
--------------------------------------
DROP TABLE if exists sample_assay_protocol CASCADE;
CREATE TABLE sample_assay_protocol (
                                     id SERIAL PRIMARY KEY,
                                     protocol_id integer REFERENCES protocol ON DELETE CASCADE,
                                     sample_assay_id integer REFERENCES sample_assay ON DELETE CASCADE,
                                     CONSTRAINT unq_sample_assay_protocol_ref UNIQUE (protocol_id,sample_assay_id)
);



-----------------------------------
-- INDEXES
-----------------------------------

CREATE INDEX subject_name_index ON subject (name);
CREATE INDEX subject_project_index ON subject (project_id);

CREATE INDEX sample_name_index ON sample (name);
CREATE INDEX sample_subject_index ON sample (subject_id);
CREATE INDEX sample_sample_matrix_index ON sample (sample_matrix);

CREATE INDEX sample_assay_assay_index ON sample_assay (assay_id);
CREATE INDEX sample_assay_sample_index ON sample_assay (sample_id);
CREATE INDEX sample_assay_sample_file_name_index ON sample_assay (sample_file_name);
CREATE INDEX sample_assay_sample_base_name_index ON sample_assay (sample_base_name);

CREATE INDEX metadata_field_project_index ON metadata_field (project_id);
CREATE INDEX metadata_field_name_index ON metadata_field (name);

CREATE INDEX metadata_value_sample_index ON metadata_value (sample_id);
CREATE INDEX metadata_value_metadata_field_index ON metadata_value (metadata_field_id);

CREATE INDEX annotation_compound_compound_index ON annotation_compound (compound_id);
CREATE INDEX annotation_compound_harmonised_annotation_index ON annotation_compound (harmonised_annotation_id);

CREATE INDEX harmonised_annotation_annotation_method_index ON harmonised_annotation (annotation_method_id);
CREATE INDEX harmonised_annotation_assay_index ON harmonised_annotation (assay_id);
CREATE INDEX harmonised_cpd_name_index ON harmonised_annotation (cpd_name);

CREATE INDEX annotation_cpd_name_index ON annotation (cpd_name);
CREATE INDEX annotation_version_index ON annotation (version);
CREATE INDEX annotation_harmonised_annotation_index ON annotation (harmonised_annotation_id);

CREATE INDEX compound_class_compound_compound_id_index ON compound_class_compound (compound_id);
CREATE INDEX compound_class_compound_compound_class_id_index ON compound_class_compound (compound_class_id);

CREATE INDEX compound_external_db_compound_index ON compound_external_db (compound_id);
CREATE INDEX compound_external_db_external_db_index ON compound_external_db (external_db_id);

CREATE INDEX annotated_feature_sample_assay_index ON annotated_feature (sample_assay_id);
CREATE INDEX annotated_feature_feature_metadata_index ON annotated_feature (feature_metadata_id);
CREATE INDEX annotated_feature_intensity_index ON annotated_feature (intensity);

CREATE INDEX feature_metadata_feature_name_index ON feature_metadata (feature_name);
CREATE INDEX feature_metadata_rt_average_index ON feature_metadata (rt_average);
CREATE INDEX feature_metadata_mz_average_index ON feature_metadata (mz_average);
CREATE INDEX feature_metadata_annotation_index on feature_metadata (annotation_id);

CREATE INDEX harmonised_annotated_feature_intensity_index ON harmonised_annotated_feature (intensity);
CREATE INDEX harmonised_annotated_feature_rt_index ON harmonised_annotated_feature (rt);
CREATE INDEX harmonised_annotated_feature_mz_index ON harmonised_annotated_feature (mz);
CREATE INDEX harmonised_annotated_feature_annotated_feature_index ON harmonised_annotated_feature (annotated_feature_id);
CREATE INDEX harmonised_dataset_task_run_index ON harmonised_dataset (task_run_id);

CREATE INDEX publication_project_index ON publication (project_id);

CREATE INDEX data_repository_project_index ON data_repository (project_id);

CREATE INDEX task_run_saved_query_index ON task_run (saved_query_id);

CREATE INDEX sample_assay_name_index ON sample_assay (name);

CREATE INDEX ontology_ref_ontology_source_index ON ontology_ref (ontology_source_id);
CREATE INDEX ontology_ref_compound_class_kingdom_index ON ontology_ref (compound_class_kingdom_id);
CREATE INDEX ontology_ref_compound_class_categoy_index ON ontology_ref (compound_class_category_id);
CREATE INDEX ontology_ref_compound_class_main_class_index ON ontology_ref (compound_class_main_class_id);
CREATE INDEX ontology_ref_compound_class_subclass_index ON ontology_ref (compound_class_sub_class_id);
CREATE INDEX ontology_ref_compound_class_direct_parent_index ON ontology_ref (compound_class_direct_parent_id);
CREATE INDEX ontology_ref_harmonised_metadata_field_index ON harmonised_metadata_field (ontology_ref_id);

CREATE INDEX pipeline_run_id ON task_run (pipeline_run_id);


-- --------------------------------
-- Views to support the Airflow UI
-- --------------------------------
CREATE OR REPLACE VIEW v_project_subject_sample_metadata AS (
SELECT mf.name, hmf.name as "harmonised_name", mv.id as "metadata_value_id", mv.raw_value,
	mv.harmonised_text_value,mv.harmonised_numeric_value, mv.harmonised_datetime_value, s.id as sample_id, s.name as "sample",
	project.id as "project_id", mf.id as "metadata_field_id", project.name as "project",
    subject.name as "subject", s.sample_matrix, subject.id as "subject_id"
	FROM metadata_field mf
	LEFT JOIN metadata_value mv ON mv.metadata_field_id = mf.id
	LEFT JOIN harmonised_metadata_field hmf ON hmf.id = mf.harmonised_metadata_field_id
	JOIN sample s ON s.id = mv.sample_id JOIN subject on subject.id = s.subject_id
	JOIN project on mf.project_id = project.id
	ORDER BY project_id, subject_id);

CREATE OR REPLACE VIEW v_metadata_fields AS
	(SELECT mf.*, hmf.name as "harmonised_name" FROM metadata_field mf LEFT JOIN harmonised_metadata_field hmf ON hmf.id = mf.harmonised_metadata_field_id);

CREATE OR REPLACE VIEW v_compound_with_externaldbs AS
	(SELECT c.id as compound_id,
		link.database_ref as external_ref,
		db.name as external_db_name,
		db.url as external_db_url,
        db.id as external_db_id FROM compound c INNER JOIN compound_external_db link ON c.id = link.compound_id INNER JOIN external_db db ON link.external_db_id = db.id ORDER BY compound_id);


DROP VIEW IF EXISTS v_compound_with_dataset_counts;
CREATE OR REPLACE VIEW v_compound_with_dataset_counts AS
    (SELECT c.id AS id,
        c.name,
        c.inchi,
        c.inchi_key,
        c.monoisotopic_mass,
        c.chemical_formula,
        (SELECT count(*) from annotation_compound ac where ac.compound_id = c.id) as annotation_count
	 	FROM compound c GROUP BY c.id ORDER BY c.id DESC
	);

--select * from evidence_record_file_upload;

DROP VIEW IF EXISTS v_annotation_evidence_records;
CREATE OR REPLACE VIEW v_annotation_evidence_records AS
    (SELECT a.id as "annotation_id",annotation_method.name as "annotation_method_name", compound.name as "compound_name",
    er.id as "evidence_record_id", ha.annotation_method_id, ac.compound_id, a.cpd_name,
    er.evidence_type_id, er.json_data, er.comments, er.analysed_by_user, er.validated_by_user, er.recorded_by_user,er.date_analysed, er.date_recorded, er.date_validated,
    et.name as "evidence_type_name", et.description as "evidence_type_description", et.json_format as "evidence_type_json_format"
    FROM annotation a LEFT JOIN harmonised_annotation ha on ha.id = a.harmonised_annotation_id LEFT JOIN annotation_compound ac on ac.harmonised_annotation_id = ha.id left join compound ON compound.id = ac.compound_id
	 LEFT JOIN annotation_method ON ha.annotation_method_id = annotation_method.id LEFT JOIN annotation_evidence er on er.annotation_id = a.id LEFT JOIN evidence_type et on et.id = er.evidence_type_id);

-- View to assist in finding data location names for a given project id
DROP VIEW IF EXISTS v_sample_assays_by_project;
CREATE OR REPLACE VIEW v_sampe_assays_by_project AS
    (SELECT project.id as project_id, sa.sample_base_name FROM sample_assay sa LEFT join sample s on sa.sample_id = s.id LEFT join subject on s.subject_id = subject.id LEFT join project on subject.project_id = project.id GROUP BY project.id, sa.sample_base_name ORDER BY project.id);


DROP VIEW IF EXISTS v_annotations_no_group_by;
CREATE OR REPLACE VIEW v_annotations_no_group_by AS
(
    select p.id as "project_id",
        su.id as "subject_id",
        s.id as "sample_id",
        sa.id as "sample_assay_id",
        af.id as "annotated_feature_id",
        p.name as "project",
        s.name as "sampling_event_name",
        s.sampling_date,
        s.sample_type,
        s.assay_role,
        s.sample_matrix,
        s.biological_tissue,
        sa.acquired_time,
        sa.sample_file_name,
        sa.run_order,
        sa.batch,
        fm.lod,
        af.intensity,
        fm.lloq,
        fm.uloq,
        fm.rt_average,
        fm.mz_average,
        fm.quantification_type,
        fm.calibration_method,
        a.name as "assay",
        a.platform as "platform",
        a.targeted as "targeted",
        a.ms_polarity as "ms_polarity",
        am.name as "annotation_method",
        c.name as "compound",
        c.id as "compound_id",
        c.chemical_formula,
        an.id as "annotation_id",
        han.id as "harmonised_annotation_id",
        han.cpd_name,
        c.inchi,
        c.inchi_key,
        c.monoisotopic_mass,
        u.name as "unit",
        cg.inchi_key_backbone,
        cg.category,
        cg.main_class,
        cg.sub_class
    from annotated_feature af
    inner join sample_assay sa on sa.id = af.sample_assay_id
    inner join sample s on s.id = sa.sample_id
    inner join subject su on s.id = s.subject_id
    inner join project p on p.id = su.project_id
    inner join assay a on sa.assay_id = a.id
    inner join feature_metadata fm on fm.id = af.feature_metadata_id
    inner join annotation an on an.id = fm.annotation_id
    inner join harmonised_annotation han on han.id = an.harmonised_annotation_id
    inner join annotation_compound ac on han.id = ac.harmonised_annotation_id
    inner join compound c on ac.compound_id = c.id
    inner join compound_class_compound cgc on c.id = cgc.compound_id
    inner join compound_class cg on cg.id = cgc.compound_class_id
    inner join annotation_method am on am.id = han.annotation_method_id
    inner join unit u on af.unit_id = u.id
    );


DROP VIEW IF EXISTS v_annotation_methods_summary;
CREATE OR REPLACE VIEW v_annotation_methods_summary AS
(SELECT
	sa.sample_id as sample_id,
	sa.id as sample_assay_id,
	a.name as assay,
	am.name as annotation_method,
	COUNT(an.id) as annotation_count
 FROM sample_assay sa
 LEFT JOIN assay a on a.id = sa.assay_id
 LEFT JOIN annotated_feature af on af.sample_assay_id = sa.id
 left join feature_metadata fm on af.feature_metadata_id = fm.id
 LEFT JOIN annotation an on an.id = fm.annotation_id
 left join harmonised_annotation ha on ha.id = an.harmonised_annotation_id
 LEFT JOIN annotation_method am on am.id = ha.annotation_method_id
 GROUP BY sa.sample_id, sa.id, a.name, am.name
 ORDER BY sa.sample_id, sa.id);


DROP VIEW IF EXISTS v_sample_id;
CREATE OR REPLACE VIEW v_sample_id as (
	select se.name as sample_id, p.name as project_name,a.name as assay_name,
	s.name as subject_id,se.sample_matrix
	from sample se
	inner join subject s on s.id = se.subject_id
	inner join project p on p.id = s.project_id
	left join sample_assay sa on se.id = sa.sample_id
	left join assay a on a.id = sa.assay_id
);



DROP VIEW IF EXISTS v_compound_with_peaklists;
CREATE OR REPLACE VIEW v_compound_with_peaklists AS
    (SELECT compound.id AS id,
        compound.name AS name,
        compound.chemical_formula,
        compound.monoisotopic_mass,
        compound.inchi,
        compound.inchi_key,
        compound.iupac,
        compound.smiles,
        compound.log_p,
        chemical_standard_dataset.id AS chemical_standard_dataset_id,
        chemical_standard_dataset.acquired_date,
        chemical_standard_dataset.collision_energy,
        chemical_standard_dataset.source_file,
        chemical_standard_peaklist.id AS chemical_standard_peaklist_id,
        chemical_standard_peaklist.rt_seconds,
        chemical_standard_peaklist.mz AS mz,
        chemical_standard_peaklist.intensity AS intensity FROM compound LEFT OUTER JOIN chemical_standard_dataset ON chemical_standard_dataset.compound_id = compound.id LEFT OUTER JOIN chemical_standard_peaklist ON chemical_standard_dataset.id = chemical_standard_peaklist.chemical_standard_dataset_id);

DROP VIEW IF EXISTS v_compound_with_dataset_counts;
CREATE OR REPLACE VIEW v_compound_with_dataset_counts AS
 (SELECT compound.id AS id,
       compound.name,
       compound.inchi,
       compound.inchi_key,
       compound.monoisotopic_mass,
       compound.chemical_formula,
       COUNT(chemical_standard_dataset.id) AS datasets,
       (SELECT count(*) from annotation_compound where annotation_compound.compound_id = compound.id) as compound_annotations
 FROM compound LEFT JOIN chemical_standard_dataset ON compound.id = chemical_standard_dataset.compound_id
 GROUP BY compound.id ORDER BY datasets DESC );