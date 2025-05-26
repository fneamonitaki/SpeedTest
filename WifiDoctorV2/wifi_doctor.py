import os
import pathlib
from parser_all import extract_all_data, add_rate_gap, filter_for_1_2
from parser_for_testings import extract_all_data_testing_pcap as extract_testing
from wifi_analysis_engine import run_analysis


def get_parser_choice():
    print("\nSelect Parser:")
    print("1) parser_all - 802.11n")
    print("2) parser_for_testing - 802.11ac")
    print("3) Exit")
    return input("Enter your choice: ").strip()

def get_pcap_file():
    print("\nAvailable PCAP files:")
    pcap_dir = pathlib.Path(__file__).parent / "pcap_files"

    if not pcap_dir.exists():
        print(f"[ERROR] Could not find directory: {pcap_dir}")
        return None

    files = [f for f in pcap_dir.iterdir() if f.suffix in [".pcap", ".pcapng"]]

    if not files:
        print("No .pcap files found in pcap_files/")
        return None

    for i, file in enumerate(files, 1):
        print(f"{i}) {file.name}")
    try:
        choice = int(input("Select a file: "))
        return str(files[choice - 1])
    except (ValueError, IndexError):
        print("Invalid selection.")
        return None


def run_wifi_doctor():
    parser_map = {
        "1": (extract_all_data, "parser_all"),
        "2": (extract_testing, "parser_for_testings")
    }

    parser_choice = get_parser_choice()
    if parser_choice == "3":
        print("Exiting...")
        return

    if parser_choice not in parser_map:
        print("Invalid choice.")
        return

    extract_func, parser_name = parser_map[parser_choice]
    pcap_path = get_pcap_file()
    if not pcap_path:
        return

    print(f"\n[INFO] Running Wi-Fi Doctor using {parser_name} on {pcap_path}")
    packets = extract_func(pcap_path)
    packets = add_rate_gap(packets)

    print("\n[INFO] Analyzing metrics...")
    run_analysis(packets)
    print("\n[INFO] Wi-Fi Doctor analysis complete.")


if __name__ == "__main__":
    run_wifi_doctor()
