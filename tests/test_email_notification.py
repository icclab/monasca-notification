# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import smtplib
import socket
import time
import unittest

from monasca_notification.notification import Notification
from monasca_notification.types import email_notifier


def alarm(metrics):
    return {"tenantId": "0",
            "alarmId": "0",
            "alarmName": "test Alarm",
            "oldState": "OK",
            "newState": "ALARM",
            "stateChangeReason": "I am alarming!",
            "timestamp": time.time(),
            "metrics": metrics}


class smtpStub(object):
    def __init__(self, trap):
        self.trap = trap

    def sendmail(self, from_addr, to_addr, msg):
        self.trap.append("%s %s %s" % (from_addr, to_addr, msg))


class smtpStubException(object):
    def __init__(self, queue):
        self.queue = queue

    def sendmail(self, from_addr, to_addr, msg):
        raise smtplib.SMTPServerDisconnected


class TestEmail(unittest.TestCase):
    def setUp(self):
        self.trap = []

        self.email_config = {'server': 'my.smtp.server',
                             'port': 25,
                             'user': None,
                             'password': None,
                             'timeout': 60,
                             'from_addr': 'hpcs.mon@hp.com'}

    def tearDown(self):
        pass

    def _smtpStub(self, *arg, **kwargs):
        return smtpStub(self.trap)

    def _smtbStubException(self, *arg, **kwargs):
        return smtpStubException(self.trap)

    @mock.patch('monasca_notification.types.email_notifier.smtplib')
    def notify(self, smtp_stub, metric, mock_smtp):
        mock_smtp.SMTP = smtp_stub

        mock_log = mock.MagicMock()
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append

        email = email_notifier.EmailNotifier(mock_log)

        email.config(self.email_config)

        alarm_dict = alarm(metric)

        notification = Notification('email', 0, 1, 'email notification', 'me@here.com', 0, alarm_dict)

        self.trap.append(email.send_notification(notification))

    def test_email_notification_single_host(self):
        """Email with single host
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)

        self.notify(self._smtpStub, metrics)

        email = self.trap.pop(0)

        self.assertRegexpMatches(email, "From: hpcs.mon@hp.com")
        self.assertRegexpMatches(email, "To: me@here.com")
        self.assertRegexpMatches(email, "Content-Type: text/plain")
        self.assertRegexpMatches(email, "Alarm .test Alarm.")
        self.assertRegexpMatches(email, "On host .foo1.")

        return_value = self.trap.pop(0)
        self.assertTrue(return_value)

    def test_email_notification_multiple_hosts(self):
        """Email with multiple hosts
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)
        metric_data = {'dimensions': {'hostname': 'foo2', 'service': 'bar2'}}
        metrics.append(metric_data)

        self.notify(self._smtpStub, metrics)

        email = self.trap.pop(0)

        self.assertRegexpMatches(email, "From: hpcs.mon@hp.com")
        self.assertRegexpMatches(email, "To: me@here.com")
        self.assertRegexpMatches(email, "Content-Type: text/plain")
        self.assertRegexpMatches(email, "Alarm .test Alarm.")
        self.assertNotRegexpMatches(email, "foo1")
        self.assertNotRegexpMatches(email, "foo2")

        return_value = self.trap.pop(0)
        self.assertTrue(return_value)

    @mock.patch('monasca_notification.types.email_notifier.smtplib')
    def test_smtp_sendmail_failed_connection_twice(self, mock_smtp):
        """Email that fails on smtp_connect twice
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)
        metric_data = {'dimensions': {'hostname': 'foo2', 'service': 'bar2'}}
        metrics.append(metric_data)

        mock_log = mock.MagicMock()
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.debug = self.trap.append
        mock_log.info = self.trap.append
        mock_log.exception = self.trap.append

        # mock_smtp.SMTP.return_value = mock_smtp
        mock_smtp.SMTP.side_effect = [mock_smtp,
                                      smtplib.SMTPServerDisconnected,
                                      socket.error]

        mock_smtp.sendmail.side_effect = [smtplib.SMTPServerDisconnected,
                                          smtplib.SMTPServerDisconnected]

        # There has to be a better way to preserve exception definitions when
        # we're mocking access to a library
        mock_smtp.SMTPServerDisconnected = smtplib.SMTPServerDisconnected
        mock_smtp.SMTPException = smtplib.SMTPException

        email = email_notifier.EmailNotifier(mock_log)

        email.config(self.email_config)

        alarm_dict = alarm(metrics)

        notification = Notification('email', 0, 1, 'email notification', 'me@here.com', 0, alarm_dict)

        self.trap.append(email.send_notification(notification))

        self.assertIn("SMTP server disconnected. Will reconnect and retry message.", self.trap)
        self.assertIn("Unable to connect to email server.", self.trap)

    @mock.patch('monasca_notification.types.email_notifier.smtplib')
    def test_smtp_sendmail_smtp_None(self, mock_smtp):
        """Email that fails on smtp_connect twice
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)
        metric_data = {'dimensions': {'hostname': 'foo2', 'service': 'bar2'}}
        metrics.append(metric_data)

        mock_log = mock.MagicMock()
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.debug = self.trap.append
        mock_log.info = self.trap.append
        mock_log.exception = self.trap.append

        mock_smtp.SMTP.return_value = None
        mock_smtp.SMTP.side_effect = [socket.error,
                                      socket.error,
                                      socket.error]

        mock_smtp.sendmail.side_effect = [smtplib.SMTPServerDisconnected,
                                          smtplib.SMTPServerDisconnected]

        # There has to be a better way to preserve exception definitions when
        # we're mocking access to a library
        mock_smtp.SMTPServerDisconnected = smtplib.SMTPServerDisconnected
        mock_smtp.SMTPException = smtplib.SMTPException

        email = email_notifier.EmailNotifier(mock_log)

        email.config(self.email_config)

        del self.trap[:]

        alarm_dict = alarm(metrics)

        notification = Notification('email', 0, 1, 'email notification', 'me@here.com', 0, alarm_dict)

        email_result = email.send_notification(notification)

        self.assertFalse(email_result)
        self.assertIn("Connecting to Email Server {}"
                      .format(self.email_config['server']),
                      self.trap)

    @mock.patch('monasca_notification.types.email_notifier.smtplib')
    def test_smtp_sendmail_failed_connection_once_then_email(self, mock_smtp):
        """Email that fails on smtp_connect once then email
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)
        metric_data = {'dimensions': {'hostname': 'foo2', 'service': 'bar2'}}
        metrics.append(metric_data)

        mock_log = mock.MagicMock()
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.debug = self.trap.append
        mock_log.info = self.trap.append
        mock_log.exception = self.trap.append

        mock_smtp.SMTP.return_value = mock_smtp

        mock_smtp.sendmail.side_effect = [smtplib.SMTPServerDisconnected,
                                          smtplib.SMTPException]

        # There has to be a better way to preserve exception definitions when
        # we're mocking access to a library
        mock_smtp.SMTPServerDisconnected = smtplib.SMTPServerDisconnected
        mock_smtp.SMTPException = smtplib.SMTPException

        email = email_notifier.EmailNotifier(mock_log)

        email.config(self.email_config)

        alarm_dict = alarm(metrics)

        notification = Notification('email', 0, 1, 'email notification', 'me@here.com', 0, alarm_dict)

        self.trap.append(email.send_notification(notification))

        self.assertIn("SMTP server disconnected. Will reconnect and retry message.", self.trap)
        self.assertIn("Error sending Email Notification", self.trap)
        self.assertNotIn("Unable to connect to email server.", self.trap)

    @mock.patch('monasca_notification.types.email_notifier.smtplib')
    def test_smtp_sendmail_failed_connection_once(self, mock_smtp):
        """Email that fails on smtp_connect once
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)
        metric_data = {'dimensions': {'hostname': 'foo2', 'service': 'bar2'}}
        metrics.append(metric_data)

        mock_log = mock.MagicMock()
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.debug = self.trap.append
        mock_log.info = self.trap.append
        mock_log.exception = self.trap.append

        mock_smtp.SMTP.return_value = mock_smtp
        mock_smtp.sendmail.side_effect = [smtplib.SMTPServerDisconnected, None]

        # There has to be a better way to preserve exception definitions when
        # we're mocking access to a library
        mock_smtp.SMTPServerDisconnected = smtplib.SMTPServerDisconnected
        mock_smtp.SMTPException = smtplib.SMTPException

        email = email_notifier.EmailNotifier(mock_log)

        email.config(self.email_config)

        alarm_dict = alarm(metrics)

        notification = Notification('email', 0, 1, 'email notification', 'me@here.com', 0, alarm_dict)

        self.trap.append(email.send_notification(notification))

        self.assertIn("SMTP server disconnected. Will reconnect and retry message.", self.trap)
        self.assertIn("Sent email to %s, notification %s"
                      % (notification.address, notification.to_json()), self.trap)

    @mock.patch('monasca_notification.types.email_notifier.smtplib')
    def test_smtp_sendmail_failed_exception(self, mock_smtp):
        """Email that fails on exception
        """

        metrics = []
        metric_data = {'dimensions': {'hostname': 'foo1', 'service': 'bar1'}}
        metrics.append(metric_data)
        metric_data = {'dimensions': {'hostname': 'foo2', 'service': 'bar2'}}
        metrics.append(metric_data)

        mock_log = mock.MagicMock()
        mock_log.warn = self.trap.append
        mock_log.error = self.trap.append
        mock_log.debug = self.trap.append
        mock_log.info = self.trap.append
        mock_log.exception = self.trap.append

        mock_smtp.SMTP.return_value = mock_smtp
        mock_smtp.sendmail.side_effect = smtplib.SMTPException

        # There has to be a better way to preserve exception definitions when
        # we're mocking access to a library
        mock_smtp.SMTPServerDisconnected = smtplib.SMTPServerDisconnected
        mock_smtp.SMTPException = smtplib.SMTPException

        email = email_notifier.EmailNotifier(mock_log)

        email.config(self.email_config)

        alarm_dict = alarm(metrics)

        notification = Notification('email', 0, 1, 'email notification', 'me@here.com', 0, alarm_dict)

        self.trap.append(email.send_notification(notification))

        self.assertNotIn("SMTP server disconnected. Will reconnect and retry message.", self.trap)
        self.assertIn("Error sending Email Notification", self.trap)
