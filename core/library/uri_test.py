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
module: uri_test
version_added: 2.never
short_description: A utility to test a website's response time
description:
  - "A simple utility to make repeated calls to a web server at the specified URI."

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
      - "A boolean value, which when set tells the module to use the HTTP KeepAlive feature."
    required: no
    default: no
  variable_length:
    description:
      - "A boolean value, which when set tells the module to accept variable-length responses."
      - "When disabled, any differences in bytes returned from the first response C(ab) 
        receives is marked as an error in the report."
    required: no
    default: no

requirements: [] # <- NO REQUIREMENTS!

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
  uri_test:
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
from ansible.module_utils.urls import open_url

import time

from collections import namedtuple
from multiprocessing import Pool

URIResult = namedtuple('URIResult', ['status', 'time', 'content_length', 'total_length'])

def run_test(uri, keepalive, variable_length):
    headers = dict()
    if keepalive:
       headers['Connection'] = 'keep-alive'
    start = time.time()
    res = open_url(uri, headers=headers)
    end = time.time()
    info = res.info()

    total_length = content_length = len(res.read())
    return URIResult(res.code, end - start, content_length, total_length)

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

    # pull arguments out of the parsed module parameters
    uri             = module.params['uri']
    request_count   = module.params['request_count']
    workers         = module.params['workers']
    keepalive       = module.params['keepalive']
    variable_length = module.params['variable_length']

    # we have to do some parameter validation now...
    if workers < 1:
        module.fail_json(dict(msg="workers must be greater than 0"))
    if request_count < 1:
        module.fail-json(dict(msg="the request_count value must be greater than 0"))
    if request_count < workers:
        workers = request_count

    # use a multiprocessing pool to process each request
    pool = Pool(processes=workers)
    start = time.time()
    async_results = [pool.apply_async(run_test, (uri, keepalive, variable_length)) for i in range(0, request_count)]
    pool.close()
    pool.join()
    end = time.time()

    # now do some basic result processing
    total_time          = round(end - start, 3)
    total_bytes         = 0
    total_content_bytes = 0
    total_errors        = 0

    for async_result in async_results:
        res = async_result.get()
        total_bytes += res.total_length
        total_content_bytes += res.content_length
        if res.status < 200 or res.status >= 400:
            total_errors += 1

    # we build our dictionary for the final result we'll return
    result = dict(
        total_time = total_time,
        total_bytes_transferred = total_bytes,
        total_content_bytes_transferred = total_content_bytes,
        requests_per_second = round(request_count / total_time, 2),
        kbytes_per_second = round((float(total_bytes) / total_time) / 2**10, 2),
        failed_requests = total_errors,
    )

    # finally we return the result using exit_json()
    module.exit_json(**result)


if __name__ == '__main__':
    main()
