from decimal import Decimal

from django import forms

from core.utils.anio import obtener_anio_activo

from estudiantes.models import Inscripcion

from .models import (
    AsignacionConcepto,
    Caja,
    ConceptoPago,
    Egreso,
    Pago,
    SesionCaja,
)
from .services import cajas_disponibles, saldo_por_concepto

INPUT = (
    'w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 '
    'text-sm text-gray-800 shadow-sm outline-none transition '
    'focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200'
)


class CajaForm(forms.ModelForm):
    class Meta:
        model = Caja
        fields = ['nombre', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': INPUT,
                'placeholder': 'Ej: Caja Principal'
            }),
            'activa': forms.CheckboxInput(),
        }


class ConceptoPagoForm(forms.ModelForm):
    class Meta:
        model = ConceptoPago
        fields = ['nombre', 'monto', 'es_recurrente', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT}),
            'monto': forms.NumberInput(attrs={
                'class': INPUT,
                'step': '0.01'
            }),
            'es_recurrente': forms.CheckboxInput(),
            'activo': forms.CheckboxInput(),
        }


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['estudiante', 'concepto', 'monto', 'metodo_pago', 'fecha', 'voucher']
        widgets = {
            'estudiante': forms.Select(attrs={
                'class': INPUT,
                'id': 'id-estudiante',
            }),
            'concepto': forms.Select(attrs={
                'class': INPUT,
                'id': 'id-concepto',
            }),
            'monto': forms.NumberInput(attrs={
                'class': INPUT,
                'id': 'id-monto',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
            }),
            'metodo_pago': forms.HiddenInput(),
            'voucher': forms.HiddenInput(),
            'fecha': forms.DateInput(attrs={
                'type': 'hidden',
                'class': INPUT,
            }),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['concepto'].queryset = ConceptoPago.objects.filter(
                centro=centro,
                activo=True
            )
            qs = self.fields['estudiante'].queryset.filter(centro=centro)
            anio = obtener_anio_activo(centro)
            if anio:
                inscritos = Inscripcion.objects.filter(
                    centro=centro,
                    anio_escolar=anio,
                ).values_list('estudiante_id', flat=True)
                qs = qs.filter(id__in=inscritos)
            self.fields['estudiante'].queryset = qs

        self.fields['estudiante'].empty_label = "Busca y selecciona el estudiante"
        self.fields['estudiante'].label_from_instance = self._label_estudiante
        self.fields['concepto'].empty_label = "Selecciona el concepto"
        self.fields['concepto'].label_from_instance = self._label_concepto

    def _label_estudiante(self, obj):
        return f"{obj.nombre_completo()} · {obj.matricula}"

    def _label_concepto(self, obj):
        return f"{obj.nombre} — RD$ {obj.monto:,.2f}"

    def clean(self):
        cleaned = super().clean()
        estudiante = cleaned.get('estudiante')
        concepto = cleaned.get('concepto')
        monto = cleaned.get('monto')

        if not (estudiante and concepto and monto is not None):
            return cleaned

        anio = obtener_anio_activo(estudiante.centro)
        if not anio:
            return cleaned

        inscrito = Inscripcion.objects.filter(
            centro=estudiante.centro,
            anio_escolar=anio,
            estudiante=estudiante,
        ).exists()

        if not inscrito:
            raise forms.ValidationError(
                f"El estudiante no está matriculado en el año escolar "
                f"activo ({anio.nombre}). Matrículalo primero para "
                "poder registrarle pagos."
            )

        asignado = AsignacionConcepto.objects.filter(
            centro=estudiante.centro,
            estudiante=estudiante,
            concepto=concepto,
            anio_escolar=anio,
            activo=True,
        ).exists()

        if not asignado:
            raise forms.ValidationError(
                f"El estudiante no tiene asignado el concepto "
                f"«{concepto.nombre}» para el año {anio.nombre}. "
                "Asigna el concepto antes de cobrarlo."
            )

        _, _, saldo = saldo_por_concepto(
            estudiante.centro,
            estudiante,
            concepto,
            anio,
        )

        if monto > saldo + Decimal('0.01'):
            raise forms.ValidationError(
                f"El monto supera lo pendiente (RD$ {saldo:,.2f}). "
                "El pago no puede ser mayor a lo establecido. "
                "Si es un abono, ingresa un monto menor o igual."
            )

        return cleaned


class AperturaCajaForm(forms.ModelForm):
    class Meta:
        model = SesionCaja
        fields = ['caja', 'monto_inicial', 'nota_apertura']
        widgets = {
            'caja': forms.Select(attrs={'class': INPUT}),
            'monto_inicial': forms.NumberInput(attrs={
                'class': INPUT,
                'step': '0.01',
                'min': '0'
            }),
            'nota_apertura': forms.TextInput(attrs={
                'class': INPUT,
                'placeholder': 'Nota opcional'
            }),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['caja'].queryset = cajas_disponibles(centro)
            self.fields['caja'].empty_label = "Selecciona la caja"

        self.fields['caja'].required = True


class CierreCajaForm(forms.ModelForm):
    class Meta:
        model = SesionCaja
        fields = ['arqueo', 'nota_cierre']
        widgets = {
            'arqueo': forms.NumberInput(attrs={
                'class': INPUT,
                'step': '0.01',
                'min': '0',
                'placeholder': 'Efectivo contado en caja'
            }),
            'nota_cierre': forms.TextInput(attrs={
                'class': INPUT,
                'placeholder': 'Nota opcional'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['arqueo'].required = True


class EgresoForm(forms.ModelForm):
    class Meta:
        model = Egreso
        fields = ['concepto', 'beneficiario', 'monto', 'metodo_pago', 'fecha', 'nota']
        widgets = {
            'concepto': forms.TextInput(attrs={
                'class': INPUT,
                'placeholder': 'Ej: Compra de materiales, pago a proveedor...'
            }),
            'beneficiario': forms.TextInput(attrs={
                'class': INPUT,
                'placeholder': 'A nombre de quién (opcional)'
            }),
            'monto': forms.NumberInput(attrs={
                'class': INPUT,
                'step': '0.01'
            }),
            'metodo_pago': forms.Select(attrs={'class': INPUT}),
            'fecha': forms.DateInput(attrs={
                'class': INPUT,
                'type': 'date'
            }),
            'nota': forms.TextInput(attrs={
                'class': INPUT,
                'placeholder': 'Nota opcional'
            }),
        }


class AsignacionConceptoForm(forms.ModelForm):
    class Meta:
        model = AsignacionConcepto
        fields = ['estudiante', 'concepto', 'anio_escolar', 'activo']
        widgets = {
            'estudiante': forms.Select(attrs={'class': INPUT}),
            'concepto': forms.Select(attrs={'class': INPUT}),
            'anio_escolar': forms.Select(attrs={'class': INPUT}),
            'activo': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        estudiantes_qs = kwargs.pop('estudiantes_qs', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['estudiante'].queryset = (
                estudiantes_qs
                if estudiantes_qs is not None
                else self.fields['estudiante'].queryset.filter(centro=centro)
            )
            self.fields['concepto'].queryset = ConceptoPago.objects.filter(
                centro=centro
            )
            self.fields['anio_escolar'].queryset = self.fields[
                'anio_escolar'
            ].queryset.filter(centro=centro)
