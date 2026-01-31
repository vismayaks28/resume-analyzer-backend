from django.contrib import admin
from .models import Resume
# Register your models here.


from django.contrib import admin
from .models import Resume

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'file', 'uploaded_at')
    list_filter = ('uploaded_at', 'user')
    search_fields = ('user__username',)

