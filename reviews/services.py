from .models import Review

def upsert_review(*, user, catalog, rating, review_text):
    """
    Create the user's review for this catalog work, or update it if one already
    exists. Returns the review.
    """
    review, created = Review.objects.update_or_create(
        user=user,
        catalog=catalog,
        defaults={
            'rating': rating,
            'review_text': review_text,
        },
    )
    return review
