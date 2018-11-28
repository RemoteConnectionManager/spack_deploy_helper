#!/usr/bin/env python

import logging
import logging.config
import argparse
import os

#from external import hiyapyco
import cascade_yaml_config



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

        for curr_logger in [logging.getLogger(__name__), logging.getLogger('cascade_yaml_config')]:
            curr_logger.setLevel(self.get_level(parser.parse_known_args()[0].debug))
        #logging.basicConfig(format=BASEFORMAT, level=self.get_level(parser.parse_known_args()[0].debug))
        logging.getLogger(__name__).debug("#########init")
        #logging.getLogger('external1.hiyapyco').setLevel(logging.INFO)

    def get_level(self,arg_level):
        return self.LEVELS.get(arg_level, logging.INFO)

    def set_args(self,):
        conf = cascade_yaml_config.CascadeYamlConfig(default_paths=['config'], glob_suffix='defaults.yaml' ).conf
        log_configs=conf.get('logging_configs',{})
        if not log_configs.get('version',None) : log_configs['version']=1
        for d in log_configs :
            logging.getLogger(__name__).debug("logging_conf : " + d + " - " + type(log_configs[d]).__name__ + "<-->" + str(log_configs[d]))

        logging.config.dictConfig(log_configs)



#################
if __name__ == '__main__':

    ls=log_setup()
    #logging.basicConfig(format="[%(levelname)-5s %(name)s # %(pathname)s:%(lineno)s] %(message)s", level=logging.INFO)
    logging.debug("__file__:" + os.path.realpath(__file__))

    ls.set_args()
    logging.info("######### do set_args again #####")

    ls.set_args()


