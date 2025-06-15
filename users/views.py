from pyexpat.errors import messages

import stripe
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from courses.models import Course
from .filters import PaymentFilter
from .models import Payment, Subscription
from .serializers import (
    UserSerializer,
    PaymentSerializer,
    UserProfileSerializer,
    PublicUserProfileSerializer,
    PrivateUserProfileSerializer,
    UserRegistrationSerializer
)
from .services import create_product, create_price, create_checkout_session
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        if payment.payment_method == 'transfer' and (payment.paid_course or payment.paid_lesson):
            try:
                # Определение продукта
                product_name = payment.paid_course.name if payment.paid_course else payment.paid_lesson.name

                # Создание в Stripe
                product = create_product(product_name)
                price = create_price(product.id, payment.amount)
                session = create_checkout_session(price.id)

                # Сохранение идентификаторов
                payment.stripe_product_id = product.id
                payment.stripe_price_id = price.id
                payment.stripe_session_id = session.id
                payment.save()

                # Возврат ссылки на оплату
                return Response({
                    'payment_id': payment.id,
                    'payment_url': session.url
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                payment.delete()
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)


class PaymentStatusAPIView(APIView):
    """
    Проверка статуса платежа в Stripe.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, user=request.user)

        if not payment.stripe_session_id:
            return Response({'error': 'Stripe session not found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = stripe.checkout.Session.retrieve(payment.stripe_session_id)
            payment.stripe_payment_status = session.payment_status
            payment.save()
            return Response({'status': session.payment_status})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

class SubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get('course_id')
        course = get_object_or_404(Course, id=course_id)

        # Проверяем существование подписки
        subscription_exists = Subscription.objects.filter(
            user=user,
            course=course
        ).exists()

        if subscription_exists:
            Subscription.objects.filter(user=user, course=course).delete()
            return Response({"message": "Подписка удалена"}, status=status.HTTP_200_OK)
        else:
            Subscription.objects.create(user=user, course=course)
            return Response({"message": "Подписка добавлена"}, status=status.HTTP_201_CREATED)