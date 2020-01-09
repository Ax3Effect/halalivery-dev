from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from django.http import HttpResponseForbidden
from rest_framework import status, viewsets
from rest_framework.decorators import action

from .serializers import DriverActiveOrderSerializer, DriverSerializer
from halalivery.order.models import Order
from halalivery.order import OrderStatus

from . import InsuranceType, TransportType
from halalivery.delivery import DeliveryProvider, DeliveryType

from decimal import Decimal

# Payments
from halalivery.payment.models import Transfer, Payment
from halalivery.payment import TransferParty
from halalivery.payment.utils import gateway_transfer

from halalivery.users.models import Driver
from halalivery.users.permissions import IsAuthenticatedDriver
from rest_framework.permissions import AllowAny

from halalivery.marketplaces import signals

from halalivery.drivers.models import DriverOrderVisibility, DriverLocation
from halalivery.drivers.gateways.stuart import StuartClient
from halalivery.delivery.models import DeliveryPartnerDriver, DeliveryPartnerJob

# Postgis
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance


import json
import requests
from halalivery.static import ZEGO_API_KEY, ZEGO_BASE_URL, STRIPE_API_KEY
import datetime
from django.utils import timezone
from pytz import UTC
import stripe
from halalivery.helpers import driver_order_total, vendor_order_total
import newrelic.agent
import sys
import math

from sentry_sdk import capture_exception

# No need to send notifications on preparatins, background worker does that
#from halalivery.vendors.tasks import send_push_notifications_available_drivers_task
#from halalivery.marketplaces.tasks import send_notification_to_drivers_around_task

# LIVE ORDER: Those that are not accepted by any drivers
@permission_classes((IsAuthenticatedDriver,))
class LiveOrdersView(APIView):
    def get(self, request):
        # TODO: live orders

        driver = get_object_or_404(Driver, user=request.user)

        driver_location = driver.get_last_location()
        if driver_location is None:
            return Response({'error': 'No live orders'}, status=status.HTTP_404_NOT_FOUND)

        # driver_location = driver.last_location #LocationSerializer(driver.last_location).data
        lon = driver_location.longitude
        lat = driver_location.latitude

        driver_order_visibility = DriverOrderVisibility.objects.all().last()

        # send_push_notifications_available_drivers(order_id=9)
        # send_notification_to_drivers_around_task()
        # lat = driver_lat
        # lon = driver_long

        # R = 6378.1  # earth radius
        # distance = 5  # distance in km
        # if driver.transport_type <= TransportType.MOTORBIKE:
        #     distance = 12
        #R = 3959
        radius = 2  # distance in km
        if driver.transport_type != TransportType.BICYCLE:
            radius = 8

        if driver_order_visibility:
            if driver.transport_type == TransportType.BICYCLE:
                radius = driver_order_visibility.bicycle_radius
            elif driver.transport_type == TransportType.MOTORBIKE:
                radius = driver_order_visibility.motorcycle_radius
            elif driver.transport_type == TransportType.CAR:
                radius = driver_order_visibility.car_radius

        driver_point = Point((lon, lat))

        # distance = float(distance + 12)
        # print(distance + 3)
        # lat1 = lat - math.degrees(distance / R)
        # lat2 = lat + math.degrees(distance / R)
        # long1 = lon - math.degrees(distance / R / math.cos(math.degrees(lat)))
        # long2 = lon + math.degrees(distance / R / math.cos(math.degrees(lat)))

        # live_orders = Order.halalivery_delivery.filter(status__range=[2, 3], driver=None) \
        #     .filter(vendor__address__latitude__gte=lat1, vendor__address__latitude__lte=lat2) \
        #     .filter(vendor__address__longitude__gte=long1, vendor__address__longitude__lte=long2)

        live_orders = Order.objects.internal_delivery().filter(status__in=[OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP], driver=None, delivery_by=DeliveryProvider.CELERY) \
            .filter(vendor__address__point__distance_lt=(driver_point, Distance(mi=radius))).order_by('-id')

        if not live_orders:
            return Response({'error': 'No live orders'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DriverActiveOrderSerializer(live_orders, many=True)
        return Response(serializer.data)

# ACTIVE ORDER: Those that are assigned to the driver
@permission_classes((IsAuthenticatedDriver,))
class ActiveOrdersView(APIView):
    def get(self, request):
        driver = get_object_or_404(Driver, user=request.user)

        active_orders = Order.objects.internal_delivery().filter(status__in=[
            OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP, OrderStatus.DRIVER_ARRIVED, OrderStatus.DRIVER_COLLECTED], driver=driver, delivery_by=DeliveryProvider.CELERY)

        if not active_orders:
            return Response({'error': 'No active orders'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DriverActiveOrderSerializer(active_orders)

        return Response(serializer.data)

@permission_classes((IsAuthenticatedDriver,))
class DriverProfileActionView(viewsets.ViewSet):

    @action(methods=['post'], detail=True)
    def online(self, request, pk=None):
        driver = get_object_or_404(Driver, user=request.user)
        online = request.data.get('online', None)
        if not isinstance(online, bool):
            return HttpResponseForbidden()

        # afrazik, add your zego code here
        driver.online = online
        driver.save()
        serializer = DriverSerializer(driver)
        return Response(serializer.data)

@permission_classes((IsAuthenticatedDriver,))
class DriverLocationView(APIView):
    def post(self, request):
        driver = get_object_or_404(Driver, user=request.user)

        try:
            json_data = json.loads(request.body)
            latitude = json_data['latitude']
            longitude = json_data['longitude']

            DriverLocation.objects.get_or_create(
                driver=driver, latitude=latitude, longitude=longitude, point=Point(longitude, latitude))
            serializer = DriverSerializer(driver)
            return Response(serializer.data)
        except Exception:
            return Response({'error': 'Error parsing the inputs.'},
                            status=status.HTTP_400_BAD_REQUEST)

@permission_classes((IsAuthenticatedDriver,))
class DriverActionView(viewsets.ViewSet):

    @action(methods=['post'], detail=True)
    def accept_order(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id, delivery_by=DeliveryProvider.CELERY,
                                  delivery_type=DeliveryType.DELIVERY)
        driver = get_object_or_404(Driver, user=request.user)

        if driver.online is False:
            return Response({'error': 'Driver must be online to accept the order'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if order.status < OrderStatus.PREPARING:
            return Response({"error": "Internal error 1142. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
        elif order.status > OrderStatus.READY_FOR_PICKUP:
            return Response({"error": "Order cannot be accepted."}, status=status.HTTP_400_BAD_REQUEST)

        # Do not check for zego for cyclists which is transport_type==2
        if driver.insurance_type == InsuranceType.ZEGO:
            # Zego implementation
            driver_id = driver.id  # driver.id '94900'
            response = requests.post(
                '{}v1/shift/login/'.format(ZEGO_BASE_URL),
                headers={'Authorization': ZEGO_API_KEY},
                data=json.dumps({
                    'driverId': driver_id,
                    'timestamp': timezone.localtime(timezone.now()).isoformat()
                })
            )

            zego_json = response.json()
            if response.status_code != 202 or zego_json["status"] != "PENDING":
                return Response({'error': 'There is an issue with your Zego insurance. Please contact us at support@halalivery.co.uk for further details. Please include your driver id: {}'.format(driver.id)}, status=status.HTTP_406_NOT_ACCEPTABLE)

        picked_up_orders = Order.objects.filter(driver=driver, status__range=[2, 3]).exists()
        if picked_up_orders:
            return Response({'error': 'You can only pick one order at a time'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not order.driver:
            order.driver = driver
            order.save()
            signals.driver_accepted.send(sender=None, order=order, driver=driver)
        else:
            return Response({'error': 'This order has already been picked up'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DriverActiveOrderSerializer(order)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def reject_order(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id, delivery_by=DeliveryProvider.CELERY,
                                  delivery_type=DeliveryType.DELIVERY)
        driver = get_object_or_404(Driver, user=request.user)

        if order.driver != driver:
            return HttpResponseForbidden()

        order.driver = None
        order.save()

        signals.driver_rejected.send(sender=None, order=order)
        serializer = DriverActiveOrderSerializer(order)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def arrived(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id, delivery_by=DeliveryProvider.CELERY,
                                  delivery_type=DeliveryType.DELIVERY)
        driver = get_object_or_404(Driver, user=request.user)

        if order.driver != driver or order.driver is None:
            return HttpResponseForbidden()

        if order.status != OrderStatus.READY_FOR_PICKUP:
            return Response({"error": "The order is not ready yet. Please wait."}, status=status.HTTP_400_BAD_REQUEST)
        if order.status == OrderStatus.DRIVER_ARRIVED:
            return Response({"error": "Driver has arrived already"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = OrderStatus.DRIVER_ARRIVED
        order.save()

        serializer = DriverActiveOrderSerializer(order)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def collected(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id, delivery_by=DeliveryProvider.CELERY,
                                  delivery_type=DeliveryType.DELIVERY)
        driver = get_object_or_404(Driver, user=request.user)

        if order.driver != driver or order.driver is None:
            return HttpResponseForbidden()

        if order.status != OrderStatus.DRIVER_ARRIVED:
            return Response({"error": "Internal error 1140. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
        elif order.status == OrderStatus.DRIVER_COLLECTED:
            return Response({"error": "Order has been collected already"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = OrderStatus.DRIVER_COLLECTED
        order.save()
        signals.driver_collected.send(sender=None, order=order)
        serializer = DriverActiveOrderSerializer(order)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def delivered(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id, delivery_by=DeliveryProvider.CELERY,
                                  delivery_type=DeliveryType.DELIVERY)
        driver = get_object_or_404(Driver, user=request.user)

        if order.driver != driver or order.driver is None:
            return HttpResponseForbidden()

        if order.status != OrderStatus.DRIVER_COLLECTED:
            return Response({"error": "Internal error 1139. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
        elif order.status == OrderStatus.DRIVER_DELIVERED:
            return Response({"error": "Order has been delivered."}, status=status.HTTP_400_BAD_REQUEST)

        # Do not check for zego for cyclists which is transport_type==2
        if driver.insurance_type == 'zego':
            # Zego implementation
            driver_id = driver.id  # driver.id '94900'
            response = requests.post(
                '{}v1/shift/logout/'.format(ZEGO_BASE_URL),
                headers={'Authorization': ZEGO_API_KEY},
                data=json.dumps({
                    'driverId': driver_id,
                    'timestamp': timezone.localtime(timezone.now()).isoformat()
                })
            )
            zego_json = response.json()
            if response.status_code != 202 or zego_json["status"] != "PENDING":
                return Response({'error': 'There is an issue with your Zego insurance. Please contact us at support@halalivery.co.uk for further details. Please include your driver id: {}'.format(driver.id)}, status=status.HTTP_406_NOT_ACCEPTABLE)
        # vendor_total = vendor_order_total(order=order)
        driver_total = driver_order_total(order=order)

        payment = order.get_last_payment()
        # last_transaction = last_payment.get_last_transaction()
        # last_transfer = last_payment.get_last_transfer()

        #total_sum = vendor_total + driver_total

        try:
            #last_payment.transfer(amount=driver_total, destination=driver.stripe_connect_id, transfer_party=TransferParty.DRIVER)
            gateway_transfer(payment=payment, amount=driver_total)
        except Exception as e:
            capture_exception(e)
            exc_info = sys.exc_info()
            newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
            return Response({'error': 'Internal error 1237. Please contact our support at support@halalivery.co.uk.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = OrderStatus.DRIVER_DELIVERED
        order.save()

        # Send slack notification upon driver delivery
        signals.order_delivered.send(sender=None, order=order)

        serializer = DriverActiveOrderSerializer(order)
        return Response(serializer.data)

@permission_classes((AllowAny,))
class StuartTest(APIView):
    def get(self, request):
        response = StuartClient().job_pricing()
        return Response({'ok': response})


@permission_classes([AllowAny, ])
class StuartWebhook(APIView):
    def post(self, request):
        try:
            json_data = json.loads(request.body)
            event = json_data.get('event')
            event_type = json_data.get('type')

            if event == 'job' and event_type == 'create':
                data = json_data.get('data')
                job_reference = data.get('jobReference')
                order_id = ''.join([n for n in job_reference if n.isdigit()])
                order = get_object_or_404(Order, id=order_id)
                job = DeliveryPartnerJob(
                    order=order,
                    job_id=data.get('id'),
                    status=data.get('status'),
                    comment=data.get('comment'),
                    pickup_at=data.get('pickupAt'),
                    dropoff_at=data.get('dropoffAt'),
                    created_at=data.get('createdAt'),
                    ended_at=data.get('endedAt'),
                    origin_comment=data.get('originComment'),
                    destination_comment=data.get('destinationComment'),
                    job_reference=data.get('jobReference'),
                    current_delivery=data.get('currentDelivery'),
                    transport_type=data.get('transportType'),
                    packageType=data.get('packageType'),
                )
                job.save()

            elif event == 'job' and event_type == 'update':
                data = json_data.get('data')
                job, _ = DeliveryPartnerJob.objects.update_or_create(
                    job_id=data.get('id'),
                    defaults={
                        'status': data.get('status'),
                        'comment': data.get('comment'),
                        'pickup_at': data.get('pickupAt'),
                        'dropoff_at': data.get('dropoffAt'),
                        'created_at': data.get('createdAt'),
                        'ended_at': data.get('endedAt'),
                        'origin_comment': data.get('originComment'),
                        'destination_comment': data.get('destinationComment'),
                        'job_reference': data.get('jobReference'),
                        'current_delivery': data.get('currentDelivery'),
                        'transport_type': data.get('transportType'),
                        'packageType': data.get('packageType'),
                    }
                )

            elif event == 'delivery' and event_type == 'create':
                # print(json_data)
                pass

            elif event == 'delivery' and event_type == 'update':
                data = json_data.get('data')
                if data.get('status') == 'picking':
                    client_reference = data.get('clientReference')
                    order_id = ''.join([n for n in client_reference if n.isdigit()])
                    order = get_object_or_404(Order, id=order_id)
                    if order.status < OrderStatus.DRIVER_ARRIVED:
                        order.status = OrderStatus.DRIVER_ARRIVED
                        order.save()
                        signals.driver_accepted.send(sender=None, order=order, driver=None)

                elif data.get('status') == 'delivering':
                    client_reference = data.get('clientReference')
                    order_id = ''.join([n for n in client_reference if n.isdigit()])
                    order = get_object_or_404(Order, id=order_id)
                    if order.status < OrderStatus.DRIVER_COLLECTED:
                        order.status = OrderStatus.DRIVER_COLLECTED
                        order.save()
                        signals.driver_collected.send(sender=None, order=order)
                elif data.get('status') == 'delivered':
                    client_reference = data.get('clientReference')
                    order_id = ''.join([n for n in client_reference if n.isdigit()])
                    order = get_object_or_404(Order, id=order_id)

                    order.status = OrderStatus.DRIVER_DELIVERED
                    order.save()

                    # Send slack notification upon driver delivery
                    signals.order_delivered.send(sender=None, order=order)

            elif event == 'driver' and event_type == 'update':
                job_id = json_data.get('data').get('job').get('id')
                driver_object = json_data.get('data')
                job = get_object_or_404(DeliveryPartnerJob, job_id=job_id)
                delivery_driver, _ = DeliveryPartnerDriver.objects.update_or_create(
                    job=job,
                    defaults={
                        'status': driver_object.get('status'),
                        'latitude': driver_object.get('latitude'),
                        'longitude': driver_object.get('longitude'),
                        'name': driver_object.get('name'),
                        'firstname': driver_object.get('firstname'),
                        'lastname': driver_object.get('lastname'),
                        'phone': driver_object.get('phone'),
                        'picture_path_imgix': driver_object.get('picture_path_imgix'),
                        'transport_type': driver_object.get('transportType').get('code'),
                        'point': Point((driver_object.get('longitude')), (driver_object.get('latitude')))
                    }
                )
        except Exception as e:
            return Response({'error': 'Internal error: 2000. Something went wrong.{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"ok": 'ok'})
