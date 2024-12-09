# encoding: utf-8

import logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests

log = logging.getLogger(__name__)


class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IActions) # Implement IActions

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def before_map(self, map):
        map.connect(
            'send_notification',
            '/send_notification',
            controller='ckanext.orgextra.plugin:OrgextraController',
            action='send_notification',
        )
        return map

    def get_actions(self):  # Define get_actions
        return {
            'send_line_notification': action_send_line_notification
        }


class OrgextraController(toolkit.BaseController):
    def send_notification(self):
        try:
            # You can call the action function here if needed:
            # toolkit.get_action('send_line_notification')({}, {})
            # ... or handle the notification directly as before ...
            api_url = "https://notify-api.line.me/api/notify"
            token = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"
            headers = {"Authorization": "Bearer {}".format(token)}
            data = {"message": "User logged in!"}

            response = requests.post(api_url, headers=headers, data=data)
            if response.status_code == 200:
                return toolkit.response("Notification sent successfully!")
            else:
                return toolkit.response(
                    "Failed to send notification: {}".format(response.text), 500
                )
        except Exception as e:
            log.error("Error sending notification: %s", e)
            return toolkit.response("An error occurred while sending the notification.", 500)


def action_send_line_notification(context, data_dict):
    """
    Action function to send LINE notification.  This can be called via the
    Action API.
    """
    try:
        api_url = "https://notify-api.line.me/api/notify"
        token = toolkit.config.get('ckanext.orgextra.line_token') # Get token from config
        if not token:
            raise toolkit.ValidationError("LINE token not configured.")

        headers = {"Authorization": "Bearer {}".format(token)}
        message = data_dict.get('message', "Default notification message") # Allow custom message
        data = {"message": message}

        response = requests.post(api_url, headers=headers, data=data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return {'success': True}

    except requests.exceptions.RequestException as e:
        log.error("Error sending LINE notification: %s", e)
        raise toolkit.ValidationError("Failed to send notification: {}".format(e))
    except Exception as e:
        log.error("Error in send_line_notification action: %s", e)
        raise