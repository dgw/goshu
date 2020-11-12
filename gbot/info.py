#!/usr/bin/env python3
# Goshu IRC Bot
# written by Daniel Oaks <daniel@danieloaks.net>
# licensed under the ISC license

import hashlib
import json
import os

from .libs.helper import timedelta_to_string, string_to_timedelta
from .irc import default_timeout_check_interval, default_timeout_length


class InfoStore():
    """Stores and manages general information, settings, etc; to be subclassed."""
    version = 1

    def __init__(self, bot, path):
        self.bot = bot
        self.path = path
        self.store = {}
        self.load()

    # loading and saving
    def load(self):
        """Load information from our data file."""
        try:
            with open(self.path, 'r', encoding='utf-8') as info_file:
                self.store = json.loads(info_file.read())
                current_version = self.store.get('store_version', 1)
                while current_version < self.version:
                    current_version = self.update_store_version(current_version)
        except FileNotFoundError:
            self.initialize_store()

    def save(self):
        """Save information to our data file."""
        # only save file if we have data
        if not self.store:
            return

        # ensure info file folder exists
        folder = os.path.dirname(self.path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        with open(self.path, 'w', encoding='utf-8') as info_file:
            info_file.write(json.dumps(self.store, sort_keys=True, indent=4))

    # version updating
    def initialize_store(self):
        """Initialize the info store."""
        self.store = {
            'store_version': self.version,
        }

    def update_store_version(self, current_version):
        """Update our internal store from the given version, return the new version."""
        raise NotImplementedError('update_store_version must be replaced when subclassed')

    # helper function
    def _split_base_from_key(self, key):
        if isinstance(key, (list, tuple)):
            base = self.store
            for key_part in key[:-1]:
                if key_part not in base:
                    return None, None
                base = base[key_part]
            key = key[-1]
        else:
            base = self.store

        return base, key

    def _create_base_from_key(self, key):
        if isinstance(key, (list, tuple)):
            base = self.store
            for key_part in key[:-1]:
                if key_part not in base:
                    base[key_part] = {}
                base = base[key_part]

    # getting and setting
    def has_key(self, key):
        """Returns True if we have the given key in our store."""
        base, key = self._split_base_from_key(key)
        if base is None:
            return False

        return key in base

    def has_all_keys(self, *keys):
        """Returns True if we have all of the given keys in our store."""
        for key in keys:
            if not self.has_key(key):
                return False
        return True

    def set(self, key, value, create_base=True):
        """Sets key to value in our store."""
        # find base
        if isinstance(key, (list, tuple)):
            base = self.store
            for key_part in key[:-1]:
                if key_part not in base:
                    if create_base:
                        base[key_part] = {}
                    else:
                        raise Exception('key_part not in base: {}'.format(key))
                base = base[key_part]
            key = key[-1]
        else:
            base = self.store

        base[key] = value
        self.save()

    def get(self, key, default=None):
        """Returns value from our store, or default if it doesn't exist."""
        base, key = self._split_base_from_key(key)
        if base is None:
            return default

        return base.get(key, default)

    def remove(self, key):
        """Remove the given key from our store."""
        if not self.has_key(key):
            return

        # find base
        if isinstance(key, (list, tuple)):
            base = self.store
            for key_part in key[:-1]:
                if key_part not in base:
                    # XXX - TODO: - wtf to do here?
                    if create_base:
                        base[key_part] = {}
                    else:
                        raise Exception('key_part not in base: {}'.format(key))
                base = base[key_part]
            key = key[-1]
        else:
            base = self.store

        try:
            del base[key]
        except KeyError:
            pass

        self.save()

    def initialize_to(self, key, value):
        """If key is not in our store, set it to value."""
        if self.has_key(key):
            return

        self.set(key, value)

    def append_to(self, key, value):
        """Append a value to a list in our store."""
        # find base
        if isinstance(key, (list, tuple)):
            base = self.store
            for key_part in key[:-1]:
                if key_part not in base:
                    # XXX - TODO: - wtf to do here?
                    if create_base:
                        base[key_part] = {}
                    else:
                        raise Exception('key_part not in base: {}'.format(key))
                base = base[key_part]
            key = key[-1]
        else:
            base = self.store

        base[key].append(value)

        self.save()

    def remove_from(self, key, value):
        """Remove a value from a list in our store."""
        # find base
        if isinstance(key, (list, tuple)):
            base = self.store
            for key_part in key[:-1]:
                if key_part not in base:
                    # XXX - TODO: - wtf to do here?
                    if create_base:
                        base[key_part] = {}
                    else:
                        raise Exception('key_part not in base: {}'.format(key))
                base = base[key_part]
            key = key[-1]
        else:
            base = self.store

        base[key].remove(value)

        self.save()

    # complex junk
    def add_key(self, value_type, key, prompt, repeating_prompt=None, confirm_prompt=None,
                default=None, allow_none=False, blank_allowed=False, password=False,
                encrypted=False):
        """Adds given key to our store, and requests it if not yet defined.

        Args:
            value_type: type of value (eg: str, int, float)
            key: key name to store it as
            prompt: what to prompt the user with if it does not exist
            repeating_prompt: prompt on repeated question, defaults to prompt
            confirm_prompt: (str) prompt to confirm the value, prompts for value twice if given
            default: if defined, set this if the user does not type in a value themselves
            password: use a password prompt, that does not echo characters typed for the value
            allow_none: allow the default value `None` for bool keys
            blank_allowed: allow a blank string when requesting string value from the user
            encrypted: (str) store it encrypted blob in our store
        """
        if self.has_key(key):
            return

        if repeating_prompt is None:
            repeating_prompt = prompt

        if value_type == str:
            if default is not None:
                blank_allowed = True

            value = self.bot.gui.get_string(prompt,
                                            repeating_prompt=repeating_prompt,
                                            confirm_prompt=confirm_prompt,
                                            blank_allowed=blank_allowed,
                                            password=password)

            if default is not None and value.strip() == '':
                value = default

            if encrypted:
                value = self.encrypt(value)
        elif value_type == float:
            value = self.bot.gui.get_number(prompt,
                                            repeating_prompt=repeating_prompt,
                                            default=default,
                                            password=password)
        elif value_type == int:
            value = self.bot.gui.get_number(prompt,
                                            repeating_prompt=repeating_prompt,
                                            default=default,
                                            force_int=True,
                                            password=password)
        elif value_type == bool:
            value = self.bot.gui.get_bool(prompt,
                                          repeating_prompt=repeating_prompt,
                                          default=default,
                                          allow_none=allow_none,
                                          password=password)
        else:
            raise Exception('Unknown value_type {} in InfoStore[{}]'.format(value_type, self))

        self.set(key, value)

    # misc
    def encrypt(self, password):
        """Returns hashed password."""
        if type(password) == str:
            password = password.encode()
        return hashlib.sha512(password).hexdigest()

    def add_standard_keys(self):
        """Add custom keys."""
        pass


class BotSettings(InfoStore):
    """Manages basic bot settings."""
    version = 2

    # version upgrading
    def update_store_version(self, current_version):
        if current_version == 1:
            new_store = {
                'store_version': 2,
                'command_prefix': self.get('prefix', "'"),
            }
            master_bot_password = self.get('passhash', '')
            if master_bot_password:
                new_store['master_bot_password'] = master_bot_password

            # we ignore nick here, but we can ask that on startup anyway, oh well

            self.store = new_store
            self.save()

            current_version = 2

        return current_version

    # standard menus
    def add_standard_keys(self):
        wrap = self.bot._prompt_wraps

        # module settings
        #
        print(wrap['section']('Modules'))

        enabled_modules = self.get('enabled_modules', [])
        disabled_modules = self.get('disabled_modules', [])

        # core modules
        repeating_prompt = wrap['prompt']('Load all core modules? [yes]')
        prompt = '\n'.join([
            wrap['subsection']('Core Modules'),
            "Core modules provide the core functionality and commands required for running "
            "and administering your bot.",
            '',
            "You should leave this enabled unless you're reprogramming the Goshu internals.",
            '',
            repeating_prompt,
        ])
        self.add_key(bool, 'load_all_core_modules', prompt,
                     repeating_prompt=repeating_prompt,
                     default=True)

        if not self.get('load_all_core_modules'):
            for module in self.bot.modules.core_module_names:
                module_slug = module.lower()
                if module_slug not in enabled_modules and module_slug not in disabled_modules:
                    prompt = wrap['prompt']('Load core module {}: [y]'.format(module))
                    enable_module = self.bot.gui.get_bool(prompt, default=True)

                    if enable_module:
                        enabled_modules.append(module_slug)
                    else:
                        disabled_modules.append(module_slug)

        # dynamic command modules
        repeating_prompt = wrap['prompt']('Load all dynamic command modules? [yes]')
        prompt = '\n'.join([
            wrap['subsection']('Dynamic Command Modules'),
            "Dynamic command modules provide commands based off JSON and YAML files in the "
            "module's folder. This lets you create a site-specific Google search command or "
            "a command that queries and returns results from a site's API without programming "
            "your own module, instead simply creating a simple JSON file to do so.",
            '',
            wrap['note']("Disabling this will prevent Youtube, Google, Gelbooru, Wikipedia, "
                         "and the standard 'responses' commands."),
            wrap['note']("If you want to disable just specific commands, you'll be able to "
                         "run through and disable them one-by-one instead in a moment."),
            '',
            "You should leave this enabled unless you know what you're doing.",
            '',
            repeating_prompt,
        ])
        self.add_key(bool, 'load_all_dynamic_command_modules', prompt,
                     repeating_prompt=repeating_prompt,
                     default=True)

        if not self.get('load_all_dynamic_command_modules'):
            for module in sorted(self.bot.modules.dcm_module_commands):
                module_slug = module.lower()
                if module_slug not in enabled_modules and module_slug not in disabled_modules:
                    prompt = wrap['prompt']('Load dynamic command module {}: [y]'
                                            ''.format(module))
                    enable_module = self.bot.gui.get_bool(prompt, default=True)

                    if enable_module:
                        enabled_modules.append(module_slug)
                    else:
                        disabled_modules.append(module_slug)

        repeating_prompt = wrap['prompt']('Run through existing dynamic commands one-by-one '
                                          'and approve / disable them? [no]')
        prompt = '\n'.join([
            wrap['subsection']('Dynamic Commands'),
            "Dynamic commands are specific commands, such as 'gel for searching Gelbooru, "
            "'youtube for searching Youtube, 'imgur for searching Imgur, etc.",
            '',
            "Here you may disable them one-by-one, so you are left with just the ones you "
            "prefer for your own channel / network.",
            '',
            wrap['note']("Enabling this means you will be asked about newly-added dynamic "
                         "commands every time the bot is started."),
            wrap['note']("You may also disable commands while the bot is running through the "
                         "  'module commands   command."),
            '',
            repeating_prompt,
        ])
        self.add_key(bool, 'confirm_all_dynamic_commands', prompt,
                     repeating_prompt=repeating_prompt,
                     default=False)

        if self.get('confirm_all_dynamic_commands'):
            enabled_dynamic_cmds = self.get('dynamic_commands_enabled', {})
            disabled_dynamic_cmds = self.get('dynamic_commands_disabled', {})

            for module in sorted(self.bot.modules.dcm_module_commands):
                module_slug = module.lower()

                if module_slug not in enabled_dynamic_cmds:
                    enabled_dynamic_cmds[module_slug] = []
                if module_slug not in disabled_dynamic_cmds:
                    disabled_dynamic_cmds[module_slug] = []

                if self.get('load_all_dynamic_command_modules') or (
                        module_slug in enabled_modules):
                    for command in sorted(self.bot.modules.dcm_module_commands[module]):
                        if (command in enabled_dynamic_cmds[module_slug] or
                                command in disabled_dynamic_cmds[module_slug]):
                            continue
                        prompt = wrap['prompt']('Load command {}:{} : [y]'
                                                ''.format(module, command))
                        enable_command = self.bot.gui.get_bool(prompt, default=True)

                        if enable_command:
                            enabled_dynamic_cmds[module_slug].append(command)
                        else:
                            disabled_dynamic_cmds[module_slug].append(command)

            self.set('dynamic_commands_enabled', enabled_dynamic_cmds)
            self.set('dynamic_commands_disabled', disabled_dynamic_cmds)

        # other, regular modules
        other_modules = self.bot.modules.all_module_names
        for name in self.bot.modules.core_module_names:
            other_modules.remove(name)
        for module_name in self.bot.modules.dcm_module_commands:
            if module_name in other_modules:
                other_modules.remove(module_name)

        repeating_prompt = wrap['prompt']('Enable all other modules? [yes]')
        prompt = '\n'.join([
            wrap['subsection']('Other Modules'),
            "Automatically enable all other modules, and do so in the future for any added modules?",
            '',
            wrap['note']("If this is not enabled, you will be asked which ones you want to enable."),
            '',
            repeating_prompt,
        ])
        self.add_key(bool, 'enable_all_other_modules', prompt,
                     repeating_prompt=repeating_prompt,
                     default=True)

        if self.get('enable_all_other_modules'):
            for name in other_modules:
                if name not in enabled_modules and name not in disabled_modules:
                    enabled_modules.append(name)
        else:
            for name in sorted(other_modules):
                if name in enabled_modules or name in disabled_modules:
                    continue

                prompt = wrap['prompt']('Load module {}: [y]'
                                        ''.format(name))
                enable_module = self.bot.gui.get_bool(prompt, default=True)

                if enable_module:
                    enabled_modules.append(name)
                else:
                    disabled_modules.append(name)

        self.set('enabled_modules', enabled_modules)
        self.set('disabled_modules', disabled_modules)

        print(wrap['success']('Modules'))

        # bot control settings
        #
        print(wrap['section']('Bot Control'))

        repeating_prompt = wrap['prompt']("Command prefix: [']")
        prompt = '\n'.join([
            wrap['subsection']('Command Prefix'),
            "Users will need to type this before every command to use it. For instance:",
            "  .google Puppies and Kittens",
            "  'google Puppies and Kittens",
            "  !google Puppies and Kittens",
            '',
            "The recommended (and default) command prefix is ' , as this is not widely-"
            "spread, should not cause any conflicts, and is simple to type.",
            '',
            wrap['note']("[.] is a very commonly-used command prefix, so we "
                         "do not recommend using it."),
            '',
            repeating_prompt,
        ])
        self.add_key(str, 'command_prefix', prompt,
                     repeating_prompt=repeating_prompt,
                     default="'")

        repeating_prompt = wrap['prompt']("Admin Command prefix: [@]")
        prompt = '\n'.join([
            wrap['subsection']('Admin Command Prefix'),
            "In Goshu, admin commands are used to modify specific modules' settings and "
            "provide a way to let you access module-specific administrative functions.",
            '',
            "Your users will not be seeing this, and admin commands can only be used via a "
            "message directly to your bot (not to a channel the bot is in).",
            '',
            "The recommended (and default) admin command prefix is @ for admin, as it is "
            "simple to remember and will not cause any conflicts.",
            '',
            repeating_prompt,
        ])
        self.add_key(str, 'admin_command_prefix', prompt,
                     repeating_prompt=repeating_prompt,
                     default="@")

        repeating_prompt = wrap['prompt']('Master Bot Password:')
        confirm_prompt = wrap['prompt']('Confirm Master Bot Password:')
        prompt = '\n'.join([
            wrap['subsection']('Master Bot Password'),
            "This password controls master access to the bot, and anyone with this password "
            "can access ANY function, run ANY command, and have complete control over your bot."
            '',
            "Needless to say, try to make it something long and difficult to guess. "
            "Feel free to write it down, unless those pesky IRC hackers are going to get into "
            "your notebook.",
            '',
            repeating_prompt,
        ])
        self.add_key(str, 'master_bot_password', prompt,
                     repeating_prompt=repeating_prompt,
                     confirm_prompt=confirm_prompt,
                     password=True,
                     encrypted=True)

        print(wrap['success']('Bot Control'))


class IrcInfo(InfoStore):
    """Manages bot's IRC info."""
    version = 2

    # version upgrading
    def update_store_version(self, current_version):
        if current_version == 1:
            new_store = {
                'store_version': 2,
                'servers': {},
            }

            for name, info in self.store.items():
                info = info.get('connection', {})
                new_store['servers'][name] = {}
                autojoin_channels = info.get('autojoin_channels', [])
                new_store['servers'][name]['autojoin_channels'] = autojoin_channels
                new_store['servers'][name]['hostname'] = info.get('address')
                new_store['servers'][name]['ipv6'] = info.get('ipv6', False)
                new_store['servers'][name]['ssl'] = info.get('ssl', False)
                new_store['servers'][name]['port'] = info.get('port', 6667)

                # other normal attributes
                for attr_name in ['nickserv_password', 'vhost_wait',
                                  'timeout_check_interval', 'timeout_length']:
                    orig = info.get(attr_name)
                    if orig:
                        new_store['servers'][name][attr_name] = orig

                # connect attributes
                for attr_name in ['username', 'realname', 'password']:
                    orig = info.get(attr_name)
                    if orig:
                        new_attr_name = 'connect_{}'.format(attr_name)
                        new_store['servers'][name][new_attr_name] = orig

            self.store = new_store
            self.save()

            current_version = 2

        return current_version

    # standard menus
    def add_standard_keys(self, autostart=False):
        wrap = self.bot._prompt_wraps

        # module settings
        #
        print(wrap['section']('IRC Info'))

        repeating_prompt = wrap['prompt']('Default Nick:')
        prompt = '\n'.join([
            wrap['subsection']('Default Nick'),
            "This will be the default nick your bot uses for new networks. You may also set "
            "a custom nick on each network, this will just be the default choice.",
            '',
            repeating_prompt,
        ])
        self.add_key(str, 'default_nick', prompt, repeating_prompt=repeating_prompt)

        # so we always modify connections on first run
        modify_connections = not autostart

        if self.has_key('servers') and modify_connections:
            prompt = wrap['prompt']('Current IRC connections OK? [y]')
            modify_connections = not self.bot.gui.get_bool(prompt, default=True)

            # remove connections
            if modify_connections:
                current_servers = self.get('servers', {})
                for name in dict(current_servers):
                    server_info = current_servers[name]
                    prompt = wrap['prompt']('Delete Server {name} [{ssl}{host}:{port}] [n]'
                                            ''.format(**{
                                                'name': name,
                                                'ssl': '+' if server_info['ssl'] else '',
                                                'host': server_info['hostname'],
                                                'port': server_info['port'],
                                            }))
                    delete_server = self.bot.gui.get_bool(prompt, default=False)

                    if delete_server:
                        del current_servers[name]

                self.set('servers', current_servers)

        # new connections
        if modify_connections:
            header = '\n'.join([
                wrap['subsection']('New IRC Connections'),
            ])
            print(header)

            while True:
                if not self.has_key('servers') or not self.get('servers', None):
                    setup_new_connection = True
                else:
                    prompt = wrap['prompt']('Add new server? [n]')
                    setup_new_connection = self.bot.gui.get_bool(prompt, default=False)

                if not setup_new_connection:
                    break

                # setup new connection
                new_connection = {}

                prompt = wrap['prompt']('Server Nickname:')
                server_name = self.bot.gui.get_string(prompt)

                prompt = wrap['prompt']('Hostname:')
                new_connection['hostname'] = self.bot.gui.get_string(prompt)

                prompt = wrap['prompt']('IPv6? [n]')
                new_connection['ipv6'] = self.bot.gui.get_bool(prompt, default=False)

                prompt = wrap['prompt']('SSL? [y]')
                new_connection['ssl'] = self.bot.gui.get_bool(prompt, default=True)

                prompt = wrap['prompt']('Verify SSL? [y]')
                new_connection['ssl_verify'] = self.bot.gui.get_bool(prompt, default=True)

                if new_connection['ssl']:
                    default_port = 6697
                else:
                    default_port = 6667

                prompt = wrap['prompt']('Port? [{}]'.format(default_port))
                new_connection['port'] = self.bot.gui.get_number(prompt,
                                                                 force_int=True,
                                                                 default=default_port)

                default_nick = self.get('default_nick')
                prompt = wrap['prompt']('Nickname: [{}]'.format(default_nick))
                new_connection['nick'] = self.bot.gui.get_string(prompt, default=default_nick)

                print(wrap['note']('This is the bit of your userhost before the @ sign, eg:    '
                                   'nick!~username@hostname'))
                prompt = wrap['prompt']('Connect Username:')
                new_connection['connect_username'] = self.bot.gui.get_string(prompt)

                print(wrap['note']('This is something users can see when they /whois your bot'))
                prompt = wrap['prompt']('Connect Realname:')
                new_connection['connect_realname'] = self.bot.gui.get_string(prompt)

                print(wrap['note']('This is not your NickServ password, this is the IRC server '
                                   'connection password.'))
                prompt = wrap['prompt']('Connect Password:')
                confirm_prompt = wrap['prompt']('Confirm Connect Password:')
                connect_password = self.bot.gui.get_string(prompt,
                                                           confirm_prompt=confirm_prompt,
                                                           blank_allowed=True,
                                                           password=True)
                new_connection['connect_password'] = connect_password

                print(wrap['note']('If you do not have a NickServ password, simply leave '
                                   'this empty'))
                prompt = wrap['prompt']('NickServ Password:')
                confirm_prompt = wrap['prompt']('Confirm NickServ Password:')
                ns_password = self.bot.gui.get_string(prompt,
                                                      confirm_prompt=confirm_prompt,
                                                      blank_allowed=True,
                                                      password=True)
                if ns_password:
                    new_connection['nickserv_password'] = ns_password

                    repeating_prompt = wrap['prompt']('NickServ Wait Period in seconds: [10]')
                    prompt = '\n'.join([
                        "NickServ authentication sometimes takes a number of seconds to "
                        "complete.",
                        "Here, you can type in a number of seconds to wait before joining "
                        "channels to make sure you're properly authenticated with NickServ.",
                        '',
                        "This is commonly used to wait for vhosts to apply, before joining "
                        "channels, as well as waiting for login so ChanServ-protected channels "
                        "don't kick you."
                        '',
                        repeating_prompt,
                    ])
                    vhost_wait = self.bot.gui.get_number(prompt,
                                                         repeating_prompt=repeating_prompt,
                                                         force_int=True,
                                                         default=10)
                    new_connection['vhost_wait'] = vhost_wait

                repeating_prompt = wrap['prompt']('Channels to autojoin:')
                prompt = '\n'.join([
                    wrap['subsection']('Channels to Autojoin'),
                    "In here, you list the channels you want to autojoin when connecting to "
                    "the network!",
                    '',
                    wrap['note']('Separate the channels by spaces, eg:  #a #b #chat #ret'),
                    '',
                    repeating_prompt
                ])
                chanlist = self.bot.gui.get_string(prompt, repeating_prompt=repeating_prompt)

                new_connection['autojoin_channels'] = []
                for chan in chanlist.split():
                    if not chan.startswith('#'):
                        continue
                    if chan.lower() not in new_connection['autojoin_channels']:
                        new_connection['autojoin_channels'].append(chan.lower())

                default_timeout = timedelta_to_string(default_timeout_check_interval)
                repeating_prompt = wrap['prompt']('Timeout Check Interval: [{}]'
                                                  ''.format(default_timeout))
                prompt = '\n'.join([
                    '',
                    wrap['subsection']('Timeout Check Interval').strip(),
                    "This is how long between our checks to see if we have timed out. "
                    "Changing this can help if your connection keeps timing out.",
                    '',
                    wrap['note']('This is a string like:  "5m14s"  "1h3m12s'),
                    '',
                    repeating_prompt,
                ])
                timeout_check = self.bot.gui.get_string(prompt,
                                                        repeating_prompt=repeating_prompt,
                                                        default=default_timeout,
                                                        validate=string_to_timedelta)
                new_connection['timeout_check_interval'] = string_to_timedelta(timeout_check)

                default_timeout = timedelta_to_string(default_timeout_length)
                repeating_prompt = wrap['prompt']('Timeout Length: [{}]'
                                                  ''.format(default_timeout))
                prompt = '\n'.join([
                    '',
                    wrap['subsection']('Timeout Length').strip(),
                    "This is how long without a message from the server we can go before we "
                    "assume we have been timed out and try to reconnect. Higher values here "
                    "can help prevent disconnections on some networks, but will increase the "
                    "time it takes to automatically reconnect after pinging out."
                    '',
                    wrap['note']('This is a string like:  "5m14s"  "1h3m12s"'),
                    '',
                    repeating_prompt,
                ])
                timeout_length = self.bot.gui.get_string(prompt,
                                                         repeating_prompt=repeating_prompt,
                                                         default=default_timeout,
                                                         validate=string_to_timedelta)
                new_connection['timeout_length'] = string_to_timedelta(timeout_length)

                # add new connection to our list
                new_server_dict = self.get('servers', {})
                new_server_dict[server_name] = new_connection
                self.set('servers', new_server_dict)

        print(wrap['success']('IRC Info'))
