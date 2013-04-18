from plone.app.testing import PloneSandboxLayer
# from plone.app.testing import applyProfile
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting

from plone.testing import z2

from zope.configuration import xmlconfig


class OxfamatransmogrifierLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import oxfama.transmogrifier
        xmlconfig.file(
            'configure.zcml',
            oxfama.transmogrifier,
            context=configurationContext
        )
        # we do not run the contentdump pipeline here because this would 
        # actually export content. 

OXFAMA_TRANSMOGRIFIER_FIXTURE = OxfamatransmogrifierLayer()
OXFAMA_TRANSMOGRIFIER_INTEGRATION_TESTING = IntegrationTesting(
    bases=(OXFAMA_TRANSMOGRIFIER_FIXTURE,),
    name="OxfamatransmogrifierLayer:Integration"
)
OXFAMA_TRANSMOGRIFIER_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(OXFAMA_TRANSMOGRIFIER_FIXTURE, z2.ZSERVER_FIXTURE),
    name="OxfamatransmogrifierLayer:Functional"
)
