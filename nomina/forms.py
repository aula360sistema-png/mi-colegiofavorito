from django import forms

from administracion.models import Administrativo
from docentes.models import Docente
from usuarios.models import Usuario

from .models import (
    AFP,
    ARS,
    Cargo,
    ConfiguracionNomina,
    TipoIngreso,
    TipoDescuento,
    IngresoEmpleado,
    DescuentoEmpleado,
)


# ==========================================
# AFP
# ==========================================

class AFPForm(forms.ModelForm):

    class Meta:
        model = AFP
        fields = '__all__'


# ==========================================
# ARS
# ==========================================

class ARSForm(forms.ModelForm):

    class Meta:
        model = ARS
        fields = '__all__'


# ==========================================
# CARGOS
# ==========================================

class CargoForm(forms.ModelForm):

    class Meta:
        model = Cargo
        fields = '__all__'


# ==========================================
# CONFIGURACION NOMINA
# ==========================================

class ConfiguracionNominaForm(forms.ModelForm):

    class Meta:
        model = ConfiguracionNomina
        exclude = ['centro']

    def __init__(self, *args, **kwargs):
        centro_id = kwargs.pop('centro_id', None)
        super().__init__(*args, **kwargs)

        if centro_id:
            self.fields['usuario'].queryset = self._usuarios_disponibles(
                centro_id,
                instancia=self.instance
            )

        self.fields['usuario'].label_from_instance = (
            lambda obj: f"{obj.get_full_name()} ({obj.username})"
        )

    def _usuarios_disponibles(self, centro_id, instancia=None):
        """Usuarios del centro aún no configurados para nómina."""

        ids = set()
        ids.update(
            Docente.objects.filter(centro_id=centro_id)
            .values_list('usuario_id', flat=True)
        )
        ids.update(
            Administrativo.objects.filter(centro_id=centro_id)
            .values_list('usuario_id', flat=True)
        )

        usuarios = (
            Usuario.objects
            .filter(is_active=True, id__in=ids)
            .exclude(id=None)
        )

        # Los administradores globales también pueden ser empleados
        usuarios = usuarios | Usuario.objects.filter(
            is_active=True,
            rol__in=['admin', 'superadmin'],
        )

        ya_configurados = ConfiguracionNomina.objects.filter(
            centro_id=centro_id
        ).values_list('usuario_id', flat=True)

        if instancia and instancia.pk:
            ya_configurados = [
                u for u in ya_configurados
                if u != instancia.usuario_id
            ]

        return usuarios.exclude(id__in=ya_configurados).distinct()


# ==========================================
# TIPOS INGRESOS
# ==========================================

class TipoIngresoForm(forms.ModelForm):

    class Meta:
        model = TipoIngreso
        fields = '__all__'


# ==========================================
# TIPOS DESCUENTOS
# ==========================================

class TipoDescuentoForm(forms.ModelForm):

    class Meta:
        model = TipoDescuento
        fields = '__all__'


# ==========================================
# INGRESOS EMPLEADO
# ==========================================

class IngresoEmpleadoForm(forms.ModelForm):

    class Meta:
        model = IngresoEmpleado
        fields = ['tipo', 'monto', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoIngreso.objects.filter(
            activo=True
        )
        self.fields['monto'].help_text = (
            "Monto mensual. Se divide según el tipo de pago del centro "
            "(mensual, quincenal o semanal)."
        )


# ==========================================
# DESCUENTOS EMPLEADO
# ==========================================

class DescuentoEmpleadoForm(forms.ModelForm):

    class Meta:
        model = DescuentoEmpleado
        fields = ['tipo', 'monto', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoDescuento.objects.filter(
            activo=True
        )
        self.fields['monto'].help_text = (
            "Monto mensual. Se divide según el tipo de pago del centro "
            "(mensual, quincenal o semanal)."
        )
