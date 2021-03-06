"""
The FileMgr reads and writes the set of torrent files.  If the files exist, it
opens them and creates a bitfield to reflect which pieces are present (not
implemented).  If not, it creates the files.  The FileMgr maps locations 
in the set of pieces to where they appear in the files and vice versa.
"""

import errno
import logging
import os
from bitstring import BitArray

logger = logging.getLogger('bt.filemgr')

class FileMgr(object):
    def __init__(self, metainfo):
        self._metainfo = metainfo 
        self._have = BitArray(self._metainfo.num_pieces)

        directory = metainfo.directory
        if directory != '':
            try:
                if not os.path.exists(directory):
                    os.makedirs(directory)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

        files =  metainfo.files

        self._files = []

        offset = 0
        subdirs = []
        for path, length in files:
            dirname = directory+"/".join(path[0:-1])

            if dirname != '' and dirname not in subdirs:
                subdirs.append(dirname)
                try:
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                except OSError as err:
                    if err.errno != errno.EEXIST:
                        raise
                
            if dirname == '':
                filename = path[-1]
            else:
                filename = dirname+"/"+path[-1]

            try:
                open(filename, 'a').close()
                fd = open(filename,'rb+')
            except IOError:
                logger.critical("Unable to open file {}".format(filename))
                raise 

            self._files.append((fd, length, offset))
            offset += length

    def _file_index(self, offset):
        for i, (fd, length, begin) in enumerate(self._files):
            if offset >= begin and offset < begin + length:
                return i

    def have(self):
        return self._have.copy()

    def write_block(self, piece_index, offset_in_piece, buf, file_index=None):
        offset_in_torrent = (piece_index * self._metainfo.piece_length + 
                             offset_in_piece)

        if file_index == None:
            file_index = self._file_index(offset_in_torrent)
        fd, file_length, file_offset_in_torrent = self._files[file_index] 
        offset_in_file = offset_in_torrent - file_offset_in_torrent
        fd.seek(offset_in_file)
        if len(buf) <= file_length - offset_in_file:
            fd.write(buf)
        else:
            to_write = file_length - offset_in_file
            fd.write(buf[:to_write])
            self.write_block(piece_index, offset_in_piece + to_write,
                        buf[to_write:], file_index+1)

    def flush(self): 
        for fd, _, _ in self._files:
            fd.flush()

        
        
