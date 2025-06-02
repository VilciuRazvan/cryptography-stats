import pandas as pd
from typing import Dict, List, Any

def export_results_to_excel(all_run_data: Dict[str, List[Dict]], 
                          excel_filename: str,
                          calculate_statistics) -> Dict[str, Dict]:
    """
    Export test results to Excel and return summary statistics.
    
    Args:
        all_run_data: Dictionary containing test results for each configuration
        excel_filename: Name of the Excel file to create
        calculate_statistics: Function to calculate statistics on data sets
    
    Returns:
        Dictionary containing summary statistics for all configurations
    """
    print(f"\n\n========= Processing Results & Exporting to {excel_filename} =========")
    all_stats_summary = {}  # For final console printout

    try:
        with pd.ExcelWriter(excel_filename, engine='openpyxl', mode='w') as writer:
            for config_name, results_list in all_run_data.items():
                if not results_list:
                    print(f"No data collected for {config_name}, skipping sheet.")
                    continue

                # Convert list of dictionaries to DataFrame
                df = pd.DataFrame(results_list)
                df = df[['iteration', 'handshake', 'puback', 'total', 'error']]

                # Calculate statistics
                handshake_stats = calculate_statistics(df['handshake'].tolist())
                puback_stats = calculate_statistics(df['puback'].tolist())
                total_stats = calculate_statistics(df['total'].tolist())
                successful_runs = handshake_stats['Count']
                failed_runs = len(df) - successful_runs

                # Prepare Stats DataFrame
                stats_data = {
                    'Metric': [
                        'Successful Runs', 'Failed Runs', '',
                        'Handshake Mean', 'Handshake Median', 'Handshake StdDev',
                        'Handshake Min', 'Handshake Max', 'Handshake 95th %', '',
                        'PubAck Mean', 'PubAck Median', 'PubAck StdDev',
                        'PubAck Min', 'PubAck Max', 'PubAck 95th %', '',
                        'Total Mean', 'Total Median', 'Total StdDev',
                        'Total Min', 'Total Max', 'Total 95th %'
                    ],
                    'Value': [
                        successful_runs, failed_runs, '',
                        handshake_stats['Mean'], handshake_stats['Median'], handshake_stats['StdDev'],
                        handshake_stats['Min'], handshake_stats['Max'], handshake_stats['95th percentile'], '',
                        puback_stats['Mean'], puback_stats['Median'], puback_stats['StdDev'],
                        puback_stats['Min'], puback_stats['Max'], puback_stats['95th percentile'], '',
                        total_stats['Mean'], total_stats['Median'], total_stats['StdDev'],
                        total_stats['Min'], total_stats['Max'], total_stats['95th percentile']
                    ]
                }
                stats_df = pd.DataFrame(stats_data)

                # Write to Excel
                df.to_excel(writer, sheet_name=config_name, index=False, startrow=0, startcol=0)
                stats_df.to_excel(writer, sheet_name=config_name, index=False, startrow=0, startcol=6)

                # Store summary statistics
                all_stats_summary[config_name] = {
                    'Handshake Mean': handshake_stats['Mean'],
                    'Handshake Median': handshake_stats['Median'],
                    'Handshake StdDev': handshake_stats['StdDev'],
                    'PubAck Mean': puback_stats['Mean'],
                    'PubAck Median': puback_stats['Median'],
                    'PubAck StdDev': puback_stats['StdDev'],
                    'Total Mean': total_stats['Mean'],
                    'Total Median': total_stats['Median'],
                    'Total StdDev': total_stats['StdDev'],
                    'Successful Runs': successful_runs,
                    'Failed Runs': failed_runs
                }

                print(f"  Sheet '{config_name}' written with data and statistics.")

        print(f"Excel file '{excel_filename}' created successfully.")
        
        # Print summary statistics
        print("\n\n========= FINAL SUMMARY STATISTICS (CONSOLE) =========")
        summary_df_console = pd.DataFrame.from_dict(all_stats_summary, orient='index')
        pd.set_option('display.float_format', '{:.6f}'.format)
        pd.set_option('display.width', 120)
        print(summary_df_console)

        return all_stats_summary

    except Exception as e:
        print(f"\nError writing to Excel file: {e}")
        print("Check if the file is open or if you have write permissions.")
        return {}