import sys
import logging
import yaml 
import os

def load_config(path="config.yaml"):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

### Orchestrator logic ####

def setup_env() -> tuple:
    base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False) 
            else os.path.dirname(os.path.dirname(__file__)))
    config = load_config(os.path.join(base, "config.yaml"))

    paths = {
        'base': base,
        'data': os.path.join(base, config["path"]["data"]),
        'log': os.path.join(base, config["path"]["log"])
    }
    return config, paths

def setup_logging(base_path, config) -> logging.Logger:
    """Initializes the logging system based on config paths."""
    log_dir = os.path.join(base_path, config["path"]["log"])
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "staff_scheduler.log")
    
    logging.basicConfig(
        filename=log_file,
        filemode='a',
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Optional: Add a console handler to see logs in the terminal while debugging
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)
    
    return logging.getLogger(__name__)

def run_reconciliation_update(staff_manager, staff_ui, logging, data_path, config) -> None:
    ## Automatically remplace the new name corresponding to the email in the staff register, to avoid duplicates and errors in the reconciliation process
    staff_manager.change_name_in_staff_register()

    ## Flag and modfify new workers in staff register
    new_workers = staff_manager.get_new_workers()
    for name in new_workers: 
        result = staff_ui.popup_new_staff(name)
        if result is not None:
            staff_manager.add_staff(name, result)

    if (new_workers):
        logging.info("Add new workers to the staff register: " + ", ".join(new_workers))

    ## Flag ghost workers and ask for confirmation to delete them from staff register
    ghost_workers = staff_manager.get_ghost_workers()
    for name in ghost_workers:
        if staff_ui.confirm_ghost_worker(name):
            staff_manager.remove_staff(name)
            
    if (ghost_workers):
        logging.info("Remove ghost workers from the staff register: " + ", ".join(ghost_workers))

    ## Ask if we need to modify the attributes of a worker
    updates = staff_ui.modify_staff_register(sorted(staff_manager.staff_register['Name'].unique()))

    if updates is not None:
        for update in updates:
            staff_manager.update_staff(update["Name"], update["data"])
            logging.info("Updated staff member: " + update["Name"] + " with the following changes: " + str(update["data"]))

    ## Update staff Register with new infos from reconciliation dataManagement (permanent change)
    staff_manager.staff_register.to_csv(os.path.join(data_path, config["names_df"]["staff_register"]), index=False)
    
    ## Ask if we need to modify the demand for this week 
    new_demand = staff_ui.modify_demand()
    if new_demand is not None:
        logging.info("Demand manually modified by user.")
        staff_manager.demand = new_demand
