from django.shortcuts import render
from django.http import HttpResponse
from account.account_lib import check_logged
from account.models import User
from ITstudioWeibo.calunvier_lib import page_of_queryset
from .models import WeiboItem, Images, WeiboToImage, Video, WeiboToVideo, WeiboComment
from .weibo_lib import weibo_list_process_to_dict, to_create_weibo, create_weibo_comment
from django.db.models.query import QuerySet
import json
import pathlib
import re
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
            page = request.GET.get('page', 1)
            try:
                page = int(page)
            except:
                page = 1
            num = request.GET.get('num', 10)
            try:
                num = int(num)
            except:
                num = 10

            tag = request.GET.get('tag', 'hot')

            # 检索数据库
            if tag == 'follow':
                user = check_logged(request)
                if user:
                    # todo 优化数据库
                    followings = user.user_info.following.all()
                    weibo_db = WeiboItem.objects.none()
                    if followings:
                        for author in followings:
                            weibo_db = weibo_db | WeiboItem.objects.select_related('super', 'weiboinfo').filter(author=author).exclude(is_active=False)
                    weibo_db.order_by('-create_time')
                else:
                    return HttpResponse(json.dumps({'status': 4}), status=401)
            elif tag == 'video':
                weibo_db = WeiboItem.objects.select_related('super', 'weiboinfo').filter(content_type=2).exclude(is_active=False)
            else:
                weibo_db = WeiboItem.objects.select_related('super', 'weiboinfo').exclude(is_active=False).order_by('-weiboinfo__like_num')

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
        return HttpResponse("{\"status\":6}")


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
            weibo_id = request.GET.get('weibo_id', '')
            try:
                weibo_id = int(weibo_id)
                item = WeiboItem.objects.get(id = weibo_id)
                assert item.is_active
            except:
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
            if item.super:
                item_data['is_forward'] = True
                item_data["super_weibo"] = {
                    'weibo_id': item.super.id,
                    'content': item.super.content,
                    'author_id': item.super.author.id,
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
                    check_follow = user.userweiboinfo.following.filter(username=item_data['author_id'])
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
                        "comment_id": comment.id
                    }
                    response_list.append(comment_dict)
                return HttpResponse(json.dumps({"page": page, "list": response_list, "status": 0}))
            elif tag == 'forward':
                # 检索数据库，为方便复制代码，变量名为comment
                comments = WeiboItem.objects.select_related('author').filter(super=weibo).exclude(is_active=False)
                # 分页
                comments = page_of_queryset(comments, page, num)
                response_list = []
                for comment in comments:
                    comment_dict = {
                        "user_id": comment.author.username,
                        "user_head": comment.author.head.url,
                        "time": comment.create_time.timestamp(),
                        "comment_id": comment.id
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
            try:
                weibo = WeiboItem.objects.select_related('weiboinfo').get(int(request.GET.get('weibo_id', '')))
            except:
                logger.debug("找不到指定微博")
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
            return HttpResponse(json.dumps({"page": page, 'list':response_list, 'status': 0}))
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
        weibo_id = request.POST.get("weibo_id")
        try:
            weibo_id = int(weibo_id)
            weibo = WeiboItem.objects.get(id = weibo_id)
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
            try:
                comment = WeiboComment.objects.get(id=int(request.POST.get('comment_id', '')))
            except:
                logger.debug("找不到评论")
                return HttpResponse("{\"status\":2}")
            try:
                weibo = WeiboItem.objects.get(id = int(request.POST.get('weibo_id', '')))
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
    content = request.GET.get('content', '')
    pictures = request.GET.get('picture', '[]')
    super_weibo_id = request.GET.get('super', '')
    content_type = request.GET.get('content_type', '0')
    video_id = request.GET.get('video','')

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
        return HttpResponse("{\"status\":7}")

    try:
        pictures = json.dumps(pictures)
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
        6：未知错误
        7：未发现上传的图片
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            try:
                image = request.FILES['image']
            except:
                # 没有发现上传的图片
                return HttpResponse("{\"status\":7}", status=204)
            img_db = Images(image=image)
            img_db.save()
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
                video = request.FILES['image']
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
            user.user_info.collect_weibo.add(*weibo)
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

            if weibo.weiboinfo.like.filter(user):
                weibo.weiboinfo.like.remove(user)
                weibo.weiboinfo.like_num -= 1
            else:
                weibo.weiboinfo.like.add(user)
                weibo.weiboinfo.like_num += 1
            weibo.weiboinfo.save()
            return HttpResponse("{\"status\":0}")
        else:
            return HttpResponse(status=404)
    except:
        logger.error("未知错误")
        return HttpResponse("{\"status\":6}", status=500)
