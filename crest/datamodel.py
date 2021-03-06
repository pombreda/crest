#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import copy, os

from xobj import xobj
from conary import versions

class BaseObject(object):

    def __init__(self, **kwargs):
        for key, val in self.__class__.__dict__.iteritems():
            if type(val) == list:
                setattr(self, key, [])

        for key, val in kwargs.iteritems():
            if (hasattr(self.__class__, key) or
                (hasattr(self, '_xobj') and key in (self._xobj.attributes))):
                setattr(self, key, val)
            else:
                raise TypeError, 'unknown constructor parameter %s' % key

class VersionSummary(BaseObject):

    revision = str
    ordering = float

    def __init__(self, v):
        self.revision = str(v.trailingRevision())
        # we don't use getTimestamp here because 0 is okay...
        ts = v.trailingRevision().timeStamp
        self.ordering = ts

class Version(BaseObject):

    full = str
    label = str
    revision = str
    ordering = float

    def __init__(self, v):
        self.full = str(v)
        self.label = str(v.trailingLabel())
        self.revision = str(v.trailingRevision())
        # we don't use getTimestamp here because 0 is okay...
        ts = v.trailingRevision().timeStamp
        self.ordering = ts

class TroveIdent(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str })
    name = str
    version = Version
    flavor = str

    def __init__(self, version = None, mkUrl = None, **kwargs):
        BaseObject.__init__(self, **kwargs)
        self.version = Version(version)
        if mkUrl:
            host = version.trailingLabel().getHost()
            self.id = mkUrl('trove', "%s=%s[%s]" % (self.name, version,
                                                    self.flavor),
                            host = host)

class TroveIdentList(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'total' : int, 'start' : int,
                                             'id' : str } )
    trove = [ TroveIdent ]

    def append(self, name = None, version = None, flavor = None, mkUrl = None):
        self.trove.append(TroveIdent(name = name, version = version,
                                     flavor = flavor, mkUrl = mkUrl))

    def __init__(self, **kwargs):
        BaseObject.__init__(self, **kwargs)

class NamedTroveIdentList(TroveIdentList):

    trove = [ TroveIdent ]
    _xobj = copy.copy(TroveIdentList._xobj)
    _xobj.tag = 'trovelist'

class Inode(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str })

class FileReference(BaseObject):

    inode = Inode
    path = str
    version = str
    fileId = str
    pathId = str
    isCapsule = int

    def __init__(self, mkUrl = None, fileId = None, version = None,
                 thisHost = None, path = None, pathId = None,
                 contentAvailable = None, **kwargs):
        BaseObject.__init__(self, fileId = fileId, version = version,
                            pathId = pathId, path = path, **kwargs)
        if mkUrl:
            host = versions.VersionFromString(version).trailingLabel().getHost()
            flags = [ ( 'path', os.path.basename(path)) ]
            if not contentAvailable:
                flags.append(( 'nocontent', '1'))
            self.inode = Inode(id = mkUrl('file', self.fileId, 'info',
                               flags, host = host))

class ListOfTroves(BaseObject):

    displayname = str
    trovelist = TroveIdentList

    def __init__(self, **kwargs):
        self.trovelist = TroveIdentList()
        BaseObject.__init__(self, **kwargs)
        self.displayname = self.__class__.DisplayName

    def append(self, name = None, version = None, flavor = None, mkUrl = None):
        self.trovelist.append(name = name, version = version,
                              flavor = flavor, mkUrl = mkUrl)

class SourceTrove(ListOfTroves):

    DisplayName = "Source"

class IncludedTroves(ListOfTroves):

    DisplayName = "Includes"

class ClonedFrom(ListOfTroves):

    DisplayName = "Cloned from"

class BuildDeps(ListOfTroves):

    DisplayName = "Built with"

class PolicyProvider(ListOfTroves):

    DisplayName = "Policy from"

class LoadedTroves(ListOfTroves):

    DisplayName = "Build troves loaded"

class CopiedFrom(ListOfTroves):

    DisplayName = "Groups copied from"

class DerivedFrom(ListOfTroves):

    DisplayName = "Derived from"

class BuildLog(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str } )

    def __init__(self, fileId, host, thisHost = None, mkUrl = None):
        BaseObject.__init__(self, id = mkUrl('logfile', fileId, host = host,
                                             thisHost = thisHost))

class SingleTrove(TroveIdent):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'trove')
    fileref = [ FileReference ]
    included = IncludedTroves
    source = SourceTrove
    buildtime = long
    clonedfrom = ClonedFrom
    size = long
    builddeps = BuildDeps
    policyprovider = PolicyProvider
    loadedtroves = LoadedTroves
    copiedfrom = CopiedFrom
    derivedfrom = DerivedFrom
    license = [ str ]
    shortdesc = str
    longdesc = str
    crypto = [ str ]
    displayflavor = str
    buildlog = str
    xmlbuildlog = BuildLog
    buildlog = BuildLog

    def __init__(self, source = None, mkUrl = None, thisHost = None, **kwargs):
        TroveIdent.__init__(self, mkUrl = mkUrl, **kwargs)
        self._mkUrl = mkUrl
        self._thisHost = thisHost
        if source:
            self.source = SourceTrove()
            self.source.append(name = source[0], version = source[1],
                               flavor = source[2], mkUrl = mkUrl)

    def addFile(self, f):
        self.fileref.append(f)

    def addReferencedTrove(self, name, version, flavor, mkUrl = None):
        if self.included == IncludedTroves:
            self.included = IncludedTroves()

        self.included.append(name = name, version = version,
                             flavor = flavor, mkUrl = mkUrl)

    def addClonedFrom(self, name, version, flavor, mkUrl = None):
        if self.clonedfrom == ClonedFrom:
            self.clonedfrom = ClonedFrom()

        self.clonedfrom.append(name = name, version = version,
                               flavor = flavor, mkUrl = mkUrl)

    def setBuildLog(self, host, fileId):
        self.buildlog = BuildLog(fileId, host, mkUrl = self._mkUrl,
                                 thisHost = self._thisHost)

    def setXMLBuildLog(self, host, fileId):
        self.xmlbuildlog = BuildLog(fileId, host, mkUrl = self._mkUrl,
                                    thisHost = self._thisHost)

class TroveList(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'trovelist')
    trove = [ SingleTrove ]

    def append(self, trv):
        self.trove.append(trv)

class ChangeLog(BaseObject):

    name = str
    message = str

class Node(BaseObject):

    _xobj = xobj.XObjMetadata()
    name = str
    trovelist = TroveIdentList
    fullnodelist = object
    version = VersionSummary
    flavor = str
    changeLog = ChangeLog
    shortdesc = str

    def __init__(self, version = None, mkUrl = None, **kwargs):
        BaseObject.__init__(self, **kwargs)
        self.version = VersionSummary(version)
        if mkUrl:
            host = version.trailingLabel().getHost()
            self.trovelist = \
                TroveIdentList(id = mkUrl('troves', "%s=%s" %
                                                (self.name, version),
                          host = host))
            self.fullnodelist = \
                TroveIdentList(id = mkUrl('node',
                          [ ('label',  str(version.trailingLabel())),
                            ('name',   self.name),
                            ('latest', '0') ]))

class NodeList(BaseObject):
    _xobj = xobj.XObjMetadata(attributes = { 'total' : int, 'start' : int,
                                             'id' : str, 'href' : str })
    node = [ Node ]

    def append(self, name = None, version = None, mkUrl = None,
               changeLog = None, shortdesc = None):
        self.node.append(Node(name = name, version = version, mkUrl = mkUrl,
                              changeLog = changeLog, shortdesc = None))
Node.fulltrovelist = NodeList           # circular type reference

class NamedNodeList(NodeList):
    _xobj = xobj.XObjMetadata(tag = 'nodelist',
                              attributes = { 'total' : int, 'start' : int,
                                             'id' : str })
    node = [ Node ]

class Label(BaseObject):

    name = str
    latest = TroveIdentList
    nodelist = NodeList

class FileId(xobj.XObj):

    _xobj = xobj.XObjMetadata(attributes = { 'href' : str })

class FileObj(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str })

    owner = str
    group = str
    mtime = long
    perms = int

    def __init__(self, mkUrl = None, fileId = None, **kwargs):
        BaseObject.__init__(self, **kwargs)
        if mkUrl:
            self.id = mkUrl('file', fileId, 'info')

class XObjLong(long):

    pass

class Content(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'href' : str })

class RegularFile(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str },
                              tag = 'file')
    size = XObjLong
    sha1 = str
    content = Content

    def __init__(self, mkUrl = None, fileId = None, path = None,
                 withContentLink = True, **kwargs):
        FileObj.__init__(self, mkUrl = mkUrl, fileId = fileId, **kwargs)
        if withContentLink and mkUrl:
            self.content = Content(href=mkUrl('file', fileId, 'content', path))


class Directory(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'directory')

class Socket(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'socket')

class NamedPipe(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'namedpipe')

class SymlinkFile(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'symlink')
    target = str

class _DeviceFile(FileObj):

    major = int
    minor = int

class BlockDeviceFile(_DeviceFile):
    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'blockdevice')

class CharacterDeviceFile(_DeviceFile):
    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'chardevice')

class Repository(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'repository')
    label = [ Label ]
    trovelist = TroveIdentList

    def appendLabel(self, labelStr, mkUrl = None):
        l = Label(name = labelStr)
        if mkUrl:
            l.latest = TroveIdentList(
                    id = mkUrl('trove',  [ ('label', labelStr) ])
            )
            l.summary = NodeList(
                        href = mkUrl('node', [ ('label', labelStr ),
                                               ('type', 'package' ),
                                               ('type', 'group'),
                                               ('type', 'fileset') ] )
            )
            l.groups = NodeList(
                        href = mkUrl('node', [ ('label', labelStr ),
                                               ('type', 'group') ] )
            )
            l.packages = NodeList(
                        href = mkUrl('node', [ ('label', labelStr ),
                                               ('type', 'package'),
                                               ('type', 'fileset') ] )
            )
            l.sources = NodeList(
                        href = mkUrl('node', [ ('label', labelStr ),
                                               ('type', 'source') ] )
            )

        self.label.append(l)
