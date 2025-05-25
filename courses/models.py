from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=250)
    preview = models.ImageField(upload_to='courses/privileges', blank=True, null=True)
    description = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Курсы"
        verbose_name = "Курс"


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    name = models.CharField(max_length=250)
    description = models.TextField()
    preview = models.ImageField(upload_to='courses/lesson_previews', blank=True, null=True)
    video_link = models.URLField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"