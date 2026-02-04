from django.db import models
from django.contrib.auth import get_user_model
from apps.hrm.models import Subsidiary
from apps.sales.models import Person
from apps.users.models import CustomUser
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, Adjust
import decimal

User = get_user_model()


class DestinationEntity(models.Model):
    """Entidades de destino para depósitos bancarios"""
    name = models.CharField('Nombre de la Entidad', max_length=100, unique=True)
    code = models.CharField('Código', max_length=20, unique=True)
    is_active = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField('Fecha de Creación', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de Actualización', auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Entidad de Destino'
        verbose_name_plural = 'Entidades de Destino'
        ordering = ['name']


class DepositOrder(models.Model):
    """Orden de depósito bancario"""
    STATUS_CHOICES = [
        ('P', 'Pendiente'),
        ('C', 'Confirmado'),
        ('A', 'Anulado'),
    ]
    
    TYPE_DEPOSIT_CHOICES = [
        ('DEP', 'DEPÓSITO'),
        ('PAG', 'PAGO'),
        ('LET', 'LETRA'),
    ]

    id = models.AutoField(primary_key=True)
    
    # Campos de numeración
    serial = models.CharField('Serie', max_length=10, null=True, blank=True)
    correlative = models.IntegerField(default=0)
    type_deposit = models.CharField('Tipo de Depósito', max_length=3, choices=TYPE_DEPOSIT_CHOICES, default='DEP')
    deposit_number = models.CharField('Número de Depósito', max_length=20, unique=True)
    
    # Campos del cajero
    cashier = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Cajero(a)', related_name='deposits_cashier')
    creation_date = models.DateTimeField('Fecha de Creación', auto_now_add=True)
    
    # Entidad de destino
    destination_entity = models.ForeignKey(DestinationEntity, on_delete=models.CASCADE, verbose_name='Entidad de Destino', related_name='deposits')
    
    # Sucursales
    origin_subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE, verbose_name='Sucursal de Origen', related_name='deposits_origin')
    subsidiary_encargada = models.ForeignKey(Subsidiary, on_delete=models.CASCADE, verbose_name='Sucursal Encargada', related_name='deposits_assigned', null=True, blank=True)
    
    # Cliente depositante
    depositor_client = models.ForeignKey(Person, on_delete=models.CASCADE, verbose_name='Cliente Depositante', related_name='deposits_made')
    
    # Titular receptor
    account_holder = models.CharField('Titular Receptor', max_length=200)
    account_number = models.CharField('Número de Cuenta', max_length=20)
    
    # Campos adicionales
    amount = models.DecimalField('Monto', max_digits=10, decimal_places=2)
    amount_in_words = models.CharField('Monto en Letras', max_length=500, null=True, blank=True)
    observation = models.CharField('Observación', max_length=500, null=True, blank=True, default='VOUCHER')
    
    # Sucursal de gestión
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE, verbose_name='Sucursal de Gestión', related_name='deposits_managed')
    
    # Estados y auditoría
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P')
    updated_at = models.DateTimeField('Fecha de Actualización', auto_now=True)
    confirmed_at = models.DateTimeField('Fecha de Confirmación', null=True, blank=True)
    confirmed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='deposits_confirmed', verbose_name='Confirmado por')

    photo = models.ImageField(upload_to='subsidiary/', default='vouchers/default-placeholder.png', blank=True)
    photo_thumbnail = ImageSpecField([Adjust(contrast=1.2, sharpness=1.1), ResizeToFill(100, 100)], source='photo',
                                     format='JPEG', options={'quality': 90})
    
    def __str__(self):
        return f"{self.serial}-{self.correlative:04d} - {self.depositor_client.full_name} - S/ {self.amount}"
    
    class Meta:
        verbose_name = 'Orden de Depósito'
        verbose_name_plural = 'Órdenes de Depósito'
        ordering = ['-creation_date']
        unique_together = ['serial', 'correlative']
    
    def get_amount_in_words(self):
        """Convierte el monto a palabras en español"""
        from .utils import number_to_words
        return number_to_words(self.amount)
    
    def get_series_prefix(self):
        """Obtiene el prefijo de serie basado en el tipo de depósito"""
        series_map = {
            'DEP': 'DEP',
            'PAG': 'PAG', 
            'LET': 'LET'
        }
        return series_map.get(self.type_deposit, 'DEP')
    
    def save(self, *args, **kwargs):
        if not self.amount_in_words:
            self.amount_in_words = self.get_amount_in_words()
        super().save(*args, **kwargs)


