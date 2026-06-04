from django import forms

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
    PeriodoNomina
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

        centro_id = kwargs.pop(
            'centro_id',
            None
        )

        super().__init__(*args, **kwargs)

        usuarios = Usuario.objects.filter(
            is_active=True,
            rol__in=[
                'docente',
                'director',
                'secretaria',
                'admin'
            ]
        ).exclude(
            configuracion_nomina__isnull=False
        )

        self.fields['usuario'].queryset = usuarios

        self.fields['usuario'].label_from_instance = (
            lambda obj:
            f"{obj.get_full_name()} ({obj.username})"
        )


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

        fields = '__all__'


# ==========================================
# DESCUENTOS EMPLEADO
# ==========================================

class DescuentoEmpleadoForm(forms.ModelForm):

    class Meta:

        model = DescuentoEmpleado

        fields = '__all__'


# ==========================================
# PERIODOS NOMINA
# ==========================================

class PeriodoNominaForm(forms.ModelForm):

    class Meta:

        model = PeriodoNomina

        exclude = ['centro']


class ARSForm(forms.ModelForm):

    class Meta:

        model = ARS

        fields = '__all__'