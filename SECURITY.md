# Practice 3 security

## Certificate authentication and session keys

1. The client connects and starts a TLS 1.3 handshake. It verifies the
   server's chain against `ca.pem` and checks the hostname or address in the
   certificate's Subject Alternative Name.
2. The server requires a client certificate. It verifies the certificate
   against `ca.pem` and checks the certificate's validity and client-authentication
   usage. TLS signatures prove both peers hold their respective private keys.
3. During the handshake, ephemeral Diffie–Hellman establishes a shared
   secret. TLS derives symmetric traffic keys and authenticates the
   handshake before either peer exchanges application frames. The server
   disables session tickets so clients authenticate on each connection.
4. TLS records carry the JSON frames using the negotiated authenticated
   cipher, such as `TLS_AES_256_GCM_SHA384`. The receiver verifies record
   integrity before handing data to the JSON protocol.

The wire protocol is newline-delimited JSON over TCP. The HTTP digest header
in the REST requirement applies to HTTP deployments. This version keeps the
JSON/TCP protocol and uses TLS authenticated encryption for confidentiality
and integrity. [TLS 1.3 specification](https://www.rfc-editor.org/rfc/rfc8446)

## Certificate files

| Files | Role |
| --- | --- |
| `ca.pem` | Trusted root certificate loaded by both programs |
| `ca.key` | CA signing key used for certificate issuance |
| `server.pem`, `server.key` | Server identity for `localhost`, `127.0.0.1`, and `::1` |
| `client-one.pem`, `client-one.key` | First client identity |
| `client-two.pem`, `client-two.key` | Second client identity |

The two client certificates have separate private keys and serial numbers.
Both have the same CRUD permissions after authentication. The trusted CA
controls which client identities can connect. The server certificate and
client certificates have separate extended key usages. Lab certificates
expire after 30 days and the CA certificate after 365 days. Keep the CA
signing key and each endpoint's private key with their respective owners.

## Verification

Run the server and the two client commands in [README.md](README.md). The
server logs the verified certificate subject for each connection. To check
that the server requires a client certificate, connect with OpenSSL using
only the CA certificate. After the TLS attempt, the server rejects the client
with a certificate-required alert and the router receives no request.

```powershell
openssl s_client -connect 127.0.0.1:5050 -CAfile certs/ca.pem -verify_ip 127.0.0.1 -verify_return_error -tls1_3
```

The integration tests exercise both valid clients, the absence of a client
certificate, a client certificate signed by an unrelated CA, and a server
hostname mismatch. TLS handshake errors are handled by Python's `ssl`
integration in asyncio. [Python TLS documentation](https://docs.python.org/3/library/ssl.html)
