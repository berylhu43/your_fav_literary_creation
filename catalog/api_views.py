from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Catalog, Artist
from .serializers import CatalogSerializer, ArtistSerializer
from reviews.models import Review
from reviews.serializers import PublicReviewSerializer
from .services import (
    get_popular_movies, get_popular_tv,
    get_cached_movie_genres, get_cached_tv_genres,
    _slim_movie_result, _slim_tv_result,
    search_external, get_or_create_work, get_artist_filmography
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
    

class CatalogReviewsAPI(APIView):
    permission_classes = [permissions.AllowAny]   # login to show my review, otherwise null

    def get(self, request, pk):
        reviews = Review.objects.filter(catalog_id=pk).select_related('user').order_by('-created_at')

        my_review = None
        others = reviews
        if request.user.is_authenticated:
            my_review = reviews.filter(user=request.user).first()
            others = reviews.exclude(user=request.user)

        return Response({
            'my_review': PublicReviewSerializer(my_review).data if my_review else None,
            'other_reviews': PublicReviewSerializer(others, many=True).data,
        })

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
        genre_id = request.query_params.get('genre_id', '')
        movies = get_popular_movies(genre_id)
        return Response([_slim_movie_result(m) for m in movies])   


class CatalogPopularTVAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        genre_id = request.query_params.get('genre_id', '')
        tv = get_popular_tv(genre_id)
        return Response([_slim_tv_result(t) for t in tv])


# *** movie and tv genres
class MovieGenresAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response(get_cached_movie_genres())


class TVGenresAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response(get_cached_tv_genres())


# *** artist detail page view ***
class ArtistDetailAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        artist = get_object_or_404(Artist, pk=pk)
        filmography = get_artist_filmography(artist)   
        return Response({
            'artist': ArtistSerializer(artist).data,
            **filmography,      
        })
