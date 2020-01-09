from decimal import Decimal
from halalivery.marketplaces.static import HALALIVERY_ADDITIONAL_FEE, HALALIVERY_PERCENT

from halalivery.delivery import DeliveryProvider

from math import radians, cos, sin, asin, sqrt

# import mpu
import geopy.distance

from sentry_sdk import capture_exception
from django.utils import timezone

# Substract delivery fee from the order
# Scenarios:
# Halalivery delivery - Restaurant - 2.00
# Halalivery delivery - Grocery - 3.00
# Vendor delivery - Restaurant - 2.00
# Vendor delivery - Grocery - 3.00
# Self_pickup - Restaurant - 2.00
# Self_pickup - Grocery - 3.00

def vendor_order_total(order):
    vendor_total = Decimal('0.00')
    if order.partner_discount_is_applied:
        order_subtotal = order.subtotal
    else:
        order_subtotal = order.subtotal + order.discount_amount

    vendor_total = order_subtotal
    if order.delivery_by == DeliveryProvider.VENDOR:
         vendor_total = order_subtotal + order.driver_tip
    
    vendor_total += order.surcharge

    # Charge 30% of our fee
    vendor_total -= vendor_total * HALALIVERY_PERCENT

    # Take 1.5 if selected our deliver
    if order.delivery_by == DeliveryProvider.CELERY:
        vendor_total -= HALALIVERY_ADDITIONAL_FEE

    # Round the total
    vendor_total = round(vendor_total, 2)
    
    return vendor_total

def driver_order_total(order):
    driver_total = Decimal('4.50') + order.driver_tip
    delivery_route =  order.get_last_delivery_route()
    if delivery_route:
        driver_total = delivery_route.driver_payout + order.driver_tip
    return driver_total

def customer_order_total(order):
    customer_total = Decimal('0.00')

    return customer_total

def _get_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    result = (c * r) / 1000  # Convert from meters to kms
    result = convert_to_miles(kms=result) # Converm form kms to miles
    return result

# def get_distance(lat1, lon1, lat2, lon2):
#     dist = mpu.haversine_distance((lat1, lon1), (lat2, lon2))
#     dist = convert_to_miles(kms=dist)
#     return dist

def get_distance(lat1,lon1,lat2,lon2):
    coords_1 = (lat1, lon1)
    coords_2 = (lat2, lon2)
    return geopy.distance.vincenty(coords_1, coords_2).miles

def yards_to_miles(yards=None):
    return yards / 1760

def get_upload_path(instance, filename):
    filename = "{}_{}_{}".format(str(instance.id), str(instance.name).replace(" ", "_"), filename)
    return os.path.join('vendor', 'item_images', filename)


    # order_total = order.total + (order.total * (Decimal('1.00') - order.voucher.price_modifier)) # Remove discount

    # print('in:', order.total)

    #   order_total = order.total * (2 - order.voucher.price_modifier)
        #price_modifier = Decimal('1.00')
    # if order.voucher != None:
    #     price_modifier = order.voucher.price_modifier
    # sub_total = order_subtotal / (price_modifier)


    # if order.vendor.vendor_type == RESTAURANT:
    #     if order.delivery_type == DELIVERY_TYPE_HALALIVERY:
    #         vendor_total = order_subtotal - HALALIVERY_ADDITIONAL_FEE
    #     elif order.delivery_type == DELIVERY_TYPE_VENDOR:
    #         vendor_total = order_subtotal + order.driver_tip
    #     elif order.delivery_type == DELIVERY_TYPE_SELF_PICKUP:
    #         vendor_total = order_subtotal

    # elif order.vendor.vendor_type == GROCERY:
    #     if order.delivery_type == DELIVERY_TYPE_HALALIVERY:
    #         vendor_total = order_subtotal - HALALIVERY_ADDITIONAL_FEE
    #     elif order.delivery_type == DELIVERY_TYPE_VENDOR:
    #         vendor_total = order_subtotal + order.driver_tip
    #     elif order.delivery_type == DELIVERY_TYPE_SELF_PICKUP:
    #         vendor_total = order_subtotal

def get_client_ip(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', None)
    if ip:
        return ip.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', None)

def convert_to_miles(kms: Decimal):
    return kms * 0.62137

def convert_to_kms(miles: Decimal):
    return miles / 0.62137