import os
import shutil
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

# mylogger = logging.getLogger(__name__)

#ls=utils.log_setup()
logging.debug("__file__:" + os.path.realpath(__file__))
#ls.set_args()

def is_git_clone(path):
    print("@@@@@ check git checkout in: "+path)
    return os.path.exists(os.path.join(path, '.git'))

class GitWorkspaceManager(cascade_yaml_config.ArgparseSubcommandManager):

    def __init__(self, **kwargs):
        super(GitWorkspaceManager, self).__init__(**kwargs)
        for par in kwargs:
            self.logger.debug("init par "+ par+" --> "+str(kwargs[par]))



    def create(self):
        uuid_ = uuid.uuid4()
        path = os.path.join(self.base_path, str(uuid_))
        os.mkdir(path)
        print('Created a new workspace in: ' + path)
        return uuid

    def list(self):
        print('The current git repositories found in ' + self.base_path + ' are:')
        count = 0
        for root, dirs, files in os.walk(self.base_path, topdown=True):
            if is_git_clone(root):
                print("  " + str(count) + " : " + root)
                count += 1
                dirs[:] = []
                #del dirs

    def remove(self, uuid):
        if str(uuid[0]) == '/':
            path = str(uuid)
        else:
            path = os.path.join(self.base_path, str(uuid))
        if not os.path.exists(path):
            count = 0
            for root, dirs, files in os.walk(self.base_path, topdown=True):

                if is_git_clone(root):
                    if str(count) == str(uuid):
                        path = root

                        break
                    count += 1
                    del dirs
        print("removing: " + path)

        try:
            # os.rmdir(path)
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            print('error: failed to remove the directory ' + path)

    def deploy(self,
                   git_dest='src',
                   tempdir='',
                   tarfile='',
                   integration=False,
                   origin_update=False,
                   upstream_update=False,
                   rebase_update=False,
                   integration_branch='integration',
                   integration_branches=[],
                   prlist=[],
                   origin='',
                   origin_master='master',
                   pull_flags=['ff-only'],
                   upstream=''):


        if git_dest[0] != '/':
            final_dest = os.path.join(self.base_path, git_dest)
        else:
            final_dest = git_dest
        if os.path.exists(final_dest):
            self.logger.error("Exiting: alreay existing Git folder destination: " + final_dest )
            exit()
        if tempdir:
            if os.path.exists(tempdir):
                import uuid
                new_tempdir = os.path.normpath(tempdir) + str(uuid.uuid4().fields[-1])[:10]
                self.logger.info("Existing temporary folder: %s substituting with %s" % (tempdir, new_tempdir))
                tempdir = new_tempdir
            dest = tempdir
        else:
            dest = final_dest

        # print("@@@@@@@@@@@@@@@@@@@@", dest, self.dry_run)
        dev_git = utils.git_repo(dest, logger=self.logger, dry_run=self.dry_run)

        origin_branches = [origin_master] + utils.get_branches(origin, branch_selection= integration_branches)
        self.logger.info("searching %s found  origin_branches %s" % (str([origin_master] + integration_branches), str(origin_branches)))
        upstream_branches = utils.get_branches(
            upstream,
            branch_pattern='.*?\s+refs/pull/([0-9]*?)/head\s+',
            # branch_exclude_pattern='.*?\s+refs/pull/({branch})/merge\s+',
            branch_format_string='pull/{branch}/head',
            branch_selection=prlist)


        local_pr = utils.trasf_match(upstream_branches, in_match='.*/([0-9]*)/(.*)', out_format='pull/{name}/clean')
        self.logger.info("found %s searching for upstream_branches %s->" % (str(local_pr), str(upstream_branches)))

        remote_names = {'origin': 'origin'}
        if upstream != origin:
            remote_names['upstream'] = 'upstream' 
        else:
                remote_names['upstream'] = 'origin'

        if not os.path.exists(dest):
            self.logger.info("MISSING destination_dir-->" + dest + "<-- ")
            os.makedirs(dest)

            self.logger.info("init git repo into dir: " + dest )
            dev_git.init()

            dev_git.get_remotes()

            self.logger.info("Adding remote origin %s fetching branches %s" % (origin, str(origin_branches)))
            dev_git.add_remote(origin, name='origin', fetch_branches=origin_branches)
            if upstream != origin:
                dev_git.add_remote(upstream, name='upstream')
                self.logger.info("Adding remote upstream %s " % (upstream))

            dev_git.fetch(name='origin', prefix="{name}/",  branches=origin_branches)

            if integration:
                if len(origin_branches) > 0:
                    upstream_clean = 'origin/' + origin_branches[0]
                    # print("--------------------------------------" + upstream_clean + "-----------------------")
                    dev_git.checkout(upstream_clean)
                    if upstream_update:
                        dev_git.sync_upstream(upstream=remote_names['upstream'] )
                    dev_git.checkout(upstream_clean, newbranch=integration_branch)

                    if upstream_update:
                        dev_git.sync_upstream(upstream=remote_names['upstream'])

                    for b in origin_branches[1:]:
                        b = 'origin/' + b
                        if upstream_update:
                            merge_branch = b + '_merge'
                            self.logger.info("merge updated upstream branch: " + b + " into " + merge_branch)
                            dev_git.checkout(b, newbranch=merge_branch)
                            dev_git.merge(upstream_clean)

                            if rebase_update:
                                rebase_branch = b + '_rebase'
                                self.logger.info("merge upstream, rebase with -Xtheirs option and merge againnormal merge with :-Xtheirs branch: " + b + " into " + rebase_branch)
                                dev_git.checkout(b, newbranch=rebase_branch)
                                dev_git.merge(upstream_clean)
                                dev_git.rebase(branch=upstream_clean, options=['-Xtheirs'])
                                dev_git.merge(merge_branch, options=['-Xtheirs'])

                                self.logger.info("direct in_place rebase updated upstream of branch: " + b)
                                dev_git.checkout(b)
                                dev_git.rebase(branch=upstream_clean, options=['-Xtheirs'])

                                self.logger.info(
                                    "comparing direct in_place rebased branch: " + b + " with merged,rebased and remerged branch " + rebase_branch)
                                out_diff = dev_git.compare_branches(b, rebase_branch)
                                if out_diff == '':
                                    dev_git.delete(rebase_branch)
                                else:
                                    self.logger.warning("DIFF " + b + " " + rebase_branch + "\n" + out_diff)

                                #dev_git.merge(merge_branch, options=['-Xtheirs'])
                                self.logger.info(
                                    "comparing direct in_place rebased %s with simply merged %s " % (b, merge_branch))
                                out_diff = dev_git.compare_branches(b, merge_branch)
                                if out_diff == '':
                                    self.logger.info("removing " + merge_branch)
                                    dev_git.delete(merge_branch)
                                else:
                                    self.logger.warning("DIFF " + b + " " + merge_branch + "\n" + out_diff)
                            # not needed? dev_git.checkout(b)

                            # dev_git.delete(merge_branch)
                        dev_git.checkout(b)




                    dev_git.fetch(name=remote_names['upstream'], branches=local_pr)

                    for n, branch in local_pr.items():
                        self.logger.info(
                            "itegrating pr %s (%s) into %s by updating into %s" % (n, branch, integration_branch, branch + '_update', ))
                        dev_git.checkout(branch, newbranch=branch + '_update')
                        dev_git.merge(upstream_clean, comment='sync with upstream develop ')
                        dev_git.checkout(integration_branch)
                        dev_git.merge(branch + '_update', comment='merged ' + branch)

                    dev_git.checkout(integration_branch)
                    for branch in origin_branches[1:]:
                        self.logger.info("merging %s into %s" % (branch, integration_branch))
                        dev_git.merge('origin/' + branch, comment='merged ' + branch)
            else:
                dev_git.fetch(name='origin', branches=[origin_master])
                dev_git.checkout(origin_master)

            dev_git.copy_repo( tarfile, final_dest) 
            final_dest = os.path.normpath(os.path.abspath(final_dest))
            dest = os.path.normpath(os.path.abspath(dest))
            if final_dest != dest :
                if os.path.exists(dest):
                    import shutil
                    shutil.rmtree(dest)
            
        else:
            self.logger.warning("Folder ->" + dest + "<- already existing")
            if origin_update:
                self.logger.info("Updating Folder ->" + dest + "<-")
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
                        dev_git.sync_upstream(upstream=remote_names['upstream'], options=merge_options)
