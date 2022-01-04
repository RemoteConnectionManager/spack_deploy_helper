#!/bin/bash
#! /bin/bash
# Absolute path to this script. /home/user/bin/foo.sh

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path wh
ere the symlink file was located
done
ROOTPATH="$( cd -P "$( dirname "$SOURCE" )" && pwd )"


for (( i=2; i <= "$#"; i++ )); do
#    echo "arg position: ${i}"
#    echo "arg value: ${!i}"

    spack-python ${ROOTPATH}/add_external.py  ${!i} /tmp/add_external.yaml $1
#    cat /tmp/add_external.yaml
    spack config  --scope site add -f /tmp/add_external.yaml
done

