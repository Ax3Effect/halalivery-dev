from halalivery.drivers.serializers import DriverSerializer
from halalivery.marketplaces import signals
from django.utils import timezone
from datetime import datetime, timedelta, time
from halalivery.drivers.models import DriverAvailability



def is_halalivery_delivery_available():
    now = timezone.localtime(timezone.now())
    now_time = now.time()
    availability = DriverAvailability.objects.all().last()
    available_from = time(10, 00, 00)
    available_until = time(23, 00, 00)
    if availability:
        available_from = availability.available_from#time(10, 00, 00)
        available_until = availability.available_to#time(23, 00, 00)
    return available_from < now_time < available_until