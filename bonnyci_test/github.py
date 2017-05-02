
import base64
import logging

import github3

LOG = logging.getLogger(__name__)


class Github(object):
    def __init__(self, username, org, reponame, api_token, ssh_key):
        self.username = username
        self.org = org
        self.reponame = reponame
        self.api_token = api_token
        self.ssh_key = ssh_key
        self._github = None
        self._user = None
        self._repo = None
        self._pull_requests = []

    def __str__(self):
        return ("Github: %s/%s, auth: as %s'" %
                (self.org, self.reponame, self.username))

    def cleanup(self):
        for pr in self._pull_requests:
            pr.close()

    def authenticate(self):
        LOG.debug('Authenticating to github for %s...', self.org)
        github = github3.GitHub()
        github.login(token=self.api_token)
        self._github = github

    @property
    def repo(self):
        if not self._repo:
            self._repo = self._github.repository(self.org, self.reponame)
        return self._repo

    @property
    def connection(self):
        if not self._github:
            self._github = self.authenticate()
        return self._github

    def create_fork(self, org, repo):
        """Creates a fork of the specified org/repo"""
        upstream = self._github.repository(org, repo)
        upstream.create_fork()
        self.load()

    def foo(self):
        return 'bar'

    def create_pull_request(self, branch, target_repo, target_branch='master',
                            description=None):
        upstream_org = target_repo.owner.login
        upstream_repo = target_repo.name
        repo = self._github.repository(upstream_org, upstream_repo)
        pr = repo.create_pull(
            title='BonnyCI Test Pull Request',
            base=target_branch,
            head='%s:%s' % (self.username, branch),
            body=description,
        )
        self._pull_requests.append(pr)
        return pr

    def add_review(self, number, state):
        # currently no github3 support for adding reviews
        pull_request = self._github.pull_request(
            self.org, self.reponame, number)
        data = {'event': state}
        url = self._github._build_url('reviews', base_url=pull_request._api)
        headers = {'Accept': 'application/vnd.github.black-cat-preview+json'}
        self._github._post(url, data=data, headers=headers)

    def get_statuses(self, pull_request):
        pull_request.refresh()
        sha = pull_request.head.sha
        statuses = {}
        for status in self.repo.commit(sha).statuses():
            status = status.as_dict()
            creator = status['creator']['login']
            context = '%s:%s' % (creator, status['context'])
            if context not in statuses:
                statuses[context] = status
        return statuses

    def get_file_contents(self, path):
        self.repo.refresh()
        content = self.repo.file_contents(path)
        if content:
            return base64.b64decode(content.content)
