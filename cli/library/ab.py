#!/usr/bin/python
# -*- coding: utf-8 -*-

#------------------------------------------------------------------------------
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#------------------------------------------------------------------------------


# The ANSIBLE_METADATA dictionary contains information about the module for use
# by other tools. At the moment, it informs other tools which type of maintainer
# the module has and to what degree users can rely on a module’s behaviour remaining
# the same over time.

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'community',
}

# The DOCUMENTATION string is used to build the docs for both https://docs.ansible.com
# as well as the ansible-doc command.

DOCUMENTATION = '''
---
module: ab
version_added: 2.never
short_description: Use the ab command line utility to test a website's response time
description:
  - "This module use the C(ab) (apache bench) CLI utility to load test a target URL.
    From the C(ab) man page:"
  - "C(ab) is a tool for benchmarking your Apache Hypertext Transfer Protocol (HTTP)
    server. It is designed to give you an impression of how your current Apache
    installation performs."
  - "This especially shows you how many requests per second your Apache installation
    is capable of serving."

options:
  uri:
    description:
      - "The target URI to test."
    required: yes
  reqeust_count:
    description:
      - "The number of requests to send to the C(uri)."
    required: no
    default: 1000
  workers:
    description:
      - "The number of concurrent workers to use for sending requests."
    required: no
    default: 5
  keepalive:
    description:
      - "A boolean value, which when set tells C(ab) to use the HTTP KeepAlive feature."
    required: no
    default: no
  variable_length:
    description:
      - "A boolean value, which when set tells C(ab) to accept variable-length responses."
      - "When disabled, any differences in bytes returned from the first response C(ab) 
        receives is marked as an error in the report."
    required: no
    default: no

requirements:
  - BeautifulSoup
  - ab (apache bench CLI utility)

notes:
  - Please be aware that a large number of concurrent workers can overwhelm either the
    webserver, the host on which the module is executing, or both. Use with caution only
    on webservers you control.

author:
  - "James Cammarata"
'''

# The EXAMPLES string is likewise used on the docs website

EXAMPLES = '''
- name: load test a simple webserver
  ab:
    uri: "http://www.mydomain.com:8080/"
    request_count: 1000
    workers: 10
    keepalive: yes
    variable_length: yes
'''

# The import of AnsibleModule is done here. As discussed, this is found by
# the Ansible module compilter, which adds the `module_utils/basic.py` file
# to the compiled python tar.gz.

from ansible.module_utils.basic import AnsibleModule

try:
   from bs4 import BeautifulSoup
   HAS_BEAUTIFUL_SOUP=True
except ImportError:
   HAS_BEAUTIFUL_SOUP=False

def main():
    module = AnsibleModule(
        argument_spec=dict(
            uri = dict(required=True),
            request_count = dict(default=1000, type="int"),
            workers = dict(default=5, type="int"),
            keepalive = dict(default=False, type="bool"),
            variable_length = dict(default=False, type="bool"),
        ),
        supports_check_mode=False,
    )

    # this will fail if the "ab" binary is not available in the $PATH
    ab_path = module.get_bin_path('ab', required=True)

    # pull arguments out of the parsed module parameters
    uri             = module.params['uri']
    request_count   = module.params['request_count']
    workers         = module.params['workers']
    keepalive       = module.params['keepalive']
    variable_length = module.params['variable_length']

    # now we build the argument list to be executed later, starting first
    # with the ab_path we found with get_bin_path() above
    args = [ab_path, '-n', str(request_count), '-c', str(workers), '-w']

    if keepalive:
        args.append('-k')
    if variable_length:
        args.append('-l')

    args.append(uri)

    # now run the compiled args with run_command()
    rc, stdout, stderr = module.run_command(args)
    if rc != 0:
        module.fail_json(dict(rc=rc, stdout=stdout, stderr=stderr))

    # build the result dictionary, starting with a single element representing
    # the ab connection times table printed at the end of the output
    result = {"connection times": dict()}

    # parse the stdout data (which using the `-w` flag above is in HTML)
    # so we use the BeautifulSoup module to pull the data out.
    soup = BeautifulSoup(stdout, 'lxml')
    for tr in soup.find_all('tr'):
        if len(tr.find_all('th')) > 1:
            continue
        th = getattr(tr, 'th', None)
        if th is None:
            continue
        if 'colspan' in th.attrs:
            colspan = int(th.attrs['colspan'])
            if colspan == 4:
                continue
            label = u' '.join(th.contents).lower()
            if label[-1] == ':':
                label = label[:-1]
            result[label] = u' '.join(tr.td.contents)
        else:
            td_labels = ['Min.', 'Avg.', 'Max']
            th_label = u' '.join(tr.th.contents)
            for idx, item in enumerate(tr.find_all('td')):
                label = ('%s %s' % (td_labels[idx], th_label)).lower()
                if label[-1] == ':':
                    label = label[:-1]
                result["connection times"][label] = int(u' '.join(item.contents))

    # finally we return using a zero rc
    module.exit_json(**result)


if __name__ == '__main__':
    main()
