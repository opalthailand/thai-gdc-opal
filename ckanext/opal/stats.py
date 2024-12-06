# encoding: utf-8

import datetime
import logging
from ckan.common import config
from six import text_type
from sqlalchemy import Table, select, join, func, and_
from sqlalchemy.sql import text
import ckan.plugins as p
import ckan.model as model
import db, re

log = logging.getLogger(__name__)
cache_enabled = p.toolkit.asbool(
    config.get('ckanext.stats.cache_enabled', False)
)

if cache_enabled:
    log.warn(
        'ckanext.stats does not support caching in current implementations'
    )

DATE_FORMAT = '%Y-%m-%d'


def table(name):
    return Table(name, model.meta.metadata, autoload=True)


def datetime2date(datetime_):
    return datetime.date(datetime_.year, datetime_.month, datetime_.day)

class OpendStats(object):
    recent_period = config.get('dga.recent_time_period') or 60
    recent_limit = config.get('dga.recent_page_limit') or 50
    
    @classmethod
    def top_pageckage_view(cls, limit=3, page_no=0):
        pass

    @classmethod
    def keyword_search_result(cls, limit=50):
        searchterm = table('discovery_searchterm')
        result = model.Session.query(searchterm.c.id, 
        searchterm.c.term, 
        searchterm.c.count, 
        searchterm.c.result
        ).filter(searchterm.c.result > 0
        ).order_by(searchterm.c.count.desc()).limit(limit).all()

        return result
    
    def keyword_search_noresult(cls, limit=50):
        searchterm = table('discovery_searchterm')
        result = model.Session.query(searchterm.c.id, 
        searchterm.c.term, 
        searchterm.c.count, 
        searchterm.c.result
        ).filter(searchterm.c.result == 0
        ).order_by(searchterm.c.count.desc()).limit(limit).all()

        return result
    
    def keyword_search_noresult_field(cls, limit=50):
        searchterm = table('discovery_searchterm')
        result = model.Session.query(searchterm.c.id, 
        searchterm.c.term, 
        searchterm.c.count
        ).order_by(searchterm.c.count.desc()).limit(limit).all()

        return result

    def export_keywordsearch(cls):
        searchterm = table('discovery_searchterm')
        result = model.Session.query(searchterm.c.id, 
        searchterm.c.term, 
        searchterm.c.count, 
        searchterm.c.result
        ).order_by(searchterm.c.count.desc()).all()

        return result
    

    @classmethod
    def export_usage_by_org(cls):
        usage = table('ckanext_opendstats_usage_by_org')
        sql = select([usage.c.org_title, usage.c.org_name, usage.c.org_id, usage.c.parent_org_title,
            usage.c.parent_org_name, usage.c.parent_org_id, usage.c.tracking_month, func.sum(usage.c.views).label('views'),
            func.sum(usage.c.downloads).label('downloads'), func.sum(usage.c.create_packages).label('create_packages'), func.sum(usage.c.updated_packages).label('updated_packages'), func.sum(usage.c.create_resources).label('create_resources')]). \
            group_by(usage.c.org_title, usage.c.org_name, usage.c.org_id, usage.c.parent_org_title,
            usage.c.parent_org_name, usage.c.parent_org_id, usage.c.tracking_month).order_by(func.sum(usage.c.views).desc())
        
        res_usage = model.Session.execute(sql).fetchall()
        return res_usage

    @classmethod
    def usage_summary_by_org(cls, limit=100, page=1):
        offset = (page - 1) * limit
        def fetch_used_dataset_by_org(offset, limit):
            connection = model.Session.connection()
            res = connection.execute('''
            SELECT pkv.org_title,
                pkv.org_name,
                pkv.org_id,
                pkv.parent_org_title, 
                pkv.parent_org_name, 
                pkv.parent_org_id,
				pkv.tracking_month,
                SUM(views) AS views,
				SUM(downloads) AS downloads,
				SUM(create_packages) AS create_packages,
				SUM(updated_packages) AS updated_packages,
				SUM(create_resources) AS create_resources
            FROM ckanext_opendstats_usage_by_org pkv
            GROUP BY pkv.org_title,
                pkv.org_name,
                pkv.org_id,
                pkv.parent_org_title, 
                pkv.parent_org_name, 
                pkv.parent_org_id,
				pkv.tracking_month
            ORDER BY views DESC
            OFFSET {} LIMIT {};
            '''.format(str(offset), str(limit))).fetchall()
            return res
        def count_data():
            connection = model.Session.connection()
            res = connection.execute('''
            SELECT COUNT(pkv.*)
            FROM ckanext_opendstats_usage_by_org pkv
            GROUP BY pkv.org_title,
                pkv.org_name,
                pkv.org_id,
                pkv.parent_org_title, 
                pkv.parent_org_name, 
                pkv.parent_org_id,
                pkv.tracking_month;
            ''').fetchall()
            return res

        if cache_enabled:
            key = 'used_dataset_by_org_limit_%s' % str(limit)
            res_pkgs = our_cache.get_value(key=key,
                                           createfunc=fetch_used_dataset_by_org,
                                           expiretime=cache_default_timeout)
        else:
            res_pkgs = fetch_used_dataset_by_org(offset, limit)
            item_count = len(count_data())

        return {'data':res_pkgs, 'item_count': item_count}
    @classmethod
    def top_package_views(cls, limit=20):
        sql = '''
            SELECT pkv.package_id,
                pkv.package_name,
                pkv.package_title,
                SUM(pkv.count) AS views,
                (SELECT COALESCE(sum(count),0) AS count_data 
                    FROM public.ckanext_opendstats_resource_downloads
                    WHERE package_id = pkv.package_id
                ) AS downloads,
                (SELECT recent_views 
                    FROM public.ckanext_opendstats_package_views
                    WHERE package_id = pkv.package_id
                    ORDER BY tracking_date DESC
                    LIMIT 1
                ) AS recent_views,
                COALESCE((SELECT recent_views
                    FROM public.ckanext_opendstats_resource_downloads
                    WHERE package_id = pkv.package_id
                    ORDER BY tracking_date DESC
                    LIMIT 1),
                0) AS recent_downloads
            FROM public.ckanext_opendstats_package_views pkv
            GROUP BY pkv.package_id,
                pkv.package_name,
                pkv.package_title
            ORDER BY views DESC
            LIMIT 20
        '''
        res = model.Session.execute(sql).fetchall()
        return res

    @classmethod
    def top_rated_packages(cls, limit=10):
        # NB Not using sqlalchemy as sqla 0.4 doesn't work using both group_by
        # and apply_avg
        def fetch_top_rated_packages():
            package = table('package')
            rating = table('rating')
            sql = select([package.c.id, func.avg(rating.c.rating), func.count(rating.c.rating)],
                         from_obj=[package.join(rating)]). \
                where(package.c.private == 'f'). \
                group_by(package.c.id). \
                order_by(func.avg(rating.c.rating).desc(), func.count(rating.c.rating).desc()). \
                limit(limit)
            res_ids = model.Session.execute(sql).fetchall()
            return [(model.Session.query(model.Package).get(unicode(pkg_id)), avg, num) for pkg_id, avg, num in res_ids]

        if cache_enabled:
            key = 'top_rated_packages_limit_%s' % str(limit)
            res_pkgs = our_cache.get_value(key=key,
                                           createfunc=fetch_top_rated_packages,
                                           expiretime=cache_default_timeout)
        else:
            res_pkgs = fetch_top_rated_packages()
        return res_pkgs

    @classmethod
    def most_edited_packages(cls, limit=10):

        def fetch_most_edited_packages():
            connection = model.Session.connection()
            res = connection.execute("select a.object_id, count(a.id) from activity a inner join package p on a.object_id = p.id "
                                    "where p.private = 'f' and p.state = 'active' and p.type = 'dataset' and a.activity_type = 'changed package' "
                                    "group by a.object_id order by count(a.id) desc limit {recent_limit};".format(
                                        recent_limit=limit)).fetchall()
            return [(model.Session.query(model.Package).get(unicode(pkg_id)), val) for pkg_id, val in res]

        if cache_enabled:
            key = 'most_edited_packages_limit_%s' % str(limit)
            res_pkgs = our_cache.get_value(key=key,
                                           createfunc=fetch_most_edited_packages,
                                           expiretime=cache_default_timeout)
        else:
            res_pkgs = fetch_most_edited_packages()

        return res_pkgs

    @classmethod
    def largest_groups(cls, limit=10):

        def fetch_largest_groups():
            member = table('member')
            s = select([member.c.group_id, func.count(member.c.table_id)]). \
                group_by(member.c.group_id). \
                where(member.c.group_id != None). \
                where(member.c.table_name == 'package'). \
                where(member.c.capacity == 'public'). \
                where(member.c.state == 'active'). \
                order_by(func.count(member.c.table_id).desc())
                #limit(limit)

            res_ids = model.Session.execute(s).fetchall()
            return [(model.Session.query(model.Group).get(unicode(group_id)), val) for group_id, val in res_ids]

        if cache_enabled:
            key = 'largest_groups_limit_%s' % str(limit)
            res_groups = our_cache.get_value(key=key,
                                             createfunc=fetch_largest_groups,
                                             expiretime=cache_default_timeout)
        else:
            res_groups = fetch_largest_groups()
        return res_groups
    
    @classmethod
    def top_tags(cls, limit=50, returned_tag_info='object'):  # by package
        assert returned_tag_info in ('name', 'id', 'object')
        tag = table('tag')
        package_tag = table('package_tag')
        package = table('package')
        if returned_tag_info == 'name':
            from_obj = [package_tag.join(tag)]
            tag_column = tag.c.name
        else:
            from_obj = None
            tag_column = package_tag.c.tag_id
        j = join(
            package_tag, package, package_tag.c.package_id == package.c.id
        )
        s = select([tag_column,
                    func.count(package_tag.c.package_id)],
                   from_obj=from_obj).select_from(j).where(
                       and_(
                           package_tag.c.state == 'active',
                           package.c.private == False,
                           package.c.state == 'active',
                           package.c.type == 'dataset'
                       )
                   )
        s = s.group_by(tag_column).order_by(
            func.count(package_tag.c.package_id).desc()
        ).limit(limit)
        res_col = model.Session.execute(s).fetchall()
        if returned_tag_info in ('id', 'name'):
            return res_col
        elif returned_tag_info == 'object':
            res_tags = [
                (model.Session.query(model.Tag).get(text_type(tag_id)), val)
                for tag_id, val in res_col
            ]
            return res_tags

    @classmethod
    def by_org(cls, limit=10):

        def fetch_by_org():
            connection = model.Session.connection()
            res = connection.execute("select package.owner_org, package.private, count(*) from package \
		        inner join \"group\" on package.owner_org = \"group\".id \
		        where package.state='active' and package.type = 'dataset'\
		        group by package.owner_org,\"group\".name, package.private \
		        order by \"group\".name, package.private;").fetchall()
            return [(model.Session.query(model.Group).get(unicode(group_id)), private, val) for group_id, private, val
                      in res]

        if cache_enabled:
            key = 'fetch_by_org'
            res_groups = our_cache.get_value(key=key,
                                             createfunc=fetch_by_org,
                                             expiretime=cache_default_timeout)
        else:
            res_groups = fetch_by_org()

        return res_groups

    @classmethod
    def res_by_org(cls, limit=10):

        def fetch_res_by_org():
            connection = model.Session.connection()
            reses = connection.execute("select owner_org,format,count(*) from \
            resource inner join package on resource.package_id = package.id where package.state = 'active' and package.type = 'dataset' and resource.state = 'active' group by owner_org,format order by count desc;").fetchall();
            group_ids = []
            group_tab = {}
            group_spatial = {}
            group_other = {}
            for group_id, format, count in reses:
                if group_id not in group_ids:
                    group_ids.append(group_id)
                    group_tab[group_id] = 0
                    group_spatial[group_id] = 0
                    group_other[group_id] = 0
                if re.search('xls|csv|ms-excel|spreadsheetml.sheet|zip|netcdf', format, re.IGNORECASE):
                    group_tab[group_id] = group_tab[group_id] + count
                elif re.search('wms|wfs|wcs|shp|kml|kmz', format, re.IGNORECASE):
                    group_spatial[group_id] = group_spatial[group_id] + count
                else:
                    group_other[group_id] = group_other[group_id] + count
            return [(model.Session.query(model.Group).get(unicode(group_id)), group_tab[group_id], group_spatial[group_id],
                     group_other[group_id], group_tab[group_id] + group_spatial[group_id] + group_other[group_id]) for
                    group_id in group_ids]

        if cache_enabled:
            key = 'res_by_org'
            res_by_orgs = our_cache.get_value(key=key,
                                              createfunc=fetch_res_by_org,
                                              expiretime=cache_default_timeout)
        else:
            res_by_orgs = fetch_res_by_org()

        return res_by_orgs

    @classmethod
    def top_active_orgs(cls, limit=10):

        def fetch_top_active_orgs():
            connection = model.Session.connection()
            res = connection.execute("select package.owner_org, count(*) from package \
            inner join (select distinct package_id from resource) as r on package.id = r.package_id \
            inner join \"group\" on package.owner_org = \"group\".id \
                    inner join (select distinct object_id from activity where activity.timestamp > (now() - interval '60 day')) \
                    latestactivities on latestactivities.object_id = package.id \
                    where package.state='active' \
                    and package.private = 'f' \
                    and package.type = 'dataset' \
                    group by package.owner_org \
                    order by count(*) desc;").fetchall()
            return [(model.Session.query(model.Group).get(unicode(group_id)), val) for group_id, val in res]

        if cache_enabled:
            key = 'top_active_orgs'
            res_groups = our_cache.get_value(key=key,
                                             createfunc=fetch_top_active_orgs,
                                             expiretime=cache_default_timeout)
        else:
            res_groups = fetch_top_active_orgs()
        return res_groups

    @classmethod
    def top_package_owners(cls, limit=10):

        def fetch_top_package_owners():
            userid_count = model.Session.query(
            model.Package.creator_user_id,
            func.count(model.Package.creator_user_id)
                ).filter(model.Package.state == 'active'
                ).filter(model.Package.type == 'dataset'
                 ).filter(model.Package.private == False).group_by(
                     model.Package.creator_user_id
                 ).order_by(func.count(model.Package.creator_user_id).desc()
                            ).limit(limit).all()
            user_count = [
                (model.Session.query(model.User).get(text_type(user_id)), count)
                for user_id, count in userid_count
                if user_id
            ]
            return user_count

        if cache_enabled:
            key = 'top_package_owners_limit_%s' % str(limit)
            res_groups = our_cache.get_value(key=key,
                                             createfunc=fetch_top_package_owners,
                                             expiretime=cache_default_timeout)
        else:
            res_groups = fetch_top_package_owners()
        return res_groups

    @classmethod
    def summary_stats(cls):

        def fetch_summary_stats():
            connection = model.Session.connection()

            res = connection.execute(text("SELECT 'Total Organizations', count(*) from \"group\" where type = 'organization' and state = 'active' union "
                    "select 'Total Datasets', count(*) from package where package.type='dataset' and package.state='active' and package.id not in (select package_id from package_extra where key = 'harvest_portal') union "
                    "select 'Total Data Files/Resources', count(*) from resource left join package on resource.package_id = package.id where resource.state='active' and package_id not IN (select distinct package_id from package INNER JOIN  package_extra on package.id = package_extra.package_id where key = 'harvest_portal') and package.state = 'active' and package.type = 'dataset' union "
                    "select 'Total Data API Resources', count(*) from resource left join package on resource.package_id = package.id where resource.state='active' and resource.extras like :string and package_id not IN (select distinct package_id from package INNER JOIN package_extra on package.id = package_extra.package_id where key = 'harvest_portal') and package.state = 'active' and package.type = 'dataset';").bindparams(string="%\"datastore_active\": true%")).fetchall();
            return res

        if cache_enabled:
            key = 'summary_stats'
            sum_stats = our_cache.get_value(key=key,
                                            createfunc=fetch_summary_stats,
                                            expiretime=cache_fast_timeout)
        else:
            sum_stats = fetch_summary_stats()

        return sum_stats


    @classmethod
    def activity_counts(cls):

        def fetch_activity_counts():
            connection = model.Session.connection()
            return connection.execute(
                "select to_char(timestamp, 'YYYY-MM') as month,activity_type, count(*) from activity group by month, activity_type order by month;").fetchall();

        if cache_enabled:
            key = 'activity_counts'
            res = our_cache.get_value(key=key,
                                      createfunc=fetch_activity_counts,
                                      expiretime=cache_default_timeout)
        else:
            res = fetch_activity_counts()

        return res

    @classmethod
    def users_by_organisation(cls):

        def fetch_user_by_organisation():
            connection = model.Session.connection()
            res = connection.execute(
                "select \"group\".id,\"user\".id ,capacity, sysadmin from \"group\""
                "        inner join member on member.group_id = \"group\".id"
                "        inner join \"user\" on member.table_id = \"user\".id"
                "        where capacity is not null and \"group\".type = 'organization' and member.state='active' order by \"group\".title, \"user\".name, capacity;").fetchall()
            return [(model.Session.query(model.Group).get(unicode(org)), model.Session.query(model.User).get(unicode(user_id)), role, sysadmin ) for
                      (org, user_id, role, sysadmin) in res]

        if cache_enabled:
            key = 'users_by_organisation'
            res = our_cache.get_value(key=key,
                                      createfunc=fetch_user_by_organisation,
                                      expiretime=cache_default_timeout)
        else:
            res = fetch_user_by_organisation()

        return res

    @classmethod
    def user_access_list(cls):

        def fetch_user_access_list():
            connection = model.Session.connection()
            res = connection.execute(
                "select \"user\".id ,sysadmin,capacity,max(last_active),array_agg(\"group\".name) member_of_orgs from \"user\" "
                " left outer join member on member.table_id = \"user\".id "\
                " left OUTER JOIN (select max(timestamp) last_active,user_id from activity group by user_id) a on \"user\".id = a.user_id "\
                " left outer join \"group\" on member.group_id = \"group\".id  where \"group\".is_organization is true and (sysadmin = 't' or (capacity is not null and member.state = 'active'))"\
                " group by \"user\".id ,sysadmin,capacity order by max(last_active) desc;").fetchall()
            return [(model.Session.query(model.User).get(unicode(user_id)), sysadmin, role, last_active, orgs) for
                      (user_id, sysadmin, role, last_active, orgs) in res]

        if cache_enabled:
            key = 'user_access_list'
            res = our_cache.get_value(key=key,
                                      createfunc=fetch_user_access_list,
                                      expiretime=cache_default_timeout)
        else:
            res = fetch_user_access_list()

        return res

    @classmethod
    def recent_created_datasets(cls):

        def fetch_recent_created_datasets():
            connection = model.Session.connection()
            result = connection.execute("select metadata_created as timestamp,package.id as package_id,creator_user_id, maintainer from package "
                                        "full outer join (select object_id from activity "
                                        "where activity_type = 'new package' and timestamp > NOW() - interval '{recent_period} day') act on act.object_id=package.id "
                                        "where type = 'dataset' and private = 'f' and state='active' "
                                        "and metadata_created > NOW() - interval '{recent_period} day' order by metadata_created asc limit {recent_limit};".format(
                                            recent_period=cls.recent_period,
                                            recent_limit=cls.recent_limit)).fetchall()
            r = []

            for timestamp, package_id, creator_user_id, maintainer in result:
                package = model.Session.query(model.Package).get(unicode(package_id))
                if creator_user_id:
                    user = model.Session.query(model.User).get(unicode(creator_user_id))
                else:
                    user = model.User.by_name(unicode(maintainer))
                if package.owner_org:
                    r.append((timestamp, package, model.Session.query(model.Group).get(unicode(package.owner_org)),user))
                else:
                    r.append((timestamp, package, None,user))
            return r

        if cache_enabled:
            key = 'recent_created_datasets'
            res = our_cache.get_value(key=key,
                                      createfunc=fetch_recent_created_datasets,
                                      expiretime=cache_default_timeout)
        else:
            res = fetch_recent_created_datasets()

        return res

    @classmethod
    def recent_updated_datasets(cls):

        def fetch_recent_updated_datasets():
            connection = model.Session.connection()
            result = connection.execute("select distinct timestamp,package.id as package_id,user_id from package "
									    "full outer join activity on activity.object_id=package.id "
                                        "where activity_type = 'changed package' "
                                        "and timestamp::date > NOW() - interval '{recent_period} day' and type = 'dataset' and private = 'f' and state='active' "
                                        "order by timestamp asc limit {recent_limit};".format(
                                            recent_period=cls.recent_period,
                                            recent_limit=cls.recent_limit)).fetchall()
            r = []
            for timestamp, package_id, user_id in result:
                package = model.Session.query(model.Package).get(unicode(package_id))
                if package.owner_org:
                    r.append((timestamp, package, model.Session.query(model.Group).get(unicode(package.owner_org)),
                        model.Session.query(model.User).get(unicode(user_id))))
                else:
                    r.append(
                        (timestamp, package, None, model.Session.query(model.User).get(unicode(user_id))))
            return r

        if cache_enabled:
            key = 'recent_updated_datasets'
            res = our_cache.get_value(key=key,
                                      createfunc=fetch_recent_updated_datasets,
                                      expiretime=cache_default_timeout)
        else:
            res = fetch_recent_updated_datasets()

        return res
