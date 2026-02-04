from django import forms
from django.utils import timezone
from .models import PaymentService, DepositOrder, LetterOrder
from apps.sales.models import Person
from apps.hrm.models import Subsidiary


class PaymentServiceForm(forms.ModelForm):
    class Meta:
        model = PaymentService
        fields = ['service_type', 'client', 'amount', 'observation']
        widgets = {
            'service_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'client': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'observation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo clientes
        self.fields['client'].queryset = Person.objects.filter(type='C').order_by('full_name')


class DepositOrderForm(forms.ModelForm):
    class Meta:
        model = DepositOrder
        fields = [
            'type_deposit', 'destination_entity', 'origin_subsidiary', 'subsidiary_encargada',
            'depositor_client', 'account_holder', 'account_number', 'amount', 'observation'
        ]
        widgets = {
            'type_deposit': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
                'onchange': 'updateSerial()'
            }),
            'destination_entity': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'origin_subsidiary': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'subsidiary_encargada': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'depositor_client': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'account_holder': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Nombre del titular receptor'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Número de cuenta bancaria'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True,
                'placeholder': '0.00'
            }),
            'observation': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'VOUCHER'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo clientes
        self.fields['depositor_client'].queryset = Person.objects.filter(type='C').order_by('full_name')
        # Filtrar solo sucursales activas
        self.fields['origin_subsidiary'].queryset = Subsidiary.objects.all().order_by('name')
        self.fields['subsidiary_encargada'].queryset = Subsidiary.objects.all().order_by('name')
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return amount


class LetterOrderForm(forms.ModelForm):
    class Meta:
        model = LetterOrder
        fields = ['client', 'amount', 'due_date', 'bank', 'observation']
        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True,
                'placeholder': '0.00'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'bank': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del banco'
            }),
            'observation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo clientes
        self.fields['client'].queryset = Person.objects.filter(type='C').order_by('full_name')
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return amount
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError('La fecha de vencimiento no puede ser anterior a hoy.')
        return due_date


class DepositOrderConfirmForm(forms.ModelForm):
    class Meta:
        model = DepositOrder
        fields = ['observation']
        widgets = {
            'observation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones de confirmación'
            }),
        }


class LetterOrderConfirmForm(forms.ModelForm):
    class Meta:
        model = LetterOrder
        fields = ['observation']
        widgets = {
            'observation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones de confirmación'
            }),
        }
