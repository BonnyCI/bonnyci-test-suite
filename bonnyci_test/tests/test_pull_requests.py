
from bonnyci_test.waiter import WaiterTimeOut
from bonnyci_test.tests import base

TEST_OUTPUT = "XXX TEST_ID: %s"


class BonnyCIPRTests(base.BonnyCITestBase):
    def setUp(self):
        super(BonnyCIPRTests, self).setUp()
        self.test_output = TEST_OUTPUT % self.test_id
        self.create_fork()
        self.downstream = self.checkout_downstream()
        self.create_downstream_branch(self.test_id)

        self.bot_name = self.config.get('DEFAULT', 'bot_name')
        self.check_name = self.config.get('DEFAULT', 'check_context')
        self.gate_name = self.config.get('DEFAULT', 'gate_context')

        self.check_status = "%s:%s" % (self.bot_name, self.check_name)
        self.gate_status = "%s:%s" % (self.bot_name, self.gate_name)

    def status_check(self, state):
        return self.check_status + (':%s' % state)

    def status_gate(self, state):
        return self.gate_status + (':%s' % state)

    def test_pr_failed_gate_not_merged(self):
        """Ensure a PR with a failing gate job is not merged"""
        # set the check job to pass, the gate job to fail
        self.downstream.set_tests_fail(
            check=False, gate=True, output=self.test_output)
        self.commit_downstream_changes(self.downstream.changes)

        # push up to the test fork
        self.push_downstream()

        # create a pull request against the upstream
        pr = self.create_pull_request(
            branch=self.test_id, target_repo=self.githubs.upstream.repo)

        # ensure check passes
        self.wait_for_pull_request_status(
            pr, self.status_check('success'))

        # approve it
        self.approve_pull_request(pr)

        # ensure gate fails
        self.wait_for_pull_request_status(
            pr, self.status_gate('failure'))

        # ensure that logs for each pipeline were published
        self.assert_logs_published(
            pr, context=self.check_status, string=self.test_output)
        self.assert_logs_published(
            pr, context=self.gate_status, string=self.test_output)

    def test_pr_failed_check_no_gate_job(self):
        """Ensure a gate job is not run if a check job has not passed"""
        # Set check job to fail
        self.downstream.set_tests_fail(
            check=True, gate=True, output=self.test_output)

        self.commit_downstream_changes(self.downstream.changes)

        # push up to the test fork
        self.push_downstream()

        # create a pull request against the upstream
        pr = self.create_pull_request(
            branch=self.test_id, target_repo=self.githubs.upstream.repo)

        # ensure check passes
        self.wait_for_pull_request_status(
            pr, self.status_check('failure'))

        # TODO: Update waiter to return true on multiple statuses, and check
        # for pending/failure/success instead of just pending.
        self.assertRaises(
            WaiterTimeOut,
            self.wait_for_pull_request_status,
            pr, self.status_gate('pending'), 12)

        # ensure that logs for each pipeline were published
        self.assert_logs_published(
            pr, context=self.check_status, string=self.test_output)

    def test_pr_patch_merges(self):
        """Ensure an approved PR with passing gate+check is successfully
        merged.  This waits until the check job passes before adding the
        required approval"""
        # create a file in the repo
        test_file = self.downstream.create_file(uniq=self.test_id)
        self.commit_downstream_changes(self.downstream.changes)

        # push up to the test fork
        self.push_downstream()

        # create a pull request against the upstream
        pr = self.create_pull_request(
            branch=self.test_id, target_repo=self.githubs.upstream.repo)

        # ensure check passes
        self.wait_for_pull_request_status(
            pr, self.status_check('success'))

        # approve it
        self.approve_pull_request(pr)

        # ensure gate passes
        self.wait_for_pull_request_status(
            pr, self.status_gate('success'))

        # wait for the PR to close and the file to be accessible via API
        self.wait_for_pr_merged(pr)
        self.wait_for_repo_file(self.githubs.upstream, test_file)

        # ensure the file merged correctly
        self.assert_repo_contains_file(
            self.githubs.upstream, test_file, self.test_id)

    def test_pr_patch_merges_quick_approval(self):
        """Ensure an approved PR with passing gate+check is successfully
        merged.  This immediately adds the required approval before either the
        check or gate jobs finish.
        """
        # create a file in the repo
        test_file = self.downstream.create_file(uniq=self.test_id)
        self.commit_downstream_changes(self.downstream.changes)

        # push up to the test fork
        self.push_downstream()

        # create a pull request against the upstream
        pr = self.create_pull_request(
            branch=self.test_id, target_repo=self.githubs.upstream.repo)

        # approve it
        self.approve_pull_request(pr)

        # ensure check passes
        self.wait_for_pull_request_status(
            pr, self.status_check('success'))

        # ensure gate passes
        self.wait_for_pull_request_status(
            pr, self.status_gate('success'))

        # wait for the PR to close and the file to be accessible via API
        self.wait_for_pr_merged(pr)
        self.wait_for_repo_file(self.githubs.upstream, test_file)

        # ensure the file merged correctly
        self.assert_repo_contains_file(
            self.githubs.upstream, test_file, self.test_id)
