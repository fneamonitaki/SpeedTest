import pyshark
from tqdm import tqdm

def extract_all_data_testing_pcap(pcap_file: str, packet_limit=0) -> list:
    """
    Using pyshark this method applies no filter into the pcap file
    and tries to extract various information from those packets such as:
    ->BSSID
    ->Transmitter MAC address
    ->Receiver MAC address
    ->Type/subtype
    ->PHY Type
    ->MCS Index
    ->Bandwidth
    ->Spatial Streams
    ->Short GI
    ->Data Rate
    ->Rate Gap
    ->Channel
    ->Frequency
    ->Signal Strength 
    ->Signal/Noise Ratio (SNR)

    Args:
        pcap_file (str): path to the pcap file

    Returns:
       List: Contains a dictionary for each packet in the pcap_file
    """

    capture = pyshark.FileCapture(pcap_file)
    extracted_data_all = []

    i = 0
    for packet in tqdm(capture, desc="Extracting Data", unit="packet"):
        if packet_limit != 0 and i >= packet_limit:
            break 
        packet_data_all = {
            'bssid': None,
            'transmitter_mac': None,
            'receiver_mac': None,
            'frame_type_subtype': None,
            'phy_type': None,
            'mcs_index': None,
            'bandwidth': None,
            'spatial_streams': None,
            'short_gi': None,
            'data_rate': None,
            'rate_gap' : None,
            'channel': None,
            'frequency': None,
            'signal_strength': None,
            'retry_flag': None,
            'snr': None,
            'ssid': None,
            'timestamp': None,
            'tsf_timestamp': None
        }

        if hasattr(packet, 'wlan'):
            packet_data_all['bssid'] = getattr(packet.wlan, 'bssid', None)
            
            packet_data_all['transmitter_mac'] = getattr(packet.wlan, 'ta', None)
            packet_data_all['receiver_mac'] = getattr(packet.wlan, 'ra', None)
            packet_data_all['frame_type_subtype'] = getattr(packet.wlan, 'fc_type_subtype', None)
            packet_data_all['retry_flag'] = getattr(packet.wlan, 'fc.retry', None)

        if hasattr(packet, 'wlan_radio'):
            packet_data_all['phy_type'] = getattr(packet.wlan_radio, 'phy', None)
            packet_data_all['mcs_index'] = getattr(packet.wlan_radio, '11ac.mcs_index', None)
            bandwidth = getattr(packet.wlan_radio, '11ac.bandwidth', None)
            packet_data_all['bandwidth'] = "20 MHz" if bandwidth == "0" else bandwidth
            packet_data_all['spatial_streams'] = getattr(packet.wlan_radio, '11ac.num_sts', None)
            packet_data_all['short_gi'] = getattr(packet.wlan_radio, '11ac.short_gi', None)
            packet_data_all['data_rate'] = getattr(packet.wlan_radio, 'data_rate', None)
            packet_data_all['channel'] = getattr(packet.wlan_radio, 'channel', None)
            packet_data_all['signal_strength'] = getattr(packet.wlan_radio, 'signal_dbm', None)
            packet_data_all['snr'] = getattr(packet.wlan_radio, 'snr', None)
            packet_data_all['tsf_timestamp'] = getattr(packet.wlan_radio, 'timestamp', None) 

        if hasattr(packet, 'radiotap'):
            packet_data_all['frequency'] = getattr(packet.radiotap, 'channel_freq', None)

        #this is for ssid eg TUC   
        if 'wlan.mgt' in packet:
            ssid_tag = packet['wlan.mgt'].get('wlan.tag', None)
            #timestamps =packet['wlan.mgt'].get('wlan_fixed_timestamp', None)
            #print(f"this is the {timestamps}\n\n")
            #packet_data_all['timestamp'] = timestamps
            if ssid_tag and 'SSID parameter set:' in ssid_tag:
                packet_data_all['ssid'] = ssid_tag.split('SSID parameter set: ')[-1].strip('"')
            else:
                packet_data_all['ssid'] = None  
        extracted_data_all.append(packet_data_all)
        
        if packet_data_all['mcs_index'] is None:
            packet_data_all['mcs_index'] = 7


    capture.close()
    return extracted_data_all

def replace_phy_type_5_with_7(data_all: list) -> list:
    for packet in data_all:
        if packet.get('phy_type') == '5':  
            packet['mcs_index'] = 7
        else: 
            packet['mcs_index'] = 1
    return data_all

def find_spatial_streams(data_all: list) -> list:
    """
    If the spatial streams inforamtion is missing, find the spatial streams based on table[4]
    with MCS index.

    Args:
        data_all (list): list of dictionaries with the extracted data from extract_all_data()

    Returns:
        List: new list with assigned spatial stream values.
    """
    for packet in data_all:
        if packet.get('spatial_streams') is None and packet.get('mcs_index') is not None:
            try:
                mcs_index = int(packet['mcs_index'])  
                if 1 <= mcs_index <= 7:
                    packet['spatial_streams'] = 1
                elif 8 <= mcs_index <= 15:
                    packet['spatial_streams'] = 2
                elif 16 <= mcs_index <= 23:
                    packet['spatial_streams'] = 3
            except ValueError:
                pass 
        else:
            packet['spatial_streams'] = 1


    return data_all

#briskei to expected mcs index basei to rssi tou pinaka
def find_expected_mcs_index(signal_strength, spatial_streams):

    if spatial_streams == 1:          
        if signal_strength >= -64:
            return 7  
        elif -65 <= signal_strength < -64:
            return 6 
        elif -66 <= signal_strength < -65:
            return 5
        elif -70 <= signal_strength < -66:
            return 4
        elif -74 <= signal_strength < -70:
            return 3
        elif -77 <= signal_strength < -74:
            return 2
        elif -79 <= signal_strength < -77:
            return 1
        else:
            return 0
    if spatial_streams == 2:
        if signal_strength >= -64:
            return 15   
        elif -65 <= signal_strength < -64:
            return 14 
        elif -66 <= signal_strength < -65:
            return 13
        elif -70 <= signal_strength < -66:
            return 12
        elif -74 <= signal_strength < -70:
            return 11
        elif -77 <= signal_strength < -74:
            return 10
        elif -79 <= signal_strength < -77:
            return 9
        else:
            return 8
    if spatial_streams == 3:
        if signal_strength >= -64:
            return 23  
        elif -65 <= signal_strength < -64:
            return 22 
        elif -66 <= signal_strength < -65:
            return 21
        elif -70 <= signal_strength < -66:
            return 20
        elif -74 <= signal_strength < -70:
            return 19
        elif -77 <= signal_strength < -74:
            return 18
        elif -79 <= signal_strength < -77:
            return 17
        else:
            return 16

#bazei rate gap sto data[dict]
def add_rate_gap(data_all: list) -> list:

    for packet in data_all:
        if packet.get('spatial_streams') is None and packet.get('mcs_index') is not None:
            try:
                mcs_index = int(packet['mcs_index'])
                if 1 <= mcs_index <= 7:
                    packet['spatial_streams'] = 1
                elif 8 <= mcs_index <= 15:
                    packet['spatial_streams'] = 2
                elif 16 <= mcs_index <= 23:
                    packet['spatial_streams'] = 3
                else:
                    packet['spatial_streams'] = None
            except ValueError:
                packet['spatial_streams'] = None
        
        if packet.get('signal_strength') is not None and packet.get('spatial_streams') is not None:
            try:
                signal_strength = int(packet['signal_strength'])
                spatial_streams = int(packet['spatial_streams'])
                expected_mcs_index = find_expected_mcs_index(signal_strength, spatial_streams)

                # Compute the rate gap
                actual_mcs_index = int(packet['mcs_index']) if packet.get('mcs_index') is not None else 0
                packet['rate_gap'] = find_rate_gap(expected_mcs_index, actual_mcs_index)

            except (ValueError, TypeError):
                packet['rate_gap'] = None  

    return data_all


## ORIZOUME EMEIS ENA BASELINE -> kinito dipla sto router einai to ideal
## MCS INDEX
def find_rate_gap(expected_mcs_index, actual_mcs_index):

    return expected_mcs_index-actual_mcs_index

def filter_for_1_2(data_all: list, source_mac: str, dest_mac: str, filter) -> list:
    """
    filters the packets with the corresponding sa mac and ta mac with a specific filter 

    Args:
        data_all (list): list of dictionaries with the extracted data from extract_all_data()
        source_mac (str): The sa MAC address to filter.
        dest_mac (str): The ta MAC address to filter.

    Returns:
        List: filtered list with only packets matching the source and destination MAC addresses.
    """
    filtered_packets = [
        packet for packet in data_all
        if packet.get("transmitter_mac") == source_mac and packet.get("receiver_mac") == dest_mac and packet.get("phy_type") == filter
    ]
    return filtered_packets

def no_filter_for_1_2(data_all: list, source_mac: str, dest_mac: str) -> list:
    """
    filters the packets with the corresponding sa mac and ta mac with a specific filter 

    Args:
        data_all (list): list of dictionaries with the extracted data from extract_all_data()
        source_mac (str): The sa MAC address to filter.
        dest_mac (str): The ta MAC address to filter.

    Returns:
        List: filtered list with only packets matching the source and destination MAC addresses.
    """
    filtered_packets = [
        packet for packet in data_all
        if packet.get("transmitter_mac") == source_mac and packet.get("receiver_mac") == dest_mac 
    ]
    return filtered_packets

if __name__ == "__main__":
    print("eimai kainourgio")
    pcap_file = 'pcap_files/1_2_test_pcap1.pcap'  
    data = extract_all_data_testing_pcap(pcap_file)
    data = find_spatial_streams(data)
    data = add_rate_gap(data)
    
   

    #filter beacon frames
    #beacon_frame_data = filter_beacon_frames(data)

    communication_packets = no_filter_for_1_2(data, "d0:b6:6f:96:2b:bb", "dc:e9:94:2a:68:31")
    

    print("\nBeacon Frames:")
    for i, packet_info in enumerate(communication_packets):
        #if((packet_info['mcs_index'] != '130') and (packet_info['short_gi'] == False)):
        print(f"Packet #{i+1}: {packet_info}")

