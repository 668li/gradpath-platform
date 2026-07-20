import base64
import subprocess
import sys

SRC = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\knowledge_deep.json"
DEST = "/app/app/crawlers/real_data/knowledge_deep.json"

with open(SRC, "rb") as f:
    data = base64.b64encode(f.read()).decode()

print(f"Base64 size: {len(data)} bytes")

# Write to a temp file inside container using docker exec
# Split into chunks that fit in command line
chunk_size = 80000
chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
print(f"Chunks: {len(chunks)}")

# Write each chunk
for i, chunk in enumerate(chunks):
    cmd = ["docker", "exec", "gradpath-backend-1", "bash", "-c",
           f"echo -n '{chunk}' | base64 -d > /tmp/kd_{i}.bin"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Chunk {i} failed: {r.stderr}")
        sys.exit(1)
    print(f"  Chunk {i}/{len(chunks)-1} written")

# Concatenate and move
parts = " ".join(f"/tmp/kd_{i}.bin" for i in range(len(chunks)))
cmd = ["docker", "exec", "gradpath-backend-1", "bash", "-c",
       f"cat {parts} > {DEST}"]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(f"Merge failed: {r.stderr}")
    sys.exit(1)

# Cleanup
cmd = ["docker", "exec", "gradpath-backend-1", "bash", "-c",
       f"rm -f /tmp/kd_*.bin"]
subprocess.run(cmd, capture_output=True)

# Verify
cmd = ["docker", "exec", "gradpath-backend-1", "bash", "-c",
       f"wc -c < {DEST}"]
r = subprocess.run(cmd, capture_output=True, text=True)
print(f"File size in container: {r.stdout.strip()} bytes")
print("Done!")
