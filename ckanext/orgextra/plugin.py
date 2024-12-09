# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model

class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelper)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')

    # ITemplateHelper
    def get_helpers(self):
        return {'get_all_organizations': self._get_all_organizations}

    def _get_all_organizations(self):
        """
        Fetches all organizations from the CKAN database.
        """
        return model.Session.query(model.Group).filter(model.Group.type == 'organization', model.Group.state == 'active').all()
    def update_config(self, config_):
         toolkit.add_template_directory(config_, 'templates')
