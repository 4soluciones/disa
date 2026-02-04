from django.contrib import admin
from .models import DepositOrder, DestinationEntity


@admin.register(DestinationEntity)
class DestinationEntityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DepositOrder)
class DepositOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'deposit_number', 'depositor_client', 'account_holder', 'amount', 'status', 'creation_date']
    list_filter = ['status', 'creation_date', 'subsidiary', 'destination_entity']
    search_fields = ['deposit_number', 'depositor_client__full_name', 'account_holder', 'account_number']
    readonly_fields = ['deposit_number', 'creation_date', 'updated_at', 'confirmed_at', 'confirmed_by']

