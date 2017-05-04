
import os

from six.moves import configparser as ConfigParser


def load_config():
    config_paths = [
        os.path.expanduser("~/.bonnyci_test.conf"),
        'bonnyci_test.conf',
        '/etc/bonnyci_test.conf',
    ]
    config = ConfigParser.ConfigParser({'ssh_key': '~/.ssh/id_rsa'})
    loaded = config.read(config_paths)
    if not loaded:
        raise Exception("Could not load config from %s" % path)
    return config
