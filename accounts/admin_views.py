from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin
from django.utils.timezone import now
from .models import Resume

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_users(request):

    users = User.objects.all().values(
        'id','username','email','role'
    )

    return Response(users)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_analytics(request):

    total_users = User.objects.count()
    total_resumes = Resume.objects.count()
    admin_count = User.objects.filter(is_staff=True).count()

    uploads_today = Resume.objects.filter(
        uploaded_at__date=now().date()
    ).count()

    users_without_resumes = User.objects.filter(
        resumes__isnull=True
    ).count()

    data = {
        "total_users": total_users,
        "total_resumes": total_resumes,
        "admins": admin_count,
        "uploads_today": uploads_today,
        "users_without_resumes": users_without_resumes
    }

    return Response(data)
