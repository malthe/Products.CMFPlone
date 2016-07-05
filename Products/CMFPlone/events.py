from zope.interface import implementer
from zope.component.interfaces import ObjectEvent

from Products.CMFCore.utils import getToolByName

from interfaces import ISiteManagerCreatedEvent
from interfaces import IReorderedEvent


@implementer(ISiteManagerCreatedEvent)
class SiteManagerCreatedEvent(ObjectEvent):

    pass


@implementer(IReorderedEvent)
class ReorderedEvent(ObjectEvent):
    pass


def profileImportedEventHandler(event):
    """
    When a profile is imported with the keyword "latest", it needs to
    be reconfigured with the actual number.
    """
    profile_id = event.profile_id
    if profile_id is None:
        return
    profile_id = profile_id.replace('profile-', '')
    gs = event.tool
    qi = getToolByName(gs, 'portal_quickinstaller', None)
    if qi is None:
        # CMF-only site, or a test run.
        return
    installed_version = gs.getLastVersionForProfile(profile_id)
    if installed_version == (u'latest',):
        actual_version = qi.getLatestUpgradeStep(profile_id)
        gs.setLastVersionForProfile(profile_id, actual_version)


def removeBase(event):
    """ Make Zope not to inject a <base> tag into the returned HTML
    https://dev.plone.org/ticket/13705
    """
    event.request.response.base = None
