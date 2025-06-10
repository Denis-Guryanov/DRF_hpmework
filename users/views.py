from django_filters import rest_framework as filters
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .filters import PaymentFilter
from .models import Payment
from .serializers import (
    UserSerializer,
    PaymentSerializer,
    UserProfileSerializer,
    PublicUserProfileSerializer,
    PrivateUserProfileSerializer,
    UserRegistrationSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date']

class UserRegistrationAPIView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user_id': user.id,
            'email': user.email,
            'message': 'User created successfully'
        }, status=status.HTTP_201_CREATED)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve' and self.kwargs['pk'] != self.request.user.pk:
            return PublicUserProfileSerializer
        return PrivateUserProfileSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def profile(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        if request.user.pk != int(kwargs['pk']):
            return Response(
                {"detail": "You can only edit your own profile"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)