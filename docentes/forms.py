# docentes/forms.py
from django import forms
from .models import Docente

class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        exclude = ('usuario','centro',) 
        fields = [
            
            'centro',
            'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido',
            'cedula',
            'sexo',
            'fecha_nacimiento',
            'nacionalidad',
            'direccion',
            'telefono',
            'correo_personal',
            'codigo_docente_minerd',
            'area_especialidad',
            'fecha_ingreso',
            'tipo_contrato',
            'tanda',
            'estado',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}),
        }
