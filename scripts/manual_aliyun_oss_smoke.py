from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys
from urllib import request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.knowact.authoring.sources import AliyunOSSConfig
from backend.knowact.llm.config import load_dotenv_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload a temporary text object to Aliyun OSS and verify its signed URL."
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Text content to upload. Defaults to a timestamped smoke-test string.",
    )
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=None,
        help="Signed URL lifetime. Defaults to KNOWACT_OSS_SIGNED_URL_TTL_SECONDS.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the uploaded object instead of deleting it after verification.",
    )
    args = parser.parse_args()

    load_dotenv_file()
    config = AliyunOSSConfig.from_env()
    ttl_seconds = args.ttl_seconds or config.signed_url_ttl_seconds
    text = args.text or (
        "KnowAct Aliyun OSS smoke test "
        f"{datetime.now(UTC).isoformat()} id={uuid.uuid4().hex}"
    )
    object_key = f"{config.object_prefix.strip('/')}/manual-smoke/{uuid.uuid4().hex}.txt"

    import oss2

    auth = oss2.Auth(config.access_key_id, config.access_key_secret)
    bucket = oss2.Bucket(auth, config.endpoint, config.bucket_name)

    print(f"Uploading object: {object_key}")
    bucket.put_object(object_key, text.encode("utf-8"), headers={"Content-Type": "text/plain; charset=utf-8"})

    signed_url = bucket.sign_url("GET", object_key, ttl_seconds)
    print(f"Signed URL valid for {ttl_seconds} seconds:")
    print(signed_url)

    try:
        with request.urlopen(signed_url, timeout=30) as response:
            downloaded = response.read().decode("utf-8")
    except Exception:
        if not args.keep:
            _delete_object(bucket, object_key)
        raise

    if downloaded != text:
        if not args.keep:
            _delete_object(bucket, object_key)
        raise RuntimeError("Downloaded text did not match uploaded text")

    print("Download verification succeeded.")
    if args.keep:
        print("Keeping uploaded object because --keep was set.")
    else:
        _delete_object(bucket, object_key)
        print("Deleted uploaded smoke-test object.")
    return 0


def _delete_object(bucket, object_key: str) -> None:
    bucket.delete_object(object_key)


if __name__ == "__main__":
    raise SystemExit(main())
