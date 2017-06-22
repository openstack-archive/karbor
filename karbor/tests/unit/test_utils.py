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

from karbor.tests import base

from karbor import utils


class WalkClassHierarchyTestCase(base.TestCase):
    def test_walk_class_hierarchy(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(B):
            pass

        class E(A):
            pass

        class_pairs = zip((D, B, E),
                          utils.walk_class_hierarchy(A, encountered=[C]))
        for actual, expected in class_pairs:
            self.assertEqual(expected, actual)

        class_pairs = zip((D, B, C, E), utils.walk_class_hierarchy(A))
        for actual, expected in class_pairs:
            self.assertEqual(expected, actual)
