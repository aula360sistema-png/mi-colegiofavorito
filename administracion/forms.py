from django import forms
from .models import AnioEscolar, Administrativo

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
    primer_nombre = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Primer Nombre'}))
    segundo_nombre = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Segundo Nombre'}))
    primer_apellido = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Primer Apellido'}))
    segundo_apellido = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Segundo Apellido'}))
    cedula = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Cédula'}))
    sexo = forms.ChoiceField(choices=[('M', 'Masculino'), ('F', 'Femenino')], widget=forms.Select())
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    nacionalidad = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Nacionalidad'}))
    direccion = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Dirección', 'rows': 3}))
    telefono = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Teléfono'}))
    correo_personal = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Correo personal'}))

    # Cargo / rol (un solo campo)
    cargo = forms.ChoiceField(
        choices=[('director', 'Director'), ('secretaria', 'Secretaria'), ('cajero', 'Cajero')],
        widget=forms.Select()
    )

    estado = forms.ChoiceField(
        choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')],
        widget=forms.Select()
    )

    foto = forms.ImageField(
        required=False,
        label='Foto',
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*'})
    )

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

        if 'foto' in self.fields:
            self.fields['foto'].widget.attrs.update({
                'accept': 'image/*',
                'class': 'w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 '
                         'file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 '
                         'file:font-semibold hover:file:bg-blue-100',
            })
