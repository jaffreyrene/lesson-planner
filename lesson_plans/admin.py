from django.contrib import admin
from .models import UserProfile

admin.site.register(UserProfile)
from .models import Tag, Document, Philosophy, Persona, Voice, Tone, OutputFormat

admin.site.register(Philosophy)
admin.site.register(Persona)
admin.site.register(Voice)
admin.site.register(Tone)
admin.site.register(OutputFormat)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

# touched on 2025-06-13T18:50:14.177215Z