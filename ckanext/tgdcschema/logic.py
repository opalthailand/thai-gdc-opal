# encoding: utf-8

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
from ckan.lib.search.common import make_connection
from ckan.common import _
import ckan.lib.dictization.model_dictize as model_dictize
import ast

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust
_check_access = logic.check_access
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized

def _isEnglish(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True

@toolkit.side_effect_free
def similar_package_search(context, data_dict):

    query = _get_or_bust(data_dict, 'query')
    if not 'rows' in data_dict:
        rows = 30
    else:
        rows = data_dict['rows']
    # max_num = data_dict['max_num'] or 20
    # if max_num > 20:
    #     max_num = 20
    solr = make_connection()
    query = query.replace('+',' ')
    query = query.strip()
    query = " ".join(query.split())
    q_list = query.split()
    q_list_result = []
    for q_item in q_list:
        if _isEnglish(q_item):
            q_item = 'text:'+q_item
        else:
            q_item = 'text:*'+q_item+'*'
        q_list_result.append(q_item)
    q = ' OR '.join(q_list_result)
    query = q

    #mlt_dict = {'mlt':'true','fl':'id,validated_data_dict,score','mlt.fl':'title,notes','sort':'score desc, metadata_modified desc','fq':'state:active +capacity:public','mlt.count':20,'rows':20}

    mlt_dict = {'fl':'id,title,notes,tags,organization,groups,score','sort':'score desc, metadata_modified desc','fq':'state:active +capacity:public','rows':rows}

    if 'mintf' in data_dict:
        mlt_dict['mlt.mintf'] = data_dict['mintf']
    
    if 'mindf' in data_dict:
        mlt_dict['mlt.mindf'] = data_dict['mindf']
    
    if 'maxdf' in data_dict:
        mlt_dict['mlt.maxdf'] = data_dict['maxdf']

    results = solr.search(q=query,**mlt_dict)

    log.debug('Similar datasets for {}:'.format(id))
    print('Similar datasets for {}:'.format(id))
    for doc in results.docs:
        log.debug('  {id} (score {score})'.format(**doc))
        print('  {id} (score {score})'.format(**doc))
    return results.raw_response#['response'][json.loads(doc['validated_data_dict']) for doc in results.docs]

def member_create(context, data_dict=None):
    model = context['model']
    user = context['user']

    group_id, obj_id, obj_type, capacity = \
        _get_or_bust(data_dict, ['id', 'object', 'object_type', 'capacity'])

    group = model.Group.get(group_id)
    if not group:
        raise NotFound('Group was not found.')

    obj_class = logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound('%s was not found.' % obj_type.title())

    _check_access('member_create', context, data_dict)

    # Look up existing, in case it exists
    member = model.Session.query(model.Member).\
        filter(model.Member.table_name == obj_type).\
        filter(model.Member.table_id == obj.id).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == 'active').first()
    if member:
        user_obj = model.User.get(user)
        if user_obj and member.table_name == u'user' and \
                member.table_id == user_obj.id and \
                member.capacity == u'admin' and \
                capacity != u'admin':
            raise NotAuthorized("Administrators cannot revoke their "
                                "own admin status")
    else:
        member = model.Member(table_name=obj_type,
                              table_id=obj.id,
                              group_id=group.id,
                              state='active')
        member.group = group
    member.capacity = capacity

    model.Session.add(member)
    if not context.get("defer_commit"):
        model.repo.commit()

    if obj_type == 'package' and capacity == 'public':
        _related_group_add(context, obj.id, group.id)

    return model_dictize.member_dictize(member, context)

def _related_group_add(context, package, primary_group):
    group_dict = logic.get_action('group_show')(context, {'id':primary_group, 'include_dataset_count':False, 'include_users':False})
    model = context['model']
    user = context['user']
    if group_dict['type'] == 'category01' and 'related_group' in group_dict:
        if '{' not in group_dict['related_group'][0] and '}' not in group_dict['related_group'][0]:
            r_group = "[u'"+group_dict['related_group'][0]+"']"
        else:
            r_group = str(group_dict['related_group'][0]).replace('{','').replace('}','').split(',')
        log.info(r_group)
        for other_group in r_group:
            try:
                group_id = other_group
                obj_id = package
                obj_type = 'package'
                capacity = 'public'

                group = model.Group.get(group_id)
                if not group:
                    raise NotFound('Group was not found.')

                obj_class = logic.model_name_to_class(model, obj_type)
                obj = obj_class.get(obj_id)
                if not obj:
                    raise NotFound('%s was not found.' % obj_type.title())

                # Look up existing, in case it exists
                member = model.Session.query(model.Member).\
                    filter(model.Member.table_name == obj_type).\
                    filter(model.Member.table_id == obj.id).\
                    filter(model.Member.group_id == group.id).\
                    filter(model.Member.state == 'active').first()
                if member:
                    user_obj = model.User.get(user)
                    if user_obj and member.table_name == u'user' and \
                            member.table_id == user_obj.id and \
                            member.capacity == u'admin' and \
                            capacity != u'admin':
                        raise NotAuthorized("Administrators cannot revoke their "
                                            "own admin status")
                else:
                    member = model.Member(table_name=obj_type,
                                        table_id=obj.id,
                                        group_id=group.id,
                                        state='active')
                    member.group = group
                member.capacity = capacity

                model.Session.add(member)
                if not context.get("defer_commit"):
                    model.repo.commit()
            except NotFound:
                continue
