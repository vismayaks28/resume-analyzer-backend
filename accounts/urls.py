from django.urls import path
from . import views
from .admin_views import admin_users
from .admin_views import admin_analytics

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('analyze-resume/', views.analyze_resume),
    path('job-matcher/', views.job_matcher),
    path('skill-gap/', views.skill_gap_analyzer),
    path('admin/users/', admin_users),
    path('admin/analytics/', admin_analytics),
    path('job-description-match/', views.job_description_matcher, name='job_description_matcher'),
    
]
