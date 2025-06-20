from django.apps import AppConfig


class LessonPlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lesson_plans'

    def ready(self):
        import lesson_plans.signals
