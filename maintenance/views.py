from django.shortcuts import render


def index(request):
    """The ResFix home page."""
    return render(request, "maintenance/index.html")
