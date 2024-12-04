import ckan.plugins as p
import ckan.plugins.toolkit as tk
import logging
from ckanext.cdp import actions, auth

log = logging.getLogger(__name__)


class CDPPlugin(p.SingletonPlugin):
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceController)  
    p.implements(p.ITemplateHelpers)

    def get_actions(self):
        return {
            'push_to_cdp': actions.push_to_cdp,
        }

    def get_auth_functions(self):
        return {
            'push_to_cdp': auth.push_to_cdp,
        }

    def before_create(self, context, resource):
        return resource

    def after_create(self, context, resource):
        data_dict = {'id': resource['id'], 'push_to_cdp': resource.get('push_to_cdp')}
        tk.get_action('push_to_cdp')(context, data_dict)
        return resource


    def before_update(self, context, resource):
        return resource

    def after_update(self, context, resource):
        data_dict = {'id': resource['id'], 'push_to_cdp': resource.get('push_to_cdp')}
        tk.get_action('push_to_cdp')(context, data_dict)
        return resource

    def before_delete(self, context, resource_dict):
        return resource_dict

    def after_delete(self, context, resource_dict):
        return resource_dict

    def before_show(self, context, resource):
        return resource

    def after_show(self, context, resource):
        return resource

    def get_helpers(self):
        return {}