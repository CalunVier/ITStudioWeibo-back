from django.conf.urls import url
from .views import *


urlpatterns = [
    url('^get_items_list', get_item_list),
    url(r"^delete_weibo", delete_weibo),
    url(r"^create_weibo", create_weibo),
    url(r"^upload_img", upload_image),
    url(r"^collect_weibo", collect_weibo),
    url(r"^info", get_weibo_info),
    url(r"^create_comment", comment_weibo),
    url(r"^like", change_like_status),
    url(r"^delete_comment", delete_comment),
    url(r"^comments_list", comment_like_list),
    url(r'^like_list', liker_list),
    url(r'^change_notice_read', change_notice_read),
    url(r'^notice_list', get_notice_list),
    url(r'^search_all', search_all),
    url(r'^search_weibo', search_weibo),
    url(r'^search_user', search_user)
]
