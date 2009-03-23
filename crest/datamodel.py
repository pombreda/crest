#
# Copyright (c) 2009 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

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

class BaseTroveInfo(BaseObject):

    name = str
    version = str
    flavor = str

    def __init__(self, version = None, mkUrl = None, **kwargs):
        BaseObject.__init__(self, version = version, **kwargs)
        if mkUrl:
            ver = versions.VersionFromString(version)
            host = ver.trailingLabel().getHost()
            self.id = mkUrl('trove', "%s=%s[%s]" % (self.name, self.version,
                                                    self.flavor),
                            host = host)

class TroveIdent(BaseTroveInfo):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'trove')

class TroveIdentList(BaseObject):

    _xobj = xobj.XObjMetadata(tag = 'troveList')
    troveList = [ TroveIdent ]

    def append(self, name = None, version = None, flavor = None, mkUrl = None):
        self.troveList.append(TroveIdent(name = name, version = version,
                                         flavor = flavor, mkUrl = mkUrl))

class LabelList(BaseObject):

    _xobj = xobj.XObjMetadata(tag = 'LabelList')
    label = [ str ]

    def append(self, labelStr):
        self.label.append(labelStr)

class FileId(xobj.XObj):

    _xobj = xobj.XObjMetadata(attributes = { 'href' : str })

class FileInTrove(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str })

    path = str
    version = str
    fileId = str
    pathId = str

    def __init__(self, mkUrl = None, fileId = None, version = None,
                 thisHost = None, **kwargs):
        BaseObject.__init__(self, fileId = fileId, version = version, **kwargs)
        if mkUrl:
            host = versions.VersionFromString(version).trailingLabel().getHost()
            self.id = mkUrl('file', self.fileId, 'info', host = host)

class ReferencedTrove(BaseTroveInfo):

    pass

class SingleTrove(TroveIdent):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'Trove')
    file = [ FileInTrove ]
    trove = [ ReferencedTrove ]

    def addFile(self, f):
        self.file.append(f)

    def addReferencedTrove(self, name, version, flavor, mkUrl = None):
        self.trove.append(ReferencedTrove(name = name, version = version,
                                           flavor = flavor, mkUrl = mkUrl))

class FileObj(BaseObject):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str })

    owner = str
    group = str
    mtime = int
    perms = int

    def __init__(self, mkUrl = None, fileId = None, **kwargs):
        BaseObject.__init__(self, **kwargs)
        if mkUrl:
            self.id = mkUrl('file', fileId, 'info')

class XObjLong(long):

    pass

class RegularFile(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'href' : str,
                                             'id' : str },
                              tag = 'File')
    size = XObjLong
    sha1 = str

    def __init__(self, mkUrl = None, fileId = None, **kwargs):
        FileObj.__init__(self, mkUrl = mkUrl, fileId = fileId, **kwargs)
        if mkUrl:
            self.href = mkUrl('file', fileId, 'content')

class Directory(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'Directory')

class Socket(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'Socket')

class NamedPipe(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'NamedPipe')

class SymlinkFile(FileObj):

    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'Symlink')
    target = str

class _DeviceFile(FileObj):

    major = int
    minor = int

class BlockDeviceFile(_DeviceFile):
    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'BlockDevice')

class CharacterDeviceFile(_DeviceFile):
    _xobj = xobj.XObjMetadata(attributes = { 'id' : str }, tag = 'CharDevice')
