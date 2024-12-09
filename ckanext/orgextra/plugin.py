# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model



class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def get_users(self):
        try:
            users = model.User.all()
            return [user.name for user in users]
        except Exception as e:
            return []  # Handle potential errors gracefully

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_public_directory(config_, 'fanstatic')
        toolkit.add_resource('fanstatic',
            'orgextra')
        toolkit.add_template_global(config_, 'get_users', self.get_users)
