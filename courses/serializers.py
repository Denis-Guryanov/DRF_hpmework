from rest_framework import serializers
from .models import Course, Lesson
from .validators import validate_youtube

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ['owner']
        extra_kwargs = {
            'video_link': {'validators': [validate_youtube]}
        }

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class CourseSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True, source='lessons.all')

    class Meta:
        model = Course
        fields = ['id', 'name', 'preview', 'description', 'lessons', 'is_subscribed']
        read_only_fields = ['owner']

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.subscriptions.filter(user=user).exists()
        return False


class CourseDetailSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'name', 'preview', 'description', 'lessons_count']

    def get_lessons_count(self, obj):
        return obj.lessons.count()


