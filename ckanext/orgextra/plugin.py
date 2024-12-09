# encoding: utf-8

import logging
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests

log = logging.getLogger(__name__)


class OrgextraPlugin(plugins.SingletonPlugin):
    # Declare that this plugin implements IConfigurer and IRoutes
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)

    def update_config(self, config):
        """Adds the template and public directories to CKAN's config."""
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def before_map(self, map):
        """Add custom routes."""
        map.connect(
            'send_notification',
            '/send_notification',
            controller='ckanext.orgextra.plugin:OrgextraController',
            action='send_notification',
        )
        return map


class OrgextraController(toolkit.BaseController):
    def send_notification(self):
        """Handles the /send_notification route."""
        try:
            # Example logic to send LINE notification
            api_url = "https://notify-api.line.me/api/notify"
            token = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"  # Replace with your LINE token
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
