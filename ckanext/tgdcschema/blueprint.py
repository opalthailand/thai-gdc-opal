# encoding: utf-8

from flask import Blueprint
import ckan.lib.helpers as h
from ckanapi import LocalCKAN
import ckan.logic as logic
import ckan.lib.base as base
import ckan.plugins.toolkit as tk

NotFound = logic.NotFound

tgdcschema = Blueprint('tgdcschema', __name__)

def resource_read_redirect(package_id, resource_id):
    if resource_id != 'new':
        url = h.url_for('{0}_read'.format('dataset'), id=package_id)+'?id='+resource_id
        return h.redirect_to(url)

def dataset_group_suggest(package_id, group_id):
    result_group_name = group_id
    if result_group_name:
        member_dict = {"id": result_group_name,
                        "object": package_id,
                        "object_type": 'package',
                        "capacity": 'public'}
        try:
            portal = LocalCKAN()
            group_dict = portal.action.member_create(**member_dict)
        except NotFound:
            base.abort(404, _('Group not found'))
    
    return h.redirect_to(h.url_for('{0}_groups'.format('dataset'), id=package_id))

def dataset_datatype_patch(package_id):
    data_type = tk.h.get_request_param("data_type")
    if data_type != "":
        try:
            portal = LocalCKAN()
            patch_meta = {'id':package_id,'data_type':data_type}
            package = portal.action.package_patch(**patch_meta)
        except logic.ValidationError as e:
            return e
        
    return h.redirect_to(h.url_for('{0}_edit'.format('dataset'), id=package_id))

#tgdcschema.add_url_rule('/dataset/<package_id>/resource/<resource_id>', view_func=resource_read_redirect)
tgdcschema.add_url_rule('/dataset/group_suggest/<package_id>/group/<group_id>', view_func=dataset_group_suggest)
tgdcschema.add_url_rule('/dataset/edit-datatype/<package_id>', view_func=dataset_datatype_patch, methods=["GET"])