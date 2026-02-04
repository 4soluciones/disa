from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
from django.db.models import Q, Sum, Count
from django.contrib.auth.decorators import login_required
from http import HTTPStatus
import json
import decimal
from datetime import datetime
import pytz
from .models import *

from .models import DepositOrder, DestinationEntity
from apps.sales.models import Person
from apps.hrm.models import Subsidiary
from apps.users.models import CustomUser
from apps.accounting.models import Cash, CashFlow


def deposit_order_list(request):
    """Vista principal del listado de depósitos"""
    if request.method == 'GET':
        subsidiary_set = Subsidiary.objects.all()
        user_set = CustomUser.objects.filter(is_active=True, is_staff=False)
        peru_tz = pytz.timezone('America/Lima')
        my_date = datetime.now(peru_tz)
        date_now = my_date.strftime("%Y-%m-%d")
        
        return render(request, 'payments/deposit_order_list.html', {
            'subsidiary_set': subsidiary_set,
            'user_set': user_set,
            'date_now': date_now,
        })
    elif request.method == 'POST':
        try:
            # Filtrar depósitos según parámetros
            subsidiary_id = request.POST.get('subsidiary')
            user_id = request.POST.get('user')
            status = request.POST.get('status')
            date_from = request.POST.get('date_from')
            date_to = request.POST.get('date_to')
            client_id_filter = request.POST.get('client_id_filter')
            deposit_number_search = request.POST.get('deposit_number_search')
            
            deposits = DepositOrder.objects.all().order_by('id')
        
            # Si hay búsqueda por número de depósito, ignoramos los otros filtros (sucursal, cajero, estado, cliente)
            if not deposit_number_search or not deposit_number_search.strip():
                if subsidiary_id and subsidiary_id != '0':
                    deposits = deposits.filter(subsidiary_id=subsidiary_id)
                if user_id and user_id != '0':
                    deposits = deposits.filter(cashier_id=user_id)
                if status and status != '0':
                    deposits = deposits.filter(status=status)
                if client_id_filter and client_id_filter != '':
                    deposits = deposits.filter(depositor_client_id=client_id_filter)
            if deposit_number_search and deposit_number_search.strip():
                deposits = deposits.filter(deposit_number__icontains=deposit_number_search.strip())

            # Filtros de fecha - Si no se especifican fechas y no hay búsqueda de número de depósito, cargar solo del día actual
            if not deposit_number_search or not deposit_number_search.strip():
                if not date_from and not date_to:
                    # Usar zona horaria de Perú (GMT-5)
                    peru_tz = pytz.timezone('America/Lima')
                    current_date = datetime.now(peru_tz).strftime('%Y-%m-%d')
                    date_from = current_date
                    date_to = current_date
                    deposits = deposits.filter(creation_date__date=current_date)
                else:
                    if date_from:
                        deposits = deposits.filter(creation_date__date__gte=date_from)
                    if date_to:
                        deposits = deposits.filter(creation_date__date__lte=date_to)
            else:
                # Si hay búsqueda por número de depósito, NO aplicamos filtros de fecha para que la búsqueda sea global (independiente)
                pass

            deposits = deposits.select_related('depositor_client', 'cashier', 'subsidiary', 'origin_subsidiary', 'subsidiary_encargada', 'confirmed_by', 'destination_entity').order_by('-creation_date')

            # Obtener la sucursal del usuario actual
            user_subsidiary = request.user.subsidiary if hasattr(request.user, 'subsidiary') and request.user.subsidiary else None
            
            # Crear diccionario con datos de cada depósito
            deposit_dict = []
            for deposit in deposits:
                # Determinar si el usuario es de la sucursal de origen o destino
                is_origin_subsidiary = user_subsidiary and deposit.origin_subsidiary and user_subsidiary.id == deposit.origin_subsidiary.id
                is_destination_subsidiary = user_subsidiary and deposit.subsidiary_encargada and user_subsidiary.id == deposit.subsidiary_encargada.id
                
                deposit_data = {
                    'id': deposit.id,
                    'deposit': deposit,
                    'serial': deposit.serial,
                    'correlative': deposit.correlative,
                    'deposit_number': deposit.deposit_number,
                    'type_deposit': deposit.type_deposit,
                    'type_deposit_display': deposit.get_type_deposit_display(),
                    'creation_date': deposit.creation_date,
                    'status': deposit.status,
                    'status_display': deposit.get_status_display(),
                    'depositor_client': deposit.depositor_client.full_name if deposit.depositor_client else 'Sin Cliente',
                    'depositor_client_document': deposit.depositor_client.get_document_display() if deposit.depositor_client else '',
                    'depositor_client_number': deposit.depositor_client.number if deposit.depositor_client else '',
                    'depositor_client_phone': deposit.depositor_client.phone if deposit.depositor_client and hasattr(deposit.depositor_client, 'phone') else '',
                    'cashier': deposit.cashier.first_name if deposit.cashier else '',
                    'destination_entity': deposit.destination_entity.name if deposit.destination_entity else '',
                    'destination_entity_display': deposit.destination_entity.name if deposit.destination_entity else '',
                    'account_holder': deposit.account_holder,
                    'account_number': deposit.account_number,
                    'amount': str(round(deposit.amount, 2)),
                    'amount_in_words': deposit.amount_in_words,
                    'observation': deposit.observation,
                    'subsidiary': deposit.subsidiary.name if deposit.subsidiary else '',
                    'origin_subsidiary': deposit.origin_subsidiary.name if deposit.origin_subsidiary else '',
                    'destination_subsidiary': deposit.subsidiary_encargada.name if deposit.subsidiary_encargada else '',
                    'is_origin_subsidiary': is_origin_subsidiary,
                    'is_destination_subsidiary': is_destination_subsidiary,
                    'can_change_status': is_destination_subsidiary,  # Solo la sucursal destino puede cambiar el estado
                    'confirmed_by': deposit.confirmed_by.first_name if deposit.confirmed_by else None,
                    'confirmed_at': deposit.confirmed_at,
                }
                deposit_dict.append(deposit_data)

            # Calcular totales del período
            total_amount = deposits.aggregate(total=Sum('amount'))['total'] or 0
            total_deposits = deposits.count()
            confirmed_deposits = deposits.filter(status='C').count()
            pending_deposits = deposits.filter(status='P').count()

            tpl = loader.get_template('payments/deposit_order_grid.html')
            context = {
                'deposit_dict': deposit_dict,
                'total_amount': total_amount,
                'total_deposits': total_deposits,
                'confirmed_deposits': confirmed_deposits,
                'pending_deposits': pending_deposits,
                'date_from': date_from,
                'date_to': date_to
            }

            return JsonResponse({
                'grid': tpl.render(context, request),
            }, status=HTTPStatus.OK)
        
        except Exception as e:
            print(e)
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar los depósitos: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)


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


def modal_deposit_create(request):
    if request.method == 'GET':
        my_date = datetime.now()
        user_id = request.user.id
        user_obj = CustomUser.objects.get(id=int(user_id))
        destination_entities = DestinationEntity.objects.filter(is_active=True).order_by('name')

        t = loader.get_template('payments/deposit_order_new.html')
        c = ({
            'subsidiary_set': Subsidiary.objects.all(),
            'user': user_obj,
            'destination_entities': destination_entities,
            'my_date': my_date,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


@csrf_exempt
def deposit_save(request):
    """Vista para guardar nuevo depósito"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            type_deposit = request.POST.get('type_deposit')
            depositor_client_id = request.POST.get('depositor_client_id')
            destination_entity = request.POST.get('destination_entity')
            account_holder = request.POST.get('account_holder')
            account_number = request.POST.get('account_number')
            amount = request.POST.get('amount')
            origin_subsidiary_id = request.POST.get('origin_subsidiary_id')
            subsidiary_encargada_id = request.POST.get('subsidiary_encargada_id')
            observation = request.POST.get('observation', 'VOUCHER')
            
            # Validaciones básicas
            if not all([type_deposit, depositor_client_id, destination_entity, account_holder, account_number, amount, origin_subsidiary_id]):
                return JsonResponse({
                    'success': False,
                    'message': 'Faltan datos obligatorios'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Obtener objetos relacionados
            depositor_client_obj = Person.objects.get(id=int(depositor_client_id))
            origin_subsidiary_obj = Subsidiary.objects.get(id=int(origin_subsidiary_id))
            
            # Validar que la sucursal encargada no sea la misma que la de origen
            if subsidiary_encargada_id and int(subsidiary_encargada_id) == int(origin_subsidiary_id):
                return JsonResponse({
                    'success': False,
                    'message': 'La sucursal encargada no puede ser la misma que la sucursal de origen'
                }, status=HTTPStatus.BAD_REQUEST)
            
            subsidiary_encargada_obj = Subsidiary.objects.get(id=int(subsidiary_encargada_id)) if subsidiary_encargada_id else None
            if not subsidiary_encargada_obj:
                return JsonResponse({
                    'success': False,
                    'message': 'Debe seleccionar una sucursal encargada diferente a la de origen'
                }, status=HTTPStatus.BAD_REQUEST)
            
            destination_entity_obj = DestinationEntity.objects.get(id=int(destination_entity))
            
            # Validar apertura de caja en la sucursal de origen
            # Obtener la cuenta de caja principal de la sucursal de origen
            origin_cash_accounts = Cash.objects.filter(subsidiary=origin_subsidiary_obj, currency_type='S').order_by('id')
            if not origin_cash_accounts.exists():
                return JsonResponse({
                    'success': False,
                    'message': f'No existe una cuenta de caja configurada para la sucursal {origin_subsidiary_obj.name}'
                }, status=HTTPStatus.BAD_REQUEST)
            
            origin_cash = origin_cash_accounts.first()
            
            # Verificar que la caja esté abierta para el día actual
            from datetime import datetime
            current_date = datetime.now().date()
            opening_exists = CashFlow.objects.filter(
                cash=origin_cash,
                type='A',
                transaction_date__date=current_date
            ).exists()
            
            if not opening_exists:
                return JsonResponse({
                    'success': False,
                    'message': f'Debe abrir la caja del día para la sucursal {origin_subsidiary_obj.name} antes de crear una orden de depósito'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Actualizar teléfono del cliente si se proporcionó y es diferente
            depositor_client_phone = request.POST.get('depositor_client_phone', '').strip()
            if depositor_client_phone:
                # Actualizar el teléfono del cliente si ha cambiado
                if depositor_client_obj.phone1 != depositor_client_phone:
                    depositor_client_obj.phone1 = depositor_client_phone
                    depositor_client_obj.save(update_fields=['phone1'])
            
            # Generar serial y correlativo usando la función
            serial_result = generate_serial_and_correlative(type_deposit, origin_subsidiary_obj)
            
            if not serial_result['success']:
                return JsonResponse({
                    'success': False,
                    'message': serial_result['message']
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            
            serial = serial_result['serial']
            new_correlative = serial_result['correlative']
            deposit_number = serial_result['deposit_number']
            
            # Crear el depósito
            deposit_obj = DepositOrder(
                serial=serial,
                correlative=new_correlative,
                type_deposit=type_deposit,
                deposit_number=deposit_number,
                cashier=request.user,
                destination_entity=destination_entity_obj,
                origin_subsidiary=origin_subsidiary_obj,
                subsidiary_encargada=subsidiary_encargada_obj,
                depositor_client=depositor_client_obj,
                account_holder=account_holder.upper(),
                account_number=account_number,
                amount=decimal.Decimal(amount),
                observation=observation.upper(),
                subsidiary=origin_subsidiary_obj,
                status='P'
            )
            deposit_obj.save()
            
            # Crear registro en CashFlow como ENTRADA en la caja de origen
            try:
                cashflow_entry = CashFlow.objects.create(
                    transaction_date=datetime.now(),
                    created_at=datetime.now(),
                    description=f"{deposit_obj.get_type_deposit_display()} {deposit_number} - {depositor_client_obj.full_name}",
                    type='E',  # Entrada
                    subtotal=decimal.Decimal('0.00'),
                    total=decimal.Decimal(amount),
                    igv=decimal.Decimal('0.00'),
                    cash=origin_cash,
                    user=request.user,
                    document_type_attached='O'
                )
            except Exception as e:
                # Si falla la creación de CashFlow, registrar el error pero no fallar la operación
                print(f"Error al crear registros en CashFlow: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': f'Depósito {deposit_obj.get_type_deposit_display()} registrado correctamente',
                'deposit_id': deposit_obj.id,
                'deposit_number': deposit_obj.deposit_number,
                'last_correlative': new_correlative,
                'download_pdf': True  # Indicar que se debe descargar el PDF
            }, status=HTTPStatus.OK)
            
        except Person.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cliente no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Subsidiary.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Sucursal no encontrada'
            }, status=HTTPStatus.NOT_FOUND)
        except DestinationEntity.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Entidad de destino no encontrada'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al registrar el depósito: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def deposit_update(request):
    """Vista para actualizar depósito existente"""
    if request.method == 'POST':
        try:
            deposit_id = request.POST.get('deposit_id')
            if not deposit_id:
                return JsonResponse({
                    'success': False,
                    'message': 'ID de depósito no proporcionado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            deposit_obj = DepositOrder.objects.get(id=int(deposit_id))
            
            # Obtener IDs de sucursales
            origin_subsidiary_id = request.POST.get('origin_subsidiary_id')
            subsidiary_encargada_id = request.POST.get('subsidiary_encargada_id')
            
            # Validar que la sucursal encargada no sea la misma que la de origen
            if subsidiary_encargada_id and origin_subsidiary_id and int(subsidiary_encargada_id) == int(origin_subsidiary_id):
                return JsonResponse({
                    'success': False,
                    'message': 'La sucursal encargada no puede ser la misma que la sucursal de origen'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Actualizar campos básicos
            deposit_obj.type_deposit = request.POST.get('type_deposit', deposit_obj.type_deposit)
            deposit_obj.depositor_client_id = request.POST.get('depositor_client_id')
            
            # Actualizar entidad de destino
            destination_entity_id = request.POST.get('destination_entity')
            if destination_entity_id:
                deposit_obj.destination_entity_id = destination_entity_id
            
            deposit_obj.account_holder = request.POST.get('account_holder', '').upper()
            deposit_obj.account_number = request.POST.get('account_number')
            deposit_obj.amount = decimal.Decimal(request.POST.get('amount', 0))
            deposit_obj.origin_subsidiary_id = origin_subsidiary_id
            deposit_obj.subsidiary_encargada_id = subsidiary_encargada_id if subsidiary_encargada_id else None
            deposit_obj.observation = request.POST.get('observation', 'VOUCHER').upper()
            
            # Actualizar teléfono del cliente si se proporcionó y es diferente
            depositor_client_phone = request.POST.get('depositor_client_phone', '').strip()
            if depositor_client_phone and deposit_obj.depositor_client:
                # Actualizar el teléfono del cliente si ha cambiado
                if deposit_obj.depositor_client.phone1 != depositor_client_phone:
                    deposit_obj.depositor_client.phone1 = depositor_client_phone
                    deposit_obj.depositor_client.save(update_fields=['phone1'])
            
            deposit_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Depósito actualizado correctamente'
            }, status=HTTPStatus.OK)
            
        except DepositOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Depósito no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar el depósito: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def get_deposit_for_edit(request):
    """Vista para obtener datos de un depósito para edición en el modal"""
    if request.method == 'GET':
        deposit_id = request.GET.get('deposit_id')
        if deposit_id:
            try:
                deposit_obj = DepositOrder.objects.select_related(
                    'depositor_client', 'cashier', 'origin_subsidiary', 'subsidiary_encargada', 'destination_entity'
                ).get(id=int(deposit_id))
                
                # Preparar datos del depósito
                depositor_client = deposit_obj.depositor_client
                deposit_data = {
                    'id': deposit_obj.id,
                    'serial': deposit_obj.serial,
                    'correlative': str(deposit_obj.correlative).zfill(4),
                    'type_deposit': deposit_obj.type_deposit,
                    'deposit_number': deposit_obj.deposit_number,
                    'depositor_client_id': depositor_client.id if depositor_client else None,
                    'depositor_client_name': depositor_client.full_name if depositor_client else '',
                    'depositor_client_document': depositor_client.document if depositor_client else None,
                    'depositor_client_number': depositor_client.number if depositor_client else None,
                    'depositor_client_phone': depositor_client.phone1 if depositor_client else '',
                    'destination_entity': deposit_obj.destination_entity.id if deposit_obj.destination_entity else None,
                    'account_holder': deposit_obj.account_holder,
                    'account_number': deposit_obj.account_number,
                    'amount': float(deposit_obj.amount),
                    'origin_subsidiary_id': deposit_obj.origin_subsidiary.id if deposit_obj.origin_subsidiary else None,
                    'origin_subsidiary_name': deposit_obj.origin_subsidiary.name if deposit_obj.origin_subsidiary else '',
                    'subsidiary_encargada_id': deposit_obj.subsidiary_encargada.id if deposit_obj.subsidiary_encargada else None,
                    'observation': deposit_obj.observation or '',
                    'status': deposit_obj.status,
                }
                
                return JsonResponse({
                    'success': True,
                    'deposit': deposit_data
                }, status=HTTPStatus.OK)
                
            except DepositOrder.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Depósito no encontrado'
                }, status=HTTPStatus.NOT_FOUND)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al cargar el depósito: {str(e)}'
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        
        return JsonResponse({
            'success': False,
            'message': 'ID de depósito no proporcionado'
        }, status=HTTPStatus.BAD_REQUEST)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def search_clients(request):
    """Vista para búsqueda de clientes con autocompletado"""
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


@csrf_exempt
def create_client(request):
    """Vista para crear nuevo cliente desde el modal de depósitos"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            full_name = request.POST.get('full_name')
            document = request.POST.get('document', '')
            number = request.POST.get('number', '')
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
            if number:
                existing_client = Person.objects.filter(number=number, type='C').first()
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
                        message = f'Cliente existente actualizado con documento {number}'
                    else:
                        message = f'Cliente ya existe con documento {number} (sin cambios)'
                    
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


def generate_serial_and_correlative(type_deposit, subsidiary_obj):
    """Función para generar serial y correlativo para un depósito"""
    try:
        # Obtener el último correlativo para el tipo de depósito y sucursal
        last_deposit = DepositOrder.objects.filter(
            type_deposit=type_deposit,
            subsidiary=subsidiary_obj
        ).order_by('-correlative').first()
        
        if last_deposit:
            new_correlative = last_deposit.correlative + 1
        else:
            new_correlative = 1
        
        # Generar serie
        series_prefix = {
            'DEP': 'DEP',
            'PAG': 'PAG', 
            'LET': 'LET'
        }.get(type_deposit, 'DEP')
        
        # serial = f"{series_prefix}-{subsidiary_obj.serial:02d}"
        serial = f"{series_prefix}-{subsidiary_obj.serial}"

        deposit_number = f"{serial}-{new_correlative:04d}"
        
        return {
            'success': True,
            'serial': serial,
            'correlative': new_correlative,
            'deposit_number': deposit_number
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error al generar serial: {str(e)}'
        }


def get_next_serial(request):
    """Vista para obtener el siguiente serial y correlativo"""
    if request.method == 'GET':
        type_deposit = request.GET.get('type_deposit', 'DEP')
        subsidiary_id = request.GET.get('subsidiary_id', '')
        
        if not subsidiary_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de sucursal no proporcionado'
            }, status=HTTPStatus.BAD_REQUEST)
        
        try:
            subsidiary_obj = Subsidiary.objects.get(id=int(subsidiary_id))
            result = generate_serial_and_correlative(type_deposit, subsidiary_obj)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'serial': result['serial'],
                    'correlative': str(result['correlative']).zfill(4),
                    'deposit_number': result['deposit_number']
                }, status=HTTPStatus.OK)
            else:
                return JsonResponse({
                    'success': False,
                    'message': result['message']
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            
        except Subsidiary.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Sucursal no encontrada'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al obtener serial: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def deposit_confirm(request):
    """Vista para confirmar un depósito"""
    if request.method == 'POST':
        try:
            deposit_id = request.POST.get('deposit_id')
            if not deposit_id:
                return JsonResponse({
                    'success': False,
                    'message': 'ID de depósito no proporcionado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            deposit_obj = DepositOrder.objects.get(id=int(deposit_id))
            
            # Verificar que el depósito no esté ya confirmado
            if deposit_obj.status == 'C':
                return JsonResponse({
                    'success': False,
                    'message': 'El depósito ya está confirmado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Verificar que el depósito no esté anulado
            if deposit_obj.status == 'A':
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede confirmar un depósito anulado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Confirmar el depósito
            deposit_obj.status = 'C'
            deposit_obj.confirmed_by = request.user
            deposit_obj.confirmed_at = datetime.now()
            deposit_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Depósito {deposit_obj.deposit_number} confirmado exitosamente por {request.user.first_name} {request.user.last_name}'
            }, status=HTTPStatus.OK)
            
        except DepositOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Depósito no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al confirmar el depósito: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def deposit_cancel(request):
    """Vista para anular un depósito"""
    if request.method == 'POST':
        try:
            deposit_id = request.POST.get('deposit_id')
            cancellation_reason = request.POST.get('cancellation_reason', '')
            
            if not deposit_id:
                return JsonResponse({
                    'success': False,
                    'message': 'ID de depósito no proporcionado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            if not cancellation_reason.strip():
                return JsonResponse({
                    'success': False,
                    'message': 'Debe proporcionar el motivo de la anulación'
                }, status=HTTPStatus.BAD_REQUEST)
            
            deposit_obj = DepositOrder.objects.get(id=int(deposit_id))
            
            # Verificar que el depósito no esté ya anulado
            if deposit_obj.status == 'A':
                return JsonResponse({
                    'success': False,
                    'message': 'El depósito ya está anulado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Verificar que el depósito no esté confirmado
            if deposit_obj.status == 'C':
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede anular un depósito confirmado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Anular el depósito
            deposit_obj.status = 'A'
            deposit_obj.observation = f"{deposit_obj.observation} - ANULADO: {cancellation_reason}"
            deposit_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Depósito {deposit_obj.deposit_number} anulado exitosamente. Motivo: {cancellation_reason}'
            }, status=HTTPStatus.OK)
            
        except DepositOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Depósito no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al anular el depósito: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def modal_entities(request):
    if request.method == 'GET':
        try:
            entities_list = get_destination_entity_list()

            t = loader.get_template('payments/destination_entity_modal.html')

            c = ({
                'entities': entities_list
            })

            return JsonResponse({
                'form': t.render(c, request),
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar entidades: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def get_destination_entity_list():
    entities = DestinationEntity.objects.all().order_by('id')
    entities_list = []

    for entity in entities:
        entity_data = {
            'id': entity.id,
            'name': entity.name,
            'code': entity.code,
            'is_active': entity.is_active,
            'created_at': entity.created_at.strftime('%d/%m/%Y %H:%M'),
            'updated_at': entity.updated_at.strftime('%d/%m/%Y %H:%M'),
        }
        entities_list.append(entity_data)

    return entities_list


def destination_entity_list(request):
    if request.method == 'GET':
        try:
            entities_list = get_destination_entity_list()

            return JsonResponse({
                'success': True,
                'entities': entities_list
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar entidades: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def destination_entity_save(request):
    """Vista para crear o actualizar entidad de destino"""
    if request.method == 'POST':
        try:
            entity_id = request.POST.get('entity_id')
            name = request.POST.get('name', '').strip().upper()
            code = request.POST.get('code', '').strip().upper()
            is_active = True if request.POST.get('is_active') == 'on' else False

            # Validaciones
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'El nombre es obligatorio'
                }, status=HTTPStatus.BAD_REQUEST)
            
            if not code:
                return JsonResponse({
                    'success': False,
                    'message': 'El código es obligatorio'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Verificar si el código ya existe (excluyendo el registro actual si es edición)
            existing_entity = DestinationEntity.objects.filter(code=code)
            if entity_id:
                existing_entity = existing_entity.exclude(id=entity_id)
            
            if existing_entity.exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Ya existe una entidad con el código "{code}"'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Verificar si el nombre ya existe (excluyendo el registro actual si es edición)
            existing_name = DestinationEntity.objects.filter(name__iexact=name)
            if entity_id:
                existing_name = existing_name.exclude(id=entity_id)
            
            if existing_name.exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Ya existe una entidad con el nombre "{name}"'
                }, status=HTTPStatus.BAD_REQUEST)
            
            if entity_id:
                # Actualizar entidad existente
                entity = DestinationEntity.objects.get(id=int(entity_id))
                entity.name = name
                entity.code = code
                entity.is_active = is_active
                entity.save()
                
                message = f'Entidad "{name}" actualizada correctamente'
            else:
                # Crear nueva entidad
                entity = DestinationEntity.objects.create(
                    name=name,
                    code=code,
                    is_active=is_active
                )
                message = f'Entidad "{name}" creada correctamente'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'entity': {
                    'id': entity.id,
                    'name': entity.name,
                    'code': entity.code,
                    'is_active': entity.is_active,
                    'created_at': entity.created_at.strftime('%d/%m/%Y %H:%M'),
                    'updated_at': entity.updated_at.strftime('%d/%m/%Y %H:%M'),
                }
            }, status=HTTPStatus.OK)
            
        except DestinationEntity.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Entidad no encontrada'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al guardar la entidad: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def destination_entity_get(request):
    """Vista para obtener datos de una entidad específica"""
    if request.method == 'GET':
        entity_id = request.GET.get('entity_id')
        if entity_id:
            try:
                entity = DestinationEntity.objects.get(id=int(entity_id))
                
                entity_data = {
                    'id': entity.id,
                    'name': entity.name,
                    'code': entity.code,
                    'is_active': entity.is_active,
                    'created_at': entity.created_at.strftime('%d/%m/%Y %H:%M'),
                    'updated_at': entity.updated_at.strftime('%d/%m/%Y %H:%M'),
                }
                
                return JsonResponse({
                    'success': True,
                    'entity': entity_data
                }, status=HTTPStatus.OK)
                
            except DestinationEntity.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Entidad no encontrada'
                }, status=HTTPStatus.NOT_FOUND)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al cargar la entidad: {str(e)}'
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        
        return JsonResponse({
            'success': False,
            'message': 'ID de entidad no proporcionado'
        }, status=HTTPStatus.BAD_REQUEST)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def update_deposit_status(request):
    """Vista para actualizar el estado de un depósito"""
    if request.method == 'POST':
        try:
            deposit_id = request.POST.get('deposit_id')
            status = request.POST.get('status')
            reason = request.POST.get('reason', '')
            
            if not deposit_id or not status:
                return JsonResponse({
                    'success': False,
                    'message': 'ID de depósito y estado son obligatorios'
                }, status=HTTPStatus.BAD_REQUEST)
            
            deposit_obj = DepositOrder.objects.get(id=int(deposit_id))
            
            # Validar transiciones de estado
            if deposit_obj.status == 'C' and status != 'C':
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede cambiar el estado de un depósito confirmado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            if deposit_obj.status == 'A' and status != 'A':
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede cambiar el estado de un depósito anulado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Actualizar estado
            deposit_obj.status = status
            
            if status == 'A' and reason:
                deposit_obj.observation = f"{deposit_obj.observation} - ANULADO: {reason}"
            
            deposit_obj.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Estado del depósito {deposit_obj.deposit_number} actualizado a {deposit_obj.get_status_display()}'
            }, status=HTTPStatus.OK)
            
        except DepositOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Depósito no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al actualizar el estado: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def confirm_deposit(request):
    """Vista para confirmar un depósito con usuario y foto"""
    if request.method == 'POST':
        try:
            deposit_id = request.POST.get('deposit_id')
            confirmed_by_id = request.POST.get('confirmed_by')
            observation = request.POST.get('observation', '')
            
            if not deposit_id or not confirmed_by_id:
                return JsonResponse({
                    'success': False,
                    'message': 'ID de depósito y usuario confirmador son obligatorios'
                }, status=HTTPStatus.BAD_REQUEST)
            
            deposit_obj = DepositOrder.objects.get(id=int(deposit_id))
            confirmed_by_obj = CustomUser.objects.get(id=int(confirmed_by_id))
            
            # Verificar que el depósito no esté ya confirmado
            if deposit_obj.status == 'C':
                return JsonResponse({
                    'success': False,
                    'message': 'El depósito ya está confirmado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Verificar que el depósito no esté anulado
            if deposit_obj.status == 'A':
                return JsonResponse({
                    'success': False,
                    'message': 'No se puede confirmar un depósito anulado'
                }, status=HTTPStatus.BAD_REQUEST)
            
            # Actualizar depósito
            deposit_obj.status = 'C'
            deposit_obj.confirmed_by = confirmed_by_obj
            deposit_obj.confirmed_at = datetime.now()
            
            if observation:
                deposit_obj.observation = f"{deposit_obj.observation} - CONFIRMADO: {observation}"
            
            # Manejar foto si se subió
            if 'photo' in request.FILES:
                deposit_obj.photo = request.FILES['photo']
            
            deposit_obj.save()
            
            # Registrar SALIDA en la caja de la sucursal de destino al confirmar
            try:
                # Obtener la cuenta de caja de la sucursal encargada (destino)
                destination_cash_accounts = Cash.objects.filter(
                    subsidiary=deposit_obj.subsidiary_encargada,
                    currency_type='S'
                ).order_by('id')
                
                if destination_cash_accounts.exists():
                    destination_cash = destination_cash_accounts.first()
                    
                    # Crear registro de SALIDA en la sucursal de destino
                    cashflow_exit = CashFlow.objects.create(
                        transaction_date=datetime.now(),
                        created_at=datetime.now(),
                        description=f"CONFIRMACIÓN {deposit_obj.get_type_deposit_display()} {deposit_obj.deposit_number} - {deposit_obj.depositor_client.full_name}",
                        type='S',  # Salida
                        subtotal=decimal.Decimal('0.00'),
                        total=deposit_obj.amount,
                        igv=decimal.Decimal('0.00'),
                        cash=destination_cash,
                        user=confirmed_by_obj,
                        document_type_attached='O'
                    )
            except Exception as e:
                # Si falla la creación de CashFlow, registrar el error pero no fallar la operación
                print(f"Error al crear registro de CashFlow en confirmación: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': f'Depósito {deposit_obj.deposit_number} confirmado exitosamente por {confirmed_by_obj.first_name} {confirmed_by_obj.last_name}'
            }, status=HTTPStatus.OK)
            
        except DepositOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Depósito no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Usuario no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al confirmar el depósito: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def view_deposit(request):
    """Vista para mostrar los detalles de un depósito"""
    if request.method == 'GET':
        deposit_id = request.GET.get('deposit_id')
        if deposit_id:
            try:
                deposit_obj = DepositOrder.objects.select_related(
                    'depositor_client', 'cashier', 'origin_subsidiary', 'subsidiary_encargada', 
                    'destination_entity', 'confirmed_by', 'subsidiary'
                ).get(id=int(deposit_id))
                
                t = loader.get_template('payments/deposit_details.html')
                context = {
                    'deposit': deposit_obj,
                }
                
                return JsonResponse({
                    'success': True,
                    'html': t.render(context, request)
                }, status=HTTPStatus.OK)
                
            except DepositOrder.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Depósito no encontrado'
                }, status=HTTPStatus.NOT_FOUND)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al cargar el depósito: {str(e)}'
                }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        
        return JsonResponse({
            'success': False,
            'message': 'ID de depósito no proporcionado'
        }, status=HTTPStatus.BAD_REQUEST)
    
    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)
