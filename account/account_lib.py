from .models import User
from account.models import User
from django.http import HttpResponse
import hashlib
import json
import datetime
import logging
import re
import time
from django.contrib.auth.hashers import is_password_usable

logger = logging.getLogger('my_logger.account.lib')


# 注册
def to_register(username: str, password: str, email: str) -> (int, User):
    """
    返回值
        0:注册成功
        1：用户id重复
        2：邮箱已被注册
    :param username 用户名
    :param password 密码
    :param email 电子邮件
    :returns status:状态码, user: 用户对象，注册失败，返回None
    """
    try:
        if User.objects.filter(username=username):
            logger.debug('用户名重复')
            return 1, None
        if User.objects.filter(email=email):
            logger.debug('邮箱重复')
            return 2, None
        user = User(username=username, password=password, email=email)
        user.save()
        logger.debug('user.save()成功')
        return 0, user
    except Exception:
        logger.error('注册失败')
        return 6, None


# 用于登录的函数
def set_login_cookie(request, response: HttpResponse, user: User):
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
        logger.debug('向session中写入user.username')
        request.session['login_time'] = time.time()
        logger.debug('向session中写入time.time()')
        response.set_cookie('username', json.dumps(user.username))
        logger.debug('向cookie中写入user.username')
        logger.info('登陆成功')
    except Exception:
        logger.error('登陆失败')


# 用于登出的函数
def delete_login_cookie(request, response):
    try:
        request.session.delete()
        logger.debug("删除session")
        logger.debug("遍历cookies")
        for key in request.COOKIES:
            response.delete_cookie(key)
            logger.debug('删除%s' % key)
        response.content = b'{\"status\":0}'
        response.status_code = 200
        return response
    except:
        logger.error('未知错误，登出失败')
        return HttpResponse("{\"status\":6}", status=500)


# 检查密码是否合法
def check_password_verify(password):
    if not is_password_usable(password):
        if 5 < len(password) < 17:
            for c in password:
                if not 32 < ord(c) < 127:
                    logger.debug('密码含有违规字符')
                    return False
            return True
        else:   # 长度不合法
            logger.debug('密码长度不合法')
            return False
    else:
        logger.debug('不可用的密码')
        return False


# 检查用户ID格式是否合法
def check_user_id_verify(user_id):
    if 5 < len(user_id) < 17:
        if re.match(r'^\w+$', user_id):
            return True
        else:
            logger.debug('username含有非法字符')
            return False
    else:
        logger.debug('username长度不符合要求')
        return False


# 检查邮箱是否合法
def check_email_verify(email):
    return re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', email)


# 检查是否登陆
def check_logged(request) -> User:
    if time.time()-request.session.get('login_time', 0) < 86400:    # 检查登陆是否过期
        # 检查登陆是否异常
        try:
            username = json.loads(request.COOKIES.get('username'))
        except:
            return None
        if username == request.session.get('username', ''):
            # 检查是否存在于数据库
            user = User.objects.filter(username=username)
            if user:
                # 检查用户是否为active
                if user[0].is_active:
                    return user[0]
                else:
                    logger.debug('用户被封禁')
                    return None
            else:
                logger.debug('未检索到用户')
                return None
        else:
            logger.debug('COOKIE中未含有username或username与session中的值不符')
            return None
    else:
        logger.debug('过期的Session')
        return None
