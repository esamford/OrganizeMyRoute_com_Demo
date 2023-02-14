import datetime
import re
import secrets
from hashlib import sha256

import jwt
from django.db.models import QuerySet
from ipware import get_client_ip

from django.db import models
from rest_framework.authentication import get_authorization_header


class HashedIP(models.Model):
    # This string is used to anonymize client IP addresses. Each IP address is concatenated alongside this random,
    # unknown string before being hashed. In case of a data breach, hackers should not be able to brute-force hashed
    # IP addresses to get he original unless they knew what this value was -- which isn't possible because it's only
    # stored in memory and refreshes at each server restart.
    __CONST_RANDOM_HASH_STR = str(secrets.token_urlsafe(128))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hashed_ip = models.CharField(max_length=100, unique=True)

    @classmethod
    def get_hashed_ip_prefix(cls) -> str:
        return "HASHED_IP-&$!-"

    @classmethod
    def get_hashed_ip(cls, ip_string: str) -> str:
        hashed_prefix = cls.get_hashed_ip_prefix()
        if ip_string.startswith(hashed_prefix):
            return ip_string
        else:
            hashed_ip = hashed_prefix + \
                        sha256(
                            "{} {}".format(
                                ip_string,
                                cls.__CONST_RANDOM_HASH_STR  # Add a random, unknown string to prevent reverse lookups.
                            ).encode('utf-8')
                        ).hexdigest()
            return hashed_ip

    def clean(self):
        self.hashed_ip = self.get_hashed_ip(self.hashed_ip)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_from_request(cls, request):
        client_ip, _ = get_client_ip(request)
        if client_ip is None:
            raise Exception("Could not retrieve client IP address from request.")
        else:
            ip_hash = cls.get_hashed_ip(client_ip)
            found_ip = HashedIP.objects.filter(hashed_ip=ip_hash).first()

            if found_ip is None:
                found_ip = HashedIP(hashed_ip=client_ip)
                found_ip.save()

            return found_ip

    def __str__(self):
        self.clean()
        return str(self.hashed_ip)


class TrackedAction(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hashed_ip = models.ForeignKey(HashedIP, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=200)

    @staticmethod
    def create_action_with_request_and_type(request, action_type: str) -> QuerySet:
        found_hashed_ip = HashedIP.get_or_create_from_request(request)
        action = TrackedAction(hashed_ip=found_hashed_ip, action_type=action_type)
        action.save()
        return TrackedAction.objects.filter(id=action.id)

    @staticmethod
    def get_actions_within_last_x_minutes(request, action_type: str, num_minutes: int) -> QuerySet:
        found_hashed_ip = HashedIP.get_or_create_from_request(request)
        lower_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=num_minutes)

        found_actions = TrackedAction.objects.filter(
            hashed_ip=found_hashed_ip, action_type=action_type, created_at__gte=lower_time
        ).order_by('created_at')
        return found_actions


class JWTBlacklist(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    jti = models.CharField(max_length=200, unique=True)

    @staticmethod
    def __get_jwt_from_request(request) -> str:
        token = get_authorization_header(request).decode('utf-8')
        jwt_list = re.findall(r"[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+", token)
        assert len(jwt_list) > 0
        return str(jwt_list[0])

    @staticmethod
    def __get_jti_from_jwt(jwt_str: str) -> str:
        payload_dict = jwt.decode(jwt_str, options={"verify_signature": False})
        return payload_dict['jti']

    @classmethod
    def get_by_jwt(cls, jwt_str: str) -> QuerySet:
        jti_str = cls.__get_jti_from_jwt(jwt_str)
        return JWTBlacklist.objects.filter(jti=jti_str)

    @classmethod
    def get_by_request(cls, request) -> QuerySet:
        jwt_str = cls.__get_jwt_from_request(request)
        return cls.get_by_jwt(jwt_str)

    @classmethod
    def create_by_jwt(cls, jwt_str) -> QuerySet:
        if cls.get_by_jwt(jwt_str).first() is None:
            jti_str = cls.__get_jti_from_jwt(jwt_str)
            blacklisted_token = JWTBlacklist(jti=jti_str)
            blacklisted_token.save()
        result = cls.get_by_jwt(jwt_str)
        print(result)
        return result

    @classmethod
    def create_by_request(cls, request) -> QuerySet:
        jwt_str = cls.__get_jwt_from_request(request)
        result = cls.create_by_jwt(jwt_str)
        print(result)
        return result

    @classmethod
    def check_if_jwt_is_blacklisted_with_request(cls, request) -> bool:
        print("\n\n\n", cls.get_by_request(request), "\n\n\n")
        return len(cls.get_by_request(request)) > 0


