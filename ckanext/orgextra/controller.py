# encoding: utf-8


import logging
import ckan.plugins.toolkit as toolkit
import requests

log = logging.getLogger(__name__)


class NotificationController(toolkit.BaseController):
    def send_notification(self):
        # Example: Logic to send LINE notification
        try:
            api_url = "https://notify-api.line.me/api/notify"
            token = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"  # Replace with your token
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
            log.error("Error sending notification: {}".format(e))
            return toolkit.response("An error occurred.", 500)