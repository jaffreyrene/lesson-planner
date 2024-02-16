from django import forms
from .models import Document, Tag, Philosophy, Persona, Voice, Tone, OutputFormat

class DocumentUploadForm(forms.ModelForm):
    title = forms.CharField(
        max_length=255,
        required=False,  # optional if you use auto-fill fallback
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter document title',
            'class': 'form-control'
        })
    )

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'select2-multiple',
            'data-placeholder': 'Select tags...'
        }),
        required=False
    )

    class Meta:
        model = Document
        fields = ['title', 'file', 'tags']


MODEL_CHOICES = [
    ('gpt-4o-mini-2024-07-18', 'GPT-4o Mini (Default)'),
    ('gpt-4o-2024-08-06', 'GPT-4o'),
    ('gpt-4-turbo-2024-04-09', 'GPT-4 Turbo'),

]

class SearchForm(forms.Form):
    query = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)

    philosophy = forms.ModelMultipleChoiceField(queryset=Philosophy.objects.all(),required=False)
    personas = forms.ModelMultipleChoiceField(queryset=Persona.objects.all(), required=False)
    voice = forms.ModelChoiceField(queryset=Voice.objects.all(), required=False)
    tone = forms.ModelMultipleChoiceField(queryset=Tone.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    outputformat = forms.ModelChoiceField(queryset=OutputFormat.objects.all(), required=False)
    model = forms.ChoiceField(choices=MODEL_CHOICES, required=False, initial='gpt-4o-mini-2024-07-18')



class PhilosophyUploadForm(forms.ModelForm):
    class Meta:
        model = Philosophy
        fields = ['title', 'file', 'is_global']


class PersonaUploadForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = ['title', 'file']


class VoiceUploadForm(forms.ModelForm):
    class Meta:
        model = Voice
        fields = ['title', 'file']


class ToneUploadForm(forms.ModelForm):
    class Meta:
        model = Tone
        fields = ['title', 'file']


class OutputFormatUploadForm(forms.ModelForm):
    class Meta:
        model = OutputFormat
        fields = ['title', 'file']


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name']

# touched on 2025-06-13T18:50:23.211839Z