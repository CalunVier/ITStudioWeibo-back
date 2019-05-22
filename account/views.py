import datetime
import json
import logging
import re
from django.http import HttpResponse
from ITstudioWeibo.calunvier_lib import page_of_queryset
from ITstudioWeibo.general import check_email_verify_code_not_right, get_pages_info
from weibo.models import WeiboItem, Images
from weibo.weibo_lib import weibo_list_process_to_dict
from .account_lib import check_user_id_verify, check_password_verify, set_login_cookie, check_email_verify, to_register, \
    check_logged, delete_login_cookie
from .models import UserWeiboInfo, User

logger = logging.getLogger('my_logger.account.view')
status_str = '{"status": %d}'

"""POST"""


# 注册
def register(request):
    """
    返回及status状态返回说明
    接收到POST请求时：
        0: 注册成功
        1：用户ID重复
        2：邮箱重复
        3:验证码错误
        5：无效的密码
        6:未知错误
        7:用户id无效
        10：无效的邮箱
    非POST请求不做处理，返回HTTP状态404
    """
    try:
        if request.method == 'POST':
            logger.debug('收到post请求')

            # 为了兼容旧代码 构建post_body_json
            post_body_json = {
                'email': request.POST.get('email', ''),
                'password': request.POST.get('password', ''),
                'verify_code': request.POST.get('verify_code', ''),
                'username': request.POST.get('user_id', '')
            }
            # 检查验证码是否正确
            if not check_email_verify_code_not_right(post_body_json['email'], post_body_json['verify_code'], 'reg'):
                logger.debug('验证码检查通过')

                # 检查用户ID合法
                if not check_user_id_verify(post_body_json['username']):
                    return HttpResponse(status_str % 7, status=412)

                # post判断post_body是否存在所需内容
                if not check_email_verify(post_body_json['email']):
                    logger.info('邮箱格式不合法')
                    return HttpResponse("{\"status\":10}", status=412)

                if not check_password_verify(post_body_json['password']):
                    logger.info('密码不合法')
                    return HttpResponse("{\"status\":5}", status=412)
                # 写入数据库
                logger.info('将注册信息写入数据库')
                result, user = to_register(post_body_json['username'], post_body_json['password'], post_body_json['email'])
                # 返回结果
                if not result:      # 注册成功返回0，故not
                    # 注册成功
                    logger.debug('返回注册成功')
                    return HttpResponse("{\"status\":0}", status=200)
                else:
                    # 注册失败返回状态码
                    logger.error('注册失败,状态码：%d', result)
                    return HttpResponse("{\"status\":" + str(result) + "}", status=406)

            else:
                # 验证码错误，返回状态码
                logger.debug(check_email_verify_code_not_right(post_body_json['email'], post_body_json['verify_code'], 'reg'))
                logger.debug('验证码错误'+post_body_json['email']+post_body_json['verify_code']+'reg')
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
                if not check_password_verify(post_body_json['password']):
                    # 无效的密码
                    logger.info('无效的密码')
                    return HttpResponse("{\"status\":2}", status=400)

                # 查询用户，获取用户数据库对象
                user = User.objects.filter(email=post_body_json['user_key'])

                if user:
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
            logger.debug("收到POST请求")
            new_sex = request.POST.get('user_sex', -1)      # 如果未给出该参数，则-1，标记为未给定
            new_birth = request.POST.get('user_birth', '')  # 如果未给出，置为空
            new_school = request.POST.get('school', '')     # 如果未给出，置为空
            # 登陆状态检查
            user = check_logged(request)
            if not user:
                # 未登录
                return HttpResponse("{\"status\":4}", status=401)

            # 数据预处理
            re_birth = re.match(r'^(\d+)-(\d+)-(\d+)$', new_birth)    # 正则匹配
            if re_birth:
                try:
                    new_birth = datetime.datetime(year=int(re_birth.group(1)), month=int(re_birth.group(2)), day=int(re_birth.group(3)))
                except:
                    logger.debug('无效的日期')
                    new_birth = None
            else:
                logger.debug('未匹配到新生日信息')
                new_birth = None
            try:
                new_sex = int(new_sex)
            except:
                logger.debug('无效的新性别')
                new_sex = -1

            if new_sex in (0, 1, 2, 3):
                user.sex = new_sex
                logger.debug("新性别已添加")
            if new_birth and new_birth < datetime.datetime.now():
                user.birth = new_birth
                logger.debug("新出生日期已添加")
            if new_school:
                if new_school == 'none':
                    user.school = ''
                    logger.debug('学校已置为空')
                else:
                    user.school = new_school
                    logger.debug("新学校已添加")
            user.save()
            logger.debug('信息保存成功')
            return HttpResponse("{\"status\":0}")
        else:
            return HttpResponse(status=404)
    except:
        logger.error('未知错误')
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
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            username = request.POST.get('user_id', '')
            if not check_password_verify(new_password):
                # 新密码不符合规范
                return HttpResponse("{\"status\":2}", status=406)
            if not check_password_verify(old_password):
                # 旧密码不符合规范
                return HttpResponse("{\"status\":3}", status=406)
            # 数据库检索用户
            try:
                user = User.objects.get(username=username)
            except:
                logger.debug('未检索到用户:%s', username)
                return HttpResponse("{\"status\":1}", status=404)
            # 检查旧密码是否正确
            if user.check_password(old_password):
                user.password = new_password
                user.save()
                logger.debug('密码已修改')
                return HttpResponse("{\"status\":0}")
            else:
                # 旧密码错误
                return HttpResponse("{\"status\":3}", status=403)
        else:
            return HttpResponse(status=404)
    except:
        logger.error('未知错误')
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
        user = check_logged(request)
        if not user:
            logger.debug('未登录')
            return HttpResponse("{\"status\":4}", status=401)
        # 检索图片
        try:
            head_img = Images.objects.get(image_id=int(request.POST.get('head', '')))
        except:
            logger.debug('未检索到图片，image_id: %s' % request.POST.get('head', ''))
            return HttpResponse("{\"status\":3}", status=406)
        user.head = head_img.image
        user.save()
        return HttpResponse("{\"status\":0}")
    except:
        logger.debug('未知错误')
        return HttpResponse("{\"status\":6}", status=500)


def change_username(request):
    """
    返回及status状态说明
        0:成功
        3：昵称不合法
        4：未登录
        5:用户名重复
        6：未知错误
    :param request:
    :return:
    """
    try:

        username = request.POST.get('name', '')
        if not check_user_id_verify(username):
            logger.debug('新用户id不合法：username=%s' % username)
            return HttpResponse("{\"status\":3}", status=403)

        user = check_logged(request)
        if not user:
            logger.debug('未登录')
            return HttpResponse("{\"status\":4}", status=401)

        if not User.objects.filter(username=username):
            user.username = username
            user.save()
            return HttpResponse("{\"status\":0}")
        else:
            logger.info('用户名重复')
            return HttpResponse(status_str % 5, status=403)

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
        4：错误的email
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
                # 错误的email
                return HttpResponse(status_str % 4)
            if check_email_verify_code_not_right(email, verfy_code, 'forgot'):
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
            "follow_num": user_info_db.follow_num,
            "fans_num": user_info_db.fans_num,
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
                "user_id":user.username,
                "user_head": user.head.url,     # 头像
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
                "photo": [user.head.url]
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
                weibo_info_db = user.like_weibo.select_related('weibo').exclude(weibo__is_active=False)
                weibo_info_db = page_of_queryset(weibo_info_db, page, num)
                weibo_db = []
                for info in weibo_info_db:
                    weibo_db.append(info.weibo)
                del weibo_info_db
            elif tag == 'collect':
                weibo_db = user.user_info.collect_weibo.all().exclude(is_active=False)
            elif tag == 'original':
                weibo_db = WeiboItem.objects.filter(author=user, super_weibo=None).exclude(is_active=False)
            elif tag == 'my_weibo':
                weibo_db = WeiboItem.objects.filter(author=user).exclude(is_active=False)
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


# 我关注的人
def following_list(request):
    """
    返回及status状态说明
        status
            0:成功
            4：未登陆
            6：未知错误
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
            user = check_logged(request)
            if not user:
                logger.debug("未登录")
                return HttpResponse('{"status":4}', status=401)
            following_user_db = user.user_info.following.exclude(is_active=False)
            following_user_db = page_of_queryset(following_user_db, page, num)
            response_list = []
            for fu in following_user_db:
                response_list.append({
                    "user_id": fu.username,
                    "user_head": fu.head.url,
                    "user_info": fu.intro
                })
            return HttpResponse(json.dumps({'page':page, 'list':response_list, 'status': 0}))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 关注我的人
def followers_list(request):
    """
    返回及status状态说明
        status
            0:成功
            4：未登陆
            6：未知错误
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
            user = check_logged(request)
            if not user:
                logger.debug("未登录")
                return HttpResponse('{"status":4}', status=401)
            followers_info_db = user.followers.select_related('user').exclude(user__is_active=False)
            followers_info_db =page_of_queryset(followers_info_db, page, num)
            response_list = []
            for fi in followers_info_db:
                response_list.append({
                    "user_id": fi.user.username,
                    "user_head": fi.user.head.url,
                    "user_info": fi.user.intro
                })
            return HttpResponse(json.dumps({'page': page, 'list': response_list, 'status': 0}))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse("{\"status\":6}", status=500)


# 获取相册
def get_gallery(request):
    """
    返回及status状态说明
        status
            0：成功
            1：位置用户
            3：错误的日期
            6：未知错误
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            page, num = get_pages_info(request)
            try:
                user = User.objects.get(username=request.GET.get('user_id', ''))
            except:
                return HttpResponse(status_str % 1, status=404)
            time = re.match(r'^(\d+)-(\d+)', request.GET.get('time', ''))
            if not time or not (0 < int(time.group(2)) < 13 and 1970 < int(time.group(1)) < 2020):
                logger.debug("错误的日期")
                return HttpResponse(status_str % 3, status=406)
            gallery = user.user_info.gallery.filter(upload_time__year=int(time.group(1)), upload_time__month=int(time.group(2)))
            gallery = page_of_queryset(gallery, page, num)
            response_list = []
            for img in gallery:
                response_list.append({'url': img.image.url, 'time': img.upload_time.timestamp()})
            return HttpResponse(json.dumps({'list': response_list, 'status': 0}))
        else:
            return HttpResponse(status=404)
    except:
        return HttpResponse(status_str % 6, status=500)


def log_page(request):
    log = ''.join(open('server_log', 'r').readlines()[-100:])
    log = log.replace('\n', '<br/>')
    return HttpResponse(log)
