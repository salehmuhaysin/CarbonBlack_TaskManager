#!/usr/bin/python3

from cbapi.response  import *
import pprint
from os import walk
import time
import os
from os import system, name
import argparse
import _thread
import sys
from datetime import datetime

"""
Examples:
To run on background:
 nohup python3 Tasks_Manager.py -m targeted_machines.txt -a run_command -c "/c .\RUN.bat" -sf ./plugins/Hoarder.zip -o output_folder -t 'Task_Collect_Hoarder' -n 7 -l Task_Collect_Hoarder.log -v -to 3600 &


"""


print("======================== CarbonBlack Run Script ========================")


# ================== Arguments
parser = argparse.ArgumentParser(description="Run CarbonBlack task manager.\n\n")
parser.add_argument('-a' , dest='action' ,              help='Action on the sensor machine [run_command,clean_machine]' , required=True)
parser.add_argument('-m' , dest='machines' ,            help='File path contain list of machines to run the process on' , required=True)
parser.add_argument('-o' , dest='output' ,              help='Output folder (default "result"), result stored on zip file of the targeted machine name')
parser.add_argument('-df' , dest='destfol' ,            help='Destination folder (default: C:\Windows\CarbonBlack\tasks\)')
parser.add_argument('-sf' , dest='srcfile' ,            help='Source file, if provided it will upload the file to (destfol) folder')
parser.add_argument('-c' , dest='command' ,             help='Run command on the targeted machine')
parser.add_argument('-t' , dest='task_name' ,           help='Task name, (by default: task_<date_time>)')
parser.add_argument('-w' , dest='wait_all' ,            action='store_true' ,  help='Wait for other machines not added to the queue')
parser.add_argument('-v' , dest='verbose' ,             action='store_true' ,  help='Verbose to print detailed information')
parser.add_argument('-n' , dest='max_running_tasks' ,   help='Maximum number of sensors running on the same time, default 10')
parser.add_argument('-l' , dest='logs' ,  help='path of file logs, if not provided the logs will not be stored')
parser.add_argument('-to' , dest='timeout' ,  help='task timeout in seconds (default 1800 -> 30 mins)')


args = parser.parse_args()


# ================================ Machines Handling Object =================================== #
class machines:
    
    
    output_folder       = "result" # output folder to store the results on current machine
    zip_path            = '7za.exe' # path of the 7za executable
    RUN_manager         = 'RUN_manager.bat' # this file will execute the bat in task, control task timeout
    CB_dest_folder      = "C:\\Windows\\CarbonBlack\\tasks\\" # target path on the client machine
    CB_src_file         = None  # path of file to be uploaded to client machines
    cb                  = CbEnterpriseResponseAPI() # CB API
    targeted_sensors    = []    # list of machines will run the task on
    sensors_queue       = []    # list of machines applicable to run the task on
    input_run_command   = None  # command to be run on client machine
    possible_actions    = ['run_command' , 'clean_machine'] # possible actions 
    task_options        = None # store the options passed to the task
    wait_all            = False # if False then will not check the machine again if applicable or not
    verbose             = False # if True then will print more details of tasks
    max_running_tasks   = 10    # number of machines to run the task on concurrently 
    log_path            = None  
    task_timeout        = 1800  # task timeout (30 mins)
    
    
    def save_record(self, record):
        if self.log_path is not None:
            f = open(self.log_path , 'a')
            f.write(record + "\n" )
            f.close()
    
    def print_error(self, msg):
        msg =  str(datetime.now()) + "[Error]: " + msg
        self.save_record(msg)
        print("\033[91m {}\033[00m" .format(msg))
    
    def print_info(self, msg):
        msg =  str(datetime.now()) + "[Info]: " + msg
        self.save_record(msg)
        if self.verbose:
            print("{}" .format(msg))
        
    def print_success(self, msg):
        msg =  str(datetime.now()) + "[Success]: " + msg
        self.save_record(msg)
        print("\033[92m {}\033[00m" .format(msg))

    def print_warning(self, msg):
        msg =  str(datetime.now()) + "[Warning]: " + msg
        self.save_record(msg)
        print("\033[93m {}\033[00m" .format(msg))

    def __init__(self, args):
        
        # check action
        self.action = args.action
        if self.action not in self.possible_actions:
            self.print_error('[-] Error: possible actions ' + str(possible_actions) )
            sys.exit()


        if(self.action == "run_command" and args.command is None):
            self.print_error('[-] Error: if action argument (-a) selected as run_command, you need to enter the command name argument (-c)')
            sys.exit()

        
        # output folder
        if args.output is not None:
            self.output_folder = args.output
        # create output folder if not exists
        if not os.path.isdir(self.output_folder):
            os.mkdir(self.output_folder)
        
        
        
        # destnation folder on the sensor machine
        if args.destfol is not None:
            self.CB_dest_folder = args.destfol
        
        
        self.task_name = args.task_name if args.task_name is not None else 'task_' + str(datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
        self.task_path = self.CB_dest_folder + self.task_name
        
        
        # source file, it will upload the file and unzip from the current machine
        self.CB_src_file = args.srcfile

        # wait all, if True will wait all machines even the machines not added to the queue
        self.wait_all = True if args.wait_all == True else False 
        
        # if True print detailed information 
        self.verbose = True if args.verbose == True else False
        
        # if not provided dont store the logs
        self.log_path = args.logs if args.logs is not None else None
        
        # Maximum number of running tasks on the same time
        self.max_running_tasks = int(args.max_running_tasks) if args.max_running_tasks is not None else 10
        
        # if not provided dont store the timeout
        self.task_timeout = int(args.timeout) if args.timeout is not None else self.task_timeout
        
        
        # task run command
        self.input_run_command = args.command
    
        self.task_options = {
            'output_folder'     : self.output_folder,
            'zip_path'          : self.zip_path,
            'RUN_manager'       : self.RUN_manager,
            'CB_dest_folder'    : self.CB_dest_folder,
            'CB_src_file'       : self.CB_src_file,
            'input_run_command' : self.input_run_command,
            'task_path'         : self.task_path,
            'task_name'         : self.task_name,
            'verbose'           : self.verbose,
            'log_path'          : self.log_path,
            'CB_folder'         : self.CB_dest_folder,
            'task_timeout'      : self.task_timeout
        }

        # get the list of machines to run the process on
        f = open(args.machines , 'r')
        
        self.print_warning('[+] Targeted Machines')
        for s in f.readlines():
            s = s.strip()
            
            # skip empty lines 
            if s == "":
                continue
                
            is_disabled = s.startswith('#')
            machine_name = s.lstrip('#')
            
            # if machine in targeted_sensors skip it
            if self.is_machine_in_target_sensors(machine_name):
                continue
            
            try:
                sensor = self.cb.select(Sensor).where("hostname:"+machine_name)[0]
            except:
                sensor = None
            
            if sensor is None:
                machine = {
                    'name' : machine_name,
                    'disabled' : None,
                    'online' : None,
                    'sensor' : None,
                    'queued' : False,
                    'machine': None
                }
            else:
                machine = {
                    'name' : machine_name,
                    'disabled' :  True if is_disabled else False,
                    'online' : True if sensor.status == "Online" else False,
                    'sensor' : sensor,
                    'queued' : False,
                    'machine': None
                }
            
            self.targeted_sensors.append( machine )
            #print("[+] " + machine['name'] + "\t,Disabled: " + str(machine['disabled']) + "\t,Online: " + str(machine['online'])  )

        f.close()
        
        
        # update the sensors queue
        self.update_sensors_queue()
        
        
        # run the tasks managements
        self.manage_task_progress()
        
    
    # check if machine already in targeted_sensors
    def is_machine_in_target_sensors(self , machine_name):
        for m in self.targeted_sensors:
            if m['name'] == machine_name and m['disabled'] == False:
                return True
        return False
        
    # this will manage the tasks and machines
    def manage_task_progress(self):
    
        self.print_info('max_running_tasks ' + str(self.max_running_tasks))
        # if there is task running or there is machines not added to queue wait
        running_tasks = None
        while( running_tasks is None or running_tasks or self.get_queued_sensors() < len(self.targeted_sensors)):
            time.sleep(2)
            running_tasks = self.get_running_tasks()
            
            # run new task 
            m = self.get_machine_from_queue()
            if m is not None and running_tasks < self.max_running_tasks:
                
                try:
                    self.print_info('[+] Create thread for machine: ' + m['name'])
                    _thread.start_new_thread( self.start_new_machine, (m, ) )
                    time.sleep(2)
                    running_tasks = self.get_running_tasks()
                except Exception as e:
                    self.print_error("Error: Failed to create thread: " + m['name'] + " \t " + str(e))
                
                continue
            
            
            
            # check when to stop the waiting
            if running_tasks == 0 and not self.wait_all:
                
                # if wait_all == False, dont wait other machines to be added to the 
                self.print_warning('All machines in queue processed')
                for mach in self.sensors_queue:
                    if mach['machine'].status == 'Done':
                        self.print_success('[+] ' + mach['name'] + ' -> Done')
                    elif mach['machine'].status == 'Failed':
                        self.print_error('[+] ' + mach['name'] + ' -> Failed')
                    else:
                        self.print_warning('[+] ' + mach['name'] + ' -> ' + mach['machine'].status)
                break
                
            
            
                
         
    # this will create tasks from new machine in the queue
    def start_new_machine(self, machine):
        
        if self.action == 'run_command': 
            try:
                machine['machine'].run_command(machine['sensor'])
            except KeyboardInterrupt:
                self.print_error('[-] ' + machine['name'] + ' - Ctrl+C Entered: task ['+machine['machine'].options['task_name']+'] stopped' )
                machine['machine'].session.close()
                machine['machine'].status = 'Failed'
                return False
            except Exception as e:
                print(str(e))
            return True
        
        elif self.action == "clean_machine":
            try:
                machine['machine'].clean_machine(machine['sensor'])
            except KeyboardInterrupt:
                self.print_error('[-] ' + machine['name'] + ' - Ctrl+C Entered: Clean machine stopped' )
                machine['machine'].session.close()
                machine['machine'].status = 'Failed'
                return False
            except Exception as e:
                print(str(e))
            return True
        
    # get number of running machines tasks
    def get_running_tasks(self):
        count = 0
        for s in self.sensors_queue:
            if s['machine'].status not in [ 'NotRunning' , 'Failed' , 'Done' , 'Timeout-Done']:
                count += 1
        return count
    
    # get machine from queue to start process it
    def get_machine_from_queue(self):
        for s in self.sensors_queue:
            if s['machine'].status  == 'NotRunning':
                return s
        return None
    
    # get the number of machines in the queue 
    def get_queued_sensors(self):
        count = 0
        for t in self.targeted_sensors:
            if t['queued']:
                count +=1 
        return count
        
        
    # update the tasks sensors queue
    def update_sensors_queue(self):
        for t in range( len( self.targeted_sensors) ):
            if self.targeted_sensors[t]['disabled'] == False and self.targeted_sensors[t]['online'] == True and self.targeted_sensors[t]['queued'] == False:
                self.print_success( "[+] " + self.targeted_sensors[t]['name'] + "\t,Disabled: " + str(self.targeted_sensors[t]['disabled']) + "\t,Online: " + str(self.targeted_sensors[t]['online'])  )
                self.targeted_sensors[t]['queued'] = True
                
                # create machine object
                self.targeted_sensors[t]['machine'] = run_script( self.targeted_sensors[t] , self.task_options , self.action )
                
                self.sensors_queue.append( self.targeted_sensors[t] )
            else:
                self.print_error( "[+] " + self.targeted_sensors[t]['name'] + "\t,Disabled: " + str(self.targeted_sensors[t]['disabled']) + "\t,Online: " + str(self.targeted_sensors[t]['online']) )
        
        self.print_warning("\n\n[+] Targeted Machines ["+str(len(self.targeted_sensors))+"] and [" + str(len(self.sensors_queue) ) + "] applicable \t Max Concurrent running machines: " + str(self.max_running_tasks) )
    




# ================================ Machines Handling Object =================================== #
class run_script:
    
    options = {}
    status = 'NotRunning'
    '''
    NotRunning:     still script not running
    Running:        the script is running
    Finished:       script finished but result not downloaded
    Done:           script finished and result downloaded
    Failed:         script failed running
    Timeout:        script timeout
    Timeout-Done    script timeout and done task
    '''
    status_lock = 'status.lck'
    machine = None
    
    def save_record(self, record):
        if self.options['log_path'] is not None:
            f = open(self.options['log_path'] , 'a' , encoding="utf-8")
            f.write(record + "\n" )
            f.close()
    
    
    
    def print_error(self, msg):
        msg =  str(datetime.now()) + "[Error]: " + msg
        self.save_record(msg)
        print("\033[91m {}\033[00m" .format(msg))
    
    def print_info(self, msg):
        msg =  str(datetime.now()) + "[Info]: " + msg
        self.save_record(msg)
        if self.options['verbose']:
            print("{}" .format(msg))
        
    def print_success(self, msg):
        msg =  str(datetime.now()) + "[Success]: " + msg
        self.save_record(msg)
        print("\033[92m {}\033[00m" .format(msg))
        
    def print_warning(self, msg):
        msg =  str(datetime.now()) + "[Warning]: " + msg
        self.save_record(msg)
        if self.options['verbose']:
            print("\033[93m {}\033[00m" .format(msg))
        
        
    def __init__(self , machine , options , action):
        self.machine = machine
        self.options = options
        self.session = None
        
            
        
    
    # ============ commands ======================
    # ========== clean_machine
    def clean_machine(self, sensor):
        machine_name = self.machine['name']
        
        self.status = 'Running'
        self.print_success('[+] '+machine_name+' - Clean machine : ' + self.status)
        
        try:
            with sensor.lr_session() as self.session:
                self.print_info('[+] '+machine_name+' - Clean machine: Session Created ['+str(self.session.session_id)+'] on sensor ['+str(self.session.sensor_id)+']')
                
                if not self.delete_folder( self.options['CB_folder']):
                    raise Exception( '[-] '+machine_name+ ' - Failed to delete the output result : ' + self.options['CB_folder'] )
                    
                # if done the task
                self.status = 'Finished'
                self.print_success('[+] '+machine_name+' - Clean machine: ' + self.status)
        
        # ===== if failed to run the task
        except Exception as e:
            self.print_error(str(e))
            self.session.close()
            self.status = 'Failed'
            return False
        
        
       
        # if done the task
        self.status = 'Done'
        self.print_success('[+] '+machine_name+' - Clean machine: ' + self.status)
        return True
        
    # ========== run_command
    def run_command(self , sensor):
        machine_name = self.machine['name']
        
        self.status = 'Running'
        self.print_success('[+] '+machine_name+' task ' + self.options['task_name'] + ': ' + self.status)
        
        is_timeout = False # True if the task is timeout
        
        try:
            with sensor.lr_session() as self.session:
                self.print_info('[+] '+machine_name+' task ' + self.options['task_name'] + ': Session Created ['+str(self.session.session_id)+'] on sensor ['+str(self.session.sensor_id)+']')
                
                # ===== create tasks folder in sensor
                self.mkdir(self.options['CB_dest_folder'])
                self.mkdir(self.options['task_path'])
                
                # ===== upload the RUN_manager.bat file
                if not self.upload_file( self.options['RUN_manager'] , self.options['task_path'] + "\\"):
                    raise Exception('[-] '+machine_name+' - Error uploading the file : ' + self.options['RUN_manager'])
                
                
                
                # ===== set task status
                set_lock = 'cmd.exe /c echo '+self.options['task_name']+':Running > ' + self.options['task_path']+ '\\' +self.status_lock
                self.print_info('[+] '+machine_name+' - Set Task Status Running: '+ set_lock)
                try:
                    self.session.create_process( set_lock , wait_for_output=True,wait_for_completion=True)
                except Exception as e:
                    raise Exception('[-] '+machine_name+' - Failed to set the task status [Running] : ' + str(e))
                
                # ===== Starting the task
                self.print_info("[+] "+machine_name+" - Task Started: " + self.options['task_name'] )
                
                
        
                # ===== upload source file package
                if self.options['CB_src_file'] is not None:
                    if not os.path.exists(self.options['CB_src_file']):
                        raise Exception('[-] '+machine_name+' - Provided file not exists: ' + self.options['CB_src_file'])
                    else:
                        if not self.upload_file( self.options['CB_src_file'] , self.options['task_path'] + "\\"):
                            raise Exception('[-] '+machine_name+' - Error uploading the file : ' + self.options['CB_src_file'])
                 
                
                
                # ===== run the command
                change_dir_cmd = 'cmd.exe /c cd ' + self.options['task_path']
                free_lock = 'cmd.exe /c echo '+self.options['task_name']+':Timeout > .\\' +self.status_lock + " || " + 'cmd.exe /c echo '+self.options['task_name']+':Finished > .\\' +self.status_lock
                input_cmd = self.options['RUN_manager'] + " \"" + self.options['input_run_command'] + "\" " + str(self.options['task_timeout'])
                
                cmd_run = change_dir_cmd + " && " + input_cmd 
                self.print_info("[+] "+machine_name+" - Start Command: " + cmd_run )
                
                
                try:
                    self.session.create_process( cmd_run , wait_for_output=False,wait_for_completion=False , working_directory=self.options['task_path'], remote_output_file_name=self.options['task_path'] + "\\CB_output.txt")
                except Exception as e:
                    raise Exception('[-] '+machine_name+' - Failed execute task: ' + str(e))
                    
                
                # ==== wait for status task to be finished
                wait = True
                while(wait):
                    #time.sleep(2) # wait 10 seconds before checking the result again
                    s = self.get_status() 
                    if s == False:
                        self.print_error('[-] ' + machine_name + ' - Failed getting the status')
                    else:
                        if s == "Finished":
                            self.status = "Finished"
                            self.print_success('[+] '+machine_name+' task ' + self.options['task_name'] + ': ' + s)
                            break
                        elif s == "Timeout":
                            is_timeout = True
                            self.status = "Timeout"
                            self.print_error('[-] '+machine_name+' task ' + self.options['task_name'] + ': ' + s)
                            break
                
                # ===== compress the result
                if not self.compress_folder( self.options['task_path'] , self.options['task_path'] + '\\' + machine_name +'.zip'):
                    self.print_error('[-] '+machine_name+ ' - Failed compressing the results ')
                else:
                # ===== download output to current machine
                    self.print_info('[+] '+machine_name+ ' - Download output file: ' + self.options['task_path'] + '\\' + machine_name +'.zip -> ' + self.options['output_folder'] + "/" + machine_name +'.zip')
                    if not self.download_file(self.options['task_path'] + "\\" + machine_name +'.zip' , self.options['output_folder'] + "/" + machine_name +'.zip' ):
                        self.print_error('[-] '+machine_name+ ' - Download output file failed: ' + self.options['task_path'] + '\\' + machine_name +'.zip -> ' + self.options['output_folder'] + "/" + machine_name +'.zip')
                
                
                # ===== delete the output result
                #self.print_info('[+] '+machine_name+ ' - Delete task folder: ' + self.options['task_path'])
                #if not self.delete_folder( self.options['task_path']):
                #    self.print_error('[-] '+machine_name+ ' - Failed to delete the output result')
                
                
                # delete the output result .zip file
                #self.print_info('[+] '+machine_name+ ' - Delete output file: ' +self.options['CB_dest_folder'] + machine_name +'.zip')
                #self.delete_file(session , self.options['CB_dest_folder'] + machine_name +'.zip' )
                
        
        
        # ===== if failed to run the task
        except Exception as e:
            self.print_error('[-] '+machine_name+' - Failed to establish session: ' + str(e))
            if self.session is not None:
                self.session.close()
            self.status = 'Failed'
            return False
        
        
       
        # if done the task
        if is_timeout:
            self.status = 'Timeout-Done'
            self.print_success('[+] '+machine_name+' task ' + self.options['task_name'] + ': ' + self.status)
        else:
            self.status = 'Done'
            self.print_success('[+] '+machine_name+' task ' + self.options['task_name'] + ': ' + self.status)
        return True
        
        
                    

    
    # ============ helper functions ==============
    # create file in sensor to set the task status
    def set_status(self, status):
        change_dir_cmd = 'cmd.exe /c cd ' + self.options['task_path']
        input_cmd = 'cmd.exe /c echo '+self.options['task_name']+':' + status + ' > ' + self.status_lock
        try:
            self.session.create_process(change_dir_cmd + " && " + input_cmd , wait_for_output=True,wait_for_completion=True , working_directory=self.options['task_path'])
            return True
        except:
            return False
    
    # delete the status lock file 
    def delete_status(self):
        self.status_lock
        return self.delete_file(self.options['task_path'] + '\\' + self.status_lock)
    
    # get the task status from status lock file
    def get_status(self):
        input_cmd = "cmd.exe /c type " + self.options['task_path']+ '\\' +self.status_lock
        try:
            status = self.session.create_process( input_cmd , wait_for_output=True,wait_for_completion=True).decode('ascii').strip().split(":")
        except Exception as e:
            print(str(e))
            return False
        
        if len(status) == 1:
            self.print_error(status)
            return False
        else:
            return status[1].strip()
    
    # write the output file locally in output_folder 
    def download_file(self , remote_file , local_file):  
            
        try:
            # timeout 24 hours
            file_content = self.session.get_file(remote_file , timeout=86400)
            res = open( local_file , 'wb')
            res.write( file_content )
            res.close()
            return True
        except Exception as e:
            if 'ERROR_FILE_EXISTS' in str(e):
                self.print_warning( '[-] ' + self.machine['name'] + " - Error: " + str(e))
            else:
                self.print_error( '[-] ' + self.machine['name'] + " - Error: " + str(e))

        return False
    
    
    # upload zip file
    def upload_file(self, src_file , dest_folder):
        self.print_info('[+] '+self.machine['name']+' - Uploading file: ['+src_file+'] -> [' + dest_folder + ']')
        file_name = src_file.split('/')[-1]
        # upload the zip file
        try:
            self.session.put_file(open(src_file ,"rb"), dest_folder + file_name)
        except Exception as e:
            if 'ERROR_FILE_EXISTS' in str(e):
                self.print_warning('[-] ' + self.machine['name'] + " - Error: " + str(e))
            else:
                self.print_error( '[-] ' + self.machine['name'] + " - Error: " + str(e))
                
            self.delete_file( dest_folder + file_name )
            return self.upload_file(src_file , dest_folder)
            
        if file_name.endswith('.zip'):
            # decompress the zip file
            if not self.decompress_file( dest_folder , file_name):
                self.print_info('[-] '+self.machine['name']+' - Failed to decompress the file: ' + dest_folder + file_name)
            else:
                self.delete_file( dest_folder + file_name )
            
        return True
    
    # delete file from sensor 
    def delete_file(self, file_path):
        try:
            self.session.delete_file( file_path )
            return True
        except:
            return False 
    
    
    # delete provided folder path
    def delete_folder(self , path):
        self.print_info('[+] '+self.machine['name']+' - Delete Folder: ' + path )
        try:
            del_fol = self.session.create_process("cmd.exe /c rmdir /Q /S "+path  , wait_for_output=True,wait_for_completion=True).decode('ascii')
            if  len(del_fol) != 0:
                self.print_info('[-] '+self.machine['name']+' - Failed Delete Folder: ' + del_fol)
                return False
                
            return True
        except:
            return False
            
            
    # check if the folder not exists in the sensor machine, create it
    def mkdir(self, folder):
        self.print_info("[+] "+self.machine['name']+" - Create Driectory: " + folder )
        try:
            self.session.create_directory(folder)
            return True
        except:
            return False
            
    # compress the provided folder
    def compress_folder(self , folder_path , file_name):
        # uplaod the 7zip executable
        if not self.upload_file(self.options['zip_path'] , self.options['CB_dest_folder']):
            return False
        
        # compress the output result    
        self.print_info("[+] "+self.machine['name']+" - Compress folder: " + folder_path + ' -> ' + file_name)
        try:
            self.session.create_process('cmd.exe /c ' + self.options['CB_dest_folder'] + '7za.exe a ' + file_name + ' ' + folder_path + ' -y ' , wait_for_output=True,wait_for_completion=True )
        except:
            return False
        return True
    
    
    # decompress the provided file
    def decompress_file(self  , folder_path , file_name):
        # uplaod the 7zip executable
        if not self.upload_file(self.options['zip_path'] , self.options['CB_dest_folder']):
            return False
        
        # compress the output result    
        self.print_info("[+] "+self.machine['name']+" - Decompress file: " + folder_path + "\\" + file_name + ' -> ' + folder_path )
        try:
            self.session.create_process('cmd.exe /c ' + self.options['CB_dest_folder'] + '7za.exe x '+folder_path + "\\" + file_name+' -o'+folder_path +' -y ' , wait_for_output=True,wait_for_completion=True )
        except:
            return False
        return True
        
        
        


 
########################################################################################################--MAin--#####################################################################

m = machines(args)

    
