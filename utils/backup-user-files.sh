#!/usr/bin/env bash

usage="$(basename "$0") [-h] [-o <string>] [-d <string>] [-v]
Backup the task cache files

where:
    -h  show this help text
    -d  the app directory path (default .})
    -o  the output path (default ./output)
    -v  verbose output
"

output_path="./output"
remote_path=$PHENOMEDB__DATA__BACKUP_PATH
app_data_path=$PHENOMEDB__DATA__APP_DATA

while getopts ':h:o:d:v' option; do
  case "$option" in
    h) echo "$usage"
       exit
       ;;
    o) output_path=$OPTARG
       ;;
    d) app_data_path=$OPTARG
       ;;
    v) verbose="v"
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

mkdir -p $output_path

datestr=`date '+%Y-%m-%d-%H-%M'`

if [ "${verbose}" = "v"  ]
then
    echo "app_data_path = ${app_data_path}"
    echo "p_output_path = ${output_path}"
    echo "tar -c${verbose}zpf ${output_path}/phenomedb_output_backup_${datestr}.tar.gz ${app_data_path}/output/*"
    echo "tar -c${verbose}zpf ${output_path}/phenomedb_uploads_backup_${datestr}.tar.gz ${app_data_path}/uploads/*"
    echo "tar -c${verbose}zpf ${output_path}/phenomedb_reports_backup_${datestr}.tar.gz ${app_data_path}/reports/*"
fi

tar -c${verbose}zpf ${output_path}phenomedb_output_backup_${datestr}.tar.gz ${app_data_path}/output/*
tar -c${verbose}zpf ${output_path}phenomedb_uploads_backup_${datestr}.tar.gz ${app_data_path}/uploads/*
tar -c${verbose}zpf ${output_path}phenomedb_reports_backup_${datestr}.tar.gz ${app_data_path}/reports/*
