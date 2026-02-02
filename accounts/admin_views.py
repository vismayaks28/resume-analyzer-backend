from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_users(request):
    users = User.objects.all().values('id','username','email','role')

    return Response(users)
