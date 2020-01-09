from django.urls import path
# from .views import stripeTestPage
from . import views

urlpatterns = [
    path('orders/live', views.VendorGetOrders.as_view(), name="liveOrders"),

    path('profile/', views.VendorGetInfo.as_view(), name="getInfo"),
    path('profile/online/', views.VendorStatus.as_view(), name="setOnlineStatus"),
    path('orders/', views.VendorGetOrders.as_view(), name="getOrders"),
    path('orders/history/', views.VendorGetOrdersHistory.as_view(), name="getOrdersHistory"),
    path('status/', views.VendorBusyStatus.as_view(), name='vendorBusyStatus'),
    path('prep_time/', views.VendorPrepTime.as_view(), name='vendorPrepTime'),
    path('operating_time/', views.VendorOperatingTime.as_view(), name='vendorOperatingTime'),
    path('profile/items/', views.VendorMenuItems.as_view(), name='vendorMenuItems'),
    path('orders/action/accept_order/', views.VendorOrderAction.as_view({'post': 'accept_order'}), name='orderActionstest'),
    path('orders/action/reject_order/', views.VendorOrderAction.as_view({'post': 'reject_order'}), name='orderActionstest'),
    path('orders/action/prepare_order/', views.VendorOrderAction.as_view({'post': 'prepare_order'}), name='orderActionstest'),
    path('orders/action/pickup_order/', views.VendorOrderAction.as_view({'post': 'pickup_order'}), name='orderActionstest'),
    # path('orders/action/own_delivered/', views.VendorOrderAction.as_view({'post': 'own_delivered'}), name='orderActionstest'),
]
