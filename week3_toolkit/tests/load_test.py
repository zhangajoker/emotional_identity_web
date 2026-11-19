import argparse
import base64
import http.cookiejar
import json
import math
import statistics
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        data: bytes | None = None,
        content_type: str | None = None,
        timeout: float = 30,
    ) -> tuple[int, bytes]:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type

        request = urllib.request.Request(
            self.url(path),
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float = 30,
    ) -> tuple[int, bytes]:
        return self.request(
            path,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            timeout=timeout,
        )

    def register(self, username: str, password: str) -> int:
        status, body = self.post_json(
            "/api/auth/register",
            {
                "username": username,
                "display_name": f"Load {username[-5:]}",
                "password": password,
            },
        )
        if status != 201:
            raise RuntimeError(
                f"register failed: {status} {body[:200]!r}"
            )
        return int(json.loads(body)["user"]["id"])

    def login(self, username: str, password: str) -> None:
        status, body = self.post_json(
            "/api/auth/login",
            {
                "username": username,
                "password": password,
            },
        )
        if status != 200:
            raise RuntimeError(
                f"login failed: {status} {body[:200]!r}"
            )

    def create_chat_session(self) -> int:
        status, body = self.post_json("/api/chat/sessions", {})
        if status != 201:
            raise RuntimeError(
                f"chat session failed: {status} {body[:200]!r}"
            )
        return int(json.loads(body)["data"]["id"])

    def analyze_frame(
        self,
        image_data: bytes,
        filename: str,
        content_type: str,
        timeout: float,
    ) -> float:
        boundary = f"----emotion-{uuid.uuid4().hex}"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; '
            f'filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("ascii")
        body += image_data
        body += f"\r\n--{boundary}--\r\n".encode("ascii")

        started = time.perf_counter()
        status, response_body = self.request(
            "/api/analyze",
            method="POST",
            data=body,
            content_type=f"multipart/form-data; boundary={boundary}",
            timeout=timeout,
        )
        latency = time.perf_counter() - started
        if status != 200:
            raise RuntimeError(
                f"vision {status}: {response_body[:160]!r}"
            )
        return latency

    def social_feed(self, timeout: float) -> float:
        started = time.perf_counter()
        status, body = self.request(
            "/api/social/feed?limit=20",
            timeout=timeout,
        )
        latency = time.perf_counter() - started
        if status != 200:
            raise RuntimeError(f"feed {status}: {body[:160]!r}")
        return latency

    def chat_stream(
        self,
        session_id: int,
        timeout: float,
    ) -> tuple[float, float]:
        payload = json.dumps(
            {
                "content": (
                    "I feel tired today. Please reply briefly "
                    "with one supportive question."
                )
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url(
                f"/api/chat/sessions/{session_id}/messages/stream"
            ),
            data=payload,
            headers={
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        started = time.perf_counter()
        first_delta = None
        content = bytearray()

        try:
            response = self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"chat {exc.code}: {exc.read(160)!r}"
            ) from exc

        with response:
            while True:
                chunk = response.read(1024)
                if not chunk:
                    break

                content.extend(chunk)
                if first_delta is None and b"event: delta" in content:
                    first_delta = time.perf_counter()

        total = time.perf_counter() - started

        if b"event: done" not in content:
            raise RuntimeError("chat stream missing done event")

        return (first_delta or started) - started, total


@dataclass
class Worker:
    username: str
    password: str
    chat_session_id: int


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.samples: dict[str, list[float]] = defaultdict(list)
        self.errors: list[str] = []

    def record(self, category: str, latency: float) -> None:
        with self.lock:
            self.samples[category].append(latency)

    def error(self, message: str) -> None:
        with self.lock:
            if len(self.errors) < 50:
                self.errors.append(message[:300])

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            samples = {
                name: list(values)
                for name, values in self.samples.items()
            }
            errors = list(self.errors)

        summary = {}
        for name, values in samples.items():
            ordered = sorted(values)
            summary[name] = {
                "count": len(ordered),
                "p50_ms": round(
                    statistics.median(ordered) * 1000,
                    1,
                ),
                "p95_ms": round(
                    ordered[
                        min(
                            len(ordered) - 1,
                            math.ceil(len(ordered) * 0.95) - 1,
                        )
                    ]
                    * 1000,
                    1,
                ),
                "max_ms": round(ordered[-1] * 1000, 1),
            }
        summary["errors"] = errors
        return summary


def run_periodic(
    name: str,
    client: ApiClient,
    metrics: Metrics,
    deadline: float,
    interval: float,
    operation,
    initial_delay: float = 1,
) -> None:
    next_run = time.monotonic() + initial_delay

    while time.monotonic() < deadline:
        now = time.monotonic()
        if now < next_run:
            time.sleep(min(next_run - now, 0.2))
            continue

        try:
            result = operation()
            metrics.record(name, result)
        except Exception as exc:
            metrics.error(f"{name}: {exc}")

        next_run = max(
            time.monotonic(),
            next_run + interval,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://frontend",
    )
    parser.add_argument("--duration", type=int, default=600)
    parser.add_argument("--users", type=int, default=3)
    parser.add_argument("--vision-interval", type=float, default=0.5)
    parser.add_argument("--social-interval", type=float, default=10)
    parser.add_argument("--chat-interval", type=float, default=20)
    parser.add_argument("--username-prefix", default="stage9")
    parser.add_argument("--vision-image", default=None)
    args = parser.parse_args()

    stamp = int(time.time())
    password = "Stage9Check123!"
    workers: list[Worker] = []
    usernames: list[str] = []
    user_ids: list[int] = []

    print(
        json.dumps(
            {
                "status": "setup",
                "base_url": args.base_url,
                "users": args.users,
                "duration": args.duration,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    for index in range(1, args.users + 1):
        username = f"{args.username_prefix}_{stamp}_{index}"
        setup_client = ApiClient(args.base_url)
        user_id = setup_client.register(username, password)
        session_id = setup_client.create_chat_session()
        users_ready = Worker(
            username=username,
            password=password,
            chat_session_id=session_id,
        )
        workers.append(users_ready)
        usernames.append(username)
        user_ids.append(user_id)

    metrics = Metrics()
    deadline = time.monotonic() + args.duration
    threads: list[threading.Thread] = []
    vision_data = PNG_1X1
    vision_filename = "frame.png"
    vision_content_type = "image/jpeg"

    if args.vision_image:
        with open(args.vision_image, "rb") as image_file:
            vision_data = image_file.read()
        vision_filename = "face.jpg"
        vision_content_type = "image/jpeg"

    for index, worker in enumerate(workers):
        vision_client = ApiClient(args.base_url)
        vision_client.login(worker.username, worker.password)
        social_client = ApiClient(args.base_url)
        social_client.login(worker.username, worker.password)
        chat_client = ApiClient(args.base_url)
        chat_client.login(worker.username, worker.password)

        threads.append(
            threading.Thread(
                target=run_periodic,
                args=(
                    "vision",
                    vision_client,
                    metrics,
                    deadline,
                    args.vision_interval,
                    lambda client=vision_client: client.analyze_frame(
                        vision_data,
                        vision_filename,
                        vision_content_type,
                        60,
                    ),
                    1 + index * 0.1,
                ),
                daemon=True,
            )
        )
        threads.append(
            threading.Thread(
                target=run_periodic,
                args=(
                    "social",
                    social_client,
                    metrics,
                    deadline,
                    args.social_interval,
                    lambda client=social_client: client.social_feed(30),
                    1.3 + index * 0.2,
                ),
                daemon=True,
            )
        )

        def chat_operation(
            client=chat_client,
            session_id=worker.chat_session_id,
            metrics=metrics,
        ):
            first_delta, total = client.chat_stream(session_id, 240)
            metrics.record("chat_first", first_delta)
            return total

        threads.append(
            threading.Thread(
                target=run_periodic,
                args=(
                    "chat",
                    chat_client,
                    metrics,
                    deadline,
                    args.chat_interval,
                    chat_operation,
                    2.0 + index * 0.7,
                ),
                daemon=True,
            )
        )

    for thread in threads:
        thread.start()

    while time.monotonic() < deadline:
        time.sleep(min(30, max(0, deadline - time.monotonic())))
        snapshot = metrics.snapshot()
        print(
            json.dumps(
                {
                    "status": "running",
                    "remaining_seconds": round(
                        max(0, deadline - time.monotonic())
                    ),
                    "metrics": {
                        name: value["count"]
                        for name, value in snapshot.items()
                        if name != "errors"
                    },
                    "errors": len(snapshot["errors"]),
                }
            ),
            flush=True,
        )

    for thread in threads:
        thread.join(timeout=10)

    result = metrics.snapshot()
    result["status"] = "complete"
    result["users"] = usernames
    result["user_ids"] = user_ids
    result["duration_seconds"] = args.duration
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
