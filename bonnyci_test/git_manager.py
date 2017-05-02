
import os
import shutil

import git

import logging


LOG = logging.getLogger(__name__)


def _mkdir(path):
    if not os.path.isdir(path):
        os.mkdir(path)


class GitManager(object):
    def __init__(self, git_dir):
        _mkdir(git_dir)
        self.git_dir = git_dir
        self.repos = {}
        self._current_branch = 'master'
        self._branches = []

    def cleanup(self):
        for _, org in self.repos.items():
            for _, repo in org.items():
                shutil.rmtree(repo.working_dir)

    def _ensure_repo(self, github, protocol):

        if protocol == 'ssh':
            remote = 'git@github.com:%s/%s.git' % (
                github.org, github.reponame)
        else:
            remote = 'https://github.com/%s/%s.git' % (
                github.org, github.reponame)

        base_path = os.path.join(self.git_dir, github.org)
        _mkdir(base_path)

        repo_path = os.path.join(base_path, github.reponame)
        if not os.path.isdir(repo_path):
            _mkdir(repo_path)
            repo = git.Repo.clone_from(remote, repo_path)
        else:
            repo = git.Repo(repo_path)

        if github.org not in self.repos:
            self.repos[github.org] = {}
        self.repos[github.org][github.reponame] = repo
        return repo.working_dir

    def clone(self, github, protocol='https'):
        return self._ensure_repo(github, protocol)

    def get_repo(self, org, reponame):
        try:
            return self.repos[org][reponame]
        except KeyError:
            return None

    def create_branch(self, github, branch):
        """creates and checks out a branch at the current head"""
        self._ensure_repo(github, branch)
        repo = self.get_repo(github.org, github.reponame)
        head = repo.create_head(branch)
        repo.head.reference = head
        self._current_branch = branch
        self._branches = [branch]

    def commit_changes(self, github, changes):
        repo = self.get_repo(github.org, github.reponame)
        repo.index.add([f[0] for f in changes])
        msg = 'Test commit\n\n'
        for k, v in changes:
            msg += ' * %s: %s\n' % (k, v)
        repo.index.commit(msg)
        repo.git.clean('-x', '-f', '-d')

    def push(self, github, remote='origin'):
        LOG.debug(
            "Pushing local branch %s to %s (%s/%s)" %
            (self._current_branch, remote, github.org, github.reponame))
        repo = self.get_repo(github.org, github.reponame)
        remote = git.Remote(repo, remote)
        if github.ssh_key:
            ssh_command = 'ssh -i %s' % os.path.expanduser(github.ssh_key)
        else:
            ssh_command = 'ssh'
        with remote.repo.git.custom_environment(GIT_SSH_COMMAND=ssh_command):
            res = remote.push(self._current_branch)[0]
        if res.flags & git.remote.PushInfo.ERROR:
            raise Exception(
                "git push failed to remote @ %s/%s with msg: %s" %
                (github.org, github.reponame, res.summary))
