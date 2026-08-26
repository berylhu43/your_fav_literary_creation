from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Catalog
from .serializers import CatalogSerializer
from reviews.models import Review
from reviews.serializers import PublicReviewSerializer
from .services import (
    get_popular_movies, get_popular_tv,
    get_cached_movie_genres, get_cached_tv_genres,
    search_external, get_or_create_work
)

# *** select work and add to database
class CatalogSelectAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        external_id = request.data.get('external_id')
        media_type = request.data.get('media_type')

        # two required fields
        if not external_id or not media_type:
            return Response(
                {'error': 'external_id and media_type are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        work = get_or_create_work(media_type=media_type, external_id=external_id)
        if work is None:
            return Response(
                {'error': 'Could not fetch this work.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(CatalogSerializer(work).data)
        


# *** detail page views ***
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

# *** search work views ***
class CatalogSearchAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        media_type = request.query_params.get('media_type', 'movie')
        return Response(search_external(query=query, media_type=media_type))

# *** popular movie and tv views ***
class CatalogPopularMovieAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        genre_movie = request.query_params.get('genre_movie', '')
        return Response({
            'movies': get_popular_movies(genre_movie),
            'genres_movie': get_cached_movie_genres(),
        })

class CatalogPopularTVAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        genre_tv = request.query_params.get('genre_tv', '')
        return Response({
            'tv': get_popular_tv(genre_tv),
            'genres_tv': get_cached_tv_genres(),
        })
