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
        if ('disabled' in values):
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
        raise exception.OperationLogNotFound(restore_id=operation_log_id)

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
    models.Trigger: (_trigger_list_query, _trigger_list_process_filters,
                     _trigger_get),
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
