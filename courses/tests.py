from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course, Lesson

User = get_user_model()


class LessonCRUDTests(APITestCase):
    def setUp(self):
        self.moderator_group = Group.objects.create(name='moderators')

        self.owner = User.objects.create_user(
            email='owner@test.com',
            password='testpass',
            is_active=True
        )
        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='testpass',
            is_active=True
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass',
            is_active=True
        )

        self.moderator.groups.add(self.moderator_group)

        self.course = Course.objects.create(
            name="Test Course",
            description="Course description",
            owner=self.owner
        )

        self.lesson = Lesson.objects.create(
            course=self.course,
            name="Test Lesson",
            description="Lesson description",
            video_link="https://www.youtube.com/test",
            owner=self.owner
        )

        self.lesson_list_url = reverse('lesson-list')
        self.lesson_detail_url = reverse('lesson-detail', kwargs={'pk': self.lesson.pk})

    def test_lesson_create_authenticated(self):
        self.client.force_authenticate(user=self.owner)
        data = {
            "course": self.course.id,
            "name": "New Lesson",
            "description": "New lesson description",
            "video_link": "https://www.youtube.com/new"
        }
        response = self.client.post(self.lesson_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_lesson_create_moderator(self):
        self.client.force_authenticate(user=self.moderator)
        data = {
            "course": self.course.id,
            "name": "Moderator Lesson",
            "description": "Moderator lesson description",
            "video_link": "https://www.youtube.com/moderator"
        }
        response = self.client.post(self.lesson_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_lesson_create_unauthenticated(self):
        data = {
            "course": self.course.id,
            "name": "Unauthorized Lesson",
            "description": "Should fail",
            "video_link": "https://www.youtube.com/unauth"
        }
        response = self.client.post(self.lesson_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lesson_list_owner(self):
        Lesson.objects.create(
            course=self.course,
            name="Other Lesson",
            description="Other lesson",
            video_link="https://youtube.com/other",
            owner=self.other_user
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(self.lesson_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_lesson_list_moderator(self):
        Lesson.objects.create(
            course=self.course,
            name="Additional Lesson",
            description="Additional lesson",
            video_link="https://youtube.com/additional",
            owner=self.other_user
        )
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(self.lesson_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_lesson_update_owner(self):
        self.client.force_authenticate(user=self.owner)
        data = {"name": "Updated Lesson Name"}
        response = self.client.patch(self.lesson_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.name, "Updated Lesson Name")

    def test_lesson_update_moderator(self):
        self.client.force_authenticate(user=self.moderator)
        data = {"description": "Updated by moderator"}
        response = self.client.patch(self.lesson_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.description, "Updated by moderator")


    def test_lesson_delete_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.lesson_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Lesson.objects.count(), 0)

    def test_lesson_delete_moderator(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.delete(self.lesson_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Lesson.objects.count(), 1)




class SubscriptionTests(APITestCase):
    def setUp(self):
        # Создаем пользователя
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass',
            is_active=True
        )

        # Создаем курс
        self.course = Course.objects.create(
            name="Course with Subscription",
            description="Course for subscription tests",
            owner=self.user
        )

        # URL для работы с курсами
        self.course_detail_url = reverse('course-detail', kwargs={'pk': self.course.pk})
        self.subscribe_url = reverse('course-subscribe', kwargs={'pk': self.course.pk})

    def test_subscription_field(self):
        """Тест наличия поля подписки в ответе API"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.course_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_subscribed', response.data)
        self.assertFalse(response.data['is_subscribed'])

    def test_subscription_flow(self):
        """Тест полного цикла подписки/отписки"""
        self.client.force_authenticate(user=self.user)

        # Подписываемся
        response = self.client.post(self.subscribe_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем статус подписки
        response = self.client.get(self.course_detail_url)
        self.assertTrue(response.data['is_subscribed'])

        # Отписываемся
        response = self.client.delete(self.subscribe_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверяем статус подписки
        response = self.client.get(self.course_detail_url)
        self.assertFalse(response.data['is_subscribed'])

    def test_double_subscription(self):
        """Тест: повторная подписка невозможна"""
        self.client.force_authenticate(user=self.user)

        # Первая подписка
        response = self.client.post(self.subscribe_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Вторая попытка подписки
        response = self.client.post(self.subscribe_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsubscribe_without_subscription(self):
        """Тест: отписка без активной подписки возвращает ошибку"""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.subscribe_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)