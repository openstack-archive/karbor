# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from io import BytesIO
import os

from oslo_log import log as logging
from oslo_service import loopingcall

from karbor.services.protection.bank_plugin import BankIO

LOG = logging.getLogger(__name__)


def backup_image_to_bank(glance_client, image_id, bank_section, object_size):
    image_response = glance_client.images.data(image_id, do_checksum=True)
    bank_chunk_num = int(object_size / 65536)

    image_chunks_num = 0
    chunks_num = 1
    image_response_data = BytesIO()
    for chunk in image_response:
        image_response_data.write(chunk)
        image_chunks_num += 1
        if image_chunks_num == bank_chunk_num:
            image_chunks_num = 0
            image_response_data.seek(0, os.SEEK_SET)
            data = image_response_data.read(object_size)
            bank_section.update_object("data_" + str(chunks_num), data)
            image_response_data.truncate(0)
            image_response_data.seek(0, os.SEEK_SET)
            chunks_num += 1

    image_response_data.seek(0, os.SEEK_SET)
    data = image_response_data.read()
    if data != '':
        bank_section.update_object("data_" + str(chunks_num), data)
    else:
        chunks_num -= 1
    return chunks_num


def restore_image_from_bank(glance_client, bank_section, restore_name):
    resource_definition = bank_section.get_object('metadata')
    image_metadata = resource_definition['image_metadata']
    objects = [key.split("/")[-1] for key in
               bank_section.list_objects()
               if (key.split("/")[-1]).startswith("data_")]

    chunks_num = resource_definition.get("chunks_num", 0)
    if len(objects) != int(chunks_num):
        raise Exception("The chunks num of restored image is invalid")

    sorted_objects = sorted(objects, key=lambda s: int(s[5:]))
    image_data = BankIO(bank_section, sorted_objects)
    disk_format = image_metadata["disk_format"]
    container_format = image_metadata["container_format"]
    image = glance_client.images.create(
        disk_format=disk_format,
        container_format=container_format,
        name=restore_name
    )
    glance_client.images.upload(image.id, image_data)
    image_info = glance_client.images.get(image.id)
    if image_info.checksum != image_metadata["checksum"]:
        raise Exception("The checksum of restored image is invalid")
    return image_info


def update_resource_restore_result(restore_record, resource_type, resource_id,
                                   status, reason=''):
    try:
        restore_record.update_resource_status(resource_type, resource_id,
                                              status, reason)
        restore_record.save()
    except Exception:
        LOG.error('Unable to update restoration result. '
                  'resource type: %(resource_type)s, '
                  'resource id: %(resource_id)s, '
                  'status: %(status)s, reason: %(reason)s',
                  {'resource_type': resource_type, 'resource_id': resource_id,
                   'status': status, 'reason': reason})
        pass


def status_poll(get_status_func, interval, success_statuses=set(),
                failure_statuses=set(), ignore_statuses=set(),
                ignore_unexpected=False):
    def _poll():
        status = get_status_func()
        if status in success_statuses:
            raise loopingcall.LoopingCallDone(retvalue=True)
        if status in failure_statuses:
            raise loopingcall.LoopingCallDone(retvalue=False)
        if status in ignore_statuses:
            return
        if ignore_unexpected is False:
            raise loopingcall.LoopingCallDone(retvalue=False)

    loop = loopingcall.FixedIntervalLoopingCall(_poll)
    return loop.start(interval=interval, initial_delay=interval).wait()


def update_resource_verify_result(verify_record, resource_type, resource_id,
                                  status, reason=''):
    try:
        verify_record.update_resource_status(resource_type, resource_id,
                                             status, reason)
        verify_record.save()
    except Exception:
        LOG.error('Unable to update verify result. '
                  'resource type: %(resource_type)s, '
                  'resource id: %(resource_id)s, '
                  'status: %(status)s, reason: %(reason)s',
                  {'resource_type': resource_type, 'resource_id': resource_id,
                   'status': status, 'reason': reason})
        raise
