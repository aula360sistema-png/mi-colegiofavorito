from django import forms

from academico.models import Grado
from tutores.models import Tutor

from .models import Campania


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
