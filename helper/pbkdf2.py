# -*- coding: utf-8 -*-
import hmac
import hashlib
from base64 import b64encode, b64decode
from itertools import izip, starmap
from operator import xor
from os import urandom
from struct import Struct

def pbkdf2_bin(data, salt, iterations=1000, keylen=24, hashfunc=None):
    """Returns a binary digest for the PBKDF2 hash algorithm of `data`
    with the given `salt`.  It iterates `iterations` time and produces a
    key of `keylen` bytes.  By default SHA-1 is used as hash function,
    a different hashlib `hashfunc` can be provided.
    """
    _pack_int = Struct(">I").pack
    hashfunc = hashfunc or hashlib.sha1
    mac = hmac.new(data, None, hashfunc)

    def _pseudorandom(x, mac=mac):
        h = mac.copy()
        h.update(x)
        return map(ord, h.digest())
    buf = []
    for block in xrange(1, -(-keylen // mac.digest_size) + 1):
        rv = u = _pseudorandom(salt + _pack_int(block))
        for _ in xrange(iterations - 1):
            u = _pseudorandom("".join(map(chr, u)))
            rv = starmap(xor, izip(rv, u))
        buf.extend(rv)
    return "".join(map(chr, buf))[:keylen]

# Parameters to PBKDF2. Only affect new passwords.
SALT_LENGTH = 12
KEY_LENGTH = 24
HASH_FUNCTION = "sha256"  # Must be in hashlib.
# Linear to the hashing time. Adjust to be high but take a reasonable
# amount of time on your server. Measure with:
# python -m timeit -s "import passwords as p" "p.make_hash("something")"
COST_FACTOR = 1000

def pbkdf2(password):
    """Generate a random salt and return a new hash for the password."""
    if isinstance(password, unicode):
        password = password.encode("utf-8")
    salt = b64encode(urandom(SALT_LENGTH))
    return "PBKDF2${}${}${}${}".format(
        HASH_FUNCTION,
        COST_FACTOR,
        salt,
        b64encode(pbkdf2_bin(password, salt, COST_FACTOR, KEY_LENGTH,
                             getattr(hashlib, HASH_FUNCTION))))

def pbkdf2_check(raw_password, encrypted_passwd):
    """Check a password against an existing hash."""
    if isinstance(raw_password, unicode):
        raw_password = raw_password.encode("utf-8")
    algorithm, hash_function, cost_factor, salt, derived_key = encrypted_passwd.split("$")
    assert algorithm == "PBKDF2"
    derived_key = b64decode(derived_key)
    hash_b = pbkdf2_bin(raw_password, salt, int(cost_factor), len(derived_key),
                        getattr(hashlib, hash_function))
    assert len(derived_key) == len(hash_b)  # we requested thisfrom helper.pbkdf2_bin()
    # Same as "return hash_a == hash_b" but takes a constant time.
    # See http://carlos.bueno.org/2011/10/timing.html
    diff = 0
    for char_a, char_b in izip(derived_key, hash_b):
        diff |= ord(char_a) ^ ord(char_b)
    return diff == 0