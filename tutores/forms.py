from datetime import date

from django import forms

from .models import Tutor
from estudiantes.models import Estudiante
from core.paises import PAISES
from core.validators import es_cedula_rd, es_telefono_rd


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

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': (
                    'w-full border rounded px-3 py-2 '
                    'focus:outline-none focus:ring-2 '
                    'focus:ring-blue-500'
                )
            })

        if 'fecha_nacimiento' in self.fields:
            self.fields['fecha_nacimiento'].widget.attrs.update({
                'type': 'date',
                'class': (
                    'js-datepicker w-full border rounded px-3 py-2 '
                    'focus:outline-none focus:ring-2 focus:ring-blue-500'
                ),
                'max': date.today().isoformat(),
            })

        if 'cedula' in self.fields:
            self.fields['cedula'].widget.attrs.update({
                'data-mascara': 'cedula',
                'placeholder': '000-0000000-0',
            })

        for nombre in ('telefono', 'telefono_secundario'):
            if nombre in self.fields:
                self.fields[nombre].widget.attrs.update({
                    'data-mascara': 'telefono',
                    'placeholder': '000-000-0000',
                })

        if 'nacionalidad' in self.fields:
            self.fields['nacionalidad'] = forms.ChoiceField(
                choices=[('', 'Seleccione la nacionalidad...')] + [(p, p) for p in PAISES],
                widget=forms.Select(attrs={
                    'class': (
                        'w-full border rounded px-3 py-2 '
                        'focus:outline-none focus:ring-2 '
                        'focus:ring-blue-500 searchable'
                    ),
                }),
            )
            if not self.instance.pk:
                self.fields['nacionalidad'].initial = 'República Dominicana'
            self._asegurar_opcion(
                self.fields['nacionalidad'],
                self.instance.nacionalidad,
            )

        if 'foto' in self.fields:
            self.fields['foto'].widget.attrs.update({
                'accept': 'image/*',
                'class': 'w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 '
                         'file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 '
                         'file:font-semibold hover:file:bg-blue-100',
            })

    def _asegurar_opcion(self, campo, valor):
        if not valor:
            return
        if valor not in [c[0] for c in campo.choices]:
            campo.choices = campo.choices[:1] + [(valor, valor)] + campo.choices[1:]

    def clean_cedula(self):
        valor = self.cleaned_data.get('cedula')
        if valor and not es_cedula_rd(valor):
            raise forms.ValidationError(
                'La cédula no es válida. Debe tener el formato 000-0000000-0.'
            )
        return valor

    def clean_telefono(self):
        valor = self.cleaned_data.get('telefono')
        if valor and not es_telefono_rd(valor):
            raise forms.ValidationError(
                'El teléfono debe tener el formato 000-000-0000.'
            )
        return valor

    def clean_telefono_secundario(self):
        valor = self.cleaned_data.get('telefono_secundario')
        if valor and not es_telefono_rd(valor):
            raise forms.ValidationError(
                'El teléfono debe tener el formato 000-000-0000.'
            )
        return valor