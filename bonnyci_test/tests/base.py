
import os
import requests
import uuid

from collections import namedtuple
import logging

import testtools

from bonnyci_test import utils
from bonnyci_test import waiter
from bonnyci_test.editor import Editor
from bonnyci_test.github import Github
from bonnyci_test.git_manager import GitManager


class BonnyCITestBase(testtools.TestCase):
    log = None

    def setUp(self):
        super(BonnyCITestBase, self).setUp()
        self.config = utils.load_config()

        logging.basicConfig(level=logging.DEBUG)
        self.log = logging.getLogger(__name__)

        self.githubs = namedtuple(
            'Githubs', 'upstream downstream')

        test_name = self.id().split('.').pop()

        _git_dir = os.path.expanduser(self.config.get('DEFAULT', 'git_dir'))
        utils.mkdir(_git_dir)
        git_dir = os.path.join(_git_dir, test_name)
        self.git = GitManager(git_dir)

        self.connect_githubs()

        self.test_id = str(uuid.uuid4())

        self.check_job = self.config.get('DEFAULT', 'check_job')
        self.gate_job = self.config.get('DEFAULT', 'gate_job')

    def tearDown(self):
        super(BonnyCITestBase, self).tearDown()
        self.git.cleanup()
        self.githubs.downstream.cleanup()
        self.githubs.upstream.cleanup()

    def connect_githubs(self):
        for org in ['upstream', 'downstream']:
            section = 'github_connection_%s' % org
            gh = Github(
                org=self.config.get(section, 'org'),
                reponame=self.config.get(section, 'repo'),
                api_token=self.config.get(section, 'api_token'),
                ssh_key=self.config.get(section, 'ssh_key'))
            gh.authenticate()
            setattr(self.githubs, org, gh)

    def create_fork(self):
        """creates a fork in the downstream org of the upstream repo, if one
        does not already exist. forcing deletes any existing fork and creates
        a new one.
        """
        downstream = self.githubs.downstream
        if not downstream.repo:
            self.log.debug(
                "Fork of %s not found, creating at %s" %
                (self.githubs.upstream, downstream))
            downstream.create_fork(
                self.githubs.upstream.org, self.githubs.upstream.reponame)

    def checkout_downstream(self):
        """Clones the downstream fork and returns an Editor"""
        downstream_dir = self.git.clone(
            self.githubs.downstream, protocol='ssh')
        return Editor(downstream_dir)

    def create_downstream_branch(self, name):
        self.git.create_branch(self.githubs.downstream, branch=name)

    def commit_downstream_changes(self, changes):
        self.git.commit_changes(self.githubs.downstream, changes, self.id())

    def push_downstream(self):
        self.git.push(self.githubs.downstream)

    def create_pull_request(self, branch, target_repo, target_branch='master',
                            description=''):
        desc = self.id() + '\n\n' + description
        return self.githubs.downstream.create_pull_request(
            branch, target_repo, target_branch, desc)

    def wait_for_pull_request_status(self, pull_request, status, retries=None):
        retries = retries or self.config.get('DEFAULT', 'pr_status_timeout')
        waiter.PullRequestStatus(
            retries=retries,
            github=self.githubs.upstream,
            pull_request=pull_request, status=status).wait()

    def wait_for_pr_merged(self, pull_request):
        waiter.PullRequestMerged(
            github=self.githubs.upstream, pull_request=pull_request).wait()

    def wait_for_repo_file(self, github, path):
        waiter.FileExistsInRepo(github=github, path=path).wait()

    def approve_pull_request(self, pull_request):
        self.githubs.upstream.add_review(pull_request.number, 'APPROVE')

    def assert_logs_published(self, pull_request, context, string=None):
        status = self.githubs.upstream.get_statuses(pull_request)[context]
        url = status['target_url']
        # target_url *may* be empty if we've beaten the reporter
        self.assertNotEqual(
            url, None,
            'commit status for %s does not have a target_url' % pull_request)

        if 'gate' in context:
            job = self.gate_job
        else:
            job = self.check_job
        url += '%s/console.html' % job

        resp = requests.get(url)
        self.assertEqual(
            resp.status_code, 200,
            'Request for %s logs @ %s returned status code %s, not 200.' %
            (job, url, resp.status_code))

        if string:
            self.assertIn(
                string, resp.text,
                'Did not find expected string "%s" in %s' % (string, url))

    def assert_repo_contains_file(self, github, path, expected_content=None):
        content = github.get_file_contents(path)
        self.assertNotEqual(
            content, None,
            'Could not get repo file contents of %s' % path)
        if expected_content:
            self.assertEqual(content, expected_content)
