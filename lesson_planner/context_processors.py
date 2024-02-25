from lesson_plans.models import UserProfile

def user_role_context(request):
    if request.user.is_authenticated:
        try:
            return {'user_role': request.user.userprofile.role}
        except UserProfile.DoesNotExist:
            pass
    return {'user_role': None}

# touched on 2025-06-13T18:49:51.142687Z
# touched on 2025-06-13T18:50:34.772344Z
# touched on 2025-06-13T18:51:02.883308Z