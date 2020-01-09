# import os

# from celery import Celery
# from django.conf import settings


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "halalivery.config")

# app = Celery('halalivery')

# app.config_from_object('django.conf:settings', namespace='CELERY')

# CELERY_TIMEZONE = 'UTC'

# print(settings.INSTALLED_APPS)

# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'halalivery.config')
os.environ.setdefault("DJANGO_CONFIGURATION", "Local")


from configurations import importer
importer.install()

app = Celery('halalivery')

app.config_from_object('django.conf.settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
