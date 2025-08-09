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



class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        
        fields = [
            'reason', 
            'refund_method', 
            'account_holder_name', 
            'bank_account_number', 
            'ifsc_code'
        ]
       
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide a detailed reason for the return...'}),
            'refund_method': forms.RadioSelect(), 
            'account_holder_name': forms.TextInput(attrs={'placeholder': "Account Holder's Name"}),
            'bank_account_number': forms.TextInput(attrs={'placeholder': 'Your Bank Account Number'}),
            'ifsc_code': forms.TextInput(attrs={'placeholder': 'Your Bank IFSC Code'}),
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
        
class CouponApplyForm(forms.Form):
    code = forms.CharField(
        label="",  
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter Coupon Code'
        })
    )
