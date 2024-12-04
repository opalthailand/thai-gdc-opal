import ckan.plugins as p
import ckan.plugins.toolkit as tk
import requests

class CDPPlugin(p.SingletonPlugin):
    p.implements(p.IResourceController, inherit=True)

    def before_create(self, context, resource):
        # Check if the user wants to push data to CDP
        push_to_cdp = tk.request.params.get('push_to_cdp', 'false')  # Get parameter, default to 'false'
        if push_to_cdp.lower() == 'true': # Check if the parameter is set to 'true'
            resource['push_to_cdp'] = True # Store the choice in the resource dict
        else:
            resource['push_to_cdp'] = False

    def after_create(self, context, resource):
        if resource.get('push_to_cdp', False): # Check the stored choice
            try:
                response = requests.get('https://www.google.com') # Use https
                response.raise_for_status()  # Raise an exception for bad status codes
                print("Successfully pushed data to CDP (simulated with Google request)")
            except requests.exceptions.RequestException as e:
                print(f"Error pushing data to CDP: {e}") # Provide more informative error message