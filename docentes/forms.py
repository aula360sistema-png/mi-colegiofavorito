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
            'foto',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': (
                    'w-full border rounded px-3 py-2 '
                    'focus:outline-none focus:ring-2 '
                    'focus:ring-blue-500'
                )
            })

        if 'foto' in self.fields:
            self.fields['foto'].widget.attrs.update({
                'accept': 'image/*',
                'class': 'w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 '
                         'file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 '
                         'file:font-semibold hover:file:bg-blue-100',
            })
