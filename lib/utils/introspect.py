from __future__ import print_function

import os
import re
import sys
import platform
import socket
import logging

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
        self.sysintro['hostname']=socket.getfqdn()
        self.sysintro['clustername']='.'.join(self.sysintro['hostname'].split('.')[1:][:1])
        self.sysintro['domainname']='.'.join(self.sysintro['hostname'].split('.')[-2:])
        self.sysintro['distroname']=distro_name()

        logging.getLogger(__name__).debug("sysintro-->"+str(self.sysintro)+"<<-")
        #print("sysintro-->"+str(self.sysintro)+"<<-")

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

        commandintrospect.__init__(self,[])

        #self.test('git config --get remote.origin.url',key='giturl')
        self.tags=tags

    def platform_tag(self):
        #search tag in order, first in hostname and then in plaform string
        hostname=self.sysintro['hostname']
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
        tags=[]
        for parameter in ['hostname', 'clustername', 'domainname', 'distroname']:
            for k in self.tags:
                if self.sysintro[parameter] == k:
                    tags.append(self.tags[k])
                    break
        return tags


#################
if __name__ == '__main__':

    print("__file__:" + os.path.realpath(__file__))
    for k,v in baseintrospect().sysintro.items() : print("sysintro["+ k +"]=" + v )
    me=myintrospect(tags={'calori': 'ws_mint', 'galileo':'galileo', 'marconi':'marconi','m100':'m100', 'rhel8':'rhel8','centos.8':'centos8','centos':'centos','Linux':'genericlinux' })
    for k,v in me.commands.items() : print("commands["+ k +"]=" + str(v) )
    print("myintrospection:  host->" + me.platform_tag())
    print("myintrospection:  tags->" + str(me.multi_platform_tag()))

