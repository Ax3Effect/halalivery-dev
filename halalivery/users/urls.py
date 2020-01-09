from django.urls import re_path, path
from . import views

urlpatterns = [
    path('customer/profile/', views.CustomerProfileView.as_view(), name='customerProfile'),
    path('customer/address/', views.CustomerAddressView.as_view(), name='customerAddress'),
    path('customer/payment_token/', views.PaymentTokenView.as_view(), name='customerAddress'),
    path('driver/profile/', views.DriverProfileView.as_view(), name='driverProfile'),
    re_path(r'^driver/summary/(?P<from_date>\d+)/(?P<to_date>\d+)/$',
            views.DriverSummaryView.as_view(), name="driverOrderSummary"),
    path('driver/summary/', views.DriverSummaryView.as_view(), name='driverProfile'),
    path('driver/online/', views.DriverStatus.as_view(), name='setDriverOnlineStatus'),
    path('onesignal/', views.OneSignalRegisterDevice.as_view(), name='userOneSignal'),
]
