#!/usr/bin/env bash

usage="$(basename "$0") [-h] [-o <string>] [-H <string>] [-p <string>] [-u <string>][-v]
Export the phenomedb schema, data, min_data, and airflow databases.

Uses the \$PGPASSWORD environment variable for password access

Remember to update the /sql/latest/ directory with the database files you wish to import when creating the containers.

where:
    -h  show this help text
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

while getopts ':h:o:H:p:u:v' option; do
  case "$option" in
    h) echo "$usage"
       exit
       ;;
    o) output_folder=$OPTARG
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

if [ "${verbose}" = " -v "  ]
then
    echo "output_folder = ${output_folder}"
    echo "host = ${host}"
    echo "port = ${port}"
    echo "username = ${username}"
fi

mkdir -p $output_folder

datestr=`date '+%Y-%m-%d-%H-%M'`

pg_dump -h ${host} -p ${port} -U ${username} ${verbose}phenomedb > "${output_folder}/phenomedb_${datestr}.custom"

pg_dump -h ${host} -p ${port} -U ${username}${verbose}airflow > "${output_folder}/airflow_${datestr}.custom"