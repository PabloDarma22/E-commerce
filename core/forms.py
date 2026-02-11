from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Address

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "cep",
            "street",
            "number",
            "complement",
            "district",
            "city",
            "state",
            "is_default",
        ]
        widgets = {
            "cep": forms.TextInput(attrs={"placeholder": "00000-000"}),
            "state": forms.TextInput(attrs={"placeholder": "RJ", "maxlength": 2}),
        }

    def clean_state(self):
        state = (self.cleaned_data.get("state") or "").strip().upper()
        if len(state) != 2:
            raise forms.ValidationError("UF deve ter 2 letras. Ex: RJ, SP.")
        return state