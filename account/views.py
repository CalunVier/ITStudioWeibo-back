from django.shortcuts import render
from django.http import HttpResponse
from .models import UserWeiboInfo, User
from .account_lib import check_password_verify, set_login_cookie, check_email_verify, to_register, sign_password_md5, check_logged
from ITstudioWeibo.general import check_email_verify_code_not_right
import logging
import json
import random
import string

# todo 解决删除用户再注册的问题
logger = logging.getLogger('my_logger.account.view')


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
            if 'username' not in request.session:
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
    if request.method == 'GET':
        if 'user_id' in request.session:
            logger.info(request.session['user_id']+'退出登录')
            request.session.flush()
            response = HttpResponse("{\"status\":\"ok\"}")
            # todo 登出函数等待适配
            try:
                response.delete_cookie('sessionid')
                response.delete_cookie('user_id')
                response.delete_cookie('user_nick')
            finally:
                pass
            return response
        else:
            return HttpResponse("{\"status\":\"not_logged_in\"}")
    else:
        # 非get不接
        pass


# 获取用户信息
def get_user_info(request):
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
        1：未知用户
        2：未登录
    对于非GET请求不做处理，返回Http状态404
    """
    if request.method == 'GET':
        if check_logged(request):
            try:
                user = User.objects.select_related('userweiboinfo').get(username=request.COOKIES.get('username'))
            except:
                return HttpResponse("{\"status\":1}",status=404)
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
