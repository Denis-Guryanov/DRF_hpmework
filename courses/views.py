from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Subscription
from . import permissions
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer, CourseDetailSerializer
from .paginators import LessonPagination, CoursePagination

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = CoursePagination

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseDetailSerializer
        return CourseSerializer

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated(), permissions.IsOwner()]
        return [IsAuthenticated(), permissions.IsModeratorOrOwner()]

    def get_queryset(self):
        if self.request.user.groups.filter(name='moderators').exists():
            return Course.objects.all()
        return Course.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        course = self.get_object()
        user = request.user

        if request.method == 'POST':
            # Проверка существующей подписки
            if Subscription.objects.filter(user=user, course=course).exists():
                return Response(
                    {"detail": "Вы уже подписаны на этот курс"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, course=course)
            return Response(
                {"detail": "Подписка успешно оформлена"},
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            try:
                subscription = Subscription.objects.get(user=user, course=course)
                subscription.delete()
                return Response(
                    {"detail": "Подписка успешно отменена"},
                    status=status.HTTP_204_NO_CONTENT
                )
            except Subscription.DoesNotExist:
                return Response(
                    {"detail": "Вы не подписаны на этот курс"},
                    status=status.HTTP_404_NOT_FOUND
                )

class LessonListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    pagination_class = LessonPagination
    permission_classes = [IsAuthenticated, permissions.IsModeratorOrOwner]

    def get_queryset(self):
        if self.request.user.groups.filter(name='moderators').exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, permissions.IsModeratorOrOwner]

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), permissions.IsOwner()]
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.groups.filter(name='moderators').exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        if instance.owner != self.request.user:
            raise PermissionDenied("You can only delete your own lessons")
        instance.delete()