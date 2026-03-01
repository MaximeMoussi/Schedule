import pandas as pd
import os 

class StaffManager:
    """Handle all staff-related operations: validation, reconciliation, and modifications."""
    #### Initialization and validation ####
    def __init__(self, paths ,config):
        self.staff_register =  pd.read_csv(os.path.join(paths['data'], config["names_df"]["staff_register"]))### Main database, containing all staff members and their attributes
        self.staff_availability = pd.read_csv(os.path.join(paths['data'], config["names_df"]["staff_availability"]))
        self.need_for_staff = pd.read_csv(os.path.join(paths['data'], config["names_df"]["need_for_staff"]))
        self.config = config
        self.check_headers() ### Raise errors if any of the input files have missing or extra columns

    #### INPUT VALIDATION ####
    def check_headers(self) -> None:
        """Check if the input files have the expected headers as defined in the config file. Raise ValueError if not."""
        headers_map = {
            'staff_register': self.config["headers"]["staff_register"],
            'staff_availability': self.config["headers"]["staff_availability"],
            'need_for_staff': self.config["headers"]["need_for_staff"]
        }
        for key, expected_cols in headers_map.items():
            df = getattr(self, key)
            missing = set(expected_cols) - set(df.columns)
            extra = set(df.columns) - set(expected_cols)
            if missing:
                raise ValueError(f"{key}.csv missing columns: {missing}")
            if extra:
                raise ValueError(f"{key}.csv has extra columns: {extra}")
                
    #### RECONCILIATION ####
    def get_new_workers(self) -> list:
        """Handle case where a worker is in availability but not in the staff register"""
        new_workers = self.staff_availability[~self.staff_availability['Adresse e-mail'].isin(self.staff_register['Email'])]
        return list(set(new_workers['Name']))
    
    def get_ghost_workers(self) -> list:
        """Handle case where a worker is in availability but not in the staff register"""
        old_workers = self.staff_register[~self.staff_register['Email'].isin(self.staff_availability['Adresse e-mail'])]
        return list(set(old_workers['Name']))
    
    ## In place modification of class attributes
    def change_name_in_staff_register(self) -> None:
        """Handle case where a worker changed name but kept the same email"""
        for _, row in self.staff_availability.iterrows():
            email = row['Adresse e-mail']
            name = row['Name']
            if email in self.staff_register['Email'].values:
                self.staff_register.loc[self.staff_register['Email'] == email, 'Name'] = name

    def add_staff(self, name, info) -> None:
        """Add staff into staff registry"""
        new_row = {'Name': name, **info}
        self.staff_register = pd.concat([self.staff_register, pd.DataFrame([new_row])], ignore_index=True)

    def remove_staff(self, name) -> None:
        """Remove staff from staff registry"""
        self.staff_register = self.staff_register[self.staff_register['Name'] != name]

    def update_staff(self, name, info) -> None:
        """Update staff in staff registry"""
        self.staff_register.loc[self.staff_register['Name'] == name, ['Role','Till_Authorized','Is_Manager']] = [
            info['Role'], info['Till_Authorized'], info['Is_Manager']
        ]