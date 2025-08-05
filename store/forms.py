from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Address, CancellationRequest,ReturnRequest,Review

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Please provide a valid email address.')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)
class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['street_address', 'city', 'state', 'postal_code', 'country', 'phone_number']
class CancellationReasonForm(forms.ModelForm):
    class Meta:
        model = CancellationRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide a reason for cancellation...'}),
        }
from .models import ReturnRequest

class ReturnReasonForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide a reason for the return...'}),
        }
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your review here...'}),
        }

class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']