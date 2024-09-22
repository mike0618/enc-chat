from rsa import encrypt, decrypt


def rsa_enc(bytez: bytes, key):
    result = b""
    for n in range(0, len(bytez), 117):
        part = bytez[n : n + 117]
        result += encrypt(part, key)
    return result


def rsa_decr(bytez: bytes, key):
    result = b""
    for n in range(0, len(bytez), 128):
        part = bytez[n : n + 128]
        result += decrypt(part, key)
    return result
