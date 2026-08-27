from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import get_recommendations, _resolve_external_id
from catalog.services import get_or_create_work
from catalog.serializers import CatalogSerializer


class RecommendationAPI(APIView):
    # default IsAuthenticated
    def post(self, request):
        query = (request.data.get('query') or '').strip()
        media_types = request.data.get('media_types') or []

        if not query or not media_types:
            return Response(
                {'error': 'query and at least one media_type are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recommendations = get_recommendations(request.user, query, media_types)
        return Response({'recommendations': recommendations})

class RecommendationPickAPI(APIView):

    def post(self, request):
        title = (request.data.get('title') or '').strip()
        media_type = (request.data.get('media_type') or '').strip()

        if not title or not media_type:
            return Response(
                {'error': 'title and media_type are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        external_id = _resolve_external_id(title, media_type)   
        if external_id is None:
            return Response(
                {'error': f'Could not find "{title}".'},
                status=status.HTTP_404_NOT_FOUND,
            )

        work = get_or_create_work(media_type=media_type, external_id=external_id)
        if work is None:
            return Response(
                {'error': 'Could not fetch this work.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(CatalogSerializer(work).data)