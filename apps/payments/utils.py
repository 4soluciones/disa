"""
Utilidades para el sistema de pagos
"""

def number_to_words(number):
    """
    Convierte un número a palabras en español
    """
    if number == 0:
        return "CERO"
    
    # Separar parte entera y decimal
    integer_part = int(number)
    decimal_part = int((number - integer_part) * 100)
    
    # Convertir parte entera
    integer_words = _convert_integer_to_words(integer_part)
    
    # Convertir parte decimal
    if decimal_part > 0:
        decimal_words = _convert_integer_to_words(decimal_part)
        return f"{integer_words} CON {decimal_words}/100 SOLES"
    else:
        return f"{integer_words} SOLES"


def _convert_integer_to_words(number):
    """
    Convierte un entero a palabras en español
    """
    if number == 0:
        return "CERO"
    
    # Nombres de números del 0 al 19
    units = [
        "", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
        "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"
    ]
    
    # Nombres de decenas
    tens = [
        "", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"
    ]
    
    # Nombres de centenas
    hundreds = [
        "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
        "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"
    ]
    
    # Nombres de miles
    thousands = [
        "", "MIL", "MILLON", "MIL MILLONES"
    ]
    
    if number < 20:
        return units[number]
    elif number < 100:
        if number % 10 == 0:
            return tens[number // 10]
        else:
            return tens[number // 10] + " Y " + units[number % 10]
    elif number < 1000:
        if number == 100:
            return "CIEN"
        elif number % 100 == 0:
            return hundreds[number // 100]
        else:
            return hundreds[number // 100] + " " + _convert_integer_to_words(number % 100)
    elif number < 1000000:
        if number == 1000:
            return "MIL"
        elif number < 2000:
            return "MIL " + _convert_integer_to_words(number % 1000)
        else:
            thousands_part = _convert_integer_to_words(number // 1000)
            if number % 1000 == 0:
                return thousands_part + " MIL"
            else:
                return thousands_part + " MIL " + _convert_integer_to_words(number % 1000)
    else:
        # Para números mayores a un millón (simplificado)
        return "UN MILLON"


def generate_deposit_number():
    """
    Genera un número único para el depósito
    """
    from .models import DepositOrder
    from datetime import datetime
    
    # Obtener el último número de depósito del día
    today = datetime.now().date()
    last_deposit = DepositOrder.objects.filter(
        created_at__date=today
    ).order_by('-deposit_number').first()
    
    if last_deposit:
        # Extraer el número secuencial y incrementarlo
        try:
            last_number = int(last_deposit.deposit_number.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    # Formato: DEP-YYYYMMDD-XXXX
    return f"DEP-{today.strftime('%Y%m%d')}-{new_number:04d}"


def generate_letter_number():
    """
    Genera un número único para la letra
    """
    from .models import LetterOrder
    from datetime import datetime
    
    # Obtener el último número de letra del día
    today = datetime.now().date()
    last_letter = LetterOrder.objects.filter(
        created_at__date=today
    ).order_by('-letter_number').first()
    
    if last_letter:
        # Extraer el número secuencial y incrementarlo
        try:
            last_number = int(last_letter.letter_number.split('-')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1
    
    # Formato: LET-YYYYMMDD-XXXX
    return f"LET-{today.strftime('%Y%m%d')}-{new_number:04d}"


def get_series_prefix(type_deposit):
    """
    Obtiene el prefijo de serie basado en el tipo de depósito
    """
    series_map = {
        'DEP': 'DEP',
        'PAG': 'PAG', 
        'LET': 'LET'
    }
    return series_map.get(type_deposit, 'DEP')


def get_next_correlative(type_deposit, subsidiary=None):
    """
    Obtiene el siguiente correlativo para el tipo de depósito y sucursal
    """
    from .models import DepositOrder
    
    # Filtrar por tipo de depósito
    deposits = DepositOrder.objects.filter(type_deposit=type_deposit)
    
    # Si se especifica sucursal, filtrar también por sucursal
    if subsidiary:
        deposits = deposits.filter(subsidiary=subsidiary)
    
    # Obtener el último correlativo
    last_deposit = deposits.order_by('-correlative').first()
    
    if last_deposit:
        return last_deposit.correlative + 1
    else:
        return 1


def generate_deposit_serial(type_deposit, subsidiary=None):
    """
    Genera la serie completa para un depósito
    """
    prefix = get_series_prefix(type_deposit)
    correlative = get_next_correlative(type_deposit, subsidiary)
    
    # Formato: PREFIX-XXXX
    return f"{prefix}-{correlative:04d}"
