from datetime import timedelta
from time import timezone
from django import forms

from core.models import AnioEscolar
from .models import Calificacion, Competencia


class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ('competencia', 'nota')

    def __init__(self, *args, **kwargs):
        asignatura = kwargs.pop('asignatura', None)
        super().__init__(*args, **kwargs)

        if asignatura:
            self.fields['competencia'].queryset = Competencia.objects.all()




from .models import Nivel

class NivelForm(forms.ModelForm):
    class Meta:
        model = Nivel
        fields = ['nombre', 'tipo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm'
            })
        }



from .models import Nivel, Grado,Seccion, AreaCurricular




class GradoForm(forms.ModelForm):
    class Meta:
        model = Grado
        fields = ['nivel', 'nombre', 'orden']
        widgets = {
            'nivel': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm',
                'min': 0
            }),
        }




class SeccionForm(forms.ModelForm):
    class Meta:
        model = Seccion
        fields = ['grado', 'nombre']
        widgets = {
            'grado': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm'
            }),
        }



class AreaCurricularForm(forms.ModelForm):
    class Meta:
        model = AreaCurricular
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-300'
            })
        }



from .models import Asignatura


class AsignaturaForm(forms.ModelForm):
    class Meta:
        model = Asignatura
        fields = ['area', 'nombre']
        widgets = {
            'area': forms.Select(attrs={'class': 'w-full rounded border-gray-300'}),
            'nombre': forms.TextInput(attrs={'class': 'w-full rounded border-gray-300'}),
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
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2'
            })
        }


from .models import AreaCompetencia

from django import forms
from academico.models import AreaCurricular, Competencia, AreaCompetencia

class AreaCompetenciaForm(forms.Form):
    area = forms.ModelChoiceField(
        queryset=AreaCurricular.objects.none(),
        widget=forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
        label="Área"
    )
    
    competencias = forms.ModelMultipleChoiceField(
        queryset=Competencia.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        initial=lambda: Competencia.objects.all(),  # marcado por defecto
        label="Competencias"
    )
    
    peso = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=100,  # valor inicial
        widget=forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
        label="Peso (%)"
    )
    
    def __init__(self, *args, **kwargs):
        centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)
        if centro:
            self.fields['area'].queryset = AreaCurricular.objects.filter(centro=centro)
 
from .models import Periodo

from django import forms
from .models import Periodo

from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Periodo


class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = [
            'anio_escolar',
            'nombre',
            'orden',
            'activo',
            'es_completivo',
            'cerrado',
            'fecha_cierre'
        ]

        widgets = {
            'anio_escolar': forms.Select(
                attrs={'class': 'w-full border rounded px-3 py-2'}
            ),
            'nombre': forms.TextInput(
                attrs={
                    'class': 'w-full border rounded px-3 py-2',
                    'placeholder': 'Ej: P1, P2, Final'
                }
            ),
            'orden': forms.NumberInput(
                attrs={
                    'class': 'w-full border rounded px-3 py-2',
                    'min': 1
                }
            ),
            'activo': forms.CheckboxInput(
                attrs={'class': 'h-4 w-4'}
            ),
            'es_completivo': forms.CheckboxInput(
                attrs={'class': 'h-4 w-4'}
            ),
            'cerrado': forms.CheckboxInput(
                attrs={'class': 'h-4 w-4'}
            ),
            'fecha_cierre': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'w-full border rounded px-3 py-2',
                    'min': timezone.now().date(),
                    'max': (timezone.now() + timedelta(days=365)).date(),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.centro = kwargs.pop('centro', None)
        super().__init__(*args, **kwargs)

        # fecha_cierre NO obligatoria por defecto
        self.fields['fecha_cierre'].required = False

        if self.centro:
            self.fields['anio_escolar'].queryset = (
                self.fields['anio_escolar']
                .queryset
                .filter(centro=self.centro)
            )

    def clean(self):
        cleaned = super().clean()

        nombre = cleaned.get('nombre')
        anio = cleaned.get('anio_escolar')
        cerrado = cleaned.get('cerrado')
        fecha_cierre = cleaned.get('fecha_cierre')

        # 🔒 Validación de duplicados
        if self.centro and nombre and anio:
            qs = Periodo.objects.filter(
                centro=self.centro,
                anio_escolar=anio,
                nombre__iexact=nombre
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "Este período ya existe para este año escolar."
                )

        # 🔒 Si está cerrado, fecha_cierre es obligatoria
        if cerrado and not fecha_cierre:
            self.add_error(
                'fecha_cierre',
                'Debe indicar la fecha de cierre del período.'
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
        widgets = {
                'docente': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
                'asignatura': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
                'grado': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
                'seccion': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
                'anio_escolar': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
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
                    grado_id=grado_id
                )
            except (TypeError, ValueError):
                self.fields['seccion'].queryset = Seccion.objects.none()
        elif self.instance.pk:
            self.fields['seccion'].queryset = Seccion.objects.filter(
                grado=self.instance.grado
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
                'class': 'form-control',
                'placeholder': '2024-2025'
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'fecha_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }
