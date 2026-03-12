import time
import requests

from odoo import api, fields, models

class NotificationClient(models.Model):
    _name = "notification.client"
    _description = "Notification Client"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def get_notification_interval(self):
        url = '/partner-licence/get_interval'
        try:
            response = requests.post(url, json={})
            if response.status_code == 200:
                data = response.json()
                return data.get('interval', 60)
        except Exception as e:
            return 60

    def start_notification_loop(self):
        while True:
            interval = self.get_notification_interval()
            time.sleep(interval * 60)
            self.show_notification()

    def show_notification(self):
        self.env.user.notify_warning('Licenta ta a expirat! Te rugam sa o reinnoiest.')

