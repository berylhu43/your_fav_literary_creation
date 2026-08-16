from django import forms
from .models import Catalog, Genre
from decimal import Decimal

RATING_CHOICES = [(Decimal(x) / 2, str(Decimal(x) / 2)) for x in range(0, 11)]

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

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=Decimal,
    )

    review_text = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label='Review',
    )