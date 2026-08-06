from django import forms

from .models import AsistenciaEstudiante, DiaNoDocencia


class DiaNoDocenciaForm(forms.ModelForm):

    class Meta:
        model = DiaNoDocencia
        fields = ['anio_escolar', 'fecha', 'motivo']
        widgets = {
            'anio_escolar': forms.Select(),
            'fecha': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'motivo': forms.TextInput(
                attrs={'placeholder': 'Ej: Feriado nacional'}
            ),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)
        if centro:
            self.fields['anio_escolar'].queryset = (
                self.fields['anio_escolar'].queryset.filter(
                    centro=centro
                )
            )


class AsistenciaForm(forms.Form):
    """Formulario individual por estudiante (usado dentro de un formset)."""

    inscripcion = forms.IntegerField(
        widget=forms.HiddenInput
    )

    estado = forms.ChoiceField(
        choices=AsistenciaEstudiante.ESTADOS,
        widget=forms.RadioSelect,
        required=True,
    )
