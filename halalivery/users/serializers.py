import stripe
import datetime
import time
from rest_framework import serializers
from django.core.validators import validate_email

from .models import *
from .static import VENDOR_TYPE, TRANSPORT_TYPE

from halalivery.drivers import TransportType, InsuranceType
from halalivery.vendors import VendorType

from halalivery.static import STRIPE_API_KEY, ZEGO_BASE_URL
from urllib.parse import urlencode
from rest_framework.response import Response
from . import signals

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')


class UserSignupSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'auth_token')
        read_only_fields = ('auth_token',)
        extra_kwargs = {'password': {'write_only': True}}


class VendorSignupSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'auth_token')
        read_only_fields = ('auth_token',)
        extra_kwargs = {'password': {'write_only': True}}


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        fields = ('id', 'address_name', 'phone', 'street_address_1', 'street_address_2',
                  'postcode', 'city', 'latitude', 'longitude')
        read_only_fields = ('latitude', 'longitude', )


class CustomerAddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        exclude = ('point', )
        read_only_fields = ('latitude', 'longitude', )


class DestinationSerializer(serializers.ModelSerializer):
    destination_name = serializers.SerializerMethodField()

    class Meta:
        model = Address
        fields = ('destination_name', 'phone', 'street_address_1', 'street_address_2', 'postcode', 'city',
                  'latitude', 'longitude', 'delivery_instructions')

    def get_destination_name(self, obj):
        customer = self.context.get('customer', None)
        vendor = self.context.get('vendor', None)

        if customer is not None:
            return "{} {}.".format(customer.user.first_name, customer.user.last_name[:1])
        elif vendor is not None:
            return vendor.vendor_name


class PaymentTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentToken
        fields = ('id', 'provider', 'payment_method', 'card_type',
                  'masked_number', 'payment_type', 'expiration_date')


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    payment_token = PaymentTokenSerializer(many=True, read_only=True)
    address = CustomerAddressSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ('id', 'user', 'payment_token', 'address')


class VendorSerializer(serializers.ModelSerializer):
    address = AddressSerializer(many=False, read_only=False)

    class Meta:
        model = Vendor
        fields = ('id', 'vendor_name', 'vendor_type',
                  'halalivery_exclusive', 'hmc_approved', 'address', 'logo')


class CreateCustomerSerializer(serializers.ModelSerializer):

    user = UserSignupSerializer(many=False, read_only=False)

    def create(self, validated_data):
        try:
            user_data = validated_data.pop('user')

            if validate_email(
                    user_data['email']) and User.objects.filter(
                    email=user_data['email']).exclude(
                    username=user_data['username']).exists():
                raise ValidationError

            user = User.objects.create_user(
                username=user_data['username'], password=user_data['password'], email=user_data['email'],
                first_name=user_data['first_name'], last_name=user_data['last_name'])

            customer = Customer.objects.create(user=user)
            return customer
        except ValidationError:
            raise serializers.ValidationError(
                {"error": "Email address not valid. Please enter a unique email address."})
        except Exception:
            raise serializers.ValidationError(
                {"error": "Error parsing the request. Make sure all the required fields are present."})

    class Meta:
        model = Customer
        fields = ('user',)


class CreateDriverSerializer(serializers.ModelSerializer):

    user = UserSignupSerializer(many=False, read_only=False)
    dob = serializers.DateField(initial=datetime.date.today, required=True, format="%d/%m/%Y", input_formats=['%d/%m/%Y', 'iso-8601'])
    transport_type = serializers.ChoiceField(choices=TransportType.CHOICES, required=True)
    insurance_type = serializers.ChoiceField(choices=InsuranceType.CHOICES, required=True)
    address = AddressSerializer(many=False, read_only=False)
    sort_code = serializers.CharField(required=False)
    account_number = serializers.CharField(required=False)
    driver_personal_id_number = serializers.CharField(required=False)
    send_zego_email = serializers.BooleanField(required=False, default=False)
    send_credentials_email = serializers.BooleanField(required=False, default=False)


    def create(self, validated_data):
        try:
            # stripe.api_key = STRIPE_API_KEY
            # account = stripe.Account.retrieve('acct_1CfY4SHiDz6P4VHd')
            # print(account)
            # account.legal_entity.verification.document = '124'
            # account.save()
            #return Driver
            #print(account)
            user_data = validated_data.pop('user')
            dob = validated_data.pop('dob', None)
            transport_type = validated_data.pop('transport_type', '')
            address = validated_data.pop('address')
            sort_code = validated_data.pop('sort_code', None)
            account_number = validated_data.pop('account_number', None)
            driver_personal_id_number = validated_data.pop('driver_personal_id_number', None)
            send_zego_email = validated_data.pop('send_zego_email', False)
            send_credentials_email = validated_data.pop('send_credentials_email', False)
            insurance_type = validated_data.pop('insurance_type', 'not_required')
            # print(dob)
            # _dob = dob#datetime.datetime.strptime(str(dob),'%Y-%m-%d')
            # print(_dob)
            # print(request.META)

            stripe.api_key = STRIPE_API_KEY
            stripe_driver = stripe.Account.create(
                type='custom',
                country='GB',
                email=user_data['email'],
            )
            stripe_driver.legal_entity.type = 'individual'
            stripe_driver.legal_entity.first_name = user_data['first_name']
            stripe_driver.legal_entity.last_name = user_data['last_name']
            stripe_driver.legal_entity.dob.day = dob.day
            stripe_driver.legal_entity.dob.month = dob.month
            stripe_driver.legal_entity.dob.year = dob.year
            stripe_driver.legal_entity.address = dict(line1=address['line1'],
                                                      line2=address['line2'],
                                                      postal_code=address['postcode'],
                                                      city=address['city'],
                                                      country='GB')
            stripe_driver.legal_entity.personal_address = dict(line1=address['line1'],
                                                      line2=address['line2'],
                                                      postal_code=address['postcode'],
                                                      city=address['city'],
                                                      country='GB')
            stripe_driver.legal_entity.personal_id_number = driver_personal_id_number
            # stripe_driver.legal_entity.verification.document = driver_personal_id_number

            if sort_code and account_number:
                    stripe_driver.external_account = dict(object='bank_account',
                                                        country='GB',
                                                        currency='gbp',
                                                        routing_number=sort_code,
                                                        account_number=account_number)

            stripe_driver.payout_schedule.interval = 'weekly'
            stripe_driver.payout_schedule.weekly_anchor = 'friday'
            stripe_driver.payout_schedule.delay_days = '14'

            stripe_driver.tos_acceptance.date = int(time.time())
            stripe_driver.tos_acceptance.ip = '8.8.8.8'

            stripe_driver.save()

            user = User.objects.create_user(username=user_data['username'],
                                            password=user_data['password'],
                                            first_name=user_data['first_name'],
                                            last_name=user_data['last_name'],
                                            email=user_data['email'])
            address = Address.objects.create(**address)
            driver = Driver(user=user, dob=dob, transport_type=transport_type, address=address,
                            stripe_connect_id=stripe_driver.id, insurance_type=insurance_type)

            driver.save()

            # Zego implementation
            params = urlencode({
                'wp': 'Halalivery',
                'wp_id': driver.id,
                'email': driver.user.email
            })

            driver_url = '{}link-work-provider?{}'.format(ZEGO_BASE_URL, params)
            driver.zego_registration_url = driver_url
            driver.save()
            if send_zego_email is True:
                signals.driver_zego.send(sender=None, driver=driver)
            if send_credentials_email is True:
                signals.driver_credentials.send(sender=None, driver=driver, username=user_data['username'], password=user_data['password'])

            return driver

        except Exception as e:
            raise serializers.ValidationError(
                'Error occurred while parsing the input. Please try again. ' + str(e))

    class Meta:
        model = Driver
        fields = ('user', 'driver_personal_id_number', 'dob', 'sort_code', 'account_number', 'transport_type', 'insurance_type', 'address', 'zego_registration_url', 'send_zego_email', 'send_credentials_email')


class CreateVendorSerializer(serializers.ModelSerializer):

    user = VendorSignupSerializer(many=False, read_only=False)
    vendor_name = serializers.CharField(required=True)
    vendor_type = serializers.ChoiceField(choices=VendorType.CHOICES, required=True)
    companyhouse_number = serializers.CharField(required=True)
    halalivery_exclusive = serializers.NullBooleanField(required=False)
    hmc_approved = serializers.NullBooleanField(required=False)
    address = AddressSerializer(many=False, read_only=False)
    legal_entity_first_name = serializers.CharField(required=False)
    legal_entity_last_name = serializers.CharField(required=False)
    legal_entity_dob = serializers.DateField(initial=datetime.date.today, required=True, format="%d/%m/%Y", input_formats=['%d/%m/%Y', 'iso-8601'])
    legal_entity_phone = serializers.CharField(required=False)
    # legal_entity_address = AddressSerializer(many=False, read_only=False)
    logo = serializers.ImageField(use_url='restaurant_logo/', required=False)
    sort_code = serializers.CharField(required=False)
    account_number = serializers.CharField(required=False)

    def create(self, validated_data):
        try:
            user_data = validated_data.pop('user')
            address_data = validated_data.pop('address')
            vendor_name = validated_data.pop('vendor_name')
            vendor_type = validated_data.pop('vendor_type')
            companyhouse_number = validated_data.pop('companyhouse_number')
            legal_entity_first_name = validated_data.pop('legal_entity_first_name')
            legal_entity_last_name = validated_data.pop('legal_entity_last_name')
            legal_entity_dob = validated_data.pop('legal_entity_dob')
            legal_entity_phone = validated_data.pop('legal_entity_phone')
            # legal_entity_address_data = validated_data.pop('legal_entity_address')
            logo = validated_data.pop('logo', None)
            sort_code = validated_data.pop('sort_code', None)
            account_number = validated_data.pop('account_number', None)

            _dob = legal_entity_dob

            stripe.api_key = STRIPE_API_KEY
            stripe_vendor = stripe.Account.create(
                type='custom',
                country='GB',
                email=user_data['email'],
            )
            stripe_vendor.business_name = vendor_name

            stripe_vendor.legal_entity.business_name = vendor_name
            stripe_vendor.legal_entity.type = 'company'
            stripe_vendor.legal_entity.business_tax_id = companyhouse_number
            stripe_vendor.legal_entity.additional_owners = None
            stripe_vendor.legal_entity.first_name = legal_entity_first_name
            stripe_vendor.legal_entity.last_name = legal_entity_last_name
            stripe_vendor.legal_entity.phone_number = legal_entity_phone
            stripe_vendor.legal_entity.dob.day = _dob.day
            stripe_vendor.legal_entity.dob.month = _dob.month
            stripe_vendor.legal_entity.dob.year = _dob.year
            stripe_vendor.legal_entity.address = dict(line1=address_data['line1'],
                                                      line2=address_data['line2'],
                                                      postal_code=address_data['postcode'],
                                                      city=address_data['city'],
                                                      country='GB')
            stripe_vendor.legal_entity.personal_address = dict(line1=address_data['line1'],
                                                               line2=address_data['line2'],
                                                               postal_code=address_data['postcode'],
                                                               city=address_data['city'],
                                                               country='GB')
            if sort_code and account_number:
                stripe_vendor.external_account = dict(object='bank_account',
                                                        country='GB',
                                                        currency='gbp',
                                                        routing_number=sort_code,
                                                        account_number=account_number)

            stripe_vendor.payout_schedule.interval = 'weekly'
            stripe_vendor.payout_schedule.weekly_anchor = 'friday'
            stripe_vendor.payout_schedule.delay_days = '14'

            stripe_vendor.tos_acceptance.date = int(time.time())
            stripe_vendor.tos_acceptance.ip = '8.8.8.8'

            stripe_vendor.save()

            user = User.objects.create_user(
                username=user_data['username'], password=user_data['password'], email=user_data['email'])
            address = Address.objects.create(**address_data)
            vendor = Vendor(user=user, vendor_name=vendor_name, vendor_type=vendor_type,
                            companyhouse_number=companyhouse_number,
                            address=address, logo=logo,
                            legal_entity_first_name=legal_entity_first_name,
                            legal_entity_last_name=legal_entity_last_name,
                            legal_entity_dob=_dob,
                            legal_entity_phone=legal_entity_phone,
                            stripe_connect_id=stripe_vendor.id)
            vendor.save()
            return vendor

        except Exception as e:
            raise serializers.ValidationError(
                'Error occurred while parsing the input. Please try again.' + str(e))

    class Meta:
        model = Vendor
        fields = (
            'user',
            'vendor_name',
            'vendor_type',
            'companyhouse_number',
            'sort_code',
            'account_number',
            'halalivery_exclusive',
            'hmc_approved',
            'address',
            'legal_entity_first_name',
            'legal_entity_last_name',
            'legal_entity_dob',
            'legal_entity_phone',
            'logo')


class OneSignalSerializer(serializers.Serializer):
    onesignal = serializers.UUIDField()
