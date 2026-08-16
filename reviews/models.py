from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


def validate_half_step(value):
    "value must be in steps of 0.5."
    if (value * 2) % 1 != 0:
        raise ValidationError('Rating must be in steps of 0.5 (e.g. 3.0, 3.5).')


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
    )

    catalog = models.ForeignKey(
        'catalog.Catalog',
        on_delete=models.CASCADE,
        related_name='reviews',
    )

    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5), validate_half_step],
    )

    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'catalog'],
                name='unique_user_catalog_review',
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} -> {self.catalog} ({self.rating})'
    