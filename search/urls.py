
# Imports ###########################################################

from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from views.search import SearchAPIView


# URLs ##############################################################

urlpatterns = patterns('',
    url(r'^api/v1/search$', SearchAPIView.as_view(), name=u'api_search'),
    url(r'^$', RedirectView.as_view(url=u'/static/index.html')),
)
