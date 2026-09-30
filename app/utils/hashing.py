import hashlib

def generate_record_hash(values: list) -> str:
    normalized = "|".join(
        "" if value is None else str(value).strip()
        for value in values
    )
    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

def generate_file_hash(filepath: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
