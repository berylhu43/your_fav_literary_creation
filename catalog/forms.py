from django import forms
from .models import Catalog, Genre

class AddEntryForm(forms.Form):
    media_type = forms.ChoiceField(
        choices=Catalog.MediaType.choices,
        label='Type',
    )

    title = forms.CharField(
        max_length=225,
        label='Title',
    )
    genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Genre',
    )

    rating = forms.IntegerField(
        min_value=0,
        max_value=5,
        label='Rating (0-5),'
    )

    review_text = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label='Review',
    )