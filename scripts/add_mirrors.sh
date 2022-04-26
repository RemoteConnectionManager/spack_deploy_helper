#!/bin/bash
set -x
currpath=$(realpath $1)
rootpath=$(realpath $currpath/../..)
 
for p in $(find  $rootpath -maxdepth 5 -path "*cache/_source-cache" -not -path "${currpath}*")
do
  spack mirror add --scope site $(realpath --relative-to=$rootpath $(dirname $(dirname $p))) file://$(dirname $p)
done
