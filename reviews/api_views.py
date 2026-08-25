from rest_framework import generics, permissions
from .models import Review
from .serializer import ReviewSerializer

class ReviewListAPI(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return(
            Review.objects
            .filter(user=self.request.user)
            .select_related('catalog')
            .order_by('-created_at')
        )