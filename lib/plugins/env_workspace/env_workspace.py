import os
import glob
import logging
import copy
import utils
import cascade_yaml_config
import json
import re

logging.debug("__file__:" + os.path.realpath(__file__))

spack_version = ''
generated_subdir = ''
for h in cascade_yaml_config.CascadeYamlConfig.instances:
  _spack_version = cascade_yaml_config.CascadeYamlConfig.instances[h][['defaults','spack_version']]
  _generated_subdir = cascade_yaml_config.CascadeYamlConfig.instances[h][['defaults','generated_subdir']]
  if _spack_version: spack_version = _spack_version
  if _generated_subdir: generated_subdir = _generated_subdir

cascade_yaml_config.global_key_subst['DEPLOY_GENERATED_DIR'] = os.path.join(
                            cascade_yaml_config.global_key_subst['DEPLOY_PARENT_PARENT_ROOTPATH'],
                            generated_subdir,
                            spack_version + '_' + cascade_yaml_config.global_key_subst['DEPLOY_WORKNAME'])
def is_workdir(path):
    ret = False
    for subpath in ['defaults.yaml', 'spack.yaml']:
        ret = ret or os.path.exists(os.path.join(path, subpath))
    return ret

class CustomYamlMerger(object):
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger("CustomYamlMerger")
        self.references={}
        self.ref_regex = re.compile(r"@REF{([^}]*)}")

    def print_curr_reference(self):
        self.logger.debug("#### current refernce dict:")
        self.logger.debug(str(self.references))

    def _parse_yaml_dict(self,yaml_dict, path=''):
        classname = yaml_dict.__class__.__name__
        #print(path + ' --> ' + yaml_dict.__class__.__name__)
        if classname == 'list':
            simple=True
            for element in yaml_dict:
                if element.__class__.__name__ == 'OrderedDict':
                    simple=False
                    #for key in element:
                    #    newpath = path + '.' + key
                    #    print("### recursive list call: " + newpath)
                    #    self._parse_yaml_dict(element[key], path=newpath)
                    self._parse_yaml_dict(element, path=path)
            if simple:
                self.logger.debug("###SIMPLE LIST: " + path + ' --> ' + str(yaml_dict))
                pass
            return()
            
        if classname == 'OrderedDict':
            for key in yaml_dict:
                if path : 
                    newpath = path + '.' + key
                else:
                    newpath = key
                if newpath in self.references:
                    if self.references[newpath] == newpath:
                        self.logger.info("registering " + newpath )
                        #self.logger.debug( str(yaml_dict[key]))
                        self.references[newpath] = yaml_dict[key]
                #print("##key## "+key+" type: " + yaml_dict[key].__class__.__name__)
                if yaml_dict[key].__class__.__name__ == 'str':
                    #print("###########----> " + yaml_dict[key])
                    m = self.ref_regex.match(yaml_dict[key])
                    if m:
                        ref_name = m.group(1)
                        if ref_name in self.references:
                            if self.references[ref_name] == ref_name:
                                self.logger.debug("Waiting to fill reference: " + ref_name)
                            else:
                                self.logger.info("Substituting " + newpath)
                                yamllines = utils.hiyapyco.dump(self.references[ref_name], default_flow_style=False).split('\n')
                                if len(yamllines) > 9:
                                    for s in yamllines[:4]:
                                        self.logger.debug("    " + s)
                                    self.logger.debug("   ............")
                                    for s in yamllines[-4:]:
                                        self.logger.debug("    " + s)
                                else:
                                    for s in yamllines:
                                        self.logger.debug("    " + s)
                                   
                                yaml_dict[key] = copy.deepcopy(self.references[ref_name])
                        else:
                            self.logger.debug("Found: " + ref_name)
                            self.references[ref_name] = ref_name
                    else:
                        self._parse_yaml_dict(yaml_dict[key], path=newpath)
                else:
                    self._parse_yaml_dict(yaml_dict[key], path=newpath)
            return()
        else:
            self.logger.debug("@@@@@@ got classname:" + classname + " path: "+ path + " ---> " + str(yaml_dict))

        #print("######path: " + path + " ---> " + str(yaml_dict))

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
                          yaml_file,
                          interpolate=True,
                          do_ref_subst=False): 
        merge_files=[]
        for p in merge_config_folders:
            test=os.path.abspath(os.path.join(p,yaml_file))
            if os.path.exists(test):
                 self.logger.debug("#### config file: " + test)
                 merge_files = merge_files +[test]

        if merge_files :
            self.logger.debug("configuring "+ yaml_file + " with files: "+str(merge_files))

            if do_ref_subst:
                self.logger.debug("#######  doing ref subst #######")
                merge_strings = []
                current_merged_string=''
                for f in merge_files:
                #for i in range(len(merge_files)):
                #    files = merge_files[:i+1]
                #    print("### doing rf subst for file: " + str(files))
                    self.logger.info("### doing rf subst for file: " + f)
                    if current_merged_string:
                        to_load = [current_merged_string, f]
                    else:
                        to_load = [f]
                    file_dict = utils.hiyapyco.load(
                        *to_load,
                    #    f,
                    #    *files,
                        interpolate=False,
                        method=utils.hiyapyco.METHOD_MERGE,
                        failonmissingfiles=True
                    )
                    merger = CustomYamlMerger(logger=self.logger)
                    #print(env_dict) 
                    #print("### 0 #####")
                    #merger.print_curr_reference()
                    merger._parse_yaml_dict(file_dict)
                    self.logger.debug("### 1 #####")
                    merger.print_curr_reference()
                    merger._parse_yaml_dict(file_dict)
                    self.logger.debug("### 2 #####")
                    merger.print_curr_reference()
                    self.logger.debug("@@@@@@@@@@@@@@@@@@@@@ dict @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n" +
                                      str(file_dict) +
                                      "\n###################################################################### #####")
                    current_merged_string = utils.hiyapyco.dump(file_dict, default_flow_style=False)
                    self.logger.debug("@@@@@@@@@@@@@@@@@@@@@ current_merged_string @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n" + current_merged_string)

                    merge_strings.append(current_merged_string)

                merged_f = utils.hiyapyco.load(
                    current_merged_string,
                    #*merge_strings,
                    interpolate=interpolate,
                    method=utils.hiyapyco.METHOD_MERGE,
                    failonmissingfiles=True
                )
 
                    
            else:
                merged_f = utils.hiyapyco.load(
                    *merge_files,
                    interpolate=interpolate,
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
                merge_files=[]
                for p in merge_config_folders:
                    test=os.path.abspath(os.path.join(p,f))
                    if os.path.exists(test):
                         self.logger.info("#### config file: " + test)
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
            self.logger.info("Spack commands should use SPACK_USER_CACHE_PATH  to: " + user_cache)
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
                     spack_commands=[],
                     skip_steps=[],
                     clearconfig=True):

        def to_skip(skip_steps,step_name):
            skip = 'env' != step_name[0:3] and step_name != 'config'
            for step_to_skip in skip_steps:
                if step_to_skip in step_name:
                    self.logger.info("skipping step: " + step_name)
                    skip = True
                    break
            return skip

        if spack_root [0] != '/':
            spack_root = os.path.join(self.base_path, spack_root)

        spack_config_dir = os.path.abspath(os.path.join(spack_root, 'etc','spack'))
        current_key_subst = self._upstream_owner_spack_setup(spack_root,install,cache,modules, user_cache)


        if os.path.exists(spack_config_dir) and not to_skip(skip_steps,'config') :
            self.logger.info("processing config")
            self._merge_yaml_files(merge_config_folders,
                              current_key_subst, 
                              spack_config_dir, 
                              clearconfig,
                              self.manager_conf.get('config', dict()).get('spack_yaml_files',[]))

            for command in spack_commands:
                templ= utils.stringtemplate(command)
                cmd=templ.safe_substitute(current_key_subst)
                if self.dry_run :
                    print("############## dry run  executing: " + cmd) 
                else:
                    (ret,out,err)=utils.run(cmd.split(),logger=self.logger,pipe_output=True)
                    self.logger.info("  " + out )
        else:
            self.logger.info("skipping config" )

        env_dict = self._merge_yaml_file_into_dict( sorted(merge_config_folders), 'env.yaml',interpolate=True, do_ref_subst=True)
        merger = CustomYamlMerger(logger=self.logger)

        for envname in env_dict:
            if to_skip(skip_steps,envname):
                self.logger.debug("skipping step: " + envname)
                continue 
            else:
                self.logger.info("processing step: " + envname)
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
                    self.logger.debug("adding: "+ key + " value: " + value + " -->" + subst_value)
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
            self.logger.debug(str(substitution_commands))
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
            immediate = env_dict[envname].get('immediate', 'pre')
            separate_files = env_dict[envname].get('separate_files', False)
            execute_at_end = env_dict[envname].get('execute_at_end', False)

            command_phases = {'PRE':   env_dict[envname].get('pre_commands', []),
                              'BUILD': env_dict[envname].get('build_commands', []),
                              'POST':  env_dict[envname].get('post_commands', [])}


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
            
            last_file = '' 
            phase_files=[]
            for phase in ('PRE','BUILD','POST'):
                if separate_files :
                    curr_file = os.path.join(spack_env_dir, phase + '.sh')
                else:
                    curr_file = os.path.join(spack_env_dir,'build.sh')
                write_on_file = { 'none': True, 'all': False}.get(immediate, phase.lower() != immediate)
                if write_on_file:
                    if curr_file != last_file:
                        last_file = curr_file
                        self.logger.info("writing on  " + curr_file)
                        f = open(curr_file, 'w')
                        f.write(header)
                    f.write('# phase: ' + phase + '\n')
                    
                for command in command_phases[phase]:
                    cmd = utils.stringtemplate(command).safe_substitute(substitutions)
                    if write_on_file:
                        f.write(cmd + '\n')
                    else:
                        (ret,out,err)=utils.run(cmd.split(),logger=self.logger,pipe_output=True)
                if separate_files :
                    f.close()
                    phase_files.append(curr_file)
            if not separate_files :
                f.close()
                phase_files.append(curr_file)
            if execute_at_end:
                for shellfile in phase_files:
                    self.logger.info("Executing  " + shellfile)
                    (ret,out,err)=utils.run(['/bin/bash', shellfile],logger=self.logger,pipe_output=True)
                    

