from decimal import Decimal
from halalivery.drivers.models import DriverPayout
from . import DeliveryType

from halalivery.drivers.gateways.stuart import StuartClient
from halalivery.helpers import yards_to_miles
from halalivery.static import GOOGLE_MAPS_API_KEY
import googlemaps
from sentry_sdk import capture_exception
from django.utils import timezone
# NG9 6DQ
def get_delivery_fee(order, total):
    delivery_fee = Decimal('0.00')
    if order.delivery_type != DeliveryType.SELF_PICKUP and order.address:
        # Stuart request to determine the price
        delivery_fee = StuartClient().job_pricing(vendor=order.vendor, customer=order.customer, basket_address=order.address)
        if delivery_fee:
            delivery_fee -= get_delivery_fee_discount(total)
        else:
            distance = get_gmaps_distance(from_address=order.vendor.address, to_address=order.address)
            driver_payout = DriverPayout.objects.all().last()
            # Base 2 miles
            if distance:
                if distance <= driver_payout.base_miles:
                    delivery_fee = driver_payout.minimum
                else:
                    delivery_fee = (distance - driver_payout.base_miles) * driver_payout.per_mile
                    delivery_fee += driver_payout.minimum
            else:
                raise Exception('Cannot calculate a delivery fee for the selected address.') 
    elif order.delivery_type != DeliveryType.SELF_PICKUP and not order.address:
        delivery_fee = Decimal(3.99)

    delivery_fee -= get_delivery_fee_discount(total)
    if delivery_fee < Decimal(0):
        delivery_fee = Decimal(0)
    return round(Decimal(delivery_fee), 2)

def get_delivery_fee_discount(total):
    if total >= 15 and total < 25:
        return Decimal(0.00)
    elif total >= 25 and total < 35:
        return Decimal(1.00)
    elif total >= 35 and total < 45:
        return Decimal(2.00)
    elif total >= 45 and total < 50:
        return Decimal(3.00)
    
    return Decimal(100000000)

def get_gmaps_distance(from_address, to_address):
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    lat_to = to_address.latitude
    long_to = to_address.longitude

    lat_from = from_address.latitude
    long_from = from_address.longitude

    distance = None

    try:
        directions_result = gmaps.distance_matrix(origins=(lat_from, long_from), destinations=(
                lat_to, long_to), mode='driving', units='imperial', departure_time=timezone.localtime(timezone.now()), traffic_model='best_guess')
        if directions_result and directions_result['status'] == 'OK':
            distance = Decimal(directions_result['rows'][0]['elements'][0]['distance']['value'])
            distance_in_miles = yards_to_miles(yards=distance)
            distance = distance_in_miles
    
    except Exception as e:
        capture_exception(e)

    return distance