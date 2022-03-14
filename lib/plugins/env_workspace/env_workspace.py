import os
import glob
import logging
import copy
import utils
import cascade_yaml_config
import json

logging.debug("__file__:" + os.path.realpath(__file__))

for h in cascade_yaml_config.CascadeYamlConfig.instances:
  spack_version = cascade_yaml_config.CascadeYamlConfig.instances[h][['defaults','spack_version']]
  generated_subdir = cascade_yaml_config.CascadeYamlConfig.instances[h][['defaults','generated_subdir']]

cascade_yaml_config.global_key_subst['DEPLOY_GENERATED_DIR'] = os.path.join(
                            cascade_yaml_config.global_key_subst['DEPLOY_PARENT_PARENT_ROOTPATH'],
                            generated_subdir,
                            spack_version + '_' + cascade_yaml_config.global_key_subst['DEPLOY_WORKNAME'])

def is_workdir(path):
    ret = False
    for subpath in ['defaults.yaml', 'spack.yaml']:
        ret = ret or os.path.exists(os.path.join(path, subpath))
    return ret

class EnvWorkspaceManager(cascade_yaml_config.ArgparseSubcommandManager):

    def __init__(self, **kwargs):
        super(EnvWorkspaceManager, self).__init__(**kwargs)
        join_string= "\n    "
        for par in kwargs:
            out = "init par "+ par+" --> "
            if isinstance(kwargs[par], list):
                out += join_string + join_string.join(kwargs[par])
            else:
                out += str(kwargs[par])
            self.logger.debug(out)


    def list_spack_roots(self, spack_roots=''):
        if not spack_roots:
            spack_roots = self.base_path
        else:
            if spack_roots[0] != '/':
                spack_roots = os.path.join(self.base_path, spack_roots)
        spack_roots = os.path.abspath(spack_roots)
        print('Searching workspaces into:', spack_roots)
        for root, dirs, files in os.walk(spack_roots, topdown=True):
            if utils.is_spack_root(root):
                print(" OOOOOOOOOOOOO list OOOOO found spack folder ", root)
                dirs[:] = []



    def list(self, base_env=''):
        if not base_env:
            base_env = self.base_path
        print('The current workdirs found in ' + self.base_path + ' are:')
        count = 0
        for root, dirs, files in os.walk(base_env, topdown=True):
            if is_workdir(root):
                rel_path = os.path.relpath(root, base_env)
                deployed_path =  os.path.abspath(os.path.join(cascade_yaml_config.parent_root_path, 'deploy',  rel_path))
                printline = "  " + str(count) + " : " + os.path.relpath(root, base_env)
                if os.path.exists(deployed_path): printline += " -->" + deployed_path
                #else: printline += " MISSING -->" + deployed_path
                print(printline)
                count += 1
                dirs[:] = []

    def _merge_yaml_file_into_dict(self,
                          merge_config_folders,
                          yaml_file): 
        print("-------------- " + yaml_file)
        merge_files=[]
        for p in merge_config_folders:
            test=os.path.abspath(os.path.join(p,yaml_file))
            if os.path.exists(test):
                 print("#### config file: " + test)
                 merge_files = merge_files +[test]

        if merge_files :
            self.logger.debug("configuring "+ yaml_file + " with files: "+str(merge_files))

            merged_f = utils.hiyapyco.load(
                *merge_files,
                interpolate=True,
                method=utils.hiyapyco.METHOD_MERGE,
                failonmissingfiles=True
            )
            return(merged_f)
        else:
            self.logger.info("no template file for "+ yaml_file + " : skipping ")

    def _merge_yaml_files(self,
                          merge_config_folders,
                          current_key_subst, 
                          spack_config_dir,
                          clearconfig,
                          yaml_files): 

        if os.path.exists(spack_config_dir) :

            if clearconfig:
                self.logger.info("Clear config Folder ->"+spack_config_dir+"<-")
                for f in glob.glob(spack_config_dir+ "/*.yaml"):
                    if self.dry_run:
                        print("##### dry run remove: " + f )
                    else:
                        print("##### removing: " + f )
                        os.remove(f)


            for f in yaml_files :
                print("-------------- " + f)
                merge_files=[]
                for p in merge_config_folders:
                    test=os.path.abspath(os.path.join(p,f))
                    if os.path.exists(test):
                         print("#### config file: " + test)
                         merge_files = merge_files +[test]

                if merge_files :
                    self.logger.debug("configuring "+ f + " with files: "+str(merge_files))

                    merged_f = utils.hiyapyco.load(
                        *merge_files,
                        interpolate=True,
                        method=utils.hiyapyco.METHOD_MERGE,
                        failonmissingfiles=True
                    )

                    self.logger.debug("merged "+f+" yaml-->"+str(merged_f)+"<--")

                    outfile = os.path.basename(f)
                    target = os.path.join(spack_config_dir, outfile)
                    self.logger.debug(" output config_file " + outfile + "<-- ")
                    if not os.path.exists(target):
                        out=utils.hiyapyco.dump(merged_f, default_flow_style=False)
                        out = utils.stringtemplate(out).safe_substitute(current_key_subst)
                        if self.dry_run:
                            print("##### dry run write: " + target )
                        else:
                            self.logger.info("WRITING config_file " + outfile + " -->" + target + "<-- ")
                            open(target, "w").write(out)
                else :
                    self.logger.info("no template file for "+ f + " : skipping ")


    def _upstream_owner_spack_setup(self,spack_root,install,cache,modules, user_cache):
        current_key_subst = copy.deepcopy(cascade_yaml_config.global_key_subst)
        current_key_subst['DEPLOY_SPACK_CACHE'] = cache
        os.environ['SPACK_ROOT_CACHE'] = cache
        current_key_subst['DEPLOY_SPACK_INSTALL'] = install
        os.environ['SPACK_ROOT_INSTALL'] = install
        current_key_subst['DEPLOY_SPACK_MODULES'] = modules
        os.environ['SPACK_ROOT_MODULES'] = modules
        
        if user_cache :
            current_key_subst['DEPLOY_SPACK_USER_CACHE_PATH'] = user_cache
            os.environ['SPACK_USER_CACHE_PATH'] = user_cache
            self.logger.warning("Spack commands should use SPACK_USER_CACHE_PATH  to: " + user_cache)
        for subst_key in current_key_subst:
            utils.hiyapyco.jinja2env.globals[subst_key] = current_key_subst[subst_key]

        ret =  utils.source(os.path.join(spack_root,'share','spack','setup-env.sh'))
        if ret:
            self.logger.warning("Spack setup env failed  EXITING ")
            exit(1) 
        

    def config_setup(self,
                     spack_root='spack',
                     out_config_dir = os.path.join('etc','spack'),
                     merge_config_folders = [],
                     cache='cache',
                     install='install',
                     modules='modules',
                     user_cache='user_cache',
                     spack_commands=[],
                     clearconfig=True,
                     runconfig=False):

        # print("@@@@@@@@@@@@@@@@@@@@",self.dry_run)
        if spack_root [0] != '/':
            dest = os.path.join(self.base_path, spack_root)
        else:
            dest = spack_root

        current_key_subst = self._upstream_owner_spack_setup(dest,install,cache,modules, user_cache)

#        current_key_subst = copy.deepcopy(cascade_yaml_config.global_key_subst)
#        current_key_subst['DEPLOY_SPACK_CACHE'] = cache
#        current_key_subst['DEPLOY_SPACK_INSTALL'] = install
#        current_key_subst['DEPLOY_SPACK_MODULES'] = modules
#        if user_cache :
#            current_key_subst['DEPLOY_SPACK_USER_CACHE_PATH'] = user_cache
#            os.environ['SPACK_USER_CACHE_PATH'] = user_cache
#            self.logger.warning("Spack commands should use SPACK_USER_CACHE_PATH  to: " + user_cache)
#        for subst_key in current_key_subst:
#            utils.hiyapyco.jinja2env.globals[subst_key] = current_key_subst[subst_key]


#        if spack_commands :
#           ret =  utils.source(os.path.join(spack_root,'share','spack','setup-env.sh'))
#           if ret:
#               self.logger.warning("Spack setup env failed and spack commands not empty EXITING ")
#               return(1) 

        if out_config_dir:
            if out_config_dir[0] != '/':
                spack_config_dir = os.path.abspath(os.path.join(dest, out_config_dir))
            else:
                if not os.path.exists(out_config_dir) : os.makedirs(out_config_dir)
                spack_config_dir = out_config_dir

        if os.path.exists(spack_config_dir) :
            self._merge_yaml_files(merge_config_folders,
                              current_key_subst, 
                              spack_config_dir, 
                              clearconfig,
                              self.manager_conf.get('config', dict()).get('spack_yaml_files',[]))

            for command in spack_commands:
                templ= utils.stringtemplate(command)
                cmd=templ.safe_substitute(current_key_subst)
                if self.dry_run or not runconfig :
                    if self.dry_run:
                        print("############## dry run  executing: " + cmd) 
                    if not runconfig:
                        print("############## skipping  executing: " + cmd) 
                else:
                    (ret,out,err)=utils.run(cmd.split(),logger=self.logger,pipe_output=True)
                    self.logger.info("  " + out )


    def generate_env(self,
                     spack_root='spack',
                     merge_config_folders = [],
                     user_cache='user_cache',
                     cache='cache',
                     install='install',
                     modules='modules',
                     clearconfig=True,
                     separate_files=False,
                     spackfile='spack.yaml'):


        current_key_subst = self._upstream_owner_spack_setup(spack_root,install,cache,modules, user_cache)



        env_dict = self._merge_yaml_file_into_dict( merge_config_folders, 'env.yaml')
        for envname in env_dict:
            susbstitutions_info = env_dict[envname].get('substitutions', {})
            #substitutions = copy.deepcopy(cascade_yaml_config.global_key_subst)
            substitutions={}
            substitutions['DEPLOY_DOUBLE_COLON_HACK'] = ':'
            substitutions['DEPLOY_GENERATED_PREFIX'] = envname

            # parse explicit substitutions
            explicit_subst_info = susbstitutions_info.get('explicit', [])
            for subst_info in explicit_subst_info:
                for key in subst_info:
                    value = subst_info[key]
                    subst_value = utils.stringtemplate(value).safe_substitute(substitutions)
                    print("adding: "+ key + " value: " + value + " -->" + subst_value)
                    substitutions[key] =  subst_value

            # parse accumulators (list) substitutionsnd convert them into space separated string
            # TODO: allow for customizable separator
            accumulators_info = susbstitutions_info.get('accumulators', [])
            for subst_info in accumulators_info:
                for key in subst_info:
                    values = subst_info[key]
                    values_string = ''
                    for value in values:
                        values_string += utils.stringtemplate(value).safe_substitute(substitutions) + ' '
                    substitutions[key] =  values_string

            # parse commands: each command must return on stdout a  json string represting a dict for substitutions
            # init_command is a single entry that can be overriden by hiyapico simple overriding, while commands is a list, where files in different dirs
            # can add but not override
            substitution_commands = []
            init_command = susbstitutions_info.get('init_command', '')
            if init_command: 
                substitution_commands.append(init_command)
            for c in susbstitutions_info.get('commands', []):
                substitution_commands.append(c)
            print(substitution_commands)
            if substitution_commands:
                ret =  utils.source(os.path.join(spack_root,'share','spack','setup-env.sh'))

            for command in substitution_commands:
                subst_command = utils.stringtemplate(command).safe_substitute(substitutions)
                self.logger.info("executing substitution command--> " + subst_command)
                (ret,out,err)=utils.run(subst_command.split(),logger=self.logger,pipe_output=True)
                if out:
                    subst_from_command = json.loads(out)
                    substitutions.update(subst_from_command)
            self.logger.debug("Active substitutions:")
            for key in substitutions:
                self.logger.debug(key + " --> " + substitutions[key])
            spack_env_info = env_dict[envname]['spack']
            spack_env=utils.hiyapyco.dump({'spack': spack_env_info}, default_flow_style=False)
            spack_env_subst = utils.stringtemplate(spack_env).safe_substitute(substitutions)
            spack_env_dir = utils.stringtemplate('@{GENERATED_ENV_FOLDER}').safe_substitute(substitutions)
            if not os.path.exists(spack_env_dir) : os.makedirs(spack_env_dir)
            open(os.path.join(spack_env_dir, 'spack.yaml'), "w").write(spack_env_subst)
            self.logger.info("written " + os.path.join(spack_env_dir, 'spack.yaml'))
     

            ####   write out build and post command shell files,
            ####   header taken from defined headerfile
            headerfile = env_dict[envname].get('headerfile', '')
            header='#!/bin/bash \n'
            if headerfile:
                if os.path.exists(headerfile):
                    with open(headerfile, 'r') as h:
                        header = h.read()
            if user_cache :
                header += ('export SPACK_USER_CACHE_PATH="' + user_cache + '"\n')
            header += ('export SPACK_ROOT_CACHE="' + cache + '"\n')
            header += ('export SPACK_ROOT_INSTALL="' + install + '"\n')
            header += ('export SPACK_ROOT_MODULES="' + modules + '"\n')

            header += ('source ' + os.path.join(spack_root,'share','spack','setup-env.sh') + '\n')
            
            command_phases = {'PRE':   env_dict[envname].get('pre_commands', []),
                              'BUILD': env_dict[envname].get('build_commands', []),
                              'POST':  env_dict[envname].get('post_commands', [])}

            if not separate_files :
                f = open(os.path.join(spack_env_dir,'build.sh'), 'w')                
                f.write(header)
            for phase in command_phases:
                if separate_files :
                    f = open(os.path.join(spack_env_dir, phase + '.sh'), 'w')                
                    f.write(header)
                f.write('# phase: ' + phase + '\n')
                for command in command_phases[phase]:
                    cmd = utils.stringtemplate(command).safe_substitute(substitutions)
                    f.write(cmd + '\n')
                if separate_files :
                    f.close()
            if not separate_files :
                f.close()

