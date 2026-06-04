from openai import OpenAI
from django.conf import settings

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)

def preguntar_ia(mensaje):

    try:

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