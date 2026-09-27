from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import LogoutSerializer


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class LoginView(TokenObtainPairView):
    pass


@extend_schema_view(post=extend_schema(tags=["Authentication"]))
class RefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=LogoutSerializer,
        responses={status.HTTP_204_NO_CONTENT: None},
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
