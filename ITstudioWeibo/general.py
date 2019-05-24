from django.core.mail import send_mail
from django.core.cache import cache
from django.http import HttpResponse
from account.account_lib import check_email_verify
import random
import time
import _thread
import logging

logger = logging.getLogger('my_logger.general')


def check_email_verify_code_not_right(verify_id, verify_code, use):
    vc = cache.get('email_verify_'+verify_id, {})
    logger.debug(vc)
    if vc:
        if verify_code == vc.get('code', '') and use == vc.get('use', ''):
            return 0
        else:
            logger.debug('验证码错误,key:'+verify_id+'提交的验证码：'+verify_code+'缓存中的验证码：'+vc.get('code', '')+'提交的use:'+use+'缓存中的use:'+vc.get('use', ''))
            return 1
    else:
        return 2


def to_send_email_verify_code(to_email, use):
    try:
        # 生成验证码
        code = str(random.randint(100000, 999999))
        logger.debug("验证码生成")
        # 发送邮件部分
        send_mail(
            'ITStudio 微博 验证码',
            '您的验证码为：'+code+",验证码在60分钟内有效（请勿回复）",
            'itstudiomtimea@163.com',
            [to_email],
            fail_silently=False,
        )
        logger.debug('邮件发送成功')
        logger.debug('写入缓存')
        cache.set('email_verify_'+to_email, {'sent_time': time.time(), 'code': code, 'use': use}, 3600)
    except Exception as e:
        logger.error(str(e))
        logger.error('出现异常,发送邮件到:%s失败,use:%s' % (to_email, use))


def i_get_email_verify_code(request):
    if request.method == 'GET':
        logger.debug('收到GET请求')
        email = request.GET.get('email', '')
        use = request.GET.get('use', '')
        # 检查邮箱是否为空
        if check_email_verify(email):

            # 检查该邮箱是否存在于缓存
            c = cache.get(email)
            if c:
                if time.time() - c['sent_time'] < 60:
                    return HttpResponse("{\"status\":\"too_fast\"}")

            # 满足条件发送邮件
            _thread.start_new_thread(to_send_email_verify_code, (email, use,))
            logger.debug("创建新线程发送邮件")
            return HttpResponse("{\"id\":\""+email+"\",\"wait\":60,\"status\":\"ok\"}")
        else:
            # 邮箱不合法
            logger.info("邮箱不合法:%s" % email)
            return HttpResponse("{\"status\":\"invalid_email\"}", status=412)
    else:
        logger.info('收到非GET请求')
        return HttpResponse(status=404)


def get_pages_info(request):
    try:
        page = int(request.GET.get("page", 1))
    except:
        page = 1
    try:
        num = int(request.GET.get("num", 10))
    except:
        num = 10
    return page, num
