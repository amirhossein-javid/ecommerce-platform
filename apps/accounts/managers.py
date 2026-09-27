from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Create users whose email address is their login identifier."""

    @classmethod
    def normalize_email(cls, email):
        """Return the canonical, lowercase representation used for login."""
        if not email:
            return ""
        return super().normalize_email(email.strip()).lower()

    def _create_user(self, email, password, **extra_fields):
        if not email or not email.strip():
            raise ValueError("The email address must be provided.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, email):
        return self.get(email=self.normalize_email(email))

    async def aget_by_natural_key(self, email):
        return await self.aget(email=self.normalize_email(email))

    def create_user(self, email, password=None, **extra_fields):
        if extra_fields.get("is_staff"):
            raise ValueError("A regular user cannot have is_staff=True.")
        if extra_fields.get("is_superuser"):
            raise ValueError("A regular user cannot have is_superuser=True.")

        extra_fields["is_staff"] = False
        extra_fields["is_superuser"] = False
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        if not password:
            raise ValueError("A superuser must have a password.")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        if extra_fields.get("is_active") is not True:
            raise ValueError("A superuser must have is_active=True.")

        return self._create_user(email, password, **extra_fields)
