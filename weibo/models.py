from django.db import models
from django.conf import settings


# 图片表
class Images(models.Model):
    image_id = models.AutoField(primary_key=True, unique=True, auto_created=True, verbose_name="ImageID")
    image = models.ImageField(upload_to='upload/image/%Y/%m')
    upload_time = models.DateTimeField(auto_now=True, verbose_name='上传时间')


# 视频表
class Video(models.Model):
    video_id = models.AutoField(primary_key=True, unique=True, auto_created=True, verbose_name="VedioID")
    video = models.FileField(upload_to='upload/video/%Y/%m', verbose_name=u'视频')
    upload_time = models.DateTimeField(auto_now=True, verbose_name='上传时间')


# 微博信息表
class WeiboInfo(models.Model):
    weibo = models.OneToOneField('weibo.WeiboItem',related_name='weiboinfo', verbose_name=u'微博')
    forward_num = models.IntegerField(default=0, verbose_name=u'转发量')
    comment_num = models.IntegerField(default=0, verbose_name=u'评论量')
    like_num = models.IntegerField(default=0, verbose_name=u'点赞数量')
    like = models.ManyToManyField('account.User', related_name="like_weibo", verbose_name=u'点赞的人')


# 微博表
class WeiboItem(models.Model):
    """
    :type
        0:普通微博
        1:图片
        2:视频
    """
    type_choices = (
        (0, '文本'),
        (1, '图片'),
        (2, '视频')
    )
    author = models.ForeignKey('account.User', verbose_name='作者')
    create_time = models.DateTimeField(auto_now=True, verbose_name='发表时间')
    content = models.CharField(max_length=150, verbose_name='内容')
    super = models.ForeignKey('WeiboItem', null=True, blank=True, on_delete=models.CASCADE, verbose_name='转发自微博')
    content_type = models.IntegerField(choices=type_choices, default=0, verbose_name='微博类型')
    is_active = models.BooleanField(default=True, verbose_name='激活')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            super(WeiboItem, self).save()
            WeiboInfo(weibo=self).save()
        else:
            super(WeiboItem, self).save()

    def __str__(self):
        return self.content


# 微博评论表
class WeiboComment(models.Model):
    author = models.ForeignKey('account.User', on_delete=models.CASCADE)
    weibo = models.ForeignKey(WeiboItem, related_name='comments', on_delete=models.CASCADE)
    content = models.CharField(max_length=128, verbose_name=u'内容')
    ctime = models.DateTimeField(auto_now=True)


# 消息表
class Notice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户')
    notice = models.CharField(max_length=128, verbose_name='通知内容')
    new = models.BooleanField(default=True, verbose_name='是否为新消息')


# 微博_图片表
class WeiboToImage(models.Model):
    weibo = models.OneToOneField(WeiboItem, primary_key=True, related_name='images', verbose_name='微博')
    image = models.ManyToManyField(Images, verbose_name='图片')


# 微博_视频表
class WeiboToVideo(models.Model):
    weibo = models.OneToOneField(WeiboItem, primary_key=True, related_name='video', verbose_name='微博')
    video = models.ForeignKey(Video, verbose_name='视频')
