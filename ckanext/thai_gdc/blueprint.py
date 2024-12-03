# encoding: utf-8

from flask import Blueprint, make_response
from ckan.common import _, config, g, request
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
from ckan.lib.helpers import helper_functions as h
import ckan.model as model
import ckan.lib.base as base
import ckan.lib.uploader as uploader
import ckan.lib.navl.dictization_functions as dfunc
import six
import ckan.lib.app_globals as app_globals
import time
import pandas as pd
import os
import uuid
import numpy as np
from ckanapi import LocalCKAN
import datetime

import logging
log = logging.getLogger(__name__)

thai_gdc_blueprint = Blueprint('thai_gdc', __name__)

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
check_access = logic.check_access
schema_ = logic.schema
_validate = dfunc.validate
ValidationError = logic.ValidationError

def datatype_patch(package_id):
    try:
        data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.args)))
            )
        patch_meta = {'id':package_id,'data_type':data_dict[u'data_type']}
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        check_access(u'package_patch', context, {'id':package_id})
        package = get_action(u'package_patch')(context, patch_meta)
        url = h.url_for(u'{0}.read'.format(u'dataset'), id=package_id)
        return h.redirect_to(url)
    except:
        return base.abort(404)

def clear_import_log():        
    config["import_log"] = ''
    config['template_file'] = ''
    config['import_org'] = ''
    config['template_org'] = ''
    config['ckan.import_params'] = ''
    config['ckan.import_uuid'] = ''
    config['ckan.import_row'] = ''

    return base.render('admin/clear_import_log.html')

def user_activate():
    try:
        data_dict = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.args)))
        )
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        check_access('user_update', context, {'id':data_dict[u'id']})
        user_dict = get_action('user_show')(None, {'id':data_dict[u'id']})
        if user_dict and user_dict['state'] == 'deleted':
            user = model.User.get(user_dict['name'])
            user.state = model.State.ACTIVE
            user.save()
        return h.redirect_to(u'user.read', id=user_dict[u'id'])
    except:
        return base.abort(404)

def edit_banner():
    context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
    try:
        check_access('config_option_update', context, {})
    except logic.NotAuthorized:
        base.abort(403, _('Need to be system administrator to administer'))

    items = [
        {'name': 'ckan.promoted_banner', 'control': 'image_upload', 'label': _('Promoted banner'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'ckan.promoted_banner', 'field_upload': 'promoted_banner_upload', 'field_clear': 'clear_promoted_banner_upload'},
        {'name': 'ckan.search_background', 'control': 'image_upload', 'label': _('Search background'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'ckan.search_background', 'field_upload': 'search_background_upload', 'field_clear': 'clear_search_background_upload'},
        {'name': 'ckan.favicon', 'control': 'favicon_upload', 'label': _('Site favicon'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'ckan.favicon', 'field_upload': 'favicon_upload', 'field_clear': 'clear_favicon_upload'},
    ]
    req_data = request.form.to_dict()
    
    if 'save' in req_data:
        try:
            data_dict = logic.clean_dict(dict_fns.unflatten(logic.tuplize_dict(logic.parse_params(request.form))))
            file_dict = logic.clean_dict(dict_fns.unflatten(logic.tuplize_dict(logic.parse_params(request.files))))

            del data_dict['save']
            data_dict['promoted_banner_upload'] = file_dict.get('promoted_banner_upload')
            data_dict['search_background_upload'] = file_dict.get('search_background_upload')
            data_dict['favicon_upload'] = file_dict.get('favicon_upload')

            schema = schema_.update_configuration_schema()

            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data_dict, 'ckan.promoted_banner',
                                'promoted_banner_upload', 'clear_promoted_banner_upload')
            upload.upload(uploader.get_max_image_size())
        
            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data_dict, 'ckan.search_background',
                                'search_background_upload', 'clear_search_background_upload')
            upload.upload(uploader.get_max_image_size())

            upload = uploader.get_uploader('admin')
            upload.update_data_dict(data_dict, 'ckan.favicon',
                                'favicon_upload', 'clear_favicon_upload')
            upload.upload(uploader.get_max_image_size())

            data, errors = _validate(data_dict, schema, context)
            if errors:
                model.Session.rollback()
                raise ValidationError(errors)

            for key, value in six.iteritems(data):
            
                if key == 'ckan.promoted_banner' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))
                
                if key == 'ckan.search_background' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))
                
                if key == 'ckan.favicon' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))

                # Save value in database
                model.set_system_info(key, value)

                # Update CKAN's `config` object
                config[key] = value

                # Only add it to the app_globals (`g`) object if explicitly defined
                # there
                globals_keys = app_globals.app_globals_from_config_details.keys()
                if key in globals_keys:
                    app_globals.set_app_global(key, value)

            # Update the config update timestamp
            model.set_system_info('ckan.config_update', str(time.time()))

            log.info('Updated config options: {0}'.format(data))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            vars = {'data': req_data, 'errors': errors,
                    'error_summary': error_summary, 'form_items': items}
            return base.render('admin/banner_form.html', extra_vars=vars)

        h.redirect_to(h.url_for(u'thai_gdc.edit_banner'))

    schema = logic.schema.update_configuration_schema()
    data = {}
    for key in schema:
        data[key] = config.get(key)

    vars = {'data': data, 'errors': {}, 'form_items': items}
    return base.render('admin/banner_form.html', extra_vars=vars)

def edit_popup(data=None):
    context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
    try:
        check_access('config_option_update', context, {})
    except logic.NotAuthorized:
        base.abort(403, _('Need to be system administrator to administer'))

    data = request.form.to_dict()
    
    if 'save' in data:
        post_data_dict = logic.clean_dict(dict_fns.unflatten(logic.tuplize_dict(logic.parse_params(request.form))))
        post_file_dict = logic.clean_dict(dict_fns.unflatten(logic.tuplize_dict(logic.parse_params(request.files))))

        del post_data_dict['save']
        post_data_dict['EVENT_IMAGE_UPLOAD'] = post_file_dict.get('EVENT_IMAGE_UPLOAD')

        upload = uploader.get_uploader('admin')
        upload.update_data_dict(post_data_dict, 'EVENT_IMAGE', 'EVENT_IMAGE_UPLOAD', 'EVENT_IMAGE_CLEAR')
        upload.upload(uploader.get_max_image_size())

        data_dict_event = {
            'fields': {
                'EVENT_IMAGE': post_data_dict['EVENT_IMAGE'],
                'EVENT_TEXT': post_data_dict['EVENT_TEXT'],
                'EVENT_URL': post_data_dict['EVENT_URL'],
                'EVENT_PUBLIC': post_data_dict['EVENT_PUBLIC']
            },
            'conf_group': 'EVENT'
        }
        try:
            get_action('gdc_agency_update_conf_group')(data_dict=data_dict_event)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
            return base.render('admin/popup.html', extra_vars=vars)
        
        h.redirect_to(h.url_for(u'thai_gdc.edit_popup'))

    else:
        data = get_action('gdc_agency_get_conf_group')(data_dict={'conf_group': 'EVENT'})

    data.update({
        'EVENT_IMAGE_IS_URL': data and 'EVENT_IMAGE' in data.keys() and data['EVENT_IMAGE'].startswith('http')
    })

    extra_vars = {'data': data, 'errors': {}}
    return base.render('admin/popup.html', extra_vars=extra_vars)

def export_dataset_init():
    context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
    try:
        check_access('config_option_update', context, {})
    except logic.NotAuthorized:
        base.abort(403, _('Need to be system administrator to administer'))
    
    my_path = config.get('ckan.storage_path', None)
    if not my_path:
        base.abort(404, _('Page Not Found'))

    export_path = '%s/storage/uploads/admin_export' % my_path

    if os.path.isdir(export_path):
            for filename in os.listdir(export_path):
                file_path = os.path.join(export_path, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

    return base.render('admin/export_package.html')

def export_dataset(id):
    context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
    try:
        check_access('config_option_update', context, {})
    except logic.NotAuthorized:
        base.abort(403, _('Need to be system administrator to administer'))
    
    my_path = config.get('ckan.storage_path', None)
    if not my_path:
        base.abort(404, _('Page Not Found'))

    export_path = '%s/storage/uploads/admin_export' % my_path
    
    file_path = '%s/%s.xlsx' % (export_path, id)
    rec_sheet_name = u'ข้อมูลระเบียน'
    sta_sheet_name = u'ข้อมูลสถิติ'
    gis_sheet_name = u'ข้อมูลภูมิสารสนเทศเชิงพื้นที่'
    oth_sheet_name = u'ข้อมูลประเภทอื่นๆ'
    mlt_sheet_name = u'ข้อมูลหลากหลายประเภท'

    with pd.ExcelWriter(file_path) as writer:
        rec_csv = '%s/%s_rec.csv' % (export_path, id)
        if os.path.isfile(rec_csv):
            try:
                df_record = pd.read_csv(rec_csv, keep_default_na=False, error_bad_lines=False)
                df_record.to_excel(writer, encoding='utf-8', sheet_name=rec_sheet_name)
            except:
                pass
            os.unlink(rec_csv)

        sta_csv = '%s/%s_sta.csv' % (export_path, id)
        if os.path.isfile(sta_csv):
            try:
                df_stat = pd.read_csv(sta_csv, keep_default_na=False, error_bad_lines=False)
                df_stat.to_excel(writer, encoding='utf-8', sheet_name=sta_sheet_name)
            except:
                pass
            os.unlink(sta_csv)

        gis_csv = '%s/%s_gis.csv' % (export_path, id)
        if os.path.isfile(gis_csv):
            try:
                df_gis = pd.read_csv(gis_csv, keep_default_na=False, error_bad_lines=False)
                df_gis.to_excel(writer, encoding='utf-8', sheet_name=gis_sheet_name)
            except:
                pass
            os.unlink(gis_csv)

        oth_csv = '%s/%s_oth.csv' % (export_path, id)
        if os.path.isfile(oth_csv):
            try:
                df_other = pd.read_csv(oth_csv, keep_default_na=False, error_bad_lines=False)
                df_other.to_excel(writer, encoding='utf-8', sheet_name=oth_sheet_name)
            except:
                pass
            os.unlink(oth_csv)

        mlt_csv = '%s/%s_mlt.csv' % (export_path, id)
        if os.path.isfile(mlt_csv):
            try:
                df_multi = pd.read_csv(mlt_csv, keep_default_na=False, error_bad_lines=False)
                df_multi.to_excel(writer, encoding='utf-8', sheet_name=mlt_sheet_name)
            except:
                pass
            os.unlink(mlt_csv)

    if not os.path.exists(file_path):
        base.abort(404, _('Page Not Found'))
    
    with open(file_path) as f:
        file_content = f.read()
    
    response = make_response(file_content, 200)
    response.headers['Content-Description'] = 'File Transfer'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Content-Type'] = 'application/application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=dataset.xlsx'
    response.headers['Content-Length'] = os.path.getsize(file_path)

    return response

def _record_type_process(data_dict):
    try:
        record_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Record')
        record_df.drop(0, inplace=True)
        record_df["data_type"] = u'ข้อมูลระเบียน'

        record_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type']
        record_df.drop(['d_type'], axis=1, inplace=True)
        record_df.replace(np.nan, '', regex=True, inplace=True)
        record_df = record_df.astype('unicode')
        record_df = record_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        record_df['high_value_dataset'] = np.where(record_df['high_value_dataset'].str.contains(u'ไม่'), "False", "True")
        record_df['reference_data'] = np.where(record_df['reference_data'].str.contains(u'ไม่'), "False", "True")

        record_df["dataset_name"] = record_df["name"]
        record_df["name"] = record_df["name"].str.lower()
        record_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            record_df = record_df.loc[record_df['owner_org'] == str(data_dict['template_org']).encode('utf-8')]
            record_df.reset_index(drop=True, inplace=True)
        record_df["owner_org"] = data_dict['owner_org']
        record_df["private"] = True
        record_df["allow_harvest"] = "False"
        record_df["allow_cdp"] = "False"
        record_df['tag_string'] = record_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        record_df["created_date"] = pd.to_datetime((pd.to_numeric(record_df["created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+record_df["created_date"].str.slice(start=4), errors='coerce').astype(str)
        record_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(record_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+record_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = [u'ยุทธศาสตร์ชาติ', u'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', u'แผนความมั่นคงแห่งชาติ',u'แผนแม่บทภายใต้ยุทธศาสตร์ชาติ',u'แผนปฏิรูปประเทศ',u'แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)',u'นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี',u'มติคณะรัฐมนตรี',u'เพื่อการให้บริการประชาชน',u'กฎหมายที่เกี่ยวข้อง',u'พันธกิจหน่วยงาน',u'ดัชนี/ตัวชี้วัดระดับนานาชาติ',u'ไม่ทราบ']
        record_df['objective_other'] = record_df['objective'].isin(objective_choices)
        record_df['objective_other'] = np.where(record_df['objective_other'], 'True', record_df['objective'])
        record_df['objective'] = np.where(record_df['objective_other'] == 'True', record_df['objective'], u'อื่นๆ')
        record_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = [u'ไม่ทราบ', u'ปี', u'ครึ่งปี',u'ไตรมาส',u'เดือน',u'สัปดาห์',u'วัน',u'วันทำการ',u'ชั่วโมง',u'นาที',u'ตามเวลาจริง',u'ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        record_df['update_frequency_unit_other'] = record_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        record_df['update_frequency_unit_other'] = np.where(record_df['update_frequency_unit_other'], 'True', record_df['update_frequency_unit'])
        record_df['update_frequency_unit'] = np.where(record_df['update_frequency_unit_other'] == 'True', record_df['update_frequency_unit'], u'อื่นๆ')
        record_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = [u'ไม่มี', u'โลก', u'ทวีป/กลุ่มประเทศในทวีป',u'กลุ่มประเทศทางเศรษฐกิจ',u'ประเทศ',u'ภาค',u'จังหวัด',u'อำเภอ',u'ตำบล',u'หมู่บ้าน',u'เทศบาล/อบต.',u'พิกัด',u'ไม่ทราบ']
        record_df['geo_coverage_other'] = record_df['geo_coverage'].isin(geo_coverage_choices)
        record_df['geo_coverage_other'] = np.where(record_df['geo_coverage_other'], 'True', record_df['geo_coverage'])
        record_df['geo_coverage'] = np.where(record_df['geo_coverage_other'] == 'True', record_df['geo_coverage'], u'อื่นๆ')
        record_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = [u'ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','DOC/DOCX','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        record_df['data_format_other'] = record_df['data_format'].isin(data_format_choices)
        record_df['data_format_other'] = np.where(record_df['data_format_other'], 'True', record_df['data_format'])
        record_df['data_format'] = np.where(record_df['data_format_other'] == 'True', record_df['data_format'], u'อื่นๆ')
        record_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['Open Data Common', 'Creative Commons Attributions','Creative Commons Attribution Non-Commercial','Creative Commons Attribution Share-Alike','Creative Commons Attribution Non-Commercial Share-Alike','Creative Commons Attribution Non-Commercial No-Derivs','Creative Commons Attribution No-Derivs']
        record_df['license_id_other'] = record_df['license_id'].isin(license_id_choices)
        record_df['license_id_other'] = np.where(record_df['license_id_other'], 'True', record_df['license_id'])
        record_df['license_id'] = np.where(record_df['license_id_other'] == 'True', record_df['license_id'], u'อื่นๆ')
        record_df['license_id_other'].replace('True', '', regex=True, inplace=True)
        
        data_support_choices = ['',u'ไม่มี', u'หน่วยงานของรัฐ', u'หน่วยงานเอกชน',u'หน่วยงาน/องค์กรระหว่างประเทศ',u'มูลนิธิ/สมาคม',u'สถาบันการศึกษา']
        record_df['data_support_other'] = record_df['data_support'].isin(data_support_choices)
        record_df['data_support_other'] = np.where(record_df['data_support_other'], 'True', record_df['data_support'])
        record_df['data_support'] = np.where(record_df['data_support_other'] == 'True', record_df['data_support'], u'อื่นๆ')
        record_df['data_support_other'].replace('True', '', regex=True, inplace=True)

        data_collect_choices = ['',u'ไม่มี',u'บุคคล', u'ครัวเรือน/ครอบครัว', u'บ้าน/ที่อยู่อาศัย',u'บริษัท/ห้างร้าน/สถานประกอบการ',u'อาคาร/สิ่งปลูกสร้าง',u'พื้นที่การเกษตร ประมง ป่าไม้',u'สัตว์และพันธุ์พืช',u'ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่',u'แหล่งน้ำ เช่น แม่น้ำ อ่างเก็บน้ำ',u'เส้นทางการเดินทาง เช่น ถนน ทางรถไฟ',u'ไม่ทราบ']
        record_df['data_collect_other'] = record_df['data_collect'].isin(data_collect_choices)
        record_df['data_collect_other'] = np.where(record_df['data_collect_other'], 'True', record_df['data_collect'])
        record_df['data_collect'] = np.where(record_df['data_collect_other'] == 'True', record_df['data_collect'], u'อื่นๆ')
        record_df['data_collect_other'].replace('True', '', regex=True, inplace=True)

        data_language_choices = ['',u'ไทย', u'อังกฤษ', u'จีน',u'มลายู',u'พม่า',u'ลาว',u'เขมร',u'ญี่ปุ่น',u'เกาหลี',u'ฝรั่งเศส',u'เยอรมัน',u'อารบิก',u'ไม่ทราบ']
        record_df['data_language_other'] = record_df['data_language'].isin(data_language_choices)
        record_df['data_language_other'] = np.where(record_df['data_language_other'], 'True', record_df['data_language'])
        record_df['data_language'] = np.where(record_df['data_language_other'] == 'True', record_df['data_language'], u'อื่นๆ')
        record_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        record_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        record_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type'])
        record_df.replace(np.nan, '', regex=True, inplace=True)
        record_df = record_df.astype('unicode')
        record_df = record_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
    portal = LocalCKAN()

    package_dict_list = record_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            record_df.loc[record_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            record_df.loc[record_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err)+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Record')
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect'])
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    try:
        final_df = pd.merge(record_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _stat_type_process(data_dict):
    try:
        stat_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Stat')
        stat_df.drop(0, inplace=True)
        stat_df["data_type"] = u'ข้อมูลสถิติ'

        stat_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','first_year_of_data','last_year_of_data','data_release_calendar','last_updated_date','disaggregate','unit_of_measure','unit_of_multiplier','calculation_method','standard','url','data_language','official_statistics','data_type']
        stat_df.drop(['d_type'], axis=1, inplace=True)
        stat_df.replace(np.nan, '', regex=True, inplace=True)
        stat_df = stat_df.astype('unicode')
        stat_df = stat_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        stat_df['official_statistics'] = np.where(stat_df['official_statistics'].str.contains(u'ไม่'), "False", "True")
        
        stat_df["dataset_name"] = stat_df["name"]
        stat_df["name"] = stat_df["name"].str.lower()
        stat_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            stat_df = stat_df.loc[stat_df['owner_org'] == str(data_dict['template_org']).encode('utf-8')]
            stat_df.reset_index(drop=True, inplace=True)
        stat_df["owner_org"] = data_dict['owner_org']
        stat_df["private"] = True
        stat_df["allow_harvest"] = "False"
        stat_df["allow_cdp"] = "False"
        stat_df['tag_string'] = stat_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        stat_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(stat_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+stat_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = [u'ยุทธศาสตร์ชาติ', u'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', u'แผนความมั่นคงแห่งชาติ',u'แผนแม่บทภายใต้ยุทธศาสตร์ชาติ',u'แผนปฏิรูปประเทศ',u'แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)',u'นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี',u'มติคณะรัฐมนตรี',u'เพื่อการให้บริการประชาชน',u'กฎหมายที่เกี่ยวข้อง',u'พันธกิจหน่วยงาน',u'ดัชนี/ตัวชี้วัดระดับนานาชาติ',u'ไม่ทราบ']
        stat_df['objective_other'] = stat_df['objective'].isin(objective_choices)
        stat_df['objective_other'] = np.where(stat_df['objective_other'], 'True', stat_df['objective'])
        stat_df['objective'] = np.where(stat_df['objective_other'] == 'True', stat_df['objective'], u'อื่นๆ')
        stat_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = [u'ไม่ทราบ', u'ปี', u'ครึ่งปี',u'ไตรมาส',u'เดือน',u'สัปดาห์',u'วัน',u'วันทำการ',u'ชั่วโมง',u'นาที',u'ตามเวลาจริง',u'ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        stat_df['update_frequency_unit_other'] = stat_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        stat_df['update_frequency_unit_other'] = np.where(stat_df['update_frequency_unit_other'], 'True', stat_df['update_frequency_unit'])
        stat_df['update_frequency_unit'] = np.where(stat_df['update_frequency_unit_other'] == 'True', stat_df['update_frequency_unit'], u'อื่นๆ')
        stat_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = [u'ไม่มี', u'โลก', u'ทวีป/กลุ่มประเทศในทวีป',u'กลุ่มประเทศทางเศรษฐกิจ',u'ประเทศ',u'ภาค',u'จังหวัด',u'อำเภอ',u'ตำบล',u'หมู่บ้าน',u'เทศบาล/อบต.',u'พิกัด',u'ไม่ทราบ']
        stat_df['geo_coverage_other'] = stat_df['geo_coverage'].isin(geo_coverage_choices)
        stat_df['geo_coverage_other'] = np.where(stat_df['geo_coverage_other'], 'True', stat_df['geo_coverage'])
        stat_df['geo_coverage'] = np.where(stat_df['geo_coverage_other'] == 'True', stat_df['geo_coverage'], u'อื่นๆ')
        stat_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = [u'ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','DOC/DOCX','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        stat_df['data_format_other'] = stat_df['data_format'].isin(data_format_choices)
        stat_df['data_format_other'] = np.where(stat_df['data_format_other'], 'True', stat_df['data_format'])
        stat_df['data_format'] = np.where(stat_df['data_format_other'] == 'True', stat_df['data_format'], u'อื่นๆ')
        stat_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['Open Data Common', 'Creative Commons Attributions','Creative Commons Attribution Non-Commercial','Creative Commons Attribution Share-Alike','Creative Commons Attribution Non-Commercial Share-Alike','Creative Commons Attribution Non-Commercial No-Derivs','Creative Commons Attribution No-Derivs']
        stat_df['license_id_other'] = stat_df['license_id'].isin(license_id_choices)
        stat_df['license_id_other'] = np.where(stat_df['license_id_other'], 'True', stat_df['license_id'])
        stat_df['license_id'] = np.where(stat_df['license_id_other'] == 'True', stat_df['license_id'], u'อื่นๆ')
        stat_df['license_id_other'].replace('True', '', regex=True, inplace=True)

        stat_df["data_release_calendar"] = pd.to_datetime((pd.to_numeric(stat_df["data_release_calendar"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+stat_df["data_release_calendar"].str.slice(start=4), errors='coerce').astype(str)
        
        disaggregate_choices = ['',u'ไม่มี', u'เพศ', u'อายุ/กลุ่มอายุ',u'สถานภาพสมรส',u'ศาสนา',u'ระดับการศึกษา',u'อาชีพ',u'สถานภาพการทำงาน',u'อุตสาหกรรม/ประเภทกิจการ',u'รายได้',u'ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่',u'ผลิตภัณฑ์',u'ไม่ทราบ']
        stat_df['disaggregate_other'] = stat_df['disaggregate'].isin(disaggregate_choices)
        stat_df['disaggregate_other'] = np.where(stat_df['disaggregate_other'], 'True', stat_df['disaggregate'])
        stat_df['disaggregate'] = np.where(stat_df['disaggregate_other'] == 'True', stat_df['disaggregate'], u'อื่นๆ')
        stat_df['disaggregate_other'].replace('True', '', regex=True, inplace=True)
        
        unit_of_multiplier_choices = ['',u'หน่วย', u'สิบ', u'ร้อย',u'พัน',u'หมื่น',u'แสน',u'ล้าน',u'สิบล้าน',u'ร้อยล้าน',u'พันล้าน',u'หมื่นล้าน',u'แสนล้าน',u'ล้านล้าน',u'ไม่ทราบ']
        stat_df['unit_of_multiplier_other'] = stat_df['unit_of_multiplier'].isin(unit_of_multiplier_choices)
        stat_df['unit_of_multiplier_other'] = np.where(stat_df['unit_of_multiplier_other'], 'True', stat_df['unit_of_multiplier'])
        stat_df['unit_of_multiplier'] = np.where(stat_df['unit_of_multiplier_other'] == 'True', stat_df['unit_of_multiplier'], u'อื่นๆ')
        stat_df['unit_of_multiplier_other'].replace('True', '', regex=True, inplace=True)
        
        data_language_choices = ['',u'ไทย', u'อังกฤษ', u'จีน',u'มลายู',u'พม่า',u'ลาว',u'เขมร',u'ญี่ปุ่น',u'เกาหลี',u'ฝรั่งเศส',u'เยอรมัน',u'อารบิก',u'ไม่ทราบ']
        stat_df['data_language_other'] = stat_df['data_language'].isin(data_language_choices)
        stat_df['data_language_other'] = np.where(stat_df['data_language_other'], 'True', stat_df['data_language'])
        stat_df['data_language'] = np.where(stat_df['data_language_other'] == 'True', stat_df['data_language'], u'อื่นๆ')
        stat_df['data_language_other'].replace('True', '', regex=True, inplace=True)
        
        stat_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        stat_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','first_year_of_data','last_year_of_data','data_release_calendar','last_updated_date','disaggregate','unit_of_measure','unit_of_multiplier','calculation_method','standard','url','data_language','official_statistics','data_type'])
        stat_df.replace(np.nan, '', regex=True, inplace=True)
        stat_df = stat_df.astype('unicode')
        stat_df = stat_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    portal = LocalCKAN()

    package_dict_list = stat_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['disaggregate'] == '':
                pkg_meta.pop('disaggregate', None)
                pkg_meta.pop('disaggregate_other', None)
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            stat_df.loc[stat_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            stat_df.loc[stat_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err)+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Stat')
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics']
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics'])
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    try:
        final_df = pd.merge(stat_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_first_year_of_data','resource_last_year_of_data','resource_data_release_calendar','resource_disaggregate','resource_unit_of_measure','resource_unit_of_multiplier','resource_official_statistics']

        disaggregate_choices = ['',u'ไม่มี', u'เพศ', u'อายุ/กลุ่มอายุ',u'สถานภาพสมรส',u'ศาสนา',u'ระดับการศึกษา',u'อาชีพ',u'สถานภาพการทำงาน',u'อุตสาหกรรม/ประเภทกิจการ',u'รายได้',u'ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่',u'ผลิตภัณฑ์',u'ไม่ทราบ']
        resource_df['resource_disaggregate_other'] = resource_df['resource_disaggregate'].isin(disaggregate_choices)
        resource_df['resource_disaggregate_other'] = np.where(resource_df['resource_disaggregate_other'], 'True', resource_df['resource_disaggregate'])
        resource_df['resource_disaggregate'] = np.where(resource_df['resource_disaggregate_other'] == 'True', resource_df['resource_disaggregate'], u'อื่นๆ')
        resource_df['resource_disaggregate_other'].replace('True', '', regex=True, inplace=True)

        resource_df["resource_data_release_calendar"] = pd.to_datetime((pd.to_numeric(resource_df["resource_data_release_calendar"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_data_release_calendar"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            if res_meta['resource_disaggregate'] == '':
                res_meta.pop('resource_disaggregate', None)
                res_meta.pop('resource_disaggregate_other', None)
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _gis_type_process(data_dict):
    try:
        gis_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_GIS')
        gis_df.drop(0, inplace=True)
        gis_df["data_type"] = u'ข้อมูลภูมิสารสนเทศเชิงพื้นที่'

        gis_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','geographic_data_set','equivalent_scale','west_bound_longitude','east_bound_longitude','north_bound_longitude','south_bound_longitude','positional_accuracy','reference_period','last_updated_date','data_release_calendar','data_release_date','url','data_language','data_type']
        gis_df.drop(['d_type'], axis=1, inplace=True)
        gis_df.replace(np.nan, '', regex=True, inplace=True)
        gis_df = gis_df.astype('unicode')
        gis_df = gis_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        gis_df["dataset_name"] = gis_df["name"]
        gis_df["name"] = gis_df["name"].str.lower()
        gis_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            gis_df = gis_df.loc[gis_df['owner_org'] == str(data_dict['template_org']).encode('utf-8')]
            gis_df.reset_index(drop=True, inplace=True)
        gis_df["owner_org"] = data_dict['owner_org']
        gis_df["private"] = True
        gis_df["allow_harvest"] = "False"
        gis_df["allow_cdp"] = "False"
        gis_df['tag_string'] = gis_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        gis_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(gis_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+gis_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = [u'ยุทธศาสตร์ชาติ', u'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', u'แผนความมั่นคงแห่งชาติ',u'แผนแม่บทภายใต้ยุทธศาสตร์ชาติ',u'แผนปฏิรูปประเทศ',u'แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)',u'นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี',u'มติคณะรัฐมนตรี',u'เพื่อการให้บริการประชาชน',u'กฎหมายที่เกี่ยวข้อง',u'พันธกิจหน่วยงาน',u'ดัชนี/ตัวชี้วัดระดับนานาชาติ',u'ไม่ทราบ']
        gis_df['objective_other'] = gis_df['objective'].isin(objective_choices)
        gis_df['objective_other'] = np.where(gis_df['objective_other'], 'True', gis_df['objective'])
        gis_df['objective'] = np.where(gis_df['objective_other'] == 'True', gis_df['objective'], u'อื่นๆ')
        gis_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = [u'ไม่ทราบ', u'ปี', u'ครึ่งปี',u'ไตรมาส',u'เดือน',u'สัปดาห์',u'วัน',u'วันทำการ',u'ชั่วโมง',u'นาที',u'ตามเวลาจริง',u'ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        gis_df['update_frequency_unit_other'] = gis_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        gis_df['update_frequency_unit_other'] = np.where(gis_df['update_frequency_unit_other'], 'True', gis_df['update_frequency_unit'])
        gis_df['update_frequency_unit'] = np.where(gis_df['update_frequency_unit_other'] == 'True', gis_df['update_frequency_unit'], u'อื่นๆ')
        gis_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = [u'ไม่มี', u'โลก', u'ทวีป/กลุ่มประเทศในทวีป',u'กลุ่มประเทศทางเศรษฐกิจ',u'ประเทศ',u'ภาค',u'จังหวัด',u'อำเภอ',u'ตำบล',u'หมู่บ้าน',u'เทศบาล/อบต.',u'พิกัด',u'ไม่ทราบ']
        gis_df['geo_coverage_other'] = gis_df['geo_coverage'].isin(geo_coverage_choices)
        gis_df['geo_coverage_other'] = np.where(gis_df['geo_coverage_other'], 'True', gis_df['geo_coverage'])
        gis_df['geo_coverage'] = np.where(gis_df['geo_coverage_other'] == 'True', gis_df['geo_coverage'], u'อื่นๆ')
        gis_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = [u'ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','DOC/DOCX','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        gis_df['data_format_other'] = gis_df['data_format'].isin(data_format_choices)
        gis_df['data_format_other'] = np.where(gis_df['data_format_other'], 'True', gis_df['data_format'])
        gis_df['data_format'] = np.where(gis_df['data_format_other'] == 'True', gis_df['data_format'], u'อื่นๆ')
        gis_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['Open Data Common', 'Creative Commons Attributions','Creative Commons Attribution Non-Commercial','Creative Commons Attribution Share-Alike','Creative Commons Attribution Non-Commercial Share-Alike','Creative Commons Attribution Non-Commercial No-Derivs','Creative Commons Attribution No-Derivs']
        gis_df['license_id_other'] = gis_df['license_id'].isin(license_id_choices)
        gis_df['license_id_other'] = np.where(gis_df['license_id_other'], 'True', gis_df['license_id'])
        gis_df['license_id'] = np.where(gis_df['license_id_other'] == 'True', gis_df['license_id'], u'อื่นๆ')
        gis_df['license_id_other'].replace('True', '', regex=True, inplace=True)

        equivalent_scale_choices = ['','1:4,000', '1:10,000', '1:25,000','1:50,000','1:250,000']
        gis_df['equivalent_scale_other'] = gis_df['equivalent_scale'].isin(equivalent_scale_choices)
        gis_df['equivalent_scale_other'] = np.where(gis_df['equivalent_scale_other'], 'True', gis_df['equivalent_scale'])
        gis_df['equivalent_scale'] = np.where(gis_df['equivalent_scale_other'] == 'True', gis_df['equivalent_scale'], u'อื่นๆ')
        gis_df['equivalent_scale_other'].replace('True', '', regex=True, inplace=True)

        gis_df["data_release_calendar"] = pd.to_datetime((pd.to_numeric(gis_df["data_release_calendar"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+gis_df["data_release_calendar"].str.slice(start=4),errors='coerce').astype(str)
        gis_df["data_release_date"] = pd.to_datetime((pd.to_numeric(gis_df["data_release_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+gis_df["data_release_date"].str.slice(start=4),errors='coerce').astype(str)

        data_language_choices = ['',u'ไทย', u'อังกฤษ', u'จีน',u'มลายู',u'พม่า',u'ลาว',u'เขมร',u'ญี่ปุ่น',u'เกาหลี',u'ฝรั่งเศส',u'เยอรมัน',u'อารบิก',u'ไม่ทราบ']
        gis_df['data_language_other'] = gis_df['data_language'].isin(data_language_choices)
        gis_df['data_language_other'] = np.where(gis_df['data_language_other'], 'True', gis_df['data_language'])
        gis_df['data_language'] = np.where(gis_df['data_language_other'] == 'True', gis_df['data_language'], u'อื่นๆ')
        gis_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        gis_df.replace('NaT', '', regex=True, inplace=True)

    except Exception as err:
        log.info(err)
        gis_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','geographic_data_set','equivalent_scale','west_bound_longitude','east_bound_longitude','north_bound_longitude','south_bound_longitude','positional_accuracy','reference_period','last_updated_date','data_release_calendar','data_release_date','url','data_language','data_type'])
        gis_df.replace(np.nan, '', regex=True, inplace=True)
        gis_df = gis_df.astype('unicode')
        gis_df = gis_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    portal = LocalCKAN()

    package_dict_list = gis_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            gis_df.loc[gis_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            gis_df.loc[gis_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err)+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_GIS')
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy']
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy'])
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    try:
        final_df = pd.merge(gis_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_equivalent_scale','resource_geographic_data_set','resource_created_date','resource_data_release_date','resource_positional_accuracy']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_data_release_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_data_release_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_data_release_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _multi_type_process(data_dict):
    try:
        multi_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Multi')
        multi_df.drop(0, inplace=True)
        multi_df["data_type"] = u'ข้อมูลหลากหลายประเภท'

        multi_df.columns = ['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type']
        multi_df.drop(['d_type'], axis=1, inplace=True)
        multi_df.replace(np.nan, '', regex=True, inplace=True)
        multi_df = multi_df.astype('unicode')
        multi_df = multi_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        multi_df['high_value_dataset'] = np.where(multi_df['high_value_dataset'].str.contains(u'ไม่'), "False", "True")
        multi_df['reference_data'] = np.where(multi_df['reference_data'].str.contains(u'ไม่'), "False", "True")
        
        multi_df["dataset_name"] = multi_df["name"]
        multi_df["name"] = multi_df["name"].str.lower()
        multi_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            multi_df = multi_df.loc[multi_df['owner_org'] == str(data_dict['template_org']).encode('utf-8')]
            multi_df.reset_index(drop=True, inplace=True)
        multi_df["owner_org"] = data_dict['owner_org']
        multi_df["private"] = True
        multi_df["allow_harvest"] = "False"
        multi_df["allow_cdp"] = "False"
        multi_df['tag_string'] = multi_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        multi_df["created_date"] = pd.to_datetime((pd.to_numeric(multi_df["created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+multi_df["created_date"].str.slice(start=4), errors='coerce').astype(str)
        multi_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(multi_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+multi_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = [u'ยุทธศาสตร์ชาติ', u'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', u'แผนความมั่นคงแห่งชาติ',u'แผนแม่บทภายใต้ยุทธศาสตร์ชาติ',u'แผนปฏิรูปประเทศ',u'แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)',u'นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี',u'มติคณะรัฐมนตรี',u'เพื่อการให้บริการประชาชน',u'กฎหมายที่เกี่ยวข้อง',u'พันธกิจหน่วยงาน',u'ดัชนี/ตัวชี้วัดระดับนานาชาติ',u'ไม่ทราบ']
        multi_df['objective_other'] = multi_df['objective'].isin(objective_choices)
        multi_df['objective_other'] = np.where(multi_df['objective_other'], 'True', multi_df['objective'])
        multi_df['objective'] = np.where(multi_df['objective_other'] == 'True', multi_df['objective'], u'อื่นๆ')
        multi_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = [u'ไม่ทราบ', u'ปี', u'ครึ่งปี',u'ไตรมาส',u'เดือน',u'สัปดาห์',u'วัน',u'วันทำการ',u'ชั่วโมง',u'นาที',u'ตามเวลาจริง',u'ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        multi_df['update_frequency_unit_other'] = multi_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        multi_df['update_frequency_unit_other'] = np.where(multi_df['update_frequency_unit_other'], 'True', multi_df['update_frequency_unit'])
        multi_df['update_frequency_unit'] = np.where(multi_df['update_frequency_unit_other'] == 'True', multi_df['update_frequency_unit'], u'อื่นๆ')
        multi_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = [u'ไม่มี', u'โลก', u'ทวีป/กลุ่มประเทศในทวีป',u'กลุ่มประเทศทางเศรษฐกิจ',u'ประเทศ',u'ภาค',u'จังหวัด',u'อำเภอ',u'ตำบล',u'หมู่บ้าน',u'เทศบาล/อบต.',u'พิกัด',u'ไม่ทราบ']
        multi_df['geo_coverage_other'] = multi_df['geo_coverage'].isin(geo_coverage_choices)
        multi_df['geo_coverage_other'] = np.where(multi_df['geo_coverage_other'], 'True', multi_df['geo_coverage'])
        multi_df['geo_coverage'] = np.where(multi_df['geo_coverage_other'] == 'True', multi_df['geo_coverage'], u'อื่นๆ')
        multi_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = [u'ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','DOC/DOCX','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        multi_df['data_format_other'] = multi_df['data_format'].isin(data_format_choices)
        multi_df['data_format_other'] = np.where(multi_df['data_format_other'], 'True', multi_df['data_format'])
        multi_df['data_format'] = np.where(multi_df['data_format_other'] == 'True', multi_df['data_format'], u'อื่นๆ')
        multi_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['Open Data Common', 'Creative Commons Attributions','Creative Commons Attribution Non-Commercial','Creative Commons Attribution Share-Alike','Creative Commons Attribution Non-Commercial Share-Alike','Creative Commons Attribution Non-Commercial No-Derivs','Creative Commons Attribution No-Derivs']
        multi_df['license_id_other'] = multi_df['license_id'].isin(license_id_choices)
        multi_df['license_id_other'] = np.where(multi_df['license_id_other'], 'True', multi_df['license_id'])
        multi_df['license_id'] = np.where(multi_df['license_id_other'] == 'True', multi_df['license_id'], u'อื่นๆ')
        multi_df['license_id_other'].replace('True', '', regex=True, inplace=True)
        
        data_support_choices = ['',u'ไม่มี', u'หน่วยงานของรัฐ', u'หน่วยงานเอกชน',u'หน่วยงาน/องค์กรระหว่างประเทศ',u'มูลนิธิ/สมาคม',u'สถาบันการศึกษา']
        multi_df['data_support_other'] = multi_df['data_support'].isin(data_support_choices)
        multi_df['data_support_other'] = np.where(multi_df['data_support_other'], 'True', multi_df['data_support'])
        multi_df['data_support'] = np.where(multi_df['data_support_other'] == 'True', multi_df['data_support'], u'อื่นๆ')
        multi_df['data_support_other'].replace('True', '', regex=True, inplace=True)

        data_collect_choices = ['',u'ไม่มี',u'บุคคล', u'ครัวเรือน/ครอบครัว', u'บ้าน/ที่อยู่อาศัย',u'บริษัท/ห้างร้าน/สถานประกอบการ',u'อาคาร/สิ่งปลูกสร้าง',u'พื้นที่การเกษตร ประมง ป่าไม้',u'สัตว์และพันธุ์พืช',u'ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่',u'แหล่งน้ำ เช่น แม่น้ำ อ่างเก็บน้ำ',u'เส้นทางการเดินทาง เช่น ถนน ทางรถไฟ',u'ไม่ทราบ']
        multi_df['data_collect_other'] = multi_df['data_collect'].isin(data_collect_choices)
        multi_df['data_collect_other'] = np.where(multi_df['data_collect_other'], 'True', multi_df['data_collect'])
        multi_df['data_collect'] = np.where(multi_df['data_collect_other'] == 'True', multi_df['data_collect'], u'อื่นๆ')
        multi_df['data_collect_other'].replace('True', '', regex=True, inplace=True)

        data_language_choices = ['',u'ไทย', u'อังกฤษ', u'จีน',u'มลายู',u'พม่า',u'ลาว',u'เขมร',u'ญี่ปุ่น',u'เกาหลี',u'ฝรั่งเศส',u'เยอรมัน',u'อารบิก',u'ไม่ทราบ']
        multi_df['data_language_other'] = multi_df['data_language'].isin(data_language_choices)
        multi_df['data_language_other'] = np.where(multi_df['data_language_other'], 'True', multi_df['data_language'])
        multi_df['data_language'] = np.where(multi_df['data_language_other'] == 'True', multi_df['data_language'], u'อื่นๆ')
        multi_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        multi_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        multi_df = pd.DataFrame(columns=['name','d_type','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type'])
        multi_df.replace(np.nan, '', regex=True, inplace=True)
        multi_df = multi_df.astype('unicode')
        multi_df = multi_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
    portal = LocalCKAN()

    package_dict_list = multi_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            multi_df.loc[multi_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            multi_df.loc[multi_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err)+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Multi')
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect'])
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    try:
        final_df = pd.merge(multi_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _other_type_process(data_dict):
    try:
        other_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp2_Meta_Other')
        other_df.drop(0, inplace=True)
        other_df["data_type"] = u'ข้อมูลประเภทอื่นๆ'

        other_df.columns = ['name','data_type_other','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type']
        other_df.replace(np.nan, '', regex=True, inplace=True)
        other_df = other_df.astype('unicode')
        other_df = other_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        other_df['high_value_dataset'] = np.where(other_df['high_value_dataset'].str.contains(u'ไม่'), "False", "True")
        other_df['reference_data'] = np.where(other_df['reference_data'].str.contains(u'ไม่'), "False", "True")
        
        other_df["dataset_name"] = other_df["name"]
        other_df["name"] = other_df["name"].str.lower()
        other_df["name"].replace('\s', '-', regex=True, inplace=True)
        if data_dict['template_org'] != 'all':
            other_df = other_df.loc[other_df['owner_org'] == str(data_dict['template_org']).encode('utf-8')]
            other_df.reset_index(drop=True, inplace=True)
        other_df["owner_org"] = data_dict['owner_org']
        other_df["private"] = True
        other_df["allow_harvest"] = "False"
        other_df["allow_cdp"] = "False"
        other_df['tag_string'] = other_df['tag_string'].str.split(',').apply(lambda x: [e.strip() for e in x]).tolist()

        other_df["created_date"] = pd.to_datetime((pd.to_numeric(other_df["created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+other_df["created_date"].str.slice(start=4), errors='coerce').astype(str)
        other_df["last_updated_date"] = pd.to_datetime((pd.to_numeric(other_df["last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+other_df["last_updated_date"].str.slice(start=4), errors='coerce').astype(str)

        objective_choices = [u'ยุทธศาสตร์ชาติ', u'แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ', u'แผนความมั่นคงแห่งชาติ',u'แผนแม่บทภายใต้ยุทธศาสตร์ชาติ',u'แผนปฏิรูปประเทศ',u'แผนระดับที่ 3 (มติครม. 4 ธ.ค. 2560)',u'นโยบายรัฐบาล/ข้อสั่งการนายกรัฐมนตรี',u'มติคณะรัฐมนตรี',u'เพื่อการให้บริการประชาชน',u'กฎหมายที่เกี่ยวข้อง',u'พันธกิจหน่วยงาน',u'ดัชนี/ตัวชี้วัดระดับนานาชาติ',u'ไม่ทราบ']
        other_df['objective_other'] = other_df['objective'].isin(objective_choices)
        other_df['objective_other'] = np.where(other_df['objective_other'], 'True', other_df['objective'])
        other_df['objective'] = np.where(other_df['objective_other'] == 'True', other_df['objective'], u'อื่นๆ')
        other_df['objective_other'].replace('True', '', regex=True, inplace=True)

        update_frequency_unit_choices = [u'ไม่ทราบ', u'ปี', u'ครึ่งปี',u'ไตรมาส',u'เดือน',u'สัปดาห์',u'วัน',u'วันทำการ',u'ชั่วโมง',u'นาที',u'ตามเวลาจริง',u'ไม่มีการปรับปรุงหลังจากการจัดเก็บข้อมูล']
        other_df['update_frequency_unit_other'] = other_df['update_frequency_unit'].isin(update_frequency_unit_choices)
        other_df['update_frequency_unit_other'] = np.where(other_df['update_frequency_unit_other'], 'True', other_df['update_frequency_unit'])
        other_df['update_frequency_unit'] = np.where(other_df['update_frequency_unit_other'] == 'True', other_df['update_frequency_unit'], u'อื่นๆ')
        other_df['update_frequency_unit_other'].replace('True', '', regex=True, inplace=True)

        geo_coverage_choices = [u'ไม่มี', u'โลก', u'ทวีป/กลุ่มประเทศในทวีป',u'กลุ่มประเทศทางเศรษฐกิจ',u'ประเทศ',u'ภาค',u'จังหวัด',u'อำเภอ',u'ตำบล',u'หมู่บ้าน',u'เทศบาล/อบต.',u'พิกัด',u'ไม่ทราบ']
        other_df['geo_coverage_other'] = other_df['geo_coverage'].isin(geo_coverage_choices)
        other_df['geo_coverage_other'] = np.where(other_df['geo_coverage_other'], 'True', other_df['geo_coverage'])
        other_df['geo_coverage'] = np.where(other_df['geo_coverage_other'] == 'True', other_df['geo_coverage'], u'อื่นๆ')
        other_df['geo_coverage_other'].replace('True', '', regex=True, inplace=True)

        data_format_choices = [u'ไม่ทราบ', 'Database', 'CSV','XML','Image','Video','Audio','Text','JSON','HTML','DOC/DOCX','XLS','PDF','RDF','NoSQL','Arc/Info Coverage','Shapefile','GeoTiff','GML']
        other_df['data_format_other'] = other_df['data_format'].isin(data_format_choices)
        other_df['data_format_other'] = np.where(other_df['data_format_other'], 'True', other_df['data_format'])
        other_df['data_format'] = np.where(other_df['data_format_other'] == 'True', other_df['data_format'], u'อื่นๆ')
        other_df['data_format_other'].replace('True', '', regex=True, inplace=True)

        license_id_choices = ['Open Data Common', 'Creative Commons Attributions','Creative Commons Attribution Non-Commercial','Creative Commons Attribution Share-Alike','Creative Commons Attribution Non-Commercial Share-Alike','Creative Commons Attribution Non-Commercial No-Derivs','Creative Commons Attribution No-Derivs']
        other_df['license_id_other'] = other_df['license_id'].isin(license_id_choices)
        other_df['license_id_other'] = np.where(other_df['license_id_other'], 'True', other_df['license_id'])
        other_df['license_id'] = np.where(other_df['license_id_other'] == 'True', other_df['license_id'], u'อื่นๆ')
        other_df['license_id_other'].replace('True', '', regex=True, inplace=True)
        
        data_support_choices = ['',u'ไม่มี', u'หน่วยงานของรัฐ', u'หน่วยงานเอกชน',u'หน่วยงาน/องค์กรระหว่างประเทศ',u'มูลนิธิ/สมาคม',u'สถาบันการศึกษา']
        other_df['data_support_other'] = other_df['data_support'].isin(data_support_choices)
        other_df['data_support_other'] = np.where(other_df['data_support_other'], 'True', other_df['data_support'])
        other_df['data_support'] = np.where(other_df['data_support_other'] == 'True', other_df['data_support'], u'อื่นๆ')
        other_df['data_support_other'].replace('True', '', regex=True, inplace=True)

        data_collect_choices = ['',u'ไม่มี',u'บุคคล', u'ครัวเรือน/ครอบครัว', u'บ้าน/ที่อยู่อาศัย',u'บริษัท/ห้างร้าน/สถานประกอบการ',u'อาคาร/สิ่งปลูกสร้าง',u'พื้นที่การเกษตร ประมง ป่าไม้',u'สัตว์และพันธุ์พืช',u'ขอบเขตเชิงภูมิศาสตร์หรือเชิงพื้นที่',u'แหล่งน้ำ เช่น แม่น้ำ อ่างเก็บน้ำ',u'เส้นทางการเดินทาง เช่น ถนน ทางรถไฟ',u'ไม่ทราบ']
        other_df['data_collect_other'] = other_df['data_collect'].isin(data_collect_choices)
        other_df['data_collect_other'] = np.where(other_df['data_collect_other'], 'True', other_df['data_collect'])
        other_df['data_collect'] = np.where(other_df['data_collect_other'] == 'True', other_df['data_collect'], u'อื่นๆ')
        other_df['data_collect_other'].replace('True', '', regex=True, inplace=True)

        data_language_choices = ['',u'ไทย', u'อังกฤษ', u'จีน',u'มลายู',u'พม่า',u'ลาว',u'เขมร',u'ญี่ปุ่น',u'เกาหลี',u'ฝรั่งเศส',u'เยอรมัน',u'อารบิก',u'ไม่ทราบ']
        other_df['data_language_other'] = other_df['data_language'].isin(data_language_choices)
        other_df['data_language_other'] = np.where(other_df['data_language_other'], 'True', other_df['data_language'])
        other_df['data_language'] = np.where(other_df['data_language_other'] == 'True', other_df['data_language'], u'อื่นๆ')
        other_df['data_language_other'].replace('True', '', regex=True, inplace=True)

        other_df.replace('NaT', '', regex=True, inplace=True)
        
    except Exception as err:
        log.info(err)
        other_df = pd.DataFrame(columns=['name','data_type_other','title','owner_org','maintainer','maintainer_email','tag_string','notes','objective','update_frequency_unit','update_frequency_interval','geo_coverage','data_source','data_format','data_category','data_classification','license_id','accessible_condition','created_date','last_updated_date','url','data_support','data_collect','data_language','high_value_dataset','reference_data','data_type'])
        other_df.replace(np.nan, '', regex=True, inplace=True)
        other_df = other_df.astype('unicode')
        other_df = other_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    portal = LocalCKAN()

    package_dict_list = other_df.to_dict('records')
    for pkg_meta in package_dict_list:
        try:
            if pkg_meta['data_language'] == '':
                pkg_meta.pop('data_language', None)
                pkg_meta.pop('data_language_other', None)
            package = portal.action.package_create(**pkg_meta)
            log_str = 'package_create: '+datetime.datetime.now().isoformat()+' -- สร้างชุดข้อมูล: '+str(package.get("name"))+' สำเร็จ\n'
            activity_dict = {"data": {"actor": six.ensure_text(data_dict["importer"]), "package":package, 
                "import": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": package.get("id"), 
                "activity_type": "new package"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)
            other_df.loc[other_df['name'] == pkg_meta['name'], 'success'] = '1'
        except Exception as err:
            other_df.loc[other_df['name'] == pkg_meta['name'], 'success'] = '0'
            log_str = 'package_error: '+datetime.datetime.now().isoformat()+' -- ไม่สามารถสร้างชุดข้อมูล: '+str(pkg_meta['name'])+' : '+str(err)+'\n'
            activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Running", "import_log": log_str}, 
                "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
                "activity_type": "changed user"
                }
            portal.action.activity_create(**activity_dict)
            log.info(log_str)

    try:
        resource_df = pd.read_excel(data_dict['filename'], header=[3], sheet_name='Temp3_Resource_Other')
        resource_df.drop(0, inplace=True)
        resource_df.columns = ['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    except:
        resource_df = pd.DataFrame(columns=['dataset_name','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect'])
        resource_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = resource_df.astype('unicode')
        resource_df = resource_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    try:
        final_df = pd.merge(other_df,resource_df,how='left',left_on='dataset_name',right_on='dataset_name')
        final_df.replace(np.nan, '', regex=True, inplace=True)
        resource_df = final_df[(final_df['resource_url'] != '') & (final_df['success'] == '1')]
        resource_df = resource_df[['name','success','resource_name','resource_url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']]
        resource_df.columns = ['package_id','success','name','url','description','resource_accessible_condition','resource_last_updated_date','format','resource_created_date','resource_data_collect']
        resource_df["resource_created_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_created_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_created_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df["resource_last_updated_date"] = pd.to_datetime((pd.to_numeric(resource_df["resource_last_updated_date"].str.slice(stop=4), errors='coerce').astype('Int64')-543).astype(str)+resource_df["resource_last_updated_date"].str.slice(start=4), errors='coerce').astype(str)
        resource_df['created'] = datetime.datetime.utcnow().isoformat()
        resource_df['last_modified'] = datetime.datetime.utcnow().isoformat()
        resource_df.replace('NaT', '', regex=True, inplace=True)
        resource_dict_list = resource_df.to_dict('records')

        for resource_dict in resource_dict_list:
            res_meta = resource_dict
            resource = portal.action.resource_create(**res_meta)
            log.info('resource_create: '+datetime.datetime.now().isoformat()+' -- '+str(resource)+'\n')
    except Exception as err:
        log.info(err)

def _finished_process(data_dict):
    portal = LocalCKAN()
    log_str = 'import finished: '+datetime.datetime.now().isoformat()+' -- จบการทำงาน\n'
    activity_dict = {"data": {"import_id": data_dict["import_uuid"], "import_status": "Finished", "import_log": log_str}, 
        "user_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
        "object_id": model.User.by_name(six.ensure_text(data_dict["importer"])).id, 
        "activity_type": "changed user"
        }
    portal.action.activity_create(**activity_dict)
    log.info(log_str)

def import_dataset():

    context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
    try:
        check_access('config_option_update', context, {})
    except logic.NotAuthorized:
        base.abort(403, _('Need to be system administrator to administer'))

    items = [
        {'name': 'template_file', 'control': 'image_upload', 'label': _('Template File'), 'placeholder': '', 'upload_enabled':h.uploads_enabled(),
            'field_url': 'template_file', 'field_upload': 'template_file_upload', 'field_clear': 'clear_template_file_upload'},
    ]
    data = request.form.to_dict()
    if 'save' in data:
        try:
            # really?
            post_data_dict = logic.clean_dict(dict_fns.unflatten(logic.tuplize_dict(logic.parse_params(request.form))))
            post_file_dict = logic.clean_dict(dict_fns.unflatten(logic.tuplize_dict(logic.parse_params(request.files))))

            del post_data_dict['save']
            post_data_dict['template_file_upload'] = post_file_dict.get('template_file_upload')

            schema = schema_.update_configuration_schema()

            upload = uploader.get_uploader('admin')
            upload.update_data_dict(post_data_dict, 'template_file',
                                'template_file_upload', 'clear_template_file_upload')
            upload.upload(uploader.get_max_image_size())

            data, errors = _validate(post_data_dict, schema, context)
            if errors:
                model.Session.rollback()
                raise ValidationError(errors)

            for key, value in six.iteritems(data):
            
                if key == 'template_file' and value and not value.startswith('http')\
                        and not value.startswith('/'):
                    image_path = 'uploads/admin/'

                    value = h.url_for_static('{0}{1}'.format(image_path, value))

                # Update CKAN's `config` object
                config[key] = value

            log.info('Import Dataset: {0}'.format(data))
            
            import_uuid = str(uuid.uuid4())
            filename = str(config['ckan.storage_path'])+'/storage/uploads/admin/'+data['template_file']
            template_org = data['template_org'] or u'all'
            owner_org = data['import_org']
            importer = g.user
            data_dict = {"import_uuid":import_uuid, "template_org":template_org, "owner_org":owner_org, "filename":filename, "importer":importer}
            log.info('Prepare to import data import_id:%r file:%r org:%r to_org:%r user:%r',import_uuid, filename, template_org, owner_org, importer)

            row_count = 0

            record_df = pd.read_excel(filename, header=[3], sheet_name='Temp2_Meta_Record')
            if template_org != 'all':
                row_count += record_df.iloc[:, 3].tolist().count(template_org)
            else:
                row_count += (len(record_df.index)-1)
            
            stat_df = pd.read_excel(filename, header=[3], sheet_name='Temp2_Meta_Stat')
            if template_org != 'all':
                row_count += stat_df.iloc[:, 3].tolist().count(template_org)
            else:
                row_count += (len(stat_df.index)-1)

            gis_df = pd.read_excel(filename, header=[3], sheet_name='Temp2_Meta_GIS')
            if template_org != 'all':
                row_count += gis_df.iloc[:, 3].tolist().count(template_org)
            else:
                row_count += (len(gis_df.index)-1)

            multi_df = pd.read_excel(filename, header=[3], sheet_name='Temp2_Meta_Multi')
            if template_org != 'all':
                row_count += multi_df.iloc[:, 3].tolist().count(template_org)
            else:
                row_count += (len(multi_df.index)-1)

            other_df = pd.read_excel(filename, header=[3], sheet_name='Temp2_Meta_Other')
            if template_org != 'all':
                row_count += other_df.iloc[:, 3].tolist().count(template_org)
            else:
                row_count += (len(other_df.index)-1)

            get_action('dataset_bulk_import')(context, data_dict)

            data_dict['row'] = row_count
            config["import_log"] = ''
            config['ckan.import_params'] = data_dict
            config['ckan.import_uuid'] = import_uuid
            config['ckan.import_row'] = row_count

            model.set_system_info('ckan.import_params', data_dict)
            model.set_system_info('ckan.import_uuid', import_uuid)
            model.set_system_info('ckan.import_row', row_count)
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            vars = {'data': data, 'errors': errors,
                    'error_summary': error_summary, 'form_items': items}
            return base.render('admin/dataset_import_form.html', extra_vars=vars)

        h.redirect_to(h.url_for(u'thai_gdc.import_dataset'))

    schema = logic.schema.update_configuration_schema()
    data = {}
    for key in schema:
        data[key] = config.get(key)

    vars = {'data': data, 'errors': {}, 'form_items': items}
    return base.render('admin/dataset_import_form.html', extra_vars=vars)

thai_gdc_blueprint.add_url_rule(u'/dataset/edit-datatype/<package_id>', view_func=datatype_patch, methods=["GET"])
thai_gdc_blueprint.add_url_rule(u'/ckan-admin/clear-import-log', view_func=clear_import_log)
thai_gdc_blueprint.add_url_rule(u'/user/edit/user_active', view_func=user_activate, methods=["GET"])
thai_gdc_blueprint.add_url_rule(u'/ckan-admin/banner-edit', view_func=edit_banner, methods=["GET", "POST"])
thai_gdc_blueprint.add_url_rule(u'/ckan-admin/popup-edit', view_func=edit_popup, methods=["GET", "POST"])
thai_gdc_blueprint.add_url_rule(u'/ckan-admin/dataset-export', view_func=export_dataset_init)
thai_gdc_blueprint.add_url_rule(u'/ckan-admin/dataset-export/<id>', view_func=export_dataset, methods=["GET"])
thai_gdc_blueprint.add_url_rule(u'/ckan-admin/dataset-import', view_func=import_dataset, methods=["GET", "POST"])
