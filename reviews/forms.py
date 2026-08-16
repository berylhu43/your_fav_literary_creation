from django import forms
from .models import Review
from decimal import Decimal

RATING_CHOICES = [(Decimal(x) / 2, str(Decimal(x) / 2)) for x in range(0, 11)]

class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=Decimal,
    )

    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'review_text': forms.Textarea(attrs={'rows':4}),
        }