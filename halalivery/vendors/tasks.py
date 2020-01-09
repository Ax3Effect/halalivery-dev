from celery import shared_task

from halalivery.drivers.serializers import DriverSerializer
from halalivery.helpers import get_distance
from halalivery.marketplaces import signals
from halalivery.marketplaces.models import Order
from halalivery.drivers.models import DriverAvailability, DriverOrderVisibility
from halalivery.drivers import TransportType
from halalivery.users.models import Driver

from datetime import datetime, timedelta, time


@shared_task
def send_push_notifications_available_drivers_task(order_id):
    order = Order.objects.get(id=order_id)
    # drivers = Driver.objects.exclude(order__status__gte=6).filter(
    #     online=True, order__isnull=True)  # , address__city="Nottingham")
    drivers = Driver.objects.filter(online=True)

    driver_order_visibility = DriverOrderVisibility.objects.all().last()
    
    if drivers.exists():
        for driver in drivers:
            
            #driver_serialize = DriverSerializer(driver, many=False).data
            driver_location = driver.get_last_location()
            
            if driver_location:
                distance = get_distance(lon1=driver_location.longitude, lat1=driver_location.latitude, \
                lon2=order.vendor.address.longitude, lat2=order.vendor.address.latitude)
                if (driver.transport_type == TransportType.BICYCLE and distance <= driver_order_visibility.bicycle_radius) \
                    or (driver.transport_type == TransportType.MOTORBIKE and distance <= driver_order_visibility.motorcycle_radius) \
                    or (driver.transport_type == TransportType.CAR and distance <= driver_order_visibility.car_radius):
                    driverOrders = Order.objects.filter(driver=driver).exclude(status__gt=5).count()
                    if driverOrders == 0:
                        #print('Driver {} Distance {}'.format(driver.id,distance))
                        signals.order_available.send(sender=None, order=order, driver=driver)

                # if driver.transport_type <= TransportType.MOTORBIKE and distance <= driver_order_visibility.:
                #     signals.order_available.send(sender=None, order=order, driver=driver)
                # elif driver.transport_type == 2 and distance <= 2.5:
                #     signals.order_available.send(sender=None, order=order, driver=driver)
