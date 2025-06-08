from django_filters import rest_framework as filters
from .models import Payment


class PaymentFilter(filters.FilterSet):
    paid_course = filters.NumberFilter(field_name='paid_course__id')
    paid_lesson = filters.NumberFilter(field_name='paid_lesson__id')

    class Meta:
        model = Payment
        fields = {
            'payment_method': ['exact'],
        }

    ordering = filters.OrderingFilter(
        fields=(
            ('payment_date', 'payment_date'),
        ),
        field_labels={
            'payment_date': 'Дата оплаты',
        }
    )
