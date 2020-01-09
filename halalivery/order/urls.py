from django.urls import re_path, path
from . import views

urlpatterns = [
    re_path(r'^$', views.CreateOrderView.as_view(), name="createOrder"),
    path('payment/', views.OrderPaymentView.as_view(), name="addOrderPayment"),
    re_path(r'^$', views.OrderView.as_view(), name="customerOrders"),
    re_path(r'^(?P<order_id>\d+)/$', views.OrderView.as_view(), name="customerOrder"),
]
