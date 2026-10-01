from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class UserSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    posts_count = serializers.IntegerField(source="reels.count", read_only=True)
    avatar = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ["id", "username", "email", "avatar", "bio", "location", "followers_count", "following_count", "posts_count"]
        read_only_fields = ["id", "followers_count", "following_count", "posts_count"]
    def get_avatar(self, obj):
        return self.context["request"].build_absolute_uri(obj.avatar.url) if obj.avatar else None

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "access", "refresh"]
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        token = RefreshToken.for_user(user)
        user.access_token = str(token.access_token)
        user.refresh_token = str(token)
        return user
    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["access"] = instance.access_token
        result["refresh"] = instance.refresh_token
        result["user"] = UserSerializer(instance, context=self.context).data
        return result

class EmailTokenSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD
    def validate(self, attrs):
        identifier = attrs.get(self.username_field)
        user = User.objects.filter(email__iexact=identifier).first() if "@" in str(identifier) else None
        if user:
            attrs[self.username_field] = user.username
        return super().validate(attrs)