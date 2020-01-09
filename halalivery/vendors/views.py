from django.shortcuts import get_object_or_404
from decimal import Decimal
import newrelic.agent
import sys
import threading
import json

from django.db import transaction

from rest_framework.views import APIView
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from django.http import HttpResponseForbidden
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny


from halalivery.menu.models import MenuItem
from halalivery.payment.models import Transfer, Payment
from halalivery.payment import TransferParty, PaymentError
from halalivery.payment.utils import gateway_capture, gateway_transfer, gateway_refund, gateway_void
from halalivery.marketplaces.serializers import GrocerySerializer, RestaurantSerializer

from .serializers import *
from halalivery.drivers.serializers import DriverSerializer
from halalivery.drivers.models import DriverAvailability
from halalivery.delivery.models import DeliveryPartnerDriver, DeliveryPartnerJob

from halalivery.users.models import Vendor, Driver
from halalivery.marketplaces import signals
from halalivery.order import OrderStatus, OrderEvents
from halalivery.delivery import DeliveryType

from halalivery.users.permissions import IsAuthenticatedVendor


from halalivery.helpers import vendor_order_total
from .utils import is_halalivery_delivery_available

from sentry_sdk import capture_exception

# Stuart
from halalivery.drivers.gateways.stuart import StuartClient
#from .tasks import send_push_notifications_available_drivers

# Create your views here.


@permission_classes((IsAuthenticatedVendor,))
class VendorGetOrders(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()
        if marketplace:
            orders = Order.objects.filter(vendor=vendor, status__in=(
                OrderStatus.DRIVER_DELIVERED, OrderStatus.SELF_PICKED_UP, OrderStatus.CONFIRMED)).order_by('-created_at')

            serializer = VendorOrderSerializer(orders, many=True)
            return Response(serializer.data)
        else:
            return Response({'errors': 'Vendor is not associated with a marketplace'},
                            status=status.HTTP_404_NOT_FOUND)

@permission_classes((IsAuthenticatedVendor,))
class VendorGetOrdersHistory(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()
        if marketplace:
            orders = Order.objects.filter(vendor=vendor, status__in=[OrderStatus.DRIVER_DELIVERED, OrderStatus.SELF_PICKED_UP]).order_by('-created_at')
            
            serializer = VendorOrderSerializer(orders, many=True)
            return Response(serializer.data)
        else:
            return Response({'errors': 'Vendor is not associated with a marketplace'},
                            status=status.HTTP_404_NOT_FOUND)

@permission_classes((IsAuthenticatedVendor,))
class VendorOrderAction(viewsets.ViewSet):

    @action(methods=['post'], detail=True)
    def accept_order(self, request, pk=None):
        order_id = request.data.pop('order_id', None)
        delivery_by = request.data.pop('delivery_by', None)
        order = get_object_or_404(Order, id=order_id)
        vendor = get_object_or_404(Vendor, user=request.user)

        available_delivery_by = {DeliveryProvider.CELERY, DeliveryProvider.VENDOR}

        # If a requested order does not belong to the vendor that is requesting it.
        if order.vendor != vendor:
            return HttpResponseForbidden()

        if not order.is_pre_authorized():
            return Response({"error": "Internal error 1000. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)

        if order.status == OrderStatus.DRAFT:
            return Response({"error": "Internal error 1236. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
        elif order.status != OrderStatus.CONFIRMED:
            return Response({"error": "Order #{} has already been accepted.".format(order.id)}, status=status.HTTP_400_BAD_REQUEST)

        # Check if vendor can select Halalivery delivery

        # If we have a delivery selected, then notify drivers
        if order.delivery_type != DeliveryType.SELF_PICKUP:
            if delivery_by in available_delivery_by:
                if delivery_by == DeliveryProvider.CELERY:
                    driver_availability = DriverAvailability.objects.all().last()
                    halalivery_driver_available = driver_availability.is_available() if driver_availability else None
                    if not halalivery_driver_available:
                        return Response({'errors': 'Halalivery drivers are not available at this time. Halalivery drivers are available from {} to {} 7 days a week.'.format(driver_availability.available_from, driver_availability.available_to)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'errors': 'Please select the correct delivery type'}, status=status.HTTP_400_BAD_REQUEST)

        # Process the payment
        payment = order.get_last_payment()
        amount = payment.get_charge_amount()

        try:
            try:
                gateway_capture(payment, amount=amount)
            except PaymentError as e:
                capture_exception(e)
                return Response({'error': 'Could not process the payment for the Order #{}. Please contact our support.'.format(order.id)}, status=status.HTTP_400_BAD_REQUEST)

            order.events.create(
                parameters={'amount': amount},
                type=OrderEvents.PAYMENT_CAPTURED.value,
                user=request.user)

            # Send push notifications to available drivers only if its Celery delivery
            if delivery_by == DeliveryProvider.CELERY:
                order.delivery_by = DeliveryProvider.CELERY
                # send_push_notifications_available_drivers.delay(order_id=order.id)
                # Notify on slack about halalivery delivery selected
                signals.vendor_delivery_halalivery.send(sender=None, order=order, vendor=vendor)
            elif delivery_by == DeliveryProvider.VENDOR:
                order.delivery_by = DeliveryProvider.VENDOR
                # Notify on slack about vendor delivery selected
                signals.vendor_delivery_own_signal(sender=None, order=order, vendor=vendor)

            # Notify user about order acceptance
            signals.order_accepted.send(sender=None, customer=order.customer, order=order)

            order.status = OrderStatus.PREPARING
            order.save()

            order.events.create(type=OrderEvents.VENDOR_ACCEPTED.value, user=request.user)

            # Notify on Slack that vendor has accepted the order
            order_serializer = VendorOrderSerializer(order)
            return Response(order_serializer.data)
        except Exception as e:
            capture_exception(e)
            exc_info = sys.exc_info()
            newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
            return Response({'error': 'Internal error 1337. Please contact our support at support@halalivery.co.uk.{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Internal error 1336. Please contact our support at support@halalivery.co.uk.'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=['post'], detail=True)
    def reject_order(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        vendor = get_object_or_404(Vendor, user=request.user)
        order = get_object_or_404(Order, id=order_id, vendor=vendor)

        if order.status != OrderStatus.CONFIRMED:
            return Response({"error": "Order cannot be rejected at this stage."}, status=status.HTTP_400_BAD_REQUEST)
        
        payment = order.get_last_payment()
        
        if payment.can_refund():
            refund_amount = payment.get_captured_amount()
            gateway_refund(payment=payment)
            order.events.create(
                parameters={'amount': refund_amount},
                type=OrderEvents.PAYMENT_REFUNDED.value,
                user=request.user)
        else:
            authorized_amount = payment.get_authorized_amount()
            gateway_void(payment=payment)
            order.events.create(
                parameters={'amount': authorized_amount},
                type=OrderEvents.PAYMENT_VOIDED.value,
                user=request.user)

        order.status = OrderStatus.CANCELED
        order.save()

        signals.order_rejected.send(sender=None, order=order)
        order_serializer = VendorOrderSerializer(order)
        return Response(order_serializer.data)

    @action(methods=['post'], detail=True)
    def prepare_order(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id)
        vendor = get_object_or_404(Vendor, user=request.user)
        
        if order.vendor != vendor:
            return HttpResponseForbidden()

        if order.status != OrderStatus.PREPARING:
            return Response({"error": "Order #{} cannot be prepared at this stage.".format(order.id)}, status=status.HTTP_400_BAD_REQUEST)

        elif order.status == OrderStatus.READY_FOR_PICKUP:
            return Response({"error": "Order has been prepared already."}, status=status.HTTP_400_BAD_REQUEST)
            
        payment = order.get_last_payment()
        amount = vendor_order_total(order=order)
        try:
            gateway_transfer(payment=payment, amount=amount,
                             destination=vendor.stripe_connect_id, transfer_party=TransferParty.VENDOR)
        except PaymentError as e:
            capture_exception(e)
            return Response({'error': 'Could not process the payment for the Order #{}. Please contact our support.{}'.format(order.id, e)}, status=status.HTTP_400_BAD_REQUEST)
        
        order.events.create(parameters={'amount': amount},type=OrderEvents.PAYMENT_CAPTURED.value, user=request.user)
        # last_payment.transfer(amount=vendor_total, destination=vendor.stripe_connect_id,
        #                       transfer_party=TransferParty.VENDOR)
        # Send a job to Stuart

        #StuartClient().create_job(order)
        
        order.status = OrderStatus.READY_FOR_PICKUP
        order.save()
        
        # Save an event
        order.events.create(type=OrderEvents.VENDOR_PREPARED.value, user=request.user)

        if order.delivery_type == DeliveryType.SELF_PICKUP:
            signals.order_ready_for_self_pickup.send(sender=None, order=order)

        signals.vendor_prepared_order.send(sender=None, order=order, vendor=vendor)
        order_serializer = VendorOrderSerializer(order)
        return Response(order_serializer.data)


        # except Exception as e:
        #     capture_exception(e)
        #     exc_info = sys.exc_info()
        #     newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
        #     return Response({'error': 'Internal error 1338. Please contact our support at support@halalivery.co.uk.'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=['post'], detail=True)
    def pickup_order(self, request, pk=None):
        order_id = request.data.get('order_id', None)
        order = get_object_or_404(Order, id=order_id)
        vendor = get_object_or_404(Vendor, user=request.user)

        if order.vendor != vendor:
            return HttpResponseForbidden()

        if order.status != OrderStatus.READY_FOR_PICKUP:
            return Response({"error": "Internal error 1240. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
        elif order.delivery_type == DeliveryType.SELF_PICKUP and order.status == OrderStatus.SELF_PICKED_UP:
            return Response({"error": "Order has been picked up by the customer."}, status=status.HTTP_400_BAD_REQUEST)
        # elif order.delivery_type == DeliveryType.DELIVERY and order.status == OrderStatus.DRIVER_COLLECTED:
        #     return Response({"error": "Order has been picked up by the driver."}, status=status.HTTP_400_BAD_REQUEST)
        # elif order.delivery_type == DeliveryType.DELIVERY and order.delivery_by != DeliveryProvider.VENDOR:
        #     return Response({"error": "Order will be picked up by the Celery driver."}, status=status.HTTP_400_BAD_REQUEST)

        # self pickup
        if order.delivery_type == DeliveryType.SELF_PICKUP:
            order.status = OrderStatus.SELF_PICKED_UP
            order.events.create(type=OrderEvents.SELF_PICKED_UP.value, user=request.user)
            # signals.order_ready_for_self_pickup_signal(sender=None, order=order)

        order.save()
        order_serializer = VendorOrderSerializer(order)
        return Response(order_serializer.data)

    # @action(methods=['post'], detail=True)
    # def own_delivered(self, request, pk=None):
    #     order_id = request.data.get('order_id', None)
    #     order = get_object_or_404(Order, id=order_id)
    #     vendor = get_object_or_404(Vendor, user=request.user)
    #     if order.vendor != vendor:
    #         return HttpResponseForbidden()

    #     if order.delivery_by != DeliveryProvider.VENDOR:
    #         return Response({"error": "Internal error 1231. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
    #     if order.status < OrderStatus.DRIVER_COLLECTED:
    #         return Response({"error": "Internal error 1239. Please contact our support at support@halalivery.co.uk."}, status=status.HTTP_400_BAD_REQUEST)
    #     elif order.status > OrderStatus.DRIVER_COLLECTED:
    #         return Response({"error": "Order has been delivered already"}, status=status.HTTP_400_BAD_REQUEST)

    #     #order_transfer = get_object_or_404(Transfer, id=order.transfer.id)

    #     # order_last_transaction = last_payment.get_last_transaction()
    #     # order_last_transfer = last_payment.get_last_transfer()
    #     #order_charge = get_object_or_404(Charge, id=order.charge.id)
    #     vendor_total = vendor_order_total(order=order)

    #     if order.delivery_type == DeliveryType.VENDOR:
    #         try:
    #             last_payment = order.get_last_payment()

    #             vendor_total = vendor_order_total(order=order)
    #             last_payment.transfer(amount=vendor_total, destination=vendor.stripe_connect_id,
    #                                   transfer_party=TransferParty.VENDOR)
    #             # Vendor Transfer
    #             # stripe.api_key = STRIPE_API_KEY
    #             # if vendor_total > order.total:
    #             #     transfer = stripe.Transfer.create(
    #             #         amount=int(vendor_total * 100),
    #             #         currency="gbp",
    #             #         description="ORDER #{}".format(order.id),
    #             #         metadata={'order_id': order.id},
    #             #         destination="{}".format(order.vendor.stripe_connect_id),
    #             #         transfer_group="ORDER #{}".format(order.id),
    #             #     )
    #             #     order_last_transfer.vendor_transfer_id = transfer.id
    #             #     order_last_transfer.save()
    #             # elif vendor_total <= order.total:
    #             #     transfer = stripe.Transfer.create(
    #             #         amount=int(vendor_total * 100),
    #             #         currency="gbp",
    #             #         description="ORDER #{}".format(order.id),
    #             #         metadata={'order_id': order.id},
    #             #         source_transaction=order_last_transaction.token,
    #             #         destination="{}".format(order.vendor.stripe_connect_id),
    #             #         transfer_group="ORDER #{}".format(order.id),
    #             #     )
    #             #     order_last_transfer.vendor_transfer_id = transfer.id
    #             #     order_last_transfer.save()
    #         except Exception as e:
    #             exc_info = sys.exc_info()
    #             newrelic.agent.record_exception(exc_info[0], exc_info[1], exc_info[2])
    #             return Response({'error': 'Internal error 1340. Please contact our support at support@halalivery.co.uk.{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)

    #     order.status = OrderStatus.DRIVER_DELIVERED
    #     order.save()

    #     # Send a notification on slack
    #     signals.vendor_delivered.send(sender=None, order=order, vendor=vendor)

    #     order_serializer = VendorOrderSerializer(order)
    #     return Response(order_serializer.data)


@permission_classes((IsAuthenticatedVendor,))
class VendorBusyStatus(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()
        serializer = PrepTimeVendorSerializer(marketplace.prep_time)
        return Response(serializer.data)

    def post(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)

        try:
            busy_status = request.data.get('busy_status')
            marketplace = vendor.marketplace()

            marketplace.prep_time.busy_status = busy_status

            marketplace.prep_time.save()
            serializer = PrepTimeVendorSerializer(marketplace.prep_time)
            return Response(serializer.data)
        except Exception:
            return Response({"error": "Error updating status. Try again."}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes((IsAuthenticatedVendor,))
class VendorPrepTime(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()
        serializer = PrepTimeVendorSerializer(marketplace.prep_time)
        return Response(serializer.data)

    def post(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)

        try:
            quiet_time = request.data.get('quiet_time')
            moderate_time = request.data.get('moderate_time')
            busy_time = request.data.get('busy_time')

            marketplace = vendor.marketplace()

            marketplace.prep_time.quiet_time = quiet_time
            marketplace.prep_time.moderate_time = moderate_time
            marketplace.prep_time.busy_time = busy_time

            marketplace.prep_time.save()
            serializer = PrepTimeVendorSerializer(marketplace.prep_time)
            return Response(serializer.data)
        except Exception:
            return Response({"error": "Error updating preparation time. Try again."},
                            status=status.HTTP_400_BAD_REQUEST)


@permission_classes((IsAuthenticatedVendor,))
class VendorOperatingTime(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()
        serializer = VendorOperatingTimeSerializer(marketplace.operating_times, many=True)
        return Response(serializer.data)


@permission_classes((IsAuthenticatedVendor,))
class VendorStatus(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        restaurant = vendor.marketplace()

        return Response({"status": restaurant.online})

    def post(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        online_status = request.data.get('online', None)
        restaurant = vendor.marketplace()

        if restaurant:
            if isinstance(online_status, bool):
                restaurant.online = online_status
                restaurant.save()
                return Response({'success': True})
            else:
                return Response({'error': 'Invalid status request'}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes((IsAuthenticatedVendor,))
class VendorMenuItems(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()

        serializer = MenuVendorSerializer(marketplace.menu)
        return Response(serializer.data)

    def post(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        marketplace = vendor.marketplace()
        for item in request.data:
            menu_item = get_object_or_404(MenuItem, id=item["id"])
            marketplace_menu_categories = marketplace.menu.categories.filter(items__id=menu_item.id).count()
            if not marketplace_menu_categories:
                return Response({'error': '{} is not in the {} menu.'.format(menu_item, marketplace)})
            menu_item.available = item["on"]
            menu_item.save()
            # print(marketplace_menu_categories.filter(items__id=menu_item.id))
            # if menu_item not in marketplace_menu_categories.filter(items__id=menu_item.id):
            #     print('NOT')
            # for category in marketplace_menu_categories.filter:
            #     print(category.items.all())

            # if item not in
            # for category in marketplace_menu_categories:
            #     print(category.items.all())

        # for i in request.data:
        #     item = get_object_or_404(MenuItem, id=i["id"])
        #     if item not in restaurant_items:
        #         return Response({'error': '{} is not in the {} menu.'.format(item, restaurant)})
        #     item.available = i["on"]
        #     item.save()

        serializer = MenuVendorSerializer(marketplace.menu)
        return Response(serializer.data)

@permission_classes((IsAuthenticatedVendor,))
class VendorGetInfo(APIView):
    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        if vendor:
            if vendor.vendor_type == 0:
                serializer = VendorRestaurantProfileSerializer(vendor.marketplace())
            elif vendor.vendor_type == 1:
                serializer = VendorGroceryProfileSerializer(vendor.marketplace())
            if not serializer.data:
                return Response({'errors': 'Vendor is not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response(serializer.data)
        else:
            return Response({'errors': 'Requested vendor is not found'}, status=status.HTTP_404_NOT_FOUND)
