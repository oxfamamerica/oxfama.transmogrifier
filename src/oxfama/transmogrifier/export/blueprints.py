from zope.interface import classProvides, implements

from Products.CMFCore.interfaces import IFolderish
from Products.Archetypes.interfaces import IBaseFolder
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from quintagroup.transmogrifier.sitewalker import SiteWalkerSection


class CountLimitedSitewalkerSection(SiteWalkerSection):
    """allow 'limit' on the number of objects to walk before quitting

    provide 'limit' as an integer value in pipeline configuration, defaults
      to 0, which means unlimited.
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        super(CountLimitedSitewalkerSection, self).__init__(
            transmogrifier, name, options, previous)
        self.limit = int(options.get('limit', 0))
        self.count = 0

    def walk(self, obj):
        if self.limit and self.count < self.limit:
            self.count += 1
            if IFolderish.providedBy(obj) or IBaseFolder.providedBy(obj):
                contained = self.getContained(obj)
                yield obj, tuple([(k, v.getPortalTypeName()) for k, v in contained])
                for k, v in contained:
                    for x in self.walk(v):
                        yield x
            else:
                yield obj, ()
        else:
            # we've reached our limit, stop iteration
            raise StopIteration
