# stdlib
import sys
import os
import logging
import copy
import glob
from collections import OrderedDict
import argparse
import inspect

lib_path = os.path.dirname((os.path.dirname(os.path.abspath(__file__))))
if lib_path not in sys.path:
    sys.path.append(lib_path)
import utils

root_path = os.path.dirname(lib_path)
logger = logging.getLogger(__name__)

def argparse_get_config_paths():
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument('-c', '--config_paths', nargs='*', help='yaml config folders',
                             default=[os.path.join(root_path, 'config')])

    base_args = base_parser.parse_known_args()[0]
    # for name in vars(base_args):
    #     print(name + " :: " + str(vars(base_args)[name]))

    listpaths = []
    for c in base_args.config_paths:
        logger.debug("config folder:" + c)
        if c[0] != '/':
            c = os.path.abspath(os.path.join(root_path, c))
            listpaths.append(c)
    return listpaths

def argparse_add_arguments(parser,argument_dict):
    for a in argument_dict:
        conf_args = argument_dict[a]
        arguments = dict()
        arguments['help'] = conf_args['help']
        arguments['action'] = conf_args['action']
        d = conf_args['default']
        # print("param:", a, " :::", d, type(d).__name__)
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


class ArgparseSubcommandManager(object):

    def __init__(self):
        self.methods_defaults = self._get_class_methods_defaults()
        logger.debug("@@@@@@@@"+str(self.methods_defaults)+"@@@@@@@@@@")
        # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

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
                arguments = dict()
                if 'help' in param_defaults:
                    arguments['help'] = param_defaults['help']
                if 'action' in param_defaults:
                    arguments['action'] = param_defaults['action']

                if 'default' in param_defaults:
                    d=param_defaults['default']
                    if d[0]=='['  :
                        #print("multimpar",a,conf_args[a]['default'])
                        arguments['nargs']='*'
                        arguments['default'] = eval(d)
                    else:
                        if  arguments['action'] == 'store_true': arguments['default'] = eval(d)
                        else: arguments['default'] = str(d)
                else:
                    if self.methods_defaults[method][param] != None:
                        arguments['default'] = self.methods_defaults[method][param]
                        if len(str(arguments['default'])) > 0:
                            if str(arguments['default'])[0]=='[':
                                arguments['nargs'] = '*'
                    else:
                        logger.info("method: " + method + " has positional param " + param + " defaults:>" + str(self.methods_defaults[method][param]) + "<:")
                    arguments['action'] = 'store'
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
        # print("@@@@@", merged_args)
        getattr(self.__class__, method)(self,*merged_args,**merged_kwargs)



    def _add_subparser(self, subparsers, name=None, conf=None, help=''):
        if name:
            self.subparser_name = name
        else:
            self.subparser_name = self.__class__.__name__
        if conf:
            self.conf=conf
        else:
            self.conf = self._get_argparse_methods()
        self.subparser = subparsers.add_parser(self.subparser_name , help=help, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        #self.subparsers = self.subparser.add_subparsers(dest='sub_' + self.subparser_name)
        subparsers_help = ''
        for method in self.conf:
            subparsers_help += method + ','
        subparsers_help = "{ " + subparsers_help + " }"
        self.subparsers = self.subparser.add_subparsers(dest='sub_' + self.subparser_name, metavar=subparsers_help)
        self.subparsers.required = True
        self.metavar='pippo'

        self.methods_subparsers = dict()
        for method in self.conf:
            # print("---handling method",method)
            method_conf = self.conf[method]
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


class CascadeYamlConfig:
    """
    singleton ( pattern from https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html )
    config class that parse cascading yaml files with hiyapyco
    constructor take a list of files that are parsed hierachically by parse method
    """

    class __CascadeYamlConfig:
        def __init__(self, list_paths,
                     default_paths,
                     env_var_config_path,
                     glob_suffix):
            #print("#############   here ############  ", str(list_paths), str(default_paths), glob_suffix)
            self._conf = OrderedDict()
            self.list_paths = []
            if list_paths:
                input_list_paths = list_paths
            else:
                input_list_paths = []
            if env_var_config_path:
                env_config_path = os.environ.get(env_var_config_path, None)
                if env_config_path:
                    input_list_paths.append(env_config_path)
            if list_paths:
                logger.info("CascadeYamlConfig: list_paths: " + str(list_paths))
                for path in list_paths:
                    if os.path.isfile(path) and os.path.exists(path):
                        self.list_paths.append(path)
                    else:
                        if os.path.isdir(path) and os.path.exists(path):
                            self.list_paths.extend(glob.glob(os.path.join(path, glob_suffix)))
                        else:
                            for def_path in default_paths:
                                self.list_paths.extend(glob.glob(os.path.join(root_path, def_path, path, glob_suffix)))

            for def_path in default_paths:
                self.list_paths.extend(glob.glob(os.path.join(root_path, def_path, glob_suffix)))

            self.list_paths.reverse()
            #print("list paths: ", self.list_paths)

        def parse(self):
            logger.info("CascadeYamlConfig: parsing: " + str(self.list_paths))
            if self.list_paths:
                self._conf = utils.hiyapyco.load(
                    *self.list_paths,
                    interpolate=True,
                    method=utils.hiyapyco.METHOD_MERGE,
                    failonmissingfiles=False
                )

        @property
        def conf(self):
            return copy.deepcopy(self._conf)

        def __getitem__(self, nested_key_list=None):
            """
            this funchion access parsed config as loaded from hiyapyco
            :param nested_key_list: list of the nested keys to retrieve
            :return: deep copy of OrderedDict
            """
            val = self._conf
            if nested_key_list:
                for key in nested_key_list:
                    val = val.get(key, OrderedDict())
            return copy.deepcopy(val)

    instances = dict()

    def __init__(self, **kwargs):
        default_values = {
            'list_paths': None,
            'default_paths' : ['etc', os.path.join('etc', 'defaults')],
            'env_var_config_path' : 'RCM_CONFIG_PATH',
            'glob_suffix' :  "*.yaml"}

        for k in default_values:
            default_values[k]=kwargs.get(k,default_values[k])

        if not default_values['list_paths']:
            default_values['list_paths']=argparse_get_config_paths()
        par_hash=hash(str(default_values))
        if par_hash in  CascadeYamlConfig.instances:
            self.instance = CascadeYamlConfig.instances[par_hash]
        else:
            self.instance = CascadeYamlConfig.__CascadeYamlConfig(**default_values)
            CascadeYamlConfig.instances[par_hash] = self.instance
            self.instance.parse()

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __getitem__(self, nested_key_list):
        return self.instance.__getitem__(nested_key_list)

