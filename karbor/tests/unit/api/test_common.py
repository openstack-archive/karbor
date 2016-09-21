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

"""
Test suites for 'common' code used throughout the OpenStack HTTP API.
"""

import mock
from testtools import matchers
import webob
import webob.exc

from oslo_config import cfg

from karbor.api import common
from karbor.tests import base


NS = "{http://docs.openstack.org/compute/api/v1.1}"
ATOMNS = "{http://www.w3.org/2005/Atom}"
CONF = cfg.CONF


class PaginationParamsTest(base.TestCase):
    """Unit tests for `karbor.api.common.get_pagination_params` method.

    This method takes in a request object and returns 'marker' and 'limit'
    GET params.
    """

    def test_nonnumerical_limit(self):
        """Test nonnumerical limit param."""
        req = webob.Request.blank('/?limit=hello')
        self.assertRaises(
            webob.exc.HTTPBadRequest, common.get_pagination_params,
            req.GET.copy())

    @mock.patch.object(common, 'CONF')
    def test_no_params(self, mock_cfg):
        """Test no params."""
        mock_cfg.osapi_max_limit = 100
        req = webob.Request.blank('/')
        expected = (None, 100, 0)
        self.assertEqual(expected,
                         common.get_pagination_params(req.GET.copy()))

    def test_valid_marker(self):
        """Test valid marker param."""
        marker = '263abb28-1de6-412f-b00b-f0ee0c4333c2'
        req = webob.Request.blank('/?marker=' + marker)
        expected = (marker, CONF.osapi_max_limit, 0)
        self.assertEqual(expected,
                         common.get_pagination_params(req.GET.copy()))

    def test_valid_limit(self):
        """Test valid limit param."""
        req = webob.Request.blank('/?limit=10')
        expected = (None, 10, 0)
        self.assertEqual(expected,
                         common.get_pagination_params(req.GET.copy()))

    def test_invalid_limit(self):
        """Test invalid limit param."""
        req = webob.Request.blank('/?limit=-2')
        self.assertRaises(
            webob.exc.HTTPBadRequest, common.get_pagination_params,
            req.GET.copy())

    def test_valid_limit_and_marker(self):
        """Test valid limit and marker parameters."""
        marker = '263abb28-1de6-412f-b00b-f0ee0c4333c2'
        req = webob.Request.blank('/?limit=20&marker=%s' % marker)
        expected = (marker, 20, 0)
        self.assertEqual(expected,
                         common.get_pagination_params(req.GET.copy()))


class SortParamUtilsTest(base.TestCase):

    def test_get_sort_params_defaults(self):
        """Verifies the default sort key and direction."""
        sort_keys, sort_dirs = common.get_sort_params({})
        self.assertEqual(['created_at'], sort_keys)
        self.assertEqual(['desc'], sort_dirs)

    def test_get_sort_params_override_defaults(self):
        """Verifies that the defaults can be overridden."""
        sort_keys, sort_dirs = common.get_sort_params({}, default_key='key1',
                                                      default_dir='dir1')
        self.assertEqual(['key1'], sort_keys)
        self.assertEqual(['dir1'], sort_dirs)

    def test_get_sort_params_single_value_sort_param(self):
        """Verifies a single sort key and direction."""
        params = {'sort': 'key1:dir1'}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1'], sort_keys)
        self.assertEqual(['dir1'], sort_dirs)

    def test_get_sort_params_single_value_old_params(self):
        """Verifies a single sort key and direction."""
        params = {'sort_key': 'key1', 'sort_dir': 'dir1'}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1'], sort_keys)
        self.assertEqual(['dir1'], sort_dirs)

    def test_get_sort_params_single_with_default_sort_param(self):
        """Verifies a single sort value with a default direction."""
        params = {'sort': 'key1'}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1'], sort_keys)
        # Direction should be defaulted
        self.assertEqual(['desc'], sort_dirs)

    def test_get_sort_params_single_with_default_old_params(self):
        """Verifies a single sort value with a default direction."""
        params = {'sort_key': 'key1'}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1'], sort_keys)
        # Direction should be defaulted
        self.assertEqual(['desc'], sort_dirs)

    def test_get_sort_params_multiple_values(self):
        """Verifies multiple sort parameter values."""
        params = {'sort': 'key1:dir1,key2:dir2,key3:dir3'}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1', 'key2', 'key3'], sort_keys)
        self.assertEqual(['dir1', 'dir2', 'dir3'], sort_dirs)

    def test_get_sort_params_multiple_not_all_dirs(self):
        """Verifies multiple sort keys without all directions."""
        params = {'sort': 'key1:dir1,key2,key3:dir3'}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1', 'key2', 'key3'], sort_keys)
        # Second key is missing the direction, should be defaulted
        self.assertEqual(['dir1', 'desc', 'dir3'], sort_dirs)

    def test_get_sort_params_multiple_override_default_dir(self):
        """Verifies multiple sort keys and overriding default direction."""
        params = {'sort': 'key1:dir1,key2,key3'}
        sort_keys, sort_dirs = common.get_sort_params(params,
                                                      default_dir='foo')
        self.assertEqual(['key1', 'key2', 'key3'], sort_keys)
        self.assertEqual(['dir1', 'foo', 'foo'], sort_dirs)

    def test_get_sort_params_params_modified(self):
        """Verifies that the input sort parameter are modified."""
        params = {'sort': 'key1:dir1,key2:dir2,key3:dir3'}
        common.get_sort_params(params)
        self.assertEqual({}, params)

        params = {'sort_key': 'key1', 'sort_dir': 'dir1'}
        common.get_sort_params(params)
        self.assertEqual({}, params)

    def test_get_sort_params_random_spaces(self):
        """Verifies that leading and trailing spaces are removed."""
        params = {'sort': ' key1 : dir1,key2: dir2 , key3 '}
        sort_keys, sort_dirs = common.get_sort_params(params)
        self.assertEqual(['key1', 'key2', 'key3'], sort_keys)
        self.assertEqual(['dir1', 'dir2', 'desc'], sort_dirs)

    def test_get_params_mix_sort_and_old_params(self):
        """An exception is raised if both types of sorting params are given."""
        for params in ({'sort': 'k1', 'sort_key': 'k1'},
                       {'sort': 'k1', 'sort_dir': 'd1'},
                       {'sort': 'k1', 'sort_key': 'k1', 'sort_dir': 'd2'}):
            self.assertRaises(webob.exc.HTTPBadRequest,
                              common.get_sort_params,
                              params)


class MiscFunctionsTest(base.TestCase):

    def test_remove_major_version_from_href(self):
        fixture = 'http://www.testsite.com/v1/images'
        expected = 'http://www.testsite.com/images'
        actual = common.remove_version_from_href(fixture)
        self.assertEqual(expected, actual)

    def test_remove_version_from_href(self):
        fixture = 'http://www.testsite.com/v1.1/images'
        expected = 'http://www.testsite.com/images'
        actual = common.remove_version_from_href(fixture)
        self.assertEqual(expected, actual)

    def test_remove_version_from_href_2(self):
        fixture = 'http://www.testsite.com/v1.1/'
        expected = 'http://www.testsite.com/'
        actual = common.remove_version_from_href(fixture)
        self.assertEqual(expected, actual)

    def test_remove_version_from_href_3(self):
        fixture = 'http://www.testsite.com/v10.10'
        expected = 'http://www.testsite.com'
        actual = common.remove_version_from_href(fixture)
        self.assertEqual(expected, actual)

    def test_remove_version_from_href_4(self):
        fixture = 'http://www.testsite.com/v1.1/images/v10.5'
        expected = 'http://www.testsite.com/images/v10.5'
        actual = common.remove_version_from_href(fixture)
        self.assertEqual(expected, actual)

    def test_remove_version_from_href_bad_request(self):
        fixture = 'http://www.testsite.com/1.1/images'
        self.assertRaises(ValueError,
                          common.remove_version_from_href,
                          fixture)

    def test_remove_version_from_href_bad_request_2(self):
        fixture = 'http://www.testsite.com/v/images'
        self.assertRaises(ValueError,
                          common.remove_version_from_href,
                          fixture)

    def test_remove_version_from_href_bad_request_3(self):
        fixture = 'http://www.testsite.com/v1.1images'
        self.assertRaises(ValueError,
                          common.remove_version_from_href,
                          fixture)


class TestCollectionLinks(base.TestCase):
    """Tests the _get_collection_links method."""

    def _validate_next_link(self, item_count, osapi_max_limit, limit,
                            should_link_exist):
        req = webob.Request.blank('/?limit=%s' % limit if limit else '/')
        link_return = [{"rel": "next", "href": "fake_link"}]
        self.flags(osapi_max_limit=osapi_max_limit)
        if limit is None:
            limited_list_size = min(item_count, osapi_max_limit)
        else:
            limited_list_size = min(item_count, osapi_max_limit, limit)
        limited_list = [{"uuid": str(i)} for i in range(limited_list_size)]
        builder = common.ViewBuilder()

        def get_pagination_params(params, max_limit=CONF.osapi_max_limit,
                                  original_call=common.get_pagination_params):
            return original_call(params, max_limit)

        def _get_limit_param(params, max_limit=CONF.osapi_max_limit,
                             original_call=common._get_limit_param):
            return original_call(params, max_limit)

        with mock.patch.object(common, 'get_pagination_params',
                               get_pagination_params), \
                mock.patch.object(common, '_get_limit_param',
                                  _get_limit_param), \
                mock.patch.object(common.ViewBuilder, '_generate_next_link',
                                  return_value=link_return) as href_link_mock:
            results = builder._get_collection_links(req, limited_list,
                                                    mock.sentinel.coll_key,
                                                    item_count, "uuid")
        if should_link_exist:
            href_link_mock.assert_called_once_with(limited_list, "uuid",
                                                   req,
                                                   mock.sentinel.coll_key)
            self.assertThat(results, matchers.HasLength(1))
        else:
            self.assertFalse(href_link_mock.called)
            self.assertThat(results, matchers.HasLength(0))

    def test_items_equals_osapi_max_no_limit(self):
        item_count = 5
        osapi_max_limit = 5
        limit = None
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_equals_osapi_max_greater_than_limit(self):
        item_count = 5
        osapi_max_limit = 5
        limit = 4
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_equals_osapi_max_equals_limit(self):
        item_count = 5
        osapi_max_limit = 5
        limit = 5
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_equals_osapi_max_less_than_limit(self):
        item_count = 5
        osapi_max_limit = 5
        limit = 6
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_less_than_osapi_max_no_limit(self):
        item_count = 5
        osapi_max_limit = 7
        limit = None
        should_link_exist = False
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_limit_less_than_items_less_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 7
        limit = 4
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_limit_equals_items_less_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 7
        limit = 5
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_less_than_limit_less_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 7
        limit = 6
        should_link_exist = False
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_less_than_osapi_max_equals_limit(self):
        item_count = 5
        osapi_max_limit = 7
        limit = 7
        should_link_exist = False
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_less_than_osapi_max_less_than_limit(self):
        item_count = 5
        osapi_max_limit = 7
        limit = 8
        should_link_exist = False
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_greater_than_osapi_max_no_limit(self):
        item_count = 5
        osapi_max_limit = 3
        limit = None
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_limit_less_than_items_greater_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 3
        limit = 2
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_greater_than_osapi_max_equals_limit(self):
        item_count = 5
        osapi_max_limit = 3
        limit = 3
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_greater_than_limit_greater_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 3
        limit = 4
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_items_equals_limit_greater_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 3
        limit = 5
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)

    def test_limit_greater_than_items_greater_than_osapi_max(self):
        item_count = 5
        osapi_max_limit = 3
        limit = 6
        should_link_exist = True
        self._validate_next_link(item_count, osapi_max_limit, limit,
                                 should_link_exist)


class LinkPrefixTest(base.TestCase):
    def test_update_link_prefix(self):
        vb = common.ViewBuilder()
        result = vb._update_link_prefix("http://192.168.0.243:24/",
                                        "http://127.0.0.1/volume")
        self.assertEqual("http://127.0.0.1/volume", result)

        result = vb._update_link_prefix("http://foo.x.com/v1",
                                        "http://new.prefix.com")
        self.assertEqual("http://new.prefix.com/v1", result)

        result = vb._update_link_prefix(
            "http://foo.x.com/v1",
            "http://new.prefix.com:20455/new_extra_prefix")
        self.assertEqual("http://new.prefix.com:20455/new_extra_prefix/v1",
                         result)


class RequestUrlTest(base.TestCase):
    def test_get_request_url_no_forward(self):
        app_url = 'http://127.0.0.1/v2;param?key=value#frag'
        request = type('', (), {
            'application_url': app_url,
            'headers': {}
        })
        result = common.get_request_url(request)
        self.assertEqual(app_url, result)

    def test_get_request_url_forward(self):
        request = type('', (), {
            'application_url': 'http://127.0.0.1/v2;param?key=value#frag',
            'headers': {'X-Forwarded-Host': '192.168.0.243:24'}
        })
        result = common.get_request_url(request)
        self.assertEqual('http://192.168.0.243:24/v2;param?key=value#frag',
                         result)
