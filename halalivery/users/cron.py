from django_cron import CronJobBase, Schedule
import logging
from .models import Location
import requests
import os
from halalivery.static import SLACK_CRON_JOBS_WEBHOOK_URL

class ClearDriverLocations(CronJobBase):
    #RUN_EVERY_MINS = 10080 # every 7 days
    RUN_EVERY_MINS = 5
    #RUN_AT_TIMES = ['23:59']

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'halalivery.clear_driver_locations'    # a unique code

    def do(self):
        # location_count = Location.objects.all().count()
        # Location.objects.all().delete()
        # locations_after_delete = Location.objects.all().count()
        # requests.post(
        #     url=SLACK_CRON_JOBS_WEBHOOK_URL,
        #     json={
        #         "attachments": [
        #             {
        #                 "title": self.code,
        #                 "pretext": "*Completed*",
        #                 "text": "Total locations deleted *{}*.\nLocations left: *{}*".format(location_count, locations_after_delete),
        #                 "mrkdwn_in": [
        #                     "text",
        #                     "pretext"
        #                 ]
        #             }
        #         ]
        #     }
        # )
        requests.post(
            url=SLACK_CRON_JOBS_WEBHOOK_URL,
            json={
                "attachments": [
                    {
                        "title": self.code,
                        "pretext": "*Completed*",
                        "text": "Should send this every 5 mins.",
                        "mrkdwn_in": [
                            "text",
                            "pretext"
                        ]
                    }
                ]
            }
        )
        pass    # do your thing here
