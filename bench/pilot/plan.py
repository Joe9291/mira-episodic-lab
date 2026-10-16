"""Turn config/pilot.json into the workflow matrix (one cell per model, arm, world)."""
import json
import os
import sys

request = json.load(open(sys.argv[1]))
cells = [{"model": m, "arm": a, "index": i}
         for m in request["models"] for a in request["arms"] for i in request["indices"]]
with open(os.environ["GITHUB_OUTPUT"], "a") as out:
    out.write(f"enabled={'true' if request.get('enabled') is True else 'false'}\n")
    out.write(f"series={request['series']}\n")
    out.write(f"matrix={json.dumps({'include': cells})}\n")
print(len(cells), "cells, enabled:", request.get("enabled"))
