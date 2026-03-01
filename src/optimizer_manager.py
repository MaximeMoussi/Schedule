import pulp
import pandas as pd 
from db_manager import StaffManager

class OptimizerManager:
    def __init__(self, staff_manager: StaffManager):
        self.staff_manager = staff_manager
        ### parameters for the optimization problem
        self.availability, self.need, self.counting, self.manager, self.possible_role = self.create_parameters()
        self.sol, self.s_work, self.s_till, self.s_mana = self.solve()

    def solve(self) -> tuple:
        """ Solve the scheduling optimization problem using PuLP and return the proposed solution and slacks for the shortage in staff, till and manager """
        ### Instantiate the problem 

        prob = pulp.LpProblem("Scheduling_Optimization", pulp.LpMinimize)

        ### Create Indices 
        workers = self.staff_manager.staff_availability["Name"].tolist()

        day_names = self.staff_manager.config['structure']['days'] # Number of working day in a week 
        days = list(range(len(day_names)))
        times = range(self.staff_manager.config['structure']['shifts']) # Number of starting time in a day
        night = self.staff_manager.config['structure']['night_shifts'] # Night shifts indices for flag the 
        roles = self.staff_manager.config['structure']['roles'] # Available role

        ### Create Decision Variables 
        x = pulp.LpVariable.dicts("x", (workers, days, times, roles), cat= pulp.LpBinary)
        s_work = pulp.LpVariable.dicts("s_work", (days, times, roles), lowBound= 0, cat= pulp.LpInteger)
        s_till = pulp.LpVariable.dicts("s_till", (days), lowBound= 0, cat= pulp.LpInteger)
        s_mana = pulp.LpVariable.dicts("s_mana", (days,times), lowBound= 0, cat= pulp.LpInteger)

        ### Create the objective (simple objective thata ca n be enhanced )

        shortage_penality = pulp.lpSum([s_work[j][t][role] for j in days for t in times for role in roles])  + pulp.lpSum([s_till[j] for j in days]) + pulp.lpSum([s_mana[j][t] for j in days for t in times])

        prob += shortage_penality 

        ### Constraints 

        ## 1. Availability constraints 
        for i in workers : 
            for j in days : 
                for t in times : 
                    for role in roles :
                        prob += x[i][j][t][role] <= self.availability[i][j][t] 

        ## 2. Demand Satisfcation 
        for j in days:
            for t in times:
                for role in roles:
                    prob += (
                        pulp.lpSum(
                            x[i][j][t][role]
                            for i in workers
                            if self.possible_role[i] == role or self.possible_role[i] == 'Both'
                        )
                        + s_work[j][t][role]
                        == self.need[j][t][role]
                    )


        ## 3. Only one possible starting time for each worker for each day 
        for i in workers : 
            for j in days :
                prob += pulp.lpSum([x[i][j][t][role] for t in times for role in roles]) <= 1

        ## 4. One night worker needs to do the till 
        for j in days:
            ### ONLY require a till worker if we actually need staff in this specific slot (Can be modified by detecting the closed days)
            if sum(self.need[j][t][role] for role in roles) > 0:
                prob += pulp.lpSum([x[i][j][t][role] * self.counting[i] for i in workers for role in roles for t in night]) + s_till[j] >= 1 

        ## 5. At least one manager is present 
        for j in days:
            for t in night:
            ### ONLY require a manager if the bar is actually open  (Can be modified by detecting the closed days)
                if sum(self.need[j][t][role] for role in roles) > 0: # Night
                    prob += pulp.lpSum([x[i][j][t][role] * self.manager[i] for i in workers for role in roles]) + s_mana[j][t] >= 1

                    
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        return x, s_work, s_till, s_mana
    
    
    def transform_df(self) -> pd.DataFrame: 
        """ Transform the staff availability relative to days into a binary datgaframe relative to each possible shifts"""
        ### Based only on google form csv output format 

        ### Last Entry filtering
        availability = self.staff_manager.staff_availability.copy()
        availability['Horodateur'] = pd.to_datetime(availability['Horodateur'])
        availability = availability.sort_values('Horodateur').drop_duplicates('Adresse e-mail', keep='last')

        ### Define the target structure
        days = self.staff_manager.config['structure']['days']
        hours = self.staff_manager.config['structure']['time_labels'].values()
        
        ### Initialize result with Names
        result_data = {"Name": availability['Name']}
        
        ### Transform csv format into a binary indicator of availability for each time slot
        for day in days:
            for hour in hours:
                ### Create the header name like "Mon 14h" Matching the need_for_staff format
                col_name = f"{day[:3]} {hour}"
                
                # Search for the hour in the day string (ignoring spaces)
                result_data[col_name] = availability[day].fillna("").apply(
                    lambda x: 1 if hour in str(x).replace(" ", "") else 0
                )
                
        df = pd.DataFrame(result_data)
        return df

    def apply_mapping(self) -> pd.DataFrame: 
        """ Apply mapping to the staff register to have a binary format for optimization parameters (till authorization and manager role)"""
        map_yes_no = self.staff_manager.config["mapping"]["registry"]["till"]
        regitser = self.staff_manager.staff_register.copy()
        return regitser.replace(map_yes_no)  

    def create_parameters(self) -> tuple: 
        """ Create the parameters for the optimization problem based on the staff register, availability and need for staff after applying the necessary transformations and mapping"""
        availability = self.transform_df().set_index("Name")
        register = self.apply_mapping().set_index("Name")
        demand = self.staff_manager.need_for_staff.set_index("Role")

        day_names = self.staff_manager.config['structure']['days'] # Number of working day in a week 
        days = list(range(len(day_names)))
        times = range(self.staff_manager.config['structure']['shifts']) # Number of starting time in a day

        ### Create parameter d[i][j][t]
        d = {}
        workers = availability.index.tolist()
        cols = availability.columns
        
        for worker in workers:
            d[worker] = {}
            for j in range(len(days)): 
                d[worker][j] = {}
                for t in times: 
                    col_idx = j * 3 + t
                    if col_idx < len(cols):
                        val = availability.loc[worker, cols[col_idx]]
                        d[worker][j][t] = 1.0 if val > 0.0 else 0.0
                    else:
                        d[worker][j][t] = 0.0 ### safety

        ### Create parameter n[j][t][r]
        role = demand.index.tolist()
        n = {}
        for j in range(len(days)):
            n[j] = {}
            for t in times: 
                n[j][t] = {}
                col_idx = j * 3 + t
                for position in role : 
                    if col_idx < len(cols):
                        n[j][t][position] = int(demand.loc[position, demand.columns[col_idx]])
                    else : 
                        n[j][t][position] = 0.0
        
        ### Create parameter c[i]
        if 'Name' in register.columns:
            register = register.set_index('Name')
        c = {}
        for worker in workers : 
            c[worker] = register.loc[worker,'Till_Authorized']
        
        ### Create parameter m[i]
        m = {}
        for worker in workers : 
            m[worker] = register.loc[worker, 'Is_Manager']
        
        ### Create parameter r[i]
        r = {}
        for worker in workers : 
            r[worker] = register.loc[worker, 'Role']

        return d, n, c, m, r
