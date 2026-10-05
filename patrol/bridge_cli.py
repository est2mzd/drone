"""Stream simulation commands to Android's dry-run receiver; never live flight."""
import argparse
import json
import time
from .runtime import CommandClient

# USER_SETTINGS
SEND_INTERVAL_S = 0.10  # 10 Hz command stream


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',required=True)
    p.add_argument('--token-file',required=True)
    p.add_argument('--log',required=True)
    a=p.parse_args()
    with open(a.token_file) as f:token=f.read().strip()
    with open(a.log) as f:log=json.load(f)
    client=CommandClient(a.host,token)
    try:
        # Simulation world velocity isn't aircraft-frame data; send zeros to test timing/auth only.
        for row in log:
            client.send(0.,0.,0.,'DRY_RUN_'+row['state'])
            time.sleep(SEND_INTERVAL_S)
    finally:client.close()


if __name__=='__main__':main()
