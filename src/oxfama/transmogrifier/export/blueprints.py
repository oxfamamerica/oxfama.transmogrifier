import logging
import os.path

from zope.interface import classProvides, implements
from zope.annotation.interfaces import IAnnotations
from plone.uuid.interfaces import IUUID

from Products.CMFCore.interfaces import IFolderish
from Products.Archetypes import atapi
from Products.Archetypes.interfaces import IBaseFolder
from Products.Archetypes.interfaces import IBaseObject
from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
from quintagroup.transmogrifier.sitewalker import SiteWalkerSection
from quintagroup.transmogrifier.writer import WriterSection

from oxfama.transmogrifier.export.unicode_csv import UnicodeDictWriter
from oxfama.transmogrifier.export.unicode_csv import force_unicode

try:
    from plone.app.blob.interfaces import IBlobField
    HAS_BLOB = True
except ImportError:
    HAS_BLOB = False


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
        if self.limit and self.count >= self.limit:
            raise StopIteration
        else:
            self.count += 1
            if IFolderish.providedBy(obj) or IBaseFolder.providedBy(obj):
                contained = self.getContained(obj)
                yield obj, tuple([(k, v.getPortalTypeName()) for k, v in contained])
                for k, v in contained:
                    for x in self.walk(v):
                        yield x
            else:
                yield obj, ()


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


class SchemaDictionarySection(object):
    """create a dictionary of field name -> field value pairs from items'
    AT Schema
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.context = transmogrifier.context
        self.previous = previous
        self.options = options
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')

        self.exclude = filter(None, [i.strip() for i in 
                              options.get('exclude', '').splitlines()])
        self.schema_key = options.get('schema-key', '_schemafields').strip()

    def __iter__(self):
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:
                yield item; continue

            path = item[pathkey]
            obj = self.context.unrestrictedTraverse(str(path), None)
            if obj is None:         # path doesn't exist
                yield item; continue

            obj_dict = self.get_base_object_identifiers(obj)

            if IBaseObject.providedBy(obj):
                # grab schema of item and convert it to a dict
                # import pdb; pdb.set_trace( )
                obj_schema = obj.Schema()
                try:
                    all_schema_keys = obj_schema.keys()
                except AttributeError:
                    all_schema_keys = []
                use_keys = sorted(list(
                    set(all_schema_keys).difference(set(self.exclude))))

                field_dict = {}
                for key in use_keys:
                    field = obj_schema.getField(key)
                    # simply report file fields as binary file fields, do
                    # not attempt to output binary data as csv values :)
                    if (isinstance(field, atapi.FileField) and
                        not isinstance(field, atapi.TextField):
                        value = u"binary file field"
                    else:
                        accessor = field.getAccessor(obj)
                        value = accessor()
                    # if we don't have a value for this, skip over it.
                    if not value:
                        continue
                    # get type:uid from referenced objects
                    if isinstance(field, atapi.ReferenceField):
                        value = self.get_reference_value(value)

                    if isinstance(value, (tuple, list)):
                        value = u';'.join(map(force_unicode, value))

                    field_dict[key] = force_unicode(value)

                obj_dict.update(field_dict)

            item[self.schema_key] = obj_dict
            yield item

    def get_base_object_identifiers(self, obj):
        # ensure no acquisition
        default = {'uuid': 'none', 'uid': 'none'}
        if not obj:
            return default

        unwrapped = obj.aq_base

        new_uuid = None
        try:
            new_uuid = IUUID(unwrapped)
        except TypeError:
            # leave at default
            pass
        if new_uuid:
            default['uuid'] = new_uuid

        new_uid = None
        try:
            new_uid = unwrapped.UID()
        except AttributeError:
            # leave at default
            pass
        if new_uid:
            default['uid'] = new_uid

        return default

    def get_reference_value(self, value):
        """get the UID and portal type of all referenced object
        """
        if not isinstance(value, (tuple, list)):
            value = [value]

        return_values = []
        for obj in value:
            ids = set(self.get_base_object_identifiers(obj).values())
            identifier = ','.join(ids)
            try:
                ptype = obj.portal_type
            except AttributeError:
                ptype = 'unknown type'
            return_values.append(':'.join((ptype, identifier)))
        return return_values


class FileWriterSection(WriterSection):
    """writes files stored in file fields out to disk

    Based on the quintagroup.transmogrifier WriterSection
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        super(FileWriterSection, self).__init__(
            transmogrifier, name, options, previous)
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.logger = name

    def __iter__(self):
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:
                yield item; continue

            path = item[pathkey]
            obj = self.context.unrestrictedTraverse(str(path), None)
            if obj is None:         # path doesn't exist
                yield item; continue

            files = []
            try:
                if IBaseObject.providedBy(obj):
                    # grab schema of item and convert it to a dict
                    obj_fields = [f.__name__ for f in obj.Schema().fields()]
                    for field in obj_fields:
                        if obj.isBinary(field):
                            fname, ct, data = self.extractFile(obj, field)
                            if fname == '' or data == '':
                                # empty file fields have empty filename and empty data
                                # skip them
                                continue
                            files.append(dict(filename=fname, mimetype=ct, data=data))
                        else:
                            # this is not a file field, so skip it
                            continue
            except AttributeError, e:
                msg = "Uanble to export binary file at %s: %s" % (path, str(e))
                logging.getLogger(self.logger).error(msg)
                yield item; continue
            
            if files:
                # write out files at this point
                if len(files) > 1:
                    # there is more than one file, we will create a folder at
                    # the path of the current item and export all files there.
                    item_path = path
                else:
                    # there is only one file, we can write it into the 
                    # container for the current item (item['_path'][:-1])
                    item_path, dummy = os.path.split(path)
                for file_info in files:
                    try:
                        self.export_context.writeDataFile(file_info['filename'],
                                                          file_info['data'],
                                                          file_info['mimetype'],
                                                          subdir=item_path)
                    except TypeError, e:
                        import pdb; pdb.set_trace( )
                        raise

            yield item

    # stolen from q.t.binary
    def extractFile(self, obj, field):
        """ Return tuple of (filename, content_type, data)
        """
        field = obj.getField(field)
        if HAS_BLOB and IBlobField.providedBy(field):
            wrapper = field.getRaw(obj)
            value = str(wrapper)
            fname = wrapper.getFilename()
            if fname is None:
                fname = ''
            ct = wrapper.getContentType()
            if ct is None:
                ct = ''
        else:
            # temporarily:
            # dirty call, I know, just lazy to get method arguments
            # TextField overrided getBaseUnit method but didn't follow API
            try:
                base_unit = field.getBaseUnit(obj, full=True)
            except TypeError:
                base_unit = field.getBaseUnit(obj)
            fname = base_unit.getFilename()
            ct = base_unit.getContentType()
            value = base_unit.getRaw()

        return fname, ct, value


class CSVWriterSection(object):
    """parses xml files associated with item and writes output to csv files
    """
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.options = options
        self.previous = previous
        self.schemakey = defaultMatcher(
            options, 'schema-key', name, 'schemafields')
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.typekey = defaultMatcher(options, 'type-key', name, 'type',
                                      ('portal_type', 'Type'))
        self.anno = IAnnotations(transmogrifier)
        self.storage = self.anno.setdefault(CSV_KEY, {})
        self.destination = self.options.get('destination', '/tmp')

    def __iter__(self):
        for item in self.previous:
            keys = item.keys()
            schemakey = self.schemakey(*keys)[0]
            pathkey = self.pathkey(*keys)[0]
            typekey = self.typekey(*keys)[0]
            
            item_path = item[pathkey]
            item_type = item[typekey]
            item_schema = item[schemakey]
            if not item_schema:
                # there are no xml files that we can parse into csv, skip
                yield item; continue

            fieldnames = ['path', ]
            row = {'path': item_path}
            csv_filename = "%s.csv" % item_type.lower().replace(' ', '_')
            fieldnames.extend(sorted(item_schema))
            row.update(item_schema)

            # put fieldnames and row into csvfileinfo
            csvfileinfo = self.storage.setdefault(
                csv_filename, {'fieldnames': [], 'rows': []})
            csvfileinfo['fieldnames'] = list(
                set(fieldnames + csvfileinfo['fieldnames']))
            csvfileinfo['rows'].append(row)

            yield item

        # after iteration is done
        for filename, contents in self.storage.items():
            filepath = os.path.join(self.destination, filename)
            with open(filepath, 'w') as fh:
                fieldnames = sorted(contents.get('fieldnames', []))
                writer = UnicodeDictWriter(fh, fieldnames, restval=u'')
                writer.writerow(dict([(fn, fn) for fn in fieldnames]))
                writer.writerows(contents.get('rows', []))
        # clean up
        self.storage = {}
