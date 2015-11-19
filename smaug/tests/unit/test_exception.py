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

from smaug import exception
from smaug.tests import base

import mock
import six
import webob.util


class SmaugExceptionTestCase(base.TestCase):
    def test_default_error_msg(self):
        class FakeSmaugException(exception.SmaugException):
            message = "default message"

        exc = FakeSmaugException()
        self.assertEqual('default message', six.text_type(exc))

    def test_error_msg(self):
        self.assertEqual('test',
                         six.text_type(exception.SmaugException('test')))

    def test_default_error_msg_with_kwargs(self):
        class FakeSmaugException(exception.SmaugException):
            message = "default message: %(code)s"

        exc = FakeSmaugException(code=500)
        self.assertEqual('default message: 500', six.text_type(exc))

    def test_error_msg_exception_with_kwargs(self):
        # NOTE(dprince): disable format errors for this test
        self.flags(fatal_exception_format_errors=False)

        class FakeSmaugException(exception.SmaugException):
            message = "default message: %(misspelled_code)s"

        exc = FakeSmaugException(code=500)
        self.assertEqual('default message: %(misspelled_code)s',
                         six.text_type(exc))

    def test_default_error_code(self):
        class FakeSmaugException(exception.SmaugException):
            code = 404

        exc = FakeSmaugException()
        self.assertEqual(404, exc.kwargs['code'])

    def test_error_code_from_kwarg(self):
        class FakeSmaugException(exception.SmaugException):
            code = 500

        exc = FakeSmaugException(code=404)
        self.assertEqual(404, exc.kwargs['code'])

    def test_error_msg_is_exception_to_string(self):
        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = exception.SmaugException(exc1)
        self.assertEqual(msg, exc2.msg)

    def test_exception_kwargs_to_string(self):
        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = exception.SmaugException(kwarg1=exc1)
        self.assertEqual(msg, exc2.kwargs['kwarg1'])

    def test_message_in_format_string(self):
        class FakeSmaugException(exception.SmaugException):
            message = 'FakeSmaugException: %(message)s'

        exc = FakeSmaugException(message='message')
        self.assertEqual('FakeSmaugException: message', six.text_type(exc))

    def test_message_and_kwarg_in_format_string(self):
        class FakeSmaugException(exception.SmaugException):
            message = 'Error %(code)d: %(message)s'

        exc = FakeSmaugException(message='message', code=404)
        self.assertEqual('Error 404: message', six.text_type(exc))

    def test_message_is_exception_in_format_string(self):
        class FakeSmaugException(exception.SmaugException):
            message = 'Exception: %(message)s'

        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = FakeSmaugException(message=exc1)
        self.assertEqual('Exception: test message', six.text_type(exc2))


class SmaugConvertedExceptionTestCase(base.TestCase):
    def test_default_args(self):
        exc = exception.ConvertedException()
        self.assertNotEqual('', exc.title)
        self.assertEqual(500, exc.code)
        self.assertEqual('', exc.explanation)

    def test_standard_status_code(self):
        with mock.patch.dict(webob.util.status_reasons, {200: 'reason'}):
            exc = exception.ConvertedException(code=200)
            self.assertEqual('reason', exc.title)

    @mock.patch.dict(webob.util.status_reasons, {500: 'reason'})
    def test_generic_status_code(self):
        with mock.patch.dict(webob.util.status_generic_reasons,
                             {5: 'generic_reason'}):
            exc = exception.ConvertedException(code=599)
            self.assertEqual('generic_reason', exc.title)
