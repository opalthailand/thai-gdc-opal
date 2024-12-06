# encoding: utf-8

from flask import Blueprint
import ckan.plugins.toolkit as toolkit
from ckanext.myorgexample import helpers as myh

report = Blueprint('report', __name__)

def report_by_type(report_type='last_modified_datasets'):
    if report_type == 'last_modified_datasets':
        data = myh.get_last_modified_datasets(3)
    elif report_type == 'datasets_by_organization':
        data = myh.get_datasets_by_organization()

    return toolkit.render('report/report_page.html',
                           extra_vars={
                               'type':report_type,
                               'data':data
                           })

report.add_url_rule(u'/report', view_func=report_by_type)
report.add_url_rule(u'/report/<report_type>', view_func=report_by_type)


