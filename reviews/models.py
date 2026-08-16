from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.
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

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
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