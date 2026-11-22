"""Kiểm thử API của Full Node (không cần chạy server thật, không có peer)."""
import shutil
import tempfile
import unittest

from network.node import create_node_app


class NodeApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = create_node_app(port=6001, initial_peers=[], difficulty=2, storage_dir=self.tmp)
        self.client = self.app.test_client()
        self.address = self.client.get("/wallet").get_json()["address"]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _other_node(self, port=6002):
        return create_node_app(port=port, initial_peers=[], difficulty=2, storage_dir=self.tmp).test_client()

    def test_index_serves_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.content_type)
        self.assertIn("Ví Full Node P2P", resp.get_data(as_text=True))
        resp.close()

    def test_send_without_balance_is_rejected_with_reason(self):
        resp = self.client.post("/transactions/send", json={"recipient": "ab" * 64, "amount": 1})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("số dư", resp.get_json()["error"])

    def test_send_after_mining_assigns_sequential_nonces(self):
        self.assertEqual(self.client.post("/mine").status_code, 200)
        nonces = []
        for _ in range(2):
            resp = self.client.post("/transactions/send", json={"recipient": "ab" * 64, "amount": 5})
            self.assertEqual(resp.status_code, 201)
            nonces.append(resp.get_json()["transaction"]["nonce"])
        self.assertEqual(nonces, [0, 1])
        self.assertEqual(self.client.get("/mempool").get_json()["size"], 2)

        status = self.client.get("/status").get_json()
        self.assertEqual(status["next_nonce"], 2)
        self.assertEqual(status["balance"], 50)  # chưa đào nên chưa trừ

    def test_tampered_signed_transaction_is_rejected(self):
        self.client.post("/mine")
        signed = self.client.post("/transactions/sign", json={"recipient": "ab" * 64, "amount": 5}).get_json()
        tx = signed["transaction"]
        self.assertEqual(self.client.get("/mempool").get_json()["size"], 0)  # ký nhưng chưa gửi

        resp = self.client.post("/transactions/receive", json={**tx, "amount": tx["amount"] + 1})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ECDSA", resp.get_json()["error"])

        self.assertEqual(self.client.post("/transactions/receive", json=tx).status_code, 201)
        replay = self.client.post("/transactions/receive", json=tx)
        self.assertEqual(replay.status_code, 400)
        self.assertIn("phát lại", replay.get_json()["error"])

        kinds = [entry["kind"] for entry in self.client.get("/logs").get_json()["logs"]]
        self.assertIn("ok", kinds)
        self.assertIn("bad", kinds)

    def test_receive_block_from_other_node(self):
        other = self._other_node()
        block1 = other.post("/mine").get_json()["block"]
        resp = self.client.post("/blocks/receive", json=block1, headers={"X-Node-Url": "http://peer"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get("/chain").get_json()["length"], 2)

        # Gửi lại cùng khối -> bỏ qua
        self.assertEqual(self.client.post("/blocks/receive", json=block1).status_code, 200)

        block2 = other.post("/mine").get_json()["block"]
        tampered = {**block2, "transactions": [{**block2["transactions"][0], "amount": 999}]}
        self.assertEqual(self.client.post("/blocks/receive", json=tampered).status_code, 400)
        self.assertEqual(self.client.get("/chain").get_json()["length"], 2)

    def test_register_peers(self):
        resp = self.client.post("/nodes/register", json={"peers": ["http://127.0.0.1:6009"]})
        self.assertEqual(resp.status_code, 201)
        self.assertIn("http://127.0.0.1:6001", resp.get_json()["peers"])
        self.assertEqual(self.client.get("/nodes").get_json()["peers"], ["http://127.0.0.1:6009"])


if __name__ == "__main__":
    unittest.main()
