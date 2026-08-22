from django import forms

from .models import ConsentimientoInformado


class ConsentimientoInformadoForm(forms.ModelForm):
    class Meta:
        model = ConsentimientoInformado
        fields = [
            'estudiante', 'tutor_nombre', 'tutor_cedula', 'tutor_parentesco',
            'acepta_datos_personales', 'acepta_datos_academicos',
            'acepta_datos_clinicos', 'acepta_comunicaciones',
        ]
        widgets = {
            'estudiante': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'tutor_nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'tutor_cedula': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'tutor_parentesco': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['acepta_datos_personales', 'acepta_datos_academicos',
                           'acepta_datos_clinicos', 'acepta_comunicaciones']:
            self.fields[field_name].widget.attrs.update({
                'class': 'h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
            })
