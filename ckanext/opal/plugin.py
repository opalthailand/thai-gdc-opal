# encoding: utf-8

from logging import getLogger
import ckan.plugins as p
from ckanext.opal.controller import MyLogic
from flask import Blueprint

log = getLogger(__name__)

class OpalPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)

    # IConfigurer
    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, 'templates')
        p.toolkit.add_public_directory(config_, 'public')

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)

        blueprint.add_url_rule(
            u'/opal/do_something',
            u'do_something',
            MyLogic.do_something,
            methods = ['GET']
        )

        return blueprint