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
  echo " too few par, required tmpldir outdir compiler"
  exit 1 
else
  TMPLDIR=$1
  echo "template dir is: ${OUTDIR}"
  shift
fi
if [ "x$1" == "x" ]; then
  echo " too few par, required tmpldir outdir compiler"
  exit 1 
else
  OUTDIR=$1
  echo "output_dir is: ${OUTDIR}"
  shift
fi
if [ "x$1" == "x" ]; then
  echo " too few par, required outdir compiler"
  exit 1 
else
  COMPILER=$1
  shift
  echo "compiler is: ${COMPILER}"
fi
ENVPATH=${OUTDIR}/$(basename $TMPLDIR)_${COMPILER}
echo "creating environment in: ${ENVPATH}"

COMPILER_SPEC=$(spack-python ${ROOTPATH}/scripts/select_spec.py -t '${COMPILER}' -c ${COMPILER})
echo "using compiler spec: ${COMPILER_SPEC}"
echo "adding libraries: $@"
spack env create --dir ${ENVPATH} ${CURRPATH}/${TMPLDIR}/spack.yaml 
spack env activate ${ENVPATH} 
spack add -l compilers "%${COMPILER_SPEC}"
spack add -l compiler_libs "$@"
spack concretize -f 
spack fetch --deprecated 
spack env deactivate
