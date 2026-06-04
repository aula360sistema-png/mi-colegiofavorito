from django import forms
from django.http import JsonResponse
from .models import Estudiante, Inscripcion
from django.contrib.auth.decorators import login_required

class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        exclude = ['usuario', 'centro', 'estado', 'created_at', 'updated_at']

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

        # Fecha más amigable
        if 'fecha_nacimiento' in self.fields:
            self.fields['fecha_nacimiento'].widget.attrs['type'] = 'date'



class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        exclude = ('estudiante', 'centro', 'fecha')

from django import forms
from .models import Inscripcion
from academico.models import Grado, Seccion

@login_required
def cargar_secciones(request):
    grado_id = request.GET.get('grado')
    secciones = []

    if grado_id:
        secciones = Seccion.objects.filter(
            grado_id=grado_id
        ).values('id', 'nombre')

    return JsonResponse(list(secciones), safe=False)
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
                    grado_id=grado_id
                )
            except (ValueError, TypeError):
                pass

        # 🟡 Caso edición (no aplica ahora, pero es correcto)
        elif self.instance.pk and self.instance.grado:
            self.fields['seccion'].queryset = Seccion.objects.filter(
                grado=self.instance.grado
            )

