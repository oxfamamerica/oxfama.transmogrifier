from zope.interface import implements

from Products.CMFPlone.interfaces import INonInstallable
from Products.CMFQuickInstallerTool.interfaces import INonInstallable as INonInstallableProduct


class HiddenProfiles(object):
    implements(INonInstallable)

    def getNonInstallableProfiles(self):
        return ['oxfama.transmogrifier:contentdump', ]


class UninstallableProduct(object):
    implements(INonInstallableProduct)

    def getNonInstallableProducts(self):
        return ['oxfama.transmogrifier', ]
