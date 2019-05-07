from django.contrib import admin
from .models import WeiboItem, WeiboInfo, WeiboComment, Notice, Video


class WeiboItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'content', 'content_type', 'create_time', 'super', 'like_num', 'comment_num', 'forward_num']
    list_display_links = ['content']
    list_select_related = ['weiboinfo']

    def like_num(self,weiboitem):
        return weiboitem.weiboinfo.like_num
    like_num.short_description = '点赞数'

    def comment_num(self, weiboitem):
        return weiboitem.weiboinfo.comment_num
    comment_num.short_description = '评论数'

    def forward_num(self, weiboitem):
        return weiboitem.weiboinfo.forward_num

    forward_num.short_description = '转发量'


admin.site.register(WeiboItem, WeiboItemAdmin)


class WeiboInfoAdmin(admin.ModelAdmin):
    readonly_fields = ['weibo', 'forward_num', 'comment_num', 'like_num']


admin.site.register(WeiboInfo, WeiboInfoAdmin)
admin.site.register(WeiboComment)
admin.site.register(Notice)
admin.site.register(Video)
