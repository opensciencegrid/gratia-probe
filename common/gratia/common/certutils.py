
from OpenSSL import crypto

##
## Certificate handling routine
##
def createKeyPair(keytype, bits):
    """
    Create a public/private key pair.

    Arguments: keytype - Key type, must be one of TYPE_RSA and TYPE_DSA
               bits - Number of bits to use in the key
    Returns:   The public/private key pair in a PKey object
    """

    pkey = crypto.PKey()
    pkey.generate_key(keytype, bits)
    return pkey


def createCertRequest(pkey, digest='md5', **name):
    """
    Create a certificate request.

    Arguments: pkey   - The key to associate with the request
               digest - Digestion method to use for signing, default is md5
               **name - The name of the subject of the request, possible
                        arguments are:
                          C     - Country name
                          ST    - State or province name
                          L     - Locality name
                          O     - Organization name
                          OU    - Organizational unit name
                          CN    - Common name
                          emailAddress - E-mail address
    Returns:   The certificate request in an X509Req object
    """

    req = crypto.X509Req()
    subj = req.get_subject()
    for (key, value) in name.items():
        setattr(subj, key, value)
    req.set_pubkey(pkey)
    req.sign(pkey, digest)
    return req


def createCertificate(
    req,
    issuerCert__issuerKey,
    serial,
    notBefore__notAfter,
    digest='md5',
    ):
    """
    Generate a certificate given a certificate request.

    Arguments: req        - Certificate reqeust to use
               issuerCert - The certificate of the issuer
               issuerKey  - The private key of the issuer
               serial     - Serial number for the certificate
               notBefore  - Timestamp (relative to now) when the certificate
                            starts being valid
               notAfter   - Timestamp (relative to now) when the certificate
                            stops being valid
               digest     - Digest method to use for signing, default is md5

    Note: two arguments are provided as tuples:
        (issuerCert, issuerKey) = issuerCert__issuerKey
        (notBefore, notAfter)   = notBefore__notAfter
    Returns:   The signed certificate in an X509 object
    """
    (issuerCert, issuerKey) = issuerCert__issuerKey
    (notBefore, notAfter) = notBefore__notAfter
    cert = crypto.X509()
    cert.set_serial_number(serial)
    cert.gmtime_adj_notBefore(notBefore)
    cert.gmtime_adj_notAfter(notAfter)
    cert.set_issuer(issuerCert.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.sign(issuerKey, digest)
    return cert

