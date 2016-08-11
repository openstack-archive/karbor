# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from karbor.tests.fullstack import karbor_base


class ProvidersTest(karbor_base.KarborBaseTest):
    """Test Providers operation"""

    def test_providers_list(self):
        provider_res = self.karbor_client.providers.list()
        self.assertTrue(len(provider_res))

    def test_provider_get(self):
        providers = self.karbor_client.providers.list()
        for provider in providers:
            provider_res = self.karbor_client.providers.get(provider.id)
            self.assertEqual(provider.name, provider_res.name)
