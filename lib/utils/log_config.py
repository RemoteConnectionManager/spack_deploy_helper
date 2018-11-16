#!/usr/bin/env python

import logging
import logging.config
import argparse
import os

from .external import hiyapyco
from .introspect import myintrospect

class base_config:

    def listpaths(self,filename):
        listpaths=[]
        for c in self.config_paths:
            logging.getLogger(__name__).debug("config folder:"+c)
            if c[0] != '/' : c=os.path.abspath(os.path.join(self.root_dir,c))
            found_file=os.path.join(c,filename)
            if os.path.exists(found_file)  :  listpaths.append(found_file)
        return listpaths

    def merge_conf(self,listpaths):
        logging.getLogger(__name__).debug("conf files-->"+str(listpaths))
        logging.getLogger(__name__).debug("Before hiyapyco.load")
        conf = hiyapyco.load(
            *listpaths,
            interpolate=True,
            method=hiyapyco.METHOD_MERGE,
            failonmissingfiles=False
        )
        logging.getLogger(__name__).debug("After hiyapyco.load")
        return conf

    def __init__(self):
        self.basepath = os.path.dirname(os.path.realpath(__file__))
        logging.getLogger(__name__).info("basepath-->"+self.basepath+"<--")
        self.root_dir=os.path.abspath(os.path.dirname(os.path.dirname(self.basepath)))
        logging.getLogger(__name__).info("root_dir-->"+self.root_dir+"<--")
        self.config_paths=[os.path.join(self.root_dir,'config')]

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('-c','--config_paths', nargs='*', default = [])
        config_paths=parser.parse_known_args()[0].config_paths



class log_setup:
    def __init__(self):
        self.LEVELS = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL}

        BASEFORMAT = "#aaa[%(levelname)-5s %(name)s # %(pathname)s:%(lineno)s] %(message)s"
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('-d','--debug', default = 'error')
        #logging.basicConfig(format=BASEFORMAT, level=logging.ERROR)
        logging.basicConfig(level=logging.ERROR)

        logging.getLogger(__name__).setLevel(self.get_level(parser.parse_known_args()[0].debug))
        #logging.basicConfig(format=BASEFORMAT, level=self.get_level(parser.parse_known_args()[0].debug))
        logging.getLogger(__name__).debug("#########init")
        #logging.getLogger('external1.hiyapyco').setLevel(logging.INFO)

    def get_level(self,arg_level):
        return self.LEVELS.get(arg_level, logging.INFO)

    def set_args(self,):
        config=base_config()
        conf=config.merge_conf(config.listpaths('defaults.yaml'))
        # basepath = os.path.dirname(os.path.realpath(__file__))
        # logging.getLogger(__name__).info("basepath-->"+basepath+"<--")
        # root_dir=os.path.abspath(os.path.dirname(os.path.dirname(basepath)))
        # logging.getLogger(__name__).info("root_dir-->"+root_dir+"<--")
        #
        # parser = argparse.ArgumentParser(add_help=False)
        # parser.add_argument('-c','--config_paths', nargs='*', default = [os.path.join(root_dir,'config')])
        # argfile_args=parser.parse_known_args()[0]
        # listpaths=[]
        # for c in parser.parse_known_args()[0].config_paths:
        #     logging.getLogger(__name__).debug("config folder:"+c)
        #     if c[0] != '/' : c=os.path.abspath(os.path.join(root_dir,c))
        #     default_file=os.path.join(c,'defaults.yaml')
        #     if os.path.exists(default_file)  :  listpaths.append(default_file)
        #
        # logging.getLogger(__name__).debug("conf files-->"+str(listpaths))
        # logging.getLogger(__name__).debug("---prima-------################------------")
        # conf = hiyapyco.load(
        #     *listpaths,
        #     interpolate=True,
        #     method=hiyapyco.METHOD_MERGE,
        #     failonmissingfiles=False
        # )
        # logging.getLogger(__name__).debug("---dopo-------################------------")
        log_configs=conf.get('logging_configs',{})
        if not log_configs.get('version',None) : log_configs['version']=1
        for d in log_configs :
            logging.getLogger(__name__).debug("logging_conf : " + d + " - " + type(log_configs[d]).__name__ + "<-->" + str(log_configs[d]))

        logging.config.dictConfig(log_configs)
        defaults=conf.get('defaults',{'debug':'info'})


#################
if __name__ == '__main__':
    ls=log_setup()
    #logging.basicConfig(format="[%(levelname)-5s %(name)s # %(pathname)s:%(lineno)s] %(message)s", level=logging.INFO)
    logging.debug("__file__:" + os.path.realpath(__file__))

    ls.set_args()
    logging.info("######### do set_args again #####")

    ls.set_args()


