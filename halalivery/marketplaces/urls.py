from django.urls import re_path, path
from .views import stripeTestPage
from . import views

urlpatterns = [
    # re_path(r'^$', get_restaurants, name='index'),
    # re_path(r'^(?P<restaurant_id>[0-9]+)/$', views.RestaurantView.as_view(), name='restaurant'),
    re_path(r'^$', views.MarketplaceView.as_view(), name='index'),
    re_path(r'^(?P<vendor_id>\d+)/$', views.MarketplaceView.as_view(), name="marketplace"),
    path('test/stripeView', stripeTestPage, name="stripeTestView"),
   # path('transport_to_custom_categories/', views.transport_to_custom_categories),
    path('increase_prices/', views.increase_prices),
    path('create_address_points/', views.create_address_points),
]
