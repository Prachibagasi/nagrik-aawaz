import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError("Phone number is required.")
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("citizen", "Citizen"),
        ("officer", "Field Officer"),
        ("admin", "Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=15, unique=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="citizen")

    preferred_language = models.CharField(
        max_length=5,
        default="hi",
        help_text="BCP-47 language code (hi, en, ta, te, …)",
    )
    ward = models.CharField(max_length=100, blank=True, help_text="Ward/zone assigned (officer)")
    department = models.CharField(max_length=100, blank=True, help_text="Government department (officer)")

    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    fcm_token = models.TextField(blank=True, help_text="Firebase Cloud Messaging device token")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name or self.phone} ({self.role})"

    @property
    def is_citizen(self):
        return self.role == "citizen"

    @property
    def is_officer(self):
        return self.role == "officer"

    @property
    def is_admin(self):
        return self.role == "admin"


class OTPVerification(models.Model):
    """One-time password for phone verification."""

    phone = models.CharField(max_length=15, db_index=True)
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_otp"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.phone}"
