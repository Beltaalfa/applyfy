import unittest

from applyfy_parser import _normalize_acquirer, parse_payload_order


class ApplyfyParserTests(unittest.TestCase):
    def test_parse_payload_order_success(self):
        html = """
        <html><body>
        <script>
        self.__next_f.push([1,"\\"order\\":{\\"id\\":\\"ord_1\\",\\"code\\":\\"VND001\\",\\"totalAmount\\":150.5,\\"createdAt\\":\\"2026-03-20T10:00:00Z\\",\\"client\\":{\\"name\\":\\"Joao\\",\\"email\\":\\"joao@x.com\\"},\\"producer\\":{\\"name\\":\\"Produtor A\\",\\"email\\":\\"prod@x.com\\"},\\"items\\":[{\\"quantity\\":1,\\"price\\":150.5,\\"offerCode\\":\\"OFF10\\",\\"product\\":{\\"id\\":\\"prd1\\",\\"name\\":\\"Produto X\\"}}],\\"transactions\\":[{\\"id\\":\\"tx_1\\",\\"amount\\":150.5,\\"chargeAmount\\":160.0,\\"status\\":\\"PAID\\",\\"paymentMethod\\":\\"PIX\\",\\"acquirer\\":\\"pagar_me\\",\\"acquirerExternalId\\":\\"acq_123\\",\\"availableAt\\":\\"2026-03-21T10:00:00Z\\",\\"updatedAt\\":\\"2026-03-20T11:00:00Z\\",\\"feeTransactions\\":[{\\"type\\":\\"OPERATION\\",\\"amount\\":10.0},{\\"type\\":\\"ACQUIRER\\",\\"amount\\":5.0},{\\"type\\":\\"FUND_LOCK\\",\\"amount\\":2.0}],\\"transactionAttempts\\":[{\\"status\\":\\"APPROVED\\",\\"subStatus\\":\\"OK\\",\\"responseTimeMs\\":123,\\"message\\":\\"ok\\"}]}]}\\""]);
        </script>
        </body></html>
        """
        bundles = parse_payload_order(html)
        self.assertEqual(len(bundles), 1)
        venda, fees, attempts, webhooks = bundles[0]
        self.assertEqual(venda.order_id, "ord_1")
        self.assertEqual(venda.transaction_id, "tx_1")
        self.assertEqual(venda.adquirente, "Pagar.me")
        self.assertEqual(venda.taxa_processamento, 10.0)
        self.assertEqual(venda.taxa_adquirente, 5.0)
        self.assertEqual(venda.retencao, 2.0)
        self.assertEqual(len(fees), 3)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(webhooks, [])

    def test_parse_payload_order_one_row_per_transaction(self):
        html = """
        <html><body>
        <script>
        self.__next_f.push([1,"\\"order\\":{\\"id\\":\\"ord_1\\",\\"code\\":\\"VND001\\",\\"totalAmount\\":200.0,\\"createdAt\\":\\"2026-03-20T10:00:00Z\\",\\"client\\":{},\\"producer\\":{},\\"items\\":[{}],\\"transactions\\":[{\\"id\\":\\"tx_a\\",\\"chargeAmount\\":100.0,\\"status\\":\\"PAID\\",\\"paymentMethod\\":\\"PIX\\",\\"acquirer\\":\\"pagar_me\\",\\"feeTransactions\\":[]},{\\"id\\":\\"tx_b\\",\\"chargeAmount\\":100.0,\\"status\\":\\"REFUNDED\\",\\"paymentMethod\\":\\"PIX\\",\\"acquirer\\":\\"pagar_me\\",\\"feeTransactions\\":[]}]}\\""]);
        </script>
        </body></html>
        """
        bundles = parse_payload_order(html)
        self.assertEqual(len(bundles), 2)
        self.assertEqual(bundles[0][0].transaction_id, "tx_a")
        self.assertEqual(bundles[0][0].status_pagamento, "PAID")
        self.assertEqual(bundles[1][0].transaction_id, "tx_b")
        self.assertEqual(bundles[1][0].status_pagamento, "REFUNDED")
        self.assertEqual(bundles[0][0].codigo_venda, "VND001")
        self.assertEqual(bundles[1][0].codigo_venda, "VND001")

    def test_parse_payload_order_returns_none_when_no_order(self):
        html = '<html><body><script>self.__next_f.push([1,\\"sem order\\"]);</script></body></html>'
        bundles = parse_payload_order(html)
        self.assertEqual(bundles, [])

    def test_normalize_acquirer(self):
        self.assertEqual(_normalize_acquirer("pagar_me"), "Pagar.me")
        self.assertEqual(_normalize_acquirer("mercado_pago"), "Mercado Pago")
        self.assertEqual(_normalize_acquirer("xpto"), "xpto")


if __name__ == "__main__":
    unittest.main()
