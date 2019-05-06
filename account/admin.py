from django.contrib import admin
from .models import User, UserWeiboInfo


class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_name', 'email', 'is_active', 'user_info_weibo_num', 'user_info_funs_num']
    actions = ['de_active_user', 'to_active_user']
    list_display_links = ['user_name']
    list_select_related = ['user_info']
    list_filter = ['is_active', 'sex']
    search_fields = ['username', '^id', 'email', 'nick']

    # list display
    def user_info_funs_num(self, user):
        return user.user_info.fans_num
    user_info_funs_num.admin_order_field = 'user_info__fans_num'
    user_info_funs_num.short_description = u'粉丝数'

    def user_name(self, user):
        return user.username
    user_name.short_description = u'用户ID'
    user_name.admin_order_field = 'username'

    def user_info_weibo_num(self, user):
        return user.user_info.weibo_num
    user_info_weibo_num.short_description = u'微博数'
    user_info_weibo_num.admin_order_field = 'user_info__weibo_num'

    # actives

    def de_active_user(self, request, queryset):
        rows_updated = queryset.update(is_active=False)
        if rows_updated == 1:
            message_bit = u"1 个用户被设置为不活动的"
        else:
            message_bit = u"%s 个用户被设置为不活动的" % rows_updated
        self.message_user(request, message_bit)
    de_active_user.short_description = u'设置为不活动的'

    def to_active_user(self, request, queryset):
        rows_updated = queryset.update(is_active=True)
        if rows_updated == 1:
            message_bit = u"1 个用户被设置为活动的"
        else:
            message_bit = u"%s 个用户被设置为活动的" % rows_updated
        self.message_user(request, message_bit)
    to_active_user.short_description = u'设置为活动的'


admin.site.register(User, UserAdmin)


class UserWeiboInfoAdmin(admin.ModelAdmin):
    list_display = ['user']
    ordering = ['user']
    readonly_fields = ['follow_num', 'fans_num', 'weibo_num']


admin.site.register(UserWeiboInfo, UserWeiboInfoAdmin)
