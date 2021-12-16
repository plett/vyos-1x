#!/usr/bin/env python3
#
# Copyright (C) 2019 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import sys
import os
import json
import time
from copy import deepcopy

import vyos.defaults
from vyos.config import Config
from vyos import ConfigError
from vyos.util import cmd
from vyos.util import call

from vyos import airbag
airbag.enable()

api_conf_file = '/etc/vyos/http-api.conf'

vyos_conf_scripts_dir=vyos.defaults.directories['conf_mode']

def get_config(config=None):
    http_api = deepcopy(vyos.defaults.api_data)
    x = http_api.get('api_keys')
    if x is None:
        default_key = None
    else:
        default_key = x[0]
    keys_added = False

    if config:
        conf = config
    else:
        conf = Config()

    if not conf.exists('service https api'):
        return None
    else:
        conf.set_level('service https api')

    if conf.exists('strict'):
        http_api['strict'] = True

    if conf.exists('debug'):
        http_api['debug'] = True

    if conf.exists('socket'):
        http_api['socket'] = True

    if conf.exists('port'):
        port = conf.return_value('port')
        http_api['port'] = port

    if conf.exists('cors'):
        http_api['cors'] = {}
        if conf.exists('cors allow-origin'):
            origins = conf.return_values('cors allow-origin')
            http_api['cors']['origins'] = origins[:]

    if conf.exists('keys'):
        for name in conf.list_nodes('keys id'):
            if conf.exists('keys id {0} key'.format(name)):
                key = conf.return_value('keys id {0} key'.format(name))
                new_key = { 'id': name, 'key': key }
                http_api['api_keys'].append(new_key)
                keys_added = True

    if keys_added and default_key:
        if default_key in http_api['api_keys']:
            http_api['api_keys'].remove(default_key)

    return http_api

def verify(http_api):
    return None

def generate(http_api):
    if http_api is None:
        return None

    if not os.path.exists('/etc/vyos'):
        os.mkdir('/etc/vyos')

    with open(api_conf_file, 'w') as f:
        json.dump(http_api, f, indent=2)

    return None

def apply(http_api):
    if http_api is not None:
        call('systemctl restart vyos-http-api.service')
    else:
        call('systemctl stop vyos-http-api.service')

    # Let uvicorn settle before restarting Nginx
    time.sleep(1)

    cmd(f'{vyos_conf_scripts_dir}/https.py', raising=ConfigError)

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        sys.exit(1)
