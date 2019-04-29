from django.contrib import admin
from .models import WeiboItem, WeiboInfo, WeiboComment, Notice


class WeiboItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'content', 'content_type', 'create_time', 'super']
    list_display_links = ['content']
    list_select_related = ['weiboinfo']

    def like_num(self,weiboitem):
        return weiboitem.weiboinfo.like_num
    like_num.short_description = '点赞数'


admin.site.register(WeiboItem, WeiboItemAdmin)


class WeiboInfoAdmin(admin.ModelAdmin):
    readonly_fields = ['weibo', 'forward_num', 'comment_num', 'like_num']


admin.site.register(WeiboInfo, WeiboInfoAdmin)
admin.site.register(WeiboComment)
admin.site.register(Notice)
