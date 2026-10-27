import uuid
import uuid6


def generate_uuid7() -> uuid.UUID:
    """Generate a time-ordered UUIDv7 (RFC 9562).

    UUIDv7 embeds a 48-bit Unix timestamp prefix, guaranteeing that
    new records are appended sequentially in B-Tree indexes, drastically
    reducing page fragmentation and disk I/O compared to UUIDv4.
    """
    return uuid6.uuid7()
