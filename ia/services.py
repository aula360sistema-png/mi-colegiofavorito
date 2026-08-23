from openai import OpenAI
from django.conf import settings

_client = None


def _obtener_cliente():
    """Crea el cliente OpenAI en el primer uso (no al importar).

    Si no hay OPENAI_API_KEY configurada devuelve None y los flujos
    que dependen de IA se degradan con un mensaje, sin romper el arranque
    del sistema (deploy sin credenciales de OpenAI).
    """
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            return None
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def preguntar_ia(mensaje):

    try:
        client = _obtener_cliente()
        if client is None:
            return (
                "Error IA: OPENAI_API_KEY no está configurada. "
                "Define la variable en el entorno para habilitar el módulo."
            )

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": mensaje
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error IA: {str(e)}"