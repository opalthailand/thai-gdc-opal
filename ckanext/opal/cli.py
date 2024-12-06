# encoding: utf-8

import logging, os, click, db, ckan.model as model, ckan.plugins as p

from ckan.common import config

log = logging.getLogger(__name__)

@click.group(short_help="Opend stats command line")
def opendstats():
    '''Opend stats command line'''
    pass

# @opendstats.command(
#     'db-init',
#     short_help='create table and view for ckanext-opendstats'
# )
@opendstats.command('db-init')
def init():
    '''Initialize database table for opendstats'''
    log.info('Initialize database table for opendstats')
    log.info('#### Please, waiting until message "Initialize database table for opendstats: Success" show. ####')
    try:
        log.info('Creating view for organization hierachy')
        db.create_view_org_hierarchy(model)
        log.info('Creating table ckanext_opendstats_package_views')
        if not db.check_db_views(model, 'ckanext_opendstats_package_views'):
            db.create_table_ckanext_opendstats_package_views(model)
        log.info('Creating table ckanext_opendstats_resource_downloads')
        if not db.check_db_views(model, 'ckanext_opendstats_resource_downloads'):
            db.create_table_ckanext_opendstats_resource_downloads(model)
        log.info('Creating table ckanext_opendstats_usage_by_org')
        if not db.check_db_views(model, 'ckanext_opendstats_usage_by_org'):
            db.create_table_ckanext_opendstats_usage_by_org(model)
    except Exception as e:
        p.toolkit.error_shout(e)
    else:
        click.secho('Initialize database table for opendstats: Success', fg='green', bold=True)

@opendstats.command('create-tb-org')
def create_pk_org():
    # log.info('Create table ckanext_opendstats_package_views and ckanext_opendstats_resource_downloads')
    try:
        log.info('Creating view for organization hierachy')
        db.create_view_org_hierarchy(model)
        log.info('Creating table ckanext_opendstats_package_views')
        if not db.check_db_views(model, 'ckanext_opendstats_package_views'):
            db.create_table_ckanext_opendstats_package_views(model)
        log.info('Creating table ckanext_opendstats_resource_downloads')
        if not db.check_db_views(model, 'ckanext_opendstats_resource_downloads'):
            db.create_table_ckanext_opendstats_resource_downloads(model)
    except Exception as e:
        p.toolkit.error_shout(e)
    else:
        click.secho('Create database table and view: Succsess', fg='green', bold=True)

@opendstats.command('create-tb-usage-org')
def create_usage_org():
    try:
        log.info('Creating table ckanext_opendstats_usage_by_org')
        db.create_table_ckanext_opendstats_usage_by_org(model)
    except Exception as e:
        p.toolkit.error_shout(e)
    else:
        click.secho('Create database table: Succsess', fg='green', bold=True)

@opendstats.command('fetch')
def update():
    '''fetch tracking new data for opend stats'''
    try:
        db.clear_latest_data(model)
        db.fetch_new_data_package_views(model)
        db.fetch_new_data_resource_downloads(model)
        db.fetch_new_data_usage_by_org(model)
    except Exception as e:
        p.toolkit.error_shout(e)
def get_commands():
    return [opendstats]