from django.contrib.auth import login
from django.shortcuts import redirect, render

from maintenance.models import StudentProfile

from .forms import RegistrationForm


def register(request):
    """Register a student and claim their bed space."""
    if request.method != "POST":
        form = RegistrationForm()
    else:
        form = RegistrationForm(data=request.POST)

        if form.is_valid():
            new_user = form.save()
            StudentProfile.objects.create(
                user=new_user,
                bed_space=form.bed_space,
            )
            login(request, new_user)
            return redirect("maintenance:index")

    context = {"form": form}
    return render(request, "registration/register.html", context)
