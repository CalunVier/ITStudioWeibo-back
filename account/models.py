from django.db import models
from django.contrib.auth.models import AbstractUser


class UserWeiboInfo(models.Model):
    """
    :model:'accoun.User'.
    """
    user = models.OneToOneField('account.User', related_name='user_info', primary_key=True, on_delete=models.CASCADE, verbose_name=u'用户')
    follow_num = models.IntegerField(default=0, verbose_name=u'跟随数量')
    following = models.ManyToManyField('User', related_name='following', verbose_name=u'关注的人')
    fans_num = models.IntegerField(default=0, verbose_name=u'喜欢的人')
    weibo_num = models.IntegerField(default=0, verbose_name=u'微博数量')


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
    nick = models.CharField(verbose_name=u'昵称', max_length=16)
    sex = models.IntegerField(default=0, choices=sex_choices, verbose_name=u'性别')
    birth = models.DateTimeField(null=True, blank=True, verbose_name=u'生日')
    school = models.CharField(max_length=128, null=True, blank=True, verbose_name=u'学校')
    intro = models.CharField(max_length=180, null=True, blank=True, verbose_name=u'介绍')

    class Meta:
        indexes = [
            models.Index(fields=['email'])
        ]

    def save(self, *args, **kwargs):
        super(User, self).save()
        info = UserWeiboInfo.objects.filter(user=self)
        if not info:
            UserWeiboInfo(user=self).save()
