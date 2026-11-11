import csv
import socket
import ssl
import time
import http.client
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

TXT_URL = "https://1i.l.cd/ahhfzwl/CF/main/OTC_SCAN_YX_AS906.txt"
TEST_PATH = "/__down?bytes=9999999"
HOST_HEADER = "1i.l.cd"
OUTPUT_CSV = "ip.csv"
MAX_WORKERS = 10
TIMEOUT = 1

def fetch_ip_list(url):
    print(f"[*] 获取 IP 列表: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("utf-8")

    ip_ports = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        target = line.replace(",", " ").replace("\t", " ").split()[0]
        ip, port = target.rsplit(":", 1) if ":" in target else (target, "443")
        ip_ports.append((ip, int(port)))

    print(f"[+] 加载 {len(ip_ports)} 个目标")
    return ip_ports

def test_ip(ip, port):
    start = time.time()
    latency_ms, speed_mbps = None, 0.0
    try:
        ctx = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection(ip, port, timeout=TIMEOUT, context=ctx)
        # 用 SNI + Host 头伪装成目标域名
        conn._context = ctx
        sock = socket.create_connection((ip, port), timeout=TIMEOUT)
        conn.sock = ctx.wrap_socket(sock, server_hostname=HOST_HEADER)
        conn.request("GET", TEST_PATH, headers={
            "Host": HOST_HEADER,
            "User-Agent": "Mozilla/5.0",
        })
        resp = conn.getresponse()
        if resp.status == 200:
            latency_ms = round((time.time() - start) * 1000, 2)
            downloaded, dl_start = 0, time.time()
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                downloaded += len(chunk)
            dur = time.time() - dl_start
            if dur > 0:
                speed_mbps = round((downloaded / 1048576) / dur, 2)
            print(f"[OK] {ip}:{port} | {latency_ms} ms | {speed_mbps} MB/s")
        conn.close()
    except Exception as e:
        print(f"[FAIL] {ip}:{port} | {e}")

    return {"ip": ip, "port": port, "latency_ms": latency_ms,
            "speed_mbps": speed_mbps,
            "status": "Success" if latency_ms is not None else "Failed"}

def main():
    try:
        ip_ports = fetch_ip_list(TXT_URL)
    except Exception as e:
        print(f"[-] 获取列表失败: {e}")
        return

    results = []
    print(f"[*] {MAX_WORKERS} 线程测速...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(test_ip, ip, p) for ip, p in ip_ports]
        for f in as_completed(futures):
            results.append(f.result())

    # 按延迟升序，失败（None）排最后
    results.sort(key=lambda x: (x["latency_ms"] is None, x["latency_ms"] or 0))

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["IP", "Port", "Latency (ms)", "Speed (MB/s)", "Status"])
        for r in results:
            w.writerow([r["ip"], r["port"],
                        r["latency_ms"] if r["latency_ms"] is not None else "N/A",
                        r["speed_mbps"], r["status"]])

    print(f"\n[+] 完成，结果已保存到 {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
