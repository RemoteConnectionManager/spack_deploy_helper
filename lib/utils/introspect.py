from __future__ import print_function

import os
import re
import sys
import platform
import socket
import logging
from collections import OrderedDict

from run import run

import external.distro as distro
#logging.getLogger(__name__).setLevel(logging.DEBUG)

def distro_name():
    distname, version, _ = distro.linux_distribution(full_distribution_name=False)
    version = re.split(r'[^\w-]', version)
    if 'ubuntu' in distname:
        version = '.'.join(version[0:2])
    else:
        version = version[0]
    return "%s%s" % (distname.replace('-', '_'),version.replace('-', '_'))

class baseintrospect:
    def __init__(self):
        self.sysintro=dict()
        self.sysintro['pyver']=platform.python_version()
        self.sysintro['pyinterp']=sys.executable
        self.sysintro['sysplatform']=platform.platform()
        self.sysintro['commandline']=' '.join(sys.argv)
        self.sysintro['workdir']=os.path.abspath('.')
        self.sysintro['DEPLOY_HOST']=os.environ.get('FORCED_DEPLOY_HOST',socket.getfqdn())
        self.sysintro['DEPLOY_CLUSTER']=os.environ.get('FORCED_DEPLOY_CLUSTER','.'.join(self.sysintro['DEPLOY_HOST'].split('.')[1:][:1]))
        self.sysintro['DEPLOY_DOMAIN']=os.environ.get('FORCED_DEPLOY_DOMAIN','.'.join(self.sysintro['DEPLOY_HOST'].split('.')[-2:]))
        self.sysintro['DEPLOY_DISTRO']=distro_name()

        logging.getLogger(__name__).debug("sysintro-->"+str(self.sysintro)+"<<-")
        #print("sysintro-->"+str(self.sysintro)+"<<-")

class commandintrospect(baseintrospect):
    def __init__(self,commands={}):
        baseintrospect.__init__(self)
        self.commands=dict()
        for k in commands:
            self.test(commands[k],key=k)

    def test(self,cmd,key=None):
        if key in os.environ:
            self.commands[key]=os.environ[key]
        else:
            try :
                logging.getLogger(__name__).debug("introspect command-->"+cmd+"<<-")
                (ret,o,e)=run(cmd.split(),stop_on_error=False,show_errors=False)
                if not e :
                    if not key : key=cmd
                    self.commands[key]=o.strip().splitlines()[0]
            except :
                logging.getLogger(__name__).exception("introspection failed: "+cmd)
                #print("failed: "+cmd)
                pass

class myintrospect(commandintrospect):
    def __init__(self,tags={}):

        commandintrospect.__init__(self,{
            'DEPLOY_NVIDIA_DRIVER':'nvidia-smi --query-gpu=driver_version --format=csv,noheader',
            'DEPLOY_NVIDIA_NAME':  'nvidia-smi --query-gpu=name --format=csv,noheader',
            'DEPLOY_NVIDIA_IMG':   'nvidia-smi --query-gpu=inforom.img --format=csv,noheader',
            })

        #self.test('git config --get remote.origin.url',key='giturl')
        self.tags=tags

    def platform_tag(self):
        #search tag in order, first in hostname and then in plaform string
        hostname=self.sysintro['DEPLOY_HOST']
        for k in self.tags:
            #print("search tag: "+k)
            m=re.search(k,hostname)
            if m : return self.tags[k]
        platformstring=self.sysintro['sysplatform']
        for k in self.tags:
            #print("search tag: "+k)
            m=re.search(k,platformstring)
            if m : return self.tags[k]
        return(None)


    def multi_platform_tag(self):
        #Return a list off all tags matching , in priority order of host, cluster, domain, distname
        tags=OrderedDict()
        for parameter in ['DEPLOY_HOST', 
                          'DEPLOY_CLUSTER',
                          'DEPLOY_DOMAIN',
                          'DEPLOY_DISTRO',
                          'DEPLOY_NVIDIA_DRIVER',
                          'DEPLOY_NVIDIA_NAME',
                          'DEPLOY_NVIDIA_IMG' ]:

            for k in self.tags:
                #print("searching tag " + k)
                if self.sysintro.get(parameter,None) == k:
                    tags[parameter] = self.tags[k]
                elif self.commands.get(parameter,None) == k:
                    tags[parameter] = self.tags[k]
        return tags


#################
if __name__ == '__main__':

    print("__file__:" + os.path.realpath(__file__))
    for k,v in baseintrospect().sysintro.items() : print("sysintro["+ k +"]=" + v )
    me=myintrospect(tags={'calori': 'ws_mint', 'galileo':'galileo', 'marconi':'marconi','m100':'m100', 'rhel8':'rhel8','centos.8':'centos8','centos':'centos','Linux':'genericlinux','NVIDIA GeForce':'GEFORCE','510.108.03':'CUDA_11.6' })
    for k,v in me.commands.items() : print("commands["+ k +"]=" + str(v) )
    print("myintrospection:  host->" + me.platform_tag())
    print("myintrospection:  tags->" + str(me.multi_platform_tag()))

