from django.conf.urls import url
from .views import *


urlpatterns = [
    url('^get_items_list', get_item_list),
    url(r"^delete_weibo", delete_weibo),
    url(r"^create_weibo", create_weibo),
    url(r"^upload_img", upload_image),
    url(r"^collect_weibo", collect_weibo)
]