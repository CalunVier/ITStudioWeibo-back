from django.contrib import admin
from .models import WeiboItem, WeiboInfo, WeiboComment, Notice, Video, Images


class WeiboItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'content', 'content_type', 'create_time', 'super_weibo', 'like_num', 'comment_num', 'forward_num']
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
    list_select_related = ['weibo']
    list_display = ['id', 'weibo', 'forward_num', 'comment_num', 'like_num']
    readonly_fields = ['weibo', 'forward_num', 'comment_num', 'like_num']


admin.site.register(WeiboInfo, WeiboInfoAdmin)


class WeiboCommentAdmin(admin.ModelAdmin):
    list_select_related = ['weibo', 'author']
    list_display = ['id', 'weibo', 'content', 'author', 'ctime']


admin.site.register(WeiboComment, WeiboCommentAdmin)


class NoticeAdmin(admin.ModelAdmin):
    list_display = ['id', 'notice', 'sender', 'recipient', 'n_type', 'read', 'time', 'other']


admin.site.register(Notice, NoticeAdmin)


class VideoAdmin(admin.ModelAdmin):
    list_display = ['video_id', 'video', 'upload_time']


admin.site.register(Video, VideoAdmin)


class ImageAdmin(admin.ModelAdmin):
    list_display = ['image_id', 'image', 'upload_time']


admin.site.register(Images, ImageAdmin)
