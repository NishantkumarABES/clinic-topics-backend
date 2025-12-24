from rest_framework import generics, permissions
from django.utils.timezone import now


from apps.topics.models import Topic, TopicCategory
from apps.topics.serializers import TopicCategorySerializer, TopicListSerializer, TopicDetailSerializer



class TopicCategoryListView(generics.ListAPIView):
    queryset = TopicCategory.objects.all()
    serializer_class = TopicCategorySerializer
    permission_classes = [permissions.AllowAny]


class TopicListView(generics.ListAPIView):
    serializer_class = TopicListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Topic.objects.filter(publishing_time__lte=now())

        category_id = self.request.query_params.get("category")
        audience = self.request.query_params.get("audience")

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if audience:
            queryset = queryset.filter(topic_audience=audience)

        return queryset


class TopicDetailView(generics.RetrieveAPIView):
    queryset = Topic.objects.filter(publishing_time__lte=now())
    serializer_class = TopicDetailSerializer
    permission_classes = [permissions.AllowAny]
