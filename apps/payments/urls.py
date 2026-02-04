from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import *
from .views_PDF import download_deposit_pdf

app_name = 'payments'

urlpatterns = [
    # Órdenes de depósito - Vistas principales
    # path('', views.deposit_order_list, name='deposit_order_list'),

    path('deposit_order_list/', login_required(deposit_order_list), name='deposit_order_list'),
    path('search_clients_autocomplete/', login_required(search_clients_autocomplete), name='search_clients_autocomplete'),

    # Vistas AJAX para depósitos
    path('deposit_save/', login_required(deposit_save), name='save_deposit'),
    # path('ajax/update-deposit/', views.deposit_update, name='update_deposit'),
    # path('ajax/get-deposit-for-edit/', views.get_deposit_for_edit, name='get_deposit_for_edit'),
    # path('ajax/search-clients/', views.search_clients, name='search_clients'),
    # path('ajax/create-client/', views.create_client, name='create_client'),
    path('get_next_serial/', login_required(get_next_serial), name='get_next_serial'),
    # path('ajax/confirm-deposit/', views.deposit_confirm, name='deposit_confirm'),
    # path('ajax/cancel-deposit/', views.deposit_cancel, name='deposit_cancel'),
    #
    # # URLS para entidades de destino
    path('modal_entities/', login_required(modal_entities), name='modal_entities'),
    path('destination_entity_list/', login_required(destination_entity_list), name='destination_entity_list'),
    path('destination_entity_save/', login_required(destination_entity_save), name='destination_entity_save'),
    path('destination_entity_get/', login_required(destination_entity_get), name='destination_entity_get'),

    path('modal_deposit_create/', login_required(modal_deposit_create), name='modal_deposit_create'),
    path('create_client/', login_required(create_client), name='create_client'),
    path('update_deposit_status/', login_required(update_deposit_status), name='update_deposit_status'),
    path('confirm_deposit/', login_required(confirm_deposit), name='confirm_deposit'),
    path('view_deposit/', login_required(view_deposit), name='view_deposit'),
    
    # PDF de depósitos
    path('download_deposit_pdf/<int:deposit_id>/', login_required(download_deposit_pdf), name='download_deposit_pdf'),
]
