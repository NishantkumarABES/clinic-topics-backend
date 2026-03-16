from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from apps.advertisements.models import Advertisement, AdvertisementStatus
from core.permissions import IsAdmin


class AdvertisementAnalyticsView(APIView):
    """Analytics endpoint for Advertisement metrics."""
    permission_classes = [IsAdmin]

    @swagger_auto_schema(auto_schema=None)
    def get(self, request):
        total_ads = Advertisement.objects.count()
        enabled_ads = Advertisement.objects.filter(status=AdvertisementStatus.ENABLED).count()
        disabled_ads = Advertisement.objects.filter(status=AdvertisementStatus.DISABLED).count()

        data = {
            "total_ads": total_ads,
            "enabled_ads": enabled_ads,
            "disabled_ads": disabled_ads,
        }
        return Response(data)
