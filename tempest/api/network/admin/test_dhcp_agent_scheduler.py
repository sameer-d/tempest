# Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.api.network import base
from tempest.common import utils
from tempest.common import waiters
from tempest.lib import decorators


class DHCPAgentSchedulersTestJSON(base.BaseAdminNetworkTest):
    """Test network DHCP agent scheduler extension"""

    @classmethod
    def skip_checks(cls):
        super(DHCPAgentSchedulersTestJSON, cls).skip_checks()
        if not utils.is_extension_enabled('dhcp_agent_scheduler', 'network'):
            msg = "dhcp_agent_scheduler extension not enabled."
            raise cls.skipException(msg)

    @classmethod
    def resource_setup(cls):
        super(DHCPAgentSchedulersTestJSON, cls).resource_setup()
        # Create a network and make sure it will be hosted by a
        # dhcp agent: this is done by creating a regular port
        cls.network = cls.create_network()
        cls.create_subnet(cls.network)
        cls.port = cls.create_port(cls.network)

    @decorators.idempotent_id('f164801e-1dd8-4b8b-b5d3-cc3ac77cfaa5')
    def test_dhcp_port_status_active(self):
        ports = self.admin_ports_client.list_ports(
            network_id=self.network['id'])['ports']
        for port in ports:
            waiters.wait_for_port_status(
                client=self.admin_ports_client,
                port_id=port['id'],
                status='ACTIVE')

    @decorators.idempotent_id('5032b1fe-eb42-4a64-8f3b-6e189d8b5c7d')
    def test_list_dhcp_agent_hosting_network(self):
        """Test Listing DHCP agents hosting a network"""
        self.admin_networks_client.list_dhcp_agents_on_hosting_network(
            self.network['id'])

    @decorators.idempotent_id('30c48f98-e45d-4ffb-841c-b8aad57c7587')
    def test_list_networks_hosted_by_one_dhcp(self):
        """Test Listing networks hosted by a DHCP agent"""
        body = self.admin_networks_client.list_dhcp_agents_on_hosting_network(
            self.network['id'])
        agents = body['agents']
        self.assertNotEmpty(agents, "no dhcp agent")
        agent = agents[0]
        self.assertTrue(self._check_network_in_dhcp_agent(
            self.network['id'], agent))

    def _check_network_in_dhcp_agent(self, network_id, agent):
        network_ids = []
        body = self.admin_agents_client.list_networks_hosted_by_one_dhcp_agent(
            agent['id'])
        networks = body['networks']
        for network in networks:
            network_ids.append(network['id'])
        return network_id in network_ids

    @decorators.idempotent_id('a0856713-6549-470c-a656-e97c8df9a14d')
    def test_add_remove_network_from_dhcp_agent(self):
        """Test adding and removing network from a DHCP agent"""
        # The agent is now bound to the network, we can free the port
        self.ports_client.delete_port(self.port['id'])
        agent = dict()
        agent['agent_type'] = None
        body = self.admin_agents_client.list_agents()
        agents = body['agents']
        for a in agents:
            if a['agent_type'] == 'DHCP agent':
                agent = a
                break
        self.assertEqual(agent['agent_type'], 'DHCP agent', 'Could not find '
                         'DHCP agent in agent list though dhcp_agent_scheduler'
                         ' is enabled.')
        network = self.create_network()
        network_id = network['id']
        if self._check_network_in_dhcp_agent(network_id, agent):
            self._remove_network_from_dhcp_agent(network_id, agent)
            self._add_dhcp_agent_to_network(network_id, agent)
        else:
            self._add_dhcp_agent_to_network(network_id, agent)
            self._remove_network_from_dhcp_agent(network_id, agent)

    def _remove_network_from_dhcp_agent(self, network_id, agent):
        self.admin_agents_client.delete_network_from_dhcp_agent(
            agent_id=agent['id'],
            network_id=network_id)
        self.assertFalse(self._check_network_in_dhcp_agent(
            network_id, agent))

    def _add_dhcp_agent_to_network(self, network_id, agent):
        self.admin_agents_client.add_dhcp_agent_to_network(
            agent['id'], network_id=network_id)
        self.assertTrue(self._check_network_in_dhcp_agent(
            network_id, agent))
