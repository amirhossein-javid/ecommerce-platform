from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.core.exceptions import FieldDoesNotExist
from django.db import models

TEHRAN_TIME_ZONE = ZoneInfo("Asia/Tehran")

APP_LABELS = {
    "accounts": "حساب‌ها و مشتریان",
    "auth": "هویت و مجوزها",
    "orders": "سفارش‌ها و ارسال",
    "payments": "پرداخت‌ها",
    "products": "کاتالوگ و دیدگاه‌ها",
    "token_blacklist": "نشست‌ها و توکن‌ها",
}

MODEL_LABELS = {
    ("accounts", "address"): ("نشانی", "نشانی‌ها"),
    ("accounts", "customerprofile"): ("پروفایل مشتری", "پروفایل‌های مشتریان"),
    ("accounts", "user"): ("کاربر", "کاربران"),
    ("auth", "group"): ("گروه", "گروه‌ها"),
    ("orders", "order"): ("سفارش", "سفارش‌ها"),
    ("orders", "orderitem"): ("قلم سفارش", "اقلام سفارش"),
    ("orders", "inventoryreservation"): ("رزرو موجودی", "رزروهای موجودی"),
    ("orders", "orderstatushistory"): (
        "سابقه وضعیت سفارش",
        "سوابق وضعیت سفارش",
    ),
    ("orders", "shipment"): ("مرسوله", "مرسوله‌ها"),
    ("payments", "balewebhookupdate"): (
        "رویداد وب‌هوک بله",
        "رویدادهای وب‌هوک بله",
    ),
    ("payments", "paymentattempt"): ("تلاش پرداخت", "تلاش‌های پرداخت"),
    ("products", "category"): ("دسته‌بندی", "دسته‌بندی‌ها"),
    ("products", "product"): ("محصول", "محصولات"),
    ("products", "productimage"): ("تصویر محصول", "تصاویر محصول"),
    ("products", "productreview"): ("دیدگاه محصول", "دیدگاه‌های محصولات"),
    ("products", "productreviewreply"): (
        "پاسخ رسمی دیدگاه",
        "پاسخ‌های رسمی دیدگاه‌ها",
    ),
    ("token_blacklist", "blacklistedtoken"): (
        "توکن مسدودشده",
        "توکن‌های مسدودشده",
    ),
    ("token_blacklist", "outstandingtoken"): (
        "توکن فعال",
        "توکن‌های فعال",
    ),
}

TEXT_LABELS = {
    "account status": "وضعیت حساب",
    "active": "فعال",
    "approved": "تأییدشده",
    "archived": "بایگانی‌شده",
    "actor type": "نوع عامل",
    "actor user": "کاربر عامل",
    "address": "نشانی",
    "alt text": "متن جایگزین تصویر",
    "amount": "مبلغ",
    "any attention required": "همه موارد نیازمند رسیدگی",
    "available stock": "موجودی قابل‌فروش",
    "awaiting delivery confirmation": "در انتظار تأیید تحویل",
    "awaiting payment": "در انتظار پرداخت",
    "blacklisted at": "زمان مسدودسازی",
    "cancelled": "لغوشده",
    "cancelled at": "زمان لغو",
    "carrier": "حامل",
    "catalog": "کاتالوگ",
    "category": "دسته‌بندی",
    "city": "شهر",
    "comment": "متن دیدگاه",
    "completed": "تکمیل‌شده",
    "consumed": "مصرف‌شده",
    "created at": "زمان ایجاد",
    "currency": "واحد پول",
    "customer": "مشتری",
    "customer display name": "نام نمایشی مشتری",
    "customer email": "ایمیل مشتری",
    "customer profile": "پروفایل مشتری",
    "date joined": "زمان عضویت",
    "delivered": "تحویل‌شده",
    "delivered at": "زمان تحویل",
    "description": "توضیحات",
    "discount total": "مجموع تخفیف",
    "draft": "پیش‌نویس",
    "email": "ایمیل",
    "event type": "نوع رویداد",
    "expires at": "زمان انقضا",
    "expired": "منقضی‌شده",
    "failed": "ناموفق",
    "failed while order pending": "ناموفق در زمان انتظار سفارش",
    "failed; historical": "ناموفق؛ سابقه تاریخی",
    "first name": "نام",
    "from status": "وضعیت قبلی",
    "fulfillment state": "وضعیت تکمیل سفارش",
    "gateway": "درگاه",
    "gateway reference": "شناسه درگاه",
    "grand total": "مبلغ نهایی",
    "group": "گروه",
    "groups": "گروه‌ها",
    "id": "شناسه",
    "idempotency key": "کلید تکرارناپذیری",
    "image": "تصویر",
    "important dates": "تاریخ‌های مهم",
    "in stock": "دارای موجودی",
    "in transit": "در مسیر ارسال",
    "inconsistent with order": "ناسازگار با سفارش",
    "inventory": "موجودی",
    "invalid payment inventory": "موجودی نامعتبر پرداخت",
    "is active": "فعال",
    "is default": "پیش‌فرض",
    "is primary": "تصویر اصلی",
    "is staff": "عضو کارکنان",
    "is superuser": "مدیر کل",
    "jti": "شناسه توکن",
    "last login": "آخرین ورود",
    "last name": "نام خانوادگی",
    "line total": "مبلغ ردیف",
    "locally recoverable": "قابل بازیابی محلی",
    "metadata": "اطلاعات سیستمی",
    "name": "نام",
    "needs review: inconsistent with order": "نیازمند بررسی؛ ناسازگار با سفارش",
    "needs review: missing processing timestamp": (
        "نیازمند بررسی؛ زمان شروع پردازش ثبت نشده"
    ),
    "needs shipment details": "نیازمند اطلاعات مرسوله",
    "not required": "لازم نیست",
    "operational state": "وضعیت عملیاتی",
    "operator": "اپراتور",
    "operator attention": "نیاز به رسیدگی اپراتور",
    "order": "سفارش",
    "order status": "وضعیت سفارش",
    "paid": "پرداخت‌شده",
    "paid at": "زمان پرداخت",
    "parent": "دسته‌بندی والد",
    "password": "گذرواژه",
    "payment attempt": "تلاش پرداخت",
    "payment attempts": "تلاش‌های پرداخت",
    "payment inventory invalid": "موجودی پرداخت نامعتبر است",
    "payment url": "نشانی پرداخت",
    "payment window elapsed": "مهلت پرداخت پایان یافته",
    "payments": "پرداخت‌ها",
    "pending": "در انتظار",
    "pending payment": "در انتظار پرداخت",
    "pending; invalid payment inventory": "در انتظار؛ موجودی پرداخت نامعتبر",
    "pending; payment window elapsed": "در انتظار؛ مهلت پرداخت پایان یافته",
    "permissions": "مجوزها",
    "phone number": "شماره تلفن",
    "position": "جایگاه",
    "postal code": "کد پستی",
    "pre checkout transaction id": "شناسه تراکنش پیش از پرداخت",
    "pre-checkout": "پیش از پرداخت",
    "preview": "پیش‌نمایش",
    "price": "قیمت",
    "primary image": "تصویر اصلی",
    "processed": "پردازش‌شده",
    "processed at": "زمان پایان پردازش",
    "processing": "در حال پردازش",
    "processing at": "زمان شروع پردازش سفارش",
    "processing started at": "زمان شروع پردازش",
    "processing without claim timestamp": "در حال پردازش بدون زمان دریافت",
    "product": "محصول",
    "product name": "نام محصول",
    "provider transaction id": "شناسه تراکنش ارائه‌دهنده",
    "province": "استان",
    "quantity": "تعداد",
    "rating": "امتیاز",
    "ready to process": "آماده پردازش",
    "ready to ship": "آماده ارسال",
    "received at": "زمان دریافت",
    "recipient first name": "نام گیرنده",
    "recipient last name": "نام خانوادگی گیرنده",
    "recipient phone number": "شماره تلفن گیرنده",
    "refund required": "نیازمند بازپرداخت",
    "refund resolved at": "زمان انجام بازپرداخت",
    "refund resolved by": "ثبت‌کننده بازپرداخت",
    "refund status": "وضعیت بازپرداخت",
    "rejected": "ردشده",
    "released": "آزادشده",
    "required": "لازم",
    "resolved": "انجام‌شده",
    "review": "دیدگاه",
    "shipment details required": "نیازمند اطلاعات مرسوله",
    "shipped": "ارسال‌شده",
    "shipped at": "زمان ارسال",
    "shipping address": "نشانی ارسال",
    "shipping city": "شهر ارسال",
    "shipping postal code": "کد پستی ارسال",
    "shipping province": "استان ارسال",
    "shipping recipient first name": "نام گیرنده ارسال",
    "shipping recipient last name": "نام خانوادگی گیرنده ارسال",
    "shipping recipient phone number": "شماره تلفن گیرنده ارسال",
    "shipping title": "عنوان نشانی ارسال",
    "shipping total": "هزینه ارسال",
    "sku": "شناسه کالا",
    "slug": "نامک",
    "stale; locally recoverable": "متوقف‌شده؛ قابل بازیابی محلی",
    "status": "وضعیت",
    "stock quantity": "موجودی فیزیکی",
    "subtotal": "جمع جزء",
    "success": "موفق",
    "successful payment": "پرداخت موفق",
    "successful; refund required": "موفق؛ نیازمند بازپرداخت",
    "superuser status": "وضعیت مدیر کل",
    "system": "سامانه",
    "title": "عنوان",
    "to status": "وضعیت جدید",
    "token": "توکن",
    "tracking number": "کد رهگیری",
    "unit price": "قیمت واحد",
    "update id": "شناسه به‌روزرسانی",
    "updated at": "زمان به‌روزرسانی",
    "user": "کاربر",
    "user permissions": "مجوزهای کاربر",
}

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def translate_admin_text(value):
    text = str(value)
    return TEXT_LABELS.get(text.strip().casefold(), text)


def admin_model_label(opts, *, plural=False):
    if not hasattr(opts, "app_label"):
        model = getattr(opts, "model", None)
        opts = getattr(model, "_meta", opts)
    labels = MODEL_LABELS.get((opts.app_label, opts.model_name))
    if labels:
        return labels[1 if plural else 0]
    return str(opts.verbose_name_plural if plural else opts.verbose_name)


def localize_app_list(app_list):
    localized = []
    for app in app_list:
        app_copy = dict(app)
        app_copy["name"] = APP_LABELS.get(app["app_label"], app["name"])
        app_copy["models"] = []
        for model in app["models"]:
            model_copy = dict(model)
            key = (app["app_label"], model["object_name"].lower())
            if key in MODEL_LABELS:
                model_copy["name"] = MODEL_LABELS[key][1]
            app_copy["models"].append(model_copy)
        localized.append(app_copy)
    return localized


def gregorian_to_jalali(year, month, day):
    gregorian_month_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    year_offset = year - 1600
    month_offset = month - 1
    day_offset = day - 1
    gregorian_day_number = (
        365 * year_offset
        + (year_offset + 3) // 4
        - (year_offset + 99) // 100
        + (year_offset + 399) // 400
    )
    gregorian_day_number += sum(gregorian_month_days[:month_offset]) + day_offset
    if month_offset > 1 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        gregorian_day_number += 1

    jalali_day_number = gregorian_day_number - 79
    cycles, jalali_day_number = divmod(jalali_day_number, 12053)
    jalali_year = 979 + 33 * cycles + 4 * (jalali_day_number // 1461)
    jalali_day_number %= 1461
    if jalali_day_number >= 366:
        jalali_year += (jalali_day_number - 1) // 365
        jalali_day_number = (jalali_day_number - 1) % 365
    if jalali_day_number < 186:
        jalali_month = 1 + jalali_day_number // 31
        jalali_day = 1 + jalali_day_number % 31
    else:
        jalali_month = 7 + (jalali_day_number - 186) // 30
        jalali_day = 1 + (jalali_day_number - 186) % 30
    return jalali_year, jalali_month, jalali_day


def format_admin_temporal(value):
    if value in (None, ""):
        return "—"
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(TEHRAN_TIME_ZONE)
        jalali = gregorian_to_jalali(value.year, value.month, value.day)
        rendered = (
            f"{jalali[0]:04d}/{jalali[1]:02d}/{jalali[2]:02d}، "
            f"{value.hour:02d}:{value.minute:02d}"
        )
        return rendered.translate(PERSIAN_DIGITS)
    if isinstance(value, date):
        jalali = gregorian_to_jalali(value.year, value.month, value.day)
        return f"{jalali[0]:04d}/{jalali[1]:02d}/{jalali[2]:02d}".translate(
            PERSIAN_DIGITS
        )
    return value


def make_admin_list_display(model, field_name):
    try:
        model_field = model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None
    if not isinstance(model_field, (models.DateField, models.DateTimeField)):
        if not model_field.choices:
            return None

        def localized_choice(obj):
            return translate_admin_text(getattr(obj, f"get_{field_name}_display")())

        localized_choice.short_description = translate_admin_text(
            model_field.verbose_name
        )
        localized_choice.admin_order_field = field_name
        localized_choice.__name__ = f"localized_{field_name}"
        return localized_choice

    def localized_temporal(obj):
        return format_admin_temporal(getattr(obj, field_name))

    localized_temporal.short_description = translate_admin_text(
        model_field.verbose_name
    )
    localized_temporal.admin_order_field = field_name
    localized_temporal.__name__ = f"localized_{field_name}"
    return localized_temporal
