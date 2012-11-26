import getpass
import logging
import os
import sys
import os.path
import yaml

CONFIG_DEFAULTS = {
    'defaults': {
        'keypair_name': getpass.getuser(),
        'keypair_location': os.path.expanduser('~/.ssh/id_rsa.pub'),
        'flavor_name': 'm1.small',
        'remote_user': 'ubuntu',
        'auto_provision': False,
        'forward_agent': True,
        'dotfiles': '.vimrc, .gitconfig, .gitignore, .screenrc',
        'sec_groups': [
            'icmp, -1, -1, 0.0.0.0/0',
            'tcp, 22, 22, 0.0.0.0/0',
        ]
    }
}


class EnvyConfig(object):
    """Base class for envy commands"""

    def __init__(self, args):
        self.args = args

    def get_config(self):
        args = self.args
        user_config_path = os.path.expanduser('~/.cloudenvy.yml')
        project_config_path = './Envyfile.yml'

        # Check that config files are actually present.
        self._check_config_files(user_config_path, project_config_path)

        user_config = yaml.load(open(user_config_path))
        project_config = yaml.load(open(project_config_path))

        config = dict(CONFIG_DEFAULTS.items() + project_config.items() +
                      user_config.items())
        base_name = config['project_config']['name']

        try:
            envy_name = args.name
            assert envy_name
        except (AssertionError, AttributeError):
            #FIXME(jakedahn): This should probably print an error...
            pass
        else:
            config['project_config']['name'] = '%s-%s' % (base_name, envy_name)
        finally:
            config['project_config']['base_name'] = base_name

        if 'keypair_location' in config['cloudenvy']:
            full_path = os.path.expanduser(
                config['cloudenvy']['keypair_location'])
            config['cloudenvy']['keypair_location'] = full_path

        # Parses which cloud credentials are to be used.
        clouds = config['cloudenvy']['clouds']
        if args.cloud:
            if args.cloud in clouds.keys():
                config['cloudenvy'].update({'cloud': clouds[args.cloud]})
            else:
                logging.error("Cloud %s is not found in your config" % args.cloud)
                logging.debug("Clouds Found %s" % ", ".join(config['cloudenvy']['clouds'].keys()))
                sys.exit(1)
        else:
            for name, settings in clouds.items():
                if 'default' in settings and settings['default'] == True:
                    default_cloud = settings
            if default_cloud:
                config['cloudenvy'].update({'cloud': default_cloud})
            else:
                config['cloudenvy'].update({'cloud': clouds.items()[0][1]})

        # Validate that required items are set
        self._validate_config(config, user_config_path, project_config_path)
        return config

    def _validate_config(self, config, user_config_path, project_config_path):
        for item in ['name']:
            config_item = config['project_config'].get(item)
            if config_item is None:
                raise SystemExit('Missing Configuration: Make sure `%s` is set'
                                 ' in %s' % (item, project_config_path))

        # If credentials config is not set, send output to user.
        for item in ['username', 'password', 'tenant_name', 'auth_url']:
            config_name = 'os_%s' % item
            config_item = config['cloudenvy']['cloud'].get(config_name)

            if config_item is None:
                raise SystemExit('Missing Credentials: Make sure `%s` is set '
                                 'in %s' % (config_name, user_config_path))

    def _check_config_files(self, user_config_path, project_config_path):
        if not os.path.exists(user_config_path):
            raise SystemExit('Could not read `%s`. Make sure '
                             '~/.cloudenvy has the proper configuration.'
                             % user_config_path)
        if not os.path.exists(project_config_path):
            raise SystemExit('Could not read `%s`. Make sure you '
                             'have an EnvyFile in your current directory.'
                             % project_config_path)
