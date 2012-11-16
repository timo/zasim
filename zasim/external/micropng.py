"""This module offers a PNG parser that does nothing but parse
text segments."""

import struct

png_intro = "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"

chunk_format = struct.Struct("!I4s")

def enumerate_chunks(pngfile_or_filename):
    if isinstance(pngfile_or_filename, basestring):
        pngfile = open(pngfile_or_filename, "r")

    assert pngfile.read(len(png_intro)) == png_intro

    while True:
        values = pngfile.read(chunk_format.size)
        size, chunktype = chunk_format.unpack(values)
        content = bytes(pngfile.read(size))
        crc = pngfile.read(4)
        yield size, chunktype, content, crc
        if chunktype == "IEND":
            return

def fieldgetter(*fields):
    def getter(pngfile_or_filename):
        """This function yields all fields of the %s type from the
        png file given as a filename or file-like object.""" % (",".join(fields))
        for size, chunktype, content, _ in enumerate_chunks(pngfile_or_filename):
            if chunktype in fields:
                yield chunktype, content

    return getter

textgetter = fieldgetter("iTXt", "tEXt")

def get_description(pngfile_or_filename):
    """Gets the tExt or iTxt "Description" chunk content"""
    print "getting the description"
    for chunktype, content in textgetter(pngfile_or_filename):
        if chunktype == "iTXt":
            content = content.decode("utf8")
        elif chunktype == "tEXt":
            content = content.decode("latin1")
        else:
            continue
        tag, content = content.split("\0")

        if tag == "Description":
            return content
