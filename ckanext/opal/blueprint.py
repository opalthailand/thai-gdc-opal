# encoding: utf-8

from flask import Blueprint, make_response, Response
import logging, csv, six, calendar
from ckan.plugins.toolkit import c, render, request, _
from ckan.common import config
import ckanext.opendstats.stats as stats_lib
import ckan.lib.helpers as h, helpers as my_h
from datetime import date
log = logging.getLogger(__name__)
today = date.today()

stats_route = Blueprint(u'opendstats', __name__, url_prefix=u'/site_stats')
stats = stats_lib.OpendStats()
external_stats = config.get('opendstats.external_dashboard')
def recent_created_datasets(limit=100, page=1):
    return {
        u'opendstats_data': stats.recent_created_datasets(),
        u'opendstats_page': 'recent_created_datasets'
    }

def recent_updated_datasets(limit=100, page=1):
    return {
        u'opendstats_data': stats.recent_updated_datasets(),
        u'opendstats_page': 'recent_updated_datasets'
    }

def most_edited_packages(limit=100, page=1):
    return {
        u'opendstats_data': stats.most_edited_packages(),
        u'opendstats_page': 'most_edited_packages'
    }

def top_package_owners(limit=100, page=1):
    return {
        u'opendstats_data': stats.top_package_owners(),
        u'opendstats_page': 'top_package_owners'
    }

def dataset_by_org(limit=100, page=1):
    return {
        u'opendstats_data': stats.by_org(),
        u'opendstats_page': 'by_org'
    }

def res_by_org(limit=100, page=1):
    return {
        u'opendstats_data': stats.res_by_org(),
        u'opendstats_page': 'res_by_org'
    }

def largest_groups(limit=100, page=1):
    return {
        u'opendstats_data': stats.largest_groups(),
        u'opendstats_page': 'largest_groups'
    }

def top_tags(limit=100, page=1):
    return {
        u'opendstats_data': stats.top_tags(),
        u'opendstats_page': 'top_tags'
    }

def summary_stats(limit=100, page=1):
    return {
        u'opendstats_data': stats.summary_stats(),
        u'opendstats_page': 'summary'
    }

def user_access_list(limit=100, page=1):
    return {
        u'opendstats_data': stats.user_access_list(),
        u'opendstats_page': 'user_access_list'
    }

def users_by_org(limit=100, page=1):
    return {
        u'opendstats_data': stats.users_by_organisation(),
        u'opendstats_page': 'users_by_org'
    }

def usage_by_org(limit=100, page=1):
    return {
        u'opendstats_data': stats.usage_summary_by_org(limit=limit, page=page),
        u'opendstats_page': 'usage_summary_by_org'
    }

def kw_search():
    res_list = []
    if my_h.check_table_column('discovery_searchterm', 'result'):
        res_list = [stats.keyword_search_result(), stats.keyword_search_noresult()]
    elif my_h.check_table_column('discovery_searchterm'):
        res_list = [stats.keyword_search_noresult_field()]
    return {
            u'opendstats_data': res_list,
            u'opendstats_page': 'stats_keywordsearch'
        }
def top_package_views():
    return {
        u'opendstats_data': stats.top_package_views(),
        u'opendstats_page': 'top_package_views'
    }


def index(stats_page=None):
    limit = 100
    page = h.get_page_number(request.args) or 1
    c.recent_period = stats.recent_period
    if stats_page == 'recent_created_datasets':
        extra_vars =  recent_created_datasets(limit=limit, page=page)
    elif stats_page == 'recent_updated_datasets':
        extra_vars =  recent_updated_datasets(limit=limit, page=page)
    elif stats_page == 'usage_summary_by_org' and h.check_access('sysadmin'):
        extra_vars =  usage_by_org(limit=limit, page=page)
    elif stats_page == 'most_edited_packages':
        extra_vars = most_edited_packages(limit=limit, page=page)
    elif stats_page == 'top_package_owners':
        extra_vars = top_package_owners(limit=limit, page=page)
    elif stats_page == 'by_org':
        extra_vars = dataset_by_org(limit=limit, page=page)
    elif stats_page == 'res_by_org':
        extra_vars = res_by_org(limit=limit, page=page)
    elif stats_page == 'largest_groups':
        extra_vars = largest_groups(limit=limit, page=page)
    elif stats_page == 'top_tags':
        extra_vars = top_tags(limit=limit, page=page)
    elif stats_page == 'user_access_list' and h.check_access('sysadmin'):
        extra_vars = user_access_list(limit=limit, page=page)
    elif stats_page == 'users_by_org' and h.check_access('sysadmin'):
        extra_vars = users_by_org(limit=limit, page=page)
    elif stats_page == 'stats_keywordsearch' and h.check_access('sysadmin'):
        extra_vars = kw_search()
    elif stats_page == 'top_package_views':
        extra_vars = top_package_views()
    elif stats_page == 'external_stats' and h.check_access('sysadmin'):
        extra_vars = {
            "opendstats_data": config.get('opendstats.external_dashboard_url'),
            "opendstats_page": "external_stats"
        }
    else:
        extra_vars = summary_stats(limit=limit, page=page)
    if stats_page == 'usage_summary_by_org':
        extra_vars["pages"] = h.Page(
            collection=extra_vars['opendstats_data']['data'],
            page=page,
            url=h.pager_url,
            items_per_page=limit,
            item_count=extra_vars['opendstats_data']['item_count'],
        )
    if external_stats and h.check_access('sysadmin'):
        c.external_stats = external_stats
    return render(u'ckanext/opendstats/index.html', extra_vars)

def export(stats_page):
    csv_header = []
    if six.PY2:
        from cStringIO import StringIO
        output = StringIO()
    else:
        import io
        output = io.StringIO()
    writer = csv.writer(output)
    if stats_page == 'usage_by_org' and h.check_access('sysadmin'):
        csv_header = [_('หน่วยงาน'), _('หน่วยงานต้นสังกัด'), _('ปี'), _('เดือน'), _('จำนวนเข้าชม'), _('จำนวนการดวน์โหลด'), _('จำนวนชุดข้อมูลที่สร้าง'), _('จำนวนครั้งที่มีการปรับปรุงชุดข้อมูล'), _('จำนวนทรัพยากรที่สร้าง')]
        # csv_header = ",".join(csv_header)
        writer.writerow(csv_header)
        data = stats.export_usage_by_org()
        for row in data:
            ym = list(row['tracking_month'].split('-'))
            line = [row['org_title'], row['parent_org_title'],ym[0], calendar.month_name[int(ym[1])], row['views'], row['downloads'], row['create_packages'], row['updated_packages'], row['create_resources']]
            writer.writerow(line)

        output.seek(0)

        file_name = "Report_Usage_by_org_{}".format(today.strftime('%d%m%Y'))
        headers = {"Content-Disposition":"attachment;filename={}.csv".format(file_name),
        "Content-Type": "text/csv"}
        return Response(output, mimetype="text/csv", headers=headers)

    if stats_page == 'stats_keywordsearch' and my_h.check_table_column('discovery_searchterm', 'result') and h.check_access('sysadmin'):
        csv_header = [_('ลำดับ'), _('คำค้น'), _('จำนวนการค้นหา'), _('จำนวนชุดข้อมูลที่พบ')]
        # csv_header = ",".join(csv_header)
        writer.writerow(csv_header)
        data = stats.export_keywordsearch()
        loob = 1
        for row in data:
            line = [str(loob), row.term, str(row.count), str(row.result)]
            loob += 1
            writer.writerow(line)

        output.seek(0)
        file_name = "Report_keywordsearch_{}".format(today.strftime('%d%m%Y'))
        headers = {"Content-Disposition":"attachment;filename={}.csv".format(file_name),
        "Content-Type": "text/csv"}
        return Response(output, mimetype="text/csv", headers=headers)

    return {'msg': 'ok'}

def second():
    c.stats_page = "second"
    extra_vars = {
        u'used_data_by_organi': stats.used_data_by_organize(10,40),
        u'opendstats_page': 'second'
    }
    return render(u'ckanext/opendstats/second.html', extra_vars)

stats_route.add_url_rule("",endpoint="index", view_func=index)
stats_route.add_url_rule("/stats",endpoint="index", view_func=index)
stats_route.add_url_rule("/<stats_page>",endpoint="index", view_func=index)
stats_route.add_url_rule("/second",endpoint="second", view_func=second)
stats_route.add_url_rule("/exports/<stats_page>", endpoint="export", view_func=export)