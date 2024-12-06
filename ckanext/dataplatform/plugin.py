import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckanext.dataplatform.controller import MyLogic


class DataplatformPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)  

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic',
            'dataplatform')
        
    
    def get_blueprint(self):

        blueprint = Blueprint(self.name, self.__module__)

        blueprint.add_url_rule(
            u'/dataplatform/do_something',
            u'do_something',
            MyLogic.do_something,
            methods=['GET']
        )

        return blueprint