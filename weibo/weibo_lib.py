from account.account_lib import check_logged
from account.models import User
from .models import WeiboToVideo, WeiboItem, Images, WeiboToImage, Video
from django.http import HttpResponse
import pathlib
import json


# 将微博数据库QuerySet处理为json字符串
def weibo_list_process_to_str(request, weibo_db, page):
    weibo_list_response_date = []
    for item in weibo_db:
        item_data = {
            "type": 'text' if item.content_type == 0 else 'image' if item.content_type == 1 else 'video',
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
        if item.content_type == 1:  # img
            imgs_path = pathlib.Path(
                r'./media/weibo/pictures/{0}.{1}.{2}/{3}'.format(item.create_time.year, item.create_time.month,
                                                                 item.create_time.day, item.id))
            imgs_list = []
            if imgs_path.is_dir():
                for img in imgs_path.iterdir():
                    imgs_list.append(img.as_posix())
            item_data['imgs'] = imgs_list
        elif item.content_type == 2:  # video
            video_path = pathlib.Path(
                r'./media/weibo/video/{0}.{1}.{2}/{3}'.format(item.create_time.year, item.create_time.month,
                                                              item.create_time.day, item.id))
            if video_path.is_dir():
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


# 创建微博
def to_create_weibo(content, user, content_type=0, imgs_id=None, video_id=None, super_weibo_id=None):
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
        weibo = WeiboItem(author=user, super=super_weibo_id, content=content)
        if super_weibo_id:
            try:
                super_weibo = WeiboItem.objects.get(id=super_weibo_id)
                weibo.super = super_weibo
            except:
                return HttpResponse("{\"status\":5}", status=500)
        weibo.save()
        user.user_info.weibo_num += 1
        user.user_info.save()
        if content_type == 1:
            if imgs_id:
                imgs_db = Images.objects.none()
                for img_id in imgs_id:
                    try:
                        imgs_db = imgs_db | Images.objects.get(image_id=img_id)
                    except:
                        pass

                if imgs_db:
                    weibo.content_type = 1
                    weibo.save()
                    for img in imgs_db:
                        WeiboToImage(weibo=weibo, image=img).save()
                    return HttpResponse("{\"status\":0}", status=200)

            # 没有检测到上传的图片信息，更正微博类型为0，并保存微博
            weibo.content_type = 0
            weibo.save()
            return HttpResponse(json.dumps({"status": "0","info": "We didn't find any picture, changed type to \"text\"."}))
        elif content_type == 2:
            if video_id:
                try:
                    video_db = Video.objects.get(video_id=video_id)
                except:
                    video_db = None
                if video_db:
                    weibo.content_type = 2
                    weibo.save()
                    WeiboToVideo(weibo=weibo, video=video_db).save()
                    return HttpResponse("{\"status\":0}", status=200)
            # 没有检测到上传的视频信息，更正微博类型为0，并保存微博
            weibo.content_type = 0
            weibo.save()
            return HttpResponse(json.dumps({"status": "0","info": "We didn't find any video, changed type to \"text\"."}))
        else:
            weibo.content_type = 0
            weibo.save()
            return HttpResponse("{\"status\":0}", status=200)
    except:
        return HttpResponse("{\"status\":6}")