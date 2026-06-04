from django import forms
from usuarios.models import Usuario

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'nombre', 'apellido', 'password']
