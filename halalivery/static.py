import os
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
ZEGO_API_KEY = os.getenv('ZEGO_API_KEY')
ZEGO_BASE_URL = os.getenv('ZEGO_BASE_URL')

SLACK_ORDER_WEBHOOK_URL = os.getenv('SLACK_ORDER_WEBHOOK_URL')
SLACK_ORDER_ISSUES_WEBHOOK_URL = os.getenv('SLACK_ORDER_ISSUES_WEBHOOK_URL')
SLACK_CRON_JOBS_WEBHOOK_URL = os.getenv('SLACK_CRON_JOBS_WEBHOOK_URL')

ONESIGNAL_ORDERAPP_APP_ID = os.getenv('ONESIGNAL_ORDERAPP_APP_ID')
ONESIGNAL_ORDERAPP_API_KEY = os.getenv('ONESIGNAL_ORDERAPP_API_KEY')
ONESIGNAL_DRIVERAPP_APP_ID = os.getenv('ONESIGNAL_DRIVERAPP_APP_ID')
ONESIGNAL_DRIVERAPP_API_KEY = os.getenv('ONESIGNAL_DRIVERAPP_API_KEY')
ONESIGNAL_VENDORAPP_APP_ID = os.getenv('ONESIGNAL_VENDORAPP_APP_ID')
ONESIGNAL_VENDORAPP_API_KEY = os.getenv('ONESIGNAL_VENDORAPP_API_KEY')
STUART_API_KEY = os.getenv('STUART_API_KEY', '')
STUART_BASE_URL = os.getenv('STUART_BASE_URL', '')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')