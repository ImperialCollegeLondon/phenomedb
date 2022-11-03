--create user phenomedb with encrypted password 'testpass';
create database airflow;
--grant all privileges on database airflow to phenomedb;
grant all privileges on database airflow to postgres;

create database phenomedb_test;
create database phenomedb;
--grant all privileges on database phenomedb_test to phenomedb;
--grant all privileges on database phenomedb to phenomedb;
grant all privileges on database phenomedb_test to postgres;
grant all privileges on database phenomedb to postgres;