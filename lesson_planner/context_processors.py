from lesson_plans.models import UserProfile

def user_role_context(request):
    if request.user.is_authenticated:
        try:
            return {'user_role': request.user.userprofile.role}
        except UserProfile.DoesNotExist:
            pass
    return {'user_role': None}
