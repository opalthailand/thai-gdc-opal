import logging
import sqlalchemy as sa
from ckan.common import config

log = logging.getLogger(__name__)

def create_view_org_hierarchy(model):
    sql = '''
    CREATE OR REPLACE VIEW public._org_hierarchy
        AS
        SELECT ( SELECT "group".id
                FROM "group"
                WHERE "group".id = mem.group_id) AS parent_org_id,
            ( SELECT "group".title
                FROM "group"
                WHERE "group".id = mem.table_id) AS parent_org_title,
            ( SELECT "group".name
                FROM "group"
                WHERE "group".id = mem.table_id) AS parent_org_name,
            grp.id AS org_id,
            grp.title AS org_title,
            grp.name AS org_name
        FROM "group" grp
            LEFT JOIN ( SELECT member.group_id,
                    member.table_id
                FROM member
                WHERE member.state = 'active'::text AND member.table_name = 'group'::text) mem ON grp.id = mem.group_id
        WHERE grp.state = 'active'::text AND grp.is_organization = true;
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def create_table_ckanext_opendstats_package_views(model):
    sql = '''
    SELECT pck.id AS package_id,
        pck.name AS package_name,
        pck.title AS package_title,
        date(pck.metadata_created) AS metadata_created_date,
        to_char(pck.metadata_created, 'YYYY-MM'::text) AS metadata_created_month,
        orc.parent_org_title,
        orc.parent_org_name,
        orc.parent_org_id,
        orc.org_title,
        orc.org_name,
        orc.org_id,
        tms.count,
        tms.running_total,
        tms.recent_views,
        tms.url,
        tms.tracking_date,
        to_char(tms.tracking_date::timestamp with time zone, 'YYYY-MM'::text) AS tracking_month
        INTO TABLE ckanext_opendstats_package_views
    FROM package pck
        JOIN _org_hierarchy orc ON pck.owner_org = orc.org_id
        JOIN tracking_summary tms ON tms.package_id = pck.id
    WHERE pck.state = 'active'::text;
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def create_table_ckanext_opendstats_resource_downloads(model):
    sql = '''
    SELECT orc.org_id,
        orc.org_name,
        orc.org_title,
        orc.parent_org_id,
        orc.parent_org_name,
        orc.parent_org_title,
        pck.id AS package_id,
        pck.name AS package_name,
        pck.title AS package_title,
        rcs.id AS resource_id,
        rcs.name AS resource_name,
        rcs.created AS resource_created_date,
        to_char(rcs.created, 'YYYY-MM') AS resource_created_month,
        tms.url,
        tms.count,
        tms.running_total,
        tms.recent_views,
        tms.tracking_date,
        to_char(tms.tracking_date::timestamp with time zone, 'YYYY-MM'::text) AS tracking_month
        INTO TABLE ckanext_opendstats_resource_downloads
    FROM resource rcs
        JOIN package pck ON rcs.package_id = pck.id
        JOIN _org_hierarchy orc ON pck.owner_org = orc.org_id
        JOIN tracking_summary tms ON tms.tracking_type::text = 'resource'::text
    WHERE pck.state = 'active'::text AND tms.url ~~ (('%'::text || rcs.id) || '/download%'::text);
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def create_table_ckanext_opendstats_usage_by_org(model):
    sql = '''
    SELECT pkv.package_id,
		pkv.package_name,
		pkv.package_title,
		pkv.org_title,
        pkv.org_name,
        pkv.org_id,
        pkv.parent_org_title, 
        pkv.parent_org_name, 
        pkv.parent_org_id,
        pkv.tracking_date,
        pkv.tracking_month,
        SUM(pkv.count) AS views,
        (SELECT COALESCE(sum(count),0) AS count_data 
            FROM ckanext_opendstats_resource_downloads
            WHERE tracking_date = pkv.tracking_date AND org_title = pkv.org_title 
        ) AS downloads,
        (SELECT COUNT(id) FROM package 
            WHERE state = 'active' AND 
                owner_org = pkv.org_id AND 
                DATE(metadata_created) = pkv.tracking_date
        ) AS create_packages,
		(SELECT COUNT(id) FROM activity 
            WHERE activity_type = 'changed package' AND 
                object_id = pkv.package_id AND 
                DATE(timestamp) = pkv.tracking_date
        ) AS updated_packages,
        (SELECT COUNT(id) FROM resource
            WHERE state = 'active' AND
                package_id in (SELECT id FROM package WHERE owner_org = pkv.org_id) AND
                DATE(created) = pkv.tracking_date
        ) AS create_resources
    INTO ckanext_opendstats_usage_by_org
    FROM ckanext_opendstats_package_views pkv
    GROUP BY pkv.package_id,
		pkv.package_name,
		pkv.package_title,
		pkv.org_title,
        pkv.org_name,
        pkv.org_id,
        pkv.parent_org_title, 
        pkv.parent_org_name, 
        pkv.parent_org_id,
        pkv.tracking_date,
        pkv.tracking_month;
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def clear_latest_data(model):
    sql = '''
        DELETE FROM public.ckanext_opendstats_package_views 
            WHERE tracking_date >= (
                SELECT tracking_date FROM public.ckanext_opendstats_package_views
                order by tracking_date DESC
            limit 1
            );
        DELETE FROM public.ckanext_opendstats_resource_downloads 
            WHERE tracking_date >= (
                SELECT tracking_date FROM public.ckanext_opendstats_resource_downloads
                order by tracking_date DESC
                limit 1
            );
        DELETE FROM public.ckanext_opendstats_usage_by_org 
            WHERE tracking_date >= (
                SELECT tracking_date FROM public.ckanext_opendstats_usage_by_org
                order by tracking_date DESC
                limit 1
            );
    '''
    if config.get('opendstats.special_group'):
        sql += '''
        DELETE FROM public.ckanext_opendstats_views_as_category 
            WHERE tracking_date >= (
                SELECT tracking_date FROM public.ckanext_opendstats_views_as_category
                order by tracking_date DESC
                limit 1
            );
        DELETE FROM public.ckanext_opendstats_downloads_as_category 
            WHERE tracking_date >= (
                SELECT tracking_date FROM public.ckanext_opendstats_downloads_as_category
                order by tracking_date DESC
                limit 1
            );
        DELETE FROM public.ckanext_opendstats_usage_as_category 
            WHERE tracking_date >= (
                SELECT tracking_date FROM public.ckanext_opendstats_usage_as_category
                order by tracking_date DESC
                limit 1
            );
        '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def fetch_new_data_package_views(model):
    sql = '''
    INSERT INTO  public.ckanext_opendstats_package_views
    SELECT pck.id AS package_id,
        pck.name AS package_name,
        pck.title AS package_title,
        date(pck.metadata_created) AS metadata_created_date,
        to_char(pck.metadata_created, 'YYYY-MM'::text) AS metadata_created_month,
        orc.parent_org_title,
        orc.parent_org_name,
        orc.parent_org_id,
        orc.org_title,
        orc.org_name,
        orc.org_id,
        tms.count,
        tms.running_total,
        tms.recent_views,
        tms.url,
        tms.tracking_date,
        to_char(tms.tracking_date::timestamp with time zone, 'YYYY-MM'::text) AS tracking_month
    FROM package pck
        JOIN _org_hierarchy orc ON pck.owner_org = orc.org_id
        JOIN tracking_summary tms ON tms.package_id = pck.id
    WHERE pck.state = 'active'::text
    '''
    if check_empty_table(model, 'tracking_date', 'ckanext_opendstats_package_views'):
        sql += ''' 
        AND tms.tracking_date > (SELECT tracking_date FROM public.ckanext_opendstats_package_views order by tracking_date DESC limit 1);
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def fetch_new_data_resource_downloads(model):
    sql = '''
    INSERT INTO  public.ckanext_opendstats_resource_downloads
    SELECT orc.org_id,
        orc.org_name,
        orc.org_title,
        orc.parent_org_id,
        orc.parent_org_name,
        orc.parent_org_title,
        pck.id AS package_id,
        pck.name AS package_name,
        pck.title AS package_title,
        rcs.id AS resource_id,
        rcs.name AS resource_name,
        rcs.created AS resource_created_date,
        to_char(rcs.created, 'YYYY-MM') AS resource_created_month,
        tms.url,
        tms.count,
        tms.running_total,
        tms.recent_views,
        tms.tracking_date,
        to_char(tms.tracking_date::timestamp with time zone, 'YYYY-MM'::text) AS tracking_month
    FROM resource rcs
        JOIN package pck ON rcs.package_id = pck.id
        JOIN _org_hierarchy orc ON pck.owner_org = orc.org_id
        JOIN tracking_summary tms ON tms.tracking_type::text = 'resource'::text
    WHERE pck.state = 'active'::text AND tms.url ~~ (('%'::text || rcs.id) || '/download%'::text)
    '''
    if check_empty_table(model, 'tracking_date', 'ckanext_opendstats_resource_downloads'):
        sql += ''' 
        AND tms.tracking_date > (SELECT tracking_date FROM public.ckanext_opendstats_resource_downloads order by tracking_date DESC limit 1);
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def fetch_new_data_usage_by_org(model):
    sql = '''
    INSERT INTO public.ckanext_opendstats_usage_by_org
    SELECT pkv.package_id,
		pkv.package_name,
		pkv.package_title,
		pkv.org_title,
        pkv.org_name,
        pkv.org_id,
        pkv.parent_org_title, 
        pkv.parent_org_name, 
        pkv.parent_org_id,
        pkv.tracking_date,
        pkv.tracking_month,
        SUM(pkv.count) AS views,
        (SELECT COALESCE(sum(count),0) AS count_data 
            FROM ckanext_opendstats_resource_downloads
            WHERE tracking_date = pkv.tracking_date AND org_title = pkv.org_title 
        ) AS downloads,
        (SELECT COUNT(id) FROM package 
            WHERE state = 'active' AND 
                owner_org = pkv.org_id AND 
                DATE(metadata_created) = pkv.tracking_date
        ) AS create_packages,
		(SELECT COUNT(id) FROM activity 
            WHERE activity_type = 'changed package' AND 
                object_id = pkv.package_id AND 
                DATE(timestamp) = pkv.tracking_date
        ) AS updated_packages,
        (SELECT COUNT(id) FROM resource
            WHERE state = 'active' AND
                package_id in (SELECT id FROM package WHERE owner_org = pkv.org_id) AND
                DATE(created) = pkv.tracking_date
        ) AS create_resources
    FROM ckanext_opendstats_package_views pkv
    '''
    if check_empty_table(model, 'tracking_date', 'ckanext_opendstats_usage_by_org'):
        sql += '''
        WHERE pkv.tracking_date > (SELECT tracking_date FROM public.ckanext_opendstats_usage_by_org order by tracking_date DESC limit 1)
        '''
    sql += '''
    GROUP BY pkv.package_id,
		pkv.package_name,
		pkv.package_title,
        pkv.org_title,
        pkv.org_name,
        pkv.org_id,
        pkv.parent_org_title, 
        pkv.parent_org_name, 
        pkv.parent_org_id,
        pkv.tracking_date,
        pkv.tracking_month;
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sa.sql.text(sql))
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

def check_empty_table(model, field, table_name):

    try:
        result = model.Session.execute("SELECT {} FROM public.{} order by {} DESC limit 1".format(field, table_name, field)).fetchall()
    except sa.exc.ProgrammingError as e:
        result = []
    model.Session.commit()
    return True if len(result) > 0 else False

def check_column_table(model, tb_name):
    try:
        result = model.Session.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '{}';".format(tb_name))
        result = result.fetchall()
    except sa.exc.ProgrammingError:
        # pass
        result = []
    model.Session.commit()
    return result

def check_db_views(model, view_name):
    result = {}
    tbl_has = 0;
    try:
        # result = model.Session.execute("SELECT EXISTS ( SELECT 1 FROM pg_tables WHERE tablename = {} ) AS table_existence".format(view_name))
        result = model.Session.execute("SELECT * FROM {} LIMIT 1".format(view_name))
        result = result.fetchone()
        if result is not None:
            tbl_has = len(result)
    except sa.exc.SQLAlchemyError as e:
        pass
    model.Session.commit()
    if tbl_has > 0:
        return True
    else:
        return False