import matplotlib.pyplot as plt
import pandas as pd 
import os 
from matplotlib.backends.backend_pdf import PdfPages

class ReportingManager:
    def __init__(self, solution, config, base_path, shortage, availability_dict):
        ### Arguments : 
        self.solution = solution
        self.workers_list = sorted(list(set(availability_dict.keys())))
        self.config = config
        self.base_path = base_path
        self.availability = availability_dict
        self.s_worker = shortage['worker']
        self.s_till = shortage['till']
        self.s_manager = shortage['manager']

        ### Config parameters
        self.days = config["structure"]["days"]
        self.time_labels = config["structure"]["time_labels"]
        self.roles = config["structure"]["roles"]
        ### Shadow call at initialization 
        self.df_schedule = self.generate_schedule()

    def generate_schedule(self) -> pd.DataFrame: 
        """Generate a dataframe representing the staff schedule based on the solution from the optimization model."""
        worker_schedule = []
        
        for i in self.workers_list:
            ### Start the row with the worker's name
            row = {"Staff Name": i}
            
            for idx, day in enumerate(self.days):
                day_status = []
                for t in self.time_labels.keys():
                    for role in self.roles:
                        ### Check if this worker is assigned to this day/time/role
                        if self.solution[i][idx][t][role].varValue == 1:
                            day_status.append(f"{self.time_labels[t]}")

                row[day] = ", ".join(day_status) if day_status else "-"
            worker_schedule.append(row)

        df_schedule = pd.DataFrame(worker_schedule) ### Df with rows staff name and columns are days 

        return df_schedule
        
    def save_schedule_toxl(self) -> str:
        """Save the final schedule: Headers and Staff Names are locked. Shifts are editable."""
        excel_file_path = os.path.join(self.base_path, "outputs", "Weekly_Staff_Schedule.xlsx")
        
        with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
            self.df_schedule.to_excel(writer, index=False, sheet_name='Staff Schedule')
            
            workbook  = writer.book
            worksheet = writer.sheets['Staff Schedule']

            # 1. Styles
            header_fmt = workbook.add_format({
                'bold': True, 'align': 'center', 'bg_color': '#4F81BD', 
                'font_color': 'white', 'border': 1, 'locked': True
            })
            
            # Locked format for Column 0 (Staff Names)
            locked_col_fmt = workbook.add_format({
                'bg_color': '#F2F2F2', 'border': 1, 'locked': True
            })
            
            # Unlocked format for the schedule grid
            editable_fmt = workbook.add_format({
                'border': 1, 'locked': False 
            })

            # 2. Format Headers
            for col_num, value in enumerate(self.df_schedule.columns.values):
                worksheet.write(0, col_num, value, header_fmt)

            # 3. Apply Column-Specific Protection
            for row_num in range(1, len(self.df_schedule) + 1):
                for col_num in range(len(self.df_schedule.columns)):
                    cell_value = self.df_schedule.iloc[row_num-1, col_num]
                    
                    # If it's the first column (Staff Name), lock it
                    if col_num == 0:
                        worksheet.write(row_num, col_num, cell_value, locked_col_fmt)
                    else:
                        # Otherwise, let the manager edit the shifts
                        worksheet.write(row_num, col_num, cell_value, editable_fmt)

            # UI Polish
            worksheet.set_column(0, 0, 25) # Give the Staff Name column more room
            worksheet.set_column(1, len(self.df_schedule.columns) - 1, 18)
            
            # 4. Activate Protection
            worksheet.protect()

        print(f"✔ Final Schedule saved. Staff names are locked! Path: {excel_file_path}")
        return excel_file_path
    
    def save_schedule_pdf(self) -> None:
        """
        Save the staff schedule as a nicely formatted PDF.
        """

        output_dir = os.path.join(self.base_path, "outputs")
        os.makedirs(output_dir, exist_ok=True)

        pdf_file = os.path.join(output_dir, "Weekly_Staff_Schedule.pdf")

        ### Create a PDF 
        with PdfPages(pdf_file) as pdf:
            fig, ax = plt.subplots(
                figsize=(12, len(self.df_schedule) * 0.5 + 2)
            )

            ax.axis('off')  # Hide axes

            # Build table
            table = ax.table(
                cellText=self.df_schedule.values,
                colLabels=self.df_schedule.columns,
                cellLoc='center',
                loc='center'
            )

            # Styling
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.auto_set_column_width(
                col=list(range(len(self.df_schedule.columns)))
            )

            # Header & row styling
            for (i, j), cell in table.get_celld().items():
                if i == 0:  # header row
                    cell.set_fontsize(12)
                    cell.set_text_props(weight='bold', color='white')
                    cell.set_facecolor('#4F81BD')  
                else:
                    cell.set_facecolor(
                        '#DCE6F1' if i % 2 == 0 else 'white'
                    )

            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()

        print(f"PDF schedule saved to: {pdf_file}")
    

    def save_reporting(self) -> None: 
        """Save the shortage report as a text file."""

        report_file = os.path.join(self.base_path,"outputs", "Shortage_Report.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("========================================\n")
            f.write("           BAR SHORTAGE REPORT\n")
            f.write("========================================\n\n")
            
            total_shortages_found = False
            for idx, day in enumerate(self.days):
                daily_logs = []
                daily_logs_manager = []
                for t in self.time_labels.keys():
                    ### Check for manager shortages
                    if self.s_manager[idx][t].varValue and self.s_manager[idx][t].varValue > 0:
                        daily_logs_manager.append(f"  ! {int(self.s_manager[idx][t].varValue)} Managers: Missing in day {self.days[idx]} at {self.time_labels[t]}\n")
                        total_shortages_found = True
                    ### Check for worker shortages by role
                    for role in self.roles:
                        shortage_val = self.s_worker[idx][t][role].varValue
                        if shortage_val and shortage_val > 0:
                            daily_logs.append(f"  ! {self.time_labels[t]} - {role}: Missing {int(shortage_val)}")
                            total_shortages_found = True
                
                if daily_logs:
                    f.write(f">>> {self.days[idx].upper()}\n")
                    f.write("\n".join(daily_logs) + "\n\n")
                if daily_logs_manager:
                    f.write("\n".join(daily_logs_manager) + "\n\n")
                daily_logs.clear()
                daily_logs_manager.clear()
                if self.s_till[idx].varValue and self.s_till[idx].varValue > 0:
                    f.write(f"  ! Tills: Missing {int(self.s_till[idx].varValue)}\n")
                    total_shortages_found = True

            if not total_shortages_found:
                f.write("All shifts successfully filled. No shortages detected.\n")

        print(f"✔ Shortage report saved to: {report_file}")
    
    
