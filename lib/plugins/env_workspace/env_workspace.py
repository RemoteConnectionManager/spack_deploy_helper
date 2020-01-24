import os
import shutil
import uuid
import logging

import utils
import cascade_yaml_config

logging.debug("__file__:" + os.path.realpath(__file__))

def is_workdir(path):
    ret = False
    for subpath in ['defaults.yaml', 'spack.yaml']:
        ret = ret or os.path.exists(os.path.join(path, subpath))
    return ret

class EnvWorkspaceManager(cascade_yaml_config.ArgparseSubcommandManager):

    def __init__(self, **kwargs):
        super(EnvWorkspaceManager, self).__init__(**kwargs)
        for par in kwargs:
            self.logger.debug("init par "+ par+" --> "+str(kwargs[par]))




    def list(self, base_env=''):
        if not base_env:
            base_env = self.base_path
        print('The current workdirs found in ' + self.base_path + ' are:')
        count = 0
        for root, dirs, files in os.walk(base_env, topdown=True):
            if is_workdir(root):
                rel_path = os.path.relpath(root, base_env)
                deployed_path =  os.path.abspath(os.path.join(cascade_yaml_config.parent_root_path, 'deploy', 'environments', rel_path))
                printline = "  " + str(count) + " : " + os.path.relpath(root, base_env)
                if os.path.exists(deployed_path): printline += " -->" + deployed_path
                #else: printline += " MISSING -->" + deployed_path
                print(printline)
                count += 1
                dirs[:] = []

