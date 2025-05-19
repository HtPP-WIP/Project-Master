import os
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

def parse_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str, TIME_FORMAT)
    except (ValueError, TypeError):
        return datetime.min

def get_latest_json_per_serial(serial_dir):
    file_times = []
    for file in os.listdir(serial_dir):
        if not file.endswith('.json'):
            continue
        
        file_path = os.path.join(serial_dir, file)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                ts = parse_timestamp(data.get('stateTs', ''))
                file_times.append((ts, file_path, data))
        except Exception as e:
            print(f"Error reading {file_path}: {str(e)}")
            continue
    
    if file_times:
        latest_file = max(file_times, key=lambda x: x[0])
        print(f"Found {len(file_times)} files in '{os.path.basename(serial_dir)}', use latest: '{latest_file[0]}'")
        return latest_file
    else:
        return None

def collect_chip_data(type_dir, result_num):
    chip_data = defaultdict(lambda: defaultdict(list))
    result_num_int = int(result_num)
    valid_files = 0
    result_name = None  
    
    for sn in os.listdir(type_dir):
        sn_path = os.path.join(type_dir, sn)
        if not os.path.isdir(sn_path):
            continue
        
        latest_json = get_latest_json_per_serial(sn_path)
        if not latest_json:
            continue
            
        _, file_path, data = latest_json
        
        try:
            result_entry = data['results'][result_num_int]
            array_dims = result_entry['arrayDimensions']
            if array_dims == 3:
                print(f"{file_path} arrayDimensions = 3, skip")
                continue
            elif array_dims != 2:
                print(f"File {file_path} arrayDimensions is {array_dims}, skip")
                continue
            
            values = result_entry['value']
            if len(values) != 25:
                print(f"{file_path} has {len(values)} tests, skip")
                continue
            
            if result_name is None:
                result_name = result_entry['name']
            
            valid_files += 1
            for test_num, test_values in enumerate(values, 1):
                for chip_idx, value in enumerate(test_values):
                    chip_data[chip_idx][test_num].append(float(value))
        except (KeyError, IndexError, ValueError, TypeError) as e:
            print(f"File {file_path} wrong: {str(e)}, skip")
            continue
    
    print(f"\nValid merged data: {valid_files}")
    return (chip_data, result_name) if chip_data else (None, None)

def plot_chip_means(chip_data, output_path, type, result_name):
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    plt.figure(figsize=(12, 9))
    
    test_numbers = sorted({tn for chip in chip_data.values() for tn in chip.keys()})
    
    for chip_idx, test_data in sorted(chip_data.items()):
        x = []
        y = []
        y_err = []
        
        for test_num in test_numbers:
            values = test_data.get(test_num, [])
            if values:
                x.append(test_num)
                y.append(np.mean(values))
                y_err.append(np.std(values) / np.sqrt(len(values))) 
        
        plt.errorbar(x, y, yerr=y_err,
                    linestyle='none',
                    fmt='-o',
                    label=f'Chip {chip_idx}',
                    capsize=4,
                    elinewidth=1.2,
                    markersize=8)
    ylabel = "Value"
    if result_name.lower().startswith("gain"):
        ylabel = "Gain (mV/fC)"
    elif result_name.lower().startswith("innse"):
        ylabel = "Input noise (ENC)"
    elif result_name.lower().startswith("vt50"):
        ylabel = "Vt50 (mV)"
    plt.title(f"{type} Chip Performance {result_name}", fontsize=14)
    plt.xlabel('Test Sequence', fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.xticks(test_numbers)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='best')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    type_dir = input("Input the type directory: ").strip()
    result_num = input("Input the results index: ").strip()
    output_dir = "chip_analysis"
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(type_dir):
        print(f"Error: directory {type_dir} does not exist")
        return
    
    print("Collecting data...")
    chip_data, result_name = collect_chip_data(type_dir, result_num)
    if chip_data is None:
        return
    
    print(f"{len(chip_data)} ABCs detected")

    type_name = os.path.basename(type_dir.rstrip('/'))
    output_path = os.path.join(output_dir, f"{type_name}_{result_name}.png")
    plot_chip_means(chip_data, output_path, type_name, result_name)
    print(f"\nFigure saved: {output_path}")

if __name__ == "__main__":
    main()