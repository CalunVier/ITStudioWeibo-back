from django.shortcuts import render
from django.http import HttpResponse
from ITstudioWeibo.general import check_verify_email
from .models import UserWeiboInfo, User
from .account_lib import check_password_verify, to_login, check_email_verify, to_register, sign_password_md5, check_logged
import logging
import json
import random
import string


logger = logging.getLogger('django.account.view')


# 注册
def register(request):
    # TODO:添加随机的nick
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
            if post_body_json and \
                    'email' in post_body_json and \
                    'password' in post_body_json and \
                    'verify_code' in post_body_json:
                logger.info('POST数据完整')

                # 检查验证码是否正确
                # TODO: 验证码系统待添加
                if True:
                    # logger.debug('验证码检查通过')
                    if not post_body_json['email']:
                        logger.info('空email')
                        return HttpResponse("{\"status\":10}", status=400)  # 无效的email
                    if not post_body_json['password']:
                        logger.info('空密码')
                        return HttpResponse("{\"status\":5}", status=400)

                    if not check_password_verify(post_body_json['password']):
                        logger.info('密码不合法')
                        return HttpResponse("{\"status\":5}", status=403)
                    if not check_email_verify(post_body_json['email']):
                        logger.info('邮箱格式不合法')
                        return HttpResponse("{\"status\":10}", status=400)

                    # 写入数据库
                    logger.info('将注册信息写入数据库')
                    result, user = to_register(post_body_json['user_id'],
                                               sign_password_md5(post_body_json['password']), post_body_json['email'])
                    # 返回结果
                    if not result:
                        # 注册成功
                        logger.info('返回注册成功')
                        response = HttpResponse("{\"status\":0}", status=200)
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
                        return HttpResponse("{\"status\":" + str(result) + "}}", status=406)

                # else:
                #     # 验证码错误，返回状态码
                #     logger.info('验证码错误')
                #     return HttpResponse("{\"result\":3}", status=403)
            else:
                # post数据不完整，返回状态码
                logger.info('注册数据不完整')
                return HttpResponse("{\"status\":8}", status=400)
        else:
            # 非post请求，404
            logger.info('收到非POST请求')
            return HttpResponse(status=404)
    except Exception:
        logger.error('出现未知错误')
        return HttpResponse("{\"status\":6}", status=500)


# 登陆
def login(request):
    try:
        if request.method == 'POST':
            logger.info("收到POST请求")

            # 判断是否登陆
            if 'user_id' not in request.session:
                # 读取post的内容
                # try:    # 使用try防止乱推出现异常崩溃
                #     post_body_json = json.loads(request.body)
                #     logger.info('解析json成功')
                # except json.JSONDecodeError:
                #     logger.error('json解析错误:' + str(request.body))
                #     post_body_json = {}
                #     return HttpResponse("{\"result\":9}", status=400)
                # except Exception:
                #     logger.error('json解析出现未知错误:' + str(request.body))
                #     post_body_json = {}
                #     return HttpResponse("{\"result\":9}", status=400)

                # 为兼容旧代码，构建post_body_json
                post_body_json = {
                    'user_key': request.POST.get('email', ''),
                    'password': request.POST.get('password', '')
                }

                # post判断post_body是否存在所需内容
                # if post_body_json and "user_key" in post_body_json and \
                #         'password' in post_body_json:
                #     logger.debug('post数据完整')

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
                        if sign_password_md5(post_body_json['password']) == user.password:
                            response = HttpResponse("{\"status\":0}", status=200)
                            to_login(request, response, user)
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
                # else:
                #     logger.info('post_body内容缺失')
                #     return HttpResponse("{\"result\":8}", status=400)
            else:
                logger.info('已登录，请勿重复登陆')
                return HttpResponse("{\"status\":5}", status=403)
        else:
            # 非POST不接，返回404
            logger.info('app_login收到非post请求')
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


# 获取用户主页信息
def get_user_home(request):
    if request.method == 'GET':
        if check_logged(request):
            try:
                user = User.objects.select_related('userweiboinfo').get(username=request.COOKIES.get('username'))
            except:
                return HttpResponse(status=500)
            response_data = {
                "user_head": user.head.url,
                "user_name": user.nick,
                "user_info": user.userweiboinfo.intro,
                "follow_num": user.userweiboinfo.follow_num,
                "weibo_num": user.userweiboinfo.weibo_num,
                "fans_num": user.userweiboinfo.fans_num
            }
            try:
                response_data = json.dumps(response_data)
            except:
                return HttpResponse(status=500)
            # 正常返回结果
            return HttpResponse(response_data)
        else:
            # 要求登陆
            # todo 查询相关http代码
            return HttpResponse(status=400)
    else:
        # 非GET不接
        return HttpResponse(status=404)
