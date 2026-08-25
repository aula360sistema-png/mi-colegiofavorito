from django import forms
from .models import CentroEducativo, ConfiguracionCentro, PermisoPagina, TemaCentro
from academico.services.estructura_minerd import ESTRUCTURA_MINERD


class CentroEducativoForm(forms.ModelForm):
    nivel = forms.ChoiceField(
        choices=[(tipo, datos["nombre"]) for tipo, datos in ESTRUCTURA_MINERD.items()],
        widget=forms.RadioSelect(attrs={
            'class': 'h-5 w-5 border-gray-300 accent-blue-600 focus:ring-blue-500',
        }),
        label='Nivel del centro',
        help_text=(
            'Se crearán automáticamente solo los grados oficiales del currículo '
            'MINERD correspondientes a este nivel.'
        ),
    )

    class Meta:
        model = CentroEducativo
        fields = [
            'nombre',
            'codigo_minerd',
            'direccion',
            'telefono',
            'email',
            'activo'
        ]

        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, (forms.RadioSelect, forms.CheckboxInput)):
                continue
            field.widget.attrs.setdefault(
                'class',
                'w-full rounded-lg border border-gray-300 bg-white '
                'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                'transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
            )

        # Pre-marcar el nivel que ya tiene el centro (caso edición)
        if self.instance and self.instance.pk:
            nivel_existente = self.instance.nivel_set.values_list(
                'tipo', flat=True
            ).first()
            if nivel_existente:
                self.initial['nivel'] = nivel_existente

CHECKBOX_WIDGET = forms.CheckboxInput(attrs={
    'class': 'h-4 w-4 rounded border-gray-300 accent-indigo-600'
})

class ConfiguracionCentroForm(forms.ModelForm):

    class Meta:
        model = ConfiguracionCentro

        fields = [
            'usa_calificacion_numerica',
            'nota_minima_aprobacion',
            'usa_competencias',
            'permite_completivo',

            'modulo_asistencia',
            'modulo_caja',
            'modulo_nomina',
            'modulo_biblioteca',
            'modulo_transporte',
            'modulo_cafeteria',
            'modulo_inventario',
            'modulo_reportes',
            'modulo_mensajeria',
            'tipo_pago_nomina',

            'permitir_facturacion',
            'rnc',
            'facturacion_itbis',

            'modulo_certificados',
            'precio_certificado',
            'permitir_pago_online',

            'email_proveedor',
            'email_api_key',
            'email_servidor',
            'email_puerto',
            'email_usuario',
            'email_clave',
            'email_tls',
            'email_ssl',
            'email_remitente',

            'whatsapp_url',
            'whatsapp_token',
            'whatsapp_remitente',
        ]

        widgets = {
            'usa_calificacion_numerica': CHECKBOX_WIDGET,
            'usa_competencias': CHECKBOX_WIDGET,
            'permite_completivo': CHECKBOX_WIDGET,
            'modulo_asistencia': CHECKBOX_WIDGET,
            'modulo_caja': CHECKBOX_WIDGET,
            'modulo_nomina': CHECKBOX_WIDGET,
            'modulo_biblioteca': CHECKBOX_WIDGET,
            'modulo_transporte': CHECKBOX_WIDGET,
            'modulo_cafeteria': CHECKBOX_WIDGET,
            'modulo_inventario': CHECKBOX_WIDGET,
            'modulo_reportes': CHECKBOX_WIDGET,
            'modulo_mensajeria': CHECKBOX_WIDGET,
            'permitir_facturacion': CHECKBOX_WIDGET,
            'facturacion_itbis': CHECKBOX_WIDGET,
            'nota_minima_aprobacion': forms.NumberInput(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
                'step': '0.01',
            }),
            'tipo_pago_nomina': forms.Select(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
            }),
            'rnc': forms.TextInput(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
                'placeholder': 'Ej: 1-30-00000-0',
            }),
            'precio_certificado': forms.NumberInput(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
                'step': '0.01',
                'min': '0',
            }),
            'modulo_certificados': CHECKBOX_WIDGET,
            'permitir_pago_online': CHECKBOX_WIDGET,
            'email_tls': CHECKBOX_WIDGET,
            'email_ssl': CHECKBOX_WIDGET,
            'email_proveedor': forms.Select(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
                'id': 'id_email_proveedor',
                'onchange': 'mostrarCamposCorreo(this.value)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        TEXTO = {
            'class': (
                'w-full rounded-lg border border-gray-300 bg-white '
                'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
            ),
        }
        for nombre, widget in [
            ('email_servidor', forms.TextInput),
            ('email_usuario', forms.EmailInput),
            ('email_clave', forms.PasswordInput),
            ('email_api_key', forms.PasswordInput),
            ('email_remitente', forms.EmailInput),
            ('whatsapp_url', forms.URLInput),
            ('whatsapp_token', forms.PasswordInput),
            ('whatsapp_remitente', forms.TextInput),
        ]:
            self.fields[nombre].widget = widget(attrs={**TEXTO})
        for nombre, attrs in [
            ('email_servidor', {'placeholder': 'Ej: smtp.gmail.com'}),
            ('email_puerto', {'placeholder': '587'}),
            ('email_usuario', {'placeholder': 'correo@centro.com'}),
            ('email_clave', {'placeholder': '••••••••••'}),
            ('email_api_key', {'placeholder': 'API Key del proveedor'}),
            ('email_remitente', {'placeholder': 'notificaciones@centro.com'}),
            ('whatsapp_url', {'placeholder': 'https://gateway.ejemplo.com/whatsapp'}),
            ('whatsapp_token', {'placeholder': '••••••••••'}),
            ('whatsapp_remitente', {'placeholder': 'Ej: 18290000000'}),
        ]:
            self.fields[nombre].widget.attrs.update(attrs)
        self.fields['email_puerto'].widget = forms.NumberInput(
            attrs={**TEXTO, 'placeholder': '587', 'min': '1', 'max': '65535'}
        )

        # Estos campos solo son obligatorios según el proveedor elegido
        # (se valida en clean()); a nivel de formulario todos son opcionales
        # para no bloquear el guardado con campos ocultos por el JS.
        for nombre in (
            'email_servidor', 'email_usuario', 'email_clave',
            'email_api_key', 'email_remitente',
        ):
            self.fields[nombre].required = False

    def clean(self):
        cleaned = super().clean()
        proveedor = cleaned.get('email_proveedor')

        if proveedor in ('smtp_gmail', 'smtp_outlook'):
            if not cleaned.get('email_usuario') or not cleaned.get('email_clave'):
                raise forms.ValidationError(
                    'Para Gmail/Outlook debes indicar el correo y la '
                    'clave de aplicación (app password).'
                )
        elif proveedor == 'smtp_otro':
            if not cleaned.get('email_servidor'):
                raise forms.ValidationError(
                    'Debes indicar el servidor SMTP.'
                )
        elif proveedor in ('resend', 'sendgrid'):
            if not cleaned.get('email_api_key'):
                raise forms.ValidationError(
                    'Debes indicar la API Key del proveedor elegido.'
                )

        if proveedor and proveedor != 'consola' and not cleaned.get('email_remitente'):
            raise forms.ValidationError(
                'Debes indicar el correo remitente (From).'
            )

        return cleaned


# =====================================================
# FORM PERMISO PAGINA
# =====================================================

class PermisoPaginaForm(forms.ModelForm):

    class Meta:
        model = PermisoPagina
        fields = ['url_name', 'descripcion', 'roles_permitidos', 'usuarios_permitidos', 'activo']
        widgets = {
            'url_name': forms.TextInput(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
                'placeholder': 'Ej: estudiante_list, nomina:dashboard',
            }),
            'descripcion': forms.TextInput(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
                'placeholder': 'Listado de estudiantes',
            }),
            'roles_permitidos': forms.CheckboxSelectMultiple(),
            'usuarios_permitidos': forms.CheckboxSelectMultiple(),
            'activo': CHECKBOX_WIDGET,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import RolCentro
        from usuarios.models import Usuario
        self.fields['roles_permitidos'].queryset = RolCentro.objects.all()
        self.fields['usuarios_permitidos'].queryset = Usuario.objects.filter(is_active=True)


# =====================================================
# FORM TEMA CENTRO
# =====================================================

class TemaCentroForm(forms.ModelForm):

    class Meta:
        model = TemaCentro
        fields = [
            'nombre',
            'color_primario', 'color_secundario', 'color_acento',
            'color_texto', 'color_fondo',
            'color_fondo_sidebar', 'color_texto_sidebar', 'color_borde',
            'color_peligro', 'color_exito', 'color_advertencia',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': (
                    'w-full rounded-lg border border-gray-300 bg-white '
                    'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                    'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                ),
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        COLOR_ATTR = {
            'class': 'h-10 w-20 rounded border border-gray-300 cursor-pointer',
            'type': 'color',
        }
        for field_name in self.fields:
            if field_name.startswith('color_'):
                self.fields[field_name].widget = forms.TextInput(attrs={
                    'class': (
                        'w-full rounded-lg border border-gray-300 bg-white '
                        'px-3.5 py-2.5 text-sm text-gray-800 shadow-sm outline-none '
                        'transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200'
                    ),
                    'type': 'color',
                    'style': 'height: 44px; padding: 4px;',
                })