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

from six.moves import http_client

from karbor import exception
from karbor.tests import base

import mock
import six
import webob.util


class KarborExceptionTestCase(base.TestCase):
    def test_default_error_msg(self):
        class FakeKarborException(exception.KarborException):
            message = "default message"

        exc = FakeKarborException()
        self.assertEqual('default message', six.text_type(exc))

    def test_error_msg(self):
        self.assertEqual('test',
                         six.text_type(exception.KarborException('test')))

    def test_default_error_msg_with_kwargs(self):
        class FakeKarborException(exception.KarborException):
            message = "default message: %(code)s"

        exc = FakeKarborException(code=500)
        self.assertEqual('default message: 500', six.text_type(exc))

    def test_error_msg_exception_with_kwargs(self):
        # NOTE(dprince): disable format errors for this test
        self.flags(fatal_exception_format_errors=False)

        class FakeKarborException(exception.KarborException):
            message = "default message: %(misspelled_code)s"

        exc = FakeKarborException(code=http_client.INTERNAL_SERVER_ERROR)
        self.assertEqual('default message: %(misspelled_code)s',
                         six.text_type(exc))

    def test_default_error_code(self):
        class FakeKarborException(exception.KarborException):
            code = http_client.NOT_FOUND

        exc = FakeKarborException()
        self.assertEqual(http_client.NOT_FOUND, exc.kwargs['code'])

    def test_error_code_from_kwarg(self):
        class FakeKarborException(exception.KarborException):
            code = http_client.INTERNAL_SERVER_ERROR

        exc = FakeKarborException(code=http_client.NOT_FOUND)
        self.assertEqual(http_client.NOT_FOUND, exc.kwargs['code'])

    def test_error_msg_is_exception_to_string(self):
        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = exception.KarborException(exc1)
        self.assertEqual(msg, exc2.msg)

    def test_message_in_format_string(self):
        class FakeKarborException(exception.KarborException):
            message = 'FakeKarborException: %(message)s'

        exc = FakeKarborException(message='message')
        self.assertEqual('message', six.text_type(exc))

    def test_message_and_kwarg_in_format_string(self):
        class FakeKarborException(exception.KarborException):
            message = 'Error %(code)d: %(msg)s'

        exc = FakeKarborException(code=http_client.NOT_FOUND, msg='message')
        self.assertEqual('Error 404: message', six.text_type(exc))


class KarborConvertedExceptionTestCase(base.TestCase):
    def test_default_args(self):
        exc = exception.ConvertedException()
        self.assertNotEqual('', exc.title)
        self.assertEqual(http_client.INTERNAL_SERVER_ERROR, exc.code)
        self.assertEqual('', exc.explanation)

    def test_standard_status_code(self):
        with mock.patch.dict(webob.util.status_reasons, {200: 'reason'}):
            exc = exception.ConvertedException(code=200)
            self.assertEqual('reason', exc.title)

    @mock.patch.dict(webob.util.status_reasons,
                     {http_client.INTERNAL_SERVER_ERROR: 'reason'})
    def test_generic_status_code(self):
        with mock.patch.dict(webob.util.status_generic_reasons,
                             {5: 'generic_reason'}):
            exc = exception.ConvertedException(code=599)
            self.assertEqual('generic_reason', exc.title)
