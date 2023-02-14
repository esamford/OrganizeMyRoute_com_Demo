from django import forms
from django.forms import ModelForm
from .models import Message


class MessageForm(ModelForm):
    class Meta:
        model = Message
        fields = ('subject', 'reason', 'message')
        widgets = {
            'subject': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Subject',
                }
            ),
            'reason': forms.Select(
                choices=Message.CONST_PURPOSE_CHOICES,
                attrs={
                    'class': 'form-control',
                }
            ),
            'message': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'What would you like to say?',
                }
            )
        }



