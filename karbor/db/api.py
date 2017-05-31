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

"""Defines interface for DB access.

Functions in this module are imported into the karbor.db namespace. Call these
functions from karbor.db namespace, not the karbor.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface. Currently, many of these objects are sqlalchemy objects that
implement a dictionary interface. However, a future goal is to have all of
these objects be simple dictionaries.


**Related Flags**

:connection:  string specifying the sqlalchemy connection to use, like:
              `sqlite:///var/lib/karbor/karbor.sqlite`.

:enable_new_services:  when adding a new service to the database, is it in the
                       pool of available hardware (Default: True)

"""

from oslo_config import cfg
from oslo_db import concurrency as db_concurrency
from oslo_db import options as db_options


db_opts = [
    cfg.BoolOpt('enable_new_services',
                default=True,
                help='Services to be added to the available pool on create'),
]


CONF = cfg.CONF
CONF.register_opts(db_opts)
db_options.set_defaults(CONF)

_BACKEND_MAPPING = {'sqlalchemy': 'karbor.db.sqlalchemy.api'}


IMPL = db_concurrency.TpoolDbapiWrapper(CONF, _BACKEND_MAPPING)

# The maximum value a signed INT type may have
MAX_INT = 0x7FFFFFFF


###################

def dispose_engine():
    """Force the engine to establish new connections."""

    # FIXME(jdg): When using sqlite if we do the dispose
    # we seem to lose our DB here.  Adding this check
    # means we don't do the dispose, but we keep our sqlite DB
    # This likely isn't the best way to handle this

    if 'sqlite' not in IMPL.get_engine().name:
        return IMPL.dispose_engine()
    else:
        return


###################


def service_destroy(context, service_id):
    """Destroy the service or raise if it does not exist."""
    return IMPL.service_destroy(context, service_id)


def service_get(context, service_id):
    """Get a service or raise if it does not exist."""
    return IMPL.service_get(context, service_id)


def service_get_by_host_and_topic(context, host, topic):
    """Get a service by host it's on and topic it listens to."""
    return IMPL.service_get_by_host_and_topic(context, host, topic)


def service_get_all(context, disabled=None):
    """Get all services."""
    return IMPL.service_get_all(context, disabled)


def service_get_all_by_topic(context, topic, disabled=None):
    """Get all services for a given topic."""
    return IMPL.service_get_all_by_topic(context, topic, disabled=disabled)


def service_get_by_args(context, host, binary):
    """Get the state of an service by node name and binary."""
    return IMPL.service_get_by_args(context, host, binary)


def service_create(context, values):
    """Create a service from the values dictionary."""
    return IMPL.service_create(context, values)


def service_update(context, service_id, values):
    """Set the given properties on an service and update it.

    Raises NotFound if service does not exist.

    """
    return IMPL.service_update(context, service_id, values)


def get_by_id(context, model, id, *args, **kwargs):
    return IMPL.get_by_id(context, model, id, *args, **kwargs)


###################


def trigger_get(context, id):
    """Get a trigger by its id.

    :param context: The security context
    :param id: ID of the trigger

    :returns: Dictionary-like object containing properties of the trigger

    Raises TriggerNotFound if trigger with the given ID doesn't exist.
    """
    return IMPL.trigger_get(context, id)


def trigger_create(context, values):
    """Create a trigger from the values dictionary.

    :param context: The security context
    :param values: Dictionary containing trigger properties

    :returns: Dictionary-like object containing the properties of the created
              trigger
    """
    return IMPL.trigger_create(context, values)


def trigger_update(context, id, values):
    """Set the given properties on a trigger and update it.

    :param context: The security context
    :param id: ID of the trigger
    :param values: Dictionary containing trigger properties to be updated

    :returns: Dictionary-like object containing the properties of the updated
              trigger

    Raises TriggerNotFound if trigger with the given ID doesn't exist.
    """
    return IMPL.trigger_update(context, id, values)


def trigger_delete(context, id):
    """Delete a trigger from the database.

    :param context: The security context
    :param id: ID of the trigger

    Raises TriggerNotFound if trigger with the given ID doesn't exist.
    """
    return IMPL.trigger_delete(context, id)


def trigger_get_all_by_filters_sort(context, filters, limit=None,
                                    marker=None, sort_keys=None,
                                    sort_dirs=None):
    """Get all triggers that match all filters sorted by multiple keys.

    sort_keys and sort_dirs must be a list of strings.
    """
    return IMPL.trigger_get_all_by_filters_sort(
        context, filters, limit=limit, marker=marker,
        sort_keys=sort_keys, sort_dirs=sort_dirs)


###################


def scheduled_operation_get(context, id, columns_to_join=[]):
    """Get a scheduled operation by its id.

    :param context: The security context
    :param id: ID of the scheduled operation
    :param columns_to_join: columns which will be joined

    :returns: Dictionary-like object containing properties of the scheduled
     operation

    Raises ScheduledOperationNotFound if scheduled operation with
     the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_get(context, id, columns_to_join)


def scheduled_operation_create(context, values):
    """Create a scheduled operation from the values dictionary.

    :param context: The security context
    :param values: Dictionary containing scheduled operation properties

    :returns: Dictionary-like object containing the properties of the created
              scheduled operation
    """
    return IMPL.scheduled_operation_create(context, values)


def scheduled_operation_update(context, id, values):
    """Set the given properties on a scheduled operation and update it.

    :param context: The security context
    :param id: ID of the scheduled operation
    :param values: Dictionary containing scheduled operation properties
                   to be updated

    :returns: Dictionary-like object containing the properties of the updated
              scheduled operation

    Raises ScheduledOperationNotFound if scheduled operation with
    the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_update(context, id, values)


def scheduled_operation_delete(context, id):
    """Delete a scheduled operation from the database.

    :param context: The security context
    :param id: ID of the scheduled operation

    Raises ScheduledOperationNotFound if scheduled operation with
    the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_delete(context, id)


def scheduled_operation_get_all_by_filters_sort(
        context, filters, limit=None,
        marker=None, sort_keys=None, sort_dirs=None):
    """Get all operations that match all filters sorted by multiple keys.

    sort_keys and sort_dirs must be a list of strings.
    """
    return IMPL.scheduled_operation_get_all_by_filters_sort(
        context, filters, limit=limit, marker=marker,
        sort_keys=sort_keys, sort_dirs=sort_dirs)


###################


def scheduled_operation_state_get(context, operation_id, columns_to_join=[]):
    """Get a scheduled operation state by its id.

    :param context: The security context
    :param operation_id: Operation_id of the scheduled operation state
    :columns_to_join: columns which will be joined

    :returns: Dictionary-like object containing properties of the scheduled
     operation state

    Raises ScheduledOperationStateNotFound if scheduled operation state with
     the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_state_get(context, operation_id,
                                              columns_to_join)


def scheduled_operation_state_create(context, values):
    """Create a scheduled operation state from the values dictionary.

    :param context: The security context
    :param values: Dictionary containing scheduled operation state properties

    :returns: Dictionary-like object containing the properties of the created
              scheduled operation state
    """
    return IMPL.scheduled_operation_state_create(context, values)


def scheduled_operation_state_update(context, operation_id, values):
    """Set the given properties on a scheduled operation state and update it.

    :param context: The security context
    :param operation_id: Operation_id of the scheduled operation state
    :param values: Dictionary containing scheduled operation state properties
                   to be updated

    :returns: Dictionary-like object containing the properties of the updated
              scheduled operation state

    Raises ScheduledOperationStateNotFound if scheduled operation state with
    the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_state_update(context, operation_id, values)


def scheduled_operation_state_delete(context, operation_id):
    """Delete a scheduled operation state from the database.

    :param context: The security context
    :param operation_id: Operation_id of the scheduled operation state

    Raises ScheduledOperationStateNotFound if scheduled operation state with
    the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_state_delete(context, operation_id)


def scheduled_operation_state_get_all_by_filters_sort(
        context, filters, limit=None, marker=None,
        sort_keys=None, sort_dirs=None, columns_to_join=[]):
    """Get all operation states that match all filters sorted by multiple keys.

    sort_keys and sort_dirs must be a list of strings.
    """
    return IMPL.scheduled_operation_state_get_all_by_filters_sort(
        context, filters, limit=limit, marker=marker, sort_keys=sort_keys,
        sort_dirs=sort_dirs, columns_to_join=columns_to_join)


###################


def scheduled_operation_log_get(context, log_id):
    """Get a scheduled operation log by its id.

    :param context: The security context
    :param log_id: Log_id of the scheduled operation log

    :returns: Dictionary-like object containing properties of the scheduled
     operation log

    Raises ScheduledOperationLogNotFound if scheduled operation log with
     the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_log_get(context, log_id)


def scheduled_operation_log_create(context, values):
    """Create a scheduled operation log from the values dictionary.

    :param context: The security context
    :param values: Dictionary containing scheduled operation log properties

    :returns: Dictionary-like object containing the properties of the created
              scheduled operation log
    """
    return IMPL.scheduled_operation_log_create(context, values)


def scheduled_operation_log_update(context, log_id, values):
    """Set the given properties on a scheduled operation log and update it.

    :param context: The security context
    :param log_id: Log_id of the scheduled operation log
    :param values: Dictionary containing scheduled operation log properties
                   to be updated

    :returns: Dictionary-like object containing the properties of the updated
              scheduled operation log

    Raises ScheduledOperationLogNotFound if scheduled operation log with
    the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_log_update(context, log_id, values)


def scheduled_operation_log_delete(context, log_id):
    """Delete a scheduled operation log from the database.

    :param context: The security context
    :param log_id: Log_id of the scheduled operation log

    Raises ScheduledOperationLogNotFound if scheduled operation log with
    the given ID doesn't exist.
    """
    return IMPL.scheduled_operation_log_delete(context, log_id)


def scheduled_operation_log_delete_oldest(context, operation_id,
                                          retained_num, excepted_states=[]):
    """Delete the oldest scheduled operation logs from the database.

    :param context: The security context
    :param operation_id: ID of the scheduled operation
    :param retained_num: The number of retained logs
    :param excepted_states: If the state of log is in excepted_states,
                            it will not be deleted.
    """
    return IMPL.scheduled_operation_log_delete_oldest(context, operation_id,
                                                      retained_num,
                                                      excepted_states)


def scheduled_operation_log_get_all_by_filters_sort(
        context, filters, limit=None, marker=None,
        sort_keys=None, sort_dirs=None):
    """Get all operation logs that match all filters sorted by multiple keys.

    sort_keys and sort_dirs must be a list of strings.
    """
    return IMPL.scheduled_operation_log_get_all_by_filters_sort(
        context, filters, limit=limit, marker=marker, sort_keys=sort_keys,
        sort_dirs=sort_dirs)


###################


def plan_get(context, plan_id):
    """Get a plan or raise if it does not exist."""
    return IMPL.plan_get(context, plan_id)


def plan_create(context, values):
    """Create a plan from the values dictionary."""
    return IMPL.plan_create(context, values)


def plan_update(context, plan_id, values):
    """Set the given properties on a plan and update it.

    Raises NotFound if plan does not exist.

    """
    return IMPL.plan_update(context, plan_id, values)


def plan_resources_update(context, plan_id, resources):
    """Update resources if it exists, otherwise create it."""
    return IMPL.plan_resources_update(context, plan_id, resources)


def plan_destroy(context, plan_id):
    """Destroy the plan or raise if it does not exist."""
    return IMPL.plan_destroy(context, plan_id)


def plan_get_all(context, marker, limit, sort_keys=None, sort_dirs=None,
                 filters=None, offset=None):
    """Get all plans."""
    return IMPL.plan_get_all(context, marker, limit, sort_keys=sort_keys,
                             sort_dirs=sort_dirs, filters=filters,
                             offset=offset)


def plan_get_all_by_project(context, project_id, marker, limit,
                            sort_keys=None, sort_dirs=None, filters=None,
                            offset=None):
    """Get all plans belonging to a project."""
    return IMPL.plan_get_all_by_project(context, project_id, marker, limit,
                                        sort_keys=sort_keys,
                                        sort_dirs=sort_dirs,
                                        filters=filters,
                                        offset=offset)


def restore_get(context, restore_id):
    """Get a restore or raise if it does not exist."""
    return IMPL.restore_get(context, restore_id)


def restore_create(context, values):
    """Create a restore from the values dictionary."""
    return IMPL.restore_create(context, values)


def restore_update(context, restore_id, values):
    """Set the given properties on a restore and update it.

    Raises NotFound if plan does not exist.

    """
    return IMPL.restore_update(context, restore_id, values)


def restore_destroy(context, restore_id):
    """Destroy the restore or raise if it does not exist."""
    return IMPL.restore_destroy(context, restore_id)


def restore_get_all(context, marker, limit, sort_keys=None, sort_dirs=None,
                    filters=None, offset=None):
    """Get all restores."""
    return IMPL.restore_get_all(context, marker, limit, sort_keys=sort_keys,
                                sort_dirs=sort_dirs, filters=filters,
                                offset=offset)


def restore_get_all_by_project(context, project_id, marker, limit,
                               sort_keys=None, sort_dirs=None, filters=None,
                               offset=None):
    """Get all restores belonging to a project."""
    return IMPL.restore_get_all_by_project(context, project_id, marker, limit,
                                           sort_keys=sort_keys,
                                           sort_dirs=sort_dirs,
                                           filters=filters,
                                           offset=offset)


def operation_log_get(context, operation_log_id):
    """Get a operation log or raise if it does not exist."""
    return IMPL.operation_log_get(context, operation_log_id)


def operation_log_create(context, values):
    """Create a operation log from the values dictionary."""
    return IMPL.operation_log_create(context, values)


def operation_log_update(context, operation_log_id, values):
    """Set the given properties on a operation log and update it.

    Raises NotFound if plan does not exist.

    """
    return IMPL.operation_log_update(context, operation_log_id, values)


def operation_log_destroy(context, operation_log_id):
    """Destroy the operation log or raise if it does not exist."""
    return IMPL.operation_log_destroy(context, operation_log_id)


def operation_log_get_all(context, marker, limit, sort_keys=None,
                          sort_dirs=None,
                          filters=None, offset=None):
    """Get all operation logs."""
    return IMPL.operation_log_get_all(context, marker, limit,
                                      sort_keys=sort_keys,
                                      sort_dirs=sort_dirs,
                                      filters=filters,
                                      offset=offset)


def operation_log_get_all_by_project(context, project_id, marker, limit,
                                     sort_keys=None, sort_dirs=None,
                                     filters=None,
                                     offset=None):
    """Get all operation logs belonging to a project."""
    return IMPL.operation_log_get_all_by_project(context, project_id,
                                                 marker, limit,
                                                 sort_keys=sort_keys,
                                                 sort_dirs=sort_dirs,
                                                 filters=filters,
                                                 offset=offset)


###################


def checkpoint_record_get(context, checkpoint_record_id):
    """Get a checkpoint record or raise if it does not exist."""
    return IMPL.checkpoint_record_get(context, checkpoint_record_id)


def checkpoint_record_create(context, values):
    """Create a checkpoint record from the values dictionary."""
    return IMPL.checkpoint_record_create(context, values)


def checkpoint_record_update(context, checkpoint_record_id, values):
    """Set the given properties on a checkpoint record and update it.

    Raises NotFound if checkpoint record does not exist.

    """
    return IMPL.checkpoint_record_update(context, checkpoint_record_id, values)


def checkpoint_record_destroy(context, checkpoint_record_id):
    """Destroy the checkpoint record or raise if it does not exist."""
    return IMPL.checkpoint_record_destroy(context, checkpoint_record_id)


def checkpoint_record_get_all_by_filters_sort(
        context, filters, limit=None,
        marker=None, sort_keys=None, sort_dirs=None):
    """Get all checkpoint records that match all filters sorted

    by multiple keys. sort_keys and sort_dirs must be a list of strings.

    """
    return IMPL.checkpoint_record_get_all_by_filters_sort(
        context, filters, limit=limit, marker=marker,
        sort_keys=sort_keys, sort_dirs=sort_dirs)


def purge_deleted_rows(context, age_in_days):
    """Purge deleted rows older than given age from karbor tables

    Raises InvalidParameterValue if age_in_days is incorrect.
    :returns: number of deleted rows
    """
    return IMPL.purge_deleted_rows(context, age_in_days=age_in_days)
