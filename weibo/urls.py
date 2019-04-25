from django.conf.urls import url
from .views import *


urlpatterns = [
    url('^get_items_list', get_item_list)
]