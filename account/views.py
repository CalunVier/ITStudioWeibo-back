from django.http import HttpResponse
from .models import UserWeiboInfo, User
from weibo.models import WeiboItem, Images
from .account_lib import check_password_verify, set_login_cookie, check_email_verify, to_register, check_logged, check_nickname_verify, delete_login_cookie
from weibo.weibo_lib import weibo_list_process_to_dict
from ITstudioWeibo.calunvier_lib import page_of_queryset
from ITstudioWeibo.general import check_email_verify_code_not_right
import logging
import json
import random
import datetime
import re
import string

# todo 解决删除用户再注册的问题
logger = logging.getLogger('my_logger.account.view')

"""POST"""


# 注册
def register(request):
    """
    返回及status状态返回说明
    接收到POST请求时：
        0: 注册成功
        1：用户ID重复(失效)
        2：邮箱重复
        3:验证码错误
        5：无效的密码
        10：无效的邮箱
    非POST请求不做处理，返回HTTP状态404
    """
    try:
        if request.method == 'POST':
            logger.debug('收到post请求')

            # 随机生成用户名
            while True:
                username = ''.join(random.sample(string.ascii_lowercase, 8))
                u_db = User.objects.filter(username=username)
                if not u_db:
                    break

            # 为了兼容旧代码 构建post_body_json
            post_body_json = {
                'email': request.POST.get('email', ''),
                'password': request.POST.get('password', ''),
                'verify_code': request.POST.get('verify_code', ''),
                'username': ''.join(random.sample(string.ascii_lowercase, 8))
            }

            # post判断post_body是否存在所需内容
            if not check_email_verify(post_body_json['email']):
                logger.info('邮箱格式不合法')
                return HttpResponse("{\"status\":10}", status=400)

            # 检查验证码是否正确
            if True or not check_email_verify_code_not_right(post_body_json['email'], post_body_json['verify_code']):
                # logger.debug('验证码检查通过')
                if not post_body_json['password']:
                    logger.info('空密码')
                    return HttpResponse("{\"status\":5}", status=400)

                if not check_password_verify(post_body_json['password']):
                    logger.info('密码不合法')
                    return HttpResponse("{\"status\":5}", status=403)

                # 写入数据库
                logger.info('将注册信息写入数据库')
                result, user = to_register(post_body_json['username'], post_body_json['username'],
                                           post_body_json['password'], post_body_json['email'])
                # 返回结果
                if not result:
                    # 注册成功
                    logger.info('返回注册成功')
                    return HttpResponse("{\"status\":0}", status=200)
                else:
                    # 注册失败返回状态码
                    logger.error('注册失败返回状态码')
                    return HttpResponse("{\"status\":" + str(result) + "}", status=406)

            else:
                # 验证码错误，返回状态码
                logger.info('验证码错误')
                return HttpResponse("{\"result\":3}", status=403)
        else:
            # 非post请求，404
            logger.info('收到非POST请求')
            return HttpResponse(status=404)
    except Exception:
        logger.error('出现未知错误')
        return HttpResponse("{\"status\":6}", status=500)


# 登陆
def login(request):
    """
    返回及status状态说明
        0:登陆成功
        1：无效的用户索引
        2：无效的密码
        4：账户被禁止登陆
        5：已登录（请勿重复登陆）
        6：未知错误
    非POST请求不做处理，返回HTTP状态404
    """
    try:
        if request.method == 'POST':
            logger.info("收到POST请求")

            # 判断是否登陆
            if not check_logged(request):
                # 为兼容旧代码，构建post_body_json
                post_body_json = {
                    'user_key': request.POST.get('email', ''),
                    'password': request.POST.get('password', '')
                }

                # 检查各项是否为空
                if not check_email_verify(post_body_json['user_key']):
                    # 无效的用户ID
                    logger.info('无效的用户索引')
                    return HttpResponse("{\"result\":1}", status=400)
                if not post_body_json['password']:
                    # 无效的密码
                    logger.info('无效的密码')
                    return HttpResponse("{\"status\":2}", status=400)

                # 查询用户，获取用户数据库对象
                user = User.objects.filter(email=post_body_json['user_key'])

                if user and user[0].is_active:
                    # 检索到用户
                    logger.info('检索到用户'+post_body_json['user_key'])
                    user = user[0]
                    if user.is_active:
                        if user.check_password(post_body_json['password']):
                            response = HttpResponse("{\"user_id\":\"%s\",\"status\":0}" % user.username, status=200)
                            set_login_cookie(request, response, user)
                            # 登录成功
                            return response
                        else:
                            # 密码错误
                            logger.info('密码错误')
                            return HttpResponse("{\"status\":2}", status=200)
                    else:
                        # active为Flase，账户被封禁
                        logger.info('账户被封禁')
                        return HttpResponse("{\"status\":4}", status=403)
                else:
                    # 找不到用户，无效用户ID
                    logger.info('找不到用户：' + post_body_json['user_key'])
                    return HttpResponse("{\"status\":1}", status=404)
            else:
                logger.info('已登录，请勿重复登陆')
                return HttpResponse("{\"status\":5}", status=403)
        else:
            # 非POST不接，返回404
            logger.info('收到非post请求')
            return HttpResponse(status=404)
    except Exception:
        logger.error('出现未知错误')
        return HttpResponse("{\"status\":6}", status=500)


# 登出
def logout(request):
    if check_logged(request):
        return delete_login_cookie(request, HttpResponse())
    else:
        logger.debug('未登录')
        return HttpResponse("{\"status\":3}", status=401)


# 修改个人资料
def change_user_info(request):
    """
    返回及status说明
        status
            0:已尝试对有效数据做出更改
            4：未登录
            6：未知错误
        对非POST请求不做处理
    :param request:
    :return:
    """
    try:
        if request.method == "POST":
            new_sex = request.POST.get('user_sex', -1)
            new_birth = request.POST.get('user_birth', '')
            new_school = request.POST.get('school', '')

            user = check_logged(request)
            if not user:
                # 未登录
                return HttpResponse("{\"status\":4}", status=401)

            # 数据预处理
            re_birth = re.match(r'(\d+)-(\d+)-(\d+)', new_birth)
            if re_birth:
                try:
                    new_birth = datetime.datetime(year=int(re_birth.group(1)), month=int(re_birth.group(2)), day=int(re_birth.group(3)))
                except:
                    new_birth = None
            else:
                new_birth = None
            try:
                new_sex = int(new_sex)
            except:
                new_sex = -1

            if new_sex in (0, 1, 2, 3):
                user.sex = new_sex
            if new_birth and new_birth < datetime.datetime.now():
                user.birth = new_birth
            if new_school:
                if new_school == 'none':
                    user.school = ''
                else:
                    user.school = new_school
            user.save()
            return HttpResponse("{\"status\":0}")

        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=503)


# 修改密码
def change_password(request):
    """
    返回及status状态说明
        0:成功
        1：未知用户
        2：新密码不符合规范
        3：旧密码错误
        6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            username = request.POST.get('user_id')
            try:
                user = User.objects.get(username=username)
            except:
                return HttpResponse("{\"status\":1}", status=404)
            if check_password_verify(new_password):
                if user.check_password(old_password):
                    user.password = new_password
                    user.save()
                    return HttpResponse("{\"status\":0}")
                else:
                    # 旧密码错误
                    return HttpResponse("{\"status\":3}", status=403)
            else:
                # 新密码不符合规范
                return HttpResponse("{\"status\":2}", status=406)


        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 修改头像
def change_head(request):
    """
    返回及status状态说明
        0:成功
        3：未找到指定图片
        4：未登录
        6：未知错误
    :param request:
    :return:
    """
    try:
        head_id = request.POST.get('head', '')
        try:
            head_id = int(head_id)
        except:
            head_id = None

        user = check_logged(request)
        if not user:
            return HttpResponse("{\"status\":4}", status=401)

        if head_id is not None:
            try:
                head_img = Images.objects.get(image_id=head_id)
            except:
                return HttpResponse("{\"status\":3}", status=406)
            user.head = head_img.image
            user.save()
            return HttpResponse("{\"status\":0}")
        else:
            return HttpResponse("{\"status\":3}", status=406)
    except:
        return HttpResponse("{\"status\":6}", status=500)


def change_nick(request):
    """
    返回及status状态说明
        0:成功
        3：昵称不合法
        4：未登录
        6：未知错误
    :param request:
    :return:
    """
    try:
        nick = request.POST.get('name', '')

        user = check_logged(request)
        if not user:
            return HttpResponse("{\"status\":4}", status=401)

        if check_nickname_verify(nick):
            user.nick = nick
            user.save()
            return HttpResponse("{\"status\":0}")
        else:
            return HttpResponse("{\"status\":3}", status=403)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 更改关注状态
def new_follow(request):
    """
    返回及status状态说明
        0：成功
        1：位置的follow用户
        4：未登录
        6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == "POST":
            follow_id = request.POST.get("follow_id", '')
            user = check_logged(request)
            if not user:
                return HttpResponse("{\"status\":4}", status=401)

            try:
                follow_user = User.objects.get(username=follow_id)
            except:
                return HttpResponse("{\"status\":1}", status=404)

            if follow_user in user.user_info.following.all():
                user.user_info.following.remove(follow_user)
                user.user_info.follow_num -= 1
                user.user_info.save()
            else:
                user.user_info.following.add(follow_user)
                user.user_info.follow_num += 1
                user.user_info.save()
            return HttpResponse("{\"status\":0}")

        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


def forgot_password(request):
    """
    返回及状态说明
        0:成功
        1：未检索到用户
        2：验证码错误
        3:新密码无效
        6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == "POST":
            email = request.POST.get('email', '')
            verfy_code = request.POST.get('verify_code', '')
            new_password = request.POST.get('new_password','')
            if not check_email_verify(email):
                # 错误的email todo
                return HttpResponse()
            if True or check_email_verify_code_not_right(email, verfy_code):
                # 验证码错误
                return HttpResponse("{\"status\":2}")
            else:
                try:
                    user = User.objects.get(email = email)
                except:
                    # 未检索到用户
                    return HttpResponse("{\"status\":1}", status=404)
                if check_password_verify(new_password):
                    user.password = new_password
                    user.save()
                    return HttpResponse("{\"status\":0}")
                else:
                    return HttpResponse("{\"status\":3}", status=403)

        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


"""GET"""


# 获取用户信息（个人资料）
def user_weibo_info(request):
    """
    返回及status状态说明
        0:成功
        1：未知用户
    :param request:
    :return:
    """
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        try:
            user = User.objects.get(username=user_id)
            user_info_db = UserWeiboInfo.objects.get(user_id = user.id)
        except User.DoesNotExist:
            return HttpResponse("{\"status\":1}", status=403)
        response_data = {
            "user_head": user.head.url,
            "user_name": user.nick,
            "follow_num": user_info_db.follow_num,
            "fans_num": user_info_db.funs_num,
            "status": 0
        }
        return HttpResponse(json.dumps(response_data))
    else:
        return HttpResponse(status=404)


# 获取用户主页信息（个人中心）
def get_user_home(request):
    """
    返回及status状态说明
        0:正常
        2：未登录
    对于非GET请求不做处理，返回Http状态404
    """
    if request.method == 'GET':
        logger.debug(request.COOKIES)
        user = check_logged(request)
        if user:
            response_data = {
                "user_head": user.head.url,     # 头像
                "user_name": user.nick,         # 用户昵称
                "user_info": user.intro,        # 用户简介
                "follow_num": user.user_info.follow_num,    # follow数量
                "weibo_num": user.user_info.weibo_num,      # 微博数量
                "fans_num": user.user_info.fans_num,         # 粉丝数量
                "status": 0
            }
            try:
                response_data = json.dumps(response_data)
            except:
                return HttpResponse(status=500)
            # 正常返回结果
            return HttpResponse(response_data)
        else:
            # 要求登陆
            return HttpResponse("{\"status\":2}", status=401)
    else:
        # 非GET不接
        return HttpResponse(status=404)


# 个人资料的主页
def user_info(request):
    """
    0：成功
    1:未知用户
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            user_id = request.GET.get("user_id")
            try:
                user = User.objects.get(username=user_id)
                assert user.is_active
            except:
                return HttpResponse("{\"status\":1}",status=404)
            response_data = {
                "user_sex": '男' if user.sex==1 else '女' if user.sex==2 else '其他' if user.sex==3 else '未设定',
                "user_birth": user.birth.strftime('%Y-%m-%d'),
                "school": user.school,
                "photo": []
                # todo 添加photo的解析
            }
            return HttpResponse(json.dumps(response_data))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 个人资料的微博
def my_weibo_list(request):
    """
    返回及status状态说明
        status：
            0:成功
            1:未知用户
            3：未定义的tag标签
            4：分页数据错误
            6:未知错误
        非GET请求不做处理返回HTTP状态404
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            tag = request.GET.get("tag", '')
            user_id = request.GET.get("user_id")
            page = request.GET.get("page", 1)
            num = request.GET.get('num', 10)
            try:
                page = int(page)
                num = int(num)
            except:
                # 分页数据错误
                return HttpResponse("{\"status\":4}", 406)

            # 获取用户对象
            try:
                user = User.objects.get(username=user_id)
                assert user.is_active
            except:
                logger.debug("未知用户")
                return HttpResponse("{\"status\":1}", status=404)
            # 判断tag是否有内容
            if tag == 'like':
                # 检索数据库
                weibo_db = user.like_weibo.all()
            elif tag == 'collect':
                weibo_db = user.user_info.collect_weibo.all()
            elif tag == 'personalweibo':
                weibo_db = WeiboItem.objects.filter(author=user, super=None)
            else:
                # 未定义的tag标签
                return HttpResponse("{\"status\":3}", status=406)
            # 分页
            weibo_db = page_of_queryset(weibo_db, page, num)
            response_dict = weibo_list_process_to_dict(request, weibo_db, page)
            return HttpResponse(json.dumps(response_dict), status=200)
        else:
            return HttpResponse(status=404)
    except:
        logger.error("未知错误")
        return HttpResponse("{\"status\":6}")
