### import of function 
from utility import setup_env, setup_logging, run_reconciliation_update
### import of classes
from optimizer_manager import OptimizerManager
from db_manager import StaffManager
from ui_manager import StaffUI
from reporting_manager import ReportingManager

def main(): 
    try:
        ### 1- LOADING DATA ###
        config, paths = setup_env()
        base_path = paths['base']
        data_path = paths['data']
        
        logger = setup_logging(base_path, config)
        logger.info("=== Application started ===")

        ### 2- DB MANAGEMENT ###

        staff_manager = StaffManager( paths, config) ### Check input headers and initialize staff manager
        staff_ui = StaffUI(staff_manager)

        staff_ui.show_info_message("Data loaded successfully! Starting reconciliation process...")

        run_reconciliation_update(staff_manager, staff_ui, logger, data_path, config) ### Run reconciliation process with the UI and update staff register accordingly

        ### 3- SCHEDULING : Transform database into BIP mapping and solve scheduling problem ###

        staff_ui.show_info_message("Starting scheduling optimization...")
        optimizer_manager = OptimizerManager(staff_manager)
        x, s_work, s_till, s_mana, availability_dict = optimizer_manager.sol, optimizer_manager.s_work, optimizer_manager.s_till, optimizer_manager.s_mana, optimizer_manager.availability

        ### 4- REPORTING : Generate and save schedule and reporting on shortages ###
        staff_ui.show_info_message("Starting Reporting...") 

        shortage = {
            'worker': s_work,
            'till': s_till,
            'manager': s_mana
        }
        
        reporting_manager = ReportingManager(x, config, base_path, shortage, availability_dict)
        reporting_manager.save_schedule_toxl()
        reporting_manager.save_schedule_pdf()
        reporting_manager.save_reporting()

        staff_ui.show_info_message(f"Application finished! Schedule and reporting saved in the outputs folder")

        logger.info("=== Application finished ===")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}", exc_info=True)
        staff_ui.show_error_message()
    except ValueError as e:
        logger.error(f"Data validation error: {e}", exc_info=True)
        staff_ui.show_error_message()
    except Exception as e:
        logger.error(f"Unexpected error: {e}",  exc_info=True)
        staff_ui.show_error_message()


if __name__ == "__main__":
    main()
