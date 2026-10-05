import json
import socket
import threading
import time
import unittest
from patrol.runtime import CommandClient


class Transport(unittest.TestCase):
    def test_ndjson_sequence_and_stop_packet(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(2)
            received=[]
            def consume():
                conn,_=server.accept()
                with conn,conn.makefile('r') as reader:
                    received.extend(json.loads(line) for line in reader)
            worker=threading.Thread(target=consume);worker.start()
            token='a'*64
            client=CommandClient('127.0.0.1',token,server.getsockname()[1])
            try:client.send(.1,0.,0.,'DRY_RUN')
            finally:client.close()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual([p['seq'] for p in received],[1,2])
            self.assertEqual(received[0]['session'],received[1]['session'])
            self.assertEqual(received[-1]['reason'],'CLIENT_STOP')
            self.assertEqual(received[-1]['roll_mps'],0.)
            self.assertGreater(received[0]['expires_unix_ms'],time.time()*1000-100)
            self.assertEqual(received[0]['token'],token)

    def test_invalid_token_rejected_before_connect(self):
        with self.assertRaises(ValueError):CommandClient('127.0.0.1','short')
