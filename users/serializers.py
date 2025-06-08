from rest_framework import serializers
from .models import User, Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class PaymentShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['payment_date', 'amount', 'payment_method']

class UserProfileSerializer(serializers.ModelSerializer):
    payments = PaymentShortSerializer(many=True, read_only=True)
    class Meta:
        model = User
        fields = ['email', 'phone_number', 'city', 'avatar', 'payments']
        read_only_fields = ['email']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'phone_number', 'city', 'avatar')

