from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

from ajax_select import urls as ajax_select_urls
from captcha import urls as captcha_urls
from registration.backends.default import urls as registration_urls
from registration.backends.default.views import RegistrationView

from enhydris import urls as enhydris_urls
from enhydris.api import urls as enhydris_api_urls
from enhydris.forms import RegistrationForm
from enhydris.views import ProfileDetailView, ProfileEditView

admin.autodiscover()

urlpatterns = [
    url(r"^accounts/", include(registration_urls)),
    url(r"^profile/$", ProfileDetailView.as_view(), name="current_user_profile"),
    url(r"^profile/edit/$", ProfileEditView.as_view(), name="profile_edit"),
    url(
        r"^profile/(?P<slug>[^/]+)/$",
        ProfileDetailView.as_view(),
        name="profile_detail",
    ),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^ajax/", include(ajax_select_urls)),
    url(r"^api/", include(enhydris_api_urls)),
    url(r"^captcha/", include(captcha_urls)),
    url(r"", include(enhydris_urls)),
]

if getattr(settings, "REGISTRATION_OPEN", True):
    urlpatterns.insert(
        0,
        url(
            r"^accounts/register/$",
            RegistrationView.as_view(form_class=RegistrationForm),
            name="registration_register",
        ),
    )
