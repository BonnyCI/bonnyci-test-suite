
import os

RUN_SH_TEMPLATE = """
#!/bin/bash

FAIL_CHECK=%(fail_check)s
FAIL_GATE=%(fail_gate)s
TEST_OUTPUT="%(test_output)s"

echo "$TEST_OUTPUT"

case "$BONNYCI_TEST_PIPELINE" in
    "check") [[ "$FAIL_CHECK" == 1 ]] && exit 1 ;;
    "gate") [[ "$FAIL_GATE" == 1 ]] && exit 1 ;;
esac

exit 0
"""


class Editor(object):
    """Modifies contents of a locally checked out repo. Assumes
    we're working with a BonnyCI v2.5 managed repo (.bonncyi/run.sh)

    This can be update/extended for v3/.zuul.yaml.
    """
    def __init__(self, downstream_dir):
        self.path = downstream_dir
        self._changes = []

    def set_tests_fail(self, check=False, gate=False, output=None):
        fail_check = fail_gate = 0
        if check:
            fail_check = 1
        if gate:
            fail_gate = 1
        ctxt = {
            'fail_check': fail_check,
            'fail_gate': fail_gate,
            'test_output': '',
        }
        if output:
            ctxt['test_output'] = output

        bci_dir = os.path.join(self.path, '.bonnyci')
        run_sh = os.path.join(bci_dir, 'run.sh')
        if not os.path.isdir(bci_dir):
            os.mkdir(bci_dir)
        with open(run_sh, 'w') as out:
            out.write((RUN_SH_TEMPLATE % ctxt).strip())
        os.chmod(run_sh, 0755)

        msg = 'Set: %s' % \
              ' '.join(['%s=%s' % (k, v) for k, v in ctxt.items()])
        self._changes.append((
            os.path.relpath(run_sh, self.path),
            msg
        ))

    def create_file(self, uniq=None, path=None, contents=None):
        if not uniq:
            uniq = str(uuid.uuid4())
        if not path:
            path = os.path.join(self.path, 'test_files', uniq)
        contents = contents or uniq
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as out:
            out.write(contents)
        rel_path = os.path.relpath(path, self.path)

        self._changes.append((
            rel_path, 'Created new test file'))
        return rel_path

    @property
    def changes(self):
        return self._changes
