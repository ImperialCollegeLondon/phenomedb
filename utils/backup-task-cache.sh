#!/usr/bin/env bash

usage="$(basename "$0") [-h] [-o <string>] [-d <string>] [-v]
Backup the task cache files

where:
    -h  show this help text
    -d  the cache path (default .)
    -o  the output path (default ./output)
    -v  verbose output
"

output_path="./output"
cache_path='.'

while getopts ':h:o:d:v' option; do
  case "$option" in
    h) echo "$usage"
       exit
       ;;
    o) output_path=$OPTARG
       ;;
    d) cache_path=$OPTARG
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
filename="phenomedb_task_cache_backup_${datestr}.tar.gz"
tar_path="${output_path}/${filename}"

if [ "${verbose}" = "v"  ]
then
    echo "tar_path = ${tar_path}"
    echo "cache_path = ${cache_path}"
    echo "tar -c${verbose}f ${output_path} ${cache_path}/Task*.cache"
fi

tar -c${verbose}f ${tar_path} ${cache_path}/Task*.cache
