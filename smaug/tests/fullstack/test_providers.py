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


from smaug.tests.fullstack import smaug_base


class ProvidersTest(smaug_base.SmaugBaseTest):
    """Test Providers operation"""
    provider_id = u"cf56bd3e-97a7-4078-b6d5-f36246333fd9"

    def test_providers_list(self):
        provider_res = self.smaug_client.providers.list()
        self.assertEqual(1, len(provider_res))

    def test_provider_get(self):
        provider_res = self.smaug_client.providers.get(self.provider_id)
        self.assertEqual("OS Infra Provider", provider_res.name)
