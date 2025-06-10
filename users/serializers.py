from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Payment

User = get_user_model()

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

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'phone_number', 'city', 'avatar']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number', ''),
            city=validated_data.get('city', ''),
            avatar=validated_data.get('avatar', None)
        )
        return user

class PublicUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'city']

class PrivateUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'phone_number', 'city', 'avatar']