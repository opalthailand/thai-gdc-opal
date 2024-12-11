#!/usr/bin/env python
# encoding: utf-8

import ckan.logic as logic
import ckan.logic.action.update as logic_action_update
import ckan.logic.schema as schema_
import ckan.model as model
import logging
import ckan.plugins.toolkit as toolkit
from ckan.lib.jobs import DEFAULT_QUEUE_NAME
import ckan.lib.dictization as d
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions as dfunc
from six import string_types
import ckan.model.misc as misc
from ckan.common import config
import ckan
from ckanext.thai_gdc import helpers as thai_gdc_h
from ckanext.thai_gdc import blueprint as thai_gdc_b
from sqlalchemy import func

_check_access = logic.check_access
_get_or_bust = logic.get_or_bust
NotFound = logic.NotFound
_validate = dfunc.validate
ValidationError = logic.ValidationError
_get_action = logic.get_action

log = logging.getLogger(__name__)

import requests
def send_line_notification(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": "Bearer cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)

@toolkit.side_effect_free
def status_show(context, data_dict):
    send_line_notification('status_show')
    return {
        'site_title': config.get('ckan.site_title'),
        'site_description': config.get('ckan.site_description'),
        'site_url': config.get('ckan.site_url'),
        'thaigdc_catalog_type': config.get('thai_gdc.catalog_org_type'),
        'thaigdc_is_as_a_service': config.get('thai_gdc.is_as_a_service'),
        'thaigdc_version': thai_gdc_h.get_extension_version('version'),
        'thaigdc_update': {"thai_gdc":thai_gdc_h.get_extension_version('date'), "xloader":config.get('thaigdc.xloader.extension_update_date',''), "discovery":config.get('thaigdc.discovery.extension_update_date','')},
        'ckan_version': ckan.__version__,
        'error_emails_to': config.get('email_to'),
        'locale_default': config.get('ckan.locale_default'),
        'extensions': config.get('ckan.plugins').split(),
    }

def group_type_patch(context, data_dict):
    send_line_notification('group_type_patch')
    _check_access('sysadmin', context, data_dict)
    try:
        for patch_dict in data_dict.get('patch_list'):
            group_id = _get_or_bust(patch_dict, 'name')
            group_type = _get_or_bust(patch_dict, 'type')
            if config.get('scheming.group_schemas', '') != '':
                model.Session.query(model.Group).filter(model.Group.name == group_id).filter(model.Group.state == 'active').filter(model.Group.is_organization == False).update({"type": group_type})
                model.Session.commit()
        return 'success'
    except:
        return 'fail'

def _tag_search(context, data_dict):
    send_line_notification('_tag_search')
    model = context['model']

    terms = data_dict.get('query') or data_dict.get('q') or []
    if isinstance(terms, string_types):
        terms = [terms]
    terms = [t.strip() for t in terms if t.strip()]

    if 'fields' in data_dict:
        log.warning('"fields" parameter is deprecated.  '
                    'Use the "query" parameter instead')

    fields = data_dict.get('fields', {})
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Tag)

    if 'vocabulary_id' in data_dict:
        # Filter by vocabulary.
        vocab = model.Vocabulary.get(_get_or_bust(data_dict, 'vocabulary_id'))
        if not vocab:
            raise NotFound
        q = q.filter(model.Tag.vocabulary_id == vocab.id)
    else:
        # If no vocabulary_name in data dict then show free tags only.
        q = q.filter(model.Tag.vocabulary_id == None)
        # If we're searching free tags, limit results to tags that are
        # currently applied to a package.
        q = q.distinct().join(model.Tag.package_tags)

    for field, value in fields.items():
        if field in ('tag', 'tags'):
            terms.append(value)

    if not len(terms):
        return [], 0

    for term in terms:
        escaped_term = misc.escape_sql_like_special_characters(
            term, escape='\\')
        q = q.filter(model.Tag.name.ilike('%' + escaped_term + '%'))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    return q.all(), count

@logic.side_effect_free
def tag_list(context, data_dict):
    send_line_notification('tag_list')

    model = context['model']

    vocab_id_or_name = data_dict.get('vocabulary_id')
    query = data_dict.get('query') or data_dict.get('q')
    if query:
        query = query.strip()
    all_fields = data_dict.get('all_fields', None)

    _check_access('tag_list', context, data_dict)

    if query:
        tags, count = _tag_search(context, data_dict)
    else:
        #tags = model.Tag.all(vocab_id_or_name)
        tags = None

    if tags:
        if all_fields:
            tag_list = model_dictize.tag_list_dictize(tags, context)
        else:
            tag_list = [tag.name for tag in tags]
    else:
        tag_list = []

    return tag_list

def bulk_update_public(context, data_dict):
    send_line_notification('bulk_update_public')
    from ckan.lib.search import rebuild

    _check_access('bulk_update_public', context, data_dict)
    for dataset in data_dict['datasets']:
        model.Session.query(model.PackageExtra).filter(model.PackageExtra.package_id == dataset).filter(model.PackageExtra.key == 'allow_harvest').update({"value": "True"})
    model.Session.commit()
    [rebuild(package_id) for package_id in data_dict['datasets']]
    logic_action_update._bulk_update_dataset(context, data_dict, {'private': False})

def dataset_bulk_import(context, data_dict):
    send_line_notification('dataset_bulk_import')
    _check_access('package_create', context, data_dict)
    import_uuid = _get_or_bust(data_dict, 'import_uuid')
    queue = DEFAULT_QUEUE_NAME
    
    toolkit.enqueue_job(thai_gdc_b._record_type_process, [data_dict], title=u'import record package import_id:{}'.format(import_uuid), queue=queue)
                
    toolkit.enqueue_job(thai_gdc_b._stat_type_process, [data_dict], title=u'import stat package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(thai_gdc_b._gis_type_process, [data_dict], title=u'import gis package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(thai_gdc_b._multi_type_process, [data_dict], title=u'import multi package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(thai_gdc_b._other_type_process, [data_dict], title=u'import other package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(thai_gdc_b._finished_process, [data_dict], title=u'import finished import_id:{}'.format(import_uuid), queue=queue)

def resource_view_create(context, data_dict):
    send_line_notification('resource_view_create')
    '''Creates a new resource view.

    :param resource_id: id of the resource
    :type resource_id: string
    :param title: the title of the view
    :type title: string
    :param description: a description of the view (optional)
    :type description: string
    :param view_type: type of view
    :type view_type: string
    :param config: options necessary to recreate a view state (optional)
    :type config: JSON string

    :returns: the newly created resource view
    :rtype: dictionary

    '''
    model = context['model']

    resource_id = _get_or_bust(data_dict, 'resource_id')
    view_type = _get_or_bust(data_dict, 'view_type')
    view_plugin = ckan.lib.datapreview.get_view_plugin(view_type)

    if not view_plugin:
        raise ValidationError(
            {"view_type": "No plugin found for view_type {view_type}".format(
                view_type=view_type
            )}
        )

    default = logic.schema.default_create_resource_view_schema(view_plugin)
    schema = context.get('schema', default)
    plugin_schema = view_plugin.info().get('schema', {})
    schema.update(plugin_schema)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    _check_access('resource_view_create', context, data_dict)

    if context.get('preview'):
        return data

    max_order = model.Session.query(
        func.max(model.ResourceView.order)
    ).filter_by(resource_id=resource_id).first()

    order = 0
    if max_order[0] is not None:
        order = max_order[0] + 1
    data['order'] = order

    context['resource'] = model.Resource.get(resource_id)

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    pkg_dict = _get_action('package_patch')(dict(context, return_type='dict'),
        {'id': context['resource'].package_id})
    
    send_line_notification('resource')
    send_line_notification(str(context.get('resource')))
    send_line_notification('resource_cdp')
    send_line_notification(str(context.get('resource').keys()))

    return model_dictize.resource_view_dictize(resource_view, context)

def resource_view_update(context, data_dict):
    send_line_notification('resource_view_update')
    '''Update a resource view.

    To update a resource_view you must be authorized to update the resource
    that the resource_view belongs to.

    For further parameters see ``resource_view_create()``.

    :param id: the id of the resource_view to update
    :type id: string

    :returns: the updated resource_view
    :rtype: string

    '''
    model = context['model']
    id = _get_or_bust(data_dict, "id")

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        raise NotFound

    view_plugin = ckan.lib.datapreview.get_view_plugin(resource_view.view_type)
    schema = (context.get('schema') or
              schema_.default_update_resource_view_schema(view_plugin))
    plugin_schema = view_plugin.info().get('schema', {})
    schema.update(plugin_schema)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    context['resource_view'] = resource_view
    context['resource'] = model.Resource.get(resource_view.resource_id)

    _check_access('resource_view_update', context, data_dict)

    if context.get('preview'):
        return data

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    pkg_dict = _get_action('package_patch')(dict(context, return_type='dict'),
        {'id': context['resource'].package_id})
    return model_dictize.resource_view_dictize(resource_view, context)

def resource_view_delete(context, data_dict):
    send_line_notification('resource_view_delete')
    '''Delete a resource_view.

    :param id: the id of the resource_view
    :type id: string

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        raise NotFound

    context["resource_view"] = resource_view
    context['resource'] = model.Resource.get(resource_view.resource_id)
    _check_access('resource_view_delete', context, data_dict)

    resource_view.delete()
    model.repo.commit()
    pkg_dict = _get_action('package_patch')(dict(context, return_type='dict'),
        {'id': context['resource'].package_id})

def resource_view_reorder(context, data_dict):
    send_line_notification('resource_view_reorder')
    '''Reorder resource views.

    :param id: the id of the resource
    :type id: string
    :param order: the list of id of the resource to update the order of the views
    :type order: list of strings

    :returns: the updated order of the view
    :rtype: dictionary
    '''
    model = context['model']
    id, order = _get_or_bust(data_dict, ["id", "order"])
    if not isinstance(order, list):
        raise ValidationError({"order": "Must supply order as a list"})
    if len(order) != len(set(order)):
        raise ValidationError({"order": "No duplicates allowed in order"})
    resource = model.Resource.get(id)
    context['resource'] = resource

    _check_access('resource_view_reorder', context, data_dict)

    q = model.Session.query(model.ResourceView.id).filter_by(resource_id=id)
    existing_views = [res[0] for res in
                      q.order_by(model.ResourceView.order).all()]
    ordered_views = []
    for view in order:
        try:
            existing_views.remove(view)
            ordered_views.append(view)
        except ValueError:
            raise ValidationError(
                {"order": "View {view} does not exist".format(view=view)}
            )
    new_order = ordered_views + existing_views

    for num, view in enumerate(new_order):
        model.Session.query(model.ResourceView).\
            filter_by(id=view).update({"order": num + 1})
    model.Session.commit()
    pkg_dict = _get_action('package_patch')(dict(context, return_type='dict'),
        {'id': context['resource'].package_id})
    return {'id': id, 'order': new_order}