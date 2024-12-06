import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.notipasschg import blueprint


class NotipasschgPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic',
            'notipasschg')
    
    # IBlueprint
    def get_blueprint(self):
        return blueprint.ext_route

