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


def _parse_service_endpoint(endpoint_url, context, append_project_fmt=None):
    if not endpoint_url:
        return None

    if not append_project_fmt:
        return endpoint_url

    return append_project_fmt % {
        'url': endpoint_url,
        'project': context.project_id,
    }


def get_url(service, context, client_config,
            append_project_fmt=None, **kwargs):
    '''Return the url of given service endpoint.'''

    url = ""
    privileged_user = kwargs.get('privileged_user')
    # get url by endpoint
    if privileged_user is not True:
        try:
            url = _parse_service_endpoint(
                getattr(client_config, '%s_endpoint' % service),
                context, append_project_fmt)
            if url:
                return url
        except Exception:
            pass

        # get url by catalog
        try:
            url = _parse_service_catalog_info(
                getattr(client_config, '%s_catalog_info' % service), context)
            if url:
                return url
        except Exception:
            pass

    # get url by accessing keystone
    try:
        keystone_plugin = kwargs.get('keystone_plugin')
        url = keystone_plugin.get_service_endpoint(
            client_config.service_name, client_config.service_type,
            client_config.region_id, client_config.interface)

        url = url.replace("$", "%")
    except Exception:
        pass

    if url:
        return url

    raise exception.KarborException(
        _("Couldn't find the endpoint of service(%s)") % service)
