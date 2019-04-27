from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    head = models.ImageField(verbose_name=u'头像', default='default/default_head_img.jpg', upload_to='upload/%Y/%m')
    nick = models.CharField(verbose_name=u'昵称', max_length=16)

    class Meta:
        indexes = [
            models.Index(fields=['email'])
        ]


class UserWeiboInfo(models.Model):
    user = models.OneToOneField(User, related_name='user_info', primary_key=True, on_delete=models.CASCADE, verbose_name=u'用户')
    intro = models.CharField(max_length=180, null=True, blank=True, verbose_name=u'介绍')
    follow_num = models.IntegerField(default=0, verbose_name=u'跟随数量')
    following = models.ManyToManyField(User, related_name='following', verbose_name=u'关注的人')
    fans_num = models.IntegerField(default=0, verbose_name=u'喜欢的人')
    weibo_num = models.IntegerField(default=0, verbose_name=u'微博数量')

