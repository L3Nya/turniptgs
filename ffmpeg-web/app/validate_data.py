import hashlib
import hmac


def validate(bot_token, params):
    secret_key = hmac.new(
        "WebAppData".encode(), bot_token.encode(), hashlib.sha256
    ).digest()
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items(), key=lambda x: x[0]) if k != "hash"
    )
    hsh = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    assert hsh == params["hash"], "Wrong hash"
