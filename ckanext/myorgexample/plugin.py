# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
from ckanext.myorgexample import helpers as myh
from ckanext.myorgexample import blueprint

class MyorgexamplePlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)

    # IBlueprint

    def get_blueprint(self):
        return blueprint.report

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_public_directory(config_, 'assets')
        toolkit.add_resource('assets', 'myorgexample')

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'myorg_get_last_modified_datasets': myh.get_last_modified_datasets,
            'myorg_get_datasets_by_organization': myh.get_datasets_by_organization,
            'myorg_to_thaidate': myh.to_thaidate
        }

