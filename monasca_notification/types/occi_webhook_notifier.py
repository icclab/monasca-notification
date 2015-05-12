import requests

from keystoneclient.v2_0 import client
from abstract_notifier import AbstractNotifier


class OCCIWebhookNotifier(AbstractNotifier):
    def __init__(self, log):
        self._log = log

    def config(self, config_dict):
        self._config = {'timeout': 5}
        self._config.update(config_dict)

    @property
    def type(self):
        return "occi_webhook"

    @property
    def statsd_name(self):
        return 'sent_occi_webhook_count'

    def send_notification(self, notification):
        """Send the notification via webhook
            Posts on the given url using OCCI formatting
        """
        self._log.info("Notifying alarm {} to {} with action {}"
                       .format(notification.alarm_name,
                               notification.state,
                               notification.address))


        # static user_name has to be part of the tenant from which the notification was created
        tenant_id = notification.tenant_id
        user_name = self._config['user_name']
        password = self._config['password']
        auth_url = self._config['auth_url']

        ksclient = client.Client(username=user_name, password=password, tenant_id=tenant_id, auth_url=auth_url)
        token = ksclient.auth_token
        tenant_name = ksclient.tenant_name

        self._log.info("Notifying OCCI alarm {} to {} with action {}"
                       .format(notification.alarm_name,
                               notification.state,
                               notification.address))

        # body = {'alarm_id': notification.alarm_id}
        url = notification.address

        params = {'action': 'notify'}
        headers = {
            'Category': 'notify; scheme="http://schemas.mobile-cloud-networking.eu/occi/service#"',
            'Content-Type': 'text/occi',
            'X-Auth-Token': token,
            'X-Tenant-Name': tenant_name,
            'X-OCCI-Attribute': 'notification.alarm_name=' + notification.name}

        try:
            # Posting on the given URL
            result = requests.post(url=url,
                                   headers=headers,
                                   params=params,
                                   timeout=self._config['timeout'])

            if result.status_code in range(200, 300):
                self._log.info("Notification successfully posted.")
                return True
            else:
                self._log.error("Received an HTTP code {} when trying to post on URL {}."
                                .format(result.status_code, url))
                return False
        except Exception:
            self._log.exception("Error trying to post on URL {}".format(url))
            return False


        pass