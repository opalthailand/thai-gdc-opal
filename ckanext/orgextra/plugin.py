# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)

    def update_config(self, config):
        # Add template and public directories
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def before_map(self, map):
        # Add custom routes
        map.connect(
            'send_notification',
            '/send_notification',
            controller='ckanext.orgextra.controller:NotificationController',
            action='send_notification',
        )
        return map