import ckan.plugins as plugins
import ckan.logic as logic
import requests
from datetime import datetime

# LINE Notify Token (replace with your actual token)
LINE_NOTIFY_TOKEN = 'cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW'

# Function to send LINE notification
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
        print("LINE notification sent successfully: " + str(message))
    else:
        print("Failed to send LINE notification: " + str(response.text))

# Function to send the LINE notification when a new dataset is created
def _notify_new_dataset(context, data_dict):
    """
    Send a LINE notification when a new dataset is created.
    """
    dataset_name = data_dict.get('name', 'Unnamed Dataset')
    created_by = context.get('user', 'Unknown User')
    created_at = datetime.now()

    # Prepare the message
    message = (
        "New Dataset Created:\n" +
        "Name: " + str(dataset_name) + "\n" +
        "Created By: " + str(created_by)
    )
    _send_line_notification(message)

# Define the CKAN plugin to hook into dataset creation
class NotifyDatasetCreationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAction)

    def after_create(self, context, data_dict):
        # Call the function to send LINE notification after dataset is created
        _notify_new_dataset(context, data_dict)

# Register the plugin in CKAN
def get_plugin_classes():
    return [NotifyDatasetCreationPlugin]