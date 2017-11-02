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

from datetime import datetime
from datetime import timedelta
from oslo_config import cfg
from oslo_utils import uuidutils
import six
import uuid

from karbor import context
from karbor import db
from karbor import exception
from karbor.tests import base

from oslo_utils import timeutils


CONF = cfg.CONF


class ModelBaseTestCase(base.TestCase):
    """Base Test cases which supplies assert Objects equal or not."""

    def _dict_from_object(self, obj, ignored_keys):
        if ignored_keys is None:
            ignored_keys = []
        if isinstance(obj, dict):
            items = obj.items()
        else:
            items = obj.iteritems()
        return {k: v for k, v in items
                if k not in ignored_keys}

    def _assertEqualObjects(self, obj1, obj2, ignored_keys=None):
        obj1 = self._dict_from_object(obj1, ignored_keys)
        obj2 = self._dict_from_object(obj2, ignored_keys)

        self.assertEqual(
            len(obj1), len(obj2),
            "Keys mismatch: %s" % six.text_type(
                set(obj1.keys()) ^ set(obj2.keys())))
        for key, value in obj1.items():
            self.assertEqual(value, obj2[key])


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
        self.assertEqual('hosttest', service_ref['host'])

    def test_services_get(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest1',
                                         'binary': 'binarytest1',
                                         'topic': 'topictest1',
                                         'report_count': 0})

        service_get_ref = db.service_get(self.ctxt, service_ref['id'])
        self.assertEqual('hosttest1', service_ref['host'])
        self.assertEqual('hosttest1', service_get_ref['host'])

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
        self.assertEqual('hosttest3', service_ref['host'])
        self.assertEqual('hosttest4', service_update_ref['host'])

    def test_service_get_by_host_and_topic(self):
        service_ref = db.service_create(self.ctxt,
                                        {'host': 'hosttest5',
                                         'binary': 'binarytest5',
                                         'topic': 'topictest5',
                                         'report_count': 0})

        service_get_ref = db.service_get_by_host_and_topic(self.ctxt,
                                                           'hosttest5',
                                                           'topictest5')
        self.assertEqual('hosttest5', service_ref['host'])
        self.assertEqual('hosttest5', service_get_ref['host'])


class TriggerTestCase(base.TestCase):
    """Test cases for triggers table."""

    def setUp(self):
        super(TriggerTestCase, self).setUp()
        self.ctxt = context.RequestContext(user_id='user_id',
                                           project_id='project_id')

    def _create_trigger(self):
        values = {
            'id': "0354ca9ddcd046b693340d78759fd274",
            'name': 'first trigger',
            'project_id': self.ctxt.tenant,
            'type': 'time',
            'properties': '{}',
        }
        return db.trigger_create(self.ctxt, values)

    def test_trigger_create(self):
        trigger_ref = self._create_trigger()
        self.assertEqual('time', trigger_ref['type'])

    def test_trigger_delete(self):
        trigger_ref = self._create_trigger()
        db.trigger_delete(self.ctxt, trigger_ref['id'])

        self.assertRaises(exception.TriggerNotFound,
                          db.trigger_delete,
                          self.ctxt, trigger_ref['id'])

        self.assertRaises(exception.TriggerNotFound,
                          db.trigger_get,
                          self.ctxt, trigger_ref['id'])

        self.assertRaises(exception.TriggerNotFound,
                          db.trigger_delete, self.ctxt, '100')

    def test_trigger_update(self):
        trigger_ref = self._create_trigger()
        id = trigger_ref['id']
        trigger_ref = db.trigger_update(self.ctxt, id, {'type': 'event'})
        self.assertEqual('event', trigger_ref['type'])

        trigger_ref = db.trigger_get(self.ctxt, id)
        self.assertEqual('event', trigger_ref['type'])

        self.assertRaises(exception.TriggerNotFound,
                          db.trigger_update,
                          self.ctxt, '100', {"type": "event"})

    def test_trigger_get(self):
        trigger_ref = self._create_trigger()
        trigger_ref = db.trigger_get(self.ctxt, trigger_ref['id'])
        self.assertEqual('time', trigger_ref['type'])


class ScheduledOperationTestCase(base.TestCase):
    """Test cases for scheduled_operations table."""

    def setUp(self):
        super(ScheduledOperationTestCase, self).setUp()
        self.ctxt = context.RequestContext(user_id='user_id',
                                           project_id='project_id')

    def _create_scheduled_operation(self):
        values = {
            'id': '0354ca9ddcd046b693340d78759fd274',
            'name': 'protect vm',
            'description': 'protect vm resource',
            'operation_type': 'protect',
            'user_id': self.ctxt.user_id,
            'project_id': self.ctxt.tenant,
            'trigger_id': '0354ca9ddcd046b693340d78759fd275',
            'operation_definition': '{}'
        }
        return db.scheduled_operation_create(self.ctxt, values)

    def test_scheduled_operation_create(self):
        operation_ref = self._create_scheduled_operation()
        self.assertEqual('protect', operation_ref['operation_type'])
        self.assertTrue(operation_ref['enabled'])

    def test_scheduled_operation_delete(self):
        operation_ref = self._create_scheduled_operation()
        db.scheduled_operation_delete(self.ctxt, operation_ref['id'])

        self.assertRaises(exception.ScheduledOperationNotFound,
                          db.scheduled_operation_delete,
                          self.ctxt, operation_ref['id'])

        self.assertRaises(exception.ScheduledOperationNotFound,
                          db.scheduled_operation_get,
                          self.ctxt, operation_ref['id'])

        self.assertRaises(exception.ScheduledOperationNotFound,
                          db.scheduled_operation_delete, self.ctxt, '100')

    def test_scheduled_operation_update(self):
        operation_ref = self._create_scheduled_operation()
        id = operation_ref['id']
        operation_ref = db.scheduled_operation_update(self.ctxt,
                                                      id,
                                                      {"name": "abc"})
        self.assertEqual('abc', operation_ref['name'])

        operation_ref = db.scheduled_operation_get(self.ctxt, id)
        self.assertEqual('abc', operation_ref['name'])

        self.assertRaises(exception.ScheduledOperationNotFound,
                          db.scheduled_operation_update,
                          self.ctxt, '100', {"name": "abc"})

    def test_scheduled_operation_get(self):
        operation_ref = self._create_scheduled_operation()
        operation_ref = db.scheduled_operation_get(self.ctxt,
                                                   operation_ref['id'])
        self.assertEqual('protect', operation_ref['operation_type'])

    def test_scheduled_operation_get_join_trigger(self):
        def _create_trigger():
            values = {
                'id': "0354ca9ddcd046b693340d78759fd275",
                'name': 'first trigger',
                'project_id': self.ctxt.tenant,
                'type': 'time',
                'properties': '{}',
            }
            return db.trigger_create(self.ctxt, values)

        trigger_ref = _create_trigger()
        operation_ref = self._create_scheduled_operation()
        operation_ref = db.scheduled_operation_get(
            self.ctxt,
            operation_ref['id'],
            ['trigger'])
        self.assertEqual('protect', operation_ref['operation_type'])
        self.assertEqual(trigger_ref['type'], operation_ref.trigger['type'])


class ScheduledOperationStateTestCase(base.TestCase):
    """Test cases for scheduled_operation_states table."""

    def setUp(self):
        super(ScheduledOperationStateTestCase, self).setUp()
        self.ctxt = context.RequestContext(user_id='user_id',
                                           project_id='project_id')

    def _create_scheduled_operation_state(self):
        values = {
            'operation_id': '0354ca9ddcd046b693340d78759fd274',
            'service_id': 1,
            'trust_id': '123',
            'state': 'init',
        }
        return db.scheduled_operation_state_create(self.ctxt, values)

    def test_scheduled_operation_state_create(self):
        state_ref = self._create_scheduled_operation_state()
        self.assertEqual('init', state_ref['state'])

    def test_scheduled_operation_state_delete(self):
        state_ref = self._create_scheduled_operation_state()
        db.scheduled_operation_state_delete(self.ctxt,
                                            state_ref['operation_id'])

        self.assertRaises(exception.ScheduledOperationStateNotFound,
                          db.scheduled_operation_state_delete,
                          self.ctxt, state_ref['operation_id'])

        self.assertRaises(exception.ScheduledOperationStateNotFound,
                          db.scheduled_operation_state_get,
                          self.ctxt, state_ref['operation_id'])

        self.assertRaises(exception.ScheduledOperationStateNotFound,
                          db.scheduled_operation_state_delete, self.ctxt, 100)

    def test_scheduled_operation_state_update(self):
        state_ref = self._create_scheduled_operation_state()
        operation_id = state_ref['operation_id']
        state_ref = db.scheduled_operation_state_update(self.ctxt,
                                                        operation_id,
                                                        {"state": "success"})
        self.assertEqual('success', state_ref['state'])

        state_ref = db.scheduled_operation_state_get(self.ctxt, operation_id)
        self.assertEqual('success', state_ref['state'])

        self.assertRaises(exception.ScheduledOperationStateNotFound,
                          db.scheduled_operation_state_update,
                          self.ctxt, '100', {"state": "success"})

    def test_scheduled_operation_state_get(self):
        state_ref = self._create_scheduled_operation_state()
        state_ref = db.scheduled_operation_state_get(self.ctxt,
                                                     state_ref['operation_id'])
        self.assertEqual('init', state_ref['state'])

    def test_scheduled_operation_state_get_join_operation(self):
        def _create_scheduled_operation():
            values = {
                'id': '0354ca9ddcd046b693340d78759fd274',
                'name': 'protect vm',
                'operation_type': 'protect',
                'user_id': self.ctxt.user_id,
                'project_id': self.ctxt.tenant,
                'trigger_id': '0354ca9ddcd046b693340d78759fd275',
                'operation_definition': '{}'
            }
            return db.scheduled_operation_create(self.ctxt, values)

        operation_ref = _create_scheduled_operation()
        self._create_scheduled_operation_state()
        state_ref = db.scheduled_operation_state_get(
            self.ctxt,
            operation_ref['id'],
            ['operation'])
        self.assertEqual(operation_ref['id'], state_ref.operation['id'])


class ScheduledOperationLogTestCase(base.TestCase):
    """Test cases for scheduled_operation_logs table."""

    def setUp(self):
        super(ScheduledOperationLogTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.operation_id = '0354ca9ddcd046b693340d78759fd274'

    def _create_scheduled_operation_log(self, state='in_progress',
                                        created_at=datetime.now()):
        values = {
            'operation_id': self.operation_id,
            'state': state,
            'created_at': created_at
        }
        return db.scheduled_operation_log_create(self.ctxt, values)

    def test_scheduled_operation_log_create(self):
        log_ref = self._create_scheduled_operation_log()
        self.assertEqual('in_progress', log_ref['state'])

    def test_scheduled_operation_log_delete(self):
        log_ref = self._create_scheduled_operation_log()
        db.scheduled_operation_log_delete(self.ctxt, log_ref['id'])

        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          db.scheduled_operation_log_delete,
                          self.ctxt, log_ref['id'])

        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          db.scheduled_operation_log_get,
                          self.ctxt, log_ref['id'])

        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          db.scheduled_operation_log_delete,
                          self.ctxt, 100)

    def test_scheduled_operation_log_delete_oldest(self):
        log_ids = []
        states = ['success', 'in_progress', 'success', 'success']
        for i in range(4):
            t = datetime.now() + timedelta(hours=i)
            log = self._create_scheduled_operation_log(
                states[i], t)
            log_ids.append(log['id'])

        db.scheduled_operation_log_delete_oldest(
            self.ctxt, self.operation_id, 3)
        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          db.scheduled_operation_log_get,
                          self.ctxt, log_ids[0])

        db.scheduled_operation_log_delete_oldest(
            self.ctxt, self.operation_id, 1, ['in_progress'])
        log_ref = db.scheduled_operation_log_get(self.ctxt, log_ids[1])
        self.assertEqual('in_progress', log_ref['state'])
        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          db.scheduled_operation_log_get,
                          self.ctxt, log_ids[2])

    def test_scheduled_operation_log_update(self):
        log_ref = self._create_scheduled_operation_log()
        log_id = log_ref['id']
        log_ref = db.scheduled_operation_log_update(self.ctxt,
                                                    log_id,
                                                    {"state": "success"})
        self.assertEqual('success', log_ref['state'])

        log_ref = db.scheduled_operation_log_get(self.ctxt, log_id)
        self.assertEqual('success', log_ref['state'])

        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          db.scheduled_operation_log_update,
                          self.ctxt, 100, {"state": "success"})

    def test_scheduled_operation_log_get(self):
        log_ref = self._create_scheduled_operation_log()
        log_ref = db.scheduled_operation_log_get(self.ctxt, log_ref['id'])
        self.assertEqual('in_progress', log_ref['state'])


class PlanDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.plan_*."""

    fake_plan = {
        'name': 'My 3 tier application',
        'description': 'My 3 tier application protection plan',
        'provider_id': 'efc6a88b-9096-4bb6-8634-cda182a6e12a',
        'status': 'suspended',
        'project_id': '39bb894794b741e982bd26144d2949f6',
        'resources': [],
        'parameters': '{OS::Nova::Server: {consistency: os}}'
    }

    fake_plan_with_resources = {
        'name': 'My 3 tier application',
        'description': 'My 3 tier application protection plan',
        'provider_id': 'efc6a88b-9096-4bb6-8634-cda182a6e12a',
        'status': 'suspended',
        'project_id': '39bb894794b741e982bd26144d2949f6',
        'resources': [{
            "id": "64e51e85-4f31-441f-9a5d-6e93e3196628",
            "type": "OS::Nova::Server",
            "name": "vm1"}],
        'parameters': '{OS::Nova::Server: {consistency: os}}'
    }

    def setUp(self):
        super(PlanDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def test_plan_create(self):
        plan = db.plan_create(self.ctxt, self.fake_plan)
        self.assertTrue(uuidutils.is_uuid_like(plan['id']))
        self.assertEqual('suspended', plan.status)

    def test_plan_get(self):
        plan = db.plan_create(self.ctxt,
                              self.fake_plan)
        self._assertEqualObjects(plan, db.plan_get(self.ctxt,
                                                   plan['id']),
                                 ignored_keys='resources')

    def test_plan_destroy(self):
        plan = db.plan_create(self.ctxt, self.fake_plan)
        db.plan_destroy(self.ctxt, plan['id'])
        self.assertRaises(exception.PlanNotFound, db.plan_get,
                          self.ctxt, plan['id'])

    def test_plan_update(self):
        plan = db.plan_create(self.ctxt, self.fake_plan)
        db.plan_update(self.ctxt, plan['id'],
                       {'status': 'started'})
        plan = db.plan_get(self.ctxt, plan['id'])
        self.assertEqual('started', plan['status'])

    def test_plan_update_nonexistent(self):
        self.assertRaises(exception.PlanNotFound, db.plan_update,
                          self.ctxt, 42, {})

    def test_plan_resources_update(self):
        resources2 = [{
            "id": "61e51e85-4f31-441f-9a5d-6e93e3194444",
            "type": "OS::Cinder::Volume",
            "name": "vm2",
            "extra_info": "{'availability_zone': 'az1'}"}]

        plan = db.plan_create(self.ctxt, self.fake_plan)
        db_meta = db.plan_resources_update(self.ctxt, plan["id"], resources2)

        self.assertEqual("OS::Cinder::Volume", db_meta[0]["resource_type"])
        self.assertEqual("vm2", db_meta[0]["resource_name"])
        self.assertEqual("{'availability_zone': 'az1'}",
                         db_meta[0]["resource_extra_info"])


class RestoreDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.restore_*."""

    fake_restore = {
        "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
        "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
        "provider_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
        "checkpoint_id": "09edcbdc-d1c2-49c1-a212-122627b20968",
        "restore_target": "192.168.1.2/identity/",
        "parameters": "{'username': 'admin'}",
        "status": "SUCCESS"
    }

    def setUp(self):
        super(RestoreDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def test_restore_create(self):
        restore = db.restore_create(self.ctxt, self.fake_restore)
        self.assertTrue(uuidutils.is_uuid_like(restore['id']))
        self.assertEqual('SUCCESS', restore.status)

    def test_restore_get(self):
        restore = db.restore_create(self.ctxt,
                                    self.fake_restore)
        self._assertEqualObjects(restore, db.restore_get(self.ctxt,
                                                         restore['id']))

    def test_restore_destroy(self):
        restore = db.restore_create(self.ctxt, self.fake_restore)
        db.restore_destroy(self.ctxt, restore['id'])
        self.assertRaises(exception.RestoreNotFound, db.restore_get,
                          self.ctxt, restore['id'])

    def test_restore_update(self):
        restore = db.restore_create(self.ctxt, self.fake_restore)
        db.restore_update(self.ctxt, restore['id'],
                          {'status': 'INIT'})
        restore = db.restore_get(self.ctxt, restore['id'])
        self.assertEqual('INIT', restore['status'])

    def test_restore_update_nonexistent(self):
        self.assertRaises(exception.RestoreNotFound, db.restore_update,
                          self.ctxt, 42, {})


class VerificationDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.verification_*."""

    fake_verification = {
        "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
        "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
        "provider_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
        "checkpoint_id": "09edcbdc-d1c2-49c1-a212-122627b20968",
        "parameters": "{'username': 'admin'}",
        "status": "SUCCESS"
    }

    def setUp(self):
        super(VerificationDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def test_verification_create(self):
        verification = db.verification_create(self.ctxt,
                                              self.fake_verification)
        self.assertTrue(uuidutils.is_uuid_like(verification['id']))
        self.assertEqual('SUCCESS', verification.status)

    def test_verification_get(self):
        verification = db.verification_create(self.ctxt,
                                              self.fake_verification)
        self._assertEqualObjects(verification, db.verification_get(
            self.ctxt, verification['id']))

    def test_verification_destroy(self):
        verification = db.verification_create(self.ctxt,
                                              self.fake_verification)
        db.verification_destroy(self.ctxt, verification['id'])
        self.assertRaises(exception.VerificationNotFound,
                          db.verification_get,
                          self.ctxt, verification['id'])

    def test_verification_update(self):
        verification = db.verification_create(self.ctxt,
                                              self.fake_verification)
        db.verification_update(self.ctxt, verification['id'],
                               {'status': 'INIT'})
        verification = db.verification_get(self.ctxt, verification['id'])
        self.assertEqual('INIT', verification['status'])

    def test_verification_update_nonexistent(self):
        self.assertRaises(exception.VerificationNotFound,
                          db.verification_update,
                          self.ctxt, 42, {})


class OperationLogTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.operation_log_*."""

    fake_operation_log = {
        "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
        "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
        "operation_type": "protect",
        "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
        "plan_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
        "provider_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
        "scheduled_operation_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
        "status": "failed",
        "error_info": "Could not access bank",
        "extra_info": "[entries:{'timestamp': '2015-08-27T09:50:51-05:00',"
                   "'message': 'Doing things'}]"
    }

    def setUp(self):
        super(OperationLogTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def test_operation_log_create(self):
        operation_log = db.operation_log_create(self.ctxt,
                                                self.fake_operation_log)
        self.assertTrue(uuidutils.is_uuid_like(operation_log['id']))
        self.assertEqual('failed', operation_log.status)

    def test_operation_log_get(self):
        operation_log = db.operation_log_create(self.ctxt,
                                                self.fake_operation_log)
        self._assertEqualObjects(operation_log, db.operation_log_get(
            self.ctxt, operation_log['id']))

    def test_operation_log_destroy(self):
        operation_log = db.operation_log_create(self.ctxt,
                                                self.fake_operation_log)
        db.operation_log_destroy(self.ctxt, operation_log['id'])
        self.assertRaises(exception.OperationLogNotFound, db.operation_log_get,
                          self.ctxt, operation_log['id'])

    def test_operation_log_update(self):
        operation_log = db.operation_log_create(self.ctxt,
                                                self.fake_operation_log)
        db.operation_log_update(self.ctxt, operation_log['id'],
                                {'status': 'finished'})
        operation_log = db.operation_log_get(self.ctxt, operation_log['id'])
        self.assertEqual('finished', operation_log['status'])

    def test_operation_log_update_nonexistent(self):
        self.assertRaises(exception.OperationLogNotFound,
                          db.operation_log_update,
                          self.ctxt, 42, {})


class CheckpointRecordTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.checkpoint_record_*."""

    fake_checkpoint_record = {
        "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
        "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
        "checkpoint_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
        "checkpoint_status": "available",
        "provider_id": "39bb894794b741e982bd26144d2949f6",
        "plan_id": "efc6a88b-9096-4bb6-8634-cda182a6e12b",
        "operation_id": "64e51e85-4f31-441f-9a5d-6e93e3196628",
        "create_by": "operation-engine",
        "extend_info": "[{"
                       "'id': '0354ca9d-dcd0-46b6-9334-0d78759fd275',"
                       "'type': 'OS::Nova::Server',"
                       "'name': 'vm1'"
                        "}]"
    }

    def setUp(self):
        super(CheckpointRecordTestCase, self).setUp()
        self.ctxt = context.get_admin_context()

    def test_checkpoint_record_create(self):
        checkpoint_record = db.checkpoint_record_create(
            self.ctxt,
            self.fake_checkpoint_record)
        self.assertTrue(uuidutils.is_uuid_like(checkpoint_record['id']))
        self.assertEqual('available', checkpoint_record.checkpoint_status)

    def test_checkpoint_record_get(self):
        checkpoint_record = db.checkpoint_record_create(
            self.ctxt,
            self.fake_checkpoint_record)
        self._assertEqualObjects(checkpoint_record, db.checkpoint_record_get(
            self.ctxt, checkpoint_record['id']))

    def test_checkpoint_record_destroy(self):
        checkpoint_record = db.checkpoint_record_create(
            self.ctxt,
            self.fake_checkpoint_record)
        db.checkpoint_record_destroy(self.ctxt, checkpoint_record['id'])
        self.assertRaises(exception.CheckpointRecordNotFound,
                          db.checkpoint_record_get,
                          self.ctxt, checkpoint_record['id'])

    def test_checkpoint_record_update(self):
        checkpoint_record = db.checkpoint_record_create(
            self.ctxt,
            self.fake_checkpoint_record)
        db.checkpoint_record_update(self.ctxt,
                                    checkpoint_record['id'],
                                    {'checkpoint_status': 'error'})
        checkpoint_record = db.checkpoint_record_get(
            self.ctxt,
            checkpoint_record['id'])
        self.assertEqual('error', checkpoint_record['checkpoint_status'])

    def test_checkpoint_record_update_nonexistent(self):
        self.assertRaises(exception.CheckpointRecordNotFound,
                          db.checkpoint_record_update,
                          self.ctxt, 42, {})


class QuotaDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.quota_*."""

    def setUp(self):
        super(QuotaDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.project_id = "586cc6ce-e286-40bd-b2b5-dd32694d9944"
        self.resource = "volume_backups"
        self.limit = 10

    def test_quota_create(self):
        quota = db.quota_create(self.ctxt, self.project_id,
                                self.resource, self.limit)
        self.assertEqual("volume_backups", quota.resource)
        db.quota_destroy(self.ctxt, self.project_id, self.resource)

    def test_quota_get(self):
        quota = db.quota_create(self.ctxt, self.project_id,
                                self.resource, self.limit)
        self._assertEqualObjects(quota, db.quota_get(
            self.ctxt, quota.project_id, quota.resource))
        db.quota_destroy(self.ctxt, self.project_id, self.resource)

    def test_quota_destroy(self):
        quota = db.quota_create(self.ctxt, self.project_id,
                                self.resource, self.limit)
        db.quota_destroy(self.ctxt, quota.project_id, quota.resource)
        self.assertRaises(exception.ProjectQuotaNotFound, db.quota_get,
                          self.ctxt, quota.project_id, quota.resource)

    def test_quota_update(self):
        quota = db.quota_create(self.ctxt, self.project_id,
                                self.resource, self.limit)
        db.quota_update(self.ctxt, quota.project_id, quota.resource,
                        20)
        quota = db.quota_get(self.ctxt, self.project_id, self.resource)
        self.assertEqual(20, quota.hard_limit)


class QuotaClassDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.quota_class_*."""

    def setUp(self):
        super(QuotaClassDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.class_name = "default"
        self.resource = "volume_backups"
        self.limit = 10

    def test_quota_class_create(self):
        quota_class = db.quota_class_create(self.ctxt, self.class_name,
                                            self.resource, self.limit)
        self.assertEqual("volume_backups", quota_class.resource)
        db.quota_class_destroy(self.ctxt, self.class_name, self.resource)

    def test_quota_class_get(self):
        quota_class = db.quota_class_create(self.ctxt, self.class_name,
                                            self.resource, self.limit)
        self._assertEqualObjects(quota_class, db.quota_class_get(
            self.ctxt, quota_class.class_name, quota_class.resource))
        db.quota_class_destroy(self.ctxt, self.class_name, self.resource)

    def test_quota_class_destroy(self):
        quota_class = db.quota_class_create(self.ctxt, self.class_name,
                                            self.resource, self.limit)
        db.quota_class_destroy(self.ctxt, self.class_name, self.resource)
        self.assertRaises(exception.QuotaClassNotFound, db.quota_class_get,
                          self.ctxt, quota_class.class_name,
                          quota_class.resource)

    def test_quota_class_update(self):
        quota_class = db.quota_class_create(self.ctxt, self.class_name,
                                            self.resource, self.limit)
        db.quota_class_update(self.ctxt, quota_class.class_name,
                              quota_class.resource, 20)
        quota_class = db.quota_class_get(self.ctxt, self.class_name,
                                         self.resource)
        self.assertEqual(20, quota_class.hard_limit)


class QuotaUsageDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.quota_usage_*."""

    def setUp(self):
        super(QuotaUsageDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.project_id = "586cc6ce-e286-40bd-b2b5-dd32694d9944"
        self.resource = "volume_backups"
        self.in_use = 10
        self.reserved = 10
        self.until_refresh = 0

    def test_quota_usage_create(self):
        quota_usage = db.quota_usage_create(
            self.ctxt, self.project_id, "volume_backups", self.in_use,
            self.reserved, self.until_refresh)
        self.assertEqual("volume_backups", quota_usage.resource)

    def test_quota_usage_get(self):
        quota_usage = db.quota_usage_create(
            self.ctxt, self.project_id, "volume_backups_get", self.in_use,
            self.reserved, self.until_refresh)
        self._assertEqualObjects(quota_usage, db.quota_usage_get(
            self.ctxt, self.project_id, "volume_backups_get"))


class ReservationDbTestCase(ModelBaseTestCase):
    """Unit tests for karbor.db.api.reservation_*."""

    def setUp(self):
        super(ReservationDbTestCase, self).setUp()
        self.ctxt = context.get_admin_context()
        self.project_id = "586cc6ce-e286-40bd-b2b5-dd32694d9944"
        self.resource = "volume_backups"
        self.in_use = 10
        self.reserved = 10
        self.until_refresh = 0

    def test_reservation_create(self):
        quota_usage = db.quota_usage_create(
            self.ctxt, self.project_id, "volume_backups", self.in_use,
            self.reserved, self.until_refresh)
        reservation = db.reservation_create(
            self.ctxt, str(uuid.uuid4()), quota_usage,
            self.project_id, "volume_backups", 1,
            timeutils.utcnow())
        self.assertEqual("volume_backups", quota_usage.resource)
        self.assertEqual("volume_backups", reservation.resource)

    def test_reservation_get(self):
        quota_usage = db.quota_usage_create(
            self.ctxt, self.project_id, "volume_backups_get", self.in_use,
            self.reserved, self.until_refresh)
        reservation = db.reservation_create(
            self.ctxt, str(uuid.uuid4()), quota_usage,
            self.project_id, "volume_backups_get", 1,
            timeutils.utcnow())
        self._assertEqualObjects(reservation, db.reservation_get(
            self.ctxt, reservation.uuid))
