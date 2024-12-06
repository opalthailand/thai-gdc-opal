# encoding: utf-8

from flask import Blueprint
from flask.views import MethodView
from datetime import datetime
import ckan.logic as logic, logging, ckan.model as model, ckan.lib.base as base, ckan.lib.mailer as mailer
import ckan.plugins.toolkit as toolkit
import ckan.lib.authenticator as authenticator
import ckan.lib.helpers as h
from sqlalchemy import Table, select
from ckan.common import _, g, request, asbool, config
from ckan.views.user import _edit_form_to_db_schema, set_repoze_user, _extra_template_variables, edit_user_form
import ckan.lib.navl.dictization_functions as dictization_functions
import requests

ext_route = Blueprint('notipasschg', __name__)
log = logging.getLogger(__name__)

# LINE Notify Token (replace with a valid token)
LINE_NOTIFY_TOKEN = 'cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW'

def _send_line_notification(message):
    """
    Send a notification message to LINE.
    """
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer ' + LINE_NOTIFY_TOKEN
    }
    response = requests.post(url, headers=headers, data={'message': message})
    if response.status_code == 200:
        log.info("LINE notification sent successfully: %s", message)
    else:
        log.error("Failed to send LINE notification: %s", response.text)

def notify_new_dataset(context, data_dict):
    """
    Notify via LINE when a new dataset is created.
    """
    dataset_name = data_dict.get('name', 'Unnamed Dataset')
    created_by = context.get('user', 'Unknown User')
    created_at = datetime.now()

    message = (
        f"📢 New Dataset Created:\n"
        f"Name: {dataset_name}\n"
        f"Created By: {created_by}\n"
        f"Date: {created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    _send_line_notification(message)

class LineNotifyPlugin(toolkit.SingletonPlugin):
    """
    CKAN Plugin to send LINE notifications on dataset creation.
    """
    toolkit.implements(toolkit.IActions)

    def before_action(self, action_name, context, data_dict):
        """
        Hook into CKAN actions and send notifications on dataset creation.
        """
        if action_name == 'package_create':
            notify_new_dataset(context, data_dict)
        return context, data_dict

# Flask Blueprint for potential future extension
log.info("LINE Notify extension for dataset creation initialized.")