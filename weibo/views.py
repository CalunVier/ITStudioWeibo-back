from django.shortcuts import render
from django.http import HttpResponse
from account.account_lib import check_logged
from account.models import User
from ITstudioWeibo.calunvier_lib import page_of_queryset
from .models import WeiboItem, Images, WeiboToImage, Video, WeiboToVideo
from .weibo_lib import weibo_list_process_to_dict, to_create_weibo
from django.db.models.query import QuerySet
import json
import pathlib
import logging


logger = logging.getLogger('my_logger.weibo.view')


def get_item_list(request):
    """
    :status :
        0:正常
        2:要求登陆
    """
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
                followings = user.userweiboinfo_set.all()
                weibo_db = WeiboItem.objects.none()
                if followings:
                    for author_info in followings:
                        weibo_db = weibo_db | WeiboItem.objects.select_related('super', 'weiboinfo').filter(author=author_info.user)
            else:
                return HttpResponse(json.dumps({'status': 2}), status=401)
        elif tag == 'video':
            weibo_db = WeiboItem.objects.select_related('super', 'weiboinfo').filter(content_type=2)
        else:
            weibo_db = WeiboItem.objects.select_related('super', 'weiboinfo').all().order_by('-weiboinfo__like_num')

        # 分页
        weibo_db = page_of_queryset(weibo_db, page=page, num=num)

        # 循环处理数据库中的数据
        response_data = weibo_list_process_to_dict(request, weibo_db, page)

        # 处理完毕返回列表
        return HttpResponse(json.dumps(response_data), status=200)
    else:
        # 非POST不接
        return HttpResponse(status=404)


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
