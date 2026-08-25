from rest_framework import viewsets, permissions
from .models import Review
from .serializers import ReviewSerializer
from .services import upsert_review

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Review.objects
            .filter(user=self.request.user)
            .select_related('catalog')
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        review = upsert_review(
            user=self.request.user,
            catalog=serializer.validated_data['catalog'],
            rating=serializer.validated_data['rating'],
            review_text=serializer.validated_data.get('review_text', ''),
        )
        serializer.instance = review
