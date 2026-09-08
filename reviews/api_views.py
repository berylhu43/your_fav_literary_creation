from rest_framework import permissions, viewsets

from .models import Review
from .serializers import ReviewSerializer
from .services import upsert_review


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            Review.objects.filter(user=self.request.user)
            .select_related("catalog")
            .order_by("-created_at")
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(catalog__title__icontains=q)
        return qs

    def perform_create(self, serializer):
        review = upsert_review(
            user=self.request.user,
            catalog=serializer.validated_data["catalog"],
            rating=serializer.validated_data["rating"],
            review_text=serializer.validated_data.get("review_text", ""),
        )
        serializer.instance = review
