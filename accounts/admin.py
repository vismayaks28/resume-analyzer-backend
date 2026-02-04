from django.contrib import admin
from .models import CustomUser, Resume



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_staff']
    list_filter = ('role', 'is_staff')
    search_fields = ('username', 'email')

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'file', 'uploaded_at', 'ats_score')
    list_filter = ('uploaded_at',)
