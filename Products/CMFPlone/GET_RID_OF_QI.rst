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


Products namespace
~~~~~~~~~~~~~~~~~~

There used to be special handling for the Products namespace.
Not anymore.

Old code::

    qi.installProduct('CMFPlacefulWorkflow')

New code::

    qi.install_product('Products.CMFPlacefulWorkflow')

TODO: check what happens with Products that register their profile in
Python code instead of zcml.  It might be needed for that.


isProductInstalled
~~~~~~~~~~~~~~~~~~

Old code::

    qi.isProductInstalled(product_name)

New code::

    qi.is_product_installed(product_name)


installProduct
~~~~~~~~~~~~~~

Old code::

    qi.installProduct(product_name)

New code::

    qi.install_product(product_name)

Note that no keyword arguments are accepted.
We might keep ``omit_snapshots`` and ``blacklisted_steps`` if we really want.


installProducts
~~~~~~~~~~~~~~~

This was removed.
Iterate over a list of products instead.


uninstallProduct
~~~~~~~~~~~~~~~~

Old code::

    qi.uninstallProduct(product_name)

New code::

    qi.uninstall_product(product_name)


uninstallProducts
~~~~~~~~~~~~~~~~~

This was removed.
Iterate over a list of products instead.


reinstallProducts
~~~~~~~~~~~~~~~~~

This was removed.
Reinstalling is usually not a good idea.
You can uninstall and install if you want.


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


All deprecated methods
----------------------

Some methods are no longer supported.  The methods are still there,
but they do nothing:

- listInstallableProducts

- listInstalledProducts

- getProductFile

- getProductReadme

- notifyInstalled

- reinstallProducts

Some methods have been renamed.  The old method names are kept for
backwards compatibility.  They do roughly the same as before, but
there are differences.  And all keyword arguments are ignored.  You
should switch to the new methods instead:

- isProductInstalled, use is_product_installed instead

- isProductInstallable, use is_product_installable instead

- isProductAvailable, use is_product_installable instead

- getProductVersion, use get_product_version instead

- upgradeProduct, use upgrade_product instead

- installProducts, use install_product with a single product instead

- installProduct, use install_product instead

- uninstallProducts, use uninstall_product with a single product instead.


INonInstallable
---------------

There used to be an INonInstallable interface in CMFPlone (for hiding
profiles) and one in CMFQuickInstallerTool (for hiding products).  In
the new situation, these are combined in the one from CMFPlone.

Sample usage:

In configure.zcml::

  <utility factory=".setuphandlers.NonInstallable"
           name="your.package" />

In setuphandlers.py::

  from Products.CMFPlone.interfaces import INonInstallable
  from zope.interface import implements

  class NonInstallable(object):
      implements(INonInstallable)

      def getNonInstallableProducts(self):
          # This used to be CMFQuickInstallerTool.
          # Make sure this package does not show up in the add-ons
          # control panel:
          return ['collective.hidden.package']

      def getNonInstallableProfiles(self):
          # This already was in CMFPlone.
          # Hide the base profile from your.package from the list
          # shown at site creation.
          return ['your.package:base']

When you do not need them both, you can let the other return an empty
list, or you can leave that method out completely.


Ideas for Plone 5.0
-------------------

Add ``get_installer`` function that return the old
``portal_quickinstaller`` with getToolByName.

- Good: this way you can use ``get_installer`` in all Plone 5 versions
  (well, starting from 5.0.something).  Use ``get_installer`` and the
  deprecated methods and it will work in 5.0 and higher.

- Bad: then the availability of ``get_installer`` does not tell you
  whether you get the old tool or the new view.  If you try to use the
  new methods, they will fail because they do not exist.


TODO in Plone 5.1
-----------------

- Make lots of uninstall profiles.  At least these ones, because they
  are installable in standard Plone:

  - ATContentTypes
  - plone.app.multilingual
  - plone.session
  - CMFPlacefulWorkflow
  - plone.app.openid
  - plone.app.iterate

  Probably these, because they are dependencies of the above:

  - Archetypes (from ATCT)
  - CMFFormController (from ATCT)
  - MimetypesRegistry (from Archetypes)
  - PortalTransforms (from Archetypes)

- Additional idea: before uninstalling, check if the default profile
  is a dependency of another profile that is currently installed.

- Problem: hidden installed products are no longer hidden.  These are
  installed by default in Plone and should not show up in the UI as
  installed:

  - plonetheme.barceloneta
  - plone.app.caching
  - plone.app.intid

- In uninstall_product we apply the uninstall profile and unmark the
  default profile.  We could do the last in an event handler, much
  like the old event handler in Products.CMFQuickInstallerTool, so
  that the default profile is also unmarked when someone manually
  applies the uninstall profile.


TODO in Plone 6
---------------

We do not want to break everything in Plone 5.x.
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
