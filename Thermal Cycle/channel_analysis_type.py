import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime


WARM_TESTS = {1,4,6,8,10,12,14,16,18,20,22,25}
COLD_TESTS = {2,3,5,7,9,11,13,15,17,19,21,23,24}
sq = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25]

def parse_iso_time(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except ValueError:
        return None

def find_latest_valid_json(sn_dir, required_test_count=25):
    valid_files = []
    total_files = 0
    
    for json_file in sn_dir.glob('*.json'):
        total_files += 1
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                tests = data['properties'][3]['value']['all_tests']
                if len(tests) != required_test_count:
                    continue
                
                state_ts = data.get('stateTs')
                if not state_ts:
                    continue
                    
                file_time = parse_iso_time(state_ts)
                if not file_time:
                    continue
                
                valid_files.append((file_time, json_file))
                
        except Exception as e:
            print(f"跳过损坏文件 {json_file}: {str(e)}")
    
    print(f"Found {total_files} files in {sn_dir.name}, {len(valid_files)} valid files")
    if valid_files:
        valid_files.sort(key=lambda x: x[0])
        latest_file = valid_files[-1][1]
        print(f"Use latest: {latest_file.name}, time: {valid_files[-1][0]}")
        return latest_file
    return None

def calculate_max_consecutive(channels):
    if not channels:
        return 0
    
    sorted_channels = sorted(channels)
    max_count = current = 1
    for i in range(1, len(sorted_channels)):
        if sorted_channels[i] == sorted_channels[i-1] + 1:
            current += 1
            max_count = max(max_count, current)
        else:
            current = 1
    return max_count

def process_defect_file(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    all_tests = data['properties'][3]['value']['all_tests']
    test_name_to_index = {test: idx for idx, test in enumerate(all_tests)}
    
    records = []
    seen = set()
    
    for defect in data.get('defects', []):
        props = defect.get('properties', {})
        run_num = props.get('runNumber')
        test_type = props.get('testType')
        
        if not run_num or not test_type:
            continue
            
        full_test_name = f"{run_num}_{test_type}"
        test_index = test_name_to_index.get(full_test_name)
        
        if test_index is None:
            continue
        
        channels = []
        if 'channel_from' in props and 'channel_to' in props:
            channels = range(props['channel_from'], props['channel_to']+1)
        elif 'channel' in props:
            channels = [props['channel']]
        else:
            continue
        
        for ch in channels:
            unique_key = (test_index, ch)
            if unique_key not in seen:
                seen.add(unique_key)
                records.append({
                    'test_index': test_index,
                    'test_name': full_test_name,
                    'channel': ch
                })
    
    return pd.DataFrame(records)

def create_module_level_plots(type_name, all_data):
    if not all_data:
        print(f"No valid data found for type {type_name}")
        return None, None, None
    
    total_stats = []
    consecutive_stats = []
    distribution_data = defaultdict(lambda: defaultdict(int))
    consecutive_dist_data = defaultdict(lambda: defaultdict(int))
    
    for sn, df in all_data.items():
        grouped = df.groupby('test_index')
        
        test_stats = grouped.agg(
            total_bad=('channel', 'count'),
            test_name=('test_name', 'first'),
            channels=('channel', list)
        ).reset_index()
        test_stats['max_consecutive'] = test_stats['channels'].apply(
            lambda x: calculate_max_consecutive(x)
        )
        
        for _, row in test_stats.iterrows():
            total_stats.append({
                'test_index': row['test_index'],
                'test_name': row['test_name'],
                'SN': sn,
                'TotalBad': row['total_bad']
            })
            
            consecutive_stats.append({
                'test_index': row['test_index'],
                'test_name': row['test_name'],
                'SN': sn,
                'MaxConsecutive': row['max_consecutive']
            })
            
            distribution_data[row['test_index']][row['total_bad']] += 1
            consecutive_dist_data[row['test_index']][row['max_consecutive']] += 1
    
    total_df = pd.DataFrame(total_stats).sort_values('test_index')
    consecutive_df = pd.DataFrame(consecutive_stats).sort_values('test_index')
    colors = ['#FF6B6B' if num in WARM_TESTS else '#4D96FF' for num in sq]
    
    # bad channel box
    plt.figure(figsize=(12, 9))
    plot_data = []
    positions = []
    colors = []
    for test_index in sorted(total_df['test_index'].unique()):
        subset = total_df[total_df['test_index'] == test_index]['TotalBad']
        plot_data.append(subset)
        positions.append(test_index)
        colors.append('#FF6B6B' if test_index in WARM_TESTS else '#4D96FF')
    box = plt.boxplot(
        plot_data,
        positions=positions,
        whis=1.5,
        patch_artist=True,
        widths=0.6,
        showfliers=False
    )
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('black')
    plt.title(f'Total Bad Channels by Test - {type_name}', fontsize=14)
    plt.ylabel('Total Bad Channels', fontsize=12)
    plt.xlabel('Test Sequence Number', fontsize=12)
    plt.xticks(positions, [f"T{i:02d}" for i in positions])
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    total_box = plt.gcf()
    
     # consecutive bad channel box
    plt.figure(figsize=(12, 9))
    plot_data = []
    positions = []
    colors = []
    for test_index in sorted(consecutive_df['test_index'].unique()):
        subset = consecutive_df[consecutive_df['test_index'] == test_index]['MaxConsecutive']
        plot_data.append(subset)
        positions.append(test_index)
        colors.append('#FF6B6B' if test_index in WARM_TESTS else '#4D96FF')
    box = plt.boxplot(
        plot_data,
        positions=positions,
        patch_artist=True,
        widths=0.6,
        showfliers=True
    )
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('black')
    plt.title(f'Max Consecutive Bad Channels by Test - {type_name}')
    plt.ylabel('Max Consecutive Bad Channels')
    plt.xlabel('Test Sequence Number')
    plt.xticks(positions, [f"T{i:02d}" for i in positions])
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    consecutive_box = plt.gcf()
    
    # distribution
    fig, axes = plt.subplots(len(distribution_data), 2, 
                       figsize=(20, 3*len(distribution_data)))
    if len(distribution_data) == 1:
        axes = [axes]

    for i, (test_index, counts) in enumerate(sorted(distribution_data.items())):
        test_name = total_df[total_df['test_index'] == test_index]['test_name'].iloc[0]
    
        total_bad_data = []
        for value, freq in counts.items():
            total_bad_data.extend([value] * freq)
    
        axes[i][0].hist(
            total_bad_data,
            bins=50,
            range=(0, 50),
            color='#4D96FF',
            edgecolor='white',
            alpha=0.8
        )
        axes[i][0].axvline(13, color='red', linestyle='--', linewidth=1.5)
        over_threshold = sum(1 for x in total_bad_data if x > 12)
        axes[i][0].text(
            0.95, 0.95, 
            f'Failed hybrids in total: {over_threshold}',
            transform=axes[i][0].transAxes,
            ha='right', va='top',
            fontsize=12,
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray')
        )
        axes[i][0].set_xlim(0, 50)
        axes[i][0].set_title(f'Total Bad Dist - Test {test_index+1}')
        axes[i][0].set_xlabel('Total Bad Channels')
        axes[i][0].set_ylabel('Number of modules')
        axes[i][0].grid(True, linestyle='--', alpha=0.6)
    
        consec_bad_data = []
        consec_counts = consecutive_dist_data[test_index]
        for value, freq in consec_counts.items():
            consec_bad_data.extend([value] * freq)
    
        axes[i][1].hist(
            consec_bad_data,
            bins=50,
            range=(0, 50),
            color='#FF6B6B',
            edgecolor='white',
            alpha=0.8
        )
        axes[i][1].axvline(9, color='blue', linestyle='--', linewidth=1.5)
        over_threshold = sum(1 for x in consec_bad_data if x > 8)
        axes[i][1].text(
            0.95, 0.95,
            f'Failed hybrids in total: {over_threshold}',
            transform=axes[i][1].transAxes,
            ha='right', va='top',
            fontsize=12,
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray')
        )
        axes[i][1].set_xlim(0, 50)
        axes[i][1].set_title(f'Max Consecutive Dist - Test {test_index+1}')
        axes[i][1].set_xlabel('Max Consecutive Bad Channels')
        axes[i][1].set_ylabel('Number of modules')
        axes[i][1].grid(True, linestyle='--', alpha=0.6)

    plt.suptitle(f'Distribution Histograms - {type_name}', y=1.005)
    plt.tight_layout()
    dist_fig = plt.gcf()
    
    return total_box, consecutive_box, dist_fig

def process_type_analysis(base_path, type_name, required_test_count=25):
    type_dir = Path(base_path) / type_name
    if not type_dir.exists():
        print(f"Type directory not found: {type_dir}")
        return None
    
    all_data = {}
    
    for sn_dir in type_dir.iterdir():
        if not sn_dir.is_dir():
            continue
            
        json_file = find_latest_valid_json(sn_dir, required_test_count)
        if not json_file:
            continue
            
        df = process_defect_file(json_file)
        if df.empty:
            continue
            
        all_data[sn_dir.name] = df
    
    return all_data

def main():
    base_path = input("Directory:").strip()
    target_type = input("Type:").strip()
    
    print(f"\nProcessing module-level analysis for: {target_type}")
    all_data = process_type_analysis(base_path, target_type)
    #print(all_data)
    print(len(all_data))
    if all_data:
        total_box, consecutive_box, dist_fig = create_module_level_plots(target_type, all_data)
        output_dir = Path("module_analysis")
        output_dir.mkdir(exist_ok=True)
        
        if total_box:
            total_path = output_dir / f"{target_type}_total_box.png"
            total_box.savefig(total_path, bbox_inches='tight')
            plt.close(total_box)
            print(f"Total bad channels boxplot saved to: {total_path}")
        
        if consecutive_box:
            consec_path = output_dir / f"{target_type}_consecutive_box.png"
            consecutive_box.savefig(consec_path, bbox_inches='tight')
            plt.close(consecutive_box)
            print(f"Max consecutive bad channels boxplot saved to: {consec_path}")
        
        if dist_fig:
            dist_path = output_dir / f"{target_type}_distribution.png"
            dist_fig.savefig(dist_path, bbox_inches='tight')
            plt.close(dist_fig)
            print(f"Distribution plots saved to: {dist_path}")
    else:
        print("No valid data found for analysis")

if __name__ == "__main__":
    main()