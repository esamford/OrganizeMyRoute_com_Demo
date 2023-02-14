import random
import time
from abc import ABC

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView


random.seed(time.time())


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['unique_string'] = "".join(
            random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") for _ in range(25)
        )

        return token


def get_user_jwt(user):
    # refresh = RefreshToken.for_user(user)
    token = MyTokenObtainPairSerializer.get_token(user)
    return {
        'refresh': str(token),
        'access': str(token.access_token),
    }
