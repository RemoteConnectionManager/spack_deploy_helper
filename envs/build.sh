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
ROOTPATH="$(dirname $CURRPATH)"
if [ "x$1" == "x" ]; then
  echo " too few par, required tmpldir compiler"
  exit 1 
else
  TMPLDIR=$1
  echo "template dir is: ${TMPLDIR}"
  shift
fi
if [ "x$1" == "x" ]; then
  echo " too few par, required tmpldir compiler"
  exit 1 
else
  COMPILER=$1
  shift
  echo "compiler is: ${COMPILER}"
fi
ENVPATH=$(dirname $(spack-python ${ROOTPATH}/scripts/select_spec.py --loglevel debug --compiler ${COMPILER}  --outfile ${TMPLDIR}_${COMPILER}/spack.yaml --tplfile ${CURRPATH}/${TMPLDIR}/spack.yaml))
echo "creating environment in: ${ENVPATH}"
spack env deactivate
spack env activate ${ENVPATH} 
spack concretize -f 
spack fetch --deprecated 
spack env deactivate
