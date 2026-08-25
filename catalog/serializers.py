from rest_framework import serializers
from .models import Catalog
from django.db.models import Avg

class CatalogSerializer(serializers.ModelSerializer):
    # calculate average rating
    average_rating = serializers.SerializerMethodField()
    # show genres as strings instead of ids
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
        )

    class Meta:
        model = Catalog
        fields = ['id', 'title', 'media_type', 
                  'creator', 'release_year', 'pages',
                  'runtime', 'episodes', 'cover_url', 
                  'description', 'genres', 
                  'average_rating']

    def get_average_rating(self, obj):
        return obj.reviews.aggregate(Avg('rating'))['rating__avg']