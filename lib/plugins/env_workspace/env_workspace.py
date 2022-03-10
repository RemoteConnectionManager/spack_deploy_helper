import os
import glob
import logging
import copy
import utils
import cascade_yaml_config

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
        current_key_subst = copy.deepcopy(cascade_yaml_config.global_key_subst)
        current_key_subst['DEPLOY_SPACK_CACHE'] = cache
        current_key_subst['DEPLOY_SPACK_INSTALL'] = install
        current_key_subst['DEPLOY_SPACK_MODULES'] = modules
        if user_cache :
            current_key_subst['DEPLOY_SPACK_USER_CACHE_PATH'] = user_cache
            os.environ['SPACK_USER_CACHE_PATH'] = user_cache
            self.logger.warning("Spack commands should use SPACK_USER_CACHE_PATH  to: " + user_cache)
        for subst_key in current_key_subst:
            utils.hiyapyco.jinja2env.globals[subst_key] = current_key_subst[subst_key]

        if spack_root [0] != '/':
            dest = os.path.join(self.base_path, spack_root)
        else:
            dest = spack_root

        if spack_commands :
           ret =  utils.source(os.path.join(spack_root,'share','spack','setup-env.sh'))
           if ret:
               self.logger.warning("Spack setup env failed and spack commands not empty EXITING ")
               return(1) 

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
                     outdir='/tmp/prova_env',
                     headerfile='',
                     pre_commands=[],
                     build_commands=[],
                     post_commands=[],
                     clearconfig=True,
                     separate_files=False,
                     spackfile='spack.yaml'):


        current_key_subst = copy.deepcopy(cascade_yaml_config.global_key_subst)

        if user_cache :
            os.environ['SPACK_USER_CACHE_PATH'] = user_cache

        for subst_key in current_key_subst:
            utils.hiyapyco.jinja2env.globals[subst_key] = current_key_subst[subst_key]


        if pre_commands or build_commands or post_commands :
           ret =  utils.source(os.path.join(spack_root,'share','spack','setup-env.sh'))
           if ret:
               self.logger.warning("Spack setup env failed and spack commands not empty EXITING ")
               return(1) 

        if outdir:
            if outdir[0] != '/':
                spack_config_dir = os.path.abspath(os.path.join(dest, outdir))
            else:
                if not os.path.exists(outdir) : os.makedirs(outdir)
                spack_config_dir = outdir

        if os.path.exists(outdir) :
            self._merge_yaml_files(merge_config_folders,
                              current_key_subst, 
                              outdir, 
                              clearconfig,
                              [spackfile])

            header='#!/bin/bash \n'
            if headerfile:
                if os.path.exists(headerfile):
                    with open(headerfile, 'r') as h:
                        header = h.read()
            if user_cache :
                header += ('export SPACK_USER_CACHE_PATH="' + user_cache + '"\n')
            header += ('source ' + os.path.join(spack_root,'share','spack','setup-env.sh') + '\n')
            
            command_phases = {'PRE': pre_commands, 'BUILD': build_commands, 'POST': post_commands}
            if not separate_files :
                f = open(os.path.join(outdir,'build.sh'), 'w')                
                f.write(header)
            for phase in command_phases:
                if separate_files :
                    f = open(os.path.join(outdir,'build_' + phase + '.sh'), 'w')                
                    f.write(header)
                f.write('# phase: ' + phase + '\n')
                for command in command_phases[phase]:
                    templ= utils.stringtemplate(command)
                    cmd=templ.safe_substitute(current_key_subst)
                    f.write(cmd + '\n')
                if separate_files :
                    f.close()
            if not separate_files :
                f.close()
#            with open(os.path.join(outdir,'build.sh'), 'w') as f:
        #        f.write(str(current_key_subst))
#                f.write(header)
#                for phase in command_phases:
#                    f.write('# phase: ' + phase + '\n')
#                    for command in command_phases[phase]:
#                        templ= utils.stringtemplate(command)
#                        cmd=templ.safe_substitute(current_key_subst)
#                        f.write(cmd + '\n')

