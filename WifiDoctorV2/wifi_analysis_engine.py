import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from collections import deque, defaultdict
import math

MAX_DURATION_S = 30

# === Metric Calculations ===
def compute_frame_loss(packets):
    total = len(packets)
    retries = sum(1 for pkt in packets if pkt.get('retry_flag') == '1')
    return retries / total if total > 0 else 0

def compute_rssi_avg(packets):
    rssi_values = []
    for pkt in packets:
        try:
            rssi = int(pkt['signal_strength'])
            rssi_values.append(rssi)
        except (TypeError, ValueError):
            continue
    return sum(rssi_values) / len(rssi_values) if rssi_values else None

def compute_data_rate_avg(packets):
    rates = [float(pkt['data_rate']) for pkt in packets if pkt.get('data_rate')]
    return sum(rates) / len(rates) if rates else None

def compute_rate_gap_avg(packets):
    gaps = [int(pkt['rate_gap']) for pkt in packets if pkt.get('rate_gap') is not None]
    return sum(gaps) / len(gaps) if gaps else None

def compute_rate_gap_penalty(gap):
    if gap is None:
        return 1.0
    penalty_slope = 0.07 #0.07 is empirical, anything between 0.05 and 0.07 is good. We use 0.07 here because we need to be a little harsh when it comes to real time applications
    penalty = max(0.3, 1 - penalty_slope * gap) 
    return penalty

# === RSSID Logic ===
def update_rssi(ssid, channel, new_rssi, timestamp, rssi_history, last_activity, window_size):
    key = (ssid, channel)
    if key not in rssi_history:
        rssi_history[key] = deque(maxlen=window_size)
    rssi_history[key].append((new_rssi, timestamp))
    last_activity[key] = timestamp
    return compute_wma(key, rssi_history)

def compute_wma(key, rssi_history):
    rssi_tuples = list(rssi_history[key])
    rssi_values = [rssi for rssi, _ in rssi_tuples]
    n = len(rssi_values)
    if n == 0:
        return None
    weights = [i + 1 for i in range(n)]
    wma = sum(rssi * weight for rssi, weight in zip(rssi_values, weights)) / sum(weights)
    return round(wma, 2)

def compute_weight(key, current_ts, last_activity, decay_rate):
    last_seen = float(last_activity.get(key, current_ts))
    elapsed = (float(current_ts) - last_seen) / 1e6
    return math.exp(-decay_rate * elapsed)

def compute_rssid_per_channel(ts, rssi_history, last_activity, decay_rate):
    rssid_per_channel = defaultdict(float)
    for (ssid, channel), _ in rssi_history.items():
        wma = compute_wma((ssid, channel), rssi_history)
        if wma is not None and wma != 0:
            weight = compute_weight((ssid, channel), ts, last_activity, decay_rate)
            rssid_per_channel[channel] += (1 / abs(wma)) * weight
    return dict(rssid_per_channel)

def compute_rssid_log(packets, decay_rate=0.1, window_size=10):  #decay rate here is also empirical, we changed it from 0.5 to 0.1 since we care more about real time data
    rssi_history = {}
    last_activity = {}
    rssid_log = []

    for pkt in packets:
        ssid = pkt.get('ssid')
        channel = pkt.get('channel')
        rssi = pkt.get('signal_strength')
        sniff_time = pkt.get('sniff_time')

        if ssid and rssi is not None and channel and sniff_time:
            try:
                rssi = int(rssi)
                channel = int(channel)
                timestamp = sniff_time.timestamp()  # use sniff_time as float timestamp
                update_rssi(ssid, channel, rssi, timestamp, rssi_history, last_activity, window_size)
                rssid_values = compute_rssid_per_channel(timestamp, rssi_history, last_activity, decay_rate)
                for ch, value in rssid_values.items():
                    rssid_log.append((timestamp, ch, value))
            except Exception:
                continue
    return rssid_log


def compute_avg_rssid(rssid_log, target_channel):
    values = [rssid for _, ch, rssid in rssid_log if int(ch) == target_channel]
    return sum(values) / len(values) if values else 0

def compute_theoretical_throughput(rate, loss, gap=None, rssid=0.0, avg_payload=None, avg_total=None):
    if rate is None or loss is None:
        return None
    penalty = compute_rate_gap_penalty(gap)
    utilization_penalty = 1 - min(rssid, 1.0)

    if avg_payload is not None and avg_total and avg_total > 0:
        payload_efficiency = avg_payload / avg_total
    else:
        payload_efficiency = 1.0  # fallback to ideal

    return rate * (1 - loss) * penalty * utilization_penalty * payload_efficiency

def plot_metric(results, key, ylabel, title, filename):
    times = [r['timestamp'] for r in results]
    values = [r[key] for r in results]
    #debug
    #print(f"\n{key.upper()} values:")
    #print(values)
    plt.figure(figsize=(10, 5))
    plt.plot(times, values, marker='o')
    plt.title(title)
    plt.xlabel("Time (seconds)")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.savefig(filename)
    plt.show()

def run_analysis(packet_data):
    filtered_packets = [
        pkt for pkt in packet_data
        if pkt.get('sniff_time') and pkt.get('signal_strength') is not None
    ]
    filtered_packets.sort(key=lambda pkt: pkt['sniff_time'])
    start_time = filtered_packets[0]['sniff_time']
    for pkt in filtered_packets:
        pkt['timestamp'] = (pkt['sniff_time'] - start_time).total_seconds()
    filtered_packets = [pkt for pkt in filtered_packets if isinstance(pkt['timestamp'], (float, int)) and pkt['timestamp'] <= 30]
    if not filtered_packets:
        print("No packets after filtering for 30s window.")
        return

    print("\n[INFO] Computing RSSID log internally...")
    rssid_log = compute_rssid_log(packet_data)
    channel = int(filtered_packets[0]['channel']) if 'channel' in filtered_packets[0] else 1
    avg_rssid = compute_avg_rssid(rssid_log, channel)

    WINDOW_SIZE_S = 2
    end_time = filtered_packets[-1]['timestamp']
    current_start = 0
    current_end = current_start + WINDOW_SIZE_S
    results = []

    while current_start < end_time:
        window_packets = [pkt for pkt in filtered_packets if current_start <= pkt['timestamp'] < current_end]
        print(f"Window {current_start:.2f}–{current_end:.2f}s: {len(window_packets)} packets")
        if window_packets:
            rssi = compute_rssi_avg(window_packets)
            rate = compute_data_rate_avg(window_packets)
            loss = compute_frame_loss(window_packets)
            gap = compute_rate_gap_avg(window_packets)

            payloads = [pkt['payload_length'] for pkt in window_packets if pkt.get('payload_length') is not None]
            totals = [pkt['frame_length'] for pkt in window_packets if pkt.get('frame_length') is not None]

            avg_payload = sum(payloads) / len(payloads) if payloads else None
            avg_total = sum(totals) / len(totals) if totals else None

            tput = compute_theoretical_throughput(rate, loss, gap, avg_rssid, avg_payload, avg_total)
            results.append({
                'timestamp': current_end,
                'avg_rssi': rssi,
                'avg_rate': rate,
                'frame_loss': loss,
                'rate_gap': gap,
                'theoretical_throughput': tput
            })
        current_start += WINDOW_SIZE_S
        current_end += WINDOW_SIZE_S

    df = pd.DataFrame(results)
    df.to_csv("wifi_analysis_summary.csv", index=False)
    print("Saved metrics to wifi_analysis_summary.csv")

    # Save RSSID log for reference
    pd.DataFrame(rssid_log, columns=['timestamp', 'channel', 'rssid']).to_csv("rssid_log.csv", index=False)
    print("Saved RSSID log to rssid_log.csv")

    plot_metric(results, 'avg_rssi', "RSSI (dBm)", "Average RSSI Over Time", "rssi_plot.png")
    plot_metric(results, 'avg_rate', "Data Rate (Mbps)", "Average Data Rate Over Time", "rate_plot.png")
    plot_metric(results, 'frame_loss', "Frame Loss Rate", "Frame Loss Over Time", "loss_plot.png")
    plot_metric(results, 'rate_gap', "Rate Gap", "Rate Gap Over Time", "rate_gap_plot.png")
    plot_metric(results, 'theoretical_throughput', "Throughput (Mbps)", "Estimated Throughput Over Time", "throughput_plot.png")
