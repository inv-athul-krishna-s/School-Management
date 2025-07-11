from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.conf import settings
from .models import User, Teacher, Student

class BaseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ("username", "email", "first_name", "last_name", "phone", "password")
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "username": {"required": False},
        }

    # allow same username on self‑update
    def validate_username(self, value):
        if self.instance:
            if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("A user with that username already exists.")
        else:
            if User.objects.filter(username=value).exists():
                raise serializers.ValidationError("A user with that username already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        # fallback default password if missing
        if not password:
            password = f"{validated_data['username']}123"
            print(f"[DEBUG] auto‑password for {validated_data['username']}: {password}")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class TeacherUserSerializer(BaseUserSerializer):
    def create(self, validated_data):
        validated_data["role"] = "teacher"
        return super().create(validated_data)

class StudentUserSerializer(BaseUserSerializer):
    def create(self, validated_data):
        validated_data["role"] = "student"
        return super().create(validated_data)

class TeacherSerializer(serializers.ModelSerializer):
    user = TeacherUserSerializer()

    class Meta:
        model  = Teacher
        fields = "__all__"

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = TeacherUserSerializer().create(user_data)
        return Teacher.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        sub=TeacherUserSerializer(instance=instance.user, data=user_data, partial=True)
        sub.is_valid(raise_exception=True)
        sub.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class StudentSerializer(serializers.ModelSerializer):
    user = StudentUserSerializer()

    class Meta:
        model  = Student
        fields = "__all__"

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user = StudentUserSerializer().create(user_data)
        return Student.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        sub=StudentUserSerializer(instance=instance.user, data=user_data, partial=True)
        sub.is_valid(raise_exception=True)
        sub.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        return data