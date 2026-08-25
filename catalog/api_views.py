from rest_framework import generics, permissions
from .models import Catalog
from .serializers import CatalogSerializer
from reviews.models import Review
from reviews.serializers import PublicReviewSerializer

class CatalogDetailAPI(generics.RetrieveAPIView):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer
    permission_classes = [permissions.AllowAny]
    

class CatalogReviewsAPI(generics.ListAPIView):
    serializer_class = PublicReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        catalog_id = self.kwargs['pk']
        return (
            Review.objects
            .filter(catalog_id=catalog_id)
            .select_related('user')
            .order_by('-created_at')
        )
