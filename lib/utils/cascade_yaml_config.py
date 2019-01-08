# stdlib
import sys
import os
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
logger = logging.getLogger(__name__)


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



def merge_folder_list(in_folders, merge_folders=None, prefixes=None):

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

    return current_folders


def setup_from_args_and_configs():
    """
    This function parse predefined args in hierarchical order, accumulating default parameters and
    by parsing known config files
    return a triple consisting of:
    base_parser:      base command line parser
    config_folders:   list of config folders used for setup
    plugin_folders:   list of plugin folders used for setup
    platform_folders: list of platform folders used for setup
    """

    log_controller = log_config.log_setup()

    # base parser
    base_parser = argparse.ArgumentParser(add_help=False)
    # this is the base workspace folder, containing a config file, named defaults.yaml, this file should accumulate the history
    # of the subcommands configs, so it should
    base_parser.add_argument('-w', '--workdir', action='store', help='workspace folder', default=os.getcwd())

    # partial parsing of known args
    base_args = base_parser.parse_known_args()[0]
    # print("%%%%% workdir %%%%",base_args.workdir)

    #get yaml files involved
    yaml_files = find_config_file_list(
                list_paths=[base_args.workdir],
                default_paths=['config'],
                glob_suffix='defaults.yaml' )
    # print("#######################first yaml files", yaml_files)

    base_config = CascadeYamlConfig(yaml_files=yaml_files)

    log_controller.set_args(log_configs=base_config[['logging_configs']])

    config_session = base_config[['config']]

    # print("///////////////", config_session)

    # adding config_folders arg
    key_name = 'config_folders'
    base_parser.add_argument('-' + key_name[0],
                             '--' + key_name,
                             action='append',
                             help='yaml config folders',
                             default=config_session.get(key_name,  [os.path.join(root_path, 'config')]))

    key_name = 'hosts_dir'

    base_parser.add_argument('--' + key_name,
                             action='store',
                             help='hosts config base dir',
                             default=config_session.get(key_name,  'config/hosts'))

    # now reparse with this new arguments
    base_args = base_parser.parse_known_args()[0]
    # print("@@@@@@@@@ args.hosts_dir ::::::", str(base_args.hosts_dir).split('/'))
    if base_args.hosts_dir[0] == '/':
        hosts_dir = base_args.hosts_dir
    else:
        hosts_dir = os.path.join(root_path, str(base_args.hosts_dir))
    # print("@@@@@@@@@ hosts_dir ::::::", hosts_dir)
    default_paths = ['config']
    if os.path.exists(hosts_dir):
        default_paths.append(hosts_dir)




    yaml_files = find_config_file_list(
                list_paths=[base_args.workdir] + base_args.config_folders,
                default_paths=default_paths,
                glob_suffix='defaults.yaml' )

    # print("#######################second yaml files", yaml_files)
    base_config = CascadeYamlConfig(yaml_files=yaml_files)
    log_controller.set_args(log_configs=base_config[['logging_configs']])

    config_session = base_config[['config']]


    platform_match = utils.myintrospect(tags=config_session.get('host_tags', dict())).platform_tag()
    platform_folders=[]
    if platform_match:
        logger.info(" platform -->" + str(platform_match) + "<--")
        platform_folders = merge_folder_list([],
                                            merge_folders=[os.path.join(platform_match, config_session.get('config_dir', 'config'))],
                                            prefixes=[os.getcwd(), hosts_dir])
        logger.info(" platform folders -->" + str(platform_folders) + "<--")


    key_name = 'plugin_folders'
    base_parser.add_argument('-' + key_name[0],
                             '--' + key_name,
                             action='append',
                             help='plugin folders',
                             default=config_session.get(key_name,  [os.path.join(lib_path, 'plugins')]))

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


    config_folders = merge_folder_list([os.path.join(root_path, 'config')] + platform_folders + [os.path.abspath(base_args.workdir)],
                                        merge_folders=base_args.config_folders,
                                        prefixes=[os.getcwd(),os.path.join(root_path, 'config')])
    plugin_folders = merge_folder_list([],
                                        merge_folders=base_args.plugin_folders,
                                        prefixes=[os.getcwd(),lib_path])

    return base_parser, config_folders, plugin_folders, platform_folders




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
        self.root_path = root_path
        self.methods_defaults = self._get_class_methods_defaults()
        self.yaml_config_nested_keys=[]
        logger.debug("@@@@@@@@"+str(self.methods_defaults)+"@@@@@@@@@@")
        for par in kwargs:
            logger.debug("###############initrgparseSubcommandManager  par "+ par+" --> "+str(kwargs[par]))

        self.dry_run = kwargs.get('dry_run', False)
        rel_path = kwargs.get('workdir', '')
        deploy_dir = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(sys.modules['__main__'].__file__))), 'deploy')
        for path in [os.path.join(os.curdir,rel_path),
                     os.path.join(deploy_dir,rel_path),
                     deploy_dir,
                     os.curdir] :
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
        for k in ['config_folders', 'plugin_folders', 'platform_folders']:
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

        print("$$$$$$$$$$$$$$ saving to", self.save_config_file, self.config_nested_keys, self.conf_to_save)



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
        # print("parse_args for ", method)
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
        print("@@@@@", out)

        #self._print_config(**merged_kwargs)

    def _print_config(self,**kwargs):
        for par in kwargs:
            logger.info("############### print_config par "+ par+" --> "+str(kwargs[par]))
        config_to_merge = merge_config(kwargs, nested_keys=self.yaml_config_nested_keys)
        out=utils.hiyapyco.dump(config_to_merge, default_flow_style=False)
        print("@@@@@", out)

    def _merge_config(self, nested_keys, **kwargs):
        print("UUUUUUU merging ", nested_keys, kwargs)
        print("AAAAAAA conf_to_save ", self.conf_to_save)
        self.conf_to_save = merge_config(kwargs, base_conf=self.conf_to_save, nested_keys=nested_keys)
        print("BBBBBBB conf_to_save ", self.conf_to_save)

    def _add_subparser(self, subparsers, name=None, parser_conf=None, help=''):
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
            self.subparser = subparsers.add_parser(self.manager_subcommand , help= self.manager_help, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
                                                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
            for par in  methods_conf_args:
                arguments = methods_conf_args[par]
                # print("add subparser ",name,method,par," :::"+str(arguments))
                if 'default' in arguments:
                    self.methods_subparsers[method].add_argument('--' + par, **arguments)
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


    def __init__(self, **kwargs):

        logger.info("### init kwargs:" + str(kwargs) )

        default_values = {'yaml_files': None}

        for k in default_values:
            default_values[k]=kwargs.get(k,default_values[k])

#        if not default_values['list_paths']:
#            default_values['list_paths']=argparse_get_config_paths()
        par_hash=hash(str(default_values))
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


