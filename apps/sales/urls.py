from django.urls import path, include
from django.contrib.auth.decorators import login_required
# from apps.user.views import users_list, UserList, user_create, user_update, user_save
from .views import *
from .views_PDF import download_ticket_pdf

urlpatterns = [
    # URLs existentes para clientes
    path('client_list/', login_required(get_client_list), name='get_client_list'),
    path('get_api_person/', login_required(get_api_person), name='get_api_person'),
    path('modal_client_create/', login_required(modal_client_create), name='modal_client_create'),
    path('save_client/', login_required(save_client), name='save_client'),
    path('modal_client_update/', login_required(modal_client_update), name='modal_client_update'),
    path('update_client/', login_required(update_client), name='update_client'),

    # URLs existentes para órdenes (legacy)
    path('order_client/', login_required(order_client), name='order_client'),
    path('get_order_by_client/', login_required(get_order_by_client), name='get_order_by_client'),
    # =============================================================================
    # NUEVAS URLs PARA EL SISTEMA DE ÓRDENES MODERNO
    # =============================================================================
    path('clients/create/', login_required(create_client), name='create_client'),
    path('clients/search-autocomplete/', login_required(search_clients_autocomplete), name='search_clients_autocomplete'),
    path('clients/get-client-autocomplete/', login_required(get_client_autocomplete), name='get_client_autocomplete'),
    # path('order_delivery_status_modal', login_required(order_delivery_status_modal), name='order_delivery_status_modal'),

    # =============================================================================
    # URLs PARA PDFs
    # =============================================================================
    path('orders/<int:order_id>/ticket-pdf/', login_required(download_ticket_pdf), name='download_ticket_pdf'),
]