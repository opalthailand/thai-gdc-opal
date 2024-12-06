# encoding: utf-8

import ckan.plugins as p, logging, db
import ckan.model as model
from ckan.common import config

log = logging.getLogger(__name__)

def check_plugin(plugin_name):
  plugins = config.get('ckan.plugins', '')
  plugins = list(plugins.split(" "))
  return plugin_name in plugins

def check_table_column(tb_name, fl_name=None):
  if fl_name:
    fields = [row['column_name'] for row in db.check_column_table(model, tb_name)]
    return fl_name in fields
  return db.check_db_views(model, tb_name)

