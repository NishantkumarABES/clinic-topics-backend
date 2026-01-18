from django.urls import path, re_path
from apps.video_calls.views import CallInitiateView, CallTokenView, CallAcceptView, CallRejectView, CallEndView
from apps.video_calls.consumers import CallSignalingConsumer



urlpatterns = [
    path("initiate/", CallInitiateView.as_view(), name="initate-call"),
    path("token/", CallTokenView.as_view(), name="call-token"),

    path("<uuid:id>/accept/", CallAcceptView.as_view(), name="accept-call"),
    path("<uuid:id>/reject/", CallRejectView.as_view(), name="reject-call"),
    path("<uuid:id>/end/", CallEndView.as_view(), name="end-call"),
]



websocket_urlpatterns = [
    re_path(r"ws/calls/(?P<user_id>[0-9a-f-]+)/$", CallSignalingConsumer.as_asgi()),
]
