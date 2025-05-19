import os
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D    
import numpy as np
import re
from typing import List, Any

def nested_value(data: dict, path: list) -> Any:       #decode the path of info
    current = data
    try:
        for key in path:
            if isinstance(current, list):
                current = current[int(key)]
            else:
                current = current[key]
        return current
    except (KeyError, IndexError, TypeError, ValueError):
        return None

def get_result_name(data: dict, num: str) -> str:
    name = nested_value(data, ['results', num, 'name'])
    if name:
        return name
    return "unnamed"

def filename(base_name: str, result_name: str) -> str:
    return f"{base_name}_{result_name}.png"

def find_json(input_type: str, input_sn: str) -> List[str]:
    json_files = []
    print(f"\n=== Start Search ===")
    print(f"Type: {input_type}")
    print(f"SerialNumber: {input_sn}")

    # input Type & SerialNumber
    if input_type and input_sn:
        path = os.path.join(input_type, input_sn)
        print(f"Find the accurate path:{path}")
        if os.path.exists(path):
            json_files = [os.path.join(path, f) for f in os.listdir(path) 
                         if f.endswith('.json')]
    
    # input Type
    elif input_type:
        type_dir = input_type
        if os.path.exists(type_dir):
            for sn in os.listdir(type_dir):
                sn_path = os.path.join(type_dir, sn)
                if os.path.isdir(sn_path):
                    json_files.extend([os.path.join(sn_path, f) for f in os.listdir(sn_path)
                                     if f.endswith('.json')])
    
    # input SerialNumber
    elif input_sn:
        print(f"Scan Type directory: {input_type}")
        for type_dir in os.listdir('.'):
            if os.path.isdir(type_dir):
                sn_path = os.path.join(type_dir, input_sn)
                if os.path.exists(sn_path):
                    json_files.extend([os.path.join(sn_path, f) for f in os.listdir(sn_path)
                                     if f.endswith('.json')])
    
    return json_files

def parse_data_path(input_str: str) -> tuple:          #decode the input number and locate the data
    num = re.findall(r'\d+', input_str)
    if len(num) != 1:
        raise ValueError("Please input a number")
    return (['results', num[0], 'value'], num[0])

def extract(data: dict, base_path: list) -> list:     #extract test data
    current = data
    try:
        for key in base_path:                 #locating
            if isinstance(current, list):
                current = current[int(key)]
            else:
                current = current[key]
                
        if not isinstance(current, list) or len(current) != 25:     #checking data structure
            return []
        
        processed_data = []
        for test_data in current:
            if isinstance(test_data, list) and all(isinstance(x, (int, float)) for x in test_data):  #array: 2D
                processed_data.append(test_data)
            elif isinstance(test_data, list) and all(isinstance(chip, list) for chip in test_data):  #array: 3D
                flattened = [item for chip in test_data for item in chip]
                processed_data.append(flattened)
            else:
                return []
        return processed_data
        
    except (KeyError, IndexError, ValueError, TypeError) as e:
        print(f"Data parsing error：{str(e)}")
        return []

def info(data: dict) -> tuple:
    # first line
    test_type = nested_value(data, ['testType', 'name']) or "Unknown Test"
    points = len(nested_value(data, ['properties', '4', 'value', 'points']) or 0)
    run_number = nested_value(data, ['runNumber']) or "Unknown"
    line1 = f"{test_type}, {points}-point gain, Run Number: {run_number}"

    # second line
    dut_type = nested_value(data, ['properties', '1', 'value', 'DUT_type']) or "Unknown"
    dut_name = nested_value(data, ['properties', '1', 'value', 'name']) or "Unknown"
    institution = nested_value(data, ['institution', 'name']) or "Unknown"
    parent_code = nested_value(data, ['components', '0', 'ancestorMap', 'parent', 'component', 'type', 'code']) or "Unknown"
    parent_sn = nested_value(data, ['components', '0', 'ancestorMap', 'parent', 'component', 'serialNumber']) or "Unknown"
    line2 = f"{dut_type}  {dut_name}, {institution}, Parent: {parent_code}  {parent_sn}"

    # third line
    all_tests = nested_value(data, ['properties', '3', 'value', 'all_tests']) or []
    failed_tests = nested_value(data, ['properties', '3', 'value', 'failed_tests']) or []
    test_positions = sorted([all_tests.index(t)+1 for t in failed_tests if t in all_tests])
    failed_str = ', '.join(map(str, test_positions)) if test_positions else 'None'
    passed_status = "Passed" if nested_value(data, ['passed']) is True else "Failed"
    line3 = f"TC Status: {passed_status}, Failed tests: {failed_str}"

    return (line1, line2, line3)

def temperature(data: dict) -> list:
    temps = nested_value(data, ['properties', '0', 'value', 'AMAC_NTCy'])
    if isinstance(temps, list) and len(temps) == 25:
        return [float(t) for t in temps if isinstance(t, (int, float))]
    return []

def failed_indices(data: dict) -> list:
    all_tests = nested_value(data, ['properties', '3', 'value', 'all_tests']) or []
    failed_tests = nested_value(data, ['properties', '3', 'value', 'failed_tests']) or []
    return [i+1 for i, t in enumerate(all_tests) if t in failed_tests]  

def plot_boxplot(data: list, temps: list, save_path: str, result_name: str, info_lines: tuple, yname: str, failed_indices: list):
    plt.figure(figsize=(12, 8))
    ax = plt.gca()

    colors = []                       
    for t in temps[:len(data)]:  
        if t > 0:
            colors.append('#CC7306')  
        else:
            colors.append('#4D96FF')  
    
    box = plt.boxplot(data, 
                    patch_artist=True,
                    showfliers=False,
                    widths=0.7)
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('black')
    for element in ['whiskers', 'caps', 'medians']:
        plt.setp(box[element], color='#2D4059', linewidth=1.5)
    
    # mark failed tests
    for i, (patch, median_line) in enumerate(zip(box['boxes'], box['medians'])):
        if (i+1) in failed_indices:  # index for boxplot begin from 1 in mat
            patch.set_hatch('////')
            patch.set_edgecolor('black')
            median_line.set_linewidth(3)
    
    y_min, y_max = ax.get_ylim()
    # mark shunty tests
    shunted_tests = [3, 23]  
    for test_num in shunted_tests:
        idx = test_num - 1  
        if idx >= len(data):
            continue
        median = box['medians'][idx]
        x = median.get_xdata()[1]
        y = y_min + 1
        ax.scatter(x - 0.35, y,
                  marker='^',
                  s=200,
                  color='#2A9D8F',
                  edgecolors='black',
                  zorder=4,
                  label=f'Shunted Test {test_num}' if idx == 2 else "")
    
    # embed info (adjust the position)
    text_params = {
        'fontsize': 12,
        'ha': 'left',
        'va': 'bottom',
        'bbox': dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='lightgray'),
        'linespacing': 1.5
    }
    base_y = y_max + 0.1*(y_max - y_min)  
    ax.text(0.8,  
          base_y,
          info_lines[0],
          **text_params)
    ax.text(0.8,
          base_y - 0.06*(y_max - y_min),
          info_lines[1],
          **text_params)
    ax.text(0.8,
          base_y - 0.12*(y_max - y_min),
          info_lines[2],
          **text_params)
    new_ymax = base_y + 0.05*(y_max - y_min)
    ax.set_ylim(y_min, max(y_max, new_ymax))

    legend_elements = [
        Patch(facecolor='#CC7306', edgecolor='#2D4059', label='Warm Test (T > 0℃)'),
        Patch(facecolor='#4D96FF', edgecolor='#2D4059', label='Cold Test (T < 0℃)'),
        Patch(facecolor='white', edgecolor='black', hatch='////', label='Failed Test'),
        Line2D([0], [0], marker='^',color='w',markerfacecolor='#2A9D8F',markersize=15,label='Shunted Tests')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)
    plt.title(f"Thermal Cycle Analysis: {result_name}", fontsize=16, pad=1, y=1.02)
    plt.xlabel('Test Sequence', fontsize=14)
    plt.ylabel(f"{yname}", fontsize=14)
    plt.xticks(range(1, 26), [f"T{i:02d}" for i in range(1, 26)])
    
    for i, test_data in enumerate(data):
        median = np.median(test_data)
        plt.text(i+1, median, f'{median:.2f}', 
                horizontalalignment='center',
                fontsize=8)
    
    plt.grid(True, linestyle='--', alpha=0.6, axis='y')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Figure saved：{save_path}")

def main():
    input_type = input("Input your Type (Press enter to skip): ").strip()
    input_sn = input("Input your SerialNumber (Press enter to skip): ").strip()
    data_path = input("Input the index of the data: ").strip()
    
    try:
        base_path, input_num = parse_data_path(data_path)
        files = find_json(input_type, input_sn)
        
        if not files:
            print("No matching JSON file found")
            return
        
        for file in files:
            with open(file, 'r') as f:
                data = json.load(f)
                plot_data = extract(data, base_path)
                temps = temperature(data)
                failed_index = failed_indices(data)
                if not plot_data or len(temps) != 25:
                    print(f"File {file} data is invalid (doesn't have 25 tests)")
                    continue
                result_name = get_result_name(data, input_num)
                if result_name.startswith("gain"):
                    yname = "Gain (mV/fC)"
                elif result_name.startswith("innse"):
                    yname = "Input noise (ENC)"
                elif result_name.startswith("vt50"):
                    yname = "Vt50 (mV)"
                base_name = os.path.splitext(os.path.basename(file))[0]
                output_file = filename(base_name, result_name)
                output_dir = os.path.join("plots", os.path.dirname(file))
                os.makedirs(output_dir, exist_ok=True)
                full_path = os.path.join(output_dir, output_file)
                info_lines = info(data)
                plot_boxplot(plot_data, temps, full_path, result_name, info_lines, yname, failed_indices=failed_index)

    except Exception as e:
        print(f"Runtime Error：{str(e)}")

if __name__ == "__main__":
    main()