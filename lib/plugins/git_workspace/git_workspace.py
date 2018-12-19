import os
import sys
import uuid
import logging

#lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
#if not lib_path in sys.path:
#    sys.path.append(lib_path)

import utils
import cascade_yaml_config

#rootLogger = logging.getLogger()
# rootLogger.setLevel(logging.INFO)
#consoleHandler = logging.StreamHandler()
#rootLogger.addHandler(consoleHandler)

mylogger = logging.getLogger(__name__)

#ls=utils.log_setup()
logging.info("__file__:" + os.path.realpath(__file__))
#ls.set_args()


class GitWorkspaceManager(cascade_yaml_config.ArgparseSubcommandManager):

    def __init__(self, **kwargs):
        super(GitWorkspaceManager, self).__init__(**kwargs)
        for par in kwargs:
            mylogger.info("init par "+ par+" --> "+str(kwargs[par]))



    def create(self):
        uuid_ = uuid.uuid4()
        path = os.path.join(self.base_path, str(uuid_))
        os.mkdir(path)
        print('Created a new workspace in: ' + path)
        return uuid

    def list(self):
        print('The current workspaces are:')
        for root, dirs, files in os.walk(self.base_path, topdown=False):
            for name in dirs:
                print(" * " + name)

    def remove(self, uuid_):
        path = os.path.join(self.base_path, str(uuid_))
        try:
            os.rmdir(path)
        except OSError:
            print('error: failed to remove the directory ' + path)

    def git_deploy(self,
                   git_dest='src',
                   integration=False,
                   origin_update=False,
                   upstream_update=False,
                   rebase_update=False,
                   branches=['clean/master'],
                   prlist=[],
                   origin='',
                   origin_master='',
                   pull_flags=['ff-only'],
                   upstream=''):


        # print("@@@@@@@@@@@@@@@@@@@@",self.dry_run)
        if git_dest[0] != '/':
            dest = os.path.join(self.base_path, git_dest)
        else:
            dest = git_dest

        print("@@@@@@@@@@@@@@@@@@@@", dest, self.dry_run)
        dev_git = utils.git_repo(dest, logger=mylogger, dry_run=self.dry_run)

        origin_branches = utils.get_branches(origin, branch_selection=branches)
        upstream_branches = utils.get_branches(
            upstream,
            branch_pattern='.*?\s+refs/pull/([0-9]*?)/head\s+',
            # branch_exclude_pattern='.*?\s+refs/pull/({branch})/merge\s+',
            branch_format_string='pull/{branch}/head',
            branch_selection=prlist)

        local_pr = utils.trasf_match(upstream_branches, in_match='.*/([0-9]*)/(.*)', out_format='pull/{name}/clean')

        mylogger.info("upstream_branches->" + str(upstream_branches) + "<--")

        if not os.path.exists(dest):
            mylogger.info("MISSING destination_dir-->" + dest + "<-- ")
            os.makedirs(dest)


            dev_git.init()

            dev_git.get_remotes()
            dev_git.add_remote(origin, name='origin', fetch_branches=origin_branches)
            dev_git.add_remote(upstream, name='upstream')


            dev_git.fetch(name='origin', branches=origin_branches)

            if integration:
                if len(origin_branches) > 0:
                    upstream_clean = origin_branches[0]
                    # print("--------------------------------------" + upstream_clean + "-----------------------")
                    dev_git.checkout(upstream_clean)
                    if upstream_update:
                        dev_git.sync_upstream()
                    dev_git.checkout(upstream_clean, newbranch=origin_master)

                    if upstream_update:
                        dev_git.sync_upstream()

                    for b in origin_branches[1:]:
                        if upstream_update:
                            merge_branch = b + '_merge'
                            dev_git.checkout(b, newbranch=merge_branch)
                            dev_git.merge(upstream_clean)

                            if rebase_update:
                                dev_git.checkout(b)
                                dev_git.merge(upstream_clean)
                                dev_git.rebase(branch=upstream_clean, options=['-Xtheirs'])
                                dev_git.merge(merge_branch, options=['-Xtheirs'])
                                #rebase_branch = b + '_rebase'
                                #dev_git.checkout(merge_branch, newbranch=rebase_branch)
                                #dev_git.rebase(branch=upstream_clean, options=['-Xtheirs'])
                                #dev_git.merge(merge_branch, options=['-Xtheirs'])
                            dev_git.delete(merge_branch)
                        dev_git.checkout(b)




                    dev_git.fetch(name='upstream', branches=local_pr)

                    for n, branch in local_pr.items():
                        mylogger.info("local_pr " + n + " " + branch)
                        dev_git.checkout(branch, newbranch=branch + '_update')
                        dev_git.merge(upstream_clean, comment='sync with upstream develop ')
                        dev_git.checkout(origin_master)
                        dev_git.merge(branch + '_update', comment='merged ' + branch)

                    for branch in origin_branches[1:]:
                        dev_git.checkout(origin_master)
                        dev_git.merge(branch, comment='merged ' + branch)
            else:
                dev_git.fetch(name='origin', branches=[origin_master])
                dev_git.checkout(origin_master)

        else:
            mylogger.warning("Folder ->" + dest + "<- already existing")
            if origin_update:
                mylogger.info("Updating Folder ->" + dest + "<-")
                pull_options = []
                for flag in pull_flags: pull_options.append('--' + flag)
                local_branches = dev_git.get_local_branches()
                for branch in origin_branches[1:]:
                    if branch in local_branches:
                        dev_git.checkout(branch)
                        dev_git.sync_upstream(upstream='origin', master=branch, options=pull_options)
                    else:
                        dev_git.fetch(name='origin', branches=[branch])
                        dev_git.checkout(branch)
                    if upstream_update:
                        merge_options = []
                        if rebase_update:
                            merge_options.append('--rebase')
                        dev_git.sync_upstream(options=merge_options)
