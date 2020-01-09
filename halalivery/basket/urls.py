from django.urls import re_path, path
from . import views

urlpatterns = [
    re_path(r'^$', views.BasketView.as_view(), name='index'),
    path('apply_voucher/', views.ValidateVoucher.as_view(), name='applyVoucher'),
]
