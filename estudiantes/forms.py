from django import forms
from .models import Estudiante
from tutores.models import Tutor

class EstudianteForm(forms.ModelForm):
    tutores = forms.ModelMultipleChoiceField(
        queryset=Tutor.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500'})
    )

    class Meta:
        model = Estudiante
        exclude = ['usuario', 'centro', 'estado', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['tutores'].queryset = Tutor.objects.filter(
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

        # Fecha más amigable
        if 'fecha_nacimiento' in self.fields:
            self.fields['fecha_nacimiento'].widget.attrs['type'] = 'date'

        if 'foto' in self.fields:
            self.fields['foto'].widget.attrs.update({
                'accept': 'image/*',
                'class': 'w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 '
                         'file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 '
                         'file:font-semibold hover:file:bg-blue-100',
            })

    def save(self, commit=True):
        estudiante = super().save(commit=commit)
        if commit:
            tutores = self.cleaned_data.get('tutores')
            if tutores is not None:
                estudiante.tutores.set(tutores)
        return estudiante


from django import forms
from .models import Inscripcion
from academico.models import Grado, Seccion

class InscripcionAvanzadaForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ('grado', 'seccion')

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        # 🔹 Grados del centro
        if centro:
            self.fields['grado'].queryset = Grado.objects.filter(
                nivel__centro=centro
            )

        # 🔒 IMPORTANTE: NO cargar secciones al inicio
        self.fields['seccion'].queryset = Seccion.objects.none()

        # 🟢 Cuando el usuario selecciona grado (POST)
        if 'grado' in self.data:
            try:
                grado_id = int(self.data.get('grado'))
                self.fields['seccion'].queryset = Seccion.objects.filter(
                    grados__id=grado_id
                )
            except (ValueError, TypeError):
                pass

        # 🟡 Caso edición (no aplica ahora, pero es correcto)
        elif self.instance.pk and self.instance.grado:
            self.fields['seccion'].queryset = self.instance.grado.secciones.all()


from django import forms
from .models import Estudiante, ObservacionEstudiante, SolicitudCertificado

class ObservacionEstudianteForm(forms.ModelForm):
    class Meta:
        model = ObservacionEstudiante
        fields = ('tipo', 'anio_escolar', 'fecha', 'descripcion')

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        self.fields['fecha'].widget.attrs['type'] = 'date'
        self.fields['anio_escolar'].required = False

        if centro:
            self.fields['anio_escolar'].queryset = (
                self.fields['anio_escolar'].queryset.filter(
                    centro=centro
                )
            )

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': (
                    'w-full border rounded px-3 py-2 '
                    'focus:outline-none focus:ring-2 '
                    'focus:ring-blue-500'
                )
            })


_CERT_WIDGET = (
    'w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm '
    'bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 '
    'focus:border-indigo-500 transition'
)


class SolicitudCertificadoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCertificado
        fields = ('tipo_certificado', 'metodo_pago', 'motivo')
        widgets = {
            'motivo': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Motivo de la solicitud (opcional)...',
                'class': _CERT_WIDGET,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['tipo_certificado'].label = 'Tipo de certificado'
        self.fields['metodo_pago'].label = 'Método de pago'

        for name, field in self.fields.items():
            if name != 'motivo':
                field.widget.attrs['class'] = _CERT_WIDGET


class SolicitudCertificadoTutorForm(SolicitudCertificadoForm):
    estudiante = forms.ModelChoiceField(
        queryset=Estudiante.objects.none(),
        label='Estudiante',
        required=True,
    )

    class Meta(SolicitudCertificadoForm.Meta):
        fields = ('estudiante', 'tipo_certificado', 'metodo_pago', 'motivo')

    def __init__(self, *args, **kwargs):
        estudiantes = kwargs.pop('estudiantes', None)
        super().__init__(*args, **kwargs)

        if estudiantes is not None:
            self.fields['estudiante'].queryset = estudiantes
            self.fields['estudiante'].label_from_instance = (
                lambda obj: f"{obj.matricula} — {obj.nombre_completo()}"
            )

        self.fields['estudiante'].widget.attrs['class'] = _CERT_WIDGET


class SolicitudRechazoForm(forms.Form):
    rechazo_motivo = forms.CharField(
        label='Motivo del rechazo',
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Indique el motivo...'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rechazo_motivo'].widget.attrs.update({
            'class': (
                'w-full border rounded px-3 py-2 text-sm '
                'focus:outline-none focus:ring-2 focus:ring-red-500'
            )
        })


class SolicitudCobroForm(forms.Form):
    referencia_pago = forms.CharField(
        label='Referencia del comprobante (opcional)',
        required=False,
        max_length=100,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['referencia_pago'].widget.attrs.update({
            'class': (
                'w-full border rounded px-3 py-2 text-sm '
                'focus:outline-none focus:ring-2 focus:ring-blue-500'
            )
        })


from .models import HistorialClinicoEstudiante, RegistroSalud


class HistorialClinicoForm(forms.ModelForm):
    class Meta:
        model = HistorialClinicoEstudiante
        fields = (
            'grupo_sanguineo',
            'alergias',
            'condiciones_medicas',
            'medicamentos_habituales',
            'vacunas',
            'contacto_emergencia_nombre',
            'contacto_emergencia_telefono',
            'contacto_emergencia_parentesco',
            'contacto_emergencia_secundario_nombre',
            'contacto_emergencia_secundario_telefono',
            'observaciones',
        )
        widgets = {
            'alergias': forms.Textarea(attrs={'rows': 2}),
            'condiciones_medicas': forms.Textarea(attrs={'rows': 2}),
            'medicamentos_habituales': forms.Textarea(attrs={'rows': 2}),
            'vacunas': forms.Textarea(attrs={'rows': 2}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
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


class RegistroSaludForm(forms.ModelForm):
    class Meta:
        model = RegistroSalud
        fields = ('tipo', 'fecha', 'descripcion', 'atencion_proporcionada', 'medicamento', 'notificado_a_tutor')
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2}),
            'atencion_proporcionada': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].widget.attrs['type'] = 'date'

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': (
                    'w-full border rounded px-3 py-2 '
                    'focus:outline-none focus:ring-2 '
                    'focus:ring-blue-500'
                )
            })

class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = ObservacionEstudiante
        fields = ('estudiante', 'tipo', 'anio_escolar', 'fecha', 'descripcion')
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        self.fields['fecha'].widget.attrs['type'] = 'date'
        self.fields['anio_escolar'].required = False

        self.fields['estudiante'].queryset = (
            Estudiante.objects.filter(
                centro=centro,
                estado='activo'
            ).order_by('primer_apellido', 'primer_nombre')
        )
        self.fields['estudiante'].label_from_instance = (
            lambda obj: f"{obj.matricula} — {obj.nombre_completo()}"
        )

        if centro:
            self.fields['anio_escolar'].queryset = (
                self.fields['anio_escolar'].queryset.filter(
                    centro=centro
                )
            )

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': (
                    'w-full border rounded px-3 py-2 '
                    'focus:outline-none focus:ring-2 '
                    'focus:ring-blue-500'
                )
            })

