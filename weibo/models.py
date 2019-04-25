from django.db import models
from django.conf import settings


class WeiboItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='作者')
    create_time = models.DateTimeField(auto_now=True, verbose_name='发表时间')
    content = models.CharField(max_length=150, verbose_name='内容')


class Notice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户')
    notice = models.CharField(max_length=128, verbose_name='通知内容')
    new = models.BooleanField(default=True, verbose_name='是否为新消息')