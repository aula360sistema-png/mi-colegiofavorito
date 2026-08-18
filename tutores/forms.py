from django import forms
from .models import Tutor
from estudiantes.models import Estudiante


class TutorForm(forms.ModelForm):
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=Estudiante.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )

    class Meta:
        model = Tutor
        fields = (
            'foto', 'primer_nombre', 'segundo_nombre', 'primer_apellido',
            'segundo_apellido', 'cedula', 'sexo', 'fecha_nacimiento',
            'nacionalidad', 'direccion', 'telefono', 'telefono_secundario',
            'correo_personal', 'parentesco', 'estudiantes',
        )

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['estudiantes'].queryset = Estudiante.objects.filter(
                centro=centro
            )

        if 'fecha_nacimiento' in self.fields:
            self.fields['fecha_nacimiento'].widget.attrs['type'] = 'date'

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
