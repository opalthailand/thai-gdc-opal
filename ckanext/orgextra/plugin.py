# encoding: utf-8

import logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests

log = logging.getLogger(__name__)


class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IActions)

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

    def get_actions(self):
        return {
            'send_line_notification': action_send_line_notification
        }


class OrgextraController(toolkit.BaseController):
    def send_notification(self):
        try:
            toolkit.get_action('send_line_notification')({}, {})  # Example call
            return toolkit.response("Notification sent successfully!") # Return success if no exception
        except toolkit.ValidationError as e:  # Catch validation errors
            log.error("Error sending notification: %s", e)
            return toolkit.response("An error occurred while sending the notification: %s" % e, 500)
        except Exception as e: # Catch other exceptions
            log.error("Error sending notification: %s", e)
            return toolkit.response("An error occurred while sending the notification.", 500)



def action_send_line_notification(context, data_dict):
    try:
        api_url = "https://notify-api.line.me/api/notify"
        token = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"
        if not token:
            raise toolkit.ValidationError("LINE token not configured.")

        headers = {"Authorization": "Bearer {}".format(token)}
        message = data_dict.get('message', "Default notification message")
        data = {"message": message}

        response = requests.post(api_url, headers=headers, data=data)

        # Python 2.7 compatible error checking:
        if response.status_code != 200:
            raise toolkit.ValidationError("Failed to send notification: %s" % response.text)

        return {'success': True}

    except requests.exceptions.RequestException as e:
        log.error("Error sending LINE notification: %s", e)
        raise toolkit.ValidationError("Failed to send notification: {}".format(e))
    except Exception as e:
        log.error("Error in send_line_notification action: %s", e)
        raise