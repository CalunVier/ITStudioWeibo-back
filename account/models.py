from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    head = models.ImageField(verbose_name=u'头像', default='default/default_head_img.jpg', upload_to='upload/%Y/%m')


    class Meta:
        indexes = [
            models.Index(fields=['email'])
        ]