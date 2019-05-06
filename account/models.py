from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import is_password_usable


class UserWeiboInfo(models.Model):
    """
    :model:'accoun.User'.
    """
    user = models.OneToOneField('account.User', related_name='user_info', primary_key=True, on_delete=models.CASCADE, verbose_name=u'用户')
    follow_num = models.IntegerField(default=0, verbose_name=u'跟随数量')
    following = models.ManyToManyField('User', related_name='followers', verbose_name=u'关注的人')
    fans_num = models.IntegerField(default=0, verbose_name=u'喜欢的人')
    weibo_num = models.IntegerField(default=0, verbose_name=u'微博数量')
    collect_weibo = models.ManyToManyField('weibo.WeiboItem', related_name='collect_weibo', verbose_name=u'收藏微博')
    gallery = models.ManyToManyField('weibo.Images', related_name='owner', verbose_name=u'相册')


class User(AbstractUser):
    """
    :sex
        0：未设置
        1；男
        2：女
        3：其他
    """

    sex_choices = (
        (0, '未设定'),
        (1, '男'),
        (2, '女'),
        (3, '其他')
    )
    head = models.ImageField(verbose_name=u'头像', default='default/default_head_img.jpg', upload_to='upload/%Y/%m')
    sex = models.IntegerField(default=0, choices=sex_choices, verbose_name=u'性别')
    birth = models.DateTimeField(null=True, blank=True, verbose_name=u'生日')
    school = models.CharField(max_length=128, null=True, blank=True, verbose_name=u'学校')
    intro = models.CharField(max_length=180, null=True, blank=True, verbose_name=u'介绍')

    class Meta:
        indexes = [
            models.Index(fields=['email'])
        ]

    def save(self, *args, **kwargs):
        if not is_password_usable(self.password):
            self.set_password(self.password)
        if not self.id:
            super(User, self).save()
            UserWeiboInfo(user=self).save()
        else:
            super(User, self).save()
