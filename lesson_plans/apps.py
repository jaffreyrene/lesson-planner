from django.apps import AppConfig


class LessonPlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lesson_plans'

    def ready(self):
        import lesson_plans.signals

# touched on 2025-06-13T18:49:54.501727Z