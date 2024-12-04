import ckan.plugins as plugins
import logging
import requests

log = logging.getLogger(__name__)
tk = plugins.toolkit


def push_to_cdp(context, data_dict):
    resource_id = data_dict.get('id')
    push_to_cdp = data_dict.get('push_to_cdp', 'no')

    if push_to_cdp.lower() == 'yes':
        try:
            requests.get('https://httpbin.org/get')  # Replace with your CDP API endpoint and data
            log.info(f"Successfully pushed resource {resource_id} to CDP.")
            return {'success': True}
        except requests.exceptions.RequestException as e:
            log.error(f"Error pushing resource {resource_id} to CDP: {e}")
            return {'success': False, 'error': str(e)}

    return {'success': True}