# encoding: utf-8

from flask import Blueprint
from datetime import datetime
import ckan.plugins.toolkit as toolkit
import logging
import requests

log = logging.getLogger(__name__)
ext_route = Blueprint('notipasschg', __name__)  # Keeping the extension name as 'notipasschg'

# LINE Notify Token (replace with your valid token)
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
        log.info("LINE notification sent successfully: " + str(message))
    else:
        log.error("Failed to send LINE notification: " + str(response.text))

def _notify_new_dataset(context, data_dict):
    """
    Notify via LINE when a new dataset is created.
    """
    dataset_name = data_dict.get('name', 'Unnamed Dataset')
    created_by = context.get('user', 'Unknown User')
    created_at = datetime.now()

    message = (
        "New Dataset Created:\n" +
        "Name: " + str(dataset_name) + "\n" +
        "Created By: " + str(created_by) + "\n" +
        "Date: " + str(created_at.strftime('%Y-%m-%d %H:%M:%S'))
    )
    _send_line_notification(message)

class NotiPassChgPlugin(toolkit.SingletonPlugin):
    """
    CKAN Plugin to send LINE notifications on dataset creation.
    """
    toolkit.implements(toolkit.IActions)

    def before_action(self, action_name, context, data_dict):
        """
        Hook into CKAN actions and send notifications on dataset creation.
        """
        if action_name == 'package_create':  # Hook into the 'package_create' action
            _notify_new_dataset(context, data_dict)
        return context, data_dict

# Flask Blueprint (kept for potential future usage)
log.info("LINE Notify extension (notipasschg) for dataset creation initialized.")