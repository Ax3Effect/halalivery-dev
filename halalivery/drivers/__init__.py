from django.utils.translation import pgettext_lazy


class InsuranceType:
    ZEGO = 'zego'
    OTHER = 'other'
    NOT_REQUIRED = 'not-required'

    CHOICES = [
        (ZEGO, pgettext_lazy('insurance type', 'ZEGO Insurance')),
        (OTHER, pgettext_lazy('insurance type', '3rd party insurance provider')),
        (NOT_REQUIRED, pgettext_lazy('insurance type', 'Not required'))]

class TransportType:
    CAR = 'car'
    MOTORBIKE = 'motorbike'
    BICYCLE = 'bicycle'

    CHOICES = [
        (CAR, pgettext_lazy('transport type', 'Car')),
        (MOTORBIKE, pgettext_lazy('transport type', 'Motorbike')),
        (BICYCLE, pgettext_lazy('transport type', 'Bicycle'))]