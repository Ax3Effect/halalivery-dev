from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist
from .models import Customer, Driver, Vendor


class IsAuthenticatedCustomer(permissions.BasePermission):
    message = "You have to be an authenticated customer to perform this action."

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        try:
            customer = Customer.objects.get(user=request.user)
            return True
        except ObjectDoesNotExist:
            return False


class IsAuthenticatedDriver(permissions.BasePermission):
    message = "You have to be a driver to perform this action."

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        try:
            driver = Driver.objects.get(user=request.user)  # TODO: Add driver status
            return True
        except ObjectDoesNotExist:
            return False


class IsAuthenticatedVendor(permissions.BasePermission):
    message = "You have to be a vendor to perform this action."

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        try:
            vendor = Vendor.objects.get(user=request.user)  # TODO: Add driver status
            return True
        except ObjectDoesNotExist:
            return False



class IsUserOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True

        return obj == request.user
