import os
import logging
import subprocess
import io
import re
import collections

from .run import run

#print("###TOP######## "+__name__)
logging.getLogger(__name__).debug('in module:'+ __name__ + " info")

class git_repo:
    def __init__(self, folder, logger=None,stop_on_error=True,dry_run=False):
        self.folder = os.path.abspath(folder)
        self.logger = logger or logging.getLogger(__name__)
        self.stop_on_error=stop_on_error
        self.dry_run=dry_run
        #print("debug level-->",self.debug)

    def run(self,cmd):
        (ret,out,err)=run(cmd,logger=self.logger,dry_run=self.dry_run,stop_on_error=self.stop_on_error,folder=self.folder)
        return (ret,out)

    def init(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        cmd = ['git', 'rev-parse', '--show-toplevel']
        (ret,output,err) = run(cmd,logger=self.logger,folder=self.folder,stop_on_error=False)
        git_root = os.path.abspath(output.strip())

        #print("in path ",self.folder," git rev_parse ret: ",ret, ' git top:', git_root)
        self.logger.info("in path " + self.folder + " git rev_parse ret: " + str(int(ret)) + ' git top:'+ git_root.decode('utf-8'))
        if 0 != ret or git_root != self.folder:
            cmd = ['git', 'init']
            (ret,output) = self.run(cmd)
            self.logger.info("git init in >>" + self.folder + "<< >>" + git_root.decode('utf-8') + "<< ret= "+ str(int(ret)))
            #print("git init in ",">>" + self.folder + "<<",">>" + git_root + "<< ret= ",ret)

    def get_remotes(self):
        cmd = ['git', 'remote']
        (ret,output) = self.run(cmd)
        remotes = list()
        for line in io.StringIO(output.decode()):
            r=line.strip()
            remotes.append(r)
            #print("-->" + r + "<--")
        return remotes

    def add_remote(self, url, name='origin', fetch_branches=[]):
        remotes=self.get_remotes()
        #if self.debug : print("remotes-->",remotes,"<<-")
        self.logger.debug("remotes-->"+str(remotes)+"<<-")
        if name not in self.get_remotes():
            cmd = ['git', 'remote', 'add']
            for branch in fetch_branches:
                cmd.append('-t')
                cmd.append(branch)
            cmd += [name, url]

            (ret,output) = self.run(cmd)


    def fetch(self, name='origin', prefix='',  branches=[]):
        cmd = [ 'git', 'fetch', name ]

        if isinstance(branches,list):
            for branch in branches:
 #               cmd.append(branch)
                cmd.append( branch + ':' + prefix.format(name=name) + branch)
        elif isinstance(branches,dict):
            for branch in branches:
                cmd.append( branch + ':' + prefix.format(name=name) + branches[branch])
        else:
            self.logger.error('Invalid branches type: either list or dict')

            return

        (ret,output) = self.run(cmd)

    def checkout(self, branch, newbranch=None):
        cmd = [ 'git', 'checkout', branch ]
        if newbranch: cmd.extend(['-b', newbranch])
        (ret,output) = self.run(cmd)

    def sync_upstream(self, upstream='upstream', master='develop', options=['--ff-only']):
        cmd = [ 'git', 'pull'] + options  + [upstream, master]
        (ret,output) = self.run(cmd)
        if ret : self.logger.error("sync_upstream failed")

    def merge(self, branch, comment='', options=[]):
        if not comment : comment = 'merged branch ' + branch
        self.logger.info("merging-->" + branch + '<<-')
        cmd = [ 'git', 'merge', '-m', '"' + comment  + '"'] + options + [branch]
        (ret,output) = self.run(cmd)
        if ret : self.logger.error("merge " + branch + "failed")

    def rebase(self, branch='upstream/develop', options=[]):
        self.logger.info("rebasing-->" + branch + '<<-')
        cmd = ['git', 'rebase'] + options + [branch]
        (ret,output) = self.run(cmd)
        if ret : self.logger.error("rebase " + branch + "failed")

    def get_local_branches(self):
        cmd = [ 'git', 'branch']
        (ret,output) = self.run(cmd)
        if ret :
            self.logger.error("git branch failed")
            return []
        branches = list()
        for line in io.StringIO(output.decode()):
            if line[0]=='*':
                branches.insert(0,line[2:].strip())
            else:
                branches.append(line[2:].strip())
        self.logger.debug("branches-->"+str(branches)+"<<-")
        return branches

# ------ List the branches on the origin
# And select only those that match our branch regexp
def get_branches(url, branch_pattern='.*?\s+refs/heads/(.*?)\s+', branch_format_string='{branch}', branch_selection=[]):

    cmd = ['git', 'ls-remote', url]
    logging.getLogger(__name__).info("execute-->"+str(cmd)+"<<-")
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]

    headRE = re.compile(branch_pattern)

    remote_branches = list()
    for line in io.StringIO(output.decode()):
        match = headRE.match(line)

        if match:
             branch = match.group(1)
            # excludeRE = re.compile(branch_exclude_pattern.format(branch=branch))
            # include=True
            # for line in io.StringIO(output.decode()):
            #     if excludeRE.match(line) :
            #         include= False
            #         print("excluded branch ",branch," line :",line)
            #         break

            # if include : remote_branches.append(branch)
             remote_branches.append(branch)
    remote_branches.sort()
    #print("remote_branches-->",str(remote_branches))
    #  print('#########-->' + url)
    #  for b in remote_branches:
    #    print("       -->",b)
    # ------ Construct the regular expression used to evaluate branches
    branchRE = dict()
    for p in branch_selection:
        # branchRE.append('(' + branch + ')')
        #print("----------->"+p+"<----")
        branchRE[p] = re.compile('^(' + p + ')$')
    # branchRE = re.compile('^(' + '|'.join(branchRE) + r')$')

    # ------- Figure out which of those branches we want
    fetch_branches = list()
    checkout_branch = None
    to_match = remote_branches
    for p in branch_selection:
        unmatched = []
        for branch in to_match:
            match2 = branchRE[p].match(branch)
            if match2:
                br_name = branch_format_string.format(branch=branch)
                #        if match2.group(2) and checkout_branch is None:
                #          checkout_branch = br_name
                fetch_branches.append(br_name)
            else:
                unmatched.append(branch)
        to_match = unmatched



    #  print("checkout-->",checkout_branch)
    for b in fetch_branches:
        logging.getLogger(__name__).info('{0} fetch-->{1}'.format(url, b))

    return fetch_branches

def trasf_match(in_list,in_match='(.*)',out_format='{name}'):
    #not working#logging.getLogger(__name__).info("in_list-->"+str(in_list)+"<<-")
    #not working#logging.getLogger(__name__).info("in_match-->"+str(in_match)+"<<-")
    out=collections.OrderedDict()
    in_RE = re.compile(in_match)
    for entry in in_list:
        match = in_RE.match(entry)
        if match:
            if 0 < len(match.groups()):
                name = match.group(1)
                out[entry] = out_format.format(name=name)
    return(out)

#################
if __name__ == '__main__':
    import tempfile
    import shutil
    print("__file__:" + os.path.realpath(__file__))
    #logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    #logging.debug('This message should appear on the console')
    #logging.info('So should this')
    #logging.warning('And this, too')
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)-5s %(name)s[%(filename)s:%(lineno)s ] %(message)s")

#    ff = logging.Formatter(
#        'pippo%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


    for origin,branches in [
        ('https://github.com/RemoteConnectionManager/spack.git',['clean/develop']),
#is not working        ('https://github.com/RemoteConnectionManager/RCM_spack_deploy.git',['master'])
                            ] :
        dest=tempfile.mkdtemp()
        logger.info("creating TEMP dir ->" + dest)
        repo=git_repo(dest,logger=logger)
        origin_branches = get_branches(origin, branch_selection=branches)
        repo.init()
        repo.add_remote(origin, name='origin', fetch_branches=origin_branches)
        repo.fetch(name='origin',branches=origin_branches)
        repo.checkout(origin_branches[0])
        logger.info(os.listdir(dest))
        shutil.rmtree(dest, ignore_errors=True)
