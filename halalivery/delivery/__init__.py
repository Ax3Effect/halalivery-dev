from django.utils.translation import pgettext_lazy

class RouteType:
    DRIVING = 'driving'
    BICYCLING = 'bicycling'
    WALKING = 'walking'

    CHOICES = [
        (DRIVING, pgettext_lazy('route type', 'Driving')),
        (WALKING, pgettext_lazy('route type', 'Walking')),
        (BICYCLING, pgettext_lazy('route type', 'Bicycling'))]

class DeliveryType:
    DELIVERY = 'delivery'
    SELF_PICKUP = 'pickup'

    CHOICES = [
        (DELIVERY, pgettext_lazy(
            'Status for an order to be delivered.',
            'Delivery')),
        (SELF_PICKUP, pgettext_lazy(
            'Status for an order to be Self picked up',
            'Self pickup')),
    ]

class DeliveryProvider:
    CELERY = 'celery'
    STUART = 'stuart'
    VENDOR = 'vendor'

    CHOICES = [
        (CELERY, pgettext_lazy(
            'Status for an order to be delivered by Celery.',
            'Celery delivery')),
        (STUART, pgettext_lazy(
            'Status for an order to be delivered by Stuart',
            'Stuart delivery')),
        (VENDOR, pgettext_lazy(
            'Status for an order to be delivered by Vendor',
            'Vendor delivery')),
    ]