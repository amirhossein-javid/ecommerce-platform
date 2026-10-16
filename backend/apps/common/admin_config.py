from django.contrib.admin.apps import AdminConfig


class NaghshAdminConfig(AdminConfig):
    default_site = "apps.common.admin_site.NaghshAdminSite"
