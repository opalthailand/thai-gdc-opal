import ckan.plugins as p
import ckan.plugins.toolkit as tk
import requests
class CDPPlugin(p.SingletonPlugin):
    p.implements(p.IResourceController, inherit=True)
    def before_create(self, context, resource):
        push_to_cdp = tk.request.params.get('push_to_cdp', 'false')
        if push_to_cdp.lower() == 'true':
            resource['push_to_cdp'] = True
        else:
            resource['push_to_cdp'] = False
    def after_create(self, context, resource):
        if resource.get('push_to_cdp', False):
            try:
                response = requests.get('https://www.google.com')
                response.raise_for_status()
                print("Successfully pushed data to CDP (simulated with Google request)")
            except requests.exceptions.RequestException as e:
                print(f"Error pushing data to CDP: {e}")