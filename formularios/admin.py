from django.contrib import admin
from formularios.models import Gform, GformSection, GformSectionInput, GformSectionInputOps, GformResponde, GformRespondeInput


admin.site.register(Gform)
admin.site.register(GformSection)
admin.site.register(GformSectionInput)
admin.site.register(GformSectionInputOps)
admin.site.register(GformResponde)
admin.site.register(GformRespondeInput)
