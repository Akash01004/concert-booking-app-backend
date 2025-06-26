
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')  

        
class TicketBookingForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=3,
        label="Number of Tickets"
    )

