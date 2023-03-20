#!/usr/bin/env bash

# /home/npcair/phenomedb-dev/scripts/backup-task-cache.sh -d /data1/phenomedb-cache -v -o /data1/phenomedb-backup

usage="$(basename "$0") [-h] [-o <string>] [-d <string>] [-r <string>] [-v]
Backup the task cache files

where:
    -h  show this help text
    -d  the cache path (default ${PHENOMEDB__DATA__CACHE})
    -o  the output path (default ./output)
    -r  the remote backup path (default ${PHENOMEDB__DATA__BACKUP_PATH})
    -v  verbose output
"

output_path="./output"
remote_path=$PHENOMEDB__DATA__BACKUP_PATH
cache_path=$PHENOMEDB__DATA__CACHE

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
    echo "remote_path = ${remote_path}"
    echo "tar -c${verbose}zpf ${output_path} ${cache_path}/Task*.cache"
fi

tar -c${verbose}f ${tar_path} ${cache_path}/Task*.cache
mkdir -p ${remote_path}

cp ${tar_path} ${remote_path}/${filename}