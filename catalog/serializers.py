from django.db.models import Avg
from rest_framework import serializers

from .models import Artist, Catalog


class CatalogSerializer(serializers.ModelSerializer):
    # calculate average rating
    average_rating = serializers.SerializerMethodField()
    # show genres as strings instead of ids
    genres = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    credits = serializers.SerializerMethodField()

    class Meta:
        model = Catalog
        fields = [
            "id",
            "title",
            "media_type",
            "release_year",
            "pages",
            "runtime",
            "episodes",
            "cover_url",
            "description",
            "genres",
            "average_rating",
            "credits",
        ]

    def get_average_rating(self, obj):
        return obj.reviews.aggregate(Avg("rating"))["rating__avg"]

    def get_credits(self, obj):
        # find all credit + artist
        credits = obj.credits.select_related("artist")
        directors, actors, authors = [], [], []
        for c in credits:
            if c.role == "director":
                directors.append(c.artist)
            elif c.role == "actor":
                actors.append(c.artist)
            elif c.role == "author":
                authors.append(c.artist)
        return {
            "directors": ArtistSerializer(directors, many=True).data,
            "actors": ArtistSerializer(actors, many=True).data,
            "authors": ArtistSerializer(authors, many=True).data,
        }


class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ["id", "name", "profile_url"]
