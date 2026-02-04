from django.shortcuts import render
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView
from http import HTTPStatus

from .models import *
import pytz
from django.contrib.auth.models import User
import json
from decimal import Decimal
import math
import random
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
from django.template import loader
from datetime import datetime, date
from django.db import DatabaseError, IntegrityError
from django.core import serializers
from django.db.models import Min, Sum, Max, Q, Prefetch, Subquery, OuterRef, Value, Case, When
from disa import settings
import os
from django.db.models import F, Count, CharField
from .views_API import query_apis_net_dni_ruc
from ..hrm.models import Subsidiary
from ..users.models import CustomUser


# Create your views here.

def get_client_list(request):
    if request.method == 'GET':
        client_set = Person.objects.filter(type='C').order_by('id')

        occupation_client_set = Person.objects.exclude(occupation__isnull=True).exclude(occupation=' ').exclude(occupation='')
        occupation_client_set = occupation_client_set.values('occupation').annotate(
            quantity_client=Count('id')).order_by('-quantity_client')

        occupation_name = [item['occupation'].upper() for item in occupation_client_set]

        return render(request, 'sales/client_list.html', {
            'client_set': client_set,
            'occupation_name': occupation_name,
            'quantity_occupation': [item['quantity_client'] for item in occupation_client_set],
        })


def modal_client_create(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('sales/client_new.html')
        c = ({
            'date_now': date_now,

        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def get_api_person(request):
    if request.method == 'GET':
        document_number = request.GET.get('nro_document')
        type_document = str(request.GET.get('type'))
        result = ''
        address = '-'
        first_name = ''
        second_name = ''
        paternal_name = ''
        maternal_name = ''
        client_obj = None
        client_set_search = Person.objects.filter(document=type_document, type='C', number=document_number)
        if client_set_search.exists():
            client_obj_search = client_set_search.last()
            if client_obj_search.address:
                address = client_obj_search.address
            client_id = client_obj_search.id
            names = client_obj_search.full_name
            first_name = client_obj_search.first_name
            second_name = client_obj_search.second_name
            surname = client_obj_search.surname
            second_surname = client_obj_search.second_surname
            phone1 = client_obj_search.phone1
            email = client_obj_search.email
            occupation = client_obj_search.occupation

            return JsonResponse({
                'pk': client_id,
                'names': names,
                'firstName': first_name,
                'secondName': second_name,
                'surname': surname,
                'secondSurname': second_surname,
                'phone1': phone1,
                'email': email,
                'occupation': occupation,
                'address': address,
                'message': 'Cliente encontrado en BD'
            },
                status=HTTPStatus.OK)

        else:
            if type_document == '01':
                type_name = 'DNI'
                r = query_apis_net_dni_ruc(document_number, type_name)
                name = r.get('nombres')
                paternal_name = r.get('apellidoPaterno')
                maternal_name = r.get('apellidoMaterno')
                if paternal_name is not None and len(paternal_name) > 0:

                    res = name.split()

                    if len(res) > 1:
                        if res[1] == 'DEL':
                            first_name = res[0] + ' ' + res[1] + ' ' + res[2]
                        else:
                            first_name = res[0]
                            second_name = res[1]
                    else:
                        first_name = res[0]

                    result = name + ' ' + paternal_name + ' ' + maternal_name

                    if len(result.strip()) != 0:
                        client_obj = Person(
                            full_name=result.upper(),
                            number=document_number,
                            document=type_document,
                            first_name=first_name,
                            second_name=second_name,
                            surname=paternal_name,
                            second_surname=maternal_name,
                        )
                        client_obj.save()

                    else:
                        data = {'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE'}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

                else:
                    data = {
                        'error': 'PROBLEMAS CON LA CONSULTA A LA RENIEC, FAVOR DE INTENTAR MAS TARDE O REGISTRE '
                                 'MANUALMENTE'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            elif type_document == '06':
                type_name = 'RUC'
                r = query_apis_net_dni_ruc(document_number, type_name)

                if r.get('numeroDocumento') == document_number:

                    business_name = r.get('nombre')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business

                    client_obj = Person(
                        full_name=result.upper(),
                        number=document_number,
                        address=address.upper(),
                        document=type_document,
                    )
                    client_obj.save()

                else:
                    data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

        return JsonResponse({
            'pk': client_obj.id,
            'names': result,
            'firstName': first_name,
            'secondName': second_name,
            'surname': paternal_name,
            'secondSurname': maternal_name,
            'address': address},
            status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


# registrar cliente
@csrf_exempt
def save_client(request):
    if request.method == 'POST':
        full_name = ''
        client_exist_id = request.POST.get('client-id', '')

        client_type_document = request.POST.get('type-client', '')
        client_number_document = request.POST.get('client-number', '')

        client_first_name = request.POST.get('first-name', '')
        client_second_name = request.POST.get('second-name', '')
        client_surname = request.POST.get('surname', '')
        client_second_surname = request.POST.get('second-surname', '')
        client_business_name = request.POST.get('business-name', '')

        client_address = request.POST.get('client-address', '')
        client_occupation = request.POST.get('client-occupation', '')
        client_email = request.POST.get('client-email', '')
        client_phone1 = request.POST.get('client-phone1', '')
        client_phone2 = request.POST.get('client-phone2', '')

        # Construir el nombre completo según el tipo de documento
        if client_type_document == '06':
            full_name = client_business_name
        elif client_type_document == '01':
            full_name = client_first_name.upper() + ' ' + client_second_name.upper() + ' ' + client_surname.upper() + ' ' + client_second_surname.upper()

        # Crear y guardar el cliente
        client_obj = Person(
            type='C',  # Cliente
            document=client_type_document,
            number=client_number_document,
            full_name=full_name.upper(),
            first_name=client_first_name.upper() if client_first_name else '',
            second_name=client_second_name.upper() if client_second_name else '',
            surname=client_surname.upper() if client_surname else '',
            second_surname=client_second_surname.upper() if client_second_surname else '',
            address=client_address.upper() if client_address else '',
            occupation=client_occupation.upper() if client_occupation else '',
            email=client_email,
            phone1=client_phone1,
        )
        client_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'Cliente registrado con éxito'
        }, status=HTTPStatus.OK)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def modal_client_update(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        client_obj = None
        if pk:
            client_obj = Person.objects.get(id=int(pk))
        t = loader.get_template('sales/client_edit.html')
        c = ({
            'client_obj': client_obj,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


@csrf_exempt
def update_client(request):
    if request.method == 'POST':
        _id = request.POST.get('client-id', '')
        client_obj = None
        full_name = ''
        
        if _id:
            try:
                client_obj = Person.objects.get(id=int(_id))
            except Person.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Cliente no encontrado'
                }, status=HTTPStatus.OK)
        
        if client_obj is None:
            return JsonResponse({
                'success': False,
                'message': 'Problemas al obtener el cliente'
            }, status=HTTPStatus.OK)

        client_type_document = request.POST.get('type-client', '')
        client_number_document = request.POST.get('client-number', '')
        client_first_name = request.POST.get('first-name', '')
        client_second_name = request.POST.get('second-name', '')
        client_surname = request.POST.get('surname', '')
        client_second_surname = request.POST.get('second-surname', '')
        client_business_name = request.POST.get('business-name', '')
        client_address = request.POST.get('client-address', '')
        client_occupation = request.POST.get('client-occupation', '')
        client_email = request.POST.get('client-email', '')
        client_phone1 = request.POST.get('client-phone1', '')
        client_phone2 = request.POST.get('client-phone2', '')

        # Construir el nombre completo según el tipo de documento
        if client_type_document == '06':
            full_name = client_business_name
        elif client_type_document == '01':
            full_name = client_first_name.upper() + ' ' + client_second_name.upper() + ' ' + client_surname.upper() + ' ' + client_second_surname.upper()

        # Actualizar los campos del cliente
        client_obj.document = client_type_document
        client_obj.number = client_number_document
        client_obj.first_name = client_first_name.upper() if client_first_name else ''
        client_obj.second_name = client_second_name.upper() if client_second_name else ''
        client_obj.surname = client_surname.upper() if client_surname else ''
        client_obj.second_surname = client_second_surname.upper() if client_second_surname else ''
        client_obj.full_name = full_name.upper()
        client_obj.phone1 = client_phone1
        client_obj.phone2 = client_phone2
        client_obj.email = client_email
        client_obj.address = client_address.upper() if client_address else ''
        client_obj.occupation = client_occupation.upper() if client_occupation else ''
        
        client_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'Datos actualizados correctamente',
        }, status=HTTPStatus.OK)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def order_client(request):
    if request.method == 'GET':
        search = request.GET.get('search')
        order = []
        if search:
            order_set = Order.objects.filter(client__full_name__icontains=search, type='C')
            for o in order_set:
                order.append({
                    'id': o.id,
                    'client': o.client.full_name,
                    'code': o.code,
                    'date': o.register_date.strftime("%d-%m-%Y")
                })
        return JsonResponse({
            'status': True,
            'order': order
        })


def get_order_by_client(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        order_dict = []
        if order_id:
            order_obj = Order.objects.get(id=int(order_id))
            order_item = {
                'id': order_obj.id,
                'code': order_obj.code,
                'correlative': str(order_obj.correlative).zfill(3),
                'type': order_obj.type,
                'date': order_obj.register_date,
                'coin': order_obj.coin,
                'way_to_pay': order_obj.way_to_pay,
                'district': order_obj.district,
                'type_plan': order_obj.type_plan,
                'type_construction_site': order_obj.type_construction_site,
                'land_area': order_obj.land_area,
                'covered_area_level': order_obj.covered_area_level,
                'nro_level_design': order_obj.nro_level_design,
                'nro_level_different': order_obj.nro_level_different,
                'total_area': order_obj.total_area,
                'discount': order_obj.discount,
                'subtotal': order_obj.subtotal,
                'igv': order_obj.igv,
                'total': order_obj.total,
                'subsidiary': order_obj.subsidiary.id,
                'client_document': order_obj.client.document,
                'client_number': order_obj.client.number,
                'client_name': order_obj.client.full_name,
                'client_address': order_obj.client.address,
                'client_phone': order_obj.client.phone1,
                'client_mail': order_obj.client.email,
                'type_file': order_obj.type_file.id,
                'user_id': order_obj.user.id,
                'user': order_obj.user.first_name,
                'details': []
            }
            for d in order_obj.orderdetail_set.all().order_by('id'):
                details = {
                    'id': d.id,
                    'code': d.code,
                    'include': d.include,
                    'quantity': d.quantity,
                    'price_unit': d.price_unit,
                    'specialty_text': d.specialty.name,
                    'specialty_id': d.specialty.id,
                    'specialty_element_text': d.specialty_element.name,
                    'specialty_element_id': d.specialty_element.id,
                }
                # for e in d.specialty.specialtyelement_set.all().order_by('id'):
                #     specialty_element = {
                #         'id': e.id,
                #         'code': e.code,
                #         'name': e.name,
                #         'unit': e.unit,
                #         'price': e.price,
                #     }
                #     details.get('specialty_element').append(specialty_element)
                order_item.get('details').append(details)
            order_dict.append(order_item)

            return JsonResponse({
                'success': True,
                'order': order_dict,
            }, status=HTTPStatus.OK, content_type="application/json")
        return JsonResponse({
            'success': False,
            'message': 'Problemas al obtener el cliente, intente nuevamente'
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion. Contactar con sistemas'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def create_client(request):
    """Vista para crear nuevo cliente desde el modal de órdenes"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            document = request.POST.get('document', '')
            number = request.POST.get('number', '')
            full_name = request.POST.get('full_name')
            address = request.POST.get('address', '')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            
            # Validaciones básicas - solo el nombre es obligatorio
            if not full_name:
                return JsonResponse({
                    'success': False,
                    'message': 'El campo Nombre Completo es obligatorio'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Si se proporciona documento y número, verificar si ya existe
            if document and number:
                existing_client = Person.objects.filter(document=document, number=number, type='C').first()
                if existing_client:
                    # Si ya existe, actualizar con los nuevos datos proporcionados
                    updated = False
                    
                    # Actualizar nombre si es diferente
                    if full_name and full_name.upper() != existing_client.full_name:
                        existing_client.full_name = full_name.upper()
                        updated = True
                    
                    # Actualizar dirección si se proporciona
                    if address and address.upper() != (existing_client.address or ''):
                        existing_client.address = address.upper()
                        updated = True
                    
                    # Actualizar teléfono si se proporciona
                    if phone and phone != (existing_client.phone1 or ''):
                        existing_client.phone1 = phone
                        updated = True
                    
                    # Actualizar email si se proporciona
                    if email and email != (existing_client.email or ''):
                        existing_client.email = email
                        updated = True
                    
                    # Guardar cambios si hubo actualizaciones
                    if updated:
                        existing_client.save()
                        message = f'Cliente existente actualizado con {document} número {number}'
                    else:
                        message = f'Cliente ya existe con {document} número {number} (sin cambios)'
                    
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'client': {
                            'id': existing_client.id,
                            'full_name': existing_client.full_name,
                            'document': existing_client.document,
                            'number': existing_client.number,
                            'address': existing_client.address or '',
                            'phone': existing_client.phone1 or '',
                            'email': existing_client.email or ''
                        },
                        'existing': True,
                        'updated': updated
                    }, status=HTTPStatus.OK)
            
            # Crear el cliente si no existe
            client_obj = Person(
                type='C',  # Cliente
                document=document if document else '',
                number=number if number else '',
                full_name=full_name.upper(),
                address=address.upper() if address else '',
                phone1=phone if phone else '',
                email=email if email else ''
            )
            client_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Cliente creado exitosamente',
                'client': {
                    'id': client_obj.id,
                    'full_name': client_obj.full_name,
                    'document': client_obj.document,
                    'number': client_obj.number,
                    'address': client_obj.address or '',
                    'phone': client_obj.phone1 or '',
                    'email': client_obj.email or ''
                },
                'existing': False
            }, status=HTTPStatus.OK)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al crear el cliente: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def search_clients_autocomplete(request):
    """Vista para autocompletado de clientes en filtros"""
    if request.method == 'GET':
        search_term = request.GET.get('search', '')
        
        if len(search_term) < 2:
            return JsonResponse({
                'success': False,
                'message': 'Término de búsqueda muy corto'
            }, status=HTTPStatus.BAD_REQUEST)
        
        try:
            # Buscar clientes por nombre o documento
            clients = Person.objects.filter(
                type='C'
            ).filter(
                Q(full_name__icontains=search_term) |
                Q(number__icontains=search_term)
            ).select_related().order_by('full_name')[:10]  # Limitar a 10 resultados
            
            client_list = []
            for client in clients:
                client_data = {
                    'id': client.id,
                    'full_name': client.full_name,
                    'document': client.document,
                    'number': client.number,
                    'address': client.address or '',
                    'phone': client.phone1 or '',
                    'email': client.email or ''
                }
                client_list.append(client_data)
            
            return JsonResponse({
                'success': True,
                'clients': client_list
            }, status=HTTPStatus.OK)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al buscar clientes: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def get_client_autocomplete(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')

        try:
            # Buscar clientes por nombre o documento
            client_set = Person.objects.filter(type='C').filter(id=client_id).select_related()

            if client_set.exists():
                client_obj = client_set.first()
                client_data = [{
                    'id': client_obj.id,
                    'full_name': client_obj.full_name,
                    'document': client_obj.document,
                    'number': client_obj.number,
                    'address': client_obj.address or '',
                    'phone': client_obj.phone1 or '',
                    'email': client_obj.email or ''
                }]
            else:
                client_data = []
            return JsonResponse({
                'success': True,
                'clients': client_data
            }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al buscar clientes: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)



