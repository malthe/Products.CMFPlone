from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone.interfaces import INonInstallable
from Products.Five.browser import BrowserView
from Products.GenericSetup import EXTENSION
from Products.GenericSetup.tool import UNKNOWN
from Products.statusmessages.interfaces import IStatusMessage
from plone.memoize import view
from zope.component import getAllUtilitiesRegisteredFor
import logging
import pkg_resources

logger = logging.getLogger('Plone')


class InstallerView(BrowserView):
    """View on all contexts for installing and uninstalling products.
    """

    def __init__(self, *args, **kwargs):
        super(InstallerView, self).__init__(*args, **kwargs)
        self.ps = getToolByName(self.context, 'portal_setup')
        self.errors = {}

    def is_profile_installed(self, profile_id):
        return self.ps.getLastVersionForProfile(profile_id) != UNKNOWN

    def is_product_installed(self, product_id):
        profile = self.get_install_profile(product_id)
        if not profile:
            return False
        return self.is_profile_installed(profile['id'])

    def _install_profile_info(self, product_id):
        """List extension profile infos of a given product.

        From CMFQuickInstallerTool/QuickInstallerTool.py
        _install_profile_info
        """
        profiles = self.ps.listProfileInfo()
        # We are only interested in extension profiles for the product.
        # TODO Remove the manual Products.* check here. It is still needed.
        profiles = [
            prof for prof in profiles
            if prof['type'] == EXTENSION and (
                prof['product'] == product_id or
                prof['product'] == 'Products.%s' % product_id
            )
        ]
        return profiles

    def get_install_profiles(self, product_id):
        """List all installer profile ids of the given name.

        From CMFQuickInstallerTool/QuickInstallerTool.py
        getInstallProfiles

        TODO Might be superfluous.
        """
        return [prof['id'] for prof in self._install_profile_info(product_id)]

    def _get_profile(self, product_id, name, strict=True):
        """Return profile with given name.

        Also return None when no profiles are found at all.

        @product_id: For example CMFPlone or plone.app.registry.

        @name: usually 'default' or 'uninstall'.

        @strict: return None when name is not found.  Otherwise fall
        back to the first profile.
        """
        profiles = self._install_profile_info(product_id)
        if not profiles:
            return
        # QI used to pick the first profile.
        for profile in profiles:
            profile_id = profile['id']
            profile_id_parts = profile_id.split(':')
            if len(profile_id_parts) != 2:
                logger.error("Profile with id '%s' is invalid." % profile_id)
            if profile_id[1] == 'default':
                return profile
        if not strict:
            # Return the first profile after all.
            return profiles[0]

    def get_install_profile(self, product_id):
        """Return the default install profile.

        From CMFQuickInstallerTool/QuickInstallerTool.py
        getInstallProfile
        """
        return self._get_profile(product_id, 'default', strict=False)

    def get_uninstall_profile(self, product_id):
        """Return the uninstall profile.

        Note: not used yet.
        """
        return self._get_profile(product_id, 'default', strict=True)

    def is_product_installable(self, product_id):
        """Does a product have an installation profile?

        From CMFQuickInstallerTool/QuickInstallerTool.py
        isProductInstallable (and the deprecated isProductAvailable)
        """
        # TODO Do we still want to blacklist complete products instead of only
        # specific profile ids?
        #
        # from Products.CMFQuickInstallerTool.interfaces import INonInstallable
        # not_installable = []
        # utils = getAllUtilitiesRegisteredFor(INonInstallable)
        # for util in utils:
        #     not_installable.extend(util.getNonInstallableProducts())
        # if product_id in not_installable:
        #     return False

        profile = self.get_install_profile(product_id)
        if profile is None:
            return
        try:
            self.ps.getProfileDependencyChain(profile['id'])
        except KeyError, e:
            # Don't show twice the same error: old install and profile
            # oldinstall is test in first in other methods we may have an extra
            # 'Products.' in the namespace.
            #
            # TODO:
            # 1. Make sense of the previous comment.
            # 2. Possibly remove the special case for 'Products'.
            # 3. Make sense of the next five lines: they remove 'Products.'
            #    when it is there, and add it when it is not???
            checkname = product_id
            if checkname.startswith('Products.'):
                checkname = checkname[9:]
            else:
                checkname = 'Products.' + checkname
            if checkname in self.errors:
                if self.errors[checkname]['value'] == e.args[0]:
                    return False
                # A new error is found, register it
                self.errors[product_id] = dict(
                    type=_(
                        u"dependency_missing",
                        default=u"Missing dependency"
                    ),
                    value=e.args[0],
                    product_id=product_id
                )
            else:
                self.errors[product_id] = dict(
                    type=_(
                        u"dependency_missing",
                        default=u"Missing dependency"
                    ),
                    value=e.args[0],
                    product_id=product_id
                )
            return False
        return True

    def get_product_version(self, product_id):
        """Return the version of the product (package).

        From CMFQuickInstallerTool/QuickInstallerTool
        getProductVersion
        That implementation used to fall back to getting the version.txt.
        """
        try:
            dist = pkg_resources.get_distribution(product_id)
            return dist.version
        except pkg_resources.DistributionNotFound:
            pass

        # TODO: check if extra Products check is needed after all.
        # if "." not in product_id:
        #     try:
        #         dist = pkg_resources.get_distribution(
        #             "Products." + product_id)
        #         return dist.version
        #     except pkg_resources.DistributionNotFound:
        #         pass

    def get_latest_upgrade_step(self, profile_id):
        """Get highest ordered upgrade step for profile.

        If anything errors out then go back to "old way" by returning
        'unknown'.

        From CMFPlone/QuickInstallerTool.py getLatestUpgradeStep
        """
        profile_version = UNKNOWN
        try:
            available = self.ps.listUpgrades(profile_id, True)
            if available:  # could return empty sequence
                latest = available[-1]
                profile_version = max(latest['dest'],
                                      key=pkg_resources.parse_version)
        except Exception:
            pass
        return profile_version

    def upgrade_info(self, product_id):
        """Returns upgrade info for a product.

        This is a dict with among others two booleans values, stating if
        an upgrade is required and available.

        From CMFPlone/QuickInstaller.py upgradeInfo
        """
        available = self.is_product_installable(product_id)
        if not available:
            return False
        profile = self.get_install_profile(product_id)
        if profile is None:
            # No GS profile, not supported.
            return {}
        profile_id = profile['id']
        profile_version = str(self.ps.getVersionForProfile(profile_id))
        if profile_version == 'latest':
            profile_version = self.get_latest_upgrade_step(profile_id)
        if profile_version == UNKNOWN:
            # If a profile doesn't have a metadata.xml use the package version.
            profile_version = str(self.get_product_version(product_id))
        installed_profile_version = self.ps.getLastVersionForProfile(
            profile_id)
        # getLastVersionForProfile returns the version as a tuple or unknown.
        if installed_profile_version != UNKNOWN:
            installed_profile_version = str(
                '.'.join(installed_profile_version))
        return dict(
            required=profile_version != installed_profile_version,
            available=len(self.ps.listUpgrades(profile_id)) > 0,
            hasProfile=True,  # TODO hasProfile is always True now.
            installedVersion=installed_profile_version,
            newVersion=profile_version,
        )

    def upgrade_product(self, product_id):
        messages = IStatusMessage(self.request)
        profile = self.getInstallProfile(product_id)
        if profile is None:
            logger.error("Could not upgrade %s, no profile.", product_id)
            messages.addStatusMessage(
                _(u'Error upgrading ${product}.',
                  mapping={'product': product_id}), type="error")
            return False
        try:
            self.ps.upgradeProfile(profile['id'])
            messages.addStatusMessage(
                _(u'Upgraded ${product}!', mapping={'product': product_id}),
                type="info")
            return True
        except Exception, e:
            logger.error("Could not upgrade %s: %s" % (product_id, e))
            messages.addStatusMessage(
                _(u'Error upgrading ${product}.',
                  mapping={'product': product_id}), type="error")

        return False

    def install_product(self, product_id, omit_snapshots=True,
                        blacklisted_steps=None):
        """Install a product by name.

        From CMFQuickInstallerTool/QuickInstallerTool.py installProduct

        TODO Probably fine to remove the omit_snapshots and
        blacklisted_steps keyword arguments.
        """
        messages = IStatusMessage(self.request)
        profile = self.get_install_profile(product_id)
        if not profile:
            logger.error("Could not install %s: no profile found.", product_id)
            messages.addStatusMessage(
                _(u'Error upgrading ${product}.',
                  mapping={'product': product_id}), type="error")
            # TODO Possibly raise an error.
            return False

        if self.is_product_installed(product_id):
            messages.addStatusMessage(
                _(u'Error installing ${product}. '
                  'This product is already installed, '
                  'please uninstall before reinstalling it.',
                  mapping={'product': product_id}), type="error")
            return False

        # Create a snapshot before installation.  Note: this has nothing to do
        # with the snapshots that the portal_quickinstaller used to make.
        if not omit_snapshots:
            before_id = self.ps._mangleTimestampName(
                'qi-before-%s' % product_id)
            self.ps.createSnapshot(before_id)

        profile = self.get_install_profile(product_id)
        self.ps.runAllImportStepsFromProfile(
            'profile-%s' % profile['id'],
            blacklisted_steps=blacklisted_steps)

        # Create a snapshot after installation
        if not omit_snapshots:
            after_id = self.ps._mangleTimestampName(
                'qi-after-%s' % product_id)
            self.ps.createSnapshot(after_id)

    def uninstall_product(self, product_id):
        """Uninstall a product by name.
        """
        messages = IStatusMessage(self.request)
        profile = self.get_uninstall_profile(product_id)
        if not profile:
            logger.error("Could not uninstall %s: no uninstall profile "
                         "found.", product_id)
            messages.addStatusMessage(
                _(u'Error upgrading ${product}.',
                  mapping={'product': product_id}), type="error")
            # TODO Possibly raise an error.
            return False

        self.ps.runAllImportStepsFromProfile(
            'profile-%s' % profile['id'])

        install_profile = self.get_install_profile(product_id)
        if install_profile:
            self.ps.unsetLastVersionForProfile(profile['id'])


class ManageProductsView(InstallerView):
    """
    Activate and deactivate products in mass, and without weird
    permissions issues
    """

    def __call__(self):
        return self.index()

    @view.memoize
    def marshall_addons(self):
        addons = {}

        ignore_profiles = []
        utils = getAllUtilitiesRegisteredFor(INonInstallable)
        for util in utils:
            ignore_profiles.extend(util.getNonInstallableProfiles())

        # Known profiles:
        profiles = self.ps.listProfileInfo()
        # Profiles that have upgrade steps (which may or may not have been
        # applied already).
        # profiles_with_upgrades = self.ps.listProfilesWithUpgrades()
        for profile in profiles:
            if profile['type'] != EXTENSION:
                continue

            pid = profile['id']
            if pid in ignore_profiles:
                continue
            pid_parts = pid.split(':')
            if len(pid_parts) != 2:
                logger.error("Profile with id '%s' is invalid." % pid)
            # Which package (product) is this from?
            product_id = profile['product']
            profile_type = pid_parts[-1]
            if product_id not in addons:
                # get some basic information on the product
                installed = self.is_profile_installed(pid)
                upgrade_info = None
                if installed:
                    upgrade_info = self.upgrade_info(product_id)
                elif not self.is_product_installable(product_id):
                    continue

                if profile_type in product_id:
                    profile_type = 'default'
                    # XXX override here so some products that do not
                    # explicitly say "default" for their install
                    # profile still work
                    # I'm not sure this is right but this is a way
                    # to get CMFPlacefulWorkflow to show up in addons
                    # If it's safe to rename profiles, we can do that too

                addons[product_id] = {
                    'id': product_id,
                    'title': product_id,
                    'description': '',
                    'upgrade_profiles': {},
                    'other_profiles': [],
                    'install_profile': None,
                    'uninstall_profile': None,
                    'is_installed': installed,
                    'upgrade_info': upgrade_info,
                    'profile_type': profile_type,
                }
            # At this point, we have basic information of this product, either
            # from the profile we are currently checking, or a previous
            # profile.  Get this info and enhance it.
            product = addons[product_id]
            if profile_type == 'default':
                product['title'] = profile['title']
                product['description'] = profile['description']
                product['install_profile'] = profile
                product['profile_type'] = profile_type
            elif profile_type == 'uninstall':
                product['uninstall_profile'] = profile
                if 'profile_type' not in product:
                    # if this is the only profile installed, it could just be
                    # an uninstall profile
                    product['profile_type'] = profile_type
            else:
                if 'version' in profile:
                    product['upgrade_profiles'][profile['version']] = profile
                else:
                    product['other_profiles'].append(profile)
        return addons

    def get_addons(self, apply_filter=None, product_name=None):
        """
        100% based on generic setup profiles now. Kinda.
        For products magic, use the zope quickinstaller I guess.

        @filter:= 'installed': only products that are installed
                  'upgrades': only products with upgrades
                  'available': products that are not installed bit
                               could be
                  'broken': uninstallable products with broken
                            dependencies

        @product_name:= a specific product id that you want info on. Do
                   not pass in the profile type, just the name

        XXX: I am pretty sure we don't want base profiles ...
        """
        addons = self.marshall_addons()
        filtered = {}
        if apply_filter == 'broken':
            all_broken = self.errors.values()
            for broken in all_broken:
                filtered[broken['productname']] = broken
        else:
            for product_id, addon in addons.items():
                if product_name and addon['id'] != product_name:
                    continue

                installed = addon['is_installed']
                if apply_filter in ['installed', 'upgrades'] and not installed:
                    continue
                elif apply_filter == 'available':
                    if installed:
                        continue
                    # filter out upgrade profiles
                    if addon['profile_type'] != 'default':
                        continue
                elif apply_filter == 'upgrades':
                    # weird p.a.discussion integration behavior
                    upgrade_info = addon['upgrade_info']
                    if type(upgrade_info) == bool:
                        continue

                    if not upgrade_info['available']:
                        continue

                filtered[product_id] = addon

        return filtered

    def get_upgrades(self):
        """
        Return a list of products that have upgrades on tap
        """
        return self.get_addons(apply_filter='upgrades').values()

    def get_installed(self):
        return self.get_addons(apply_filter='installed').values()

    def get_available(self):
        return self.get_addons(apply_filter='available').values()

    def get_broken(self):
        return self.get_addons(apply_filter='broken').values()


class UpgradeProductsView(InstallerView):
    """
    Upgrade a product... or twenty
    """

    def __call__(self):
        products = self.request.get('prefs_reinstallProducts', None)
        if products:
            for product in products:
                # TODO: exceptions are caught and the next product is handled.
                # I would expect that exceptions are raised instead.
                # This is already in Plone 5.0.
                self.upgrade_product(product)

        purl = getToolByName(self.context, 'portal_url')()
        self.request.response.redirect(purl + '/prefs_install_products_form')


class InstallProductsView(InstallerView):

    def __call__(self):
        products = self.request.get('install_products')
        if products:
            messages = IStatusMessage(self.request)
            for product_id in products:
                self.install_product(product_id)
                msg = _(u'Installed ${product}!',
                        mapping={'product': product_id})
                messages.addStatusMessage(msg, type='info')

        purl = getToolByName(self.context, 'portal_url')()
        self.request.response.redirect(purl + '/prefs_install_products_form')


class UninstallProductsView(InstallerView):

    def __call__(self):
        products = self.request.get('uninstall_products')
        if products:
            messages = IStatusMessage(self.request)
            # 1 at a time for better error messages
            for product_id in products:
                msg_type = 'info'
                try:
                    result = self.uninstall_product(product_id)
                except Exception, e:
                    logger.error("Could not uninstall %s: %s", product_id, e)
                    msg_type = 'error'
                    msg = _(u'Error uninstalling ${product}.', mapping={
                            'product': product_id})
                else:
                    if result:
                        msg = _(u'Uninstalled ${product}.',
                                mapping={'product': product_id})
                    else:
                        # We already gave an error.  TODO Maybe abort the
                        # transaction.
                        break
                messages.addStatusMessage(msg, type=msg_type)

        purl = getToolByName(self.context, 'portal_url')()
        self.request.response.redirect(purl + '/prefs_install_products_form')
