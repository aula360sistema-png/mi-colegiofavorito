from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def inicio(request):
    return HttpResponse("Orientación psicopedagógica (en construcción).")
