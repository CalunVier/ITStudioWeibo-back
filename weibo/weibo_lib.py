from account.account_lib import check_logged
from account.models import User
import pathlib
import json


def weibo_list_process(request, weibo_db, page):
    weibo_list_response_date = []
    for item in weibo_db:
        item_data = {
            "type": 'text' if item.contant_type == 0 else 'image' if item.contant_type == 1 else 'video',
            "content": item.content,
            "author_id": item.author.username,
            "author_name": item.author.nick,
            "author_head": item.author.head.url,
            "forward_num": item.weiboinfo.forward_num,
            "comment_num": item.weiboinfo.comment_num,
            "like_num": item.weiboinfo.like_num,
            "time": item.create_time.timestamp(),
        }

        # 检查是否following
        if check_logged(request):
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
        if item.contant_type == 1:  # img
            imgs_path = pathlib.Path(
                r'./media/weibo/pictures/{0}.{1}.{2}/{3}'.format(item.create_time.year, item.create_time.month,
                                                                 item.create_time.day, item.id))
            imgs_list = []
            for img in imgs_path.iterdir():
                imgs_list.append(img.as_posix())
            item_data['imgs'] = imgs_list
        elif item.contant_type == 2:  # video
            video_path = pathlib.Path(
                r'./media/weibo/video/{0}.{1}.{2}/{3}'.format(item.create_time.year, item.create_time.month,
                                                              item.create_time.day, item.id))
            for v in video_path.iterdir():
                item_data['video'] = v.as_posix()
        # 添加到返回列
        weibo_list_response_date.append(item_data)
    response_data = {
        'page': page,
        'list': weibo_list_response_date,
        'status': 0,
    }
    response_data = json.dumps(response_data)
    return response_data
