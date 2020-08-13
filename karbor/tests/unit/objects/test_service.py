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

from unittest import mock

from karbor import objects
from karbor.tests.unit import fake_service
from karbor.tests.unit import objects as test_objects


class TestService(test_objects.BaseObjectsTestCase):

    @mock.patch('karbor.db.sqlalchemy.api.service_get')
    def test_get_by_id(self, service_get):
        db_service = fake_service.fake_db_service()
        service_get.return_value = db_service
        service = objects.Service.get_by_id(self.context, 1)
        self._compare(self, db_service, service)
        service_get.assert_called_once_with(self.context, 1)

    @mock.patch('karbor.db.service_get_by_host_and_topic')
    def test_get_by_host_and_topic(self, service_get_by_host_and_topic):
        db_service = fake_service.fake_db_service()
        service_get_by_host_and_topic.return_value = db_service
        service = objects.Service.get_by_host_and_topic(
            self.context, 'fake-host', 'fake-topic')
        self._compare(self, db_service, service)
        service_get_by_host_and_topic.assert_called_once_with(
            self.context, 'fake-host', 'fake-topic')

    @mock.patch('karbor.db.service_get_by_args')
    def test_get_by_args(self, service_get_by_args):
        db_service = fake_service.fake_db_service()
        service_get_by_args.return_value = db_service
        service = objects.Service.get_by_args(
            self.context, 'fake-host', 'fake-key')
        self._compare(self, db_service, service)
        service_get_by_args.assert_called_once_with(
            self.context, 'fake-host', 'fake-key')

    @mock.patch('karbor.db.service_create')
    def test_create(self, service_create):
        db_service = fake_service.fake_db_service()
        service_create.return_value = db_service
        service = objects.Service(context=self.context)
        service.create()
        self.assertEqual(db_service['id'], service.id)
        service_create.assert_called_once_with(self.context, {})

    @mock.patch('karbor.db.service_update')
    def test_save(self, service_update):
        db_service = fake_service.fake_db_service()
        service = objects.Service._from_db_object(
            self.context, objects.Service(), db_service)
        service.topic = 'foobar'
        service.save()
        service_update.assert_called_once_with(self.context, service.id,
                                               {'topic': 'foobar'})

    @mock.patch('karbor.db.service_destroy')
    def test_destroy(self, service_destroy):
        db_service = fake_service.fake_db_service()
        service = objects.Service._from_db_object(
            self.context, objects.Service(), db_service)
        with mock.patch.object(service._context, 'elevated') as elevated_ctx:
            service.destroy()
            service_destroy.assert_called_once_with(elevated_ctx(), 123)


class TestServiceList(test_objects.BaseObjectsTestCase):
    @mock.patch('karbor.db.service_get_all')
    def test_get_all(self, service_get_all):
        db_service = fake_service.fake_db_service()
        service_get_all.return_value = [db_service]

        services = objects.ServiceList.get_all(self.context, 'foo')
        service_get_all.assert_called_once_with(self.context, 'foo')
        self.assertEqual(1, len(services))
        TestService._compare(self, db_service, services[0])

    @mock.patch('karbor.db.service_get_all_by_topic')
    def test_get_all_by_topic(self, service_get_all_by_topic):
        db_service = fake_service.fake_db_service()
        service_get_all_by_topic.return_value = [db_service]

        services = objects.ServiceList.get_all_by_topic(
            self.context, 'foo', 'bar')
        service_get_all_by_topic.assert_called_once_with(
            self.context, 'foo', disabled='bar')
        self.assertEqual(1, len(services))
        TestService._compare(self, db_service, services[0])

    @mock.patch('karbor.db.service_get_all_by_args')
    def test_get_all_by_args(self, service_get_all_by_args):
        db_service = fake_service.fake_db_service()
        service_get_all_by_args.return_value = [db_service]
        services = objects.ServiceList.get_all_by_args(
            self.context, 'fake-host', 'fake-service')
        service_get_all_by_args.assert_called_once_with(
            self.context, 'fake-host', 'fake-service')
        self.assertEqual(1, len(services))
        TestService._compare(self, db_service, services[0])
