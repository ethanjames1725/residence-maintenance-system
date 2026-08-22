from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from maintenance.models import BedSpace, StudentProfile

INVALID_CODE = "That code is not valid. Please check with reception."


class RegistrationForm(UserCreationForm):
    """Registration by claim code - see README section 5."""

    claim_code = forms.CharField(
        max_length=12,
        help_text="The code you were given at reception.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "claim_code")

    def clean_claim_code(self):
        code = self.cleaned_data["claim_code"].strip().upper()

        try:
            bed_space = BedSpace.objects.get(claim_code=code)
        except BedSpace.DoesNotExist:
            raise forms.ValidationError(INVALID_CODE)

        if StudentProfile.objects.filter(bed_space=bed_space).exists():
            raise forms.ValidationError(INVALID_CODE)

        self.bed_space = bed_space
        return code
