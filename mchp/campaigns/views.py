from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from .models import CampaignSubscriber
from .utils import beacon


OPEN_BEACON = beacon()

def campaign_click(request, uuid):
    """ Subscriber clicked through from an e-mail.

    """
    subscriber = get_object_or_404(CampaignSubscriber, uuid=uuid)
    subscriber.clicked = timezone.now()
    subscriber.save(update_fields=['clicked'])
    url = request.GET.get('next', 'landing_page')
    return redirect(url)


def campaign_open(request, uuid):
    """ Subscriber opened an e-mail.

    """
    subscriber = get_object_or_404(CampaignSubscriber, uuid=uuid)
    subscriber.opened = timezone.now()
    subscriber.save(update_fields=['opened'])
    return HttpResponse(OPEN_BEACON, content_type="image/png")


def campaign_unsubscribe(request, uuid):
    """ Subscriber unsubscribed from an e-mail.

    """
    subscriber = get_object_or_404(CampaignSubscriber, uuid=uuid)
    subscriber.unsubscribed = timezone.now()
    subscriber.save(update_fields=['unsubscribed'])
    return HttpResponse('You have been unsubscribed successfully.')
