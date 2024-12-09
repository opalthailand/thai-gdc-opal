# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model
from sqlalchemy import Table, select

class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def get_users(self):
        try:
            user_table = model.User.__table__ # Access the user table directly
            query = select([user_table.c.name]).where(user_table.c.state == 'active') # Select only active users
            result = model.Session.execute(query).fetchall()
            return [row[0] for row in result] # Extract usernames
        except Exception as e:
            toolkit.c.user_list_error = "Error retrieving users: " + str(e) # Store error message for template
            return []

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_public_directory(config_, 'fanstatic')
        toolkit.add_resource('fanstatic',
            'orgextra')
        toolkit.add_template_global(config_, 'get_users', self.get_users)
