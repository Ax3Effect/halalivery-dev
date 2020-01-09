from rest_framework import serializers
from halalivery.menu.models import *

class MenuItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemOption
        fields = '__all__'


class MenuOptionsGroupSerializer(serializers.ModelSerializer):
    options = MenuItemOptionSerializer(many=True, read_only=True, source='items')

    class Meta:
        model = MenuOptionsGroup
        depth = 1
        fields = ('id', 'name', 'multiple', 'sort_order', 'required', 'options')

class MenuItemCategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = MenuCategory
        fields = '__all__'

class MenuItemSerializer(serializers.ModelSerializer):
    option_groups = MenuOptionsGroupSerializer(many=True, read_only=True, source='options')

    class Meta:
        model = MenuItem
        depth = 1
        fields = ('id', 'name', 'image', 'description', 'price', 'available', 'popular', 'sort_order', 'option_groups')

class MenuCategorySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    #MenuItemSerializer(many=True, read_only=True)

    def get_items(self, obj):
        qs = obj.items.all().filter(available=True)
        serializer = MenuItemSerializer(instance=qs, many=True, read_only=True)
        return serializer.data

    class Meta:
        model = MenuCategory
        depth = 2
        fields = ('id', 'name', 'description', 'sort_order', 'top_level', 'items')

class VendorMenuCategorySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    #MenuItemSerializer(many=True, read_only=True)

    def get_items(self, obj):
        qs = obj.items.all()
        serializer = MenuItemSerializer(instance=qs, many=True, read_only=True)
        return serializer.data

    class Meta:
        model = MenuCategory
        depth = 2
        fields = ('name', 'description', 'sort_order', 'top_level', 'items')

class MenuSerializer(serializers.HyperlinkedModelSerializer):
    #items = MenuItemSerializer(many=True, read_only=True)
    items = serializers.SerializerMethodField()
    items_options_groups = MenuOptionsGroupSerializer(many=True, read_only=True)
    #categories = MenuCategorySerializer(many=True, read_only=True)

    def get_items(self, obj):
        qs = obj.items.all().filter(available=True)
        serializer = MenuItemSerializer(instance=qs, many=True, read_only=True)
        return serializer.data
    
    class Meta:
        model = Menu
        depth = 2
        fields = ('items_options_groups', 'items')

class MenuLightSerializer(serializers.HyperlinkedModelSerializer):
    categories = MenuCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        depth = 2
        fields = ('id', 'name', 'categories')
