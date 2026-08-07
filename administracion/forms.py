from django import forms
from administracion.models import Administrativo

from django import forms
from .models import AnioEscolar

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


class AdministrativoForm(forms.ModelForm):
    class Meta:
        model = Administrativo
        exclude = ['usuario', 'created_at', 'updated_at', 'fecha_ingreso', 'centro']

    # Campos personales
    primer_nombre = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Primer Nombre', 'class': 'form-input'}))
    segundo_nombre = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Segundo Nombre', 'class': 'form-input'}))
    primer_apellido = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Primer Apellido', 'class': 'form-input'}))
    segundo_apellido = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Segundo Apellido', 'class': 'form-input'}))
    cedula = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Cédula', 'class': 'form-input'}))
    sexo = forms.ChoiceField(choices=[('M', 'Masculino'), ('F', 'Femenino')], widget=forms.Select(attrs={'class': 'form-input'}))
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    nacionalidad = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Nacionalidad', 'class': 'form-input'}))
    direccion = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Dirección', 'rows': 3, 'class': 'form-input'}))
    telefono = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Teléfono', 'class': 'form-input'}))
    correo_personal = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Correo personal', 'class': 'form-input'}))

    # Cargo / rol (un solo campo)
    cargo = forms.ChoiceField(
        choices=[('director', 'Director'), ('secretaria', 'Secretaria'), ('cajero', 'Cajero')],
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    estado = forms.ChoiceField(
        choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')],
        widget=forms.Select(attrs={'class': 'form-input'})
    )
