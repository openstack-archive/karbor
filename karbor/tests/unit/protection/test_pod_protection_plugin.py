# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection import client_factory
from karbor.services.protection.clients import k8s

from karbor.services.protection.protection_plugins. \
    pod.pod_protection_plugin import PodProtectionPlugin
from karbor.services.protection.protection_plugins.pod \
    import pod_plugin_schemas

from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_pod_status import V1PodStatus

from karbor.tests import base
import mock
from oslo_config import cfg
from oslo_config import fixture


class FakeBankPlugin(BankPlugin):
    def update_object(self, key, value, context=None):
        return

    def get_object(self, key, context=None):
        return

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None, context=None):
        return

    def delete_object(self, key, context=None):
        return

    def get_owner_id(self, context=None):
        return


fake_bank = Bank(FakeBankPlugin())
fake_bank_section = BankSection(bank=fake_bank, section="fake")


def call_hooks(operation, checkpoint, resource, context, parameters, **kwargs):
    def noop(*args, **kwargs):
        pass

    hooks = (
        'on_prepare_begin',
        'on_prepare_finish',
        'on_main',
        'on_complete',
    )
    for hook_name in hooks:
        hook = getattr(operation, hook_name, noop)
        hook(checkpoint, resource, context, parameters, **kwargs)


class Checkpoint(object):
    def __init__(self):
        self.bank_section = fake_bank_section

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class PodProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(PodProtectionPluginTest, self).setUp()

        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='poll_interval',
            poll_interval=0,
        )
        self.plugin = PodProtectionPlugin(plugin_config)

        k8s.register_opts(cfg.CONF)
        cfg.CONF.set_default('k8s_host',
                             'https://192.168.98.35:6443',
                             'k8s_client')
        cfg.CONF.set_default('k8s_ssl_ca_cert',
                             '/etc/provider.d/server-ca.crt',
                             'k8s_client')
        cfg.CONF.set_default('k8s_cert_file',
                             '/etc/provider.d/client-admin.crt',
                             'k8s_client')
        cfg.CONF.set_default('k8s_key_file',
                             '/etc/provider.d/client-admin.key',
                             'k8s_client')

        self.cntxt = RequestContext(user_id='demo',
                                    project_id='abcd',
                                    auth_token='efgh',
                                    service_catalog=None)
        self.k8s_client = None
        self.checkpoint = Checkpoint()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            constants.POD_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         pod_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            constants.POD_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         pod_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            constants.POD_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         pod_plugin_schemas.SAVED_INFO_SCHEMA)

    @mock.patch('karbor.services.protection.clients.k8s.create')
    def test_create_backup(self, mock_k8s_create):
        self.k8s_client = client_factory.ClientFactory.create_client(
            "k8s", self.cntxt)
        resource = Resource(id="c88b92a8-e8b4-504c-bad4-343d92061871",
                            type=constants.POD_RESOURCE_TYPE,
                            name='default:busybox-test')

        fake_bank_section.update_object = mock.MagicMock()

        protect_operation = self.plugin.get_protect_operation(resource)
        mock_k8s_create.return_value = self.k8s_client

        self.k8s_client.read_namespaced_pod = mock.MagicMock()
        self.k8s_client.read_namespaced_pod.return_value = V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=V1ObjectMeta(
                name="busybox-test",
                namespace="default",
                uid="dd8236e1-8c6c-11e7-9b7a-fa163e18e097"),
            spec=V1PodSpec(volumes=[], containers=[]),
            status=V1PodStatus(phase="Running"))
        fake_bank_section.update_object = mock.MagicMock()
        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})

    @mock.patch('karbor.services.protection.protection_plugins.utils.'
                'update_resource_verify_result')
    def test_verify_backup(self,  mock_update_verify):
        resource = Resource(id="c88b92a8-e8b4-504c-bad4-343d92061871",
                            type=constants.POD_RESOURCE_TYPE,
                            name='default:busybox-test')

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = 'available'

        verify_operation = self.plugin.get_verify_operation(resource)
        call_hooks(verify_operation, self.checkpoint, resource, self.cntxt,
                   {})
        mock_update_verify.assert_called_with(
            None, resource.type, resource.id, 'available')

    def test_delete_backup(self):
        resource = Resource(id="c88b92a8-e8b4-504c-bad4-343d92061871",
                            type=constants.POD_RESOURCE_TYPE,
                            name='default:busybox-test')

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = {
            "pod_id": "1234"}
        fake_bank_section.list_objects = mock.MagicMock()
        fake_bank_section.list_objects.return_value = []

        delete_operation = self.plugin.get_delete_operation(resource)
        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.POD_RESOURCE_TYPE])
