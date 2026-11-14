"""A fake Ollama HTTP server for the Mehteran tests (no network, no model).

Used two ways: FakeOllama().start() in a test (a random port on 127.0.0.1), or as a program "ollama serve" (the
port comes from OLLAMA_HOST), to test that Mehteran starts and stops Ollama itself.
"""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeOllama:
    def __init__(self, port: int = 0):
        self.models = {"qwen2.5:0.5b": 397_000_000}
        self.requests: list[dict] = []
        self.pull_steps = 20
        self.pull_delay = 0.02
        self.context_length = 32768  # the model maximum that /api/show reports (None: not reported)
        self.chars_per_token = 4
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, code, data):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def stream(self, events):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                try:
                    for event in events:
                        self.wfile.write(json.dumps(event).encode() + b"\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def body(self):
                length = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(length) or b"{}")
                owner.requests.append({"path": self.path, **data})
                return data

            def do_GET(self):
                if self.path == "/api/version":
                    return self.reply(200, {"version": "0.0.0-fake"})
                if self.path == "/api/tags":
                    return self.reply(200, {"models": [{"name": n, "model": n, "size": s, "modified_at": "2026-11-01T10:00:00Z"}
                                                       for n, s in owner.models.items()]})
                self.reply(404, {"error": "not found"})

            def do_POST(self):
                data = self.body()
                if self.path == "/api/chat":
                    if data.get("model") not in owner.models:
                        return self.reply(404, {"error": f"model '{data.get('model')}' not found"})
                    # Like Ollama: a prompt longer than num_ctx is cut to it, and prompt_eval_count says how much was read.
                    text = "".join(m["content"] for m in data.get("messages", []))
                    read = min(len(text) // owner.chars_per_token + 1, (data.get("options") or {}).get("num_ctx", 4096))
                    return self.stream([{"message": {"content": "<think>hidden</think>Hello "}, "done": False},
                                        {"message": {"content": "from the local model."}, "done": False},
                                        {"message": {"content": ""}, "done": True, "prompt_eval_count": read}])
                if self.path == "/api/show":
                    if data.get("model") not in owner.models:
                        return self.reply(404, {"error": "model not found"})
                    info = {"general.architecture": "llama"}
                    if owner.context_length:
                        info["llama.context_length"] = owner.context_length
                    return self.reply(200, {"model_info": info})
                if self.path == "/api/pull":
                    name = data.get("model")

                    def events():
                        total = 1000
                        for n in range(owner.pull_steps + 1):
                            time.sleep(owner.pull_delay)
                            yield {"status": "pulling abc", "total": total, "completed": total * n // owner.pull_steps}
                        owner.models[name] = total
                        yield {"status": "success"}
                    return self.stream(events())
                self.reply(404, {"error": "not found"})

            def do_DELETE(self):
                data = self.body()
                if self.path == "/api/delete" and data.get("model") in owner.models:
                    del owner.models[data["model"]]
                    return self.reply(200, {})
                self.reply(404, {"error": "model not found"})

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"

    def start(self) -> "FakeOllama":
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


if __name__ == "__main__":  # "ollama serve" / "ollama --version"
    if sys.argv[1:] == ["--version"]:
        print("ollama version is 0.0.0-fake")
        sys.exit(0)
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    FakeOllama(int(host.rpartition(":")[2])).server.serve_forever()
