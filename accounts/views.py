from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


# Create your views here.
def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("accounts:login")

    else:
        form = UserCreationForm()

    return render(request, "registration/register.html", {"form": form})
