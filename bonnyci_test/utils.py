
from six.moves import configparser as ConfigParser

DEFAULT_CONFIG = 'test_config.conf'


def load_config(path=DEFAULT_CONFIG):
    config = ConfigParser.ConfigParser({'ssh_key': '~/.ssh/id_rsa'})
    loaded = config.read(path)
    if not loaded:
        raise Exception("Could not load config from %s" % path)
    return config
