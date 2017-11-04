#!/bin/bash
RCM_DEPLOY_CURRENT_PATH=deploy/rcm_client/15/spack

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symli
nk
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symli
nk, we need to resolve it relative to the path where the symlink file was locate
d
done
export RCM_DEPLOY_HOSTPATH="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
source ${RCM_DEPLOY_HOSTPATH}/../../../../get_root


python ${RCM_DEPLOY_ROOTPATH}/scripts/config.py -c config config/shared_install config/rcm config/rcm/client config/rcm/client/linux  --platformconfig --runconfig --dest ${RCM_DEPLOY_CURRENT_PATH=}
source ${RCM_DEPLOY_ROOTPATH}/${RCM_DEPLOY_CURRENT_PATH=}/share/spack/setup-env.sh

