from account.account_lib import check_logged
from account.models import User
from .models import WeiboToVideo, Notice, WeiboItem, Images, WeiboToImage, Video, WeiboComment
from django.http import HttpResponse
from django.core.cache import cache
import json
import logging
import re
from PIL import Image
import traceback


logger = logging.getLogger("my_logger.weibo.lib")


# 将微博数据库QuerySet处理为可转化为json字符串的python字典
def weibo_list_process_to_dict(request, weibo_db, page):
    weibo_list_response_date = []
    for item in weibo_db:
        # 获取微博信息字典并添加到返回列
        weibo_list_response_date.append(weibo_db_to_dict(request, item))
    response_data = {
        'page': page,
        'list': weibo_list_response_date,
        'status': 0,
    }
    return response_data


def weibo_db_to_dict(request, item):
    item_data = {
        'weibo_id': item.id,
        "type": 'text' if item.content_type == 0 else 'image' if item.content_type == 1 else 'video',
        "content": item.content,
        "author_id": item.author.username,
        "author_head": item.author.head.url,
        "forward_num": item.weiboinfo.forward_num,
        "comment_num": item.weiboinfo.comment_num,
        "like_num": item.weiboinfo.like_num,
        "time": item.create_time.timestamp(),
        'is_forward': False,
        'following': False,
        'is_like': False,
        'collected': False,
    }

    # 处理转发情况
    if item.super_weibo:
        end_super_weibo = item.super_weibo
        while end_super_weibo.super_weibo:
            end_super_weibo = end_super_weibo.super_weibo
        item_data['is_forward'] = True
        super_weibo_dict = {
            'weibo_id': end_super_weibo.id,
            'content': end_super_weibo.content,
            'author_id': end_super_weibo.author.username,
            'type': 'text' if end_super_weibo.content_type == 0 else 'image' if end_super_weibo.content_type == 1 else 'video',
        }
        # 处理图片和视频
        if end_super_weibo.content_type == 1:  # img
            try:
                end_super_imgs_db = end_super_weibo.images.image.all()
                end_super_imgs_list = []
                for img in end_super_imgs_db:
                    end_super_imgs_list.append(img.image.url)
                super_weibo_dict['imgs'] = end_super_imgs_list
            except:
                logger.error('super微博图片处理异常, weibo_id:%d' % end_super_weibo.id)
                logger.error('image_list: %s' % str(end_super_imgs_list))
                logger.error('异常image:%s' % img)
                logger.error(traceback.format_exc())
                end_super_weibo.content_type = 0
                end_super_weibo.save()
                logger.error('已将微博类型重置为0')
        elif end_super_weibo.content_type == 2:  # video
            try:
                end_super_videos_db = end_super_weibo.video.video
                super_weibo_dict['video'] = end_super_videos_db.video.url
            except:
                logger.error('super微博视频处理异常, weibo_id:%d' % end_super_weibo.id)
                logger.error('异常video:%s' % end_super_videos_db.video.url)
                end_super_weibo.content_type = 0
                end_super_weibo.save()
                logger.error('已将微博类型重置为0')
        item_data['super'] = super_weibo_dict

    # 处理登陆后的各种状态
    user = check_logged(request)
    if user:
        # 处理点赞情况
        if item.weiboinfo.like.filter(id=user.id):
            item_data['is_like'] = True

        # 检查是否following
        user = check_logged(request)
        if user:
            check_follow = user.user_info.following.filter(username=item_data['author_id'])
            if check_follow:
                item_data['following'] = True

        # 检查是否收藏
        if user.user_info.collect_weibo.filter(id=item.id):
            item_data['collected']=True
    else:
        logger.debug('未登录')

    # 处理视频和图片
    if item.content_type == 1:  # img
        try:
            imgs_db = item.images.image.all()
            imgs_list = []
            for img in imgs_db:
                imgs_list.append(img.image.url)
            item_data['imgs'] = imgs_list
        except:
            logger.error('微博图片处理异常, weibo_id:%d' % item.id)
            logger.error('image_list: %s' % str(imgs_list))
            logger.error('异常image:%s' % img)
            item.content_type = 0
            item.save()
            logger.error('已将微博类型重置为0')
    elif item.content_type == 2:  # video
        try:
            videos_db = item.video.video
            item_data['video'] = videos_db.video.url
        except:
            logger.error('微博视频处理异常, weibo_id:%d' % item.id)
            logger.error('异常video:%s' % videos_db.video.url)
            item.content_type = 0
            item.save()
            logger.error('已将微博类型重置为0')
    return item_data


# 创建微博
def to_create_weibo(content, user, content_type, imgs_id, video_id, super_weibo_id):
    """
    返回及status说明
        本函数直接返回HttpResponse对象
        由本函数返回的status情况
            0：成功
            5：转发失败

    :param content: 微博内容
    :param user:作者Model对象
    :param content_type:内容类型0/1/2
    :param imgs_id:如果有图片，图片ID
    :param video_id:如果有视频，视频ID
    :param super_weibo_id:如果是转发，父微博的ID
    :return:
    """
    try:
        weibo = WeiboItem(author=user, content=content)

        # 处理转发
        if super_weibo_id:
            try:
                super_weibo = WeiboItem.objects.get(id=super_weibo_id)
                weibo.super_weibo = super_weibo
                content_type = 0
            except:
                logger.debug('无效的super微博：%s' % super_weibo_id)
                return HttpResponse("{\"status\":5}", status=500)
        weibo.save()

        at_notice_catcher(user, content, weibo.id)

        # 分情况处理附加信息
        if content_type == 1:
            if imgs_id:
                imgs_db = Images.objects.none()
                for img_id in imgs_id:
                    try:
                        image = Images.objects.filter(image_id=img_id)
                        imgs_db = imgs_db | image
                    except:
                        logger.error('处理图片时出现异常')
                        logger.error(traceback.format_exc())

                if imgs_db:
                    weibo.content_type = 1
                    weibo_to_image = WeiboToImage(weibo=weibo)
                    weibo_to_image.save()
                    for img in imgs_db:
                        weibo_to_image.image.add(img)
                    weibo.save()
                    return HttpResponse("{\"status\":0}", status=200)
            # 没有检测到上传的图片信息，更正微博类型为0，并保存微博
            # 这里的代码对上面两个if都有效
            logger.debug('没有检测到上传的图片信息，更正微博类型为0，并保存微博')
            weibo.content_type = 0
            weibo.save()
            return HttpResponse(json.dumps({"status": "0"}))
        elif content_type == 2:
            if video_id:
                try:
                    video_db = Video.objects.get(video_id=video_id)
                except:
                    video_db = None
                    logger.debug('未检索到视频')
                if video_db:
                    weibo.content_type = 2
                    WeiboToVideo(weibo=weibo, video=video_db).save()
                    weibo.save()
                    return HttpResponse("{\"status\":0}", status=200)
            logger.debug('没有检测到上传的视频信息，更正微博类型为0，并保存微博')
            weibo.content_type = 0
            weibo.save()
            return HttpResponse(json.dumps({"status": "0", "info": "We didn't find any video, changed type to \"text\"."}))
        else:
            # 因默认为0，不做修改
            return HttpResponse("{\"status\":0}", status=200)
    except:
        logger.error('未知错误')
        logger.error(traceback.format_exc())
        return HttpResponse("{\"status\":6}", status=500)


# 发表评论
def create_weibo_comment(user, weibo, content):
    comment = WeiboComment(author=user, weibo=weibo, content=content)
    comment.save()
    # notice处理
    at_notice_catcher(user, content, weibo.id)
    Notice(sender=user, recipient=weibo.author, n_type=3, content='用户%s评论了你的微博' % weibo.author.username, other=json.dumps({'weibo_id': weibo.id})).save()
    logger.debug('已保存notice')
    return comment


# 捕获@内容
def at_notice_catcher(sender, content, weibo_id):
    at_list = re.findall(r'@(\w+) ', content)
    for username in at_list:
        try:
            recipient = User.objects.get(username=username)
            Notice(sender=sender, recipient=recipient, n_type=1, notice='%s在微博中提到了你' % sender.username, other=json.dumps({'weibo_id': weibo_id})).save()
            logger.debug('捕获到@内容：%s' % recipient.username)
        except:
            logger.warning('捕获@内容过程中出现异常')
            logger.warning(traceback.format_exc())


def process_notice_to_list(notice_db):
    response_list = []
    for n in notice_db:
        if n.n_type == 1:
            response_list.append({
                'type': 1,
                'notice_id': n.id,
                'content': n.notice,
                'read': n.read,
                'time': n.time.timestamp(),
                'weibo_id': json.loads(n.other).get('weibo_id', ''),
                'sender_id': n.sender.username,
            })
        elif n.n_type == 3:
            response_list.append({
                'type': 3,
                'notice_id': n.id,
                'content': n.notice,
                'read': n.read,
                'time': n.time.timestamp(),
                'sender_id': n.sender.username,
                'weibo_id': json.loads(n.other).get('weibo_id', ''),
            })
        elif n.n_type == 4:
            response_list.append({
                'type': 4,
                'notice_id': n.id,
                'content': n.notice,
                'read': n.read,
                'time': n.time.timestamp(),
                'sender_id': n.sender.username,
                'weibo_id': json.loads(n.other).get('weibo_id', ''),
            })
        else:
            response_list.append({
                'type': n.n_type,
                'notice_id': n.id,
                'content': n.notice,
                'read': n.read,
                'time': n.time.timestamp(),
                'sender_id': n.sender.username,
                'other': n.other
            })
    return response_list


def process_notice_with_tag(ns_db, tag):
    if tag == 'at':
        return ns_db.filter(n_type=1)
    elif tag == 'comment':
        return ns_db.filter(n_type=3)
    elif tag == 'like':
        return ns_db.filter(n_type=4)


def search_weibo_lib(key_word: str):
    """

    :param key_word:
    :return: weibo_db
    """
    old = cache.get('search_weibo_' + key_word)
    if old:
        cache.set('search_weibo_' + key_word, old, 10)
        return old, old.count()

    if not key_word:
        logger.debug('空关键词')
        return WeiboItem.objects.all()

    weibo_db = WeiboItem.objects.filter(content__contains=key_word).exclude(is_active=False).order_by('-create_time')
    cache.set('search_weibo_' + key_word, weibo_db, 10)
    return weibo_db, weibo_db.count()


def search_user_lib(key_word: str):
    """

    :param key_word:
    :return:
    """
    old = cache.get('search_user_' + key_word)
    if old:
        return old, old.count()
    if not key_word:
        logger.debug('空key_word')
        user_all = User.objects.all()
        return user_all, user_all.count()
    user_db = User.objects.filter(username__contains=key_word).exclude(is_active=False)
    cache.set('search_user_' + key_word, user_db, 30)
    return user_db, user_db.count()


def process_user_to_list(user_db):
    response_list = []
    for user in user_db:
        response_list.append({
            'user_id': user.username,
            'user_head': user.head.url,
            'user_info': user.intro
        })
    return response_list


def create_thumbnail(img_db):
    try:
        im = Image.open(img_db.image.path)
        im.thumbnail((480, 480))
        re_name = re.match(r'(.+)(\.\w+)$', img_db.image.name)
        im.save('media/'+img_db.image.path[:-len(img_db.image.path)] + re_name.group(1) + '_tb_480' + re_name.group(2))
    except:
        logger.error("生成缩略图失败：%s" % img_db.image.path)
        logger.error(traceback.format_exc())
