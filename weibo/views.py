from django.shortcuts import render
from django.http import HttpResponse
from django.core.cache import cache
from account.account_lib import check_logged
from account.models import User
from ITstudioWeibo.calunvier_lib import page_of_queryset
from .models import WeiboItem, Images, WeiboToImage, Video, WeiboToVideo, WeiboComment, Notice
from .weibo_lib import weibo_list_process_to_dict, to_create_weibo, create_weibo_comment, process_notice_to_list
from .weibo_lib import search_weibo_lib, search_user_lib, process_user_to_list
from django.db.models.query import QuerySet
import json
import pathlib
import re
import datetime
import logging


logger = logging.getLogger('my_logger.weibo.view')
status_str = '{"status":%d}'

"""GET"""


# 获取首页微博列表
def get_item_list(request):
    """
    返回及status状态说明
        status:
            0:成功
            4：未登录
            6：未知错误
        非GET请求不做处理，返回HTTP404
    :param request:
    :return:
    """
    try:
        logger.debug('get_item_list()')
        if request.method == 'GET':
            logger.debug('收到post请求')

            # 读取request Query
            try:
                page = int(request.GET.get('page', 1))
            except:
                page = 1
            try:
                num = int(request.GET.get('num', 10))
            except:
                num = 10

            tag = request.GET.get('tag', 'hot')

            # 检索数据库
            if tag == 'follow':
                # 关注
                user = check_logged(request)
                if user:
                    followings = user.user_info.following.all()
                    weibo_db = WeiboItem.objects.none()
                    if followings:
                        for author in followings:
                            weibo_db = weibo_db | WeiboItem.objects.select_related('super_weibo', 'weiboinfo').filter(author=author).exclude(is_active=False)
                    weibo_db = weibo_db.order_by('-create_time')
                else:
                    logger.debug('未登录')
                    return HttpResponse(json.dumps({'status': 4}), status=401)
            elif tag == 'video':
                weibo_db = WeiboItem.objects.select_related('super_weibo', 'weiboinfo').filter(content_type=2).exclude(is_active=False).order_by('-create_time')
            else:
                weibo_db = WeiboItem.objects.select_related('super_weibo', 'weiboinfo').filter(create_time__gte=datetime.datetime.now() - datetime.timedelta(7)).exclude(is_active=False).order_by('-weiboinfo__like_num', '-create_time')

            # 分页
            weibo_db = page_of_queryset(weibo_db, page=page, num=num)

            # 循环处理数据库中的数据
            response_dict = weibo_list_process_to_dict(request, weibo_db, page)

            # 处理完毕返回列表
            return HttpResponse(json.dumps(response_dict), status=200)
        else:
            # 非GET不接
            return HttpResponse(status=404)
    except:
        logger.error('未知错误')
        return HttpResponse("{\"status\":6}", status=500)


# 获取微博详细信息
def get_weibo_info(request):
    """
    返回及status说明
        0:成功,
        3:未知的微博
        6:未知错误
    :param request:
    :return:
    """
    try:
        if request.method == "GET":
            try:
                weibo_id = int(request.GET.get('weibo_id', ''))
                item = WeiboItem.objects.select_related('author', 'weiboinfo').get(id=weibo_id)
                assert item.is_active
            except:
                logger.debug('未知的微博')
                return HttpResponse("{\"status\":3}", status=404)
            item_data = {
                "type": 'text' if item.content_type == 0 else 'image' if item.content_type == 1 else 'video',
                "content": item.content,
                "weibo_id": weibo_id,
                "author_id": item.author.username,
                "author_head": item.author.head.url,
                "forward_num": item.weiboinfo.forward_num,
                "comment_num": item.weiboinfo.comment_num,
                "like_num": item.weiboinfo.like_num,
                "time": item.create_time.timestamp(),
                "status": 0
            }

            # 处理转发情况
            if item.super_weibo:
                end_super_weibo = item.super_weibo
                while end_super_weibo.super_weibo:
                    end_super_weibo = end_super_weibo.super_weibo
                item_data['is_forward'] = True
                item_data["super_weibo"] = {
                    'weibo_id': end_super_weibo.id,
                    'content': end_super_weibo.content,
                    'author_id': end_super_weibo.author.id,
                }
            else:
                item_data['is_forward'] = False

            user = check_logged(request)
            if user:
                # 处理点赞情况
                logger.debug('处理点赞情况')
                if item.weiboinfo.like.filter(id=user.id):
                    item_data['is_like'] = True

                # 检查是否following

                username = request.COOKIES.get('username', '')
                if username:
                    user = User.objects.get(username=username)
                    check_follow = user.user_info.following.filter(username=item_data['author_id'])
                    if check_follow:
                        item_data['following'] = True
                    else:
                        item_data['following'] = False
                else:
                    item_data['following'] = False
            else:
                item_data['following'] = False

            # 处理视频和图片
            if item.content_type == 1:  # img
                imgs_db = item.images.image.all()
                imgs_list = []
                for img in imgs_db:
                    imgs_list.append(img.image.url)
                item_data['imgs'] = imgs_list
            elif item.content_type == 2:  # video
                item = WeiboItem.objects.get()
                videos_db = item.video.video
                item_data['video'] = videos_db.video.url

            # 成功，返回结果
            return HttpResponse(json.dumps(item_data))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 转发/评论列表
def comment_like_list(request):
    """
    返回及状态说明
        status:
            0:成功
            2:未找到指定微博
            3：未定义的tag
            6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            # 获取分页信息
            try:
                page = int(request.GET.get("page", 1))
            except:
                page = 1
            try:
                num = int(request.GET.get("num", 10))
            except:
                num = 10

            # 获取微博对象
            try:
                weibo = WeiboItem.objects.get(id=int(request.GET.get('weibo_id', '')))
                assert weibo.is_active
            except:
                logger.debug("未找到指定微博")
                return HttpResponse("{\"status\":2}", status=404)
            # 获取标签信息
            tag = request.GET.get('tag', '')

            if tag == 'comment':
                # 评论列表  检索数据库
                comments = WeiboComment.objects.select_related('author').filter(weibo=weibo).order_by('-ctime')
                # 分页
                comments = page_of_queryset(comments, page, num)
                response_list = []
                for comment in comments:
                    comment_dict = {
                        "user_id": comment.author.username,
                        "user_head": comment.author.head.url,
                        "time": comment.ctime.timestamp(),
                        "comment_id": comment.id,
                        'content': comment.content
                    }
                    response_list.append(comment_dict)
                return HttpResponse(json.dumps({"page": page, "list": response_list, "status": 0}))
            elif tag == 'forward':
                # 检索数据库，为方便复制代码，变量名为comment
                comments = WeiboItem.objects.select_related('author').filter(super_weibo=weibo).exclude(is_active=False)
                sub_weibo = comments
                sub2_weibo = WeiboItem.objects.none()
                loop_still = 1
                while loop_still:
                    for sw in sub_weibo:
                        ssw = WeiboItem.objects.select_related('author').filter(super_weibo=sw).exclude(is_active=False)
                        if ssw:
                            loop_still = 1
                            sub2_weibo = sub2_weibo | ssw
                    comments = comments | sub2_weibo
                    sub_weibo = WeiboItem.objects.none() | sub2_weibo
                    sub2_weibo = WeiboItem.objects.none()
                    loop_still = 0
                # 分页
                comments = comments.order_by('-create_time')
                comments = page_of_queryset(comments, page, num)
                response_list = []
                for comment in comments:
                    comment_dict = {
                        "user_id": comment.author.username,
                        "user_head": comment.author.head.url,
                        "time": comment.create_time.timestamp(),
                        "weibo_id": comment.id,
                        'content': comment.content
                    }
                    response_list.append(comment_dict)
                return HttpResponse(json.dumps({"page": page, "list": response_list, "status": 0}))
            else:
                logger.debug("未定义的tag")
                return HttpResponse(status_str % 3, status=406)
        else:
            return HttpResponse(status=404)
    except:
        HttpResponse("{\"status\":6}", status=500)


# 获取点赞人员列表
def liker_list(request):
    """
    返回及状态说明
        status
            0：成功
            2: 找不到指定微博
            6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            logger.debug('收到GET请求')
            try:
                weibo = WeiboItem.objects.select_related('weiboinfo').get(id=int(request.GET.get('weibo_id', '')))
            except:
                logger.debug("找不到指定微博：%s " % request.GET.get('weibo_id', ''))
                return HttpResponse(status_str % 2, status=404)

            # 获取分页信息
            try:
                page = int(request.GET.get('page', 1))
            except:
                page = 1
            try:
                num = int(request.GET.get('num', 10))
            except:
                num = 10

            # 检索数据库
            like_db = weibo.weiboinfo.like.all().reverse()
            like_db = page_of_queryset(like_db, page, num)
            response_list = []
            for liker in like_db:
                response_list.append({
                   "user_id": liker.username,
                   "user_info": liker.intro
                })
            return HttpResponse(json.dumps({"page": page, 'list': response_list, 'status': 0}))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse(status_str % 6, status=500)


# 获取消息列表
def get_notice_list(request):
    """
    返回及状态说明
        status
            0:成功
            4：未登录
            6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            try:
                time = datetime.datetime.fromtimestamp(float(request.GET.get('time', '')))
            except:
                time = None
            user = check_logged(request)
            if not user:
                logger.debug("未登录")
                return HttpResponse(status_str % 4, status=401)
            if time:
                # 检索数据库
                ns_db = Notice.objects.select_related('sender').filter(recipient=user, time__gt=time)
                response_list = process_notice_to_list(ns_db)
                return HttpResponse(json.dumps({'list': response_list, 'status':0}))
            else:
                ns_db = Notice.objects.all()
                response_list = process_notice_to_list(ns_db)
                return HttpResponse(json.dumps({'list': response_list, 'status': 0}))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse(status_str % 6, status=500)


# 搜索
def search_all(request):
    try:
        if request.method == 'GET':
            key_word = request.GET.get('key')
            if not key_word:
                logger.debug('空关键字')
                return HttpResponse(status_str % 2, status=403)
            # 获取分页信息
            try:
                user_num = int(request.GET.get('user_num'), 6)
            except:
                user_num = 6
            try:
                weibo_num = int(request.GET.get('weibo_num'), 10)
            except:
                weibo_num = 10
            try:
                weibo_page = int(request.GET.get('weibo_page'), 1)
            except:
                weibo_page = 1
            try:
                user_page = int(request.GET.get('user_page'), 1)
            except:
                user_page = 1
            logger.debug('搜索微博')
            weibo_db, weibo_total = search_weibo_lib(key_word)
            logger.debug('搜索用户')
            user_db, user_total = search_user_lib(key_word)
            logger.debug('分页')
            weibo_db = page_of_queryset(weibo_db, weibo_page, weibo_num)
            user_db = page_of_queryset(user_db, user_page, user_num)
            logger.debug('处理返回字典')
            weibo_dict = weibo_list_process_to_dict(request, weibo_db, weibo_page)
            weibo_dict['total'] = weibo_total
            del weibo_dict['status']
            user_dict = {
                'page': user_page,
                'list': process_user_to_list(user_db),
                'total': user_total
            }
            # 返回结果
            return HttpResponse(json.dumps({
                'user': user_dict,
                'weibo': weibo_dict,
                'status': 0
            }))
        else:
            return HttpResponse(status=404)
    except:
        logger.error('未知错误')
        return HttpResponse(status_str % 6, status=500)


# 搜索微博内容
def search_weibo(request):
    """
    GET Quuery
        page:页
        num:每页数量
        key:搜索关键词

    返回及状态说明

    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            try:
                page = int(request.GET.get('page', 1))
            except:
                page = 1
            try:
                num = int(request.GET.get('num', 10))
            except:
                num = 10
            key_word = request.GET.get('key', '')
            if not key_word:
                logger.debug('空的key_word')
                return HttpResponse(status_str % 2, status=403)
            weibo_db, total = search_weibo_lib(key_word)
            logger.debug('搜索完成')
            weibo_db = page_of_queryset(weibo_db, page, num)
            response_dict = weibo_list_process_to_dict(request, weibo_db, page)
            response_dict['total'] = total
            return HttpResponse(json.dumps(response_dict), status=200)
        else:
            return HttpResponse(status=404)
    except:
        logger.error('未知错误')
        return HttpResponse(status_str % 6, status=500)


# 搜索用户
def search_user(request):
    """
    返回及状态说明：
        status
            0:成功
            2:空的关键字
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            try:
                page = int(request.GET.get('page', 1))
            except:
                page = 1
            try:
                num = int(request.GET.get('num'), 10)
            except:
                num = 10
            key_word = request.GET.get('key')
            if not key_word:
                return HttpResponse(status_str % 2, status=403)
            user_db, total = search_user_lib(key_word)
            user_db = page_of_queryset(user_db, page, num)
            response_list = process_user_to_list(user_db)
            return HttpResponse(json.dumps({'page': page, 'list': response_list, 'total':total, 'status': 0}))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse(status_str % 6, status=500)


"""DELETE"""


# 删除微博
def delete_weibo(request):
    """
    返回及status状态说明
        0:成功
        1：未检查到指定微博
        4：未登录
        5：权限不足（不是自己的微博）

    :param request:
    :return:
    """
    if request.method == "DELETE":
        query = re.findall(r'((\w+)=(\w+))', request.body.decode('utf-8'))
        for t in query:
            if t[1] == 'weibo_id':
                weibo_id = t[2]
        try:
            weibo_id = int(weibo_id)
            weibo = WeiboItem.objects.get(id=weibo_id)
        except:
            # 未检查到ID
            return HttpResponse("{\"status\":1}")
        user = check_logged(request)
        if user:
            if weibo.author == user:
                weibo.delete()
                user.user_info.weibo_num -= 1
                user.save()
                return HttpResponse("{\"status\":0}")
            else:
                return HttpResponse("{\"status\":5}")
        else:
            return HttpResponse("{\"status\":4}")


# 删除评论
def delete_comment(request):
    """
    返回及status状态说明
        status
            0:成功
            2：找不到指定评论
            3：找不到指定微博
            4：未登录
            5：无权限
            6：未知错误
            7：数据异常
        非DELETE请求不做处理，返回404
    :param request:
    :return:
    """
    try:
        if request.method == 'DELETE':
            user = check_logged(request)
            if not user:
                logger.debug("未登录")
                return HttpResponse("{\"status\":4}", status=401)
            query = re.findall(r'((\w+)=(\w+))', request.body.decode('utf-8'))
            for t in query:
                if t[1] == 'comment_id':
                    comment_id = t[2]
            try:
                comment = WeiboComment.objects.get(id=int(comment_id))
            except:
                logger.debug("找不到评论")
                return HttpResponse("{\"status\":2}")
            for t in query:
                if t[1] == 'weibo_id':
                    weibo_id = t[2]
            try:
                weibo = WeiboItem.objects.get(id=weibo_id)
            except:
                logger.debug("找不到指定微博")
                return HttpResponse("{\"status\":3}", status=406)
            if comment.weibo == weibo:
                if comment.author == user:
                    comment.delete()
                    return HttpResponse("{\"status\":0}")
                else:
                    logger.debug("评论作者非登陆用户")
                    return HttpResponse("{\"status\":5}", status=403)
            else:
                logger.debug("微博于评论微博不匹配")
                return HttpResponse("{\"status\":7}", status=403)
        else:
            return HttpResponse(status=404)
    except:
        logger.error("未知错误")
        return HttpResponse("{\"status\":6}", status=500)


"""POST"""


# 发表微博
def create_weibo(request):
    """
    返回及status状态说明
        0：成功
        2：未登录
        3：微博类型非数字
        4：在微博内容为纯文本的情况下没有内容
        5：转发失败
        6：未知错误
        7：super非数字

    :param request:
    :return:
    """
    content = request.POST.get('content', '')
    pictures = request.POST.get('picture', '[]')
    super_weibo_id = request.POST.get('super', '')
    content_type = request.POST.get('content_type', 0)
    video_id = request.POST.get('video', '')

    # 安全检查
    # 类型转换
    try:
        content_type = int(content_type)
    except:
        # 微博类型非数字
        return HttpResponse("{\"status\":3}")

    try:
        super_weibo_id = int(super_weibo_id)
    except:
        # 父微博ID非数字
        super_weibo_id = None

    try:
        pictures = json.loads(pictures)
    except:
        pictures = None

    # 登陆状态检查
    user = check_logged(request)
    if not user:
        # 未登录
        return HttpResponse("{\"status\":2}")
    if content_type == 0 and (not content):
        # 在微博内容为纯文本的情况下没有内容
        return HttpResponse('{\"status\":4}')
    return to_create_weibo(content=content, user=user, content_type=content_type, imgs_id=pictures, video_id=video_id, super_weibo_id=super_weibo_id)


# 上传图片
def upload_image(request):
    """
    返回及状态说明
        0：成功
        4：未登录
        6：未知错误
        7：未发现上传的图片
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            user = check_logged(request)
            if not user:
                return HttpResponse(status_str % 4, status=401)
            try:
                logger.debug('尝试获取照片')
                image = request.FILES['image']
            except:
                # 没有发现上传的图片
                return HttpResponse("{\"status\":7}", status=204)
            img_db = Images(image=image)
            logger.debug('尝试图片数据库文件')
            img_db.save()
            logger.debug('成功创建图片数据库文件')
            user.user_info.gallery.add(img_db)
            return HttpResponse(json.dumps({'img_id': img_db.image_id, 'status': 0}, status=201))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 上传视频
def upload_video(request):
    """
    返回及状态说明
        0：成功
        6：未知错误
        7：未发现上传的图片
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            try:
                video = request.FILES['video']
            except:
                logger.debug("没有发现上传的视频")
                return HttpResponse("{\"status\":7}", status=204)
            video_db = Video(video=video)
            video_db.save()
            return HttpResponse(json.dumps({'video_id': video_db.video_id, 'status': 0}, status=201))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 收藏微博
def collect_weibo(request):
    """
    返回及状态说明
        0:成功
        2：找不到指定微博
        4：未登录
        6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            weibo_id = request.POST.get('weibo_id', '')
            try:
                weibo_id = int(weibo_id)
                weibo = WeiboItem.objects.get(id=weibo_id)
                assert weibo.is_active
            except:
                return HttpResponse("{\"status\":2}", status=404)

            user = check_logged(request)
            if not user:
                return HttpResponse("{\"status\":4}", status=401)
            user.user_info.collect_weibo.add(weibo)
            return HttpResponse("{\"status\":0}")
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 发表评论
def comment_weibo(request):
    """
    返回及状态说明
        0：成功
        2：未找到指定微博
        3：微博内容不满足条件
        4：未登录
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            content = request.POST.get('content')
            weibo_id = request.POST.get('weibo_id')
            user = check_logged(request)
            if not user:
                logger.debug('未登录')
                return HttpResponse("{\"status\":4}", status=401)
            try:
                weibo = WeiboItem.objects.get(id=int(weibo_id))
                assert weibo.is_active
            except:
                # 未找到指定微博
                logger.debug('未找到指定微博')
                return HttpResponse("{\"status\":2}", status=404)

            # content内容检查
            if content and len(content) < 128:
                create_weibo_comment(user, weibo, content)
                return HttpResponse("{\"status\":0}")
            else:
                logger.debug("微博内容不满足条件")
                return HttpResponse("{\"status\":3}", 403)
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 改变like微博的状态
def change_like_status(request):
    """
    返回及status状态说明
        0：成功
        2：未找到指定微博
        4：未登录
        6:未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            weibo_id = request.POST.get('weibo_id', '')
            user = check_logged(request)
            if not user:
                logger.debug("未登录")
                return HttpResponse("{\"status\":4}", status=401)
            try:
                weibo = WeiboItem.objects.select_related('weiboinfo').get(id=int(weibo_id))
                assert weibo.is_active
            except:
                logger.debug("未找到指定微博")
                return HttpResponse("{\"status\":2}")

            if weibo.weiboinfo.like.filter(id=user.id):
                weibo.weiboinfo.like.remove(user)
                weibo.weiboinfo.like_num -= 1
                is_like = False
            else:
                weibo.weiboinfo.like.add(user)
                weibo.weiboinfo.like_num += 1
                is_like = True
            weibo.weiboinfo.save()
            return HttpResponse(json.dumps({'is_like': is_like, 'status':0}))
        else:
            return HttpResponse(status=404)
    except:
        logger.error("未知错误")
        return HttpResponse("{\"status\":6}", status=500)


# 改变notice的阅读状态
def change_notice_read(request):
    try:
        if request.method == 'POST':
            user = check_logged(request)
            if not user:
                logger.debug("未登录")
                return HttpResponse(status_str % 4, status=401)
            try:
                n = Notice.objects.get(id=int(request.POST.get('notice_id', '')))
            except:
                logger.debug("未找到指定消息")
                return HttpResponse(status_str % 2, status=404)
            if n.recipient == user:
                n.read = True
                n.save()
                return HttpResponse(status_str % 0)
            else:
                logger.debug('权限不足')
                return HttpResponse(status_str % 5, status='403')
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse(status_str % 6, status=500)
