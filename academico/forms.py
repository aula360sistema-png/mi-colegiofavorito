from django import forms

from core.models import AnioEscolar
from .models import Calificacion, Competencia


class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ('competencia', 'nota')

    def __init__(self, *args, **kwargs):
        nivel = kwargs.pop('nivel', None)
        super().__init__(*args, **kwargs)

        if nivel:
            self.fields['competencia'].queryset = Competencia.objects.filter(
                nivel=nivel,
                activo=True
            )




from .models import Nivel

class NivelForm(forms.ModelForm):
    class Meta:
        model = Nivel
        fields = ['nombre', 'tipo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
            })
        }



from .models import Nivel, Grado,Seccion, AreaCurricular




class GradoForm(forms.ModelForm):
    class Meta:
        model = Grado
        fields = ['nivel', 'nombre', 'orden', 'secciones']
        widgets = {
            'nivel': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white searchable',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': 0
            }),
            'secciones': forms.CheckboxSelectMultiple(attrs={
                'class': 'h-5 w-5 rounded border-gray-300 accent-blue-600 focus:ring-blue-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['secciones'].queryset = Seccion.objects.filter(
                centro=centro
            )




class SeccionForm(forms.ModelForm):
    class Meta:
        model = Seccion
        fields = ['nombre', 'capacidad_max']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'capacidad_max': forms.NumberInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        nombre = cleaned.get('nombre')

        if self.centro and nombre:
            qs = Seccion.objects.filter(
                centro=self.centro,
                nombre__iexact=nombre
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f"La sección '{nombre}' ya existe para este centro."
                )

        return cleaned



class AreaCurricularForm(forms.ModelForm):
    class Meta:
        model = AreaCurricular
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            })
        }



from .models import Asignatura


class AsignaturaForm(forms.ModelForm):
    class Meta:
        model = Asignatura
        fields = ['area', 'nombre']
        widgets = {
            'area': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white searchable',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['area'].queryset = AreaCurricular.objects.filter(centro=centro)



from .models import GradoAsignatura


from django import forms
from .models import GradoAsignatura, Asignatura

from django import forms
from .models import GradoAsignatura, Grado, Asignatura

class GradoAsignaturaForm(forms.ModelForm):
    class Meta:
        model = GradoAsignatura
        fields = ['grado', 'asignatura']
        widgets = {
            'grado': forms.Select(
                attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white searchable',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        # 🔒 Filtrar grados por centro
        if centro:
            self.fields['grado'].queryset = Grado.objects.filter(
                nivel__centro=centro
            )

        # 🚫 Por defecto NO mostrar asignaturas
        self.fields['asignatura'].queryset = Asignatura.objects.none()

        # 🔁 Si el grado ya fue seleccionado
        if 'grado' in self.data:
            try:
                grado_id = int(self.data.get('grado'))

                # 📌 Asignaturas ya asignadas a este grado
                asignadas = GradoAsignatura.objects.filter(
                    grado_id=grado_id
                ).values_list('asignatura_id', flat=True)

                # ✅ Mostrar solo las NO asignadas
                self.fields['asignatura'].queryset = Asignatura.objects.filter(
                    centro=centro
                ).exclude(id__in=asignadas)

            except (ValueError, TypeError):
                pass
    def clean(self):
        cleaned = super().clean()
        grado = cleaned.get('grado')
        asignatura = cleaned.get('asignatura')

        if grado and asignatura:
            existe = GradoAsignatura.objects.filter(
                grado=grado,
                asignatura=asignatura
            ).exists()

            if existe:
                raise forms.ValidationError(
                    'Esta asignatura ya está asignada a este grado.'
                )

        return cleaned

    
    


class CompetenciaForm(forms.ModelForm):
    class Meta:
        model = Competencia
        fields = ['nivel', 'nombre', 'activo']
        widgets = {
            'nivel': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        if centro:
            self.fields['nivel'].queryset = Nivel.objects.filter(centro=centro)


from .models import Periodo


class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = [
            'nombre',
            'orden',
            'es_completivo',
            'es_extraordinario',
        ]

        widgets = {
            'nombre': forms.TextInput(
                attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    'placeholder': 'Ej: P1, P2, Final'
                }
            ),
            'orden': forms.NumberInput(
                attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    'min': 1
                }
            ),
            'es_completivo': forms.CheckboxInput(
                attrs={'class': 'h-5 w-5 rounded border-gray-300 accent-blue-600 focus:ring-blue-500'}
            ),
            'es_extraordinario': forms.CheckboxInput(
                attrs={'class': 'h-5 w-5 rounded border-gray-300 accent-amber-600 focus:ring-amber-500'}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        nombre = cleaned.get('nombre')

        # 🔒 Validación de duplicados (catálogo por centro)
        if self.centro and nombre:
            qs = Periodo.objects.filter(
                centro=self.centro,
                nombre__iexact=nombre
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "Este período ya existe para este centro."
                )

        return cleaned


    

from django import forms
from .models import DocenteMateria
from docentes.models import Docente
from academico.models import Asignatura, Grado, Seccion


class DocenteMateriaForm(forms.ModelForm):
    class Meta:
        model = DocenteMateria
        fields = [
            'docente',
            'asignatura',
            'grado',
            'seccion',
            'anio_escolar'
        ]
        labels = {
            'docente': 'Docente',
            'asignatura': 'Asignatura',
            'grado': 'Grado',
            'seccion': 'Sección',
            'anio_escolar': 'Año Escolar',
        }
        widgets = {
                'docente': forms.Select(attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
                }),
                'asignatura': forms.Select(attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
                }),
                'grado': forms.Select(attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
                }),
                'seccion': forms.Select(attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
                }),
                'anio_escolar': forms.Select(attrs={
                    'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
                }),
            }
    def __init__(self, *args, **kwargs):
        self.centro = kwargs.pop('centro')
        super().__init__(*args, **kwargs)

        self.fields['docente'].queryset = Docente.objects.filter(
            centro=self.centro,
            estado='activo'
        )

        self.fields['asignatura'].queryset = Asignatura.objects.filter(
            centro=self.centro
        )

        self.fields['grado'].queryset = Grado.objects.filter(
            nivel__centro=self.centro
        )

        # 🔑 Secciones filtradas por grado si existe
        if 'grado' in self.data:
            try:
                grado_id = int(self.data.get('grado'))
                self.fields['seccion'].queryset = Seccion.objects.filter(
                    grados__id=grado_id,
                    centro=self.centro
                )
            except (TypeError, ValueError):
                self.fields['seccion'].queryset = Seccion.objects.none()
        elif self.instance.pk:
            self.fields['seccion'].queryset = Seccion.objects.filter(
                grados=self.instance.grado,
                centro=self.centro
            )
        else:
            self.fields['seccion'].queryset = Seccion.objects.none()

        self.fields['anio_escolar'].queryset = AnioEscolar.objects.filter(
            centro=self.centro,
            activo=True
        )

    def clean(self):
        cleaned = super().clean()

        docente = cleaned.get('docente')
        asignatura = cleaned.get('asignatura')
        grado = cleaned.get('grado')
        seccion = cleaned.get('seccion')
        anio = cleaned.get('anio_escolar')

        if not all([docente, asignatura, grado, seccion, anio]):
            return cleaned

        qs = DocenteMateria.objects.filter(
            docente=docente,
            asignatura=asignatura,
            grado=grado,
            seccion=seccion,
            anio_escolar=anio
        )

        # 🔑 Evitar choque al editar
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "Esta asignación ya existe para este docente."
            )

        return cleaned



from administracion.models import AnioEscolar

class AnioEscolarForm(forms.ModelForm):
    class Meta:
        model = AnioEscolar
        fields = ['nombre', 'fecha_inicio', 'fecha_fin', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': '2024-2025'
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'fecha_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 rounded border-gray-300 accent-blue-600 focus:ring-blue-500'
            }),
        }


from .models import FranjaHoraria, HorarioClase


class FranjaHorariaForm(forms.ModelForm):
    class Meta:
        model = FranjaHoraria
        fields = ['nombre', 'hora_inicio', 'hora_fin', 'orden']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Ej: 1ra hora'
            }),
            'hora_inicio': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'hora_fin': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': 1
            }),
        }

    def __init__(self, *args, **kwargs):
        self.centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        nombre = cleaned.get('nombre')

        if self.centro and nombre:
            qs = FranjaHoraria.objects.filter(
                centro=self.centro,
                nombre__iexact=nombre
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "Ya existe una franja con ese nombre para este centro."
                )

        hora_inicio = cleaned.get('hora_inicio')
        hora_fin = cleaned.get('hora_fin')

        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise forms.ValidationError(
                "La hora de fin debe ser posterior a la hora de inicio."
            )

        return cleaned


class HorarioClaseForm(forms.ModelForm):
    class Meta:
        model = HorarioClase
        fields = ['asignacion', 'dia_semana', 'franja']
        labels = {
            'asignacion': 'Materia (asignación docente)',
            'dia_semana': 'Día',
            'franja': 'Franja horaria',
        }
        widgets = {
            'asignacion': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
            }),
            'dia_semana': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
            }),
            'franja': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.centro = kwargs.pop('centro')
        super().__init__(*args, **kwargs)

        self.fields['asignacion'].queryset = DocenteMateria.objects.filter(
            docente__centro=self.centro,
            anio_escolar__centro=self.centro
        ).select_related('docente', 'asignatura', 'grado', 'seccion')

        self.fields['franja'].queryset = FranjaHoraria.objects.filter(
            centro=self.centro
        )

    def clean(self):
        cleaned = super().clean()

        asignacion = cleaned.get('asignacion')
        dia_semana = cleaned.get('dia_semana')
        franja = cleaned.get('franja')

        if not all([asignacion, dia_semana, franja]):
            return cleaned

        # 🔑 Evitar duplicar la misma materia el mismo día y franja
        qs = HorarioClase.objects.filter(
            asignacion=asignacion,
            dia_semana=dia_semana,
            franja=franja
        )
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "Esta materia ya está programada en ese día y franja."
            )

        # 🔑 Evitar que el mismo docente tenga dos clases a la misma hora
        choque_docente = HorarioClase.objects.filter(
            dia_semana=dia_semana,
            franja=franja,
            asignacion__docente=asignacion.docente
        )
        if self.instance.pk:
            choque_docente = choque_docente.exclude(pk=self.instance.pk)

        if choque_docente.exists():
            raise forms.ValidationError(
                "El docente ya tiene otra clase en ese día y franja."
            )

        # 🔑 Evitar que la misma sección tenga dos materias a la misma hora
        choque_seccion = HorarioClase.objects.filter(
            dia_semana=dia_semana,
            franja=franja,
            asignacion__grado=asignacion.grado,
            asignacion__seccion=asignacion.seccion,
            asignacion__anio_escolar=asignacion.anio_escolar
        )
        if self.instance.pk:
            choque_seccion = choque_seccion.exclude(pk=self.instance.pk)

        if choque_seccion.exists():
            raise forms.ValidationError(
                "Esta sección ya tiene otra materia en ese día y franja."
            )

        return cleaned
