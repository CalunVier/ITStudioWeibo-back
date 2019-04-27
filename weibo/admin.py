from django.contrib import admin
from .models import WeiboItem, WeiboInfo, WeiboComment, Notice


admin.site.register(WeiboItem)
admin.site.register(WeiboInfo)
admin.site.register(WeiboComment)
admin.site.register(Notice)
