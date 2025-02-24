#! /usr/bin/env python

# Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is intended to be run as part of a periodic proposal bot
# job in OpenStack infrastructure.
#
# In order to function correctly, the environment in which the
# script runs must have
#   * network access to the review.opendev.org Gerrit API
#     working directory
#   * network access to https://opendev.org/openstack

import json
import re
import sys

import urllib3
from urllib3.util import retry

# List of projects having tempest plugin stale or unmaintained for a long time
# (6 months or more)
# TODO(masayukig): Some of these can be removed from NON_ACTIVE_LIST in the
# future when the patches are merged.
NON_ACTIVE_LIST = [
    'x/gce-api',  # It looks gce-api doesn't support python3 yet
    # https://bugs.launchpad.net/gce-api/+bug/1931094
    'x/glare',  # To avoid sanity-job failure
    'x/group-based-policy',
    # https://bugs.launchpad.net/group-based-policy/+bug/1931091
    'x/intel-nfv-ci-tests',  # To avoid sanity-job failure
    'openstack/networking-generic-switch',
    # This is not a real tempest plugin,
    # https://review.opendev.org/#/c/634846/
    'x/networking-plumgrid',  # No longer contains tempest tests
    'x/networking-spp',  # https://review.opendev.org/#/c/635098/
    # networking-spp is missing neutron-tempest-plugin as a dep plus
    # test-requirements.txt is nested in a openstack dir and sanity script
    # doesn't count with such scenario yet
    'openstack/neutron-dynamic-routing',
    # As tests have been migrated to neutron-tempest-plugin:
    # https://review.opendev.org/#/c/637718/
    'openstack/neutron-vpnaas',
    # As tests have been migrated to neutron-tempest-plugin:
    # https://review.opendev.org/c/openstack/neutron-vpnaas/+/695834
    'x/valet',  # valet is unmaintained now
    # https://review.opendev.org/c/x/valet/+/638339
    'x/kingbird',  # kingbird is unmaintained now
    # https://bugs.launchpad.net/kingbird/+bug/1869722
    'x/mogan',
    # mogan is unmaintained now, remove from the list when this is merged:
    # https://review.opendev.org/c/x/mogan/+/767718
    'x/vmware-nsx-tempest-plugin'
    # Failing since 2021-08-27
    # https://zuul.opendev.org/t/openstack/build
    # /45f6c8d3c62d4387a70b7b471ec687c8
    # Below plugins failing for error in psycopg2 __init__
    # ImportError: libpq.so.5: cannot open shared object
    # file: No such file or directory
    # https://zuul.opendev.org/t/openstack/build
    # /b61a48196dfa476d83645aea4853e544/log/job-output.txt#271722
    # Failing since 2021-09-08
    'x/networking-l2gw-tempest-plugin'
    'x/novajoin-tempest-plugin'
    'x/ranger-tempest-plugin'
    'x/tap-as-a-service-tempest-plugin'
    'x/trio2o'
    # No changes are merging in this
    # https://review.opendev.org/q/project:x%252Fnetworking-fortinet
    'x/networking-fortinet'
]

url = 'https://review.opendev.org/projects/'

# This is what a project looks like
'''
  "openstack-attic/akanda": {
    "id": "openstack-attic%2Fakanda",
    "state": "READ_ONLY"
  },
'''

http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED')
retries = retry.Retry(status_forcelist=[500], backoff_factor=1.0)


def has_tempest_plugin(proj):
    try:
        r = http.request('GET', "https://opendev.org/%s/raw/branch/"
                         "master/setup.cfg" % proj, retries=retries)
        if r.status == 404:
            return False
    except urllib3.exceptions.MaxRetryError as err:
        # We should not ignore non 404 errors.
        raise err
    p = re.compile(r'^tempest\.test_plugins', re.M)
    if p.findall(r.data.decode('utf-8')):
        return True
    else:
        False


if len(sys.argv) > 1 and sys.argv[1] == 'nonactivelist':
    for non_active_plugin in NON_ACTIVE_LIST:
        print(non_active_plugin)
    # We just need NON_ACTIVE_LIST when we use this `nonactivelist` option.
    # So, this exits here.
    sys.exit()

r = http.request('GET', url, retries=retries)
# Gerrit prepends 4 garbage octets to the JSON, in order to counter
# cross-site scripting attacks.  Therefore we must discard it so the
# json library won't choke.
content = r.data.decode('utf-8')[4:]
projects = sorted(json.loads(content))

# Retrieve projects having no deployment tool repo (such as deb,
# puppet, ansible, etc.), infra repos, ui or spec namespace as those
# namespaces do not contains tempest plugins.
projects_list = [i for i in projects if not (
    i.startswith('openstack-dev/') or
    i.startswith('openstack-infra/') or
    i.startswith('openstack/ansible-') or
    i.startswith('openstack/charm-') or
    i.startswith('openstack/cookbook-openstack-') or
    i.startswith('openstack/devstack-') or
    i.startswith('openstack/fuel-') or
    i.startswith('openstack/deb-') or
    i.startswith('openstack/puppet-') or
    i.startswith('openstack/openstack-ansible-') or
    i.startswith('x/deb-') or
    i.startswith('x/fuel-') or
    i.startswith('x/python-') or
    i.startswith('zuul/') or
    i.endswith('-ui') or
    i.endswith('-specs'))]

found_plugins = list(filter(has_tempest_plugin, projects_list))

# We have tempest plugins not only in 'openstack/' namespace but also the
# other name spaces such as 'airship/', 'x/', etc.
# So, we print all of them here.
for project in found_plugins:
    print(project)
