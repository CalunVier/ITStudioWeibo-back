from django.conf.urls import url
from django.contrib import admin
from .views import *

urlpatterns = [
    url(r'^register', register),    # 注册
    url('^login', login),       # 登陆
    url('^logout', logout),     # 登出
    url(r'user_weibo_info', get_user_info),   # 个人资料
    url(r"home", get_user_home)     # 个人中心
]