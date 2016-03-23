#!/usr/bin/env python2
# Copyright (c) 2014-2015 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

#
# Test addressindex generation and fetching
#

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from test_framework.script import *
from test_framework.mininode import *
import binascii

class AddressIndexTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory "+self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 4)

    def setup_network(self):
        self.nodes = []
        # Nodes 0/1 are "wallet" nodes
        self.nodes.append(start_node(0, self.options.tmpdir, ["-debug"]))
        self.nodes.append(start_node(1, self.options.tmpdir, ["-debug", "-addressindex"]))
        # Nodes 2/3 are used for testing
        self.nodes.append(start_node(2, self.options.tmpdir, ["-debug"]))
        self.nodes.append(start_node(3, self.options.tmpdir, ["-debug", "-addressindex"]))
        connect_nodes(self.nodes[0], 1)
        connect_nodes(self.nodes[0], 2)
        connect_nodes(self.nodes[0], 3)

        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        print "Mining blocks..."
        self.nodes[0].generate(105)
        self.sync_all()

        chain_height = self.nodes[1].getblockcount()
        assert_equal(chain_height, 105)
        assert_equal(self.nodes[1].getbalance(), 0)
        assert_equal(self.nodes[2].getbalance(), 0)

        # Check that balances are correct
        balance0 = self.nodes[1].getaddressbalance("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br")
        assert_equal(balance0["balance"], 0)

        # Check p2pkh and p2sh address indexes
        print "Testing p2pkh and p2sh address index..."

        txid0 = self.nodes[0].sendtoaddress("mo9ncXisMeAoXwqcV5EWuyncbmCcQN4rVs", 10)
        self.nodes[0].generate(1)

        txidb0 = self.nodes[0].sendtoaddress("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br", 10)
        self.nodes[0].generate(1)

        txid1 = self.nodes[0].sendtoaddress("mo9ncXisMeAoXwqcV5EWuyncbmCcQN4rVs", 15)
        self.nodes[0].generate(1)

        txidb1 = self.nodes[0].sendtoaddress("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br", 15)
        self.nodes[0].generate(1)

        txid2 = self.nodes[0].sendtoaddress("mo9ncXisMeAoXwqcV5EWuyncbmCcQN4rVs", 20)
        self.nodes[0].generate(1)

        txidb2 = self.nodes[0].sendtoaddress("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br", 20)
        self.nodes[0].generate(1)

        self.sync_all()

        txids = self.nodes[1].getaddresstxids("mo9ncXisMeAoXwqcV5EWuyncbmCcQN4rVs")
        assert_equal(len(txids), 3)
        assert_equal(txids[0], txid0)
        assert_equal(txids[1], txid1)
        assert_equal(txids[2], txid2)

        txidsb = self.nodes[1].getaddresstxids("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br")
        assert_equal(len(txidsb), 3)
        assert_equal(txidsb[0], txidb0)
        assert_equal(txidsb[1], txidb1)
        assert_equal(txidsb[2], txidb2)

        # Check that multiple addresses works
        multitxids = self.nodes[1].getaddresstxids({"addresses": ["2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br", "mo9ncXisMeAoXwqcV5EWuyncbmCcQN4rVs"]})
        assert_equal(len(multitxids), 6)
        assert_equal(multitxids[0], txid0)
        assert_equal(multitxids[1], txidb0)
        assert_equal(multitxids[2], txid1)
        assert_equal(multitxids[3], txidb1)
        assert_equal(multitxids[4], txid2)
        assert_equal(multitxids[5], txidb2)

        # Check that balances are correct
        balance0 = self.nodes[1].getaddressbalance("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br")
        assert_equal(balance0["balance"], 45 * 100000000)

        # Check that outputs with the same address will only return one txid
        print "Testing for txid uniqueness..."
        addressHash = "6349a418fc4578d10a372b54b45c280cc8c4382f".decode("hex")
        scriptPubKey = CScript([OP_HASH160, addressHash, OP_EQUAL])
        unspent = self.nodes[0].listunspent()
        tx = CTransaction()
        tx.vin = [CTxIn(COutPoint(int(unspent[0]["txid"], 16), unspent[0]["vout"]))]
        tx.vout = [CTxOut(10, scriptPubKey), CTxOut(11, scriptPubKey)]
        tx.rehash()

        signed_tx = self.nodes[0].signrawtransaction(binascii.hexlify(tx.serialize()).decode("utf-8"))
        sent_txid = self.nodes[0].sendrawtransaction(signed_tx["hex"], True)

        self.nodes[0].generate(1)
        self.sync_all()

        txidsmany = self.nodes[1].getaddresstxids("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br")
        assert_equal(len(txidsmany), 4)
        assert_equal(txidsmany[3], sent_txid)

        # Check that balances are correct
        balance0 = self.nodes[1].getaddressbalance("2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br")
        assert_equal(balance0["balance"], 45 * 100000000 + 21)

        # Check that balances are correct after spending
        privkey2 = "cSdkPxkAjA4HDr5VHgsebAPDEh9Gyub4HK8UJr2DFGGqKKy4K5sG"
        address2 = "mgY65WSfEmsyYaYPQaXhmXMeBhwp4EcsQW"
        addressHash2 = "0b2f0a0c31bfe0406b0ccc1381fdbe311946dadc".decode("hex")
        scriptPubKey2 = CScript([OP_DUP, OP_HASH160, addressHash2, OP_EQUALVERIFY, OP_CHECKSIG])
        self.nodes[0].importprivkey(privkey2)

        unspent = self.nodes[0].listunspent()
        tx = CTransaction()
        tx.vin = [CTxIn(COutPoint(int(unspent[0]["txid"], 16), unspent[0]["vout"]))]
        amount = unspent[0]["amount"] * 100000000
        tx.vout = [CTxOut(amount, scriptPubKey2)]
        tx.rehash()
        signed_tx = self.nodes[0].signrawtransaction(binascii.hexlify(tx.serialize()).decode("utf-8"))
        spending_txid = self.nodes[0].sendrawtransaction(signed_tx["hex"], True)
        self.nodes[0].generate(1)
        self.sync_all()
        balance1 = self.nodes[1].getaddressbalance(address2)
        assert_equal(balance1["balance"], amount)

        tx = CTransaction()
        tx.vin = [CTxIn(COutPoint(int(spending_txid, 16), 0))]
        send_amount = 1 * 100000000 + 12840
        change_amount = amount - send_amount - 10000
        tx.vout = [CTxOut(send_amount, scriptPubKey), CTxOut(change_amount, scriptPubKey2)]
        tx.rehash()

        signed_tx = self.nodes[0].signrawtransaction(binascii.hexlify(tx.serialize()).decode("utf-8"))
        sent_txid = self.nodes[0].sendrawtransaction(signed_tx["hex"], True)
        self.nodes[0].generate(1)
        self.sync_all()

        balance2 = self.nodes[1].getaddressbalance(address2)
        assert_equal(balance2["balance"], change_amount)

        print "Passed\n"


if __name__ == '__main__':
    AddressIndexTest().main()
