# Optimization-Based Workforce Scheduling System  
## Summary  : 

This project implements a workforce scheduling system formulated as a Binary Integer Programming (BIP) problem. 

The system models staff availability, role requirements, operational constraints and soft penalties to generate an optimal weekly schedule under business (various) constraints needs.

## Mathematical Formulation
<img width="909" height="1222" alt="image" src="https://github.com/user-attachments/assets/043b5794-c0c3-461a-aaf0-361940211272" />

## Project Structure 
```
├── config.yaml                # Central configuration file
├── requirements.txt           # Python dependencies
│
├── data/                      # Input CSV files
│   ├── staff_availability.csv # Employee availability data
│   ├── need_for_staff.csv     # Staffing requirements per shift
│   └── staff_register.csv     # Employee master data
│
├── outputs/                   # Generated outputs
│   ├── Weekly_Staff_Schedule.xlsx
│   ├── Weekly_Staff_Schedule.pdf
│   ├── Proposed_Staff_Schedule.xlsx
│   └── Shortage_Report.txt
│
├── logs/
│   └── staff_scheduler.log    # Application logs
│
└── src/
    ├── main.py                # Application entry point
    ├── optimizer_manager.py   # Scheduling optimization logic (BIP/MIP)
    ├── db_manager.py          # Data loading and management
    ├── reporting_manager.py   # Excel/PDF report generation
    ├── ui_manager.py          # User interface logic
    └── utility.py             # Helper functions
```

### data : 

Code is based on 3 data source : 
- staff_availability.csv (change weekly based on new availability based on Google form csv format)
- need_for_staff.csv (template of demand for each shift and each role that can be adapt weekly inside the UI)
- staff_register.csv (information about each worker that can be adapt weekly inside the UI).  

The expected data format is checked using the config file that contains the headers of the csv 

### logs : 

A report of eventual errors, modification of db and various information about the eventual bugs. 

### outputs : 
- Shortage_Report.txt : a simple report with the missing role for each shift.  
- Weekly_Staff_Schedule.xlsx : final excel schedule.
- Weekly_Staff_Schedule.pdf : the schedule format to pdf.

### src : 
General Idea : the choice of the stack can be changed as long as each class implement the same API (function and report type)
- StaffManager : use pandas and apply permanent modification of dfs, reconciliation (change of name, ghost worker, new worker)
- Optimizer : use Pulp and return the optimal assignement
- ReportingManager : collect all the results
- UiManager : use FreeSimpleUI and handle collection of new datas


```mermaid
flowchart TD


Upload((fa:fa-file-csv User updates<br/>availability.csv)) -.-> Start([Start Program])


Start --> DB_Init[Initialize DBManager]
Start --> UI_Init[Initialize UIManager]

subgraph DBLayer ["DBManager Operations Pipeline"]
    DB_Init --> Load[Load CSV Files]
    Load --> NewCheck{New Workers?}
    
    %% Path 1: Worker Sync
    NewCheck -- Yes --> AskNew[[UI: Request Attributes]]
    AskNew --> SyncDB[(Update staff_register.csv)]
    SyncDB --> GhostCheck
    NewCheck -- No --> GhostCheck{Ghost Workers?}

    %% Path 2: Ghost Cleanup
    GhostCheck -- Yes --> AskGhost[[UI: Confirm Deletion]]
    AskGhost -- Yes --> SyncDB2[(Update staff_register.csv)]
    AskGhost -- No --> NameCheck
    SyncDB2 --> NameCheck{Name Changes?}
    GhostCheck -- No --> NameCheck
    
    %% Path 3: Name Sync
    NameCheck -- Yes --> SyncDB3[(Update staff_register.csv)]
    NameCheck -- No --> DemandCheck
    SyncDB3 --> DemandCheck{UI: Edit Demand?}

    %% Path 4: Demand Edit (Now inside DB Manager)
    DemandCheck -- Yes --> EditDemand[(Modify need_for_staff.csv)]
    EditDemand --> ReadyToSolve
    DemandCheck -- No --> ReadyToSolve
end

subgraph UILayer ["UIManager"]
    UI_Init -.-> NewCheck
    
    %% UI components called by the DB Pipeline
    AskNew -.-> GUI_Form[GUI: Entry Form]
    AskGhost -.-> GUI_Dialog[GUI: Yes/No Dialog]
    DemandCheck -.-> GUI_Edit[GUI: Demand Editor]
end

subgraph OptimizerLayer ["OptimizerManager"]
    ReadyToSolve --> Opti_Init[Initialize OptimizerManager] 
    Opti_Init[Initialize OptimizerManager] --> Setup[Build Math Model]
    Setup --> Solve[Pulp / Gurobi Solve]
end

subgraph ReportingLayer ["ReportingManager"]
    Solve --> Reportinit[Initialize ReportingManager] 
    Reportinit --> Generate[Export Results]
    Generate --> Save[Save to /outputs]
end

Save --> End([End Program])

style DBLayer fill:#fafafa,stroke:#333,stroke-width:2px
style UILayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
style OptimizerLayer fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
style ReportingLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px

style SyncDB fill:#fff9c4,stroke:#fbc02d,stroke-width:1px
style SyncDB2 fill:#fff9c4,stroke:#fbc02d,stroke-width:1px
style SyncDB3 fill:#fff9c4,stroke:#fbc02d,stroke-width:1px
style EditDemand fill:#fff9c4,stroke:#fbc02d,stroke-width:1px

style NewCheck fill:#ffebee,stroke:#c62828
style GhostCheck fill:#ffebee,stroke:#c62828
style NameCheck fill:#ffebee,stroke:#c62828
style DemandCheck fill:#ffebee,stroke:#c62828
```
Few Comments about the current pipeline : 

- **Automation** : As "staff_availibility.csv" is based on template from google forms export csv the whole pipeline can be automate using google api for upload result from the form and launch a new form.
- **GUI** : While operationnal using FreeSimpleGui is not the more convenient for user interface and visualization fo dataframe like staff_register or demand. Typically, an interface based on Html and CSS will be more handy.
- **Feedback loop from user** : What is currently missing is a feedback loops with the user about the proposed solutions handle by the **ReportingManager** class. 

## Running the Project 
```
 1- Create venv with requirements.txt : python -m venv .venv 
 2- Activate : .venv\Scripts\activate 
 3- Populate venv : pip install -r requirements.txt
 4- Running the code : python src/main.py
```

## Making a standalone application 
In order to be used by all type of people, the repo can be make as a standalone application using the following command with pyInstaller : 
```
python -m PyInstaller --noconfirm --onedir --windowed --name "Staff_Scheduler" --collect-all pulp --add-data "config.yaml;." --add-data "data;data" --add-data "outputs;outputs" --add-data "logs;logs" main.py

```

## Future Improvements 
 1 - Other constraints are possibles : incompatibility between two woerkers that cannot be scheduled to the same shift
 
 2 - New type of Optimizer : BIP is not the only possible way to solve the problem in an exact manner (ex: CP). Also, for larger problem with more constraints and/or more ppl excat approach will become untractable thus the implementation of approximate algorithm such as Grasp algorithm will be nice. 
 
 3 - Other objectives are possibles : we can add fairness constraint between the different workers based on various criteria (the worker the more available have priority, the assignement need to minimize the STD between workers etc... )
 
 4 - Testing : while we catch the errors in the logger, the most clean way to do will be to add Unit test
 
 5 - UI : Switch this simple pratical UI to something nicer and more user friendly.
