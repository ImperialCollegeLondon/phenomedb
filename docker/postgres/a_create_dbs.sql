--create user phenomedb with encrypted password 'testpass';

CREATE ROLE root superuser;
ALTER ROLE root WITH LOGIN;
CREATE database root;

create database airflow;
grant all privileges on database airflow to postgres;

create database phenomedb_test;
create database phenomedb;
grant all privileges on database phenomedb_test to postgres;
grant all privileges on database phenomedb to postgres;