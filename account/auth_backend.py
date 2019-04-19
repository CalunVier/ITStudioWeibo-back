# from django.contrib.auth import get_user_model
# from .models import User
#
#
# class AuthBackEnd(object):
#     def authenticate(self, request, user_key=None, password=None):
#         try:
#             user = User.objects.get(email=user_key)
#         except User.DoesNotExist:
#             return None
#
#         if user.password == password:
#             return user
#         else:
#             return None
#
#     def get_user(self, user_key):
#         try:
#             return User.objects.get(email=user_key)
#         except User.DoesNotExist:
#             return None
#
#
# class SettingsBackend(object):
#     pass
#
# from django.contrib.auth.backends import ModelBackend
# from django.contrib.auth import authenticate, login