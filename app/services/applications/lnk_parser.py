"""Binary parser for Windows Shell Link (.lnk) shortcut files."""

import os

def resolve_lnk_binary(filepath: str) -> str | None:
    """Parses a .lnk file binary structure to extract the local base path target.

    Args:
        filepath: Absolute path to the shortcut file.

    Returns:
        str | None: The resolved target executable path, or None if invalid.
    """
    try:
        if not os.path.isfile(filepath):
            return None
            
        with open(filepath, 'rb') as f:
            data = f.read()
        
        if len(data) < 0x4C:
            return None
            
        header_size = int.from_bytes(data[0:4], byteorder='little')
        if header_size != 0x4C:
            return None
            
        flags = int.from_bytes(data[20:24], byteorder='little')
        has_link_target_id_list = bool(flags & 0x01)
        has_link_info = bool(flags & 0x02)
        
        offset = 0x4C
        if has_link_target_id_list:
            if offset + 2 > len(data):
                return None
            id_list_size = int.from_bytes(data[offset:offset+2], byteorder='little')
            offset += 2 + id_list_size
            
        if has_link_info:
            if offset + 4 > len(data):
                return None
            link_info_start = offset
            link_info_size = int.from_bytes(data[offset:offset+4], byteorder='little')
            if offset + link_info_size > len(data):
                return None
                
            local_base_path_offset = int.from_bytes(data[link_info_start+16:link_info_start+20], byteorder='little')
            
            if local_base_path_offset != 0:
                path_start = link_info_start + local_base_path_offset
                path_end = data.find(b'\x00', path_start)
                if path_end != -1:
                    path = data[path_start:path_end].decode('utf-8', errors='ignore')
                    return path
    except Exception:
        pass
    return None
