from django.urls import path
# from .views import stripeTestPage
from . import views

urlpatterns = [
    path('orders/live/', views.LiveOrdersView.as_view(), name='liveOrders'),
    path('orders/active/', views.ActiveOrdersView.as_view(), name='driverActiveOrders'),
    path('location/', views.DriverLocationView.as_view(), name='driverLocation'),
    path('orders/action/accept_order/', views.DriverActionView.as_view({'post': 'accept_order'}), name='driverAction'),
    path('orders/action/reject_order/', views.DriverActionView.as_view({'post': 'reject_order'}), name='driverAction'),
    path('orders/action/arrived/', views.DriverActionView.as_view({'post': 'arrived'}), name='driverAction'),
    path('orders/action/collected/', views.DriverActionView.as_view({'post': 'collected'}), name='driverAction'),
    path('orders/action/delivered/', views.DriverActionView.as_view({'post': 'delivered'}), name='driverAction'),
    path('profile/driver/online/', views.DriverProfileActionView.as_view({'post': 'online'}), name='driverAction'),
    path('stuart/test/', views.StuartTest.as_view(), name='stuartTest'),
    path('webhook/stuart/', views.StuartWebhook.as_view(), name='stuartWebook'),

    # re_path(r'orders/active/', views.LiveOrdersView.as_view(), name='driverActiveOrders'),
    # re_path(r'getDriverOrders', views.GetDriverOrdersView.as_view(), name='driverOrders'),
]
