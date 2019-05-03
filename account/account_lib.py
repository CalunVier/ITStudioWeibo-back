from .models import User
from account.models import User
import hashlib
import json
import datetime
import logging
import re
import time
from django.contrib.auth.hashers import is_password_usable

logger = logging.getLogger('my_logger.account.lib')


# 注册
def to_register(username, nick, password, email):
    """
    返回值
        0:注册成功
        1：用户id重复
        2：邮箱已被注册
    """
    try:
        if User.objects.filter(username=username):
            logger.info('用户名重复')
            return 1, None
        if User.objects.filter(email=email):
            logger.info('邮箱重复')
            return 2, None
        user = User(username=username, password=password, email=email, nick=nick)
        user.save()
        return 0, user
    except Exception:
        logger.error('写入数据库失败')
        return 6, None


# 用于对密码进行MD5加密的函数
def sign_password_md5(passwd, salt='kHa4sDk3dhQf'):
    hashpwd_builder = hashlib.md5()         # 构建md5加密器
    hashpwd_builder.update((passwd+salt).encode())
    return hashpwd_builder.hexdigest()      # 返回加密结果


# 用于安全的获取json内容 保证获取到的json字典中包含args_list的内容
def get_json_dirt_safe(data_str, args_list=[]):
    # 读取post的内容
    # 使用try防止乱推出现异常崩溃
    try:
        post_body_json = json.loads(data_str)
    except Exception:
        post_body_json = {}
        for arg in args_list:
            post_body_json[arg] = ''
        return post_body_json
    if not isinstance(post_body_json, dict):
        post_body_json = {}
    for arg in args_list:
        if arg not in post_body_json:
            post_body_json[arg] = ''
    return post_body_json


# 检查dirt中各个元素是否有效
def check_dirt_args_valid(json_dirt, args_list=[]):
    """
    检查dirt中各个元素是否有效
    若无效，则返回无效元素名称
    若全部有效，则返回空字符串
    """
    for arg in args_list:
        if not json_dirt[arg]:
            return arg
    return ''


# 用于登录的函数
def set_login_cookie(request, response, user):
    """
    登陆session结构：
    'username': user.username
    'login_time': time.time()（时间戳）

    登陆cookie结构：
    'session_key': session_key
    'username': user.username
    """
    try:
        request.session['username'] = user.username
        request.session['login_time'] = time.time()
        response.set_cookie('username', user.username)
        # response.set_cookie('user_name', bytes(user.nickname, 'utf-8').decode("ISO-8859-1"))
        logger.info('登陆成功')
    except Exception:
        logger.error('登陆失败')


# 检查密码是否合法
def check_password_verify(password):
    if not is_password_usable(password):
        # 检查长度合法性
        if 5 < len(password) < 17:
            for c in password:
                if not 32 < ord(c) < 127:
                    logger.info('密码含有违规字符')
                    return False
            return True
        else:   # 长度不合法
            logger.info('密码长度不合法')
            return False
    else:
        return False


# 检查用户ID格式是否合法
def check_user_id_verify(user_id):
    if 5 < len(user_id) < 17:
        if re.match(r'^[A-Za-z1-9_]+$', user_id):
            return True
        else:
            return False
    else:
        return False


# 检查邮箱是否合法
def check_email_verify(email):
    return re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', email)


# 检查昵称是否合法
def check_nickname_verify(nickname):
    try:
        if 0 < len(nickname) < 21:
            if re.match(r'^\w+$', nickname):
                return True
            else:
                return False
        else:
            return False
    except Exception:
        return False


# 检查是否登陆
def check_logged(request) -> User:
    if 'username' in request.COOKIES:   # 检查username是否存在于COOKIE
        if time.time()-request.COOKIES.get('login_time', 0) < 86400: # 检查登陆是否过期
            # 检查登陆是否异常
            if request.COOKIES.get('username') and request.COOKIES.get('username') == request.session.get('username', ''):
                # 检查是否存在于数据库
                user = User.objects.filter(username=request.COOKIES.get('username'))
                if user:
                    # 检查用户是否为active
                    if user[0].is_active:
                        return user[0]
                    else:
                        return None
                else:
                    return None
            else:
                return None
        else:
            return None
    else:
        return None
