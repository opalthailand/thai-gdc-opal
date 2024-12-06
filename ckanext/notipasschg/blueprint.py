# encoding: utf-8

from flask import Blueprint
from flask.views import MethodView
from datetime import datetime
import ckan.logic as logic, logging, ckan.model as model, ckan.lib.base as base, ckan.lib.mailer as mailer
import ckan.plugins.toolkit as toolkit
import ckan.lib.authenticator as authenticator
import ckan.lib.helpers as h
from sqlalchemy import Table
from ckan.common import _, g, request, asbool, config
from ckan.views.user import _edit_form_to_db_schema, set_repoze_user, _extra_template_variables, edit_user_form
import ckan.lib.navl.dictization_functions as dictization_functions
import requests  # Ensure requests is installed for HTTP calls

log = logging.getLogger(__name__)
ext_route = Blueprint('notipasschg', __name__)
_check_access = logic.check_access

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
            'save': 'save' in request.form,
            'schema': _edit_form_to_db_schema(),
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        if id is None:
            if g.userobj:
                id = g.userobj.id
            else:
                base.abort(400, _('No user specified'))
        data_dict = {'id': id}

        try:
            logic.check_access('user_update', context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to edit a user.'))
        return context, id

    def post(self, id=None):
        context, id = self._prepare(id)
        if not context['save']:
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
            base.abort(400, _('Integrity Error'))

        data_dict.setdefault('activity_streams_email_notifications', False)
        context['message'] = data_dict.get('log_message', '')
        data_dict['id'] = id
        email_changed = data_dict['email'] != g.userobj.email

        if (data_dict['password1'] and data_dict['password2']) or email_changed:
            identity = {'login': g.user, 'password': data_dict['old_password']}
            auth = authenticator.UsernamePasswordAuthenticator()

            if auth.authenticate(request.environ, identity) != g.user:
                errors = {'oldpassword': [_('Password entered was incorrect')]}
                error_summary = {
                    _('Old Password'): _('incorrect password')
                } if not g.userobj.sysadmin else {
                    _('Sysadmin Password'): _('incorrect password')
                }
                return self.get(id, data_dict, errors, error_summary)

        try:
            user = logic.get_action('user_update')(context, data_dict)

            if data_dict['password1'] and data_dict['password2'] and not g.userobj.sysadmin:
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

                # Notify via LINE Notify API
                self._send_line_notify(f"Password changed for user: {g.userobj.name}")

        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to edit user %s') % id)
        except logic.NotFound:
            base.abort(404, _('User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, data_dict, errors, error_summary)

        h.flash_success(_('Profile updated'))
        resp = h.redirect_to('user.read', id=user['name'])
        if current_user and data_dict['name'] != old_username:
            set_repoze_user(data_dict['name'], resp)
        return resp

    def get(self, id=None, data=None, errors=None, error_summary=None):
        context, id = self._prepare(id)
        data_dict = {'id': id}
        try:
            old_data = logic.get_action('user_show')(context, data_dict)

            g.display_name = old_data.get('display_name')
            g.user_name = old_data.get('name')

            data = data or old_data
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to edit user %s') % '')
        except logic.NotFound:
            base.abort(404, _('User not found'))

        errors = errors or {}
        vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary
        }

        extra_vars = _extra_template_variables({
            'model': model,
            'session': model.Session,
            'user': g.user
        }, data_dict)

        extra_vars['show_email_notifications'] = asbool(
            config.get('ckan.activity_streams_email_notifications'))
        vars.update(extra_vars)
        extra_vars['form'] = base.render(edit_user_form, extra_vars=vars)

        return base.render('user/edit.html', extra_vars)

    def _send_line_notify(self, message):
        """Helper function to send LINE Notify message."""
        url = 'https://notify-api.line.me/api/notify'
        token = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"  # Replace with your LINE Notify token
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Bearer ' + token,
        }
        try:
            response = requests.post(url, headers=headers, data={'message': message})
            if response.status_code != 200:
                log.error(
                    f"LINE Notify failed with status: {response.status_code}, response: {response.text}"
                )
        except Exception as e:
            log.error(f"Failed to send LINE Notify: {e}")

_edit_view = EditView.as_view('edit')
ext_route.add_url_rule('/user/edit', view_func=_edit_view)
ext_route.add_url_rule('/user/edit/<id>', view_func=_edit_view)