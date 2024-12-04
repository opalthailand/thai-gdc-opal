import logging
import requests
import ckan.plugins as plugins
import ckan.plugins.interfaces as interfaces
log = logging.getLogger(__name__)

class LINENotifyPlugin(plugins.SingletonPlugin):
    plugins.implements(interfaces.IConfigurable)
    plugins.implements(interfaces.IDomainObjectModification)
    token = None
    def _is_active(self):
        return self.token is not None
    def _linenotify(self, name, url):
        notify_url = 'https://notify-api.line.me/api/notify'
        headers = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+ self.token}
        message = self.message_template % {'name': name, 'url': url}
        r = requests.post(notify_url, headers=headers, data = {'message':message})
        log.debug(f"Line Notify response: {r.text}")

    def configure(self, config):
        log.debug("config type %s" % type(config))
        self.token = config.get('linenotify.token', None)
        if not self._is_active():
            log.debug("Configuration is not enough, Notification plugin is deactivated")
        self.target_format = config.get('linenotify.target_format', "").split()
        self.message_template = config.get('linenotify.message_template', "New file comes. %(name)s\nPlease check details in %(url)s")

    def notify(self, entity, operation):
        log.debug("entity %s" % entity)
        log.debug("operation %s" % operation)
        if 'new' == operation and self._is_active() and hasattr(entity, 'format'):
            fmt = entity.format
            if fmt in self.target_format or not self.target_format:
                self._linenotify(entity.name, entity.url)