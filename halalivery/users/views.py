from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from .permissions import IsAuthenticatedCustomer, IsAuthenticatedDriver
from .models import User, Customer, Address, PaymentToken, Driver
from .serializers import CreateDriverSerializer,\
    CreateVendorSerializer, CreateCustomerSerializer,\
    CustomerSerializer, AddressSerializer, PaymentTokenSerializer, \
    OneSignalSerializer, CustomerAddressSerializer

from halalivery.drivers.serializers import DriverSerializer, DriverSummarySerializer
from halalivery.static import STRIPE_API_KEY, ZEGO_BASE_URL, ZEGO_API_KEY
from halalivery.users.models import Vendor
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
import json
import requests
import stripe
import datetime
from pytz import timezone, UTC

class UserCustomerCreateViewSet(mixins.CreateModelMixin,
                                viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = CreateCustomerSerializer
    permission_classes = (AllowAny,)


class UserDriverCreateViewSet(mixins.CreateModelMixin,
                              viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = CreateDriverSerializer
    permission_classes = (IsAdminUser,)


class UserVendorCreateViewSet(mixins.CreateModelMixin,
                              viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = CreateVendorSerializer
    permission_classes = (IsAdminUser,)


@permission_classes([IsAuthenticated, ])
class OneSignalRegisterDevice(APIView):
    """
    Registers OneSignal device in our system
    """

    def post(self, request, format=None):
        user = request.user
        onesignal_serializer = OneSignalSerializer(data=request.data)
        if onesignal_serializer.is_valid():
            onesignal_token = onesignal_serializer.validated_data["onesignal"]
            user.onesignal_token = onesignal_token
            user.save()
            return Response({"success": True})
        else:
            return Response({"error": "Unable to register a device for push notifications"}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticatedCustomer, ])
class CustomerProfileView(APIView):
    def get(self, request, format=None):
        user = request.user
        customer = get_object_or_404(Customer, user=user)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

    def patch(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        try:
            json_data = json.loads(request.body)
            user_data = json_data.pop('user')

            if 'first_name' in user_data or 'last_name' in user_data:
                User.objects.filter(id=customer.user.id).update(**user_data)
                customer = get_object_or_404(Customer, user=request.user)
                serializer = CustomerSerializer(customer)
                return Response(serializer.data)
            else:
                return Response({"error": "Error parsing inputs"},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"error": "Error parsing inputs"},
                            status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticatedDriver, ])
class DriverProfileView(APIView):
    def get(self, request, format=None):
        driver = get_object_or_404(Driver, user=request.user)
        serializer = DriverSerializer(driver)
        return Response(serializer.data)

    def patch(self, request, format=None):
        driver = get_object_or_404(Driver, user=request.user)

        try:
            json_data = json.loads(request.body)

            Driver.objects.filter(id=driver.id).update(online=json_data['online'])
            driver = get_object_or_404(Driver, user=request.user)
            serializer = DriverSerializer(driver)
            return Response(serializer.data)
        except Exception:
            return Response(
                {
                    "error": "Error parsing inputs. Please contact Halalivery support to update your profile."},
                status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticatedDriver, ])
class DriverSummaryView(APIView):
    def get(self, request, format=None, from_date=None, to_date=None):
        driver = get_object_or_404(Driver, user=request.user)

        if from_date is None and to_date is None:
            serializer = DriverSummarySerializer(driver)
        elif from_date is not None and to_date is not None:
            _from_date = datetime.datetime.strptime(from_date, '%d%m%y').astimezone(timezone('GB'))
            _to_date = datetime.datetime.strptime(to_date, '%d%m%y').astimezone(
                timezone('GB')) + datetime.timedelta(days=1)

            serializer = DriverSummarySerializer(
                driver, context={'from_date': _from_date, 'to_date': _to_date})
        else:
            return Response({"error": "Error parsing inputs"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data)

@permission_classes((IsAuthenticatedDriver,))
class DriverStatus(APIView):
    def post(self, request):
        driver = get_object_or_404(Driver, user=request.user)
        online_status = request.data.get('online', None)
        if driver:
            if isinstance(online_status, bool):
                if online_status != driver.online:
                    if online_status is False:
                        driver.online = online_status
                        driver.save()
                        return Response({'success': True})

                    # Do not check for zego for cyclists which is transport_type==2
                    if driver.insurance_type == 'zego':
                        # Zego implementation. Check if the user is insured
                        driver_id = driver.id # driver.id '94900'
                        response = requests.get(
                            '{}v1/user/status/?driverId={}'.format(ZEGO_BASE_URL, driver_id),
                            headers={'Authorization': ZEGO_API_KEY},
                        )

                        zego_json = response.json()

                        if response.status_code != 200 or zego_json["status"] != "ENABLED":
                            return Response({'error': 'There is an issue with your Zego insurance. Please contact us at support@halalivery.co.uk for further details. Please include your driver id: {}'.format(driver.id)}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    
                    #  if zego_json["status"] != "ENABLED":
                    #         return Response({'error': 'You are not insured. Please contact Zego at https://www.zego.com/contact-us for further details.'}, status=status.HTTP_401_UNAUTHORIZED)
                    #elif driver.insurance_type == 'other' or driver.insurance_type == 'not_required':
                    driver.online = online_status
                    driver.save()
                    return Response({'success': True})
                else:
                    return Response({'error': 'Already updated the status'}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'error': 'Invalid status request'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Driver not found'}, status=status.HTTP_404_NOT_FOUND)


@permission_classes([IsAuthenticatedCustomer, ])
class CustomerAddressView(APIView):

    def get(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        address = customer.address
        serializer = CustomerAddressSerializer(address, many=True)
        return Response(serializer.data)

    def patch(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)

        json_data = json.loads(request.body)
        address = customer.address.filter(id=json_data['id'])
        if address.exists():
            address_id = json_data.pop('id')
            if 'postcode' in json_data:
                r = requests.get("https://api.postcodes.io/postcodes/{}".format(json_data['postcode']))
                r_json = r.json()
                if r_json["status"] == 404:
                    return Response({"error": "Postcode not found"},
                                    status=status.HTTP_400_BAD_REQUEST)

                latitude = r_json["result"]["latitude"]
                longitude = r_json["result"]["longitude"]

                Address.objects.filter(id=address_id).update(**json_data, latitude=latitude, longitude=longitude)
            else:
                Address.objects.filter(id=address_id).update(**json_data)
            address = customer.address
            serializer = CustomerAddressSerializer(address, many=True)
            return Response(serializer.data)

        else:
            return Response({"error": "Address not found for customer"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)

        try:
            json_data = json.loads(request.body)

            address_name = json_data['address_name']
            phone = json_data['phone']
            line1 = json_data['line1']
            line2 = json_data['line2']
            postcode = json_data['postcode']
            city = json_data['city']
            delivery_instructions = json_data['delivery_instructions']

            address = Address.objects.create(address_name=address_name, street_address_1=line1, phone=phone,
                                             street_address_2=line2, postcode=postcode, city=city,
                                             delivery_instructions=delivery_instructions)

            customer.address.add(address)
            customer.save()
            address = customer.address
            serializer = CustomerAddressSerializer(address, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)

        json_data = json.loads(request.body)
        customer_address = customer.address.filter(id=json_data['id'])
        if customer_address.exists():
            address_id = json_data.pop('id')
            address_obj = Address.objects.get(id=address_id)
            address_obj.delete()
            address = customer.address
            serializer = CustomerAddressSerializer(address, many=True)
            return Response(serializer.data)
        else:
            return Response({"error": "Payment token not found for customer"},
                            status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticatedCustomer, ])
class PaymentTokenView(APIView):

    def get(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)
        payment = customer.payment_token
        serializer = PaymentTokenSerializer(payment, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)

        try:
            json_data = json.loads(request.body)

            token = json_data['token']
            provider = json_data['provider']

            if provider == 'stripe':
                stripe.api_key = STRIPE_API_KEY
                stripe_card = stripe.Token.retrieve(token)
                stripe_customer = stripe.Customer.create(
                    source=token,
                    email=customer.user.email,

                )

                payment_token = PaymentToken.objects.create(
                    token=token, provider=provider,
                    payment_method=stripe_card['type'],
                    card_type=stripe_card['card']['brand'],
                    masked_number=stripe_card['card']['last4'],
                    payment_type=stripe_card['card']['funding'],
                    expiration_date=str(stripe_card['card']['exp_month'])+'/'+str(stripe_card['card']['exp_year']),
                    customer_id=stripe_customer.id
                )

                customer.payment_token.add(payment_token)
                customer.save()

                payment = customer.payment_token
                serializer = PaymentTokenSerializer(payment, many=True)
                return Response(serializer.data)
            else:
                return Response({"error": "Provider not supported"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Error parsing the input or token not found"},
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, format=None):
        customer = get_object_or_404(Customer, user=request.user)

        json_data = json.loads(request.body)
        payment_token = customer.payment_token.filter(id=json_data['id'])
        if payment_token.exists():
            payment_token_id = json_data.pop('id')
            payment_token = PaymentToken.objects.get(id=payment_token_id)
            payment_token.delete()
            payment = customer.payment_token
            serializer = PaymentTokenSerializer(payment, many=True)
            return Response(serializer.data)
        else:
            return Response({"error": "Payment token not found for customer"},
                            status=status.HTTP_400_BAD_REQUEST)
