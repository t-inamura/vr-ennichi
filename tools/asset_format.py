"""Version 2 derived format: little-endian indexed position/normal/linear RGBA."""
import struct

def pack_chunk(raw):
    if len(raw) % 120:
        raise ValueError('Expected complete triangles of 3 x 40-byte vertices')
    vertices = bytearray(); indices = bytearray(); lookup = {}
    for offset in range(0, len(raw), 40):
        vertex = bytes(raw[offset:offset+40])
        index = lookup.get(vertex)
        if index is None:
            index = len(lookup); lookup[vertex] = index; vertices.extend(vertex)
        indices.extend(struct.pack('<I', index))
    count = len(lookup)
    return count, struct.pack('<II', count, len(raw)//40) + vertices + indices
