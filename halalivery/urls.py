from django.conf import settings
from django.urls import path, re_path, include, reverse_lazy
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views
from rest_framework.documentation import include_docs_urls
from .users.views import UserCustomerCreateViewSet, UserDriverCreateViewSet, UserVendorCreateViewSet


admin.site.site_header = "Halalivery administration"
admin.site.site_title = "Halalivery administration"
admin.site.index_title = "Welcome to Halalivery administration panel. Strictly for internal use only."

router = DefaultRouter()
router.register(r'vendor', UserVendorCreateViewSet)
router.register(r'driver', UserDriverCreateViewSet)
router.register(r'customer', UserCustomerCreateViewSet)

urlpatterns = [
    # path('grappelli/', include('grappelli.urls')), # grappelli URLS
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/marketplaces/', include('halalivery.marketplaces.urls')),
    path('api/v1/basket/', include('halalivery.basket.urls')),
    path('api/v1/order/', include('halalivery.order.urls')),
    path('api/v1/vendors/', include('halalivery.vendors.urls')),
    path('api/v1/drivers/', include('halalivery.drivers.urls')),
    path('api/v1/users/', include('halalivery.users.urls')),
    path('login/', views.obtain_auth_token),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    #re_path(r'^_nested_admin/', include('nested_admin.urls')),
    re_path(r'^api/docs/', include_docs_urls(title='Halalivery API')),
    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False))

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import debug_toolbar
urlpatterns = [
    path('__debug__/', include(debug_toolbar.urls)),

] + urlpatterns