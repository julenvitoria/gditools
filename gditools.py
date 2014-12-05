#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    gditools, a python library to extract files, sorttxt.txt and 
    bootsector (ip.bin) from SEGA Gigabyte Disc (GD-ROM) dumps.
    
    FamilyGuy 2014
        
    
    gditools.py and provided examples are licensed under the GNU
    General Public License (version 3), a copy of which is provided
    in the licences folder: GNU_GPL_v3.txt

    
    Original iso9660.py by Barney Gale : github.com/barneygale/iso9660
    iso9660.py is licensed under a BSD license, a copy of which is 
    provided in the licences folder: iso9660_licente.txt
"""

import os
from iso9660 import ISO9660 as _ISO9660_orig
from struct import unpack
from datetime import datetime
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


# TODO TODO TODO
#
#   - Write main
#   - Release it?
#
# TODO TODO TODO



class ISO9660(_ISO9660_orig):
    """
    Modification to iso9660.py to easily handle GDI files 
    
    """
    
    ### Overriding Functions of original class in this section

    def __init__(self, *args, **kwargs):
        # We obviously override the init to add support for our modifications
        self._dict1 = args[0]
        self._dirname = os.path.dirname(self._dict1['filename'])
        self._dict2 = None
        if len(args) > 1:
            if type(args[1]) == type({}):
                self._dict2 = args[1]

        self._gdifile = AppendedFiles(self._dict1, self._dict2)

        _ISO9660_orig.__init__(self, 'url') # So url doesn't starts with http

        if kwargs.has_key('verbose'):
            self._verbose = kwargs.pop('verbose')
        else:
            self._verbose = False


    
    ### Overriding this function allows to parse AppendedFiles as isos
    
    def _get_sector_file(self, sector, length): 
        # A big performance improvement versus re-opening the file for each
	# read as in the original ISO9660 implementation.
        self._gdifile.seek(sector*2048)
        self._buff = StringIO(self._gdifile.read(length))


    ### NEW FUNCTIONS FOLLOW ###

    def get_record(self, path):
        path = path.upper().strip('/').split('/')
        path, filename = path[:-1], path[-1]

        if len(path)==0:
            parent_dir = self._root
        else:
            parent_dir = self._dir_record_by_root(path)

        f = self._search_dir_children(parent_dir, filename)
        return f


    def gen_records(self, get_files = True):
        gen = self._tree_nodes_records(self._root)
        for i in gen:
            if get_files:
                yield i
            elif i['flags'] == 2:
                yield i 


    def _tree_nodes_records(self, node):
        spacer = lambda s: dict(
                    {j:s[j] for j in [i for i in s if i != 'name']}.items(),
                    name = "%s/%s" % (node['name'].lstrip('\x00\x01'), 
                    s['name']))
        for c in list(self._unpack_dir_children(node)):
            yield spacer(c)
            if c['flags'] & 2:
                for d in self._tree_nodes_records(c):
                    yield spacer(d)

    def get_pvd(self):
        return self._pvd

    def get_volume_name(self):
        return self.get_pvd()['volume_identifier']

    def print_files(self):
        for i in self.tree():
            print i


    def get_bootsector(self, lba = 45000):
        self._get_sector(lba, 16*2048)
        return self._unpack_raw(16*2048)


    def get_file_by_record(self, filerec):
        self._get_sector(filerec['ex_loc'], filerec['ex_len'])
        return self._unpack_raw(filerec['ex_len'])


    def get_sorttxt(self, crit='ex_loc', prefix='data', dummy='0.0'):
        """
        prefix : Folder that will be created in the pwd.
                 Default: 'data'

        dummy : Name of the dummy file to be put in the sorttxt
                Set to False not to use a dummy file
                Default: '0.0'

        crit : (criterion) can be any file record entry
               Default: 'ex_loc'    (LBA)

        If the first letter of crit is uppercase, order is reversed

        e.g.

        'ex_loc' or 'EX_LOC'    ->    Sorted by LBA value.
        'name' or 'NAME'        ->    Sorted by file name.
        'ex_len' or 'EX_LEN'    ->    Sorted by file size.
        

        Note: First file in sorttxt represents the last one on disc.

        e.g.

        - A sorttxt representing the file order of the source iso:
            self.get_sorted(crit='ex_loc')

        - A sorttxt with BIGGEST files at the outer part of disc:
            self.get_sorted(crit='ex_len')

        - A sorttxt with SMALLEST files at the outer part of disc:
            self.get_sorted(criterion='EX_LEN')
        """
        return self._sorttxt_from_records(self._sorted_records(crit=crit),
                                     prefix=prefix, dummy=dummy)


    def _sorted_records(self, crit='ex_loc'):
        file_records = [i for i in self.gen_records()]
        for i in self.gen_records(get_files = False):
            file_records.pop(file_records.index(i))  # Strips directories
        reverse = crit[0].islower()
        crit = crit.lower()
        ordered_records = sorted(file_records, key=lambda k: k[crit], 
                                 reverse = reverse)
        return ordered_records


    def _sorttxt_from_records(self, records, prefix='data', dummy='0.0'):
        sorttxt=''
        newline = '{prefix}{filename} {importance}\r\n'
        for i,f in enumerate(records):
            sorttxt += newline.format(prefix=prefix, filename=f['name'],
                                      importance = i+1)
        if dummy:
            if not dummy[0] == '/': 
                dummy = '/' + dummy
            sorttxt += newline.format(prefix=prefix, filename=dummy,
                                      importance=len(records)+1)
        return sorttxt


    def dump_sorttxt(self, filename='sorttxt.txt', **kwargs):
        if not filename[0] == '/': # Paths rel. to gdi folder unless full paths
            filename = self._dirname + '/' + filename
        with open(filename, 'wb') as f:
            if self._verbose: 
                print('Dumping sorttxt to {}'.format(filename))
            f.write(self.get_sorttxt(**kwargs))

    def dump_bootsector(self, filename='ip.bin'):
        if not filename[0] == '/': # Paths rel. to gdi folder unless full paths
            filename = self._dirname + '/' + filename
        with open(filename, 'wb') as f:
            if self._verbose: 
                print('Dumping bootsector to {}'.format(filename))
            f.write(self.get_bootsector())

    def dump_file_by_record(self, rec, target = '.', keep_timestamp = True,
                            filename = None):
        """
        rec: Record of a file in the filesystem
        target: Directory target to dump file into
        keep_timestamp: Uses timestamp in fs for dumped file
        filename: *None* -> Uses name in fs, else it overrides filename
        """
        if not target[-1] == '/': target += '/'
        # User provided filename overrides records's subfolders & name
        if filename:
            filename = target + filename.strip('/') 
        else: 
            filename = target + rec['name'].strip('/')

        if rec['flags'] == 2:
            # So os.path.isdirname yields right value for dir records
            filename += '/' 
        
        path = os.path.dirname(filename)
        if not os.path.exists(path):
            # Creates required dirs, including empty ones
            os.makedirs(path)   
            if self._verbose: 
                tmp_str = 'Created directory: {}'.format(path)
                print(tmp_str + ' '*(80-len(tmp_str)))

        if rec['flags'] != 2:   # If rec doesn't represents a directory
            message = 'Dumping {} to {}    ({}, {})'
            with open(filename, 'wb') as f:
                if self._verbose: 
                    UpdateLine(message.format(rec['name'].split('/')[-1],
                                              filename, rec['ex_loc'],
                                              rec['ex_len']))

                f.write(self.get_file_by_record(rec))
            if keep_timestamp:
                os.utime(filename, (self._get_timestamp_by_record(rec),)*2)


    def dump_file(self, name, **kwargs):
        self.dump_file_by_record(self.get_record(name), **kwargs)


    def dump_all_files(self, target='data', **kwargs): 
        # target has a default value not to accidentally fill dev folder 
        # Sorting according to LBA to avoid too much skipping on HDDs

        if not target[0] == '/': # Paths rel. to gdi folder unless full paths
            target = self._dirname + '/' + target
        try:
            for i in self._sorted_records(crit='ex_loc'):
                self.dump_file_by_record(i, target = target, **kwargs)

            if self._verbose:
                UpdateLine('All files were dumped successfully.')

        except:
            if self._verbose:
                UpdateLine('There was an error dumping all files.')


    def get_time_by_record(self, rec):
        tmp = datetime.fromtimestamp(self._get_timestamp_by_record(rec))
        return tmp.strftime('%Y-%m-%d %H:%M:%S (localtime)')


    def get_time(self, filename):
        return self.get_time_by_record(self.get_record(filename))


    def _get_timestamp_by_record(self, rec):
        date = rec['datetime']
        t = [unpack('<B', i)[0] for i in date[:-1]]
        t.append(unpack('<b', date[-1])[0])
        t[0] += 1900
        t_timestamp = self._datetime_to_timestamp(t)
        return t_timestamp
    
    def _datetime_to_timestamp(self, t):
        epoch = datetime(1970, 1, 1)
        timez = t.pop(-1) * 15 * 60. 
        # timez: Offset from GMT in 15 min intervals converted to secs
        T = (datetime(*t)-epoch).total_seconds()
        return T - timez



class GDIfile(ISO9660): 
    """
    Returns a class that represents a gdi dump of a GD-ROM.
    It should be initiated with a string pointing to a gdi file.

    Boolean kwarg *verbose* enables printing infos on what's going on.

    e.g.
    gdi = gdifile('disc.gdi')
    gdi.dump_all_files()
    """
    def __init__(self, filename, **kwargs): # Isn't OO programming wonderful?
        verbose = kwargs['verbose'] if kwargs.has_key('verbose') else False 
        ISO9660.__init__(self, *parse_gdi(filename, verbose=verbose), **kwargs)




class CdImage(file):
    """
    Class that allows opening a 2352 or 2048 bytes/sector data cd track
    as a 2048 bytes/sector one.
    """
    def __init__(self, filename, mode = 'auto', *args, **kwargs):

        if mode == 'auto':
            if filename[-4:] == '.iso': mode = 2048
            elif filename[-4:] == '.bin': mode = 2352

        elif not mode in [2048, 2352]:
            raise ValueError('Argument mode should be either 2048 or 2352')
        self.__mode = mode

        if (len(args) > 0) and (args[0] not in ['r','rb']):
            raise NotImplementedError('Only read mode is implemented.')

        file.__init__(self, filename, 'rb')

        file.seek(self,0,2)
        if self.__mode == 2352:
            self.length = file.tell(self) * 2048/2352
        else:
            self.length = file.tell(self)
        file.seek(self,0,0)

        self.seek(0)

    def realOffset(self,a):
        return a/2048*2352 + a%2048 + 16

    def seek(self, a, b = 0):
        if self.__mode == 2048:
            file.seek(self, a, b)

        elif self.__mode == 2352:
            if not type(a) == type(0):
                raise TypeError('First argument must be an integer!')

            if b == 0:
                self.binpointer = a
            if b == 1:
                self.binpointer += a
            if b == 2:
                self.binpointer = self.length - a

            realpointer = self.realOffset(self.binpointer)
            file.seek(self, realpointer, 0)

    def read(self, length = None):
        if self.__mode == 2048:
            return file.read(self, length)

        elif self.__mode == 2352:
            if length == None:
                length = self.length - self.binpointer

            # Amount of bytes left until beginning of next sector
            tmp = 2048 - self.binpointer % 2048    
            FutureOffset = self.binpointer + length
            realLength = self.realOffset(FutureOffset) - \
                            self.realOffset(self.binpointer)
            # This will (hopefully) accelerates readings on HDDs at the
            # cost of more memory use.
            buff = StringIO(file.read(self, realLength)) 
            data = ''
            while length:
                piece = min(length, tmp)
                tmp = 2048  # Allows first piece <1 sector if need be
                data += buff.read(piece)
                length -= piece
                # If we're not done reading, it means we reached the 
                # end of a sector and we should skip to the beginning 
                # of the next one.
                if not length == 0: 
                    buff.seek(304,1) 
                    # Seeking to beginning of next sector, jumping over
                    # EDC/ECC of current and header of next sectors.
            self.seek(FutureOffset)
            return data

    def tell(self):
        if self.__mode == 2048:
            return file.tell(self)

        elif self.__mode == 2352:
            return self.binpointer



class OffsetedFile(CdImage):
    """
    Like a file, but offsetted! Padding is made of 0x00.

    READ ONLY: trying to open a file in write mode will raise a 
    NotImplementedError
    """
    def __init__(self, filename, *args, **kwargs):

        if kwargs.has_key('offset'):
            self.offset = kwargs.pop('offset')
        else:
            self.offset = 0

        if (len(args) > 0) and (args[0] not in ['r','rb']):
            raise NotImplementedError('Only read mode is implemented.')

        CdImage.__init__(self, filename, **kwargs)
        
        CdImage.seek(self,0,2)
        self.length = CdImage.tell(self)
        CdImage.seek(self,0,0)

        self.seek(0)


    def seek(self, a, b = 0):
        if b == 0:
            self.pointer = a
        if b == 1:
            self.pointer += a
        if b == 2:
            self.pointer = self.length + self.offset - a

        if self.pointer > self.offset:
            CdImage.seek(self, self.pointer - self.offset)
        else:
            CdImage.seek(self, 0)


    def read(self, length = None):
        if length == None:
            length = self.offset + self.length - self.pointer
        tmp = self.pointer
        FutureOffset = self.pointer + length
        if tmp >= self.offset:
            #print 'AFTER OFFSET'
            self.seek(tmp)
            data = CdImage.read(self, length)
        elif FutureOffset < self.offset:
            #print 'BEFORE OFFSET'
            data = '\x00'*length
        else:
            #print 'CROSSING OFFSET'
            preData = '\x00'*(self.offset - tmp)
            self.seek(self.offset)
            postData = CdImage.read(self, FutureOffset - self.offset)
            data = preData + postData
        self.seek(FutureOffset)
        return data


    def tell(self):
        return self.pointer



class WormHoleFile(OffsetedFile):
    """
    Redirects an offset-range to another offset in a file. Because 
    everbody likes wormholes. 

    I even chose that name before WH were mainsteam (Interstellar)
    """
    def __init__(self, *args, **kwargs):

        # *wormhole* should be [target_offset, source_offset, wormlen]
        # target_offset + wormlen < source_offset
        
        if kwargs.has_key('wormhole'):
            self.target, self.source, self.wormlen = kwargs.pop('wormhole')
        else:
            self.target, self.source, self.wormlen = [0,0,0]

        OffsetedFile.__init__(self, *args, **kwargs)


    def read(self, length = None):

        if length == None:
            length = self.offset + self.length - self.pointer
        tmp = self.pointer
        FutureOffset = self.pointer + length

        # If we start after the wormhole or if we don't reach it, 
        # everything is fine
        if (tmp >= self.target + self.wormlen) or (FutureOffset < self.target):
            # print 'OUT OF WORMHOLE'
            data = OffsetedFile.read(self, length)

        # If we start inside the wormhole, it's trickier        
        elif tmp >= self.target:
            # print 'START INSIDE'
            # Through the wormhole to the source
            self.seek(tmp - self.target + self.source)  

            # If we don't exit the wormhole, it's somewhat simple
            if FutureOffset < self.target + self.wormlen: 
                # print 'DON\'T EXIT IT'
                data = OffsetedFile.read(self, length) # Read in the source

            # If we exit the wormhole midway, it's even trickier
            else:   
                # print 'EXIT IT'
                inWorm_len = self.target + self.wormlen - tmp
                outWorm_len = FutureOffset - self.target - self.wormlen
                inWorm = OffsetedFile.read(self, inWorm_len)
                self.seek(self.target + self.wormlen)
                outWorm = OffsetedFile.read(self, outWorm_len)
                data = inWorm + outWorm

        # If we start before the wormhole then hop inside, it's also 
        # kinda trickier
        elif FutureOffset < self.target + self.wormlen: 
            # print 'START BEFORE, ENTER IT'
            preWorm_len = self.target - tmp
            inWorm_len = FutureOffset - self.target
            preWorm = OffsetedFile.read(self, preWorm_len)
            self.seek(self.source)
            inWorm = OffsetedFile.read(self, inWorm_len)
            data = preWorm + inWorm

        # Now if we start before the wormhole and jump over it, it's 
        # the trickiest
        elif FutureOffset > self.target + self.wormlen:
            # print 'START BEFORE, END AFTER'
            preWorm_len = self.target - tmp
            inWorm_len = self.wormlen
            postWorm_len = FutureOffset - self.target - self.wormlen

            preWorm = OffsetedFile.read(preWorm_len)
            self.seek(self.source)
            inWorm = OffsetedFile.read(inWorm_len)
            self.seek(self.target + inWorm_len)
            postWorm = OffsetedFile.read(postWorm_len)

            data = preWorm + inWorm + postWorm
        

        # Pretend we're still where we should, in case we went where we
        # shouldn't have!
        self.seek(FutureOffset)     
        return data



class AppendedFiles():
    """
    Two WormHoleFiles one after another. 
    Takes 1 or 2 dict(s) as arguments; they're passed to WormHoleFiles'
    at the init.

    This is aimed at merging the TOC track starting at LBA45000 with 
    the last one to mimic one big track at LBA0 with the files at the 
    same LBA than the GD-ROM.
    """
    def __init__(self, wormfile1, wormfile2 =  None, *args, **kwargs):

        self._f1 = WormHoleFile(**wormfile1)

        self._f1.seek(0,2)
        self._f1_len = self._f1.tell()
        self._f1.seek(0,0)

        self._f2_len = 0
        if wormfile2:
            self._f2 = WormHoleFile(**wormfile2)

            self._f2.seek(0,2)
            self._f2_len = self._f2.tell()
            self._f2.seek(0,0)
        else:
            # So the rest of the code works for one or 2 files.
            self._f2 = StringIO('') 

        self.seek(0,0)


    def seek(self, a, b=0):
        if b == 0:
            self.MetaPointer = a
        if b == 1:
            self.MetaPointer += a
        if b == 2:
            self.MetaPointer = self._f1_len + self._f2_len - a

        if self.MetaPointer >= self._f1_len:
            self._f1.seek(0, 2)
            self._f2.seek(a - self._f1_len, 0)
        else:
            self._f1.seek(a, 0)
            self._f2.seek(0, 0)


    def read(self, length = None):
        if length == None:
            length = self._f1_len + self._f2_len - self.MetaPointer
        tmp = self.MetaPointer
        FutureOffset = self.MetaPointer + length
        if FutureOffset < self._f1_len: # Read inside file1
            data = self._f1.read(length)
        elif tmp > self._f1_len:        # Read inside file2
            data = self._f2.read(length)
        else:                           # Read end of file1 and start of file2
            data = self._f1.read(self._f1_len - tmp)
            data += self._f2.read(FutureOffset - self._f1_len)

        self.seek(FutureOffset) # It might be enough to just update 
                                # self.MetaPointer, but this is safer.
        return data
            

    def tell(self):
        return self.MetaPointer


    def __enter__(self):
        return self


    def __exit__(self, type=None, value=None, traceback=None):  
        # This is required to close files properly when using the with
        # statement. Which isn't required by ISO9660 anymore, but could
        # be useful for other uses so it stays!
        self._f1.__exit__()
        if self._f2_len:
            self._f2.__exit__()



def parse_gdi(filename, verbose = False):
    dirname = os.path.dirname(filename)
    a = dict(offset = 45000*2048, wormhole = [0, 45000*2048, 16*2048])
    # track03 always have these offsets and wormhole

    with open(filename) as f: # if i.split() removes blank lines
        l = [i.split() for i in f.readlines() if i.split()]
    if not int(l[3][1]) == 45000:
        raise AssertionError('Invalid gdi file: track03 LBA should be 45000')

    nbt = int(l[0][0])
    a['filename'] = dirname + '/' + l[3][4]
    a['mode'] = int(l[3][3])

    if nbt > 3:
        b = dict(filename=dirname + '/' + l[nbt][4], mode=int(l[nbt][3]),
                 offset = 2048*(int(l[nbt][1]) - 
                     (45000 + (get_filesize(a['filename'])/int(a['mode'])))) )
        ret = a,b
    else:
        ret = a,

    if verbose:
        print('\nParsed gdi file: {}'.format(os.path.basename(filename)))
        print('Base Directory:  {}'.format(dirname))
        print('Number of tracks:  {}'.format(nbt))
        for i,j in enumerate(ret):
            print('')
            print('{} track:'.format('DATA' if i==1 or len(ret)==1 else 'TOC'))
            print('\tFilename:  {}'.format(os.path.basename(j['filename'])))
            print('\tLBA:       {} '.format(l[3][1] if i == 0 else l[nbt][1]))
            print('\tMode:      {} bytes/sector'.format(j['mode']))
            print('\tOffset:    {}'.format(j['offset']/2048))
            if j.has_key('wormhole'):
                wh = [k/2048 for k in j['wormhole']]
            else:
                wh = 'None'
            print('\tWormHole:  {}'.format(wh))
    
    return ret


def get_filesize(filename):
    with open(filename) as f:
        f.seek(0,2)
        return f.tell()


def UpdateLine(text):
    """
    Allows to print successive messages over the last line. Line is 
    force to be 80 chars long to avoid display issues.
    """
    import sys
    if len(text) > 80:
        text = text[:80]
    if text[-1] == '\r':
        text = text[:-1]
    text += ' '*(80-len(text))+'\r'
    sys.stdout.write(text)
    sys.stdout.flush()


def _copy_buffered(f1, f2, bufsize = 1*1024*1024, closeOut = True):
    """
    Copy istream f1 into ostream f2 in bufsize chunks
    """
    f1.seek(0,2)
    length = f1.tell()
    f1.seek(0,0)
    f2.seek(0,0)

    while length:
        chunk = min(length, bufsize)
        length = length - chunk
        data = f1.read(chunk)
        f2.write(data)

    if closeOut:
        f2.close()




#def bin2iso(src, dest = None, bufsize = 1024*2048, outmode = 'wb', length_override = False):
#    """
#    A VERY stupid bin2iso implementation. Not dumb-proof AT ALL.
#    
#    It basically reads (blindly) a file in 2352 chunks and spits 2048 ones
#    ditching the first 16 and last 288 bytes of each input chunk. It should
#    be enough to provide a parseable iso and extract files/files-infos.
#
#    bufsize is floored to SECTORS, as it'd be stupid/complex to do otherwise.
#
#    bufsize of 1024 sectors was optimized on a SSD. Might be tuned for HDD.
#    Options outmode and length_override are meant to be used by isofix.
#    """
#    # TODO: Cuesheet support to skip audio tracks
#    bufsize=bufsize/2048
#
#    if dest == None:
#        if not src.find('.bin') == -1:
#            dest = src.replace('.bin','.iso')
#        elif not src.find('.BIN') == -1:
#            dest = src.replace('.BIN','.ISO')
#        else:
#            dest = src+'.iso'
#    elif dest.find('.iso') == -1:
#        dest=dest+'.iso'
#
#    with open(src,'rb') as BIN, open(dest,outmode) as ISO:
#        BIN.seek(0,2) 
#        if length_override:
#            length = length_override
#        else:
#            length = BIN.tell()/2352 # Get lenght of bin file, in sectors.
#        BIN.seek(16,0)      # Seeking here skips the 1st 16 bytes of sector 0
#        while length:
#            chunk = min(bufsize,length)
#            length = length-chunk
#            data=''
#            while chunk:
#                data+=BIN.read(2048)
#                BIN.seek(304,1) # Skips 288 last of current and 16 first of next sector.
#                chunk=chunk-1
#            ISO.write(data)
#
#
#def isofix(src, dest=None, LBA=45000, bufsize=1024*2048, source='iso'):
#    """
#    Bin files are converted to iso on the fly in the copy process.
#    """
#    # TODO: AutoDetect .bin via name. Autodetect .bin LBA via header
#    if not source.lower() in ['iso','bin']:
#        return -1
#
#    # This next line is ugly enough not to deserve explanation; it works though.
#    hasExtension=bool(src.find('.iso') + src.find('.ISO') + src.find('.bin') + src.find('.BIN') + 4)
#
#    if dest == None:
#        if (hasExtension):
#            dest = src[:-4]+'_fixed.iso'
#        else:
#            dest = src+'_fixed.iso'
#
#
#    # 1 - Writes bootsector (0-15), PVD (16) and SVD (17) to beginning of fixed iso
#    if source == 'iso':
#        with open(src,'rb') as old, open(dest,'wb') as fix:
#            fix.write(old.read(18*2048))
#    if source == 'bin':
#        bin2iso(src, dest, bufsize=bufsize, length_override=18)
#    
#    # 2 - Appends 0x00 to the file until LBA is reached
#    with open(src,'rb') as old, open(dest,'ab') as fix:
#        # Padding with zeros until LBA to fixed to
#        length = (LBA-18)*2048
#        while length:
#            chunk = min(length,bufsize)
#            length=length-chunk
#            fix.write('\x00'*chunk)
#
#    # 3 - Appends the source iso to the dest iso
#    if source == 'iso':
#        with open(src,'rb') as old, open(dest,'ab') as fix:
#            # Get length of source iso
#            old.seek(0,2)
#            length=old.tell()
#            old.seek(0,0) # Return to beginning ready to be all read
#
#            # Append source iso to end of prepared file
#            while length:
#                chunk = min(length,bufsize)
#                length=length-chunk
#                fix.write(old.read(chunk))
#    if source == 'bin':
#        bin2iso(src, dest, bufsize=bufsize, outmode='ab')







