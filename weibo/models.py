from django.db import models
from django.conf import settings


class WeiboInfo(models.Model):
    weibo = models.OneToOneField('weibo.WeiboItem',related_name='weiboinfo', verbose_name=u'微博')
    forward_num = models.IntegerField(default=0, verbose_name=u'转发量')
    comment_num = models.IntegerField(default=0, verbose_name=u'评论量')
    like_num = models.IntegerField(default=0, verbose_name=u'点赞数量')


class WeiboItem(models.Model):
    """
    :type
        0:普通微博
        1:图片
        2:视频
    微博媒体存储结构：
        图片
        media/weibo/pictures/2019.4.25/weibo_id/1.jpg
        视频:
        media/weibo/vedio/2019.4.25/weibo_id/vedio.mp4
    """
    author = models.ForeignKey('account.User', verbose_name='作者')
    create_time = models.DateTimeField(auto_now=True, verbose_name='发表时间')
    content = models.CharField(max_length=150, verbose_name='内容')
    super = models.ForeignKey('WeiboItem', null=True, blank=True, on_delete=models.CASCADE, verbose_name='转发自微博')
    content_type = models.IntegerField(default=0, verbose_name='微博类型')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(WeiboItem, self).save()
        if not self.id:
            WeiboInfo(weibo=self).save()


class WeiboComment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    weibo = models.ForeignKey(WeiboItem, on_delete=models.CASCADE)
    content = models.CharField(max_length=128, verbose_name=u'内容')
    ctime = models.DateTimeField(auto_now=True)


class Notice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户')
    notice = models.CharField(max_length=128, verbose_name='通知内容')
    new = models.BooleanField(default=True, verbose_name='是否为新消息')
