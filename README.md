# CB_TaskManager

CarbonBlack Task Manager tool to run and manage tasks on the sensors (endpoints) and collect output results, for example you could run Loki scanner on all sendors and get the results simply by using the tool

# Componenets

This package contains the following files/folder:
- **plugins**:  contain multiple .zip files each considered as a task (hoarder,loki,etc.), and you could add more custom plugins to be used in your environment.
- **7za.exe**: will uploaded to the client machine to be used to decompress the task .zip file, also compress the task folder to be downloaded
- **RUN_manager.bat**: check and control the task process status (running, timeout, fininshed)
- **Tasks_Manager.py**: python script to utilize the CarbonBlack API to manage the tasks and the client machines (upload plugin, run the process on client, download results, etc.)


# Usage

you can use the following command to run the tasks manage:
```
python3 Tasks_Manager.py -m targeted_machines.txt -a run_command -c "/c .\RUN.bat" -sf ./plugins/Hoarder.zip -o output_folder -t 'Task_Collect_Hoarder' -n 7 -l Task_Collect_Hoarder.log -v -to 3600
```


## Parameters

```
-m : the file contain the targeted machines to run the task on
-a : action to perform (run_command/clean_machine), clean_machine will delete the folder of all tasks on the client machine
-c : command to run (RUN.bat located inside the plugin zip file), preferable to put all command on the RUN.bat and don’t change the argument (-c "/c .\RUN.bat")
-sf: source file of the zip file plugin
-o: output folder on the server to place all results on this folder
-t : task name, by default (Tasks_<datetime>)
-n : maximum number of concurrent sessions (SOC only enabled 10, preferable to use only 7)
-l : log file of tasks_manager (by default not enabled and logs not stored)
-v : enable verborse mode
-to : timeout for the task, by default 1800 sec (30 min)
```
