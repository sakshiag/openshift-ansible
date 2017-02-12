#!/usr/bin/env python
# pylint: disable=missing-docstring
# flake8: noqa: T001
#     ___ ___ _  _ ___ ___    _ _____ ___ ___
#    / __| __| \| | __| _ \  /_\_   _| __|   \
#   | (_ | _|| .` | _||   / / _ \| | | _|| |) |
#    \___|___|_|\_|___|_|_\/_/_\_\_|_|___|___/_ _____
#   |   \ / _ \  | \| |/ _ \_   _| | __|   \_ _|_   _|
#   | |) | (_) | | .` | (_) || |   | _|| |) | |  | |
#   |___/ \___/  |_|\_|\___/ |_|   |___|___/___| |_|
#
# Copyright 2016 Red Hat, Inc. and/or its affiliates
# and other contributors as indicated by the @author tags.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# -*- -*- -*- Begin included fragment: lib/import.py -*- -*- -*-
'''
   OpenShiftCLI class that wraps the oc commands in a subprocess
'''
# pylint: disable=too-many-lines

from __future__ import print_function
import atexit
import json
import os
import re
import shutil
import subprocess
import tempfile
# pylint: disable=import-error
import ruamel.yaml as yaml
from ansible.module_utils.basic import AnsibleModule

# -*- -*- -*- End included fragment: lib/import.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: doc/router -*- -*- -*-

DOCUMENTATION = '''
---
module: oadm_router
short_description: Module to manage openshift router
description:
  - Manage openshift router programmatically.
options:
  state:
    description:
    - Whether to create or delete the router
    - present - create the router
    - absent - remove the router
    required: false
    default: present
    choices:
    - present
    - absent
    aliases: []
  kubeconfig:
    description:
    - The path for the kubeconfig file to use for authentication
    required: false
    default: /etc/origin/master/admin.kubeconfig
    aliases: []
  debug:
    description:
    - Turn on debug output.
    required: false
    default: False
    aliases: []
  name:
    description:
    - The name of the router
    required: false
    default: router
    aliases: []
  namespace:
    description:
    - The namespace where to manage the router.
    required: false
    default: default
    aliases: []
  credentials:
    description:
    - Path to a .kubeconfig file that will contain the credentials the registry should use to contact the master.
    required: false
    default: None
    aliases: []
  images:
    description:
    - The image to base this router on - ${component} will be replaced with --type
    required: 'openshift3/ose-${component}:${version}'
    default: None
    aliases: []
  latest_images:
    description:
    - If true, attempt to use the latest image for the registry instead of the latest release.
    required: false
    default: False
    aliases: []
  labels:
    description:
    - A set of labels to uniquely identify the registry and its components.
    required: false
    default: None
    aliases: []
  ports:
    description:
    - A list of strings in the 'port:port' format
    required: False
    default:
    - 80:80
    - 443:443
    aliases: []
  replicas:
    description:
    - The replication factor of the registry; commonly 2 when high availability is desired.
    required: False
    default: 1
    aliases: []
  selector:
    description:
    - Selector used to filter nodes on deployment. Used to run routers on a specific set of nodes.
    required: False
    default: None
    aliases: []
  service_account:
    description:
    - Name of the service account to use to run the router pod.
    required: False
    default: router
    aliases: []
  router_type:
    description:
    - The router image to use - if you specify --images this flag may be ignored.
    required: false
    default: haproxy-router
    aliases: []
  external_host:
    description:
    - If the underlying router implementation connects with an external host, this is the external host's hostname.
    required: false
    default: None
    aliases: []
  external_host_vserver:
    description:
    - If the underlying router implementation uses virtual servers, this is the name of the virtual server for HTTP connections.
    required: false
    default: None
    aliases: []
  external_host_insecure:
    description:
    - If the underlying router implementation connects with an external host
    - over a secure connection, this causes the router to skip strict certificate verification with the external host.
    required: false
    default: False
    aliases: []
  external_host_partition_path:
    description:
    - If the underlying router implementation uses partitions for control boundaries, this is the path to use for that partition.
    required: false
    default: None
    aliases: []
  external_host_username:
    description:
    - If the underlying router implementation connects with an external host, this is the username for authenticating with the external host.
    required: false
    default: None
    aliases: []
  external_host_password:
    description:
    - If the underlying router implementation connects with an external host, this is the password for authenticating with the external host.
    required: false
    default: None
    aliases: []
  external_host_private_key:
    description:
    - If the underlying router implementation requires an SSH private key, this is the path to the private key file.
    required: false
    default: None
    aliases: []
  expose_metrics:
    description:
    - This is a hint to run an extra container in the pod to expose metrics - the image
    - will either be set depending on the router implementation or provided with --metrics-image.
    required: false
    default: False
    aliases: []
  metrics_image:
    description:
    - If expose_metrics is specified this is the image to use to run a sidecar container
    - in the pod exposing metrics. If not set and --expose-metrics is true the image will
    - depend on router implementation.
    required: false
    default: None
    aliases: []
author:
- "Kenny Woodson <kwoodson@redhat.com>"
extends_documentation_fragment: []
'''

EXAMPLES = '''
- name: create routers
  oadm_router:
    name: router
    service_account: router
    replicas: 2
    namespace: default
    selector: type=infra
    cert_file: /etc/origin/master/named_certificates/router.crt
    key_file: /etc/origin/master/named_certificates/router.key
    cacert_file: /etc/origin/master/named_certificates/router.ca
    edits:
    - key: spec.strategy.rollingParams
      value:
        intervalSeconds: 1
        maxSurge: 50%
        maxUnavailable: 50%
        timeoutSeconds: 600
        updatePeriodSeconds: 1
      action: put
    - key: spec.template.spec.containers[0].resources.limits.memory
      value: 2G
      action: update
    - key: spec.template.spec.containers[0].resources.requests.memory
      value: 1G
      action: update
    - key: spec.template.spec.containers[0].env
      value:
        name: EXTENDED_VALIDATION
        value: 'false'
      action: update
  register: router_out
  run_once: True
'''

# -*- -*- -*- End included fragment: doc/router -*- -*- -*-

# -*- -*- -*- Begin included fragment: ../../lib_utils/src/class/yedit.py -*- -*- -*-
# noqa: E301,E302


class YeditException(Exception):
    ''' Exception class for Yedit '''
    pass


# pylint: disable=too-many-public-methods
class Yedit(object):
    ''' Class to modify yaml files '''
    re_valid_key = r"(((\[-?\d+\])|([0-9a-zA-Z%s/_-]+)).?)+$"
    re_key = r"(?:\[(-?\d+)\])|([0-9a-zA-Z%s/_-]+)"
    com_sep = set(['.', '#', '|', ':'])

    # pylint: disable=too-many-arguments
    def __init__(self,
                 filename=None,
                 content=None,
                 content_type='yaml',
                 separator='.',
                 backup=False):
        self.content = content
        self._separator = separator
        self.filename = filename
        self.__yaml_dict = content
        self.content_type = content_type
        self.backup = backup
        self.load(content_type=self.content_type)
        if self.__yaml_dict is None:
            self.__yaml_dict = {}

    @property
    def separator(self):
        ''' getter method for yaml_dict '''
        return self._separator

    @separator.setter
    def separator(self):
        ''' getter method for yaml_dict '''
        return self._separator

    @property
    def yaml_dict(self):
        ''' getter method for yaml_dict '''
        return self.__yaml_dict

    @yaml_dict.setter
    def yaml_dict(self, value):
        ''' setter method for yaml_dict '''
        self.__yaml_dict = value

    @staticmethod
    def parse_key(key, sep='.'):
        '''parse the key allowing the appropriate separator'''
        common_separators = list(Yedit.com_sep - set([sep]))
        return re.findall(Yedit.re_key % ''.join(common_separators), key)

    @staticmethod
    def valid_key(key, sep='.'):
        '''validate the incoming key'''
        common_separators = list(Yedit.com_sep - set([sep]))
        if not re.match(Yedit.re_valid_key % ''.join(common_separators), key):
            return False

        return True

    @staticmethod
    def remove_entry(data, key, sep='.'):
        ''' remove data at location key '''
        if key == '' and isinstance(data, dict):
            data.clear()
            return True
        elif key == '' and isinstance(data, list):
            del data[:]
            return True

        if not (key and Yedit.valid_key(key, sep)) and \
           isinstance(data, (list, dict)):
            return None

        key_indexes = Yedit.parse_key(key, sep)
        for arr_ind, dict_key in key_indexes[:-1]:
            if dict_key and isinstance(data, dict):
                data = data.get(dict_key, None)
            elif (arr_ind and isinstance(data, list) and
                  int(arr_ind) <= len(data) - 1):
                data = data[int(arr_ind)]
            else:
                return None

        # process last index for remove
        # expected list entry
        if key_indexes[-1][0]:
            if isinstance(data, list) and int(key_indexes[-1][0]) <= len(data) - 1:  # noqa: E501
                del data[int(key_indexes[-1][0])]
                return True

        # expected dict entry
        elif key_indexes[-1][1]:
            if isinstance(data, dict):
                del data[key_indexes[-1][1]]
                return True

    @staticmethod
    def add_entry(data, key, item=None, sep='.'):
        ''' Get an item from a dictionary with key notation a.b.c
            d = {'a': {'b': 'c'}}}
            key = a#b
            return c
        '''
        if key == '':
            pass
        elif (not (key and Yedit.valid_key(key, sep)) and
              isinstance(data, (list, dict))):
            return None

        key_indexes = Yedit.parse_key(key, sep)
        for arr_ind, dict_key in key_indexes[:-1]:
            if dict_key:
                if isinstance(data, dict) and dict_key in data and data[dict_key]:  # noqa: E501
                    data = data[dict_key]
                    continue

                elif data and not isinstance(data, dict):
                    return None

                data[dict_key] = {}
                data = data[dict_key]

            elif (arr_ind and isinstance(data, list) and
                  int(arr_ind) <= len(data) - 1):
                data = data[int(arr_ind)]
            else:
                return None

        if key == '':
            data = item

        # process last index for add
        # expected list entry
        elif key_indexes[-1][0] and isinstance(data, list) and int(key_indexes[-1][0]) <= len(data) - 1:  # noqa: E501
            data[int(key_indexes[-1][0])] = item

        # expected dict entry
        elif key_indexes[-1][1] and isinstance(data, dict):
            data[key_indexes[-1][1]] = item

        return data

    @staticmethod
    def get_entry(data, key, sep='.'):
        ''' Get an item from a dictionary with key notation a.b.c
            d = {'a': {'b': 'c'}}}
            key = a.b
            return c
        '''
        if key == '':
            pass
        elif (not (key and Yedit.valid_key(key, sep)) and
              isinstance(data, (list, dict))):
            return None

        key_indexes = Yedit.parse_key(key, sep)
        for arr_ind, dict_key in key_indexes:
            if dict_key and isinstance(data, dict):
                data = data.get(dict_key, None)
            elif (arr_ind and isinstance(data, list) and
                  int(arr_ind) <= len(data) - 1):
                data = data[int(arr_ind)]
            else:
                return None

        return data

    @staticmethod
    def _write(filename, contents):
        ''' Actually write the file contents to disk. This helps with mocking. '''

        tmp_filename = filename + '.yedit'

        with open(tmp_filename, 'w') as yfd:
            yfd.write(contents)

        os.rename(tmp_filename, filename)

    def write(self):
        ''' write to file '''
        if not self.filename:
            raise YeditException('Please specify a filename.')

        if self.backup and self.file_exists():
            shutil.copy(self.filename, self.filename + '.orig')

        # pylint: disable=no-member
        if hasattr(self.yaml_dict, 'fa'):
            self.yaml_dict.fa.set_block_style()

        Yedit._write(self.filename, yaml.dump(self.yaml_dict, Dumper=yaml.RoundTripDumper))

        return (True, self.yaml_dict)

    def read(self):
        ''' read from file '''
        # check if it exists
        if self.filename is None or not self.file_exists():
            return None

        contents = None
        with open(self.filename) as yfd:
            contents = yfd.read()

        return contents

    def file_exists(self):
        ''' return whether file exists '''
        if os.path.exists(self.filename):
            return True

        return False

    def load(self, content_type='yaml'):
        ''' return yaml file '''
        contents = self.read()

        if not contents and not self.content:
            return None

        if self.content:
            if isinstance(self.content, dict):
                self.yaml_dict = self.content
                return self.yaml_dict
            elif isinstance(self.content, str):
                contents = self.content

        # check if it is yaml
        try:
            if content_type == 'yaml' and contents:
                self.yaml_dict = yaml.load(contents, yaml.RoundTripLoader)
                # pylint: disable=no-member
                if hasattr(self.yaml_dict, 'fa'):
                    self.yaml_dict.fa.set_block_style()
            elif content_type == 'json' and contents:
                self.yaml_dict = json.loads(contents)
        except yaml.YAMLError as err:
            # Error loading yaml or json
            raise YeditException('Problem with loading yaml file. %s' % err)

        return self.yaml_dict

    def get(self, key):
        ''' get a specified key'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, key, self.separator)
        except KeyError:
            entry = None

        return entry

    def pop(self, path, key_or_item):
        ''' remove a key, value pair from a dict or an item for a list'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        except KeyError:
            entry = None

        if entry is None:
            return (False, self.yaml_dict)

        if isinstance(entry, dict):
            # pylint: disable=no-member,maybe-no-member
            if key_or_item in entry:
                entry.pop(key_or_item)
                return (True, self.yaml_dict)
            return (False, self.yaml_dict)

        elif isinstance(entry, list):
            # pylint: disable=no-member,maybe-no-member
            ind = None
            try:
                ind = entry.index(key_or_item)
            except ValueError:
                return (False, self.yaml_dict)

            entry.pop(ind)
            return (True, self.yaml_dict)

        return (False, self.yaml_dict)

    def delete(self, path):
        ''' remove path from a dict'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        except KeyError:
            entry = None

        if entry is None:
            return (False, self.yaml_dict)

        result = Yedit.remove_entry(self.yaml_dict, path, self.separator)
        if not result:
            return (False, self.yaml_dict)

        return (True, self.yaml_dict)

    def exists(self, path, value):
        ''' check if value exists at path'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        except KeyError:
            entry = None

        if isinstance(entry, list):
            if value in entry:
                return True
            return False

        elif isinstance(entry, dict):
            if isinstance(value, dict):
                rval = False
                for key, val in value.items():
                    if entry[key] != val:
                        rval = False
                        break
                else:
                    rval = True
                return rval

            return value in entry

        return entry == value

    def append(self, path, value):
        '''append value to a list'''
        try:
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        except KeyError:
            entry = None

        if entry is None:
            self.put(path, [])
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        if not isinstance(entry, list):
            return (False, self.yaml_dict)

        # pylint: disable=no-member,maybe-no-member
        entry.append(value)
        return (True, self.yaml_dict)

    # pylint: disable=too-many-arguments
    def update(self, path, value, index=None, curr_value=None):
        ''' put path, value into a dict '''
        try:
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        except KeyError:
            entry = None

        if isinstance(entry, dict):
            # pylint: disable=no-member,maybe-no-member
            if not isinstance(value, dict):
                raise YeditException('Cannot replace key, value entry in ' +
                                     'dict with non-dict type. value=[%s] [%s]' % (value, type(value)))  # noqa: E501

            entry.update(value)
            return (True, self.yaml_dict)

        elif isinstance(entry, list):
            # pylint: disable=no-member,maybe-no-member
            ind = None
            if curr_value:
                try:
                    ind = entry.index(curr_value)
                except ValueError:
                    return (False, self.yaml_dict)

            elif index is not None:
                ind = index

            if ind is not None and entry[ind] != value:
                entry[ind] = value
                return (True, self.yaml_dict)

            # see if it exists in the list
            try:
                ind = entry.index(value)
            except ValueError:
                # doesn't exist, append it
                entry.append(value)
                return (True, self.yaml_dict)

            # already exists, return
            if ind is not None:
                return (False, self.yaml_dict)
        return (False, self.yaml_dict)

    def put(self, path, value):
        ''' put path, value into a dict '''
        try:
            entry = Yedit.get_entry(self.yaml_dict, path, self.separator)
        except KeyError:
            entry = None

        if entry == value:
            return (False, self.yaml_dict)

        # deepcopy didn't work
        tmp_copy = yaml.load(yaml.round_trip_dump(self.yaml_dict,
                                                  default_flow_style=False),
                             yaml.RoundTripLoader)
        # pylint: disable=no-member
        if hasattr(self.yaml_dict, 'fa'):
            tmp_copy.fa.set_block_style()
        result = Yedit.add_entry(tmp_copy, path, value, self.separator)
        if not result:
            return (False, self.yaml_dict)

        self.yaml_dict = tmp_copy

        return (True, self.yaml_dict)

    def create(self, path, value):
        ''' create a yaml file '''
        if not self.file_exists():
            # deepcopy didn't work
            tmp_copy = yaml.load(yaml.round_trip_dump(self.yaml_dict, default_flow_style=False),  # noqa: E501
                                 yaml.RoundTripLoader)
            # pylint: disable=no-member
            if hasattr(self.yaml_dict, 'fa'):
                tmp_copy.fa.set_block_style()
            result = Yedit.add_entry(tmp_copy, path, value, self.separator)
            if result:
                self.yaml_dict = tmp_copy
                return (True, self.yaml_dict)

        return (False, self.yaml_dict)

    @staticmethod
    def get_curr_value(invalue, val_type):
        '''return the current value'''
        if invalue is None:
            return None

        curr_value = invalue
        if val_type == 'yaml':
            curr_value = yaml.load(invalue)
        elif val_type == 'json':
            curr_value = json.loads(invalue)

        return curr_value

    @staticmethod
    def parse_value(inc_value, vtype=''):
        '''determine value type passed'''
        true_bools = ['y', 'Y', 'yes', 'Yes', 'YES', 'true', 'True', 'TRUE',
                      'on', 'On', 'ON', ]
        false_bools = ['n', 'N', 'no', 'No', 'NO', 'false', 'False', 'FALSE',
                       'off', 'Off', 'OFF']

        # It came in as a string but you didn't specify value_type as string
        # we will convert to bool if it matches any of the above cases
        if isinstance(inc_value, str) and 'bool' in vtype:
            if inc_value not in true_bools and inc_value not in false_bools:
                raise YeditException('Not a boolean type. str=[%s] vtype=[%s]'
                                     % (inc_value, vtype))
        elif isinstance(inc_value, bool) and 'str' in vtype:
            inc_value = str(inc_value)

        # If vtype is not str then go ahead and attempt to yaml load it.
        if isinstance(inc_value, str) and 'str' not in vtype:
            try:
                inc_value = yaml.load(inc_value)
            except Exception:
                raise YeditException('Could not determine type of incoming ' +
                                     'value. value=[%s] vtype=[%s]'
                                     % (type(inc_value), vtype))

        return inc_value

    # pylint: disable=too-many-return-statements,too-many-branches
    @staticmethod
    def run_ansible(module):
        '''perform the idempotent crud operations'''
        yamlfile = Yedit(filename=module.params['src'],
                         backup=module.params['backup'],
                         separator=module.params['separator'])

        if module.params['src']:
            rval = yamlfile.load()

            if yamlfile.yaml_dict is None and \
               module.params['state'] != 'present':
                return {'failed': True,
                        'msg': 'Error opening file [%s].  Verify that the ' +
                               'file exists, that it is has correct' +
                               ' permissions, and is valid yaml.'}

        if module.params['state'] == 'list':
            if module.params['content']:
                content = Yedit.parse_value(module.params['content'],
                                            module.params['content_type'])
                yamlfile.yaml_dict = content

            if module.params['key']:
                rval = yamlfile.get(module.params['key']) or {}

            return {'changed': False, 'result': rval, 'state': "list"}

        elif module.params['state'] == 'absent':
            if module.params['content']:
                content = Yedit.parse_value(module.params['content'],
                                            module.params['content_type'])
                yamlfile.yaml_dict = content

            if module.params['update']:
                rval = yamlfile.pop(module.params['key'],
                                    module.params['value'])
            else:
                rval = yamlfile.delete(module.params['key'])

            if rval[0] and module.params['src']:
                yamlfile.write()

            return {'changed': rval[0], 'result': rval[1], 'state': "absent"}

        elif module.params['state'] == 'present':
            # check if content is different than what is in the file
            if module.params['content']:
                content = Yedit.parse_value(module.params['content'],
                                            module.params['content_type'])

                # We had no edits to make and the contents are the same
                if yamlfile.yaml_dict == content and \
                   module.params['value'] is None:
                    return {'changed': False,
                            'result': yamlfile.yaml_dict,
                            'state': "present"}

                yamlfile.yaml_dict = content

            # we were passed a value; parse it
            if module.params['value']:
                value = Yedit.parse_value(module.params['value'],
                                          module.params['value_type'])
                key = module.params['key']
                if module.params['update']:
                    # pylint: disable=line-too-long
                    curr_value = Yedit.get_curr_value(Yedit.parse_value(module.params['curr_value']),  # noqa: E501
                                                      module.params['curr_value_format'])  # noqa: E501

                    rval = yamlfile.update(key, value, module.params['index'], curr_value)  # noqa: E501

                elif module.params['append']:
                    rval = yamlfile.append(key, value)
                else:
                    rval = yamlfile.put(key, value)

                if rval[0] and module.params['src']:
                    yamlfile.write()

                return {'changed': rval[0],
                        'result': rval[1], 'state': "present"}

            # no edits to make
            if module.params['src']:
                # pylint: disable=redefined-variable-type
                rval = yamlfile.write()
                return {'changed': rval[0],
                        'result': rval[1],
                        'state': "present"}

        return {'failed': True, 'msg': 'Unkown state passed'}

# -*- -*- -*- End included fragment: ../../lib_utils/src/class/yedit.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: lib/base.py -*- -*- -*-
# pylint: disable=too-many-lines
# noqa: E301,E302,E303,T001


class OpenShiftCLIError(Exception):
    '''Exception class for openshiftcli'''
    pass


# pylint: disable=too-few-public-methods
class OpenShiftCLI(object):
    ''' Class to wrap the command line tools '''
    def __init__(self,
                 namespace,
                 kubeconfig='/etc/origin/master/admin.kubeconfig',
                 verbose=False,
                 all_namespaces=False):
        ''' Constructor for OpenshiftCLI '''
        self.namespace = namespace
        self.verbose = verbose
        self.kubeconfig = Utils.create_tmpfile_copy(kubeconfig)
        self.all_namespaces = all_namespaces

    # Pylint allows only 5 arguments to be passed.
    # pylint: disable=too-many-arguments
    def _replace_content(self, resource, rname, content, force=False, sep='.'):
        ''' replace the current object with the content '''
        res = self._get(resource, rname)
        if not res['results']:
            return res

        fname = Utils.create_tmpfile(rname + '-')

        yed = Yedit(fname, res['results'][0], separator=sep)
        changes = []
        for key, value in content.items():
            changes.append(yed.put(key, value))

        if any([change[0] for change in changes]):
            yed.write()

            atexit.register(Utils.cleanup, [fname])

            return self._replace(fname, force)

        return {'returncode': 0, 'updated': False}

    def _replace(self, fname, force=False):
        '''replace the current object with oc replace'''
        cmd = ['replace', '-f', fname]
        if force:
            cmd.append('--force')
        return self.openshift_cmd(cmd)

    def _create_from_content(self, rname, content):
        '''create a temporary file and then call oc create on it'''
        fname = Utils.create_tmpfile(rname + '-')
        yed = Yedit(fname, content=content)
        yed.write()

        atexit.register(Utils.cleanup, [fname])

        return self._create(fname)

    def _create(self, fname):
        '''call oc create on a filename'''
        return self.openshift_cmd(['create', '-f', fname])

    def _delete(self, resource, rname, selector=None):
        '''call oc delete on a resource'''
        cmd = ['delete', resource, rname]
        if selector:
            cmd.append('--selector=%s' % selector)

        return self.openshift_cmd(cmd)

    def _process(self, template_name, create=False, params=None, template_data=None):  # noqa: E501
        '''process a template

           template_name: the name of the template to process
           create: whether to send to oc create after processing
           params: the parameters for the template
           template_data: the incoming template's data; instead of a file
        '''
        cmd = ['process']
        if template_data:
            cmd.extend(['-f', '-'])
        else:
            cmd.append(template_name)
        if params:
            param_str = ["%s=%s" % (key, value) for key, value in params.items()]
            cmd.append('-v')
            cmd.extend(param_str)

        results = self.openshift_cmd(cmd, output=True, input_data=template_data)

        if results['returncode'] != 0 or not create:
            return results

        fname = Utils.create_tmpfile(template_name + '-')
        yed = Yedit(fname, results['results'])
        yed.write()

        atexit.register(Utils.cleanup, [fname])

        return self.openshift_cmd(['create', '-f', fname])

    def _get(self, resource, rname=None, selector=None):
        '''return a resource by name '''
        cmd = ['get', resource]
        if selector:
            cmd.append('--selector=%s' % selector)
        elif rname:
            cmd.append(rname)

        cmd.extend(['-o', 'json'])

        rval = self.openshift_cmd(cmd, output=True)

        # Ensure results are retuned in an array
        if 'items' in rval:
            rval['results'] = rval['items']
        elif not isinstance(rval['results'], list):
            rval['results'] = [rval['results']]

        return rval

    def _schedulable(self, node=None, selector=None, schedulable=True):
        ''' perform oadm manage-node scheduable '''
        cmd = ['manage-node']
        if node:
            cmd.extend(node)
        else:
            cmd.append('--selector=%s' % selector)

        cmd.append('--schedulable=%s' % schedulable)

        return self.openshift_cmd(cmd, oadm=True, output=True, output_type='raw')  # noqa: E501

    def _list_pods(self, node=None, selector=None, pod_selector=None):
        ''' perform oadm list pods

            node: the node in which to list pods
            selector: the label selector filter if provided
            pod_selector: the pod selector filter if provided
        '''
        cmd = ['manage-node']
        if node:
            cmd.extend(node)
        else:
            cmd.append('--selector=%s' % selector)

        if pod_selector:
            cmd.append('--pod-selector=%s' % pod_selector)

        cmd.extend(['--list-pods', '-o', 'json'])

        return self.openshift_cmd(cmd, oadm=True, output=True, output_type='raw')

    # pylint: disable=too-many-arguments
    def _evacuate(self, node=None, selector=None, pod_selector=None, dry_run=False, grace_period=None, force=False):
        ''' perform oadm manage-node evacuate '''
        cmd = ['manage-node']
        if node:
            cmd.extend(node)
        else:
            cmd.append('--selector=%s' % selector)

        if dry_run:
            cmd.append('--dry-run')

        if pod_selector:
            cmd.append('--pod-selector=%s' % pod_selector)

        if grace_period:
            cmd.append('--grace-period=%s' % int(grace_period))

        if force:
            cmd.append('--force')

        cmd.append('--evacuate')

        return self.openshift_cmd(cmd, oadm=True, output=True, output_type='raw')

    def _version(self):
        ''' return the openshift version'''
        return self.openshift_cmd(['version'], output=True, output_type='raw')

    def _import_image(self, url=None, name=None, tag=None):
        ''' perform image import '''
        cmd = ['import-image']

        image = '{0}'.format(name)
        if tag:
            image += ':{0}'.format(tag)

        cmd.append(image)

        if url:
            cmd.append('--from={0}/{1}'.format(url, image))

        cmd.append('-n{0}'.format(self.namespace))

        cmd.append('--confirm')
        return self.openshift_cmd(cmd)

    def _run(self, cmds, input_data):
        ''' Actually executes the command. This makes mocking easier. '''
        curr_env = os.environ.copy()
        curr_env.update({'KUBECONFIG': self.kubeconfig})
        proc = subprocess.Popen(cmds,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=curr_env)

        stdout, stderr = proc.communicate(input_data)

        return proc.returncode, stdout, stderr

    # pylint: disable=too-many-arguments,too-many-branches
    def openshift_cmd(self, cmd, oadm=False, output=False, output_type='json', input_data=None):
        '''Base command for oc '''
        cmds = []
        if oadm:
            cmds = ['oadm']
        else:
            cmds = ['oc']

        if self.all_namespaces:
            cmds.extend(['--all-namespaces'])
        elif self.namespace is not None and self.namespace.lower() not in ['none', 'emtpy']:  # E501
            cmds.extend(['-n', self.namespace])

        cmds.extend(cmd)

        rval = {}
        results = ''
        err = None

        if self.verbose:
            print(' '.join(cmds))

        returncode, stdout, stderr = self._run(cmds, input_data)

        rval = {"returncode": returncode,
                "results": results,
                "cmd": ' '.join(cmds)}

        if returncode == 0:
            if output:
                if output_type == 'json':
                    try:
                        rval['results'] = json.loads(stdout)
                    except ValueError as err:
                        if "No JSON object could be decoded" in err.args:
                            err = err.args
                elif output_type == 'raw':
                    rval['results'] = stdout

            if self.verbose:
                print("STDOUT: {0}".format(stdout))
                print("STDERR: {0}".format(stderr))

            if err:
                rval.update({"err": err,
                             "stderr": stderr,
                             "stdout": stdout,
                             "cmd": cmds})

        else:
            rval.update({"stderr": stderr,
                         "stdout": stdout,
                         "results": {}})

        return rval


class Utils(object):
    ''' utilities for openshiftcli modules '''

    @staticmethod
    def _write(filename, contents):
        ''' Actually write the file contents to disk. This helps with mocking. '''

        with open(filename, 'w') as sfd:
            sfd.write(contents)

    @staticmethod
    def create_tmp_file_from_contents(rname, data, ftype='yaml'):
        ''' create a file in tmp with name and contents'''

        tmp = Utils.create_tmpfile(prefix=rname)

        if ftype == 'yaml':
            Utils._write(tmp, yaml.dump(data, Dumper=yaml.RoundTripDumper))
        elif ftype == 'json':
            Utils._write(tmp, json.dumps(data))
        else:
            Utils._write(tmp, data)

        # Register cleanup when module is done
        atexit.register(Utils.cleanup, [tmp])
        return tmp

    @staticmethod
    def create_tmpfile_copy(inc_file):
        '''create a temporary copy of a file'''
        tmpfile = Utils.create_tmpfile('lib_openshift-')
        Utils._write(tmpfile, open(inc_file).read())

        # Cleanup the tmpfile
        atexit.register(Utils.cleanup, [tmpfile])

        return tmpfile

    @staticmethod
    def create_tmpfile(prefix='tmp'):
        ''' Generates and returns a temporary file name '''

        with tempfile.NamedTemporaryFile(prefix=prefix, delete=False) as tmp:
            return tmp.name

    @staticmethod
    def create_tmp_files_from_contents(content, content_type=None):
        '''Turn an array of dict: filename, content into a files array'''
        if not isinstance(content, list):
            content = [content]
        files = []
        for item in content:
            path = Utils.create_tmp_file_from_contents(item['path'] + '-',
                                                       item['data'],
                                                       ftype=content_type)
            files.append({'name': os.path.basename(item['path']),
                          'path': path})
        return files

    @staticmethod
    def cleanup(files):
        '''Clean up on exit '''
        for sfile in files:
            if os.path.exists(sfile):
                if os.path.isdir(sfile):
                    shutil.rmtree(sfile)
                elif os.path.isfile(sfile):
                    os.remove(sfile)

    @staticmethod
    def exists(results, _name):
        ''' Check to see if the results include the name '''
        if not results:
            return False

        if Utils.find_result(results, _name):
            return True

        return False

    @staticmethod
    def find_result(results, _name):
        ''' Find the specified result by name'''
        rval = None
        for result in results:
            if 'metadata' in result and result['metadata']['name'] == _name:
                rval = result
                break

        return rval

    @staticmethod
    def get_resource_file(sfile, sfile_type='yaml'):
        ''' return the service file '''
        contents = None
        with open(sfile) as sfd:
            contents = sfd.read()

        if sfile_type == 'yaml':
            contents = yaml.load(contents, yaml.RoundTripLoader)
        elif sfile_type == 'json':
            contents = json.loads(contents)

        return contents

    @staticmethod
    def filter_versions(stdout):
        ''' filter the oc version output '''

        version_dict = {}
        version_search = ['oc', 'openshift', 'kubernetes']

        for line in stdout.strip().split('\n'):
            for term in version_search:
                if not line:
                    continue
                if line.startswith(term):
                    version_dict[term] = line.split()[-1]

        # horrible hack to get openshift version in Openshift 3.2
        #  By default "oc version in 3.2 does not return an "openshift" version
        if "openshift" not in version_dict:
            version_dict["openshift"] = version_dict["oc"]

        return version_dict

    @staticmethod
    def add_custom_versions(versions):
        ''' create custom versions strings '''

        versions_dict = {}

        for tech, version in versions.items():
            # clean up "-" from version
            if "-" in version:
                version = version.split("-")[0]

            if version.startswith('v'):
                versions_dict[tech + '_numeric'] = version[1:].split('+')[0]
                # "v3.3.0.33" is what we have, we want "3.3"
                versions_dict[tech + '_short'] = version[1:4]

        return versions_dict

    @staticmethod
    def openshift_installed():
        ''' check if openshift is installed '''
        import yum

        yum_base = yum.YumBase()
        if yum_base.rpmdb.searchNevra(name='atomic-openshift'):
            return True

        return False

    # Disabling too-many-branches.  This is a yaml dictionary comparison function
    # pylint: disable=too-many-branches,too-many-return-statements,too-many-statements
    @staticmethod
    def check_def_equal(user_def, result_def, skip_keys=None, debug=False):
        ''' Given a user defined definition, compare it with the results given back by our query.  '''

        # Currently these values are autogenerated and we do not need to check them
        skip = ['metadata', 'status']
        if skip_keys:
            skip.extend(skip_keys)

        for key, value in result_def.items():
            if key in skip:
                continue

            # Both are lists
            if isinstance(value, list):
                if key not in user_def:
                    if debug:
                        print('User data does not have key [%s]' % key)
                        print('User data: %s' % user_def)
                    return False

                if not isinstance(user_def[key], list):
                    if debug:
                        print('user_def[key] is not a list key=[%s] user_def[key]=%s' % (key, user_def[key]))
                    return False

                if len(user_def[key]) != len(value):
                    if debug:
                        print("List lengths are not equal.")
                        print("key=[%s]: user_def[%s] != value[%s]" % (key, len(user_def[key]), len(value)))
                        print("user_def: %s" % user_def[key])
                        print("value: %s" % value)
                    return False

                for values in zip(user_def[key], value):
                    if isinstance(values[0], dict) and isinstance(values[1], dict):
                        if debug:
                            print('sending list - list')
                            print(type(values[0]))
                            print(type(values[1]))
                        result = Utils.check_def_equal(values[0], values[1], skip_keys=skip_keys, debug=debug)
                        if not result:
                            print('list compare returned false')
                            return False

                    elif value != user_def[key]:
                        if debug:
                            print('value should be identical')
                            print(value)
                            print(user_def[key])
                        return False

            # recurse on a dictionary
            elif isinstance(value, dict):
                if key not in user_def:
                    if debug:
                        print("user_def does not have key [%s]" % key)
                    return False
                if not isinstance(user_def[key], dict):
                    if debug:
                        print("dict returned false: not instance of dict")
                    return False

                # before passing ensure keys match
                api_values = set(value.keys()) - set(skip)
                user_values = set(user_def[key].keys()) - set(skip)
                if api_values != user_values:
                    if debug:
                        print("keys are not equal in dict")
                        print(api_values)
                        print(user_values)
                    return False

                result = Utils.check_def_equal(user_def[key], value, skip_keys=skip_keys, debug=debug)
                if not result:
                    if debug:
                        print("dict returned false")
                        print(result)
                    return False

            # Verify each key, value pair is the same
            else:
                if key not in user_def or value != user_def[key]:
                    if debug:
                        print("value not equal; user_def does not have key")
                        print(key)
                        print(value)
                        if key in user_def:
                            print(user_def[key])
                    return False

        if debug:
            print('returning true')
        return True


class OpenShiftCLIConfig(object):
    '''Generic Config'''
    def __init__(self, rname, namespace, kubeconfig, options):
        self.kubeconfig = kubeconfig
        self.name = rname
        self.namespace = namespace
        self._options = options

    @property
    def config_options(self):
        ''' return config options '''
        return self._options

    def to_option_list(self):
        '''return all options as a string'''
        return self.stringify()

    def stringify(self):
        ''' return the options hash as cli params in a string '''
        rval = []
        for key, data in self.config_options.items():
            if data['include'] \
               and (data['value'] or isinstance(data['value'], int)):
                rval.append('--%s=%s' % (key.replace('_', '-'), data['value']))

        return rval


# -*- -*- -*- End included fragment: lib/base.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: lib/service.py -*- -*- -*-


# pylint: disable=too-many-instance-attributes
class ServiceConfig(object):
    ''' Handle service options '''
    # pylint: disable=too-many-arguments
    def __init__(self,
                 sname,
                 namespace,
                 ports,
                 selector=None,
                 labels=None,
                 cluster_ip=None,
                 portal_ip=None,
                 session_affinity=None,
                 service_type=None):
        ''' constructor for handling service options '''
        self.name = sname
        self.namespace = namespace
        self.ports = ports
        self.selector = selector
        self.labels = labels
        self.cluster_ip = cluster_ip
        self.portal_ip = portal_ip
        self.session_affinity = session_affinity
        self.service_type = service_type
        self.data = {}

        self.create_dict()

    def create_dict(self):
        ''' instantiates a service dict '''
        self.data['apiVersion'] = 'v1'
        self.data['kind'] = 'Service'
        self.data['metadata'] = {}
        self.data['metadata']['name'] = self.name
        self.data['metadata']['namespace'] = self.namespace
        if self.labels:
            for lab, lab_value  in self.labels.items():
                self.data['metadata'][lab] = lab_value
        self.data['spec'] = {}

        if self.ports:
            self.data['spec']['ports'] = self.ports
        else:
            self.data['spec']['ports'] = []

        if self.selector:
            self.data['spec']['selector'] = self.selector

        self.data['spec']['sessionAffinity'] = self.session_affinity or 'None'

        if self.cluster_ip:
            self.data['spec']['clusterIP'] = self.cluster_ip

        if self.portal_ip:
            self.data['spec']['portalIP'] = self.portal_ip

        if self.service_type:
            self.data['spec']['type'] = self.service_type

# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Service(Yedit):
    ''' Class to model the oc service object '''
    port_path = "spec.ports"
    portal_ip = "spec.portalIP"
    cluster_ip = "spec.clusterIP"
    kind = 'Service'

    def __init__(self, content):
        '''Service constructor'''
        super(Service, self).__init__(content=content)

    def get_ports(self):
        ''' get a list of ports '''
        return self.get(Service.port_path) or []

    def add_ports(self, inc_ports):
        ''' add a port object to the ports list '''
        if not isinstance(inc_ports, list):
            inc_ports = [inc_ports]

        ports = self.get_ports()
        if not ports:
            self.put(Service.port_path, inc_ports)
        else:
            ports.extend(inc_ports)

        return True

    def find_ports(self, inc_port):
        ''' find a specific port '''
        for port in self.get_ports():
            if port['port'] == inc_port['port']:
                return port

        return None

    def delete_ports(self, inc_ports):
        ''' remove a port from a service '''
        if not isinstance(inc_ports, list):
            inc_ports = [inc_ports]

        ports = self.get(Service.port_path) or []

        if not ports:
            return True

        removed = False
        for inc_port in inc_ports:
            port = self.find_ports(inc_port)
            if port:
                ports.remove(port)
                removed = True

        return removed

    def add_cluster_ip(self, sip):
        '''add cluster ip'''
        self.put(Service.cluster_ip, sip)

    def add_portal_ip(self, pip):
        '''add cluster ip'''
        self.put(Service.portal_ip, pip)

# -*- -*- -*- End included fragment: lib/service.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: lib/deploymentconfig.py -*- -*- -*-


# pylint: disable=too-many-public-methods
class DeploymentConfig(Yedit):
    ''' Class to wrap the oc command line tools '''
    default_deployment_config = '''
apiVersion: v1
kind: DeploymentConfig
metadata:
  name: default_dc
  namespace: default
spec:
  replicas: 0
  selector:
    default_dc: default_dc
  strategy:
    resources: {}
    rollingParams:
      intervalSeconds: 1
      maxSurge: 0
      maxUnavailable: 25%
      timeoutSeconds: 600
      updatePercent: -25
      updatePeriodSeconds: 1
    type: Rolling
  template:
    metadata:
    spec:
      containers:
      - env:
        - name: default
          value: default
        image: default
        imagePullPolicy: IfNotPresent
        name: default_dc
        ports:
        - containerPort: 8000
          hostPort: 8000
          protocol: TCP
          name: default_port
        resources: {}
        terminationMessagePath: /dev/termination-log
      dnsPolicy: ClusterFirst
      hostNetwork: true
      nodeSelector:
        type: compute
      restartPolicy: Always
      securityContext: {}
      serviceAccount: default
      serviceAccountName: default
      terminationGracePeriodSeconds: 30
  triggers:
  - type: ConfigChange
'''

    replicas_path = "spec.replicas"
    env_path = "spec.template.spec.containers[0].env"
    volumes_path = "spec.template.spec.volumes"
    container_path = "spec.template.spec.containers"
    volume_mounts_path = "spec.template.spec.containers[0].volumeMounts"

    def __init__(self, content=None):
        ''' Constructor for deploymentconfig '''
        if not content:
            content = DeploymentConfig.default_deployment_config

        super(DeploymentConfig, self).__init__(content=content)

    # pylint: disable=no-member
    def add_env_value(self, key, value):
        ''' add key, value pair to env array '''
        rval = False
        env = self.get_env_vars()
        if env:
            env.append({'name': key, 'value': value})
            rval = True
        else:
            result = self.put(DeploymentConfig.env_path, {'name': key, 'value': value})
            rval = result[0]

        return rval

    def exists_env_value(self, key, value):
        ''' return whether a key, value  pair exists '''
        results = self.get_env_vars()
        if not results:
            return False

        for result in results:
            if result['name'] == key and result['value'] == value:
                return True

        return False

    def exists_env_key(self, key):
        ''' return whether a key, value  pair exists '''
        results = self.get_env_vars()
        if not results:
            return False

        for result in results:
            if result['name'] == key:
                return True

        return False

    def get_env_vars(self):
        '''return a environment variables '''
        return self.get(DeploymentConfig.env_path) or []

    def delete_env_var(self, keys):
        '''delete a list of keys '''
        if not isinstance(keys, list):
            keys = [keys]

        env_vars_array = self.get_env_vars()
        modified = False
        idx = None
        for key in keys:
            for env_idx, env_var in enumerate(env_vars_array):
                if env_var['name'] == key:
                    idx = env_idx
                    break

            if idx:
                modified = True
                del env_vars_array[idx]

        if modified:
            return True

        return False

    def update_env_var(self, key, value):
        '''place an env in the env var list'''

        env_vars_array = self.get_env_vars()
        idx = None
        for env_idx, env_var in enumerate(env_vars_array):
            if env_var['name'] == key:
                idx = env_idx
                break

        if idx:
            env_vars_array[idx]['value'] = value
        else:
            self.add_env_value(key, value)

        return True

    def exists_volume_mount(self, volume_mount):
        ''' return whether a volume mount exists '''
        exist_volume_mounts = self.get_volume_mounts()

        if not exist_volume_mounts:
            return False

        volume_mount_found = False
        for exist_volume_mount in exist_volume_mounts:
            if exist_volume_mount['name'] == volume_mount['name']:
                volume_mount_found = True
                break

        return volume_mount_found

    def exists_volume(self, volume):
        ''' return whether a volume exists '''
        exist_volumes = self.get_volumes()

        volume_found = False
        for exist_volume in exist_volumes:
            if exist_volume['name'] == volume['name']:
                volume_found = True
                break

        return volume_found

    def find_volume_by_name(self, volume, mounts=False):
        ''' return the index of a volume '''
        volumes = []
        if mounts:
            volumes = self.get_volume_mounts()
        else:
            volumes = self.get_volumes()
        for exist_volume in volumes:
            if exist_volume['name'] == volume['name']:
                return exist_volume

        return None

    def get_replicas(self):
        ''' return replicas setting '''
        return self.get(DeploymentConfig.replicas_path)

    def get_volume_mounts(self):
        '''return volume mount information '''
        return self.get_volumes(mounts=True)

    def get_volumes(self, mounts=False):
        '''return volume mount information '''
        if mounts:
            return self.get(DeploymentConfig.volume_mounts_path) or []

        return self.get(DeploymentConfig.volumes_path) or []

    def delete_volume_by_name(self, volume):
        '''delete a volume '''
        modified = False
        exist_volume_mounts = self.get_volume_mounts()
        exist_volumes = self.get_volumes()
        del_idx = None
        for idx, exist_volume in enumerate(exist_volumes):
            if 'name' in exist_volume and exist_volume['name'] == volume['name']:
                del_idx = idx
                break

        if del_idx != None:
            del exist_volumes[del_idx]
            modified = True

        del_idx = None
        for idx, exist_volume_mount in enumerate(exist_volume_mounts):
            if 'name' in exist_volume_mount and exist_volume_mount['name'] == volume['name']:
                del_idx = idx
                break

        if del_idx != None:
            del exist_volume_mounts[idx]
            modified = True

        return modified

    def add_volume_mount(self, volume_mount):
        ''' add a volume or volume mount to the proper location '''
        exist_volume_mounts = self.get_volume_mounts()

        if not exist_volume_mounts and volume_mount:
            self.put(DeploymentConfig.volume_mounts_path, [volume_mount])
        else:
            exist_volume_mounts.append(volume_mount)

    def add_volume(self, volume):
        ''' add a volume or volume mount to the proper location '''
        exist_volumes = self.get_volumes()
        if not volume:
            return

        if not exist_volumes:
            self.put(DeploymentConfig.volumes_path, [volume])
        else:
            exist_volumes.append(volume)

    def update_replicas(self, replicas):
        ''' update replicas value '''
        self.put(DeploymentConfig.replicas_path, replicas)

    def update_volume(self, volume):
        '''place an env in the env var list'''
        exist_volumes = self.get_volumes()

        if not volume:
            return False

        # update the volume
        update_idx = None
        for idx, exist_vol in enumerate(exist_volumes):
            if exist_vol['name'] == volume['name']:
                update_idx = idx
                break

        if update_idx != None:
            exist_volumes[update_idx] = volume
        else:
            self.add_volume(volume)

        return True

    def update_volume_mount(self, volume_mount):
        '''place an env in the env var list'''
        modified = False

        exist_volume_mounts = self.get_volume_mounts()

        if not volume_mount:
            return False

        # update the volume mount
        for exist_vol_mount in exist_volume_mounts:
            if exist_vol_mount['name'] == volume_mount['name']:
                if 'mountPath' in exist_vol_mount and \
                   str(exist_vol_mount['mountPath']) != str(volume_mount['mountPath']):
                    exist_vol_mount['mountPath'] = volume_mount['mountPath']
                    modified = True
                break

        if not modified:
            self.add_volume_mount(volume_mount)
            modified = True

        return modified

    def needs_update_volume(self, volume, volume_mount):
        ''' verify a volume update is needed '''
        exist_volume = self.find_volume_by_name(volume)
        exist_volume_mount = self.find_volume_by_name(volume, mounts=True)
        results = []
        results.append(exist_volume['name'] == volume['name'])

        if 'secret' in volume:
            results.append('secret' in exist_volume)
            results.append(exist_volume['secret']['secretName'] == volume['secret']['secretName'])
            results.append(exist_volume_mount['name'] == volume_mount['name'])
            results.append(exist_volume_mount['mountPath'] == volume_mount['mountPath'])

        elif 'emptyDir' in volume:
            results.append(exist_volume_mount['name'] == volume['name'])
            results.append(exist_volume_mount['mountPath'] == volume_mount['mountPath'])

        elif 'persistentVolumeClaim' in volume:
            pvc = 'persistentVolumeClaim'
            results.append(pvc in exist_volume)
            if results[-1]:
                results.append(exist_volume[pvc]['claimName'] == volume[pvc]['claimName'])

                if 'claimSize' in volume[pvc]:
                    results.append(exist_volume[pvc]['claimSize'] == volume[pvc]['claimSize'])

        elif 'hostpath' in volume:
            results.append('hostPath' in exist_volume)
            results.append(exist_volume['hostPath']['path'] == volume_mount['mountPath'])

        return not all(results)

    def needs_update_replicas(self, replicas):
        ''' verify whether a replica update is needed '''
        current_reps = self.get(DeploymentConfig.replicas_path)
        return not current_reps == replicas

# -*- -*- -*- End included fragment: lib/deploymentconfig.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: lib/serviceaccount.py -*- -*- -*-

class ServiceAccountConfig(object):
    '''Service account config class

       This class stores the options and returns a default service account
    '''

    # pylint: disable=too-many-arguments
    def __init__(self, sname, namespace, kubeconfig, secrets=None, image_pull_secrets=None):
        self.name = sname
        self.kubeconfig = kubeconfig
        self.namespace = namespace
        self.secrets = secrets or []
        self.image_pull_secrets = image_pull_secrets or []
        self.data = {}
        self.create_dict()

    def create_dict(self):
        ''' return a properly structured volume '''
        self.data['apiVersion'] = 'v1'
        self.data['kind'] = 'ServiceAccount'
        self.data['metadata'] = {}
        self.data['metadata']['name'] = self.name
        self.data['metadata']['namespace'] = self.namespace

        self.data['secrets'] = []
        if self.secrets:
            for sec in self.secrets:
                self.data['secrets'].append({"name": sec})

        self.data['imagePullSecrets'] = []
        if self.image_pull_secrets:
            for sec in self.image_pull_secrets:
                self.data['imagePullSecrets'].append({"name": sec})

class ServiceAccount(Yedit):
    ''' Class to wrap the oc command line tools '''
    image_pull_secrets_path = "imagePullSecrets"
    secrets_path = "secrets"

    def __init__(self, content):
        '''ServiceAccount constructor'''
        super(ServiceAccount, self).__init__(content=content)
        self._secrets = None
        self._image_pull_secrets = None

    @property
    def image_pull_secrets(self):
        ''' property for image_pull_secrets '''
        if self._image_pull_secrets is None:
            self._image_pull_secrets = self.get(ServiceAccount.image_pull_secrets_path) or []
        return self._image_pull_secrets

    @image_pull_secrets.setter
    def image_pull_secrets(self, secrets):
        ''' property for secrets '''
        self._image_pull_secrets = secrets

    @property
    def secrets(self):
        ''' property for secrets '''
        if not self._secrets:
            self._secrets = self.get(ServiceAccount.secrets_path) or []
        return self._secrets

    @secrets.setter
    def secrets(self, secrets):
        ''' property for secrets '''
        self._secrets = secrets

    def delete_secret(self, inc_secret):
        ''' remove a secret '''
        remove_idx = None
        for idx, sec in enumerate(self.secrets):
            if sec['name'] == inc_secret:
                remove_idx = idx
                break

        if remove_idx:
            del self.secrets[remove_idx]
            return True

        return False

    def delete_image_pull_secret(self, inc_secret):
        ''' remove a image_pull_secret '''
        remove_idx = None
        for idx, sec in enumerate(self.image_pull_secrets):
            if sec['name'] == inc_secret:
                remove_idx = idx
                break

        if remove_idx:
            del self.image_pull_secrets[remove_idx]
            return True

        return False

    def find_secret(self, inc_secret):
        '''find secret'''
        for secret in self.secrets:
            if secret['name'] == inc_secret:
                return secret

        return None

    def find_image_pull_secret(self, inc_secret):
        '''find secret'''
        for secret in self.image_pull_secrets:
            if secret['name'] == inc_secret:
                return secret

        return None

    def add_secret(self, inc_secret):
        '''add secret'''
        if self.secrets:
            self.secrets.append({"name": inc_secret})  # pylint: disable=no-member
        else:
            self.put(ServiceAccount.secrets_path, [{"name": inc_secret}])

    def add_image_pull_secret(self, inc_secret):
        '''add image_pull_secret'''
        if self.image_pull_secrets:
            self.image_pull_secrets.append({"name": inc_secret})  # pylint: disable=no-member
        else:
            self.put(ServiceAccount.image_pull_secrets_path, [{"name": inc_secret}])

# -*- -*- -*- End included fragment: lib/serviceaccount.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: lib/secret.py -*- -*- -*-

# pylint: disable=too-many-instance-attributes
class SecretConfig(object):
    ''' Handle secret options '''
    # pylint: disable=too-many-arguments
    def __init__(self,
                 sname,
                 namespace,
                 kubeconfig,
                 secrets=None):
        ''' constructor for handling secret options '''
        self.kubeconfig = kubeconfig
        self.name = sname
        self.namespace = namespace
        self.secrets = secrets
        self.data = {}

        self.create_dict()

    def create_dict(self):
        ''' return a secret as a dict '''
        self.data['apiVersion'] = 'v1'
        self.data['kind'] = 'Secret'
        self.data['metadata'] = {}
        self.data['metadata']['name'] = self.name
        self.data['metadata']['namespace'] = self.namespace
        self.data['data'] = {}
        if self.secrets:
            for key, value in self.secrets.items():
                self.data['data'][key] = value

# pylint: disable=too-many-instance-attributes
class Secret(Yedit):
    ''' Class to wrap the oc command line tools '''
    secret_path = "data"
    kind = 'secret'

    def __init__(self, content):
        '''secret constructor'''
        super(Secret, self).__init__(content=content)
        self._secrets = None

    @property
    def secrets(self):
        '''secret property getter'''
        if self._secrets is None:
            self._secrets = self.get_secrets()
        return self._secrets

    @secrets.setter
    def secrets(self):
        '''secret property setter'''
        if self._secrets is None:
            self._secrets = self.get_secrets()
        return self._secrets

    def get_secrets(self):
        ''' returns all of the defined secrets '''
        return self.get(Secret.secret_path) or {}

    def add_secret(self, key, value):
        ''' add a secret '''
        if self.secrets:
            self.secrets[key] = value
        else:
            self.put(Secret.secret_path, {key: value})

        return True

    def delete_secret(self, key):
        ''' delete secret'''
        try:
            del self.secrets[key]
        except KeyError as _:
            return False

        return True

    def find_secret(self, key):
        ''' find secret'''
        rval = None
        try:
            rval = self.secrets[key]
        except KeyError as _:
            return None

        return {'key': key, 'value': rval}

    def update_secret(self, key, value):
        ''' update a secret'''
        # pylint: disable=no-member
        if self.secrets.has_key(key):
            self.secrets[key] = value
        else:
            self.add_secret(key, value)

        return True

# -*- -*- -*- End included fragment: lib/secret.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: lib/rolebinding.py -*- -*- -*-

# pylint: disable=too-many-instance-attributes
class RoleBindingConfig(object):
    ''' Handle route options '''
    # pylint: disable=too-many-arguments
    def __init__(self,
                 sname,
                 namespace,
                 kubeconfig,
                 group_names=None,
                 role_ref=None,
                 subjects=None,
                 usernames=None):
        ''' constructor for handling route options '''
        self.kubeconfig = kubeconfig
        self.name = sname
        self.namespace = namespace
        self.group_names = group_names
        self.role_ref = role_ref
        self.subjects = subjects
        self.usernames = usernames
        self.data = {}

        self.create_dict()

    def create_dict(self):
        ''' return a service as a dict '''
        self.data['apiVersion'] = 'v1'
        self.data['kind'] = 'RoleBinding'
        self.data['groupNames'] = self.group_names
        self.data['metadata']['name'] = self.name
        self.data['metadata']['namespace'] = self.namespace

        self.data['roleRef'] = self.role_ref
        self.data['subjects'] = self.subjects
        self.data['userNames'] = self.usernames


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class RoleBinding(Yedit):
    ''' Class to wrap the oc command line tools '''
    group_names_path = "groupNames"
    role_ref_path = "roleRef"
    subjects_path = "subjects"
    user_names_path = "userNames"

    kind = 'RoleBinding'

    def __init__(self, content):
        '''RoleBinding constructor'''
        super(RoleBinding, self).__init__(content=content)
        self._subjects = None
        self._role_ref = None
        self._group_names = None
        self._user_names = None

    @property
    def subjects(self):
        ''' subjects property '''
        if self._subjects == None:
            self._subjects = self.get_subjects()
        return self._subjects

    @subjects.setter
    def subjects(self, data):
        ''' subjects property setter'''
        self._subjects = data

    @property
    def role_ref(self):
        ''' role_ref property '''
        if self._role_ref == None:
            self._role_ref = self.get_role_ref()
        return self._role_ref

    @role_ref.setter
    def role_ref(self, data):
        ''' role_ref property setter'''
        self._role_ref = data

    @property
    def group_names(self):
        ''' group_names property '''
        if self._group_names == None:
            self._group_names = self.get_group_names()
        return self._group_names

    @group_names.setter
    def group_names(self, data):
        ''' group_names property setter'''
        self._group_names = data

    @property
    def user_names(self):
        ''' user_names property '''
        if self._user_names == None:
            self._user_names = self.get_user_names()
        return self._user_names

    @user_names.setter
    def user_names(self, data):
        ''' user_names property setter'''
        self._user_names = data

    def get_group_names(self):
        ''' return groupNames '''
        return self.get(RoleBinding.group_names_path) or []

    def get_user_names(self):
        ''' return usernames '''
        return self.get(RoleBinding.user_names_path) or []

    def get_role_ref(self):
        ''' return role_ref '''
        return self.get(RoleBinding.role_ref_path) or {}

    def get_subjects(self):
        ''' return subjects '''
        return self.get(RoleBinding.subjects_path) or []

    #### ADD #####
    def add_subject(self, inc_subject):
        ''' add a subject '''
        if self.subjects:
            self.subjects.append(inc_subject)
        else:
            self.put(RoleBinding.subjects_path, [inc_subject])

        return True

    def add_role_ref(self, inc_role_ref):
        ''' add a role_ref '''
        if not self.role_ref:
            self.put(RoleBinding.role_ref_path, {"name": inc_role_ref})
            return True

        return False

    def add_group_names(self, inc_group_names):
        ''' add a group_names '''
        if self.group_names:
            self.group_names.append(inc_group_names)
        else:
            self.put(RoleBinding.group_names_path, [inc_group_names])

        return True

    def add_user_name(self, inc_user_name):
        ''' add a username '''
        if self.user_names:
            self.user_names.append(inc_user_name)
        else:
            self.put(RoleBinding.user_names_path, [inc_user_name])

        return True

    #### /ADD #####

    #### Remove #####
    def remove_subject(self, inc_subject):
        ''' remove a subject '''
        try:
            self.subjects.remove(inc_subject)
        except ValueError as _:
            return False

        return True

    def remove_role_ref(self, inc_role_ref):
        ''' remove a role_ref '''
        if self.role_ref and self.role_ref['name'] == inc_role_ref:
            del self.role_ref['name']
            return True

        return False

    def remove_group_name(self, inc_group_name):
        ''' remove a groupname '''
        try:
            self.group_names.remove(inc_group_name)
        except ValueError as _:
            return False

        return True

    def remove_user_name(self, inc_user_name):
        ''' remove a username '''
        try:
            self.user_names.remove(inc_user_name)
        except ValueError as _:
            return False

        return True

    #### /REMOVE #####

    #### UPDATE #####
    def update_subject(self, inc_subject):
        ''' update a subject '''
        try:
            index = self.subjects.index(inc_subject)
        except ValueError as _:
            return self.add_subject(inc_subject)

        self.subjects[index] = inc_subject

        return True

    def update_group_name(self, inc_group_name):
        ''' update a groupname '''
        try:
            index = self.group_names.index(inc_group_name)
        except ValueError as _:
            return self.add_group_names(inc_group_name)

        self.group_names[index] = inc_group_name

        return True

    def update_user_name(self, inc_user_name):
        ''' update a username '''
        try:
            index = self.user_names.index(inc_user_name)
        except ValueError as _:
            return self.add_user_name(inc_user_name)

        self.user_names[index] = inc_user_name

        return True

    def update_role_ref(self, inc_role_ref):
        ''' update a role_ref '''
        self.role_ref['name'] = inc_role_ref

        return True

    #### /UPDATE #####

    #### FIND ####
    def find_subject(self, inc_subject):
        ''' find a subject '''
        index = None
        try:
            index = self.subjects.index(inc_subject)
        except ValueError as _:
            return index

        return index

    def find_group_name(self, inc_group_name):
        ''' find a group_name '''
        index = None
        try:
            index = self.group_names.index(inc_group_name)
        except ValueError as _:
            return index

        return index

    def find_user_name(self, inc_user_name):
        ''' find a user_name '''
        index = None
        try:
            index = self.user_names.index(inc_user_name)
        except ValueError as _:
            return index

        return index

    def find_role_ref(self, inc_role_ref):
        ''' find a user_name '''
        if self.role_ref and self.role_ref['name'] == inc_role_ref['name']:
            return self.role_ref

        return None

# -*- -*- -*- End included fragment: lib/rolebinding.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: class/oadm_router.py -*- -*- -*-

import time

class RouterException(Exception):
    ''' Router exception'''
    pass

class RouterConfig(OpenShiftCLIConfig):
    ''' RouterConfig is a DTO for the router.  '''
    def __init__(self, rname, namespace, kubeconfig, router_options):
        super(RouterConfig, self).__init__(rname, namespace, kubeconfig, router_options)

class Router(OpenShiftCLI):
    ''' Class to wrap the oc command line tools '''
    def __init__(self,
                 router_config,
                 verbose=False):
        ''' Constructor for OpenshiftOC

           a router consists of 3 or more parts
           - dc/router
           - svc/router
           - endpoint/router
        '''
        super(Router, self).__init__('default', router_config.kubeconfig, verbose)
        self.config = router_config
        self.verbose = verbose
        self.router_parts = [{'kind': 'dc', 'name': self.config.name},
                             {'kind': 'svc', 'name': self.config.name},
                             {'kind': 'sa', 'name': self.config.config_options['service_account']['value']},
                             {'kind': 'secret', 'name': self.config.name + '-certs'},
                             {'kind': 'clusterrolebinding', 'name': 'router-' + self.config.name + '-role'},
                             #{'kind': 'endpoints', 'name': self.config.name},
                            ]

        self.__router_prep = None
        self.dconfig = None
        self.svc = None
        self._secret = None
        self._serviceaccount = None
        self._rolebinding = None
        self.get()

    @property
    def router_prep(self):
        ''' property deploymentconfig'''
        if self.__router_prep == None:
            results = self.prepare_router()
            if not results:
                raise RouterException('Could not perform router preparation')
            self.__router_prep = results

        return self.__router_prep

    @router_prep.setter
    def router_prep(self, obj):
        '''set the router prep property'''
        self.__router_prep = obj

    @property
    def deploymentconfig(self):
        ''' property deploymentconfig'''
        return self.dconfig

    @deploymentconfig.setter
    def deploymentconfig(self, config):
        ''' setter for property deploymentconfig '''
        self.dconfig = config

    @property
    def service(self):
        ''' property service '''
        return self.svc

    @service.setter
    def service(self, config):
        ''' setter for property service '''
        self.svc = config

    @property
    def secret(self):
        ''' property secret '''
        return self._secret

    @secret.setter
    def secret(self, config):
        ''' setter for property secret '''
        self._secret = config

    @property
    def serviceaccount(self):
        ''' property secret '''
        return self._serviceaccount

    @serviceaccount.setter
    def serviceaccount(self, config):
        ''' setter for property secret '''
        self._serviceaccount = config

    @property
    def rolebinding(self):
        ''' property rolebinding '''
        return self._rolebinding

    @rolebinding.setter
    def rolebinding(self, config):
        ''' setter for property rolebinding '''
        self._rolebinding = config

    def get(self):
        ''' return the self.router_parts '''
        self.service = None
        self.deploymentconfig = None
        self.serviceaccount = None
        self.secret = None
        self.rolebinding = None
        for part in self.router_parts:
            result = self._get(part['kind'], rname=part['name'])
            if result['returncode'] == 0 and part['kind'] == 'dc':
                self.deploymentconfig = DeploymentConfig(result['results'][0])
            elif result['returncode'] == 0 and part['kind'] == 'svc':
                self.service = Service(content=result['results'][0])
            elif result['returncode'] == 0 and part['kind'] == 'sa':
                self.serviceaccount = ServiceAccount(content=result['results'][0])
            elif result['returncode'] == 0 and part['kind'] == 'secret':
                self.secret = Secret(content=result['results'][0])
            elif result['returncode'] == 0 and part['kind'] == 'clusterrolebinding':
                self.rolebinding = RoleBinding(content=result['results'][0])

        return {'deploymentconfig': self.deploymentconfig,
                'service': self.service,
                'serviceaccount': self.serviceaccount,
                'secret': self.secret,
                'clusterrolebinding': self.rolebinding,
               }

    def exists(self):
        '''return a whether svc or dc exists '''
        if self.deploymentconfig and self.service and self.secret and self.serviceaccount:
            return True

        return False

    def delete(self):
        '''return all pods '''
        parts = []
        for part in self.router_parts:
            parts.append(self._delete(part['kind'], part['name']))

        return parts

    def add_modifications(self, deploymentconfig):
        '''modify the deployment config'''
        # We want modifications in the form of edits coming in from the module.
        # Let's apply these here
        edit_results = []
        for edit in self.config.config_options['edits'].get('value', []):
            if edit['action'] == 'put':
                edit_results.append(deploymentconfig.put(edit['key'],
                                                         edit['value']))
            if edit['action'] == 'update':
                edit_results.append(deploymentconfig.update(edit['key'],
                                                            edit['value'],
                                                            edit.get('index', None),
                                                            edit.get('curr_value', None)))
            if edit['action'] == 'append':
                edit_results.append(deploymentconfig.append(edit['key'],
                                                            edit['value']))

        if edit_results and not any([res[0] for res in edit_results]):
            return None

        return deploymentconfig

    def prepare_router(self):
        '''prepare router for instantiation'''
        # We need to create the pem file
        router_pem = '/tmp/router.pem'
        with open(router_pem, 'w') as rfd:
            rfd.write(open(self.config.config_options['cert_file']['value']).read())
            rfd.write(open(self.config.config_options['key_file']['value']).read())
            if self.config.config_options['cacert_file']['value'] and \
               os.path.exists(self.config.config_options['cacert_file']['value']):
                rfd.write(open(self.config.config_options['cacert_file']['value']).read())

        atexit.register(Utils.cleanup, [router_pem])
        self.config.config_options['default_cert']['value'] = router_pem

        options = self.config.to_option_list()

        cmd = ['router', self.config.name, '-n', self.config.namespace]
        cmd.extend(options)
        cmd.extend(['--dry-run=True', '-o', 'json'])

        results = self.openshift_cmd(cmd, oadm=True, output=True, output_type='json')

        # pylint: disable=no-member
        if results['returncode'] != 0 and results['results'].has_key('items'):
            return results

        oc_objects = {'DeploymentConfig': {'obj': None, 'path': None},
                      'Secret': {'obj': None, 'path': None},
                      'ServiceAccount': {'obj': None, 'path': None},
                      'ClusterRoleBinding': {'obj': None, 'path': None},
                      'Service': {'obj': None, 'path': None},
                     }
        # pylint: disable=invalid-sequence-index
        for res in results['results']['items']:
            if res['kind'] == 'DeploymentConfig':
                oc_objects['DeploymentConfig']['obj'] = DeploymentConfig(res)
            elif res['kind'] == 'Service':
                oc_objects['Service']['obj'] = Service(res)
            elif res['kind'] == 'ServiceAccount':
                oc_objects['ServiceAccount']['obj'] = ServiceAccount(res)
            elif res['kind'] == 'Secret':
                oc_objects['Secret']['obj'] = Secret(res)
            elif res['kind'] == 'ClusterRoleBinding':
                oc_objects['ClusterRoleBinding']['obj'] = RoleBinding(res)

        # Currently only deploymentconfig needs updating
        # Verify we got a deploymentconfig
        if not oc_objects['DeploymentConfig']['obj']:
            return results

        # results will need to get parsed here and modifications added
        oc_objects['DeploymentConfig']['obj'] = self.add_modifications(oc_objects['DeploymentConfig']['obj'])

        for oc_type in oc_objects.keys():
            oc_objects[oc_type]['path'] = Utils.create_tmp_file_from_contents(oc_type, oc_objects[oc_type]['obj'].yaml_dict)

        return oc_objects

    def create(self):
        '''Create a deploymentconfig '''
        # generate the objects and prepare for instantiation
        self.prepare_router()

        results = []
        for _, oc_data in self.router_prep.items():
            results.append(self._create(oc_data['path']))

        rval = 0
        for result in results:
            if result['returncode'] != 0 and not 'already exist' in result['stderr']:
                rval = result['returncode']

        return {'returncode': rval, 'results': results}

    def update(self):
        '''run update for the router.  This performs a delete and then create '''
        parts = self.delete()
        for part in parts:
            if part['returncode'] != 0:
                if part.has_key('stderr') and 'not found' in part['stderr']:
                    # the object is not there, continue
                    continue

                # something went wrong
                return parts

        # Ugly built in sleep here.
        time.sleep(15)

        return self.create()

    # pylint: disable=too-many-return-statements,too-many-branches
    def needs_update(self):
        ''' check to see if we need to update '''
        if not self.deploymentconfig or not self.service or not self.serviceaccount or not self.secret:
            return True

        oc_objects_prep = self.prepare_router()

        # Since the output from oadm_router is returned as raw
        # we need to parse it.  The first line is the stats_password in 3.1
        # Inside of 3.2, it is just json

        # ServiceAccount:
        #   Need to determine the pregenerated ones from the original
        #   Since these are auto generated, we can skip
        skip = ['secrets', 'imagePullSecrets']
        if not Utils.check_def_equal(oc_objects_prep['ServiceAccount']['obj'].yaml_dict,
                                     self.serviceaccount.yaml_dict,
                                     skip_keys=skip,
                                     debug=self.verbose):
            return True

        # Secret:
        #   In 3.2 oadm router generates a secret volume for certificates
        #   See if one was generated from our dry-run and verify it if needed
        if oc_objects_prep['Secret']['obj']:
            if not self.secret:
                return True
            if not Utils.check_def_equal(oc_objects_prep['Secret']['obj'].yaml_dict,
                                         self.secret.yaml_dict,
                                         skip_keys=skip,
                                         debug=self.verbose):
                return True

        # Service:
        #   Fix the ports to have protocol=TCP
        for port in oc_objects_prep['Service']['obj'].get('spec.ports'):
            port['protocol'] = 'TCP'

        skip = ['portalIP', 'clusterIP', 'sessionAffinity', 'type']
        if not Utils.check_def_equal(oc_objects_prep['Service']['obj'].yaml_dict,
                                     self.service.yaml_dict,
                                     skip_keys=skip,
                                     debug=self.verbose):
            return True

        # DeploymentConfig:
        #   Router needs some exceptions.
        #   We do not want to check the autogenerated password for stats admin
        if not self.config.config_options['stats_password']['value']:
            for idx, env_var in enumerate(oc_objects_prep['DeploymentConfig']['obj'].get(\
                        'spec.template.spec.containers[0].env') or []):
                if env_var['name'] == 'STATS_PASSWORD':
                    env_var['value'] = \
                      self.deploymentconfig.get('spec.template.spec.containers[0].env[%s].value' % idx)
                    break

        #   dry-run doesn't add the protocol to the ports section.  We will manually do that.
        for idx, port in enumerate(oc_objects_prep['DeploymentConfig']['obj'].get(\
                        'spec.template.spec.containers[0].ports') or []):
            if not port.has_key('protocol'):
                port['protocol'] = 'TCP'

        #   These are different when generating
        skip = ['dnsPolicy',
                'terminationGracePeriodSeconds',
                'restartPolicy', 'timeoutSeconds',
                'livenessProbe', 'readinessProbe',
                'terminationMessagePath', 'hostPort',
                'defaultMode',
               ]

        return not Utils.check_def_equal(oc_objects_prep['DeploymentConfig']['obj'].yaml_dict,
                                         self.deploymentconfig.yaml_dict,
                                         skip_keys=skip,
                                         debug=self.verbose)


    @staticmethod
    def run_ansible(params, check_mode):
        '''run ansible idempotent code'''

        rconfig = RouterConfig(params['name'],
                               params['namespace'],
                               params['kubeconfig'],
                               {'default_cert': {'value': None, 'include': True},
                                'cert_file': {'value': params['cert_file'], 'include': False},
                                'key_file': {'value': params['key_file'], 'include': False},
                                'images': {'value': params['images'], 'include': True},
                                'latest_images': {'value': params['latest_images'], 'include': True},
                                'labels': {'value': params['labels'], 'include': True},
                                'ports': {'value': ','.join(params['ports']), 'include': True},
                                'replicas': {'value': params['replicas'], 'include': True},
                                'selector': {'value': params['selector'], 'include': True},
                                'service_account': {'value': params['service_account'], 'include': True},
                                'router_type': {'value': params['router_type'], 'include': False},
                                'host_network': {'value': params['host_network'], 'include': True},
                                'external_host': {'value': params['external_host'], 'include': True},
                                'external_host_vserver': {'value': params['external_host_vserver'],
                                                          'include': True},
                                'external_host_insecure': {'value': params['external_host_insecure'],
                                                           'include': True},
                                'external_host_partition_path': {'value': params['external_host_partition_path'],
                                                                 'include': True},
                                'external_host_username': {'value': params['external_host_username'],
                                                           'include': True},
                                'external_host_password': {'value': params['external_host_password'],
                                                           'include': True},
                                'external_host_private_key': {'value': params['external_host_private_key'],
                                                              'include': True},
                                'expose_metrics': {'value': params['expose_metrics'], 'include': True},
                                'metrics_image': {'value': params['metrics_image'], 'include': True},
                                'stats_user': {'value': params['stats_user'], 'include': True},
                                'stats_password': {'value': params['stats_password'], 'include': True},
                                'stats_port': {'value': params['stats_port'], 'include': True},
                                # extra
                                'cacert_file': {'value': params['cacert_file'], 'include': False},
                                # edits
                                'edits': {'value': params['edits'], 'include': False},
                               })


        ocrouter = Router(rconfig)

        state = params['state']

        ########
        # Delete
        ########
        if state == 'absent':
            if not ocrouter.exists():
                return {'changed': False, 'state': state}

            if check_mode:
                return {'changed': True, 'msg': 'CHECK_MODE: Would have performed a delete.'}

            api_rval = ocrouter.delete()

            return {'changed': True, 'results': api_rval, 'state': state}

        if state == 'present':
            ########
            # Create
            ########
            if not ocrouter.exists():

                if check_mode:
                    return {'changed': True, 'msg': 'CHECK_MODE: Would have performed a create.'}

                api_rval = ocrouter.create()

                if api_rval['returncode'] != 0:
                    return {'failed': True, 'msg': api_rval}

                return {'changed': True, 'results': api_rval, 'state': state}

            ########
            # Update
            ########
            if not ocrouter.needs_update():
                return {'changed': False, 'state': state}

            if check_mode:
                return {'changed': False, 'msg': 'CHECK_MODE: Would have performed an update.'}

            api_rval = ocrouter.update()

            if api_rval['returncode'] != 0:
                return {'failed': True, 'msg': api_rval}

            return {'changed': True, 'results': api_rval, 'state': state}

# -*- -*- -*- End included fragment: class/oadm_router.py -*- -*- -*-

# -*- -*- -*- Begin included fragment: ansible/oadm_router.py -*- -*- -*-


def main():
    '''
    ansible oc module for router
    '''

    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='present', type='str',
                       choices=['present', 'absent']),
            debug=dict(default=False, type='bool'),
            namespace=dict(default='default', type='str'),
            name=dict(default='router', type='str'),

            kubeconfig=dict(default='/etc/origin/master/admin.kubeconfig', type='str'),
            cert_file=dict(default=None, type='str'),
            key_file=dict(default=None, type='str'),
            images=dict(default=None, type='str'), #'openshift3/ose-${component}:${version}'
            latest_images=dict(default=False, type='bool'),
            labels=dict(default=None, type='list'),
            ports=dict(default=['80:80', '443:443'], type='list'),
            replicas=dict(default=1, type='int'),
            selector=dict(default=None, type='str'),
            service_account=dict(default='router', type='str'),
            router_type=dict(default='haproxy-router', type='str'),
            host_network=dict(default=True, type='bool'),
            # external host options
            external_host=dict(default=None, type='str'),
            external_host_vserver=dict(default=None, type='str'),
            external_host_insecure=dict(default=False, type='bool'),
            external_host_partition_path=dict(default=None, type='str'),
            external_host_username=dict(default=None, type='str'),
            external_host_password=dict(default=None, type='str'),
            external_host_private_key=dict(default=None, type='str'),
            # Metrics
            expose_metrics=dict(default=False, type='bool'),
            metrics_image=dict(default=None, type='str'),
            # Stats
            stats_user=dict(default=None, type='str'),
            stats_password=dict(default=None, type='str'),
            stats_port=dict(default=1936, type='int'),
            # extra
            cacert_file=dict(default=None, type='str'),
            # edits
            edits=dict(default=[], type='list'),
        ),
        mutually_exclusive=[["router_type", "images"]],

        supports_check_mode=True,
    )
    results = Router.run_ansible(module.params, module.check_mode)

    if 'failed' in results:
        module.fail_json(**results)

    module.exit_json(**results)


if __name__ == '__main__':
    main()

# -*- -*- -*- End included fragment: ansible/oadm_router.py -*- -*- -*-
