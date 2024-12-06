import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.notipasschg import blueprint
import requests


class NotipasschgPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAction)

    # IConfigurer
    def update_config(self, config_):
        # Add template and public directories for the plugin
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'notipasschg')

    # IBlueprint
    def get_blueprint(self):
        # Return the blueprint that handles routes like /user/edit
        return blueprint.ext_route

    # IAction - This is where you hook into CKAN's dataset creation logic
    def after_create(self, context, data_dict):
        # When a dataset is created, send a LINE notification
        self._notify_new_dataset(context, data_dict)

    def _notify_new_dataset(self, context, data_dict):
        """
        Send a LINE notification when a new dataset is created.
        """
        dataset_name = data_dict.get('name', 'Unnamed Dataset')
        created_by = context.get('user', 'Unknown User')

        # Prepare the message
        message = (
            "New Dataset Created:\n" +
            "Name: " + str(dataset_name) + "\n" +
            "Created By: " + str(created_by) + "\n"
        )
        self._send_line_notification(message)

    def _send_line_notification(self, message):
        """
        Send the message to LINE using LINE Notify.
        """
        LINE_NOTIFY_TOKEN = 'your-line-notify-token-here'  # Replace with your actual token
        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Bearer ' + LINE_NOTIFY_TOKEN
        }
        response = requests.post(url, headers=headers, data={'message': message})
        if response.status_code == 200:
            print("LINE notification sent successfully: " + str(message))
        else:
            print("Failed to send LINE notification: " + str(response.text))