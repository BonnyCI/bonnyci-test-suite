import os
import testtools
import shutil
import subprocess
import tempfile

from bonnyci_test import editor as bci_editor


class TestEditorV25(testtools.TestCase):
    def setUp(self):
        super(TestEditorV25, self).setUp()
        self.path = tempfile.mkdtemp()
        self.run_sh = os.path.join(self.path, '.bonnyci', 'run.sh')
    def tearDown(self):
        super(TestEditorV25, self).tearDown()
        shutil.rmtree(self.path)

    def test_set_gate_fail(self):
        editor = bci_editor.Editor(self.path)
        editor.set_tests_fail(check=False, gate=True)
        self.assertTrue(os.path.isfile(self.run_sh))
        proc = subprocess.Popen(
            [self.run_sh], env={'BONNYCI_TEST_PIPELINE': 'check'})
        proc.communicate()
        self.assertEqual(proc.returncode, 0)
        proc = subprocess.Popen(
            [self.run_sh], env={'BONNYCI_TEST_PIPELINE': 'gate'})
        proc.communicate()
        self.assertEqual(proc.returncode, 1)

    def test_set_check_fail(self):
        editor = bci_editor.Editor(self.path)
        editor.set_tests_fail(check=True, gate=False)
        self.assertTrue(os.path.isfile(self.run_sh))
        proc = subprocess.Popen(
            [self.run_sh], env={'BONNYCI_TEST_PIPELINE': 'check'})
        proc.communicate()
        self.assertEqual(proc.returncode, 1)
        proc = subprocess.Popen(
            [self.run_sh], env={'BONNYCI_TEST_PIPELINE': 'gate'})
        proc.communicate()
        self.assertEqual(proc.returncode, 0)

    def test_set_test_output(self):
        editor = bci_editor.Editor(self.path)
        editor.set_tests_fail(check=False, gate=False, output='FOOXBAR')
        self.assertTrue(os.path.isfile(self.run_sh))
        proc = subprocess.Popen(
            [self.run_sh], env={'BONNYCI_TEST_PIPELINE': 'check'},
            stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        self.assertEqual(proc.returncode, 0)
        self.assertIn('FOOXBAR', stdout)

    def test_create_file(self):
        editor = bci_editor.Editor(self.path)
        path = editor.create_file(uniq='foo', contents='bar')
        test_file = os.path.join(self.path, 'test_files', 'foo')
        self.assertTrue(os.path.isfile(test_file))
        self.assertEqual(open(test_file).read(), 'bar')
        self.assertEqual(path, 'test_files/foo')

    def test_change_log(self):
        editor = bci_editor.Editor(self.path)
        editor.set_tests_fail(check=False, gate=False, output='FOOXBAR')
        editor.create_file(uniq='foo')
        files_changed = [f[0] for f in editor.changes]
        self.assertIn('.bonnyci/run.sh', files_changed)
        self.assertIn('test_files/foo', files_changed)


