from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='catalog.title', read_only=True)
    media_type = serializers.CharField(source='catalog.media_type', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'catalog', 'title', 'media_type', 'rating', 
                  'review_text', 'created_at']
        read_only_fields = ['id', 'created_at']

# for work detail page, show public reviews with username instead of user id
class PublicReviewSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'review_text', 'created_at']