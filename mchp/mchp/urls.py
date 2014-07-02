from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^profile/', include('user_profile.urls')),
    url(r'^school/', include('schedule.urls')),
    url(r'^get-email/', include('user_profile.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^accounts/', include('user_profile.urls')),
    url(r'^search/', include('haystack.urls')),
    url(r'^☭', 'landing.views.party'),
    url(r'^$', include('landing.urls')),
)
