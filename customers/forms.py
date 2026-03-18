from django import forms

from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'mobile', 'gender', 'city', 'area', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Name'}),
            'mobile': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '9876543210'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City'}),
            'area': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Area'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
