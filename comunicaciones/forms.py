from django import forms

from academico.models import Grado, Seccion
from tutores.models import Tutor

from .models import Campania, Comunicado


class CampaniaForm(forms.ModelForm):
    grado = forms.ModelChoiceField(
        queryset=Grado.objects.none(),
        required=False,
        label='Grado',
        help_text='Solo se notificará a los tutores de los estudiantes inscritos en este grado (año activo).',
    )

    tutores = forms.ModelMultipleChoiceField(
        queryset=Tutor.objects.none(),
        required=False,
        label='Tutores',
        help_text='Mantén Ctrl (Cmd en Mac) para seleccionar varios tutores.',
    )

    class Meta:
        model = Campania
        fields = ('asunto', 'mensaje', 'canal', 'alcance', 'grado', 'tutores')
        widgets = {
            'asunto': forms.TextInput(attrs={'placeholder': 'Ej: Reunión de padres · 15 de septiembre'}),
            'mensaje': forms.Textarea(
                attrs={
                    'rows': 7,
                    'placeholder': (
                        'Estimado {{tutor}}, le informamos que... '
                        '(puedes usar {{tutor}} y {{estudiante}})'
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['grado'].queryset = Grado.objects.filter(
                nivel__centro=centro,
            ).order_by('nivel', 'orden', 'nombre')
            self.fields['tutores'].queryset = Tutor.objects.filter(
                centro=centro,
            ).order_by('primer_apellido', 'primer_nombre')

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', (
                'w-full rounded-lg border border-gray-300 bg-white '
                'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                'transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
            ))


class ComunicadoForm(forms.ModelForm):
    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.none(),
        required=False,
        label='Seccion',
        help_text='Obligatoria cuando el alcance es una seccion.',
    )

    class Meta:
        model = Comunicado
        fields = (
            'titulo', 'contenido', 'alcance', 'seccion',
            'fecha_publicacion', 'fecha_vencimiento', 'fijado',
        )
        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ej: Reunion de padres � 15 de septiembre'}),
            'contenido': forms.Textarea(attrs={
                'rows': 7,
                'placeholder': 'Escribe aqui el anuncio que veran estudiantes y tutores...',
            }),
            'fecha_publicacion': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'fecha_vencimiento': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['seccion'].queryset = Seccion.objects.filter(
                centro=centro,
            ).order_by('nombre')

        for field in self.fields.values():
            field.widget.attrs.setdefault('class', (
                'w-full rounded-lg border border-gray-300 bg-white '
                'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                'transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
            ))

    def clean(self):
        cleaned = super().clean()
        alcance = cleaned.get('alcance')
        seccion = cleaned.get('seccion')

        if alcance == 'seccion' and not seccion:
            raise forms.ValidationError(
                'Selecciona la seccion destino cuando el alcance es "Una seccion".'
            )
        if alcance == 'todos':
            cleaned['seccion'] = None

        vence = cleaned.get('fecha_vencimiento')
        publicada = cleaned.get('fecha_publicacion')
        if vence and publicada and vence < publicada.date():
            self.add_error(
                'fecha_vencimiento',
                'La fecha de vencimiento no puede ser anterior a la publicacion.',
            )
        return cleaned
