# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests

def send_line_notification(message):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization":"Bearer cw37fBYJd9VAS45mLDXEtKmSpdpduuEyRO2BFVN2TrW"}
    data = {"message": message}
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()

class OrgextraPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthenticator)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')

    def login(self):
        send_line_notification("TTEESSTT")