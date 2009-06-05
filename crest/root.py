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

import gzip, os

from conary.lib import util
from restlib import controller
from restlib import response
from xobj import xobj

import repquery

class XMLResponse(response.Response):
    def __init__(self, content, contentType='text/xml; charset=utf-8'):
        response.Response.__init__(self, content, contentType)
        self.headers['cache-control'] = 'private, must-revalidate, max-age=0'

class FileResponse(response.FileResponse):

    def __init__(self, path, remotePath=None, gzipped=False, download=True):
        response.FileResponse.__init__(self, path=path)
        self.headers['cache-control'] = 'private, max-age=3600'
        if download:
            self.headers['content-type'] = 'application/octet-stream'
            self.headers['content-disposition'] = 'attachment'
            if remotePath:
                self.headers['content-disposition'] += ('; filename=%s'
                        % (remotePath,))
        else:
            # Trick the browser into displaying the file inline
            self.headers['content-type'] = 'text/plain'

        if gzipped:
            self.headers['content-encoding'] = 'gzip'

class CompressFileResponse(response.Response):

    def getLength(self):
        return None

    def get(self):
        class Output:

            def write(self, stream):
                self.s += stream

            def get(self):
                s = self.s
                self.s = ''
                return s

            def __init__(self):
                self.s = ''

        # we read from self.fileObj, we write to the compressor, which sticks
        # the data in the Output object. We read from the Output object and
        # return it from the iterator so it can be sent to the requestor
        output = Output()
        compressor = gzip.GzipFile(None, "w", fileobj = output)

        BUFSZ = 1024 * 32
        s = self.fileObj.read(BUFSZ)
        while s:
            compressor.write(s)
            compressed = output.get()
            if compressed:
                yield compressed
            s = self.fileObj.read(BUFSZ)

        compressor.close()

        yield output.get()

    def __init__(self, fileObj):
        response.Response.__init__(self)

        self.fileObj = fileObj
        # since this is based on a fileId, no reason for it to timeout
        self.headers['cache-control'] = 'private'
        self.headers['content-type'] = 'text/plain'
        self.headers['content-encoding'] = 'gzip'

class RestController(controller.RestController):

    pass

class GetNode(RestController):

    def index(self, request, cu = None, roleIds = None, repos = None, *args,
              **kwargs):
        label = request.GET.get('label', None)

        types = request.GET.get('type', [])
        if type(types) != list:
            types = [ types ]
        types = set(types)

        troves = repquery.searchNodes(cu, roleIds, label = label,
                                      mkUrl = request.makeUrl,
                                      filterSet = types, db = repos.db)
        return XMLResponse(xobj.toxml(troves, None))

class GetTrove(RestController):

    modelName = "troveString"
    modelRegex = '.*\[.*\]'

    def index(self, request, cu = None, roleIds = None, *args, **kwargs):
        label = request.GET.get('label', None)
        name = request.GET.get('name', None)
        latest = request.GET.get('latest', 1)

        types = request.GET.get('type', [])
        if type(types) != list:
            types = [ types ]
        types = set(types)

        latest = (latest != '0')

        start = int(request.GET.get('start', 0))
        if 'limit' in request.GET:
            limit = int(request.GET['limit'])
        else:
            limit = None

        troves = repquery.searchTroves(cu, roleIds, label = label,
                                       filterSet = types, latest = latest,
                                       mkUrl = request.makeUrl,
                                       start = start, limit = limit,
                                       name = name)

        return XMLResponse(xobj.toxml(troves, None))

    def get(self, request, cu = None, roleIds = None, troveString = None,
            repos = None, *args, **kwargs):
        name, rest = troveString.split('=', 2)
        version, flavor = rest.split("[", 2)
        flavor = flavor[:-1]

        x = repquery.getTrove(cu, roleIds, name, version, flavor,
                              mkUrl = request.makeUrl, thisHost = request.host)
        if x is None:
            return response.Response(status=404)

        return XMLResponse(xobj.toxml(x, None))

class GetTroves(RestController):

    modelName = "troveString"
    modelRegex = '.*'

    def get(self, request, cu = None, roleIds = None, troveString = None,
            repos = None, *args, **kwargs):
        name, version = troveString.split('=', 2)

        x = repquery.getTroves(cu, roleIds, name, version,
                              mkUrl = request.makeUrl, thisHost = request.host)
        if x is None:
            return response.Response(status=404)

        return XMLResponse(xobj.toxml(x, None))

class GetFile(RestController):

    modelName = "fileId"
    urls = { 'info' : { 'GET' : 'info' },
             'content' : { 'GET' : 'content' }}

    def info(self, request, cu, roleIds = None, fileId = None, **kwargs):
        path = request.GET.get('path', None)
        x = repquery.getFileInfo(cu, roleIds, fileId, mkUrl = request.makeUrl,
                                 path = path)
        if x is None:
            return response.Response(status=404)

        return XMLResponse(xobj.toxml(x, None))

    def content(self, request, cu, roleIds = None, fileId = None,
                repos = None, **kwargs):
        sha1, isConfig = repquery.getFileSha1(cu, roleIds, fileId)
        if sha1 is None:
            return response.Response(status=404)

        localPath = repos.repos.contentsStore.hashToPath(sha1)
        if request.unparsedPath:
            remotePath = os.path.basename(request.unparsedPath)
        else:
            remotePath = sha1
        return FileResponse(localPath, gzipped=True, remotePath=remotePath,
                download=not isConfig)

class GetLogFile(RestController):

    modelName = "fileId"

    def get(self, request, cu, roleIds = None, fileId = None,
            repos = None, **kwargs):
        sha1, isConfig = repquery.getFileSha1(cu, roleIds, fileId)
        if sha1 is None:
            return response.Response(status=404)

        localPath = repos.repos.contentsStore.hashToPath(sha1)
        bzippedFile = gzip.GzipFile(localPath, "r")
        uncompressedFile = util.BZ2File(bzippedFile)

        return CompressFileResponse(uncompressedFile)

class Controller(RestController):

    urls = { 'node'         : GetNode,
             'trove'        : GetTrove,
             'troves'       : GetTroves,
             'file'         : GetFile,
             'logfile'      : GetLogFile }

    def index(self, request, cu = None, roleIds = None, *args, **kwargs):
        l = repquery.getRepository(cu, roleIds, mkUrl = request.makeUrl)
        return XMLResponse(xobj.toxml(l, None))

