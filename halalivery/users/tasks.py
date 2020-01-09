from celery import shared_task

from .models import Location
import requests
import os
from halalivery.static import SLACK_CRON_JOBS_WEBHOOK_URL

@shared_task
def clear_drivers_locations():
        # requests.post(
        #     url=SLACK_CRON_JOBS_WEBHOOK_URL,
        #     json={
        #         "attachments": [
        #             {
        #                 "title": 'halalivery.clear_drivers_locations_task',
        #                 "pretext": "*Completed*",
        #                 "text": "Should send this every 5 mins.",
        #                 "mrkdwn_in": [
        #                     "text",
        #                     "pretext"
        #                 ]
        #             }
        #         ]
        #     }
        # )
        total_locations = Location.objects.count()
        requests.post(
            url=SLACK_CRON_JOBS_WEBHOOK_URL,
            json={
                "attachments": [
                    {
                        "title": 'halalivery.clear_drivers_locations_task',
                        "pretext": "*Started*",
                        "text": "Clearing drivers locations: *{0}*".format(total_locations),
                        "mrkdwn_in": [
                            "text",
                            "pretext"
                        ]
                    }
                ]
            }
        )
        Location.objects.all().delete()

        total_locations = Location.objects.count()
        requests.post(
            url=SLACK_CRON_JOBS_WEBHOOK_URL,
            json={
                "attachments": [
                    {
                        "title": 'halalivery.clear_drivers_locations_task',
                        "pretext": "*Completed*",
                        "text": "Driver locations after clearing: {0}".format(total_locations),
                        "mrkdwn_in": [
                            "text",
                            "pretext"
                        ]
                    }
                ]
            }
        )