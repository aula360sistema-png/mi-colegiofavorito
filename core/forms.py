from django import forms
from .models import CentroEducativo, ConfiguracionCentro


class CentroEducativoForm(forms.ModelForm):
    class Meta:
        model = CentroEducativo
        fields = [
            'nombre',
            'codigo_minerd',
            'direccion',
            'telefono',
            'email',
            'activo'
        ]

        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }

class ConfiguracionCentroForm(forms.ModelForm):

    class Meta:
        model = ConfiguracionCentro

        fields = [
            'usa_calificacion_numerica',
            'nota_minima_aprobacion',
            'usa_competencias',
            'permite_completivo',

            'modulo_asistencia',
            'modulo_caja',
            'modulo_nomina',
            'modulo_biblioteca',
            'modulo_transporte',
            'modulo_cafeteria',
            'modulo_inventario',
            'modulo_reportes',
            'tipo_pago_nomina',
            
        ]