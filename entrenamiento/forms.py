from django import forms

from .models import (
    DestrezaCognitiva,
    DiagnosticoCognitivo,
    Ejercicio,
    PlanRefuerzo,
    SesionEntrenamiento,
    TramoEdad,
    UnidadEntrenamiento,
)


class TramoEdadForm(forms.ModelForm):
    class Meta:
        model = TramoEdad
        fields = ['nombre', 'edad_min', 'edad_max', 'orden', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })


class DestrezaCognitivaForm(forms.ModelForm):
    class Meta:
        model = DestrezaCognitiva
        fields = ['tramo', 'categoria', 'nombre', 'descripcion', 'orden', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tramo'].widget.attrs.update({
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                     'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
        for field in ['categoria', 'nombre', 'descripcion', 'orden', 'activo']:
            self.fields[field].widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        if self.fields.get('descripcion'):
            self.fields['descripcion'].widget.attrs['rows'] = 3


class UnidadEntrenamientoForm(forms.ModelForm):
    class Meta:
        model = UnidadEntrenamiento
        fields = ['tramo', 'numero', 'nombre', 'destrezas', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['tramo', 'numero', 'nombre', 'activo']:
            self.fields[field_name].widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        self.fields['destrezas'].widget.attrs.update({
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                     'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
        self.fields['destrezas'].help_text = 'Mantén Ctrl (Cmd en Mac) para seleccionar múltiples.'


class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = [
            'unidad', 'destreza', 'tipo', 'dificultad', 'enunciado',
            'texto', 'opciones', 'respuesta_correcta', 'tiempo_max_seg', 'activo',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['unidad', 'destreza', 'tipo', 'dificultad', 'tiempo_max_seg', 'activo']:
            self.fields[field_name].widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        for field_name in ['enunciado', 'texto', 'respuesta_correcta']:
            self.fields[field_name].widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
            })
        self.fields['opciones'].widget.attrs.update({
            'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-mono '
                     'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'rows': 5,
            'placeholder': '[{"texto": "Opción 1", "correcta": false}, {"texto": "Opción 2", "correcta": true}]'
        })
        self.fields['texto'].help_text = 'Pasaje de lectura, opcional según el tipo.'
        self.fields['opciones'].help_text = 'JSON: [{"texto": "...", "correcta": false}]'


class DiagnosticoCognitivoForm(forms.ModelForm):
    class Meta:
        model = DiagnosticoCognitivo
        fields = ['estudiante', 'anio_escolar', 'tramo', 'resultado', 'ipd']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        self.fields['resultado'].widget.attrs.update({
            'rows': 5,
            'placeholder': '{"destreza_id": {"aciertos": 0, "errores": 0, "nivel": "medio"}}'
        })
        self.fields['resultado'].help_text = (
            'JSON por destreza: {destreza_id: {"aciertos": n, "errores": n, "nivel": "bajo"|"medio"|"alto"}}'
        )


class SesionEntrenamientoForm(forms.ModelForm):
    class Meta:
        model = SesionEntrenamiento
        fields = ['estudiante', 'anio_escolar', 'unidad']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })


class PlanRefuerzoForm(forms.ModelForm):
    class Meta:
        model = PlanRefuerzo
        fields = ['estudiante', 'anio_escolar', 'unidad', 'generado_por', 'origen', 'estado', 'nota']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm '
                         'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        self.fields['nota'].widget.attrs.update({'rows': 3})
