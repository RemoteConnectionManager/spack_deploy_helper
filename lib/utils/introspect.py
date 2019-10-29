from __future__ import print_function

import os
import re
import sys
import platform
import socket
import logging

from run import run

logging.getLogger(__name__).setLevel(logging.DEBUG)

class baseintrospect:
    def __init__(self):
        self.sysintro=dict()
        self.sysintro['pyver']=platform.python_version()
        self.sysintro['pyinterp']=sys.executable
        self.sysintro['sysplatform']=platform.platform()
        self.sysintro['commandline']=' '.join(sys.argv)
        self.sysintro['workdir']=os.path.abspath('.')
        self.sysintro['hostname']=socket.getfqdn()

        logging.getLogger(__name__).debug("sysintro-->"+str(self.sysintro)+"<<-")

class commandintrospect(baseintrospect):
    def __init__(self,commands=[]):
        baseintrospect.__init__(self)
        self.commands=dict()
        for c in commands:
            self.test(c)

    def test(self,cmd,key=None):
        try :
            logging.getLogger(__name__).debug("introspect command-->"+cmd+"<<-")
            (ret,o,e)=run(cmd.split(),stop_on_error=False)
            if not e :
                if not key : key=cmd
                self.commands[key]=o.strip()
        except :
            logging.getLogger(__name__).exception("introspection failed: "+cmd)
            #print("failed: "+cmd)
            pass

class myintrospect(commandintrospect):
    def __init__(self,tags={}):

        commandintrospect.__init__(self,['git --version'])

        #self.test('git config --get remote.origin.url',key='giturl')
        self.tags=tags

    def platform_tag(self):
        hostname=self.sysintro['hostname']
        for k in self.tags:
            m=re.search(k,hostname)
            if m : return self.tags[k]
        return(None)


#################
if __name__ == '__main__':

    print("__file__:" + os.path.realpath(__file__))
    for k,v in baseintrospect().sysintro.items() : print("sysintro["+ k +"]=" + v )
    me=myintrospect(tags={'calori': 'ws_mint', 'galileo':'galileo', 'marconi':'marconi', 'eni':'eni' })
    for k,v in me.commands.items() : print("commands["+ k +"]=" + str(v) )
    print("myintrospection:  host->" + me.platform_tag())

