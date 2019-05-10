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

"""The notification module."""
from mock import Mock
from mock import patch

from karbor.common import notification
from karbor.common.notification import EndNotification
from karbor.common.notification import StartNotification
from karbor import context
from karbor import exception
from karbor import rpc
from karbor.tests import base


class TestEndNotification(base.TestCase):

    def setUp(self):
        super(TestEndNotification, self).setUp()
        self.context = KarborTestContext(self)

    def test_call(self):
        with patch.object(self.context, "notification") as notification:
            with EndNotification(self.context):
                pass
            self.assertTrue(notification.notify_end.called)

    def server_exception(self, server_type):
        with patch.object(self.context, "notification") as notification:
            try:
                with EndNotification(self.context):
                    raise exception.InvalidInput
            except Exception:
                self.assertTrue(notification.notify_exc_info.called)


class KarborTestContext(context.RequestContext):

    def __init__(self, test_case, **kwargs):
        super(KarborTestContext, self).__init__(user_id='demo',
                                                project_id='abcd',
                                                auth_token='efgh')
        self.notification = KarborTestNotification(
            self, request_id='req_id')


class TestStartNotification(base.TestCase):

    def setUp(self):
        super(TestStartNotification, self).setUp()
        self.context = KarborTestContext(self)

    def test_call(self):
        with patch.object(self.context, "notification") as notification:
            with StartNotification(self.context):
                pass
            self.assertTrue(notification.notify_start.called)


class KarborTestNotification(notification.KaborAPINotification):

    def event_type(self):
        return 'plan_test'

    def required_start_traits(self):
        return ['name']

    def optional_start_traits(self):
        return ['parameters']

    def required_end_traits(self):
        return ['name']


class TestKarborNotification(base.TestCase):

    def setUp(self):
        super(TestKarborNotification, self).setUp()
        self.test_n = KarborTestNotification(Mock(), request=Mock())

    def test_missing_required_start_traits(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               self.test_n.required_start_traits()[0],
                               self.test_n.notify_start)

    def test_invalid_start_traits(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               "The following required keys",
                               self.test_n.notify_start, foo='bar')

    def test_missing_required_end_traits(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               self.test_n.required_end_traits()[0],
                               self.test_n.notify_end)

    def test_invalid_end_traits(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               "The following required keys",
                               self.test_n.notify_end, foo='bar')

    def test_missing_required_error_traits(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               self.test_n.required_error_traits()[0],
                               self.test_n._notify, 'error',
                               self.test_n.required_error_traits(), [])

    @patch.object(rpc, 'get_notifier')
    def test_start_event(self, notifier):
        self.test_n.notify_start(name='foo')
        self.assertTrue(notifier().info.called)
        a, _ = notifier().info.call_args
        self.assertEqual('karbor.plan_test.start', a[1])

    @patch.object(rpc, 'get_notifier')
    def test_end_event(self, notifier):
        self.test_n.notify_end(name='foo')
        self.assertTrue(notifier().info.called)
        a, _ = notifier().info.call_args
        self.assertEqual('karbor.plan_test.end', a[1])

    @patch.object(rpc, 'get_notifier')
    def test_verify_base_values(self, notifier):
        self.test_n.notify_start(name='foo')
        self.assertTrue(notifier().info.called)
        a, _ = notifier().info.call_args
        payload = a[2]
        self.assertIn('client_ip', payload)
        self.assertIn('request_id', payload)
        self.assertIn('tenant_id', payload)

    @patch.object(rpc, 'get_notifier')
    def test_verify_required_start_args(self, notifier):
        self.test_n.notify_start(name='foo')
        self.assertTrue(notifier().info.called)
        a, _ = notifier().info.call_args
        payload = a[2]
        self.assertIn('name', payload)

    @patch.object(rpc, 'get_notifier')
    def test_verify_optional_start_args(self, notifier):
        self.test_n.notify_start(name='foo', parameters="test")
        self.assertTrue(notifier().info.called)
        a, _ = notifier().info.call_args
        payload = a[2]
        self.assertIn('parameters', payload)

    @patch.object(rpc, 'get_notifier')
    def test_verify_required_end_args(self, notifier):
        self.test_n.notify_end(name='foo')
        self.assertTrue(notifier().info.called)
        a, _ = notifier().info.call_args
        payload = a[2]
        self.assertIn('name', payload)

    def _test_notify_callback(self, fn, *args, **kwargs):
        with patch.object(rpc, 'get_notifier') as notifier:
            mock_callback = Mock()
            self.test_n.register_notify_callback(mock_callback)
            mock_context = Mock()
            mock_context.notification = Mock()
            self.test_n.context = mock_context
            fn(*args, **kwargs)
            self.assertTrue(notifier().info.called)
            self.assertTrue(mock_callback.called)
            self.test_n.register_notify_callback(None)

    def test_notify_callback(self):
        required_keys = {
            'name': 'name',
            'parameters': 'parameters',
        }
        self._test_notify_callback(self.test_n.notify_start,
                                   **required_keys)
        self._test_notify_callback(self.test_n.notify_end,
                                   **required_keys)
        self._test_notify_callback(self.test_n.notify_exc_info,
                                   'error', 'exc')
