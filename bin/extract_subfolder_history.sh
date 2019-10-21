#|/bin/bash

export PREFIX=dummy_prefix_dir
export WORK_FOLDER=/tmp/work_dir
export CLONE_URL=https://github.com/RemoteConnectionManager/RCM_spack_deploy.git 
export SUBFOLDERS_common="bin lib config"
export SUBFOLDERS_rcm="repo/packages/rcm repo/packages/lxde-icon-theme"
export SUBFOLDERS_cineca="recipes/hosts/galileo recipes/hosts/marconi recipes/hosts/davide recipes/hosts/pico"


if [ ! -d $WORK_FOLDER ]; then
  mkdir $WORK_FOLDER
fi

cd $WORK_FOLDER
if [ ! -d $WORK_FOLDER/original ]; then
  git clone $CLONE_URL original
fi

if [ ! -d $WORK_FOLDER/rewrite_history ]; then
  mkdir rewrite_history
  cd rewrite_history
  git init
  git pull ../original

  git filter-branch --index-filter 'git ls-files -s | sed "s,\t,&'"$PREFIX"'/," | GIT_INDEX_FILE=$GIT_INDEX_FILE.new git update-index --index-info  && mv $GIT_INDEX_FILE.new $GIT_INDEX_FILE ' HEAD
fi

for repo in common cineca rcm
 do
  export SUBFOLDERS_PATTERN=""
  eval "SUBFOLDERS=\${SUBFOLDERS_$repo}"

  for i in $SUBFOLDERS
   do
    PAT="^$PREFIX/$i/"
    if [ "x$SUBFOLDERS_PATTERN" == "x" ]; then
      export SUBFOLDERS_PATTERN=$PAT
    else
      export SUBFOLDERS_PATTERN="${SUBFOLDERS_PATTERN}\\|${PAT}"
    fi
   done
  echo "######### $repo sub pattern $SUBFOLDERS_PATTERN"

  cd $WORK_FOLDER
  if [ ! -d ${WORK_FOLDER}/$repo ]; then
    mkdir ${WORK_FOLDER}/$repo
  fi
  cd ${WORK_FOLDER}/$repo
  if [ ! -d ${WORK_FOLDER}/$repo/cleaned ]; then
    mkdir cleaned
    cd cleaned
    git init
    git pull ../../rewrite_history
  
    #COMMAND="git filter-branch --index-filter 'git\ ls-files\ \|\ grep\ -v\ \"$SUBFOLDERS_PATTERN\"\ \|\ xargs\ --no-run-if-empty\ git\ rm\ --cached'\; HEAD"
    #echo "executing--->$COMMAND<---"
    #$COMMAND
    SUBCOMMAND="'git ls-files | grep -v \"$SUBFOLDERS_PATTERN\" | xargs --no-run-if-empty git rm --cached'"
    echo "executing--->git filter-branch --index-filter $SUBCOMMAND; HEAD<---"
    #git filter-branch --index-filter $SUBCOMMAND HEAD
    git filter-branch --index-filter 'git ls-files | grep -v "$SUBFOLDERS_PATTERN" | xargs --no-run-if-empty git rm --cached'; HEAD
  fi
  
  cd  ${WORK_FOLDER}/$repo
  if [ ! -d ${WORK_FOLDER}/$repo/moved ]; then
    mkdir moved
    cd moved
    git init
    git pull ../cleaned
    git subtree split -P $PREFIX -b clean
    git checkout clean
  fi
done
