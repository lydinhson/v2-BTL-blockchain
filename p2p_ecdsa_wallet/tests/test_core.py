"""Kiểm thử tầng lõi. Chạy từ thư mục code/:  python -m unittest discover -s tests -v"""
import os
import shutil
import tempfile
import unittest

from core.block import Block
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.wallet import Wallet


class WalletTest(unittest.TestCase):
    def test_sign_and_verify(self):
        w = Wallet()
        sig = w.sign("abc")
        self.assertTrue(Wallet.verify(w.public_key_hex, "abc", sig))
        self.assertFalse(Wallet.verify(w.public_key_hex, "abd", sig))
        self.assertFalse(Wallet.verify(Wallet().public_key_hex, "abc", sig))

    def test_restore_from_private_key(self):
        w = Wallet()
        self.assertEqual(Wallet(w.private_key_hex).public_key_hex, w.public_key_hex)


class BlockchainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.alice, self.bob = Wallet(), Wallet()
        self.bc = Blockchain(os.path.join(self.tmp, "ledger.json"), difficulty=2)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _signed_tx(self, wallet, recipient, amount, nonce=0):
        tx = Transaction(wallet.public_key_hex, recipient, amount, nonce=nonce)
        tx.sign_transaction(wallet)
        return tx

    def test_genesis_is_identical_across_nodes(self):
        other = Blockchain(os.path.join(self.tmp, "other.json"), difficulty=2)
        self.assertEqual(self.bc.chain[0].hash, other.chain[0].hash)

    def test_tampered_amount_is_rejected(self):
        self.bc.mine_pending_transactions(self.alice.public_key_hex)
        tx = self._signed_tx(self.alice, self.bob.public_key_hex, 10)
        forged = Transaction.from_dict({**tx.to_dict(), "amount": 11})
        self.assertFalse(self.bc.add_transaction(forged))
        self.assertTrue(self.bc.add_transaction(tx))

    def test_insufficient_balance_and_replay_rejected(self):
        self.assertFalse(self.bc.add_transaction(self._signed_tx(self.alice, self.bob.public_key_hex, 1)))
        self.bc.mine_pending_transactions(self.alice.public_key_hex)  # Alice nhận 50
        tx = self._signed_tx(self.alice, self.bob.public_key_hex, 20)
        self.assertTrue(self.bc.add_transaction(tx))
        self.assertFalse(self.bc.add_transaction(tx))  # trùng trong Mempool
        self.bc.mine_pending_transactions(self.bob.public_key_hex)
        self.assertFalse(self.bc.add_transaction(tx))  # đã nằm trong chuỗi
        self.assertEqual(self.bc.get_balance(self.alice.public_key_hex), 30)
        self.assertEqual(self.bc.get_balance(self.bob.public_key_hex), 70)

    def test_forged_system_tx_rejected(self):
        fake = Transaction("SYSTEM", self.bob.public_key_hex, 1000)
        self.assertFalse(self.bc.add_transaction(fake))

    def test_chain_validation_and_persistence(self):
        self.bc.mine_pending_transactions(self.alice.public_key_hex)
        self.bc.add_transaction(self._signed_tx(self.alice, self.bob.public_key_hex, 5))
        self.bc.mine_pending_transactions(self.alice.public_key_hex)
        self.assertTrue(self.bc.is_chain_valid(self.bc.chain))

        reloaded = Blockchain(self.bc.storage_path, difficulty=2)
        self.assertTrue(reloaded.is_chain_valid(reloaded.chain))
        self.assertEqual(len(reloaded.chain), 3)

        # Sửa số tiền trong khối đã đào -> chuỗi không còn hợp lệ
        tampered = [Block.from_dict(b.to_dict()) for b in self.bc.chain]
        tampered[2].transactions[1].amount = 40
        self.assertFalse(self.bc.is_chain_valid(tampered))

    def test_replace_chain_prunes_mempool(self):
        self.bc.mine_pending_transactions(self.alice.public_key_hex)
        tx = self._signed_tx(self.alice, self.bob.public_key_hex, 5)

        other = Blockchain(os.path.join(self.tmp, "other.json"), difficulty=2)
        other.replace_chain([Block.from_dict(b.to_dict()) for b in self.bc.chain])
        self.assertTrue(other.add_transaction(tx))

        self.bc.add_transaction(tx)
        self.bc.mine_pending_transactions(self.bob.public_key_hex)
        other.replace_chain([Block.from_dict(b.to_dict()) for b in self.bc.chain])
        self.assertEqual(other.mempool, [])


if __name__ == "__main__":
    unittest.main()
