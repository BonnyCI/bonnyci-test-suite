
import time


class WaiterTimeOut(Exception):
    pass


class BaseWaiter(object):
    def __init__(self, retries=10, interval=1):
        self.retries=retries
        self.interval = interval
        self.fail_msg = '%s did not succeed after %s retries at %s sec.' % (
            self.__class__, self.retries, self.interval)

    def wait_function(self):
        pass

    def wait(self):
        i = 0
        while i <= self.retries:
            if self.wait_function():
                return True
            else:
                i += 1
                time.sleep(self.interval)
        raise WaiterTimeOut(self.fail_msg)


class PollingWaiter(BaseWaiter):
    def __init__(self, retries=10, interval=1):
        super(PollingWaiter, self).__init__(retries, interval)
        self.i = 0

    def wait(self):
        i = 0
        while i <= self.retries:
            if self.wait_function():
                return True
            else:
                i += 1
                time.sleep(self.interval)
        raise WaiterTimeOut(self.fail_msg)


# TODO: Expand to support waiting for a webhook instead of polling
class PullRequestStatus(PollingWaiter):
    def __init__(self, github, pull_request, status, retries=10, interval=1):
        super(PullRequestStatus, self).__init__(retries, interval)
        self.github = github
        self.pr = pull_request
        self.target_context = ':'.join(status.split(':')[:2])
        self.target_state = status.split(':')[2]

    def wait_function(self):
        status = self.github.get_statuses(self.pr).get(self.target_context, {})
        if status.get('state') == self.target_state:
            return True
        return False


class PullRequestMerged(PollingWaiter):
    def __init__(self, github, pull_request, retries=10, interval=1):
        super(PullRequestMerged, self).__init__(retries, interval)
        self.github = github
        self.pr = pull_request

    def wait_function(self):
        self.pr.refresh()
        return self.pr.merged


class FileExistsInRepo(PollingWaiter):
    def __init__(self, github, path, retries=10, interval=1):
        super(FileExistsInRepo, self).__init__(retries, interval)
        self.github = github
        self.path = path

    def wait_function(self):
        return (self.github.get_file_contents(self.path) is not None)
