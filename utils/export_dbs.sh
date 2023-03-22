#!/usr/bin/env bash

usage="$(basename "$0") [-h] [-o <string>] [-V <string>] [-H <string>] [-p <string>] [-u <string>][-v]
Export the phenomedb schema, data, min_data, and airflow databases.

Remember to update the /sql/latest/ directory with the database files you wish to import when creating the containers.

where:
    -h  show this help text
    -V  the version suffix (required)
    -o  the output folder (default ./output)
    -H  the host of the database (default localhost)
    -p  the port of the database (default 5432)
    -u  the username to connect with (default postgres)
    -v  verbose output
"

host="localhost"
port="5432"
username="postgres"
verbose=" "
output_folder="./output/"

while getopts ':h:o:V:H:p:u:P:v' option; do
  case "$option" in
    h) echo "$usage"
       exit
       ;;
    o) output_folder=$OPTARG
       ;;
    V) version=$OPTARG
       ;;
    H) host=$OPTARG
       ;;
    p) port=$OPTARG
       ;;
    u) username=$OPTARG
       ;;
    v) verbose=" -v "
       ;;
    :) printf "missing argument for -%s\n" "$OPTARG" >&2
       echo "$usage" >&2
       exit 1
       ;;
   \?) printf "illegal option: -%s\n" "$OPTARG" >&2
       echo "$usage" >&2
       exit 1
       ;;
  esac
done
shift $((OPTIND - 1))

# 1. export schema

if [ -z "$version" ]
then
    echo "version (-V) must be set"
fi

if [ "${verbose}" = " -v "  ]
then
    echo "version = ${version}"
    echo "output_folder = ${output_folder}"
    echo "host = ${host}"
    echo "port = ${port}"
    echo "username = ${username}"
fi

mkdir -p $output_folder

base_name="${output_folder}/phenomedb_v${version}"

datestr=`date '+%Y-%m-%d-%H-%M'`

pg_dump -h ${host} -p ${port} -U ${username} ${verbose}phenomedb > "${base_name}_${datestr}_backup.sql"

#pg_dump -h ${host} -p ${port} -U ${username} -a${verbose}phenomedb > "${base_name}_data.sql"

#pg_dump -h ${host} -p ${port} -U ${username} -a --column-inserts${verbose}phenomedb -t compound -t compound_group -t compound_group_compound -t external_db -t compound_external_db -t metadata_harmonised_field > "${base_name}_min_data.sql"

#pg_dump -h ${host} -p ${port} -U ${username} -a --column-inserts${verbose}phenomedb > "${base_name}_data_column_inserts.sql"

#pg_dump -h ${host} -p ${port} -U ${username} -a --column-inserts${verbose}phenomedb > "${base_name}_data_column_inserts_test.sql"

pg_dump -h ${host} -p ${port} -U ${username}${verbose}airflow > "${output_folder}/airflow_${datestr}.sql"

#pg_dump -h ${host} -p ${port} -U ${username}${verbose}phenomedb -t ab_user -t ab_role -t ab_user_role -t ab_permission -t ab_register_user -t ab_permission_view -t ab_permission_view_role -t ab_view_menu  > "${output_folder}/ab_tables_${datestr}.sql"

