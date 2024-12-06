# encoding: utf-8

import ckan.model as model
from sqlalchemy import func
from ckan.common import _
import ckan.lib.helpers as h

def get_last_modified_datasets(limit):
    try:
        package = model.Package
        q = model.Session.query(package.name, package.title, package.type, package.metadata_modified.label('date_modified')).filter(package.state == 'active').order_by(package.metadata_modified.desc()).limit(limit)
        packages = q.all()
    except:
        return []
    return packages

def get_datasets_by_organization():
    try:
        package = model.Package
        group = model.Group
    	q = model.Session.query(package.owner_org, group.title, func.count(package.id).label('count')).join(group, package.owner_org==group.id).filter(package.state == 'active').group_by(package.owner_org,group.title)
    	datasets_by_organization = q.all()
    except:
        return []
    return datasets_by_organization

def to_thaidate(time):
    try:
    	month = [
    	    _('January'), _('February'), _('March'), _('April'),
    	    _('May'), _('June'), _('July'), _('August'),
    	    _('September'), _('October'), _('November'), _('December')
    	]

    	raw = str(time)
    	tmp = raw.split(' ')
    	dte = tmp[0]

    	tmp = dte.split('-')
    	m_key = int(tmp[1]) - 1

    	if h.lang() == 'th':
            dt = u"{} {} {}".format(int(tmp[2]), month[m_key], int(tmp[0]) + 543)
    	else:
            dt = u"{} {}, {}".format(month[m_key], int(tmp[2]), int(tmp[0]))
    except:
        return
    return dt

