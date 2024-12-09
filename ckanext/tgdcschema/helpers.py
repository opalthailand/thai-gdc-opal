#!/usr/bin/env python
# encoding: utf-8

import ckan.logic as logic
import logging
from ckan import model
from ckanext.harvest.model import HarvestObject
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

def get_action(action_name, data_dict=None):
    '''Calls an action function from a template. Deprecated in CKAN 2.3.'''
    if data_dict is None:
        data_dict = {}
    return logic.get_action(action_name)({}, data_dict)

def get_harvest_detail(package_id, all_field=None):
    harvest_object = model.Session.query(HarvestObject) \
        .filter(HarvestObject.package_id == package_id) \
        .filter(HarvestObject.current==True).first() # noqa
    if harvest_object:
        if all_field:
            from ckan.lib.helpers import json
            return {'id':harvest_object.id,'content':json.loads(harvest_object.content)}
        else:
            return {'id':harvest_object.id}
    return None

def is_user_sysadmin(user=None):
    """Returns True if authenticated user is sysadmim
    :rtype: boolean
    """
    if user is None:
        user = toolkit.g.userobj
    return user is not None and user.sysadmin

def user_has_admin_access(include_editor_access=False):
    user = toolkit.g.userobj
    # If user is "None" - they are not logged in.
    if user is None:
        return False
    if is_user_sysadmin(user):
        return True

    groups_admin = user.get_groups('organization', 'admin')
    groups_editor = user.get_groups('organization', 'editor') if include_editor_access else []
    groups_list = groups_admin + groups_editor
    organisation_list = [g for g in groups_list if g.type == 'organization']
    return len(organisation_list) > 0

def get_all_groups_all_type(type=None,id='id'):
    
    if type:
        groups = toolkit.get_action('group_list')(
            data_dict={'type':type, 'include_dataset_count': False, 'all_fields': True})
        try:
            pkg_group_ids = set(group['id'] for group
                        in toolkit.g.pkg_dict.get('groups', []))
        except:
            pkg_group_ids = []
    else:
        return []
    
    if id == 'name':
        return [[group['name'], group['display_name']]
                            for group in groups if
                            group['id'] not in pkg_group_ids]

    return [[group['id'], group['display_name']]
                            for group in groups if
                            group['id'] not in pkg_group_ids]
