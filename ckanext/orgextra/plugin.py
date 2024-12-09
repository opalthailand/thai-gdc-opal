# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests

LINE_NOTIFY_TOKEN = "cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW" # Replace with your token

def send_line_notification(message):
    # url = "https://notify-api.line.me/api/notify"
    # headers = {"Authorization": "Bearer " + LINE_NOTIFY_TOKEN}
    # data = {"message": message}
    # try:
    #     response = requests.post(url, headers=headers, data=data)
    #     response.raise_for_status()
    # except requests.exceptions.RequestException as e:
    #     # Print the error for now.  Ideally, use a logger here.
    #     print("Error sending Line notification",e)
    print('yes')


class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthenticator)

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')

    def login(self, context, data, user):
        if user: # check if a user object exists before trying to use it
            send_line_notification("User")
        else:
            print("Login attempt with no user information.") #  Handle this case as needed.
        return (context, data, user)