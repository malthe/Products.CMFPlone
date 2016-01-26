Notes about getting rid of CMFQuickInstallerTool
================================================


Changes needed in add-ons
-------------------------

When add-ons use the CMFQuickInstallerTool, what should they change?
This is also true for core packages that have not been handled yet.


Extensions/install.py
~~~~~~~~~~~~~~~~~~~~~

When your add-on has an Extensions/install.py, you must switch to a GenericSetup profile.


Uninstall
~~~~~~~~~

An uninstall profile is not required, but it is highly recommended.
The CMFQuickInstallerTool used to do an automatic partial cleanup,
for example remove added skins and css resources.
This was always only partial, so you could not rely on it to fully cleanup the site.
This cleanup is no longer done.
It is best practice to create an uninstall profile for all your packages.
When there is no uninstall profile, the add-ons control panel will give a warning.
An uninstall profile is a profile that is registered with the name ``uninstall``.
For an example, see https://github.com/plone/plone.app.multilingual/tree/master/src/plone/app/multilingual/profiles/uninstall


portal_quickinstaller
~~~~~~~~~~~~~~~~~~~~~

Old code::

    qi = getattr(self.context, 'portal_quickinstaller')

or::

    qi = getToolByName(self.context, name='portal_quickinstaller')

or::

    qi = getUtility(IQuickInstallerTool)

New code::

    from Products.CMFPlone.utils import get_installer
    qi = get_installer(self.context, self.request)

or if you do not have a request::

    qi = get_installer(self.context)

Alternative code::

    qi = getMultiAdapter((self.context, self.request), name='installer')

If you need it in a page template::

    tal:define="qi context/@@installer"

Warning:
since the code really does different things than before,
the method names were changed
and they may accept less arguments or differently named arguments.

isProductInstalled
~~~~~~~~~~~~~~~~~~

Old code::

    qi.isProductInstalled(product_name)

New code::

    qi.is_product_installed(product_name)


getLatestUpgradeStep
~~~~~~~~~~~~~~~~~~~~

Old code::

    qi.getLatestUpgradeStep(profile_id)

New code::

    qi.get_latest_upgrade_step(profile_id)


isDevelopmentMode
~~~~~~~~~~~~~~~~~

This was a helper method that had got nothing to with the quick installer.

Old code::

    qi = getToolByName(aq_inner(self.context), 'portal_quickinstaller')
    return qi.isDevelopmentMode()

New code::

    from Globals import DevelopmentMode
    return bool(DevelopmentMode)

The new code works already (Plone 4.3, 5.0).


TODO in Plone 6
---------------

We do want to break everything in Plone 5.x.
So CMFQuickInstallerTool must remain,
even when not used in core.
But in Plone 6 we intend to remove it.
Let's not mention everything in this document,
as we can search for use of portal_quickinstaller,
but only list a few important places.

In Products.CMFPlone:

- Remove portal_quickinstaller from required tools in
  profiles/default/toolset.xml

- Remove tests/testQuickInstallerTool.py

- Remove QuickInstallerTool.py
