from rsa import encrypt, decrypt
import pickle


def rsa_enc(data, key):
    result = b""
    bytez = pickle.dumps(data)
    for n in range(0, len(bytez), 117):
        part = bytez[n : n + 117]
        result += encrypt(part, key)
    return result


def rsa_decr(bytez: bytes, key):
    result = b""
    for n in range(0, len(bytez), 128):
        part = bytez[n : n + 128]
        result += decrypt(part, key)
    if result:
        return pickle.loads(result)
