#! /bin/bash
# Absolute path to this script. /home/user/bin/foo.sh

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path wh
ere the symlink file was located
done
CURRPATH="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
ROOTPATH="$(dirname $(dirname $(dirname $CURRPATH)))"
if [ "x$1" == "x" ]; then
  
  OUTDIR=${CURRPATH}/generated_envs
else
  OUTDIR=$1
fi
mkdir -p $OUTDIR
spack-python ${ROOTPATH}/scripts/select_spec.py --tplfile ${CURRPATH}/spack.yaml --external  openssl --outfile ${OUTDIR}/spack.yaml
spack env activate -d ${OUTDIR}
spack concretize -f
spack install
spack env deactivate
