# encoding: utf-8

from flask import Blueprint
from flask.views import MethodView
from datetime import datetime
import ckan.logic as logic, logging, ckan.model as model, ckan.lib.base as base
import ckan.plugins.toolkit as toolkit
import ckan.lib.authenticator as authenticator
import ckan.lib.helpers as h
from sqlalchemy import Table
from ckan.common import _, g, request, config, asbool
from ckan.views.user import _edit_form_to_db_schema, set_repoze_user, _extra_template_variables, edit_user_form
import ckan.lib.navl.dictization_functions as dictization_functions

log = logging.getLogger(__name__)
ext_route = Blueprint('notipasschg', __name__)

# Mock mailer for testing
if toolkit.check_ckan_version(max_version='2.8.99'):
    import ckan.lib.mailer as mailer
else:
    from ckan.lib import mailer

if toolkit.testing:  # Only mock during tests
    def mock_mail_user(*args, **kwargs):
        pass  # Do nothing during tests
    mailer.mail_user = mock_mail_user


def _get_sysadmin():
    user = Table('user', model.meta.metadata, autoload=True)
    sysadmins = model.Session.query(user.c.id,
                                    user.c.name,
                                    user.c.fullname.label('display_name'),
                                    user.c.email
                                    ).filter(user.c.sysadmin == True, user.c.email != None, user.c.state == 'active').all()
    return sysadmins


class EditView(MethodView):
    def _prepare(self, id):
        context = {
            u'save': u'save' in request.form,
            u'schema': _edit_form_to_db_schema(),
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        if id is None:
            if g.userobj:
                id = g.userobj.id
            else:
                base.abort(400, _(u'No user specified'))
        data_dict = {u'id': id}

        try:
            logic.check_access(u'user_update', context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit a user.'))
        return context, id

    def post(self, id=None):
        context, id = self._prepare(id)
        if not context[u'save']:
            return self.get(id)

        if id in (g.userobj.id, g.userobj.name):
            current_user = True
        else:
            current_user = False
        old_username = g.userobj.name

        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
            data_dict.update(logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.files))))
            )

        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))
        data_dict.setdefault(u'activity_streams_email_notifications', False)

        context[u'message'] = data_dict.get(u'log_message', u'')
        data_dict[u'id'] = id
        email_changed = data_dict[u'email'] != g.userobj.email

        if (data_dict[u'password1']
                and data_dict[u'password2']) or email_changed:
            identity = {
                u'login': g.user,
                u'password': data_dict[u'old_password']
            }
            auth = authenticator.UsernamePasswordAuthenticator()

            if auth.authenticate(request.environ, identity) != g.user:
                errors = {
                    u'oldpassword': [_(u'Password entered was incorrect')]
                }
                error_summary = {_(u'Old Password'): _(u'incorrect password')}\
                    if not g.userobj.sysadmin \
                    else {_(u'Sysadmin Password'): _(u'incorrect password')}
                return self.get(id, data_dict, errors, error_summary)

        try:
            user = logic.get_action(u'user_update')(context, data_dict)
            if data_dict['password1'] and not g.userobj.sysadmin:
                updated = datetime.now()
                sysadmins = _get_sysadmin()
                subject = 'User Updated Password'
                extra_vars = {
                    'datetime': updated,
                    'username': g.userobj.name,
                    'site_title': config.get('ckan.site_title'),
                    'site_url': config.get('ckan.site_url'),
                }
                body = base.render('emails/user_update_password_message.txt', extra_vars)
                body_admin = base.render('emails/admin_update_password_message.txt', extra_vars)
                mailer.mail_user(g.userobj, subject, body)
                for am in sysadmins:
                    mailer.mail_user(am, subject, body_admin)
                
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit user %s') % id)
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, data_dict, errors, error_summary)

        h.flash_success(_(u'Profile updated'))
        resp = h.redirect_to(u'user.read', id=user[u'name'])
        if current_user and data_dict[u'name'] != old_username:
            # Changing currently logged in user's name.
            # Update repoze.who cookie to match
            set_repoze_user(data_dict[u'name'], resp)
        return resp

    def get(self, id=None, data=None, errors=None, error_summary=None):
        context, id = self._prepare(id)
        data_dict = {u'id': id}
        try:
            old_data = logic.get_action(u'user_show')(context, data_dict)

            g.display_name = old_data.get(u'display_name')
            g.user_name = old_data.get(u'name')

            data = data or old_data

        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit user %s') % u'')
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        user_obj = context.get(u'user_obj')

        errors = errors or {}
        vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary
        }

        extra_vars = _extra_template_variables({
            u'model': model,
            u'session': model.Session,
            u'user': g.user
        }, data_dict)

        extra_vars[u'show_email_notifications'] = asbool(
            config.get(u'ckan.activity_streams_email_notifications'))
        vars.update(extra_vars)
        extra_vars[u'form'] = base.render(edit_user_form, extra_vars=vars)

        return base.render(u'user/edit.html', extra_vars)
    
_edit_view = EditView.as_view(str(u'edit'))
ext_route.add_url_rule('/user/edit', view_func=_edit_view)
ext_route.add_url_rule('/user/edit/<id>', view_func=_edit_view)