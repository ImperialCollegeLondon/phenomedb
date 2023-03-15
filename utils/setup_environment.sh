#!/bin/bash

# 1. Create the necessary databases
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testpass
apt-get install postgresql postgresql-contrib redis-server
sudo systemctl start postgresql.service
psql -U $POSTGRES_USER -d $POSTGRES_PASSWORD -a -f ./docker/postgres/a_create_dbs.sql
