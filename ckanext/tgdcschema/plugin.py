#!/usr/bin/env python
# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.logic.validators as validators
from ckanext.tgdcschema import helpers as tgdc
import re
from itertools import count
from ckanext.tgdcschema.logic import (
   similar_package_search, member_create
)
from ckanext.tgdcschema.resource_upload_validator import (
   validate_upload_type
)
import logging
import ckan.lib.navl.dictization_functions as df
from ckanext.tgdcschema import blueprint
import ckan.authz as authz
import ckan.logic.auth as logic_auth
from ckan import model
from ckanext.harvest.model import HarvestObject

Invalid = df.Invalid
log = logging.getLogger(__name__)
_ = toolkit._
g = toolkit.g

class TgdcschemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IPackageController, inherit=True)
    
    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "tgdcschema")

    # IBlueprint
    def get_blueprint(self):
        return blueprint.tgdcschema
    
    def _isEnglish(self, s):
        try:
            s.encode(encoding='utf-8').decode('ascii')
        except UnicodeDecodeError:
            return False
        else:
            return True

    def before_dataset_search(self, search_params):
        if 'q' in search_params:
            q = search_params['q']
            lelist = ["+","&&","||","!","(",")","{","}","[","]","^","~","*","?",":","/"]
            contains_word = lambda s, l: any(map(lambda x: x in s, l))
            if len(q) > 0 and len([e for e in lelist if e in q]) == 0:
                q_list = q.split()
                q_list_result = []
                for q_item in q_list:
                    if contains_word(q, ['AND','OR','NOT']) and q_item not in ['AND','OR','NOT'] and not self._isEnglish(q_item):
                        q_item = 'text:*'+q_item+'*'
                    elif contains_word(q, ['AND','OR','NOT']) and q_item not in ['AND','OR','NOT'] and self._isEnglish(q_item):
                        q_item = 'text:'+q_item
                    elif not contains_word(q, ['AND','OR','NOT']):
                        q_item = '*'+q_item+'*'
                    q_list_result.append(q_item)
                q = ' '.join(q_list_result)
            search_params['q'] = q
            if not contains_word(q, ['AND','OR','NOT']):
                search_params['defType'] = 'edismax'
                search_params['qf'] = 'name^4 title^4 tags^3 groups^2 organization^2 notes^2 maintainer^2 text'
        return search_params

    def after_dataset_show(self, context,package_dict):
        harvest_object = model.Session.query(HarvestObject) \
            .filter(HarvestObject.package_id == package_dict['id']) \
            .filter(HarvestObject.current==True).first() # noqa
        if harvest_object:
            from ckan.lib.helpers import json
            content = json.loads(harvest_object.content)
            if 'extras' not in package_dict:
                package_dict['extras'] = []
            package_dict['extras'].append({'key': 'harvest_object_metadata_created', 'value': content.get('metadata_created')})
            package_dict['extras'].append({'key': 'harvest_object_metadata_modified', 'value': content.get('metadata_modified')})

    def after_dataset_search(self, search_results, search_params):
        package_list = search_results['results']
        for package_dict in package_list:
            harvest_object = model.Session.query(HarvestObject) \
                .filter(HarvestObject.package_id == package_dict['id']) \
                .filter(HarvestObject.current==True).first() # noqa
            if harvest_object:
                from ckan.lib.helpers import json
                content = json.loads(harvest_object.content)
                if 'extras' not in package_dict:
                    package_dict['extras'] = []
                package_dict['extras'].append({'key': 'harvest_object_metadata_created', 'value': content.get('metadata_created')})
                package_dict['extras'].append({'key': 'harvest_object_metadata_modified', 'value': content.get('metadata_modified')})
        return search_results
    
    # IResourceController
    def before_resource_create(self, context, resource):
        validate_upload_type(resource)
        pass

    def before_resource_update(self, context, current, resource):
        validate_upload_type(resource)
        pass

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'gdc_get_action': tgdc.get_action,
            'gdc_get_harvest_detail': tgdc.get_harvest_detail,
            'gdc_get_all_groups_all_type' : tgdc.get_all_groups_all_type,
        }
    
    # IValidators
    def get_validators(self):
        return {
            'tag_name_validator': tag_name_validator,
            'tag_string_convert': tag_string_convert,
        }
    
    # IActions
    def get_actions(self):
        action_functions = {
            'similar_package_search': similar_package_search,
            'member_create': member_create,
        }
        return action_functions
    
    # IAuthFunctions
    def get_auth_functions(self):
        auth_functions = {
            'member_create': self.member_create
        }
        return auth_functions

    @toolkit.chained_auth_function
    def member_create(self, next_auth, context, data_dict):
        group = logic_auth.get_group_object(context, data_dict)
        user = context['user']

        # User must be able to update the group to add a member to it
        permission = 'update'
        # However if the user is member of group then they can add/remove datasets
        if not group.is_organization and data_dict.get('object_type') == 'package':
            permission = 'manage_group'

        blueprint, action = toolkit.get_endpoint()
        if blueprint in ['package', 'dataset'] and action in ['groups']:
            authorized = tgdc.user_has_admin_access(include_editor_access=True)
            # Fallback to the default CKAN behaviour
            if not authorized:
                authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                        user,
                                                                        permission)
        else:
            authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                    user,
                                                                    permission)
        
        if not authorized:
            return {'success': False,
                    'msg': _('User %s not authorized to edit group %s') %
                            (str(user), group.id)}
        else:
            return {'success': True}

def tag_name_validator(value, context):

    tagname_match = re.compile('[ก-๙\w \-.]*', re.UNICODE)
    if not tagname_match.match(value, re.U):
        raise Invalid(_('Tag "%s" can only contain alphanumeric '
                        'characters, spaces (" "), hyphens ("-"), '
                        'underscores ("_") or dots (".")') % (value))
    return value

def tag_string_convert(key, data, errors, context):
    '''Takes a list of tags that is a comma-separated string (in data[key])
    and parses tag names. These are added to the data dict, enumerated. They
    are also validated.'''

    if isinstance(data[key], str):
        tags = [tag.strip() \
                for tag in data[key].split(',') \
                if tag.strip()]
    else:
        tags = data[key]
    
    log.info(tags)

    current_index = max( [int(k[1]) for k in data.keys() if len(k) == 3 and k[0] == 'tags'] + [-1] )

    for num, tag in zip(count(current_index+1), tags):
        data[('tags', num, 'name')] = tag

    for tag in tags:
        validators.tag_length_validator(tag, context)
        tag_name_validator(tag, context)
