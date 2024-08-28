# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import unittest
from libcloud.utils.py3 import httplib

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.common.types import InvalidCredsError
from libcloud.compute.drivers.dreamhost import DreamhostNodeDriver
from libcloud.compute.types import NodeState

from test import MockHttp
from test.compute import TestCaseMixin
from test.secrets import DREAMHOST_PARAMS

class DreamhostTest(unittest.TestCase, TestCaseMixin):

    def setUp(self):
        DreamhostNodeDriver.connectionCls.conn_classes = (
            None,
            DreamhostMockHttp
        )
        DreamhostMockHttp.type = None
        DreamhostMockHttp.use_param = 'cmd'
        self.driver = DreamhostNodeDriver(*DREAMHOST_PARAMS)

    def test_invalid_creds(self):
        """
        Tests the error-handling for passing a bad API Key to the DreamHost API
        """
        DreamhostMockHttp.type = 'BAD_AUTH'
        try:
            self.driver.list_nodes()
            self.assertTrue(False) # Above command should have thrown an InvalidCredsException
        except InvalidCredsError:
            self.assertTrue(True)


    def test_list_nodes(self):
        """
        Test list_nodes for DreamHost PS driver.  Should return a list of two nodes:
            -   account_id: 000000
                ip: 75.119.203.51
                memory_mb: 500
                ps: ps22174
                start_date: 2010-02-25
                type: web
            -   account_id: 000000
                ip: 75.119.203.52
                memory_mb: 1500
                ps: ps22175
                start_date: 2010-02-25
                type: mysql
        """

        nodes = self.driver.list_nodes()
        self.assertEqual(len(nodes), 2)
        web_node = nodes[0]
        mysql_node = nodes[1]

        # Web node tests
        self.assertEqual(web_node.id, 'ps22174')
        self.assertEqual(web_node.state, NodeState.UNKNOWN)
        self.assertTrue('75.119.203.51' in web_node.public_ips)
        self.assertTrue(
            'current_size' in web_node.extra and
            web_node.extra['current_size'] == 500
        )
        self.assertTrue(
            'account_id' in web_node.extra and
            web_node.extra['account_id'] == 000000
        )
        self.assertTrue(
            'type' in web_node.extra and
            web_node.extra['type'] == 'web'
        )
        # MySql node tests
        self.assertEqual(mysql_node.id, 'ps22175')
        self.assertEqual(mysql_node.state, NodeState.UNKNOWN)
        self.assertTrue('75.119.203.52' in mysql_node.public_ips)
        self.assertTrue(
            'current_size' in mysql_node.extra and
            mysql_node.extra['current_size'] == 1500
        )
        self.assertTrue(
            'account_id' in mysql_node.extra and
            mysql_node.extra['account_id'] == 000000
        )
        self.assertTrue(
            'type' in mysql_node.extra and
            mysql_node.extra['type'] == 'mysql'
        )

    def test_create_node(self):
        """
        Test create_node for DreamHost PS driver.
        This is not remarkably compatible with libcloud.  The DH API allows
        users to specify what image they want to create and whether to move
        all their data to the (web) PS. It does NOT accept a name, size, or
        location.  The only information it returns is the PS's context id
        Once the PS is ready it will appear in the list generated by list_ps.
        """
        new_node = self.driver.create_node(
            image=self.driver.list_images()[0],
            size=self.driver.list_sizes()[0],
            movedata='no',
        )
        self.assertEqual(new_node.id, 'ps12345')
        self.assertEqual(new_node.state, NodeState.PENDING)
        self.assertTrue(
            'type' in new_node.extra and
            new_node.extra['type'] == 'web'
        )

    def test_destroy_node(self):
        """
        Test destroy_node for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.destroy_node(node))

    def test_destroy_node_failure(self):
        """
        Test destroy_node failure for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]

        DreamhostMockHttp.type = 'API_FAILURE'
        self.assertFalse(self.driver.destroy_node(node))

    def test_reboot_node(self):
        """
        Test reboot_node for DreamHost PS driver.
        """
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver.reboot_node(node))

    def test_reboot_node_failure(self):
        """
        Test reboot_node failure for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]

        DreamhostMockHttp.type = 'API_FAILURE'
        self.assertFalse(self.driver.reboot_node(node))

    def test_resize_node(self):
        """
        Test resize_node for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]
        self.assertTrue(self.driver._resize_node(node, 400))

    def test_resize_node_failure(self):
        """
        Test reboot_node faliure for DreamHost PS driver
        """
        node = self.driver.list_nodes()[0]

        DreamhostMockHttp.type = 'API_FAILURE'
        self.assertFalse(self.driver._resize_node(node, 400))

    def test_list_images(self):
        """
        Test list_images for DreamHost PS driver.
        """
        images = self.driver.list_images()
        self.assertEqual(len(images), 2)
        self.assertEqual(images[0].id, 'web')
        self.assertEqual(images[0].name, 'web')
        self.assertEqual(images[1].id, 'mysql')
        self.assertEqual(images[1].name, 'mysql')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        self.assertEqual(len(sizes), 5)

        self.assertEqual(sizes[0].id, 'default')
        self.assertEqual(sizes[0].bandwidth, None)
        self.assertEqual(sizes[0].disk, None)
        self.assertEqual(sizes[0].ram, 2300)
        self.assertEqual(sizes[0].price, 115)

    def test_list_locations(self):
        try:
            self.driver.list_locations()
        except NotImplementedError:
            pass

    def test_list_locations_response(self):
        self.assertRaises(NotImplementedError, self.driver.list_locations)

class DreamhostMockHttp(MockHttp):

    def _BAD_AUTH_dreamhost_ps_list_ps(self, method, url, body, headers):
        body = json.dumps({'data' : 'invalid_api_key', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_add_ps(self, method, url, body, headers):
        body = json.dumps({'data' : {'added_web' : 'ps12345'}, 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_list_ps(self, method, url, body, headers):
        data = [{
            'account_id' : 000000,
            'ip': '75.119.203.51',
            'memory_mb' : 500,
            'ps' : 'ps22174',
            'start_date' : '2010-02-25',
            'type' : 'web'
        },
        {
            'account_id' : 000000,
            'ip' : '75.119.203.52',
            'memory_mb' : 1500,
            'ps' : 'ps22175',
            'start_date' : '2010-02-25',
            'type' : 'mysql'
        }]
        result = 'success'
        body = json.dumps({'data' : data, 'result' : result})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_list_images(self, method, url, body, headers):
        data = [{
            'description' : 'Private web server',
            'image' : 'web'
        },
        {
            'description' : 'Private MySQL server',
            'image' : 'mysql'
        }]
        result = 'success'
        body = json.dumps({'data' : data, 'result' : result})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_reboot(self, method, url, body, headers):
        body = json.dumps({'data' : 'reboot_scheduled', 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _API_FAILURE_dreamhost_ps_reboot(self, method, url, body, headers):
        body = json.dumps({'data' : 'no_such_ps', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_set_size(self, method, url, body, headers):
        body = json.dumps({'data' : {'memory-mb' : '500'}, 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _API_FAILURE_dreamhost_ps_set_size(self, method, url, body, headers):
        body = json.dumps({'data' : 'internal_error_setting_size', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _dreamhost_ps_remove_ps(self, method, url, body, headers):
        body = json.dumps({'data' : 'removed_web', 'result' : 'success'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _API_FAILURE_dreamhost_ps_remove_ps(self, method, url, body, headers):
        body = json.dumps({'data' : 'no_such_ps', 'result' : 'error'})
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())

