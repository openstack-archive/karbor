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

"""Tests for Models Database."""

from oslo_config import cfg

from smaug import context
from smaug import db
from smaug import exception
from smaug.tests import base


CONF = cfg.CONF


class ServicesDbTestCase(base.TestCase):
    """Test cases for Services database table."""

    def setUp(self):
        super(ServicesDbTestCase, self).setUp()
        self.ctxt = context.RequestContext(user_id='user_id',
                                           project_id='project_id',
                                           is_admin=True)

    def test_services_create(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest',
                                         'binary': 'binarytest',
                                         'topic': 'topictest',
                                         'report_count': 0})
        self.assertEqual(service_ref['host'], 'hosttest')

    def test_services_get(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest1',
                                         'binary': 'binarytest1',
                                         'topic': 'topictest1',
                                         'report_count': 0})

        service_get_ref = db.service_get(self.ctxt, service_ref['id'])
        self.assertEqual(service_ref['host'], 'hosttest1')
        self.assertEqual(service_get_ref['host'], 'hosttest1')

    def test_service_destroy(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest2',
                                         'binary': 'binarytest2',
                                         'topic': 'topictest2',
                                         'report_count': 0})
        service_id = service_ref['id']
        db.service_destroy(self.ctxt, service_id)
        self.assertRaises(exception.ServiceNotFound, db.service_get,
                          self.ctxt, service_id)

    def test_service_update(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest3',
                                         'binary': 'binarytest3',
                                         'topic': 'topictest3',
                                         'report_count': 0})
        service_id = service_ref['id']
        service_update_ref = db.service_update(self.ctxt, service_id,
                                               {'host': 'hosttest4',
                                                'binary': 'binarytest4',
                                                'topic': 'topictest4',
                                                'report_count': 0})
        self.assertEqual(service_ref['host'], 'hosttest3')
        self.assertEqual(service_update_ref['host'], 'hosttest4')

    def test_service_get_by_host_and_topic(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest5',
                                         'binary': 'binarytest5',
                                         'topic': 'topictest5',
                                         'report_count': 0})

        service_get_ref = db.service_get_by_host_and_topic(self.ctxt,
                                                           'hosttest5',
                                                           'topictest5')
        self.assertEqual(service_ref['host'], 'hosttest5')
        self.assertEqual(service_get_ref['host'], 'hosttest5')
