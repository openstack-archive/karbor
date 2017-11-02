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

"""Implementation of SQLAlchemy backend."""

import datetime as dt
import functools
import re
import six
import sys
import threading
import time
import uuid

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exc
from oslo_db import options
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy import MetaData
from sqlalchemy.orm import joinedload
from sqlalchemy.schema import Table
from sqlalchemy.sql import expression
from sqlalchemy.sql.expression import literal_column
from sqlalchemy.sql import func

from karbor.db.sqlalchemy import models
from karbor import exception
from karbor.i18n import _


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

options.set_defaults(CONF, connection='sqlite:///$state_path/karbor.sqlite')

_LOCK = threading.Lock()
_FACADE = None
_GET_METHODS = {}


def _create_facade_lazily():
    global _LOCK
    with _LOCK:
        global _FACADE
        if _FACADE is None:
            _FACADE = db_session.EngineFacade(
                CONF.database.connection,
                **dict(CONF.database)
            )

        return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def dispose_engine():
    get_engine().dispose()

_DEFAULT_QUOTA_NAME = 'default'


def get_backend():
    """The backend is this module itself."""

    return sys.modules[__name__]


def is_admin_context(context):
    """Indicates if the request context is an administrator."""
    if not context:
        LOG.warning('Use of empty request context is deprecated',
                    DeprecationWarning)
        raise Exception('die')
    return context.is_admin


def is_user_context(context):
    """Indicates if the request context is a normal user."""
    if not context:
        return False
    if context.is_admin:
        return False
    if not context.user_id or not context.project_id:
        return False
    return True


def authorize_project_context(context, project_id):
    """Ensures a request has permission to access the given project."""
    if is_user_context(context):
        if not context.project_id:
            raise exception.NotAuthorized()
        elif context.project_id != project_id:
            raise exception.NotAuthorized()


def authorize_user_context(context, user_id):
    """Ensures a request has permission to access the given user."""
    if is_user_context(context):
        if not context.user_id:
            raise exception.NotAuthorized()
        elif context.user_id != user_id:
            raise exception.NotAuthorized()


def require_admin_context(f):
    """Decorator to require admin request context.

    The first argument to the wrapped function must be the context.

    """

    def wrapper(*args, **kwargs):
        if not is_admin_context(args[0]):
            raise exception.AdminRequired()
        return f(*args, **kwargs)
    return wrapper


def require_context(f):
    """Decorator to require *any* user or admin context.

    This does no authorization for user or project access matching, see
    :py:func:`authorize_project_context` and
    :py:func:`authorize_user_context`.

    The first argument to the wrapped function must be the context.

    """

    def wrapper(*args, **kwargs):
        if not is_admin_context(args[0]) and not is_user_context(args[0]):
            raise exception.NotAuthorized()
        return f(*args, **kwargs)
    return wrapper


def require_plan_exists(f):
    """Decorator to require the specified plan to exist.

    Requires the wrapped function to use context and plan_id as
    their first two arguments.
    """
    @functools.wraps(f)
    def wrapper(context, plan_id, *args, **kwargs):
        plan_get(context, plan_id)
        return f(context, plan_id, *args, **kwargs)
    return wrapper


def _retry_on_deadlock(f):
    """Decorator to retry a DB API call if Deadlock was received."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        while True:
            try:
                return f(*args, **kwargs)
            except db_exc.DBDeadlock:
                LOG.warning("Deadlock detected when running '%(func_name)s':"
                            " Retrying...", dict(func_name=f.__name__))
                # Retry!
                time.sleep(0.5)
                continue
    functools.update_wrapper(wrapped, f)
    return wrapped


def model_query(context, *args, **kwargs):
    """Query helper that accounts for context's `read_deleted` field.

    :param context: context to query under
    :param session: if present, the session to use
    :param read_deleted: if present, overrides context's read_deleted field.
    :param project_only: if present and context is user-type, then restrict
            query to match the context's project_id.
    """
    session = kwargs.get('session') or get_session()
    read_deleted = kwargs.get('read_deleted') or context.read_deleted
    project_only = kwargs.get('project_only')

    query = session.query(*args)
    if read_deleted == 'no':
        query = query.filter_by(deleted=False)
    elif read_deleted == 'yes':
        pass  # omit the filter to include deleted and active
    elif read_deleted == 'only':
        query = query.filter_by(deleted=True)
    else:
        raise Exception(
            _("Unrecognized read_deleted value '%s'") % read_deleted)

    if project_only and is_user_context(context):
        query = query.filter_by(project_id=context.project_id)

    return query


@require_admin_context
def service_destroy(context, service_id):
    session = get_session()
    with session.begin():
        service_ref = _service_get(context, service_id, session=session)
        service_ref.delete(session=session)


@require_admin_context
def _service_get(context, service_id, session=None):
    result = model_query(
        context,
        models.Service,
        session=session
    ).filter_by(id=service_id).first()
    if not result:
        raise exception.ServiceNotFound(service_id=service_id)

    return result


@require_admin_context
def service_get(context, service_id):
    return _service_get(context, service_id)


@require_admin_context
def service_get_all(context, disabled=None):
    query = model_query(context, models.Service)

    if disabled is not None:
        query = query.filter_by(disabled=disabled)

    return query.all()


@require_admin_context
def service_get_all_by_args(context, host, binary):
    results = model_query(
        context,
        models.Service
    )
    if host is not None:
        results = results.filter_by(host=host)
    if binary is not None:
        results = results.filter_by(binary=binary)

    return results.all()


@require_admin_context
def service_get_all_by_topic(context, topic, disabled=None):
    query = model_query(
        context,
        models.Service,
        read_deleted="no"
    ).filter_by(topic=topic)

    if disabled is not None:
        query = query.filter_by(disabled=disabled)

    return query.all()


@require_admin_context
def service_get_by_host_and_topic(context, host, topic):
    result = model_query(
        context,
        models.Service,
        read_deleted="no"
    ).filter_by(
        disabled=False
    ).filter_by(
        host=host
    ).filter_by(
        topic=topic
    ).first()
    if not result:
        raise exception.ServiceNotFound(service_id=None)
    return result


@require_admin_context
def _service_get_all_topic_subquery(context, session, topic, subq, label):
    sort_value = getattr(subq.c, label)
    return model_query(
        context,
        models.Service,
        func.coalesce(sort_value, 0),
        session=session,
        read_deleted="no"
    ).filter_by(
        topic=topic
    ).filter_by(
        disabled=False
    ).outerjoin(
        (subq, models.Service.host == subq.c.host)
    ).order_by(
        sort_value
    ).all()


@require_admin_context
def service_get_by_args(context, host, binary):
    results = model_query(
        context,
        models.Service
    ).filter_by(
        host=host
    ).filter_by(
        binary=binary
    ).all()

    for result in results:
        if host == result['host']:
            return result

    raise exception.HostBinaryNotFound(host=host, binary=binary)


@require_admin_context
def service_create(context, values):
    service_ref = models.Service()
    service_ref.update(values)
    if not CONF.enable_new_services:
        service_ref.disabled = True

    session = get_session()
    with session.begin():
        service_ref.save(session)
        return service_ref


@require_admin_context
def service_update(context, service_id, values):
    session = get_session()
    with session.begin():
        service_ref = _service_get(context, service_id, session=session)
        if 'disabled' in values:
            service_ref['modified_at'] = timeutils.utcnow()
            service_ref['updated_at'] = literal_column('updated_at')
        service_ref.update(values)
        return service_ref


def _get_get_method(model):
    # General conversion
    # Convert camel cased model name to snake format
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', model.__name__)
    # Get method must be snake formatted model name concatenated with _get
    method_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower() + '_get'
    return globals().get(method_name)


@require_context
def get_by_id(context, model, id, *args, **kwargs):
    # Add get method to cache dictionary if it's not already there
    if not _GET_METHODS.get(model):
        _GET_METHODS[model] = _get_get_method(model)

    return _GET_METHODS[model](context, id, *args, **kwargs)


###################


def trigger_get(context, id):
    return _trigger_get(context, id)


def _trigger_get(context, id, session=None):
    result = model_query(context, models.Trigger,
                         session=session).filter_by(id=id)
    result = result.first()

    if not result:
        raise exception.TriggerNotFound(id=id)

    return result


def trigger_create(context, values):
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    trigger_ref = models.Trigger()
    trigger_ref.update(values)
    trigger_ref.save(get_session())
    return trigger_ref


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def trigger_update(context, id, values):
    """Update the Trigger record with the most recent data."""

    session = get_session()
    with session.begin():
        trigger_ref = _trigger_get(context, id, session=session)
        trigger_ref.update(values)
        trigger_ref.save(session)
    return trigger_ref


def trigger_delete(context, id):
    """Delete a Trigger record."""

    session = get_session()
    with session.begin():
        trigger_ref = _trigger_get(context, id, session=session)
        trigger_ref.delete(session=session)


def _trigger_list_query(context, session, **kwargs):
    return model_query(context, models.Trigger, session=session)


def _trigger_list_process_filters(query, filters):
    exact_match_filter_names = ['project_id', 'type']
    query = _list_common_process_exact_filter(models.Trigger, query, filters,
                                              exact_match_filter_names)

    regex_match_filter_names = ['name', 'properties']
    query = _list_common_process_regex_filter(models.Trigger, query, filters,
                                              regex_match_filter_names)

    return query


def trigger_get_all_by_filters_sort(context, filters, limit=None, marker=None,
                                    sort_keys=None, sort_dirs=None):
    session = get_session()
    with session.begin():
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         paginate_type=models.Trigger,
                                         use_model=True)

        return query.all() if query else []


###################


def _trigger_execution_list_query(context, session, **kwargs):
    return model_query(context, models.TriggerExecution, session=session)


def _trigger_execution_list_process_filters(query, filters):
    exact_match_filter_names = ['id', 'trigger_id', 'execution_time']
    query = _list_common_process_exact_filter(models.Trigger, query, filters,
                                              exact_match_filter_names)
    return query


def _trigger_execution_get(context, id, session=None):
    result = model_query(context, models.TriggerExecution,
                         session=session).filter_by(id=id)
    result = result.first()

    if not result:
        raise exception.TriggerNotFound(id=id)

    return result


def trigger_execution_update(context, id, old_time, new_time):
    session = get_session()
    try:
        with session.begin():
            result = model_query(
                context, models.TriggerExecution, session=session
            ).filter_by(
                id=id, execution_time=old_time
            ).update({"execution_time": new_time})
    except Exception as e:
        LOG.warning("Unable to update trigger execution (%(execution)s): "
                    "%(exc)s",
                    {"execution": id, "exc": e})
        return False
    else:
        LOG.debug("Updated trigger execution (%(execution)s) from %(old_time)s"
                  " to %(new_time)s",
                  {"execution": id, "old_time": old_time, "new_time": new_time}
                  )
        return result == 1


def trigger_execution_create(context, trigger_id, time):
    trigger_ex_ref = models.TriggerExecution()
    trigger_ex_ref.update({
        'id': uuidutils.generate_uuid(),
        'trigger_id': trigger_id,
        'execution_time': time,
    })
    trigger_ex_ref.save(get_session())
    return trigger_ex_ref


def trigger_execution_delete(context, id, trigger_id):
    filters = {}
    if id:
        filters['id'] = id
    if trigger_id:
        filters['trigger_id'] = trigger_id

    session = get_session()
    try:
        with session.begin():
            deleted = model_query(
                context, models.TriggerExecution, session=session
            ).filter_by(**filters).delete()
    except Exception as e:
        LOG.warning("Unable to delete trigger (%(trigger)s) execution "
                    "(%(execution)s): %(exc)s",
                    {"trigger": trigger_id, "execution": id, "exc": e})
        return False
    else:
        LOG.debug("Deleted trigger (%(trigger)s) execution (%(execution)s)",
                  {"trigger": trigger_id, "execution": id})
        return deleted == 1


def trigger_execution_get_next(context):
    session = get_session()
    try:
        with session.begin():
            query = _generate_paginate_query(
                context, session,
                marker=None,
                limit=1,
                sort_keys=('execution_time', ),
                sort_dirs=('asc', ),
                filters=None,
                paginate_type=models.TriggerExecution,
            )
            result = query.first()
    except Exception as e:
        LOG.warning("Unable to get next trigger execution %s", e)
        return None
    else:
        return result


###################


def scheduled_operation_get(context, id, columns_to_join=[]):
    return _scheduled_operation_get(context, id,
                                    columns_to_join=columns_to_join)


def _scheduled_operation_get(context, id, columns_to_join=[], session=None):
    query = model_query(context, models.ScheduledOperation,
                        session=session).filter_by(id=id)

    if columns_to_join and 'trigger' in columns_to_join:
        query = query.options(joinedload('trigger'))

    result = query.first()
    if not result:
        raise exception.ScheduledOperationNotFound(id=id)

    return result


def scheduled_operation_create(context, values):
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()

    operation_ref = models.ScheduledOperation()
    operation_ref.update(values)
    operation_ref.save(get_session())
    return operation_ref


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def scheduled_operation_update(context, id, values):
    """Update the ScheduledOperation record with the most recent data."""

    session = get_session()
    with session.begin():
        operation_ref = _scheduled_operation_get(context, id,
                                                 session=session)
        operation_ref.update(values)
        operation_ref.save(session)
    return operation_ref


def scheduled_operation_delete(context, id):
    """Delete a ScheduledOperation record."""

    session = get_session()
    with session.begin():
        operation_ref = _scheduled_operation_get(context, id,
                                                 session=session)
        session.delete(operation_ref)
        session.flush()


def _scheduled_operation_list_query(context, session, **kwargs):
    return model_query(context, models.ScheduledOperation, session=session)


def _scheduled_operation_list_process_filters(query, filters):
    exact_match_filter_names = ['project_id', 'operation_type', 'trigger_id']
    query = _list_common_process_exact_filter(
        models.ScheduledOperation, query, filters,
        exact_match_filter_names)

    regex_match_filter_names = ['name', 'operation_definition']
    query = _list_common_process_regex_filter(
        models.ScheduledOperation, query, filters,
        regex_match_filter_names)

    return query


def scheduled_operation_get_all_by_filters_sort(
        context, filters, limit=None, marker=None,
        sort_keys=None, sort_dirs=None):

    session = get_session()
    with session.begin():
        query = _generate_paginate_query(
            context, session, marker, limit,
            sort_keys, sort_dirs, filters,
            paginate_type=models.ScheduledOperation,
            use_model=True)

        return query.all() if query else []


###################


def scheduled_operation_state_get(context, operation_id, columns_to_join=[]):
    return _scheduled_operation_state_get(context, operation_id,
                                          columns_to_join=columns_to_join)


def _scheduled_operation_state_get(context, operation_id,
                                   columns_to_join=[], session=None):
    query = model_query(context, models.ScheduledOperationState,
                        session=session).filter_by(operation_id=operation_id)

    if columns_to_join and 'operation' in columns_to_join:
        query = query.options(joinedload('operation'))

    result = query.first()
    if not result:
        raise exception.ScheduledOperationStateNotFound(op_id=operation_id)
    return result


def scheduled_operation_state_create(context, values):
    state_ref = models.ScheduledOperationState()
    state_ref.update(values)
    state_ref.save(get_session())
    return state_ref


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def scheduled_operation_state_update(context, operation_id, values):
    """Update the ScheduledOperationState record with the most recent data."""

    session = get_session()
    with session.begin():
        state_ref = _scheduled_operation_state_get(context, operation_id,
                                                   session=session)
        state_ref.update(values)
        state_ref.save(session)
    return state_ref


def scheduled_operation_state_delete(context, operation_id):
    """Delete a ScheduledOperationState record."""

    session = get_session()
    with session.begin():
        state_ref = _scheduled_operation_state_get(context, operation_id,
                                                   session=session)
        session.delete(state_ref)
        session.flush()


def _scheduled_operation_state_list_query(context, session, **kwargs):
    query = model_query(context, models.ScheduledOperationState,
                        session=session)

    valid_columns = ['operation']
    columns_to_join = kwargs.get('columns_to_join', [])
    for column in columns_to_join:
        if column in valid_columns:
            query = query.options(joinedload(column))

    return query


def _scheduled_operation_state_list_process_filters(query, filters):
    exact_match_filter_names = ['service_id', 'state']
    query = _list_common_process_exact_filter(
        models.ScheduledOperationState, query, filters,
        exact_match_filter_names)

    return query


def scheduled_operation_state_get_all_by_filters_sort(
        context, filters, limit=None, marker=None,
        sort_keys=None, sort_dirs=None, columns_to_join=[]):

    session = get_session()
    with session.begin():
        query = _generate_paginate_query(
            context, session, marker, limit,
            sort_keys, sort_dirs, filters,
            paginate_type=models.ScheduledOperationState,
            use_model=True, columns_to_join=columns_to_join)

        return query.all() if query else []


###################


def scheduled_operation_log_get(context, log_id):
    return _scheduled_operation_log_get(context, log_id)


def _scheduled_operation_log_get(context, log_id, session=None):
    result = model_query(context, models.ScheduledOperationLog,
                         session=session).filter_by(id=log_id).first()

    if not result:
        raise exception.ScheduledOperationLogNotFound(log_id=log_id)

    return result


def scheduled_operation_log_create(context, values):
    log_ref = models.ScheduledOperationLog()
    log_ref.update(values)
    log_ref.save(get_session())
    return log_ref


@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def scheduled_operation_log_update(context, log_id, values):
    """Update the ScheduledOperationLog record with the most recent data."""

    session = get_session()
    with session.begin():
        log_ref = _scheduled_operation_log_get(context, log_id,
                                               session=session)
        log_ref.update(values)
        log_ref.save(session)
    return log_ref


def scheduled_operation_log_delete(context, log_id):
    """Delete a ScheduledOperationLog record."""

    session = get_session()
    with session.begin():
        log_ref = _scheduled_operation_log_get(context, log_id,
                                               session=session)
        session.delete(log_ref)
        session.flush()


def scheduled_operation_log_delete_oldest(context, operation_id,
                                          retained_num, excepted_states):
    table = models.ScheduledOperationLog
    session = get_session()
    with session.begin():
        result = model_query(context, table, session=session).filter_by(
            operation_id=operation_id).order_by(
            expression.desc(table.created_at)).limit(retained_num).all()

        if not result or len(result) < retained_num:
            return
        oldest_create_time = result[-1]['created_at']

        if excepted_states and isinstance(excepted_states, list):
            filters = expression.and_(
                table.operation_id == operation_id,
                table.created_at < oldest_create_time,
                table.state.notin_(excepted_states))
        else:
            filters = expression.and_(
                table.operation_id == operation_id,
                table.created_at < oldest_create_time)

        model_query(context, table, session=session).filter(
            filters).delete(synchronize_session=False)


def _scheduled_operation_log_list_query(context, session, **kwargs):
    query = model_query(context, models.ScheduledOperationLog,
                        session=session)
    return query


def _scheduled_operation_log_list_process_filters(query, filters):
    exact_match_filter_names = ['operation_id', 'state']
    query = _list_common_process_exact_filter(
        models.ScheduledOperationLog, query, filters,
        exact_match_filter_names)

    return query


def scheduled_operation_log_get_all_by_filters_sort(
        context, filters, limit=None, marker=None,
        sort_keys=None, sort_dirs=None):

    session = get_session()
    with session.begin():
        query = _generate_paginate_query(
            context, session, marker, limit,
            sort_keys, sort_dirs, filters,
            paginate_type=models.ScheduledOperationLog,
            use_model=True)

        return query.all() if query else []


###################


def _resource_refs(resource_list, meta_class):
    resource_refs = []
    if resource_list:
        for resource in resource_list:
            resource_ref = meta_class()
            resource_ref['resource_id'] = resource['id']
            resource_ref['resource_type'] = resource['type']
            resource_ref['resource_name'] = resource['name']
            resource_ref['resource_extra_info'] = resource.get(
                'extra_info', None)
            resource_refs.append(resource_ref)
    return resource_refs


@require_context
def _plan_get_query(context, session=None, project_only=False,
                    joined_load=True):
    """Get the query to retrieve the plan.

    :param context: the context used to run the method _plan_get_query
    :param session: the session to use
    :param project_only: the boolean used to decide whether to query the
                         plan in the current project or all projects
    :param joined_load: the boolean used to decide whether the query loads
                        the other models, which join the plan model in
                        the database.
    :returns: updated query or None
    """
    query = model_query(context, models.Plan, session=session,
                        project_only=project_only)
    if joined_load:
        query = query.options(joinedload('resources'))
    return query


def _plan_resources_get_query(context, plan_id, model, session=None):
    return model_query(
        context,
        model,
        session=session,
        read_deleted="no"
    ).filter_by(plan_id=plan_id)


@require_context
def _resource_create(context, values):
    resource_ref = models.Resource()
    resource_ref.update(values)
    session = get_session()
    with session.begin():
        resource_ref.save(session)
        return resource_ref


@require_context
def _plan_resources_update(context, plan_id, resources, session=None):
    session = session or get_session()
    now = timeutils.utcnow()
    with session.begin():
        model_query(
            context,
            models.Resource,
            session=session
        ).filter_by(
            plan_id=plan_id
        ).update({
            'deleted': True,
            'deleted_at': now,
            'updated_at': literal_column('updated_at')
        })
    resources_list = []
    for resource in resources:
        resource['plan_id'] = plan_id
        resource['resource_id'] = resource.pop('id')
        resource['resource_type'] = resource.pop('type')
        resource['resource_name'] = resource.pop('name')
        resource['resource_extra_info'] = resource.pop(
            'extra_info', None)
        resource_ref = _resource_create(context, resource)
        resources_list.append(resource_ref)

    return resources_list


@require_context
def _plan_get(context, plan_id, session=None, joined_load=True):
    result = _plan_get_query(context, session=session, project_only=True,
                             joined_load=joined_load)
    result = result.filter_by(id=plan_id).first()

    if not result:
        raise exception.PlanNotFound(plan_id=plan_id)

    return result


@require_context
def plan_create(context, values):
    values['resources'] = _resource_refs(values.get('resources'),
                                         models.Resource)

    plan_ref = models.Plan()
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()
    plan_ref.update(values)

    session = get_session()
    with session.begin():
        session.add(plan_ref)

    return _plan_get(context, values['id'], session=session)


@require_context
def plan_get(context, plan_id):
    return _plan_get(context, plan_id)


@require_admin_context
@_retry_on_deadlock
def plan_destroy(context, plan_id):
    session = get_session()
    now = timeutils.utcnow()
    with session.begin():
        model_query(
            context,
            models.Plan,
            session=session
        ).filter_by(
            id=plan_id
        ).update({
            'deleted': True,
            'deleted_at': now,
            'updated_at': literal_column('updated_at')
        })
        model_query(
            context,
            models.Resource,
            session=session
        ).filter_by(
            plan_id=plan_id
        ).update({
            'deleted': True,
            'deleted_at': now,
            'updated_at': literal_column('updated_at')
        })


@require_context
@require_plan_exists
def plan_update(context, plan_id, values):
    session = get_session()
    with session.begin():
        resources = values.get('resources')
        if resources is not None:
            _plan_resources_update(context,
                                   plan_id,
                                   values.pop('resources'),
                                   session=session)

        plan_ref = _plan_get(context, plan_id, session=session)
        plan_ref.update(values)

        return plan_ref


@require_context
@require_plan_exists
@_retry_on_deadlock
def plan_resources_update(context, plan_id, resources):
    return _plan_resources_update(context,
                                  plan_id,
                                  resources)


@require_admin_context
def plan_get_all(context, marker, limit, sort_keys=None, sort_dirs=None,
                 filters=None, offset=None):
    """Retrieves all plans.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :returns: list of matching plans
    """
    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters, offset)
        # No plans would match, return empty list
        if query is None:
            return []
        return query.all()


@require_context
def plan_get_all_by_project(context, project_id, marker, limit,
                            sort_keys=None, sort_dirs=None, filters=None,
                            offset=None):
    """Retrieves all plans in a project.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param project_id: project for all plans being retrieved
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :returns: list of matching plans
    """
    session = get_session()
    with session.begin():
        authorize_project_context(context, project_id)
        # Add in the project filter without modifying the given filters
        filters = filters.copy() if filters else {}
        filters['project_id'] = project_id
        # Generate the query
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters, offset)
        # No plans would match, return empty list
        if query is None:
            return []
        return query.all()


def _process_plan_filters(query, filters):
    exact_match_filter_names = ['project_id', 'status']
    query = _list_common_process_exact_filter(models.Plan, query, filters,
                                              exact_match_filter_names)

    regex_match_filter_names = ['name', 'description']
    query = _list_common_process_regex_filter(models.Plan, query, filters,
                                              regex_match_filter_names)

    return query


###############################


@require_context
def restore_create(context, values):
    restore_ref = models.Restore()
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()
    restore_ref.update(values)

    session = get_session()
    with session.begin():
        restore_ref.save(session)
        return restore_ref


@require_context
def restore_get(context, restore_id):
    return _restore_get(context, restore_id)


@require_context
def _restore_get(context, restore_id, session=None):
    result = model_query(
        context,
        models.Restore,
        session=session
    ).filter_by(
        id=restore_id
    ).first()
    if not result:
        raise exception.RestoreNotFound(restore_id=restore_id)

    return result


@require_context
def restore_update(context, restore_id, values):
    session = get_session()
    with session.begin():
        restore_ref = _restore_get(context, restore_id, session=session)
        restore_ref.update(values)
        return restore_ref


@require_context
@_retry_on_deadlock
def restore_destroy(context, restore_id):
    session = get_session()
    with session.begin():
        restore_ref = _restore_get(context, restore_id, session=session)
        restore_ref.delete(session=session)


def is_valid_model_filters(model, filters):
    """Return True if filter values exist on the model

    :param model: a karbor model
    :param filters: dictionary of filters
    """
    for key in filters.keys():
        try:
            getattr(model, key)
        except AttributeError:
            LOG.debug("'%s' filter key is not valid.", key)
            return False
    return True


def _restore_get_query(context, session=None, project_only=False):
    return model_query(context, models.Restore, session=session,
                       project_only=project_only)


@require_admin_context
def restore_get_all(context, marker, limit, sort_keys=None, sort_dirs=None,
                    filters=None, offset=None):
    """Retrieves all restores.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :returns: list of matching restores
    """
    if filters and not is_valid_model_filters(models.Restore, filters):
        return []

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         offset, models.Restore)
        # No restores would match, return empty list
        if query is None:
            return []
        return query.all()


@require_context
def restore_get_all_by_project(context, project_id, marker, limit,
                               sort_keys=None, sort_dirs=None, filters=None,
                               offset=None):
    """Retrieves all restores in a project.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param project_id: project for all plans being retrieved
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :returns: list of matching restores
    """
    if filters and not is_valid_model_filters(models.Restore, filters):
        return []

    session = get_session()
    with session.begin():
        authorize_project_context(context, project_id)
        # Add in the project filter without modifying the given filters
        filters = filters.copy() if filters else {}
        filters['project_id'] = project_id
        # Generate the query
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         offset, models.Restore)
        # No plans would match, return empty list
        if query is None:
            return []
        return query.all()


def _process_restore_filters(query, filters):
    if filters:
        # Ensure that filters' keys exist on the model
        if not is_valid_model_filters(models.Restore, filters):
            return None
        query = query.filter_by(**filters)
    return query


###############################


@require_context
def operation_log_create(context, values):
    operation_log_ref = models.OperationLog()
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()
    operation_log_ref.update(values)

    session = get_session()
    with session.begin():
        operation_log_ref.save(session)
        return operation_log_ref


@require_context
def operation_log_get(context, operation_log_id):
    return _operation_log_get(context, operation_log_id)


@require_context
def _operation_log_get(context, operation_log_id, session=None):
    result = model_query(
        context,
        models.OperationLog,
        session=session
    ).filter_by(
        id=operation_log_id
    ).first()
    if not result:
        raise exception.OperationLogNotFound(operation_log_id=operation_log_id)

    return result


@require_context
def operation_log_update(context, operation_log_id, values):
    session = get_session()
    with session.begin():
        operation_log_ref = _operation_log_get(context, operation_log_id,
                                               session=session)
        operation_log_ref.update(values)
        return operation_log_ref


@require_context
@_retry_on_deadlock
def operation_log_destroy(context, operation_log_id):
    session = get_session()
    with session.begin():
        operation_log_ref = _operation_log_get(context, operation_log_id,
                                               session=session)
        operation_log_ref.delete(session=session)


def _operation_log_get_query(context, session=None, project_only=False):
    return model_query(context, models.OperationLog, session=session,
                       project_only=project_only)


@require_admin_context
def operation_log_get_all(context, marker, limit, sort_keys=None,
                          sort_dirs=None,
                          filters=None, offset=None):
    """Retrieves all operation logs.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :returns: list of matching operation logs
    """
    if filters and not is_valid_model_filters(models.OperationLog, filters):
        return []

    session = get_session()
    with session.begin():
        # Generate the query
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         offset, models.OperationLog)
        # No restores would match, return empty list
        if query is None:
            return []
        return query.all()


@require_context
def operation_log_get_all_by_project(context, project_id, marker, limit,
                                     sort_keys=None, sort_dirs=None,
                                     filters=None,
                                     offset=None):
    """Retrieves all operation logs in a project.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param project_id: project for all plans being retrieved
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :returns: list of matching restores
    """
    if filters and not is_valid_model_filters(models.OperationLog, filters):
        return []

    session = get_session()
    with session.begin():
        authorize_project_context(context, project_id)
        # Add in the project filter without modifying the given filters
        filters = filters.copy() if filters else {}
        filters['project_id'] = project_id
        # Generate the query
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         offset, models.OperationLog)
        # No plans would match, return empty list
        if query is None:
            return []
        return query.all()


def _process_operation_log_filters(query, filters):
    if filters:
        # Ensure that filters' keys exist on the model
        if not is_valid_model_filters(models.OperationLog, filters):
            return None
        query = query.filter_by(**filters)
    return query
###############################


@require_context
def verification_create(context, values):
    verification_ref = models.Verification()
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()
    verification_ref.update(values)

    session = get_session()
    with session.begin():
        verification_ref.save(session)
        return verification_ref


@require_context
def verification_get(context, verification_id):
    return _verification_get(context, verification_id)


@require_context
def _verification_get(context, verification_id, session=None):
    result = model_query(
        context,
        models.Verification,
        session=session
    ).filter_by(
        id=verification_id
    ).first()
    if not result:
        raise exception.VerificationNotFound(
            verification_id=verification_id)

    return result


@require_context
def verification_update(context, verification_id, values):
    session = get_session()
    with session.begin():
        verification_ref = _verification_get(
            context, verification_id, session=session)
        verification_ref.update(values)
        return verification_ref


@require_context
@_retry_on_deadlock
def verification_destroy(context, verification_id):
    session = get_session()
    with session.begin():
        verification_ref = _verification_get(context,
                                             verification_id,
                                             session=session)
        verification_ref.delete(session=session)


def _verification_get_query(context, session=None, project_only=False):
    return model_query(context, models.Verification, session=session,
                       project_only=project_only)


@require_admin_context
def verification_get_all(context, marker, limit, sort_keys=None,
                         sort_dirs=None, filters=None, offset=None):
    """Retrieves all verifications.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_verification_filters
                    function for more information
    :param offset: number of items to skip
    :returns: list of matching verifications
    """
    if filters and not is_valid_model_filters(models.Verification, filters):
        return []

    session = get_session()
    with session.begin():
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         offset, models.Verification)
        if query is None:
            return []
        return query.all()


@require_context
def verification_get_all_by_project(context, project_id, marker, limit,
                                    sort_keys=None, sort_dirs=None,
                                    filters=None, offset=None):
    """Retrieves all verifications in a project.

    If no sort parameters are specified then the returned plans are sorted
    first by the 'created_at' key and then by the 'id' key in descending
    order.

    :param context: context to query under
    :param project_id: project for all verifications being retrieved
    :param marker: the last item of the previous page, used to determine the
                   next page of results to return
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_verification_filters
                    function for more information
    :param offset: number of items to skip
    :returns: list of matching verifications
    """
    if filters and not is_valid_model_filters(models.Verification, filters):
        return []

    session = get_session()
    with session.begin():
        authorize_project_context(context, project_id)
        filters = filters.copy() if filters else {}
        filters['project_id'] = project_id
        query = _generate_paginate_query(context, session, marker, limit,
                                         sort_keys, sort_dirs, filters,
                                         offset, models.Verification)
        if query is None:
            return []
        return query.all()


def _process_verification_filters(query, filters):
    if filters:
        if not is_valid_model_filters(models.Verification, filters):
            return None
        query = query.filter_by(**filters)
    return query
###############################


@require_context
def checkpoint_record_create(context, values):
    checkpoint_record_ref = models.CheckpointRecord()
    if not values.get('id'):
        values['id'] = uuidutils.generate_uuid()
    checkpoint_record_ref.update(values)

    session = get_session()
    with session.begin():
        checkpoint_record_ref.save(session)
        return checkpoint_record_ref


@require_context
def checkpoint_record_get(context, checkpoint_record_id):
    return _checkpoint_record_get(context, checkpoint_record_id)


@require_context
def _checkpoint_record_get(context, checkpoint_record_id, session=None):
    result = model_query(
        context,
        models.CheckpointRecord,
        session=session).filter_by(
            id=checkpoint_record_id).first()
    if not result:
        raise exception.CheckpointRecordNotFound(id=checkpoint_record_id)

    return result


@require_context
def checkpoint_record_update(context, checkpoint_record_id, values):
    session = get_session()
    with session.begin():
        checkpoint_record_ref = _checkpoint_record_get(context,
                                                       checkpoint_record_id,
                                                       session=session)
        checkpoint_record_ref.update(values)
        return checkpoint_record_ref


@require_context
@_retry_on_deadlock
def checkpoint_record_destroy(context, checkpoint_record_id):
    session = get_session()
    with session.begin():
        checkpoint_record_ref = _checkpoint_record_get(context,
                                                       checkpoint_record_id,
                                                       session=session)
        checkpoint_record_ref.delete(session=session)


def _checkpoint_record_list_query(context, session, **kwargs):
    return model_query(context, models.CheckpointRecord, session=session)


def _checkpoint_record_list_process_filters(query, filters):
    exact_match_filter_names = ['project_id', 'id',
                                'checkpoint_id', 'checkpoint_status',
                                'plan_id', 'provider_id', 'operation_id']
    query = _list_common_process_exact_filter(
        models.CheckpointRecord, query, filters,
        exact_match_filter_names)

    regex_match_filter_names = ['create_by']
    query = _list_common_process_regex_filter(
        models.CheckpointRecord, query, filters,
        regex_match_filter_names)

    return query


def checkpoint_record_get_all_by_filters_sort(
        context, filters, limit=None, marker=None,
        sort_keys=None, sort_dirs=None):

    session = get_session()
    with session.begin():
        query = _generate_paginate_query(
            context, session, marker, limit,
            sort_keys, sort_dirs, filters,
            paginate_type=models.CheckpointRecord,
            use_model=True)

        return query.all() if query else []
###############################


@require_context
def _list_common_get_query(context, model, session=None):
    return model_query(context, model, session=session)


def _list_common_process_exact_filter(model, query, filters, legal_keys):
    """Applies exact match filtering to a query.

    :param model: model to apply filters to
    :param query: query to apply filters to
    :param filters: dictionary of filters; values that are lists,
                    tuples, sets, or frozensets cause an 'IN' test to
                    be performed, while exact matching ('==' operator)
                    is used for other values
    :param legal_keys: list of keys to apply exact filtering to
    :returns: the updated query.
    """

    filter_dict = {}
    for key in legal_keys:
        if key not in filters:
            continue

        value = filters.get(key)
        if isinstance(value, (list, tuple, set, frozenset)):
            if not value:
                return None  # empty IN-predicate; short circuit
            # Looking for values in a list; apply to query directly
            column_attr = getattr(model, key)
            query = query.filter(column_attr.in_(value))
        else:
            # OK, simple exact match; save for later
            filter_dict[key] = value

    # Apply simple exact matches
    if filter_dict:
        query = query.filter_by(**filter_dict)

    return query


def _list_common_process_regex_filter(model, query, filters, legal_keys):
    """Applies regular expression filtering to a query.

    :param model: model to apply filters to
    :param query: query to apply filters to
    :param filters: dictionary of filters with regex values
    :param legal_keys: list of keys to apply regex filtering to
    :returns: the updated query.
    """

    def _get_regexp_op_for_connection(db_connection):
        db_string = db_connection.split(':')[0].split('+')[0]
        regexp_op_map = {
            'postgresql': '~',
            'mysql': 'REGEXP',
            'sqlite': 'REGEXP'
        }
        return regexp_op_map.get(db_string, 'LIKE')

    db_regexp_op = _get_regexp_op_for_connection(CONF.database.connection)
    for key in legal_keys:
        if key not in filters:
            continue

        value = filters[key]
        if not isinstance(value, six.string_types):
            continue

        column_attr = getattr(model, key)
        if db_regexp_op == 'LIKE':
            query = query.filter(column_attr.op(db_regexp_op)(
                u'%' + value + u'%'))
        else:
            query = query.filter(column_attr.op(db_regexp_op)(
                value))
    return query


PAGINATION_HELPERS = {
    models.Plan: (_plan_get_query, _process_plan_filters, _plan_get),
    models.Restore: (_restore_get_query, _process_restore_filters,
                     _restore_get),
    models.Verification: (
        _verification_get_query,
        _process_verification_filters,
        _verification_get),
    models.Trigger: (_trigger_list_query, _trigger_list_process_filters,
                     _trigger_get),
    models.TriggerExecution: (_trigger_execution_list_query,
                              _trigger_execution_list_process_filters,
                              _trigger_execution_get),
    models.ScheduledOperation: (_scheduled_operation_list_query,
                                _scheduled_operation_list_process_filters,
                                _scheduled_operation_get),

    models.ScheduledOperationState: (
        _scheduled_operation_state_list_query,
        _scheduled_operation_state_list_process_filters,
        _scheduled_operation_state_get),

    models.OperationLog: (_operation_log_get_query,
                          _process_operation_log_filters,
                          _operation_log_get),

    models.ScheduledOperationLog: (
        _scheduled_operation_log_list_query,
        _scheduled_operation_log_list_process_filters,
        _scheduled_operation_log_get),
    models.CheckpointRecord: (
        _checkpoint_record_list_query,
        _checkpoint_record_list_process_filters,
        _checkpoint_record_get),
}


###############################


def _generate_paginate_query(context, session, marker, limit, sort_keys,
                             sort_dirs, filters, offset=None,
                             paginate_type=models.Plan, use_model=False,
                             **kwargs):
    """Generate the query to include the filters and the paginate options.

    Returns a query with sorting / pagination criteria added or None
    if the given filters will not yield any results.

    :param context: context to query under
    :param session: the session to use
    :param marker: the last item of the previous page; we returns the next
                    results after this value.
    :param limit: maximum number of items to return
    :param sort_keys: list of attributes by which results should be sorted,
                      paired with corresponding item in sort_dirs
    :param sort_dirs: list of directions in which results should be sorted,
                      paired with corresponding item in sort_keys
    :param filters: dictionary of filters; values that are in lists, tuples,
                    or sets cause an 'IN' operation, while exact matching
                    is used for other values, see _process_plan_filters
                    function for more information
    :param offset: number of items to skip
    :param paginate_type: type of pagination to generate
    :returns: updated query or None
    """
    get_query, process_filters, get = PAGINATION_HELPERS[paginate_type]

    sort_keys, sort_dirs = process_sort_params(sort_keys,
                                               sort_dirs,
                                               default_dir='desc')
    if use_model:
        query = get_query(context, session=session, **kwargs)
    else:
        query = get_query(context, session=session)

    if filters:
        query = process_filters(query, filters)
        if query is None:
            return None

    marker_object = None
    if marker is not None:
        marker_object = get(context, marker, session=session)

    query = sqlalchemyutils.paginate_query(query, paginate_type, limit,
                                           sort_keys,
                                           marker=marker_object,
                                           sort_dirs=sort_dirs)
    if offset:
        query = query.offset(offset)
    return query


def process_sort_params(sort_keys, sort_dirs, default_keys=None,
                        default_dir='asc'):
    """Process the sort parameters to include default keys.

    Creates a list of sort keys and a list of sort directions. Adds the default
    keys to the end of the list if they are not already included.

    When adding the default keys to the sort keys list, the associated
    direction is:
    1) The first element in the 'sort_dirs' list (if specified), else
    2) 'default_dir' value (Note that 'asc' is the default value since this is
    the default in sqlalchemy.utils.paginate_query)

    :param sort_keys: List of sort keys to include in the processed list
    :param sort_dirs: List of sort directions to include in the processed list
    :param default_keys: List of sort keys that need to be included in the
                         processed list, they are added at the end of the list
                         if not already specified.
    :param default_dir: Sort direction associated with each of the default
                        keys that are not supplied, used when they are added
                        to the processed list
    :returns: list of sort keys, list of sort directions
    :raise exception.InvalidInput: If more sort directions than sort keys
                                   are specified or if an invalid sort
                                   direction is specified
    """
    if default_keys is None:
        default_keys = ['created_at', 'id']

    # Determine direction to use for when adding default keys
    if sort_dirs and len(sort_dirs):
        default_dir_value = sort_dirs[0]
    else:
        default_dir_value = default_dir

    # Create list of keys (do not modify the input list)
    if sort_keys:
        result_keys = list(sort_keys)
    else:
        result_keys = []

    # If a list of directions is not provided, use the default sort direction
    # for all provided keys.
    if sort_dirs:
        result_dirs = []
        # Verify sort direction
        for sort_dir in sort_dirs:
            if sort_dir not in ('asc', 'desc'):
                msg = _("Unknown sort direction, must be 'desc' or 'asc'.")
                raise exception.InvalidInput(reason=msg)
            result_dirs.append(sort_dir)
    else:
        result_dirs = [default_dir_value for _sort_key in result_keys]

    # Ensure that the key and direction length match
    while len(result_dirs) < len(result_keys):
        result_dirs.append(default_dir_value)
    # Unless more direction are specified, which is an error
    if len(result_dirs) > len(result_keys):
        msg = _("Sort direction array size exceeds sort key array size.")
        raise exception.InvalidInput(reason=msg)

    # Ensure defaults are included
    for key in default_keys:
        if key not in result_keys:
            result_keys.append(key)
            result_dirs.append(default_dir_value)

    return result_keys, result_dirs


@require_admin_context
def purge_deleted_rows(context, age_in_days):
    """Purge deleted rows older than age from karbor tables."""
    try:
        age_in_days = int(age_in_days)
    except ValueError:
        msg = _('Invalid valude for age, %(age)s')
        LOG.exception(msg, {'age': age_in_days})
        raise exception.InvalidParameterValue(msg % {'age': age_in_days})
    if age_in_days <= 0:
        msg = _('Must supply a positive value for age')
        LOG.exception(msg)
        raise exception.InvalidParameterValue(msg)

    engine = get_engine()
    session = get_session()
    metadata = MetaData()
    metadata.bind = engine
    tables = []

    for model_class in models.__dict__.values():
        if hasattr(model_class, "__tablename__") and hasattr(
                model_class, "deleted"):
            tables.append(model_class.__tablename__)

    # Reorder the list so the tables are last to avoid ForeignKey constraints
    # get rid of FK constraints
    for tbl in ('plans', 'scheduled_operations'):
        try:
            tables.remove(tbl)
        except ValueError:
            LOG.warning('Expected table %(tbl)s was not found in DB.',
                        **locals())
        else:
            tables.append(tbl)

    for table in tables:
        t = Table(table, metadata, autoload=True)
        LOG.info('Purging deleted rows older than age=%(age)d days from '
                 'table=%(table)s', {'age': age_in_days, 'table': table})
        deleted_age = timeutils.utcnow() - dt.timedelta(days=age_in_days)
        try:
            with session.begin():
                result = session.execute(
                    t.delete()
                    .where(t.c.deleted_at < deleted_age))
        except db_exc.DBReferenceError:
            LOG.exception('DBError detected when purging from '
                          'table=%(table)s', {'table': table})
            raise

        rows_purged = result.rowcount
        LOG.info("Deleted %(row)d rows from table=%(table)s",
                 {'row': rows_purged, 'table': table})


###################


@require_context
def quota_get(context, project_id, resource, session=None):
    result = model_query(context, models.Quota, session=session,
                         read_deleted="no").\
        filter_by(project_id=project_id).\
        filter_by(resource=resource).\
        first()

    if not result:
        raise exception.ProjectQuotaNotFound(project_id=project_id)

    return result


@require_context
def quota_get_all_by_project(context, project_id):
    authorize_project_context(context, project_id)

    rows = model_query(context, models.Quota, read_deleted="no").\
        filter_by(project_id=project_id).\
        all()

    result = {'project_id': project_id}
    for row in rows:
        result[row.resource] = row.hard_limit

    return result


@require_admin_context
def quota_create(context, project_id, resource, limit):
    quota_ref = models.Quota()
    quota_ref.project_id = project_id
    quota_ref.resource = resource
    quota_ref.hard_limit = limit
    session = get_session()
    with session.begin():
        quota_ref.save(session)
    return quota_ref


@require_admin_context
def quota_update(context, project_id, resource, limit):
    session = get_session()
    with session.begin():
        quota_ref = quota_get(context, project_id, resource, session=session)
        quota_ref.hard_limit = limit
        quota_ref.save(session=session)


@require_admin_context
def quota_destroy(context, project_id, resource):
    session = get_session()
    with session.begin():
        quota_ref = quota_get(context, project_id, resource, session=session)
        quota_ref.delete(session=session)


###################


@require_context
def quota_class_get(context, class_name, resource, session=None):
    result = model_query(context, models.QuotaClass, session=session,
                         read_deleted="no").\
        filter_by(class_name=class_name).\
        filter_by(resource=resource).\
        first()

    if not result:
        raise exception.QuotaClassNotFound(class_name=class_name)

    return result


@require_context
def quota_class_get_all_by_name(context, class_name):
    authorize_quota_class_context(context, class_name)

    rows = model_query(context, models.QuotaClass, read_deleted="no").\
        filter_by(class_name=class_name).\
        all()

    result = {'class_name': class_name}
    for row in rows:
        result[row.resource] = row.hard_limit

    return result


def authorize_quota_class_context(context, class_name):
    """Ensures a request has permission to access the given quota class."""
    if is_user_context(context):
        if not context.quota_class:
            raise exception.NotAuthorized()
        elif context.quota_class != class_name:
            raise exception.NotAuthorized()


@require_admin_context
def quota_class_create(context, class_name, resource, limit):
    quota_class_ref = models.QuotaClass()
    quota_class_ref.class_name = class_name
    quota_class_ref.resource = resource
    quota_class_ref.hard_limit = limit
    session = get_session()
    with session.begin():
        quota_class_ref.save(session)
    return quota_class_ref


@require_admin_context
def quota_class_update(context, class_name, resource, limit):
    session = get_session()
    with session.begin():
        quota_class_ref = quota_class_get(context, class_name, resource,
                                          session=session)
        quota_class_ref.hard_limit = limit
        quota_class_ref.save(session=session)


@require_admin_context
def quota_class_destroy(context, class_name, resource):
    session = get_session()
    with session.begin():
        quota_class_ref = quota_class_get(context, class_name, resource,
                                          session=session)
        quota_class_ref.delete(session=session)


@require_admin_context
def quota_class_destroy_all_by_name(context, class_name):
    session = get_session()
    with session.begin():
        quota_classes = model_query(context, models.QuotaClass,
                                    session=session, read_deleted="no").\
            filter_by(class_name=class_name).\
            all()

        for quota_class_ref in quota_classes:
            quota_class_ref.delete(session=session)


###################


@require_context
def quota_usage_get(context, project_id, resource, session=None):
    result = model_query(context, models.QuotaUsage, session=session,
                         read_deleted="no").\
        filter_by(project_id=project_id).\
        filter_by(resource=resource).\
        first()

    if not result:
        raise exception.QuotaUsageNotFound(project_id=project_id)

    return result


@require_context
def quota_usage_get_all_by_project(context, project_id):
    authorize_project_context(context, project_id)

    rows = model_query(context, models.QuotaUsage, read_deleted="no").\
        filter_by(project_id=project_id).\
        all()

    result = {'project_id': project_id}
    for row in rows:
        result[row.resource] = dict(in_use=row.in_use, reserved=row.reserved)

    return result


@require_admin_context
def quota_usage_create(context, project_id, resource, in_use, reserved,
                       until_refresh, session=None):
    quota_usage_ref = models.QuotaUsage()
    quota_usage_ref.project_id = project_id
    quota_usage_ref.resource = resource
    quota_usage_ref.in_use = in_use
    quota_usage_ref.reserved = reserved
    quota_usage_ref.until_refresh = until_refresh
    if not session:
        session = get_session()
        with session.begin():
            quota_usage_ref.save(session=session)
    else:
        quota_usage_ref.save(session=session)

    return quota_usage_ref


###################


@require_context
def reservation_get(context, uuid, session=None):
    result = model_query(context, models.Reservation, session=session,
                         read_deleted="no").\
        filter_by(uuid=uuid).first()

    if not result:
        raise exception.ReservationNotFound(uuid=uuid)

    return result


@require_context
def reservation_get_all_by_project(context, project_id):
    authorize_project_context(context, project_id)

    rows = model_query(context, models.Reservation, read_deleted="no").\
        filter_by(project_id=project_id).all()

    result = {'project_id': project_id}
    for row in rows:
        result.setdefault(row.resource, {})
        result[row.resource][row.uuid] = row.delta

    return result


@require_admin_context
def reservation_create(context, uuid, usage, project_id, resource, delta,
                       expire, session=None):
    reservation_ref = models.Reservation()
    reservation_ref.uuid = uuid
    reservation_ref.usage_id = usage['id']
    reservation_ref.project_id = project_id
    reservation_ref.resource = resource
    reservation_ref.delta = delta
    reservation_ref.expire = expire
    if not session:
        session = get_session()
        with session.begin():
            reservation_ref.save(session=session)
    else:
        reservation_ref.save(session=session)
    return reservation_ref


@require_admin_context
def reservation_destroy(context, uuid):
    session = get_session()
    with session.begin():
        reservation_ref = reservation_get(context, uuid, session=session)
        reservation_ref.delete(session=session)


###################


# NOTE(johannes): The quota code uses SQL locking to ensure races don't
# cause under or over counting of resources. To avoid deadlocks, this
# code always acquires the lock on quota_usages before acquiring the lock
# on reservations.

def _get_quota_usages(context, session, project_id):
    # Broken out for testability
    rows = model_query(context, models.QuotaUsage,
                       read_deleted="no",
                       session=session).\
        filter_by(project_id=project_id).\
        with_lockmode('update').\
        all()
    return dict((row.resource, row) for row in rows)


@require_context
def quota_reserve(context, resources, quotas, deltas, expire,
                  until_refresh, max_age, project_id=None):
    elevated = context.elevated()
    session = get_session()
    with session.begin():
        if project_id is None:
            project_id = context.project_id

        # Get the current usages
        usages = _get_quota_usages(context, session, project_id)

        # Handle usage refresh
        work = set(deltas.keys())
        while work:
            resource = work.pop()

            # Do we need to refresh the usage?
            refresh = False
            if resource not in usages:
                usages[resource] = quota_usage_create(elevated,
                                                      project_id,
                                                      resource,
                                                      0, 0,
                                                      until_refresh or None,
                                                      session=session)
                refresh = True
            elif usages[resource].in_use < 0:
                # Negative in_use count indicates a desync, so try to
                # heal from that...
                refresh = True
            elif usages[resource].until_refresh is not None:
                usages[resource].until_refresh -= 1
                if usages[resource].until_refresh <= 0:
                    refresh = True
            elif max_age and (usages[resource].updated_at -
                              timeutils.utcnow()).seconds >= max_age:
                refresh = True

            # OK, refresh the usage
            if refresh:
                # Grab the sync routine
                sync = resources[resource].sync
                updates = {}
                if sync:
                    updates = sync(elevated, project_id, session)
                for res, in_use in updates.items():
                    # Make sure we have a destination for the usage!
                    if res not in usages:
                        usages[res] = quota_usage_create(elevated,
                                                         project_id,
                                                         res,
                                                         0, 0,
                                                         until_refresh or None,
                                                         session=session)

                    # Update the usage
                    usages[res].in_use = in_use
                    usages[res].until_refresh = until_refresh or None

                    # Because more than one resource may be refreshed
                    # by the call to the sync routine, and we don't
                    # want to double-sync, we make sure all refreshed
                    # resources are dropped from the work set.
                    work.discard(res)

                    # NOTE(Vek): We make the assumption that the sync
                    #            routine actually refreshes the
                    #            resources that it is the sync routine
                    #            for.  We don't check, because this is
                    #            a best-effort mechanism.

        # Check for deltas that would go negative
        unders = [res for res, delta in deltas.items()
                  if delta < 0 and
                  delta + usages[res].in_use < 0]

        # Now, let's check the quotas
        # NOTE(Vek): We're only concerned about positive increments.
        #            If a project has gone over quota, we want them to
        #            be able to reduce their usage without any
        #            problems.
        overs = [res for res, delta in deltas.items()
                 if quotas[res] >= 0 and delta >= 0 and
                 quotas[res] < delta + usages[res].total]

        # NOTE(Vek): The quota check needs to be in the transaction,
        #            but the transaction doesn't fail just because
        #            we're over quota, so the OverQuota raise is
        #            outside the transaction.  If we did the raise
        #            here, our usage updates would be discarded, but
        #            they're not invalidated by being over-quota.

        # Create the reservations
        if not overs:
            reservations = []
            for resource, delta in deltas.items():
                reservation = reservation_create(elevated,
                                                 str(uuid.uuid4()),
                                                 usages[resource],
                                                 project_id,
                                                 resource, delta, expire,
                                                 session=session)
                reservations.append(reservation.uuid)

                # Also update the reserved quantity
                # NOTE(Vek): Again, we are only concerned here about
                #            positive increments.  Here, though, we're
                #            worried about the following scenario:
                #
                #            1) User initiates resize down.
                #            2) User allocates a new instance.
                #            3) Resize down fails or is reverted.
                #            4) User is now over quota.
                #
                #            To prevent this, we only update the
                #            reserved value if the delta is positive.
                if delta > 0:
                    usages[resource].reserved += delta

        # Apply updates to the usages table
        for usage_ref in usages.values():
            usage_ref.save(session=session)

    if unders:
        LOG.warning(_("Change will make usage less than 0 for the following "
                      "resources: %(unders)s") % unders)
    if overs:
        usages = dict((k, dict(in_use=v['in_use'], reserved=v['reserved']))
                      for k, v in usages.items())
        raise exception.OverQuota(overs=sorted(overs), quotas=quotas,
                                  usages=usages)

    return reservations


def _quota_reservations(session, context, reservations):
    """Return the relevant reservations."""

    # Get the listed reservations
    return model_query(context, models.Reservation,
                       read_deleted="no",
                       session=session).\
        filter(models.Reservation.uuid.in_(reservations)).\
        with_lockmode('update').\
        all()


@require_context
def reservation_commit(context, reservations, project_id=None):
    session = get_session()
    with session.begin():
        usages = _get_quota_usages(context, session, project_id)

        for reservation in _quota_reservations(session, context, reservations):
            usage = usages[reservation.resource]
            if reservation.delta >= 0:
                usage.reserved -= reservation.delta
            usage.in_use += reservation.delta

            reservation.delete(session=session)

        for usage in usages.values():
            usage.save(session=session)


@require_context
def reservation_rollback(context, reservations, project_id=None):
    session = get_session()
    with session.begin():
        usages = _get_quota_usages(context, session, project_id)

        for reservation in _quota_reservations(session, context, reservations):
            usage = usages[reservation.resource]
            if reservation.delta >= 0:
                usage.reserved -= reservation.delta

            reservation.delete(session=session)

        for usage in usages.values():
            usage.save(session=session)


@require_admin_context
def quota_destroy_all_by_project(context, project_id):
    session = get_session()
    with session.begin():
        quotas = model_query(context, models.Quota, session=session,
                             read_deleted="no").\
            filter_by(project_id=project_id).\
            all()

        for quota_ref in quotas:
            quota_ref.delete(session=session)

        quota_usages = model_query(context, models.QuotaUsage,
                                   session=session, read_deleted="no").\
            filter_by(project_id=project_id).\
            all()

        for quota_usage_ref in quota_usages:
            quota_usage_ref.delete(session=session)

        reservations = model_query(context, models.Reservation,
                                   session=session, read_deleted="no").\
            filter_by(project_id=project_id).\
            all()

        for reservation_ref in reservations:
            reservation_ref.delete(session=session)


@require_admin_context
def reservation_expire(context):
    session = get_session()
    with session.begin():
        current_time = timeutils.utcnow()
        results = model_query(context, models.Reservation, session=session,
                              read_deleted="no").\
            filter(models.Reservation.expire < current_time).\
            all()

        if results:
            for reservation in results:
                if reservation.delta >= 0:
                    reservation.usage.reserved -= reservation.delta
                    reservation.usage.save(session=session)

                reservation.delete(session=session)


################
