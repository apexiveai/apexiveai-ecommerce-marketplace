from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        BUYER = "BUYER", "Buyer"
        SELLER = "SELLER", "Seller"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.BUYER,
        db_index=True,
    )
    phone_number = models.CharField(max_length=30, blank=True)
    email_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)
        if self.pk:
            UserRole.objects.update_or_create(
                user=self,
                defaults={"role": self.role},
            )

    def __str__(self):
        return f"{self.username} ({self.role})"


class SellerProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SUSPENDED = "SUSPENDED", "Suspended"

    class SellerType(models.TextChoices):
        DEALER = "DEALER", "Dealer"
        PRIVATE_SELLER = "PRIVATE_SELLER", "Private seller"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="seller_profile",
    )
    store_name = models.CharField(max_length=150)
    store_slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, default="MM")
    business_address = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    seller_type = models.CharField(
        max_length=20,
        choices=SellerType.choices,
        default=SellerType.DEALER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seller_profiles"

    def __str__(self):
        return self.store_name


class UserRole(models.Model):
    class Role(models.TextChoices):
        BUYER = "BUYER", "Buyer"
        SELLER = "SELLER", "Seller"
        ADMIN = "ADMIN", "Admin"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="marketplace_role",
    )
    role = models.CharField(max_length=10, choices=Role.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_roles"

    def __str__(self):
        return f"{self.user}: {self.role}"


class BuyerProfile(models.Model):
    class BuyerType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual buyer"
        CORPORATE = "CORPORATE", "Corporate buyer"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="buyer_profile",
    )
    buyer_type = models.CharField(
        max_length=12,
        choices=BuyerType.choices,
        default=BuyerType.INDIVIDUAL,
    )
    company_name = models.CharField(max_length=180, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "buyer_profiles"

    def __str__(self):
        return self.company_name or self.user.get_full_name() or self.user.username


class SellerBusiness(models.Model):
    class BusinessType(models.TextChoices):
        CAR_SHOWROOM = "CAR_SHOWROOM", "Car showroom"
        AUTOMOTIVE_COMPANY = "AUTOMOTIVE_COMPANY", "Automotive company"
        AUTHORIZED_DEALER = "AUTHORIZED_DEALER", "Authorized dealer"

    seller = models.OneToOneField(
        SellerProfile,
        on_delete=models.CASCADE,
        related_name="business",
    )
    business_type = models.CharField(
        max_length=24,
        choices=BusinessType.choices,
        default=BusinessType.CAR_SHOWROOM,
    )
    legal_name = models.CharField(max_length=180, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seller_businesses"

    def __str__(self):
        return self.legal_name or self.seller.store_name
