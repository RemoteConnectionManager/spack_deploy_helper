import os
import sys
import uuid
import logging

lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if not lib_path in sys.path:
    sys.path.append(lib_path)

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


class WorkspaceManager(cascade_yaml_config.ArgparseSubcommandManager):

    def __init__(self, base_deploy_path, dry_run=True):
        super(WorkspaceManager, self).__init__()
        self.base_path = base_deploy_path
        self.dry_run=dry_run

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
                   dest='spack',
                   do_update=False,
                   integration=False,
                   branches=['clean/master'],
                   prlist=[],
                   origin='',
                   origin_master='',
                   pull_flags=['ff-only'],
                   upstream=''):


        # print("@@@@@@@@@@@@@@@@@@@@",self.dry_run)
        if dest[0] != '/':
            dest=os.path.join(self.base_path, dest)

        dev_git = utils.git_repo(dest, logger=mylogger, dry_run=self.dry_run)

        if not os.path.exists(dest):
            mylogger.info("MISSING destination_dir-->" + dest + "<-- ")
            os.makedirs(dest)

            origin_branches = utils.get_branches(origin, branch_selection=branches)

            dev_git.init()

            dev_git.get_remotes()
            dev_git.add_remote(origin, name='origin', fetch_branches=origin_branches)
            dev_git.add_remote(upstream, name='upstream')

            upstream_branches = utils.get_branches(
                upstream,
                branch_pattern='.*?\s+refs/pull/([0-9]*?)/head\s+',
                # branch_exclude_pattern='.*?\s+refs/pull/({branch})/merge\s+',
                branch_format_string='pull/{branch}/head',
                branch_selection=prlist)

            local_pr = utils.trasf_match(upstream_branches, in_match='.*/([0-9]*)/(.*)', out_format='pull/{name}/clean')

            mylogger.info("upstream_branches->" + str(upstream_branches) + "<--")

            dev_git.fetch(name='origin', branches=origin_branches)

            if integration:
                if len(origin_branches) > 0:
                    upstream_clean = origin_branches[0]
                    # print("--------------------------------------" + upstream_clean + "-----------------------")
                    dev_git.checkout(upstream_clean)
                    dev_git.sync_upstream()
                    dev_git.checkout(upstream_clean, newbranch=origin_master)

                    dev_git.sync_upstream()

                    for b in origin_branches[1:]:
                        dev_git.checkout(b)
                        dev_git.sync_upstream(options=['--rebase'])

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
            mylogger.warning("Folder ->" + dest + "<- already existing, skipping git stuff")
            if do_update:
                mylogger.info("Updating Folder ->" + dest + "<-")
                pull_options = []
                for flag in pull_flags: pull_options.append('--' + flag)
                for b in dev_git.get_local_branches():
                    dev_git.checkout(b)
                    dev_git.sync_upstream(upstream='origin', master=b, options=pull_options)
