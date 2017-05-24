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

from oslo_log import log as logging

from karbor.common import karbor_keystone_plugin


LOG = logging.getLogger(__name__)


class UserTrustManager(object):
    def __init__(self):
        super(UserTrustManager, self).__init__()
        self._user_trust_map = {}
        self._skp = karbor_keystone_plugin.KarborKeystonePlugin()

    def _user_trust_key(self, user_id, project_id):
        return "%s_%s" % (user_id, project_id)

    def _add_user_trust_info(self, user_id, project_id,
                             operation_id, trust_id, session):
        key = self._user_trust_key(user_id, project_id)
        self._user_trust_map[key] = {
            'operation_ids': {operation_id},
            'trust_id': trust_id,
            'session': session
        }

    def _get_user_trust_info(self, user_id, project_id):
        return self._user_trust_map.get(
            self._user_trust_key(user_id, project_id))

    def _del_user_trust_info(self, user_id, project_id):
        key = self._user_trust_key(user_id, project_id)
        del self._user_trust_map[key]

    def get_token(self, user_id, project_id):
        auth_info = self._get_user_trust_info(user_id, project_id)
        if not auth_info:
            return None

        try:
            return auth_info['session'].get_token()
        except Exception:
            LOG.exception("Get token failed, user_id=%(user_id)s, "
                          "project_id=%(proj_id)s",
                          {'user_id': user_id, 'proj_id': project_id})
        return None

    def add_operation(self, context, operation_id):
        auth_info = self._get_user_trust_info(
            context.user_id, context.project_id)
        if auth_info:
            auth_info['operation_ids'].add(operation_id)
            return auth_info['trust_id']

        trust_id = self._skp.create_trust_to_karbor(context)
        try:
            lsession = self._skp.create_trust_session(trust_id)
        except Exception:
            self._skp.delete_trust_to_karbor(trust_id)
            raise

        self._add_user_trust_info(context.user_id, context.project_id,
                                  operation_id, trust_id, lsession)

        return trust_id

    def delete_operation(self, context, operation_id):
        auth_info = self._get_user_trust_info(
            context.user_id, context.project_id)
        if not auth_info:
            return

        operation_ids = auth_info['operation_ids']
        operation_ids.discard(operation_id)
        if len(operation_ids) == 0:
            self._skp.delete_trust_to_karbor(auth_info['trust_id'])
            self._del_user_trust_info(context.user_id, context.project_id)

    def resume_operation(self, operation_id, user_id, project_id, trust_id):
        auth_info = self._get_user_trust_info(user_id, project_id)
        if auth_info:
            auth_info['operation_ids'].add(operation_id)
            return

        try:
            lsession = self._skp.create_trust_session(trust_id)
        except Exception:
            raise

        self._add_user_trust_info(user_id, project_id,
                                  operation_id, trust_id, lsession)
