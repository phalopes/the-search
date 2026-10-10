"""Create a workers.dev namespace only if the target account has none."""

import json
import os
import urllib.error
import urllib.request

base = "https://api.cloudflare.com/client/v4/accounts/"
url = base + os.environ["CLOUDFLARE_ACCOUNT_ID"] + "/workers/subdomain"
headers = {
    "Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"],
    "Content-Type": "application/json",
}
try:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=20
    ) as response:
        result = json.load(response)
except urllib.error.HTTPError as error:
    result = json.load(error)
if result.get("success"):
    print("workers.dev namespace already configured")
elif any(e.get("code") == 10007 for e in result.get("errors", [])):
    data = json.dumps({"subdomain": "the-search-pedro"}).encode()
    with urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=headers, method="PUT"), timeout=20
    ) as response:
        created = json.load(response)
    if not created.get("success"):
        raise RuntimeError("Could not create namespace")
    print("Created workers.dev namespace for The Search")
else:
    raise RuntimeError("Cannot query target account namespace; check token scopes")
