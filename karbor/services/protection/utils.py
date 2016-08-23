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

from karbor import exception
from karbor.i18n import _


def _parse_service_catalog_info(config, context):
    try:
        service_type, service_name, endpoint_type = config.split(':')
    except ValueError:
        msg = _("Failed to parse the catalog info option %s, "
                "must be in the form: "
                "<service_type>:<service_name>:<endpoint_type>"
                ) % config
        raise exception.KarborException(msg)

    for entry in context.service_catalog:
        if entry.get('type') == service_type:
            return entry.get('endpoints')[0].get(endpoint_type)

    raise exception.KarborException(_(
        "Couldn't find the endpoint of service type %s "
        "from service catalog") % service_type)


def _parse_service_endpoint(endpoint_url, context, append_project_fmt=None):
    if not append_project_fmt:
        return endpoint_url
    return append_project_fmt \
        % {'url': endpoint_url, 'project': context.project_id}


def get_url(service, context, conf, append_project_fmt=None):
    '''Return the url of given service endpoint.'''
    client_conf = getattr(conf, service + '_client')

    endpoint = getattr(client_conf, service + '_endpoint')
    if endpoint is not None:
        return _parse_service_endpoint(endpoint, context, append_project_fmt)

    return _parse_service_catalog_info(
        getattr(client_conf, service + '_catalog_info'),
        context
    )
