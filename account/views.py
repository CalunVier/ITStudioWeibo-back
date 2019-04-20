from django.shortcuts import render
from django.http import HttpResponse
from ITstudioWeibo.general import check_verify_email
from .account_lib import *
import logging
import json
import random
import string


logger = logging.getLogger('django.account.view')


def register(request):
    try:
        if request.method == 'POST':
            logger.info('收到post请求')
            # 读取post的内容
            # 使用try防止乱推出现异常崩溃
            # try:
            #     post_body_json = json.loads(request.body)
            #     logger.debug('json解析成功')
            # except json.JSONDecodeError:
            #     post_body_json = {}
            #     logger.error('json解析失败，收到POST:' + str(request.body))
            #     return HttpResponse("{\"result\":9}", status=400)
            # except Exception:
            #     post_body_json = {}
            #     logger.error('json解析出现未知错误，收到POST:' + str(request.body))
            #     return HttpResponse("{\"result\":9}", status=400)

            post_body_json = {
                'email': request.POST.get('email', ''),
                'password': request.POST.get('password', ''),
                'verify_code': request.POST.get('verify_code', ''),
                'user_id': ''.join(random.sample(string.ascii_lowercase, 8))
            }

            # post判断post_body是否存在所需内容
            if post_body_json and \
                    'email' in post_body_json and \
                    'password' in post_body_json and \
                    'verify_code' in post_body_json:
                logger.info('POST数据完整')
                # 检查验证码是否正确
                # 此处需要更换为email格式的验证码
                if True:
                    logger.debug('验证码检查通过')
                    # 检查各项是否为空
                    # if not post_body_json['user_id']:
                    #     logger.info('空user_id')
                    #     return HttpResponse("{\"result\":7}", status=400)  # 无效的用户ID
                    if not post_body_json['email']:
                        logger.info('空email')
                        return HttpResponse("{\"result\":10}", status=400)  # 无效的email
                    if not post_body_json['password']:
                        logger.info('空密码')
                        return HttpResponse("{\"result\":5}", status=400)
                    # if not post_body_json['user_name']:
                    #     logger.info('空昵称')
                    #     return HttpResponse("{\"result\":4}", status=400)

                    # 用户名密码用户名等数据合法性检查
                    # if not check_user_id_verify(post_body_json['user_id']):
                    #     logger.info('用户名不合法')
                    #     return HttpResponse("{\"result\":7}", status=403)
                    if not check_password_verify(post_body_json['password']):
                        logger.info('密码不合法')
                        return HttpResponse("{\"result\":5}", status=403)
                    if not check_email_verify(post_body_json['email']):
                        logger.info('邮箱格式不合法')
                        return HttpResponse("{\"result\":10}", status=400)
                    # if not check_nickname_verify(post_body_json['user_name']):
                    #     logger.info('昵称不合法')
                    #     return HttpResponse("{\"result\":4}", status=403)

                    # 写入数据库
                    logger.info('将注册信息写入数据库')
                    result, user = to_register(post_body_json['user_id'],
                                               sign_password_md5(post_body_json['password']), post_body_json['email'])
                    # 返回结果
                    if not result:
                        # 注册成功
                        logger.info('返回注册成功')
                        response = HttpResponse("{\"result\":0}", status=200)
                        # 注册后自动登陆
                        try:
                            to_login(request, response, user)
                            logger.info('自动登陆完成')
                        except Exception:
                            logger.error('自动登陆出现异常')
                        return response
                    else:
                        # 注册失败返回状态码
                        logger.error('注册失败返回状态码')
                        return HttpResponse("{\"result\":" + str(result) + "}}", status=406)

                # else:
                #     # 验证码错误，返回状态码
                #     logger.info('验证码错误')
                #     return HttpResponse("{\"result\":3}", status=403)
            else:
                # post数据不完整，返回状态码
                logger.info('注册数据不完整')
                return HttpResponse("{\"result\":8}", status=400)
        else:
            # 非post请求，404
            logger.info('收到非POST请求')
            return HttpResponse(status=404)
    except Exception:
        logger.error('出现未知错误')
        return HttpResponse("{\"result\":6}", status=500)


def login(request):
    try:
        if request.method == 'POST':
            logger.info("收到POST请求")
            # 读取post的内容
            if 'user_id' not in request.session:
                # 使用try防止乱推出现异常崩溃
                try:
                    post_body_json = json.loads(request.body)
                    logger.info('解析json成功')
                except json.JSONDecodeError:
                    logger.error('json解析错误:' + str(request.body))
                    post_body_json = {}
                    return HttpResponse("{\"result\":9}", status=400)
                except Exception:
                    logger.error('json解析出现未知错误:' + str(request.body))
                    post_body_json = {}
                    return HttpResponse("{\"result\":9}", status=400)

                # post判断post_body是否存在所需内容
                if post_body_json and "user_key" in post_body_json and 'key_type' in post_body_json and \
                        'password' in post_body_json:
                    logger.debug('post数据完整')

                    # 检查各项是否为空
                    if not post_body_json['user_key'] or not post_body_json['key_type']:
                        # 无效的用户ID
                        logger.info('无效的用户索引')
                        return HttpResponse("{\"result\":1}", status=400)
                    if not post_body_json['password']:
                        # 无效的密码
                        logger.info('无效的密码')
                        return HttpResponse("{\"result\":2}", status=400)

                    # 查询用户，获取用户数据库对象
                    if post_body_json['key_type'] == 'user_id':
                        user = User.objects.filter(username=post_body_json['user_key'])
                    elif post_body_json['key_type'] == 'email':
                        user = User.objects.filter(email=post_body_json['user_key'])
                    else:
                        logger.info('无效的用户索引')
                        return HttpResponse("{\"result\":1}", status=400)
                    # 检索到用户
                    if user:
                        logger.info('检索到用户'+post_body_json['user_key'])
                        user = user[0]
                        if user.is_active:
                            if sign_password_md5(post_body_json['password']) == user.password:
                                response = HttpResponse("{\"result\":0}", status=200)
                                to_login(request, response, user)
                                # 登录成功
                                return response
                            else:
                                # 密码错误
                                logger.info('密码错误')
                                return HttpResponse("{\"result\":2}", status=200)
                        else:
                            # active为Flase，账户被封禁
                            logger.info('账户被封禁')
                            return HttpResponse("{\"result\":4}", status=403)
                    else:
                        # 找不到用户，无效用户ID
                        logger.info('找不到用户：' + post_body_json['user_key'])
                        return HttpResponse("{\"result\":1}", status=404)
                else:
                    logger.info('post_body内容缺失')
                    return HttpResponse("{\"result\":8}", status=400)
            else:
                logger.info('已登录，请勿重复登陆')
                return HttpResponse("{\"result\":5}", status=403)
        else:
            # 非POST不接，返回404
            logger.info('app_login收到非post请求')
            return HttpResponse(status=404)
    except Exception:
        logger.error('出现未知错误')
        return HttpResponse("{\"result\":6}", status=500)


# 登出
def logout(request):
    if request.method == 'GET':
        if 'user_id' in request.session:
            logger.info(request.session['user_id']+'退出登录')
            request.session.flush()
            response = HttpResponse("{\"status\":\"ok\"}")
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


def get_user_info(request):
    user = User.objects.get(id = 1)
    return HttpResponse(user.head.url)