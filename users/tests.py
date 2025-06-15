import json
import stripe
from unittest import mock
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from courses.models import Course
from users.models import User, Payment


class StripePaymentTests(TestCase):
    def setUp(self):
        # Настройка клиента API
        self.client = APIClient()

        # Создание тестового пользователя
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)

        # Создание тестового курса
        self.course = Course.objects.create(
            name='Test Course',
            description='Course Description',
            owner=self.user
        )

        # Данные для создания платежа
        self.payment_data = {
            'user': self.user.id,
            'amount': 1000,
            'payment_method': 'transfer',
            'paid_course': self.course.id
        }

    def test_create_payment_with_stripe_session(self):
        """Тестирование создания платежа с Stripe сессией"""
        # Мокируем вызовы Stripe API
        with mock.patch('stripe.Product.create') as mock_product_create, \
                mock.patch('stripe.Price.create') as mock_price_create, \
                mock.patch('stripe.checkout.Session.create') as mock_session_create:
            # Настраиваем возвращаемые значения моков
            mock_product_create.return_value = mock.MagicMock(id='prod_test123')
            mock_price_create.return_value = mock.MagicMock(id='price_test123')
            mock_session = mock.MagicMock()
            mock_session.id = 'sess_test123'
            mock_session.url = 'https://checkout.stripe.com/pay/test'
            mock_session_create.return_value = mock_session

            # Отправляем запрос на создание платежа
            url = reverse('payment-list')
            response = self.client.post(url, self.payment_data, format='json')

            # Проверяем ответ
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('payment_id', response.data)
            self.assertIn('payment_url', response.data)
            self.assertEqual(response.data['payment_url'], 'https://checkout.stripe.com/pay/test')

            # Проверяем создание платежа в БД
            payment = Payment.objects.get(id=response.data['payment_id'])
            self.assertEqual(payment.stripe_product_id, 'prod_test123')
            self.assertEqual(payment.stripe_price_id, 'price_test123')
            self.assertEqual(payment.stripe_session_id, 'sess_test123')

            # Проверяем вызовы к Stripe API
            mock_product_create.assert_called_once_with(name='Test Course')
            mock_price_create.assert_called_once_with(
                unit_amount=100000,  # 1000 * 100 (рублей в копейки)
                currency='rub',
                product='prod_test123'
            )
            mock_session_create.assert_called_once_with(
                payment_method_types=['card'],
                line_items=[{'price': 'price_test123', 'quantity': 1}],
                mode='payment',
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel',
            )

    def test_create_cash_payment(self):
        """Тестирование создания платежа наличными без Stripe"""
        # Модифицируем данные для платежа наличными
        cash_payment_data = self.payment_data.copy()
        cash_payment_data['payment_method'] = 'cash'

        url = reverse('payment-list')
        response = self.client.post(url, cash_payment_data, format='json')

        # Проверяем ответ
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

        # Проверяем создание платежа в БД
        payment = Payment.objects.get(id=response.data['id'])
        self.assertIsNone(payment.stripe_product_id)
        self.assertIsNone(payment.stripe_price_id)
        self.assertIsNone(payment.stripe_session_id)

    def test_stripe_error_handling(self):
        """Тестирование обработки ошибок Stripe"""
        with mock.patch('stripe.Product.create') as mock_product_create:
            # Эмулируем ошибку в Stripe
            mock_product_create.side_effect = stripe.error.StripeError("Stripe error")

            url = reverse('payment-list')
            response = self.client.post(url, self.payment_data, format='json')

            # Проверяем обработку ошибки
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error'], 'Stripe error')

            # Проверяем, что платеж не был сохранен
            self.assertEqual(Payment.objects.count(), 0)

    def test_payment_status_check(self):
        """Тестирование проверки статуса платежа"""
        # Создаем тестовый платеж
        payment = Payment.objects.create(
            user=self.user,
            amount=1000,
            payment_method='transfer',
            paid_course=self.course,
            stripe_session_id='sess_test123',
            stripe_payment_status='unpaid'
        )

        # Мокируем вызов Stripe API
        with mock.patch('stripe.checkout.Session.retrieve') as mock_session_retrieve:
            # Настраиваем возвращаемое значение
            mock_session = mock.MagicMock()
            mock_session.payment_status = 'paid'
            mock_session_retrieve.return_value = mock_session

            # Проверяем статус платежа
            url = reverse('payment-status', kwargs={'pk': payment.id})
            response = self.client.get(url)

            # Проверяем ответ
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'paid')

            # Проверяем обновление статуса в БД
            payment.refresh_from_db()
            self.assertEqual(payment.stripe_payment_status, 'paid')

            # Проверяем вызов к Stripe API
            mock_session_retrieve.assert_called_once_with('sess_test123')

    def test_payment_status_without_stripe_session(self):
        """Тестирование проверки статуса без Stripe сессии"""
        # Создаем платеж без Stripe сессии
        payment = Payment.objects.create(
            user=self.user,
            amount=1000,
            payment_method='cash',
            paid_course=self.course
        )

        url = reverse('payment-status', kwargs={'pk': payment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Stripe session not found')

    def test_payment_status_error_handling(self):
        """Тестирование обработки ошибок при проверке статуса"""
        # Создаем тестовый платеж
        payment = Payment.objects.create(
            user=self.user,
            amount=1000,
            payment_method='transfer',
            paid_course=self.course,
            stripe_session_id='sess_test123'
        )

        # Мокируем вызов Stripe API с ошибкой
        with mock.patch('stripe.checkout.Session.retrieve') as mock_session_retrieve:
            mock_session_retrieve.side_effect = stripe.error.StripeError("Stripe error")

            url = reverse('payment-status', kwargs={'pk': payment.id})
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error'], 'Stripe error')