from zope.interface import classProvides, implements
from zope.annotation.interfaces import IAnnotations

from Products.CMFCore.interfaces import IFolderish
from Products.Archetypes.interfaces import IBaseFolder
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
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


CSV_KEY = 'oxfama.transmogrifier.csvfiles'

# storage format:
# 
#   {
#     type_name: {'fieldnames': ['list','of','all','possible','fields'],
#                 'rows': [{<dict_of_field_values_1>}, 
#                          ...,
#                          {dict_N}],
#                }
#   }


class CSVWriterSection(object):
    """parses xml files associated with item and writes output to csv files
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        import pdb; pdb.set_trace( )
        self.transmogrifier = transmogrifier
        self.options = options
        self.fileskey = defaultMatcher(options, 'files-key', name, 'files')
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.typekey = defaultMatcher(options, 'type-key', name, 'type',
                                      ('portal_type', 'Type'))
        self.anno = IAnnotations(transmogrifier)
        self.storage = self.anno.setdefault(CSV_KEY, {})
        self.destination = self.options.get('destination', '/tmp')

    def __iter__(self):
        import pdb; pdb.set_trace( )
        for item in self.previous:
            keys = item.keys()
            fileskey = self.fileskey(*keys)[0]
            pathkey = self.pathkey(*keys)[0]
            typekey = self.typekey(*keys)[0]
            
            item_path = item[pathkey]
            item_type = item[typekey]
            filesstore = item.get(fileskey, None)
            if not filesstore:
                # there are no xml files that we can parse into csv, skip
                yield item; continue

            fieldnames = ['path', ]
            row = {'path': item_path}
            csv_filename = "%.csv" % item_type.lower().replace(' ', '_')
            for source, fileinfo in filesstore:
                data = fileinfo.get('data', '')
                if not data:
                    # no data for this file
                    continue

                # parse file getting fieldnames and row values
                fieldnames.append(source)
                row.update({source: 'present'})

                # put fieldnames and row into csvfileinfo
                csvfileinfo = self.storage.setdefault(
                    csv_filename, {'fieldnames': [], 'rows': []})
                csvfileinfo['fieldnames'] = tuple(
                    set(fieldnames + csvfileinfo['fieldnames']))
                csvfileinfo['rows'].append(row)

            yield item

        # after iteration is done
