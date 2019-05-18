from django.conf.urls import url
from django.contrib import admin
from .views import *

urlpatterns = [
    url(r'^register', register),    # 注册
    url(r'^login', login),       # 登陆
    url(r'^logout', logout),     # 登出
    url(r'^user_weibo_info', user_weibo_info),   # 个人资料
    url(r"^home", get_user_home),     # 个人中心
    url(r"^user_info", user_info),
    url(r"^my_weibo_list", my_weibo_list),
    url(r'^change_password', change_password),
    url(r'^change_head', change_head),
    url(r'^change_nick', change_username),
    url(r'^new_follow', new_follow),
    url(r"^forgot_password", forgot_password),
    url(r'^following_list', following_list),
    url(r'^get_gallery', get_gallery),
    url(r'^followers', followers_list),
    url(r'^log_page', log_page),
]