#!/usr/bin/env bash
spack repo add @{RCM_DEPLOY_ROOTPATH}/repo --scope site
spack info rcm
spack install --only dependencies rcm
spack install rcm@dev
#spack uninstall -y rcm@develop
#spack diy --source-path @{RCM_DEPLOY_ROOTPATH}/../RCM rcm@develop

