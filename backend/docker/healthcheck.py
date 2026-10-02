import http.client
import json
import os


def main():
    try:
        port = int(os.environ.get("PORT", "8000"))
        allowed_hosts = os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
        host = next(host.strip().lstrip(".") for host in allowed_hosts if host.strip())
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        connection.request(
            "GET",
            "/api/v1/health/",
            headers={"Host": host},
        )
        response = connection.getresponse()
        payload = json.loads(response.read(1024))
    except (
        KeyError,
        OSError,
        StopIteration,
        ValueError,
        http.client.HTTPException,
        json.JSONDecodeError,
    ):
        raise SystemExit(1) from None
    finally:
        if "connection" in locals():
            connection.close()

    if response.status != 200 or payload != {"status": "ok"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
