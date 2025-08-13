# core/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes, smart_str


from .models import (
    User, Teacher, Student,
    Exam, Question, Option, StudentExam,
    Message, Chat,
)


#  USER / AUTH SERIALIZERS

class BaseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ("id","username", "email", "first_name", "last_name", "phone", "password")
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "username": {"required": False},
        }

    def validate_username(self, value):
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None) or f"{validated_data['username']}123"
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
        sub = TeacherUserSerializer(instance=instance.user, data=user_data, partial=True)
        sub.is_valid(raise_exception=True)
        sub.save()
        return super().update(instance, validated_data)
    



class StudentSerializer(serializers.ModelSerializer):
    user = StudentUserSerializer()
    assigned_teacher = serializers.SerializerMethodField()
    

    class Meta:
        model  = Student
        fields = "__all__"

    def get_assigned_teacher(self, obj):
        if obj.assigned_teacher:
            return {
                "id": obj.assigned_teacher.id,
                "name": obj.assigned_teacher.user.get_full_name()
            }
        return None

    def create(self, validated_data):
        request = self.context.get("request")
        user_data = validated_data.pop("user")
        user = StudentUserSerializer().create(user_data)

        # Automatically assign teacher if creator is a teacher
        if request and request.user.role == "teacher":
            teacher = getattr(request.user, "teacher", None)
            if teacher:
                validated_data["assigned_teacher"] = teacher

        return Student.objects.create(user=user, **validated_data)
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        sub = StudentUserSerializer(instance=instance.user, data=user_data, partial=True)
        sub.is_valid(raise_exception=True)
        sub.save()
        return super().update(instance, validated_data)


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


#  EXAM / QUESTION / OPTION SERIALIZERS
class OptionInputSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Option
        fields = ["text", "is_correct"]


class QuestionInputSerializer(serializers.ModelSerializer):
    options = OptionInputSerializer(many=True, write_only=True)

    class Meta:
        model  = Question
        fields = ["text", "options"]


# -- READ‑ONLY (output) serializers --
class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Option
        fields = ["id", "text"]        # hide is_correct from students


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model  = Question
        fields = ["id", "text", "options"]


class ExamReadSerializer(serializers.ModelSerializer):
    questions    = QuestionSerializer(many=True, read_only=True)
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)

    class Meta:
        model  = Exam
        fields = ["id", "title", "description", "teacher_name","target_class",
                  "start_time", "duration_min", "end_time", "questions"]
    def get_end_time(self, obj):
        return obj.end_time


class ExamCreateSerializer(serializers.ModelSerializer):
    """Used for POST/PUT; expects nested questions with options."""
    questions = QuestionInputSerializer(many=True, write_only=True)

    class Meta:
        model  = Exam
        fields = ["title", "description", "teacher","target_class",
                  "start_time", "duration_min", "questions"]

    def validate(self, data):
        if not data.get("questions"):
            raise serializers.ValidationError("At least one question required.")
        for q in data["questions"]:
            if not q.get("options"):
                raise serializers.ValidationError("Each question needs options.")
        return data

    def create(self, validated_data):
        q_data = validated_data.pop("questions")
        exam = Exam.objects.create(**validated_data)
        for q in q_data:
            opts = q.pop("options")
            question = Question.objects.create(exam=exam, **q)
            for opt in opts:
                Option.objects.create(question=question, **opt)
        return exam
    def update(self, instance, validated_data):
        q_data = validated_data.pop("questions", [])
    
    # Update basic exam fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

    # Clear old questions and options
        instance.questions.all().delete()

    # Recreate questions and options
        for q in q_data:
            opts = q.pop("options")
            question = Question.objects.create(exam=instance, **q)
            for opt in opts:
                Option.objects.create(question=question, **opt)

        return instance


#  STUDENT SUBMISSION & RESULTS

class AnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    option_id   = serializers.IntegerField()


class SubmitExamSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True)


class StudentExamSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name")

    class Meta:
        model  = StudentExam
        fields = ["id", "student_name", "score", "started_at", "finished_at"]



#  PASSWORD‑RESET SERIALIZERS  

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("No user with this e‑mail.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid          = serializers.CharField()
    token        = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        try:
            uid  = smart_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({"uid": "Invalid UID"})

        if not PasswordResetTokenGenerator().check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired token"})

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        
#chat message


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "chat", "sender", "sender_username", "content", "timestamp", "read"]


class ChatSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    last_message = serializers.SerializerMethodField()
    class Meta:
        model = Chat
        fields = ["id", "participants", "created_by_username", "last_message"]
    def get_last_message(self, obj):
        msg = obj.messages.order_by("-timestamp").first()
        return MessageSerializer(msg).data if msg else None

