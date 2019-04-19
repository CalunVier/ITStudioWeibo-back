from django.conf.urls import url
from django.contrib import admin
from .views import *

urlpatterns = [
    url(r'^register', register),
    url('^login', login),
    url('^logout', logout),
]