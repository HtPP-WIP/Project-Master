import pandas as pd
import matplotlib.pyplot as plt

data = pd.read_excel('R3_39\scan7_s27\R3_39_s27.xlsx', sheet_name='Sheet1', header=None) 
noise_data = data[[0, 1]].dropna().rename(columns={0: 'Threshold', 1: 'NoiseOccupancy'})
efficiency_data = data[[0, 2]].dropna().rename(columns={0: 'Threshold', 2: 'Efficiency'})

noise_data = noise_data.sort_values(by='Threshold')
efficiency_data = efficiency_data.sort_values(by='Threshold')

fig, ax1 = plt.subplots(figsize=(10, 8))

plt.suptitle('ATLAS ITk Working in Progress (private work)', fontsize=14, fontweight='bold')
plt.title('ATLAS ITk beam test, @ DESY TB Dec. 2024, 5 GeV/c electrons, R3_39_s27, ABC: 0,1', fontsize=10)

ax1.set_xlabel('Threshold (DAC)', fontsize=12)
ax1.set_ylabel('Noise Occupancy', color='blue', fontsize=12)
ax1.plot(noise_data['Threshold'], noise_data['NoiseOccupancy'], color='blue', marker='o', linestyle='-', label='Noise Occupancy')
ax1.set_yscale('log')
ax1.set_yticks([1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7])  
ax1.tick_params(axis='y', labelcolor='blue')
ax1.set_xlim(0, 175)
ax1.set_xticks(range(0, 176, 25)) 
ax1.axhline(y=1e-3, color='blue', linestyle='--', label='Noise Cut-off (10^{-3})')

ax2 = ax1.twinx()
ax2.set_ylabel('Efficiency (%)', color='red', fontsize=12)
ax2.plot(efficiency_data['Threshold'], efficiency_data['Efficiency'], color='red', marker='x', linestyle='-', label='Efficiency')
ax2.tick_params(axis='y', labelcolor='red')
ax2.axhline(y=99, color='red', linestyle='--', label='Efficiency Cut-off (99%)')

def interpolate_cutoff(df, x_col, y_col, cutoff, search_direction='right'):
    ascending = True if search_direction == 'left' else False
    sorted_df = df.sort_values(x_col, ascending=ascending).reset_index(drop=True)
    
    if search_direction == 'left':
        condition = lambda y: y <= cutoff  
    else:
        condition = lambda y: y >= cutoff  

    for i in range(len(sorted_df)-1):
        x1, y1 = sorted_df.iloc[i][[x_col, y_col]]
        x2, y2 = sorted_df.iloc[i+1][[x_col, y_col]]
        if (condition(y1) != condition(y2)):
            t = (cutoff - y1)/(y2 - y1)
            return x1 + t*(x2 - x1)
    
    if search_direction == 'left':
        valid_points = sorted_df[sorted_df[y_col] <= cutoff]
        return valid_points[x_col].min() if not valid_points.empty else None
    else:
        valid_points = sorted_df[sorted_df[y_col] >= cutoff]
        return valid_points[x_col].max() if not valid_points.empty else None

noise_cutoff = interpolate_cutoff(
    noise_data, 
    'Threshold', 
    'NoiseOccupancy', 
    cutoff=1e-3,
    search_direction='left'  
)

efficiency_cutoff = interpolate_cutoff(
    efficiency_data,
    'Threshold',
    'Efficiency',
    cutoff=99,
    search_direction='right'  
)
if noise_cutoff is not None and efficiency_cutoff is not None:
    left = min(noise_cutoff, efficiency_cutoff)
    right = max(noise_cutoff, efficiency_cutoff)
    ax1.axvspan(left, right, color='green', alpha=0.3, label='Operating Window')
else:
    print("Warning: no valid OPW")

fig.legend(loc='upper right', bbox_to_anchor=(0.9, 0.82))

if noise_cutoff < efficiency_cutoff:
    window_width = efficiency_cutoff - noise_cutoff
    ax1.text(
        x=147,  
        y=4e-3,  
        s=f'Window range: [{noise_cutoff:.1f}, {efficiency_cutoff:.1f}] DAC',
        ha='center',
        va='bottom',
        color='green',
        fontsize=10,
        bbox=dict(facecolor='white', alpha=0.8)
    )
    ax1.text(
        x=153,  
        y=1.5e-3,  
        s=f'Window width: {window_width:.1f} DAC',
        ha='center',
        va='bottom',
        color='green',
        fontsize=10,
        bbox=dict(facecolor='white', alpha=0.8)
    )
    print(f'OPW range: [{noise_cutoff:.1f}, {efficiency_cutoff:.1f}] DAC')
    print(f'OPW width: {window_width:.1f} DAC')
else:
    print("Warning: no valid operating window, noise threshold higher than efficiency threshold")

plt.savefig('R3_39_s27_0_1.png')