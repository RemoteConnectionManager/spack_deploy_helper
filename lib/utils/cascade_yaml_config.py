# stdlib
import sys
import os
import pwd
import logging
import copy
import glob
from collections import OrderedDict
import argparse
import inspect
import importlib

lib_path = os.path.dirname((os.path.dirname(os.path.abspath(__file__))))
if lib_path not in sys.path:
    sys.path.append(lib_path)
import utils
import log_config

root_path = os.path.dirname(lib_path)
parent_root_path = os.path.dirname(root_path)
parent_parent_root_path = os.path.dirname(parent_root_path)
current_username = pwd.getpwuid( os.getuid() )[ 0 ]
tmpdir = os.environ.get('TMPDIR','/tmp')
global_key_subst = {'DEPLOY_USERNAME': current_username,
                    'DEPLOY_ROOTPATH': root_path,
                    'DEPLOY_PARENT_ROOTPATH': parent_root_path,
                    'DEPLOY_PARENT_PARENT_ROOTPATH': parent_parent_root_path,
                    'DEPLOY_TMPDIR': tmpdir,
                    'DEPLOY_LIBPATH': lib_path}
logger = logging.getLogger(__name__)

def formatter(prog):
    return argparse.ArgumentDefaultsHelpFormatter( prog, max_help_position=200, width=1000)

def yaml_environment_import(varlist=[]):
    import  utils.external.jinja2
    env=dict()
    for v in varlist:
        if v in os.environ:
            env[v] = os.environ[v]
    utils.hiyapyco.jinja2env.globals =  {'env' : env}

def abs_deploy_path(path, 
                    prefixes=[],
                    subst=global_key_subst):
    subst_path = utils.stringtemplate(path).safe_substitute(subst)
    out_path = subst_path
    if '/' != subst_path[0]:
        for prefix in prefixes:
            out_path = os.path.join(prefix, subst_path)
            if os.path.exists(subst_path):
                break
    return os.path.abspath(out_path)

def retrieve_plugins(plugin_folders):
    out_plugins = dict()
    for plugin_folder in plugin_folders:
        if '/' != plugin_folder[0]:
            plugin_folder = os.path.join(lib_path, plugin_folder)
        logger.debug("@@@@@@ list_plugins @@@@@"+plugin_folder)
        modules = dict()
        if os.path.isdir(plugin_folder):
            if plugin_folder not in sys.path:
                logger.info("adding " + plugin_folder + " to sys path")
                sys.path.append(plugin_folder)
            for plugfile in glob.glob(os.path.join(plugin_folder, '*.py')) :
                logger.info("importing plugfile: " + plugfile + " : " + os.path.basename(plugfile))
                #print("##################importing plugfile",plugfile,os.path.basename(plugfile))
                modules[plugfile] = importlib.import_module(os.path.splitext(os.path.basename(plugfile))[0])
                for name,cls in inspect.getmembers( modules[plugfile], inspect.isclass):
                    if issubclass(cls,ArgparseSubcommandManager):
                        logger.info("Found ArgparseSubcommandManager: " + name)
                        logger.debug("@@@@@@@@ " + str(out_plugins))
                        out_plugins[plugin_folder] = out_plugins.get(plugin_folder,[]) + [cls]
                        logger.debug("@@@--@@@ " + str(out_plugins))
    return out_plugins



def merge_folder_list(in_folders, merge_folders=None, prefixes=None, remove_and_add_when_present=False):

    if merge_folders is None:
        merge_folders = []
    if prefixes is None:
        prefixes = [os.getcwd()]

    # need do deepcoy, otherwise infinite loop
    current_folders = copy.deepcopy(in_folders)
    for in_path in merge_folders:
        # print("@@@@@@@@@@ in_path @@@@",in_path)
        logger.debug("config folder:" + in_path)
        if in_path[0] != '/':
            for base in prefixes:
                if os.path.exists(os.path.join(base, in_path)):
                    if os.path.isdir(os.path.join(base, in_path)):
                        in_path = os.path.abspath(os.path.join(base, in_path))
                        break
        # print("######",current_folders)
        if in_path not in current_folders:
            current_folders.append(str(in_path))
        else:
          if remove_and_add_when_present:
              current_folders.remove(str(in_path))
              current_folders.append(str(in_path))

    return current_folders


def setup_from_args_and_configs(log_controller=None):
    """
    This function parse predefined args in hierarchical order, accumulating default parameters and
    by parsing known config files
    return a triple consisting of:
    base_parser:      base command line parser
    config_folders:   list of config folders used for setup
    plugin_folders:   list of plugin folders used for setup
    platform_folders: list of platform folders used for setup
    """

    if log_controller == None:
        log_controller = log_config.log_setup()

    # base parser
    base_parser = argparse.ArgumentParser(add_help=False)
    # this is the base workspace folder, containing a config file, named defaults.yaml, this file should accumulate the history
    # of the subcommands configs, so it should
    base_parser.add_argument('-w', '--workdir', action='store', help='workspace folder', default=os.getcwd())

    # partial parsing of known args
    base_args = base_parser.parse_known_args()[0]

    #log_controller.set_args()

    if base_args.workdir[0] == '/':
        work_dir = os.path.abspath(base_args.workdir)
        env_dir = work_dir
    else:
        logger.warning(" workdir path is not absolute-->" + base_args.workdir + "<--")
        work_dir = os.path.abspath(os.path.join(os.getcwd(), base_args.workdir))
        if os.path.exists(work_dir):
            env_dir = work_dir
        else:
            work_dir = os.path.join(parent_root_path, 'deploy', base_args.workdir)
            env_dir = os.path.join(parent_root_path, 'environments', base_args.workdir)
        logger.warning(" setting output work folder to -->" + work_dir + "<--")
        logger.warning(" setting input environment folder to -->" + env_dir + "<--")

    global_key_subst['DEPLOY_WORKDIR'] = work_dir
    global_key_subst['DEPLOY_WORKNAME'] = os.path.basename(work_dir)
    projects_path = os.path.normpath(os.path.join(parent_root_path, 'projects'))
    if os.path.exists(projects_path):
        global_key_subst['DEPLOY_PROJECTS_PATH'] = projects_path
        project = os.path.normpath(os.path.relpath(os.path.normpath(work_dir), os.path.normpath(projects_path))).split(os.path.sep)[0]
        if os.pardir != project:
            global_key_subst['DEPLOY_PROJECTDIR'] = os.path.normpath(os.path.join(projects_path, project))
            global_key_subst['DEPLOY_PROJECT_NAME'] = project

# print("%%%%% workdir %%%%",base_args.workdir)

    #get yaml files involved
    base_yaml_files = find_config_file_list(
                list_paths=[work_dir, env_dir],
                default_paths=['config'],
                glob_suffix='defaults.yaml' )
   # print("#######################base yaml files", base_yaml_files)

############# get hosts_dir and platform  from default config ###############
    base_config_session = CascadeYamlConfig(yaml_files=base_yaml_files)[['config']]
    key_name = 'hosts_dir'

    base_parser.add_argument('--' + key_name,
                             action='store',
                             help='hosts config base dir',
                             default=abs_deploy_path(base_config_session.get(key_name,  'config/hosts'),
                                                     prefixes=[root_path]))

    # now reparse with this new arguments
    base_args = base_parser.parse_known_args()[0]
    # print("@@@@@@@@@ args.hosts_dir ::::::", str(base_args.hosts_dir).split('/'))
    if base_args.hosts_dir[0] == '/':
        hosts_dir = base_args.hosts_dir
    else:
        hosts_dir = os.path.join(root_path, str(base_args.hosts_dir))

    default_paths = ['config']
    if os.path.exists(hosts_dir):
        default_paths.append(hosts_dir)

    #get yaml files involved
    default_yaml_files = find_config_file_list(
                list_paths=[work_dir, env_dir],
                default_paths=default_paths,
                glob_suffix='defaults.yaml' )
    # print("#######################defaults yaml files", default_yaml_files)
    default_config_session = CascadeYamlConfig(yaml_files=default_yaml_files)[['config']]
    platform_match = utils.myintrospect(tags=default_config_session.get('host_tags', dict())).platform_tag()
    platform_matches = utils.myintrospect(tags=default_config_session.get('host_tags', dict())).multi_platform_tag()


##################################   now add extracted  platform to be used as key in jninja templates in 
##################################   parsing config files from now on
    platform_folders=[]
    global_key_subst['DEPLOY_HOSTS_DIR'] = hosts_dir
    for var in platform_matches:
        global_key_subst[var] = platform_matches[var]
        platform_config_folder = os.path.abspath(
            os.path.join(hosts_dir,
                         platform_matches[var],
                         base_config_session.get('config_dir', 'config')))
        if os.path.exists(platform_config_folder):
            platform_folders.append(platform_config_folder)
    if platform_folders==[]:
        logger.warning("NO platform matches ")

#    if platform_match :
#        global_key_subst['DEPLOY_PLATFORM_NAME'] = platform_match
#        platform_config_folder = os.path.abspath(os.path.join(hosts_dir,platform_match, base_config_session.get('config_dir', 'config')))
#        if os.path.exists(platform_config_folder):
#            global_key_subst['DEPLOY_HOST_CONFIGPATH'] = platform_config_folder
#            platform_folders = [platform_config_folder]
#        else:
#            platform_folders = []
#    else:        
#        logger.warning("UNABLE to find a platform match ")
#        platform_folders = []
               

##################################   from now on DEPLOY_PLATFORM_NAME should be available in jninja experssion {{DEPLOY_PLATFORM_NAME}}

    #get yaml files involved with current susbstitutions
    yaml_files = find_config_file_list(
                list_paths= platform_folders + [work_dir, env_dir],
                default_paths=['config'],
                glob_suffix='defaults.yaml' )
    base_config = CascadeYamlConfig(yaml_files=yaml_files)
    #env spack yaml files involved
    env_spack_yaml_files = find_config_file_list(
                           list_paths=[work_dir, env_dir],
                           default_paths=[],
                           glob_suffix='spack.yaml' )
    # print("#######################spack yaml files", env_spack_yaml_files)

    env_spack_config = CascadeYamlConfig(yaml_files=env_spack_yaml_files)
    env_spack_session = env_spack_config[['spack']]
    log_controller.set_args(log_configs=base_config[['logging_configs']])
    config_session = base_config[['config']]

    # adding config_folders arg
    key_name = 'config_folders'

    #print("######"+str(env_spack_session))
    #print("######"+str(env_spack_session.get('include', [os.path.join(root_path, 'config')])))
    # print("///////////////", config_session)
    defaults_config_folders = []
    for path in config_session.get(key_name, []):
        if path:
            if path[0] != '/':
                path=os.path.abspath(os.path.join(root_path, path))
            if os.path.isdir(path) and os.path.exists(path):
                defaults_config_folders.append(path)

    environment_config_folders = []
    for path in env_spack_session.get('include', []):
        if path[0] != '/':
            path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(env_spack_yaml_files[0])), path))
        if os.path.isdir(path) and os.path.exists(path):
            environment_config_folders.append(path)

    config_folders = defaults_config_folders + environment_config_folders
    config_folders = [ii for n,ii in enumerate(config_folders) if ii not in config_folders[:n]]

    base_parser.add_argument('-' + key_name[0],
                             '--' + key_name,
                             action='append',
                             help='yaml config folders',
                             default = config_folders)


    # now reparse with this new arguments
    base_args = base_parser.parse_known_args()[0]



    yaml_files = find_config_file_list(
                list_paths=[env_dir, work_dir] + base_args.config_folders,
                default_paths=default_paths,
                glob_suffix='defaults.yaml' )

    # print("#######################second yaml files", yaml_files)
    base_config = CascadeYamlConfig(yaml_files=yaml_files)
    log_controller.set_args(log_configs=base_config[['logging_configs']])

    config_session = base_config[['config']]


    #platform_folders=[]
    #if platform_match:
    #    logger.info(" platform -->" + str(platform_match) + "<--")
    #    platform_folders = merge_folder_list([],
    #                                        merge_folders=[os.path.join(platform_match, config_session.get('config_dir', 'config'))],
    #                                        prefixes=[os.getcwd(), hosts_dir])
    #    logger.info(" platform folders -->" + str(platform_folders) + "<--")
    #    global_key_subst['DEPLOY_HOST_CONFIGPATH'] = platform_folders[0]

    key_name = 'plugin_folders'
    base_parser.add_argument('-' + key_name[0],
                             '--' + key_name,
                             action='append',
                             help='plugin folders',
                             default = [abs_deploy_path(path, prefixes=[lib_path])
                                        for path in config_session.get(key_name,  [os.path.join(lib_path, 'plugins')])])

    # now reparse with this new arguments
    base_args = base_parser.parse_known_args()[0]

    # platform_folders=[]
    # if base_args.platform_dir[0] == '/':
    #     platform_dir = base_args.platform_dir
    # else:
    #     platform_dir = os.path.join(root_path, base_args.platform_dir)
    # if os.path.exists(platform_dir):
    #     platform_folders.append(platform_dir)
    #     platform_match = utils.myintrospect(tags=config_session.get('host_tags', dict())).platform_tag()
    #     logger.info(" platform -->" + str(platform_match) + "<--")
    #     if platform_match:
    #         platform_config_folder = os.path.abspath(os.path.join(platform_dir, platform_match, config_session.get('config_dir', 'config')))
    #         if os.path.exists(platform_config_folder):
    #             platform_folders.append(platform_config_folder)
    #         else:
    #             logger.warning(" NON EXISTING PLATFORM FOLDER :" + str(platform_config_folder))


    config_folders = merge_folder_list([os.path.join(root_path, 'config')] +
                                        platform_folders +
#                                        [env_dir, work_dir],
                                        [env_dir],
                                        merge_folders=base_args.config_folders,
                                        prefixes=[os.getcwd(),os.path.join(root_path, 'config')],
                                        remove_and_add_when_present=True)
    plugin_folders = merge_folder_list([],
                                        merge_folders=base_args.plugin_folders,
                                        prefixes=[os.getcwd(),lib_path])


    #compute merging config_folders by removing environment folders from config folders
    merge_config_folders =[ ]
    for folder in config_folders:
        if not folder in environment_config_folders:
            merge_config_folders.append(folder)


    global_key_subst['DEPLOY_MERGE_CONFIG_FOLDERS'] = merge_config_folders

    return base_parser, config_folders, plugin_folders, platform_folders, merge_config_folders




def argparse_add_arguments(parser,argument_dict):
    for a in argument_dict:
        conf_args = argument_dict[a]
        arguments = dict()
        arguments['help'] = conf_args['help']
        arguments['action'] = conf_args['action']
        d = conf_args['default']
        # print("OOOOOOOOOOOOOOOOOOOOOOparam:", a, " :::", d, type(d).__name__)
        if d:
            if d[0] == '[':
                # print("multimpar",a,conf_args[a]['default'])
                arguments['nargs'] = '*'
                arguments['default'] = eval(d)
            else:
                if arguments['action'] == 'store_true':
                    arguments['default'] = eval(d)
                    parser.add_argument('--no-' + a, action='store_false', dest=a)
                else:
                    arguments['default'] = str(d)

        parser.add_argument('--' + a, **arguments)



def merge_config(merge_conf, base_conf=dict(), nested_keys=[]):
    if len(nested_keys) > 0:
        out = copy.deepcopy(base_conf)
        curr = out
        for key in nested_keys[:-1]:
            next = curr.get(key,OrderedDict())
            curr[key] =next
            curr = next
        curr[nested_keys[-1]] = copy.deepcopy(merge_conf)
        return out
    else:
        return copy.deepcopy(merge_conf)


def ordered_set(in_list):
    out_list = []
    added = set()
    for val in in_list:
        if not val in added:
            out_list.append(val)
            added.add(val)
    return out_list


class ArgparseSubcommandManager(object):

    def __init__(self, **kwargs):
        self.logger = logging.getLogger('plugin.' + self.__class__.__name__)
        self.root_path = root_path
        self.methods_defaults = self._get_class_methods_defaults()
        self.yaml_config_nested_keys=[]
        logger.debug("@@@@@@@@"+str(self.methods_defaults)+"@@@@@@@@@@")
        for par in kwargs:
            logger.debug("###############initrgparseSubcommandManager  par "+ par+" --> "+str(kwargs[par]))

        self.dry_run = kwargs.get('dry_run', False)
        base_path_search_list = [os.curdir]
        deploy_dir = global_key_subst.get('DEPLOY_WORKDIR',
                     os.path.join(os.path.abspath(os.path.dirname(
                         os.path.dirname(sys.modules['__main__'].__file__))
                                                 ), 'deploy'))
        base_path_search_list = [deploy_dir] + base_path_search_list
        work_dir = kwargs.get('workdir', global_key_subst.get('DEPLOY_WORKDIR', ''))
        if work_dir :
            if work_dir[0] == '/' :
                base_path_search_list = [work_dir] + base_path_search_list
            else:
                base_path_search_list = [os.path.join(os.curdir,work_dir),
                     os.path.join(deploy_dir,work_dir)] + base_path_search_list
        for path in base_path_search_list:
            if os.path.exists(path):
                self.base_path = os.path.abspath(path)
                break
        #self.base_path = kwargs.get('workdir', os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(sys.modules['__main__'].__file__))), 'deploy'))
        self.save_config_file = kwargs.get('save_config',  'defaults.yaml' )
        if '/' != self.save_config_file[0]:
            self.save_config_file = os.path.join(self.base_path, self.save_config_file)
        self.save_config_file = os.path.abspath(self.save_config_file)
        if os.path.exists(self.save_config_file) :
            self.conf_to_save = utils.hiyapyco.load(
                    [self.save_config_file],
                    interpolate=True,
                    method=utils.hiyapyco.METHOD_MERGE,
                    failonmissingfiles=True
                )
        else:
            self.conf_to_save = OrderedDict()

        conf = copy.deepcopy(self.conf_to_save.get('config',OrderedDict()))
        for k in ['config_folders', 'plugin_folders', 'platform_folders', 'merge_config_folders']:
            conf[k] = kwargs.get(k,[])
            setattr(self, k,conf[k] )
        self.conf_to_save['config'] = conf
        self.config_nested_keys = kwargs.get('nested_keys', ['argparse', 'subparser'] + [self.__class__.__name__])
        self.top_config = kwargs.get('top_config', None)
        if self.top_config:
             self.manager_conf =  self.top_config[self.config_nested_keys]
        else:
            self.manager_conf = OrderedDict()

        self.manager_subcommand = self.manager_conf.get('command',self.__class__.__name__)

        self.manager_help = self.manager_conf.get('help', 'Manager ' + self.manager_subcommand)
        self.methods_conf = self.manager_conf.get('methods', dict())

        # print("$$$$$$$$$$$$$$ saving to", self.save_config_file, self.config_nested_keys, self.conf_to_save)



    def _get_class_methods_defaults(self):
        # print("class name",self.__class__.__name__)
        # for cls in self.__class__.__bases__:
        #     print("parent:", cls.__name__)

        methods_signature=dict()
        methods=[(name,fn) for name,fn in inspect.getmembers(self.__class__)  if callable(getattr(self.__class__, name)) and not name.startswith("_")]
        for name,fn in methods:
            signature = inspect.getargspec(fn)
            #signature['getfullargspec'] = inspect.getfullargspec(fn)
            #signature=inspect.getargspec(inspect.getmembers(self.__class__)[method_name])

            logger.debug(name + " :: " + str(signature))
            args_with_defaults = dict()
            if signature.defaults:
                number_of_args_with_defaults = len(signature.defaults)
            else:
                number_of_args_with_defaults = 0
            number_of_args_without_defaults = len(signature.args) - number_of_args_with_defaults
            count=0
            while count < len(signature.args):
                default_index = count - len(signature.args) + number_of_args_with_defaults
                par = signature.args[count]
                if par != 'self':
                    # print("#########", par)
                    args_with_defaults[par] = None if default_index < 0 else  signature.defaults[default_index]
                count += 1

#            for par in (signature.args[-number_of_args_with_defaults:] if number_of_args_with_defaults > 0 else []) :
#                args_with_defaults[par] = signature.defaults[count]
#                count += 1
            methods_signature[name]=args_with_defaults
            # print("method: " + name + " args: " + str(args_with_defaults))
            logger.debug(name + " ## " + str(methods_signature[name]))
        return methods_signature

    def _get_argparse_methods(self,conf=None):
        argparse_methods=dict()
        if not conf: conf=dict()
        #methods_defaults = self._get_class_methods_defaults()

        for method in self.methods_defaults:
            conf_params_defaults = conf.get(method,dict())
            argparse_methods[method] = {'help' : conf_params_defaults.get('help',"help for " + method +" method"),
                                        'args' : dict() }
            for param in self.methods_defaults[method]:
                param_defaults = conf_params_defaults.get(param,dict())
                # print("PPPPPPPPPPPPPPPPPP",method,param,param_defaults)
                arguments = dict()
                if 'help' in param_defaults:
                    arguments['help'] = param_defaults['help']

                arguments['action'] = param_defaults.get('action', 'store')


                if self.methods_defaults[method][param] != None:
                    arguments['default'] = str(self.methods_defaults[method][param])

                    d = param_defaults.get('default', '')
                    if len(d) > 0 :
                        arguments['default'] = str(d)


                    if len(arguments['default']) > 0 :
                        if str(arguments['default'])[0] == '[':
                             arguments['nargs'] = '*'
                             arguments['default'] = eval(arguments['default'])
                        else:
                            if  arguments['action'] == 'store_true':
                                arguments['default'] = eval(arguments['default'])
                else:
                    logger.info("!!!!!!!!!!!!!method: " + method + " has positional param " + param + " defaults:>" + str(self.methods_defaults[method][param]) + "<:")

                #     if d[0]=='['  :
                #         #print("multimpar",a,conf_args[a]['default'])
                #         arguments['nargs']='*'
                #         arguments['default'] = eval(d)
                #     else:
                #         if  arguments['action'] == 'store_true': arguments['default'] = eval(d)
                #         else: arguments['default'] = str(d)
                # else:
                #     arguments['action'] = 'store'
                #
                #
                # else:
                #     if self.methods_defaults[method][param] != None:
                #         arguments['default'] = self.methods_defaults[method][param]
                #         if len(str(arguments['default'])) > 0:
                #             if str(arguments['default'])[0]=='[':
                #                 arguments['nargs'] = '*'
                #     else:
                #         logger.info("method: " + method + " has positional param " + param + " defaults:>" + str(self.methods_defaults[method][param]) + "<:")
                #     arguments['action'] = 'store'
                argparse_methods[method]['args'][param] = arguments

        return argparse_methods

    def _get_callback(self, method):
        # print("_get_callback for ", method)
        lambda_method = lambda args: self._parse_args(method,args)
        return lambda_method

    def _parse_args(self, method, args):
        # print("parse_args for " + method)
        # getattr(self.__class__, method)(self, *args, **kw)
        all_args=vars(args)
        logger.debug("^^^^^all_args:" + str(all_args))
        merged_kwargs = dict()
        merged_args=[]
        method_args = self.methods_defaults.get(method, dict())
        logger.debug("method_args: " + str(method_args))
        for par in method_args:
            if par in all_args:
                if method_args[par] != None:
                    merged_kwargs[par] = all_args[par]
                else:
                    merged_args.append(all_args[par])

        logger.debug("@@@@merged_args: " + str(merged_args) + " merged_kw: "+ str(merged_kwargs))

        getattr(self.__class__, method)(self,*merged_args,**merged_kwargs)

        self._merge_config(self.config_nested_keys + ['methods', method], **merged_kwargs)
        out=utils.hiyapyco.dump(self.conf_to_save, default_flow_style=False)
        # print("@@@@@", out)

        #self._print_config(**merged_kwargs)

    def _print_config(self,**kwargs):
        for par in kwargs:
            logger.info("############### print_config par "+ par+" --> "+str(kwargs[par]))
        config_to_merge = merge_config(kwargs, nested_keys=self.yaml_config_nested_keys)
        out=utils.hiyapyco.dump(config_to_merge, default_flow_style=False)
        # print("@@@@@", out)

    def _merge_config(self, nested_keys, **kwargs):
        # print("UUUUUUU merging ", nested_keys, kwargs)
        # print("AAAAAAA conf_to_save ", self.conf_to_save)
        self.conf_to_save = merge_config(kwargs, base_conf=self.conf_to_save, nested_keys=nested_keys)
        # print("BBBBBBB conf_to_save ", self.conf_to_save)

    def _add_subparser(self, subparsers, parents=[], name=None, parser_conf=None, help=''):
        # print("############",type(subparsers))
        if parser_conf == None:
            parser_conf = self._get_argparse_methods(self.methods_conf)
        if name:
            self.manager_subcommand = name

        if help:
            self.manager_help = help
        subparsers_help = ''
        for method in parser_conf:
            subparsers_help += method + ','
        subparsers_help = "{ " + subparsers_help + " }"
        if self.manager_subcommand:
            self.subparser = subparsers.add_parser(self.manager_subcommand,
                                                   help= self.manager_help,
                                                   parents = parents,
                                                   formatter_class=formatter)
            self.subparsers = self.subparser.add_subparsers(dest='sub_' + self.manager_subcommand, metavar=subparsers_help)
        else:
            self.subparsers=subparsers
#            self.subparser_name = self.__class__.__name__
        #self.subparser = subparsers.add_parser(self.subparser_name , help=help, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        #self.subparsers = self.subparser.add_subparsers(dest='sub_' + self.subparser_name)
#        self.subparsers = self.subparser.add_subparsers(dest='sub_' + self.subparser_name, metavar=subparsers_help)
        self.subparsers.required = True

        self.methods_subparsers = dict()
        for method in parser_conf:
            # print("---handling method",method)
            method_conf = parser_conf[method]
            methods_conf_args=method_conf.get('args',dict())
            self.methods_subparsers[method] = self.subparsers.add_parser(method,
                                                                    help=method_conf.get('help',''),
                                                                    parents=parents,
                                                                    formatter_class=formatter)
            for par in  methods_conf_args:
                arguments = methods_conf_args[par]
                # print("add subparser ",name,method,par," :::"+str(arguments))
                if 'default' in arguments:
                    self.methods_subparsers[method].add_argument('--' + par, **arguments)
                    if 'action' in arguments:
                        if arguments['action'] == 'store_true':
                            self.methods_subparsers[method].add_argument('--no-' + par, action='store_false', dest=par )

                else:
                    self.methods_subparsers[method].add_argument(par, **arguments)

            #labda_method = lambda *args, **kw: getattr(self.__class__, method)(self,*args, **kw)
            #abda_method = lambda *args, **kw: print()
            self.methods_subparsers[method].set_defaults(func=self._get_callback(method))


def find_config_file_list(list_paths=None,
                          default_paths = ['etc', os.path.join('etc', 'defaults')],
                          env_var_config_path = 'RCM_CONFIG_PATH',
                          glob_suffix = "*.yaml"):

    out_list_paths = []
    for def_path in default_paths:
        out_list_paths.extend(glob.glob(os.path.join(root_path, def_path, glob_suffix)))
    if list_paths:
        input_list_paths = list_paths
    else:
        input_list_paths = []
    if env_var_config_path:
        env_config_path = os.environ.get(env_var_config_path, None)
        if env_config_path:
            input_list_paths.append(env_config_path)
    if list_paths:
        logger.debug("find_config_file_list: list_paths: " + str(list_paths))
        for path in list_paths:
            if os.path.isfile(path) and os.path.exists(path):
                out_list_paths.append(os.path.abspath(path))
            else:
                if os.path.isdir(path) and os.path.exists(path):
                    out_list_paths.extend(glob.glob(os.path.join(os.path.abspath(path), glob_suffix)))
                else:
                    for def_path in default_paths:
                        out_list_paths.extend(glob.glob(os.path.join(root_path, def_path, path, glob_suffix)))



    logger.debug("@@@@ BEFORE ordered_set list_paths: " + str(list_paths))
    out_list_paths = ordered_set(out_list_paths)
    logger.debug("@@@@@ AFTER ordered_set list_paths: " + str(list_paths))
    return out_list_paths


class CascadeYamlConfig:
    """
    derived from singleton idea ( pattern from https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html )
    Currently it implement a hash strategy to keep a single instance for init calls with the same input paramenters
    The object is a config class that parse cascading yaml files with hiyapyco
    constructor take a list of path, default paths env_var variable for config and a glob suffix pattern
    Files in these folders are parsed hierachically by parse method
    """

    instances = dict()


    class __CascadeYamlConfig:
        def __init__(self, yaml_files):
            self._conf = OrderedDict()
            self.list_paths = yaml_files

        def parse(self):
            logger.info("CascadeYamlConfig: parsing: " + str(self.list_paths))
            if self.list_paths:
                # add global variable substitution to jinja env, so 
                # used with {{DEPLOY_USERNAME'}}
                for subst_key in global_key_subst:
                    # print(".............. "+subst_key+" -->"+str(global_key_subst[subst_key])+"<--")
                    utils.hiyapyco.jinja2env.globals[subst_key] = global_key_subst[subst_key]
                
                self._conf = utils.hiyapyco.load(
                    *self.list_paths,
                    interpolate=True,
                    method=utils.hiyapyco.METHOD_MERGE,
                    failonmissingfiles=False
                )
                # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", self._conf['argparse'])

        @property
        def conf(self):
            return copy.deepcopy(self._conf)

        def __getitem__(self, nested_key_list=None):
            """
            this function access parsed config as loaded from hiyapyco
            :param nested_key_list: list of the nested keys to retrieve
            :return: deep copy of OrderedDict
            usage: top_config[['logging_configs']]
            """
            logger.debug("nested_key_list: " + str(nested_key_list))
            val = self._conf
            if nested_key_list:
                for key in nested_key_list:
                    val = val.get(key, OrderedDict())
            return copy.deepcopy(val)

        def __setitem__(self, nested_key_list,value):
            logger.debug("nested_key_list: " + str(nested_key_list))
            val = self._conf
            if len(nested_key_list) > 1:
                for key in nested_key_list[:-1]:
                    val = val.get(key, OrderedDict())
            val[nested_key_list[-1:][0]]=value


    def __init__(self, **kwargs):

        logger.info("### init kwargs:" + str(kwargs) )

        default_values = {'yaml_files': None}

        for k in default_values:
            default_values[k]=kwargs.get(k,default_values[k])

#        if not default_values['list_paths']:
#            default_values['list_paths']=argparse_get_config_paths()

#       added str(global_key_subst) to the string hashed as the computed dict depends also on the global subst parameters, so when
#       chaget it must be recomputed and not reused thru the hash
        par_hash=hash(str(default_values) + str(global_key_subst))
        logger.debug("CascadeYamlConfig.instances: " + str(CascadeYamlConfig.instances))

        if par_hash in  CascadeYamlConfig.instances:
            logger.info("Reusing CascadeYamlConfig instance hash:" + str(par_hash) + ": par " + str(default_values))
            self.instance = CascadeYamlConfig.instances[par_hash]
        else:
            logger.info("New CascadeYamlConfig instance hash:" + str(par_hash) + ": par " + str(default_values))
            self.instance = CascadeYamlConfig.__CascadeYamlConfig(**default_values)
            CascadeYamlConfig.instances[par_hash] = self.instance
            self.instance.parse()


    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __getitem__(self, nested_key_list):
        return self.instance.__getitem__(nested_key_list)


