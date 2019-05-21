from django.db import models
from django.conf import settings
from django.db.models.query import QuerySet
import logging


logger = logging.getLogger('my_logger.weibo.model')


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
    weibo = models.OneToOneField('weibo.WeiboItem', related_name='weiboinfo', verbose_name=u'微博')
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
    super_weibo = models.ForeignKey('WeiboItem', null=True, blank=True, on_delete=models.CASCADE, verbose_name='转发自微博')
    content_type = models.IntegerField(choices=type_choices, default=0, verbose_name='微博类型')
    is_active = models.BooleanField(default=True, verbose_name='激活')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            # 新微薄
            # 调用父类save()保存到数据库
            super(WeiboItem, self).save(force_insert=False, force_update=False, using=None, update_fields=None)
            # 增加作者的微博量
            self.author.user_info.weibo_num += 1
            self.author.user_info.save()
            logger.debug('更新user_info.weibo_num')
            # 创建微博info
            weibo_info = WeiboInfo(weibo=self)
            weibo_info.save()
            # 如果有转发，更新转发微博的转发量
            if self.super_weibo:
                end_super_weibo = self.super_weibo
                while end_super_weibo.super_weibo:
                    end_super_weibo.weiboinfo.forward_num += 1
                    end_super_weibo.weiboinfo.save()
                    end_super_weibo = end_super_weibo.super_weibo
                end_super_weibo.weiboinfo.forward_num += 1
                end_super_weibo.weiboinfo.save()
        else:
            super(WeiboItem, self).save(force_insert=False, force_update=False, using=None, update_fields=None)

    def delete(self, using=None, keep_parents=False):
        self.author.user_info.weibo_num -= 1
        self.author.user_info.save()
        if self.super_weibo:
            end_super_weibo = self.super_weibo
            while end_super_weibo.super_weibo:
                end_super_weibo.weiboinfo.forward_num -= 1
                end_super_weibo.weiboinfo.save()
                end_super_weibo = end_super_weibo.super_weibo
            end_super_weibo.weiboinfo.forward_num -= 1
            end_super_weibo.weiboinfo.save()
        super(WeiboItem, self).delete(using=None, keep_parents=False)

    def __str__(self):
        return self.content


# 微博评论表
class WeiboComment(models.Model):
    author = models.ForeignKey('account.User', on_delete=models.CASCADE)
    weibo = models.ForeignKey(WeiboItem, related_name='comments', on_delete=models.CASCADE)
    content = models.CharField(max_length=128, verbose_name=u'内容')
    ctime = models.DateTimeField(auto_now=True, verbose_name='创建时间')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.id:
            super(WeiboComment, self).save(force_insert=False, force_update=False, using=None, update_fields=None)
        else:
            super(WeiboComment, self).save(force_insert=False, force_update=False, using=None, update_fields=None)
            # 新评论
            self.weibo.weiboinfo.comment_num += 1
            self.weibo.weiboinfo.save()

    def delete(self, using=None, keep_parents=False):
        self.weibo.weiboinfo.comment_num -= 1
        self.weibo.weiboinfo.save()

        super(WeiboComment, self).delete(using=None, keep_parents=False)


# 消息表
class Notice(models.Model):
    type_choice = (
        (0, '文本'),
        (1, '@'),
        (2, '官方推送'),
        (3, '评论')
    )
    sender = models.ForeignKey('account.User', related_name='i_sent', verbose_name='发件人')
    recipient = models.ForeignKey('account.User', related_name='my_notice', verbose_name='收件人')
    notice = models.CharField(max_length=128, verbose_name='通知内容')
    n_type = models.IntegerField(choices=type_choice, verbose_name='消息类型')
    read = models.BooleanField(default=False, verbose_name=u'已读')
    time = models.DateTimeField(auto_now=True, verbose_name=u'时间')
    other = models.CharField(max_length=256,null=True, blank=True, verbose_name='备注')


# 微博_图片表
class WeiboToImage(models.Model):
    weibo = models.OneToOneField(WeiboItem, primary_key=True, related_name='images', verbose_name='微博')
    image = models.ManyToManyField(Images, verbose_name='图片')


# 微博_视频表
class WeiboToVideo(models.Model):
    weibo = models.OneToOneField(WeiboItem, primary_key=True, related_name='video', verbose_name='微博')
    video = models.ForeignKey(Video, verbose_name='视频')
