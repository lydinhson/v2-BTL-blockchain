import argparse
import sys

from network.node import create_node_app

if __name__ == "__main__":
    # Console Windows mặc định cp1252 sẽ lỗi khi in tiếng Việt có dấu
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Khởi chạy Full Node ví điện tử P2P")
    parser.add_argument("--port", type=int, default=5001, help="Cổng chạy Full Node")
    parser.add_argument("--peers", nargs="*", default=[], help="Danh sách URL các peer lân cận")
    parser.add_argument("--difficulty", type=int, default=3, help="Độ khó Proof of Work (số chữ số 0 đầu hash)")
    args = parser.parse_args()

    app = create_node_app(port=args.port, initial_peers=args.peers, difficulty=args.difficulty)
    app.run(host="127.0.0.1", port=args.port, threaded=True)
