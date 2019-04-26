from django.shortcuts import render
from django.http import HttpResponse
from account.account_lib import check_logged
from account.models import User
from ITstudioWeibo.calunvier_lib import page_of_queryset
from .models import WeiboItem
from .weibo_lib import weibo_list_process
from django.db.models.query import QuerySet
import json
import pathlib
import logging


logger = logging.getLogger('django.weibo')


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
        tag = request.GET.get('tag', 'follow')

        # 检索数据库
        if tag == 'follow':
            logged, user = check_logged(request)
            if logged:
                # todo 优化数据库
                followings = user.userweiboinfo_set.all()
                weibo_db = WeiboItem.objects.none()
                if followings:
                    for author_info in followings:
                        weibo_db = weibo_db | WeiboItem.objects.filter(author=author_info.user)
            else:
                # todo 查询要求登陆的http状态码
                return HttpResponse(json.dumps({'status': 2}), status=400)
        elif tag == 'video':
            weibo_db = WeiboItem.objects.filter(contant_type=2)
        else:
            weibo_db = WeiboItem.objects.all().order_by('-weiboinfo__like_num')

        # 分页
        weibo_db = page_of_queryset(weibo_db, page=page, num=10)

        # 循环处理数据库中的数据
        response_data = weibo_list_process(request, weibo_db, page)

        # 处理完毕返回列表
        return HttpResponse(response_data, status=200)
    else:
        # 非POST不接
        return HttpResponse(status=404)



