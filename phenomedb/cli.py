
import json, glob
import importlib
import inspect as isp
import argparse
import os, sys
if os.environ['PHENOMEDB_PATH'] not in sys.path:
   sys.path.append(os.environ['PHENOMEDB_PATH'])

import phenomedb.utilities as utils
from phenomedb.config import config
     
class CLI:
    """PhenomeDB CLI module - for running tasks via the command line.
    
    :param argv: The list of command line arguments.
    :type argv: list
    """    

    
    def read_json_task_spec(self):
        """Read the task json file.

        :return: The task spec json.
        :rtype: dict
        """        
        print(config['PIPELINES'])
        with open(config['PIPELINES']['task_spec_file'], "r") as read_file:
            json_tasks = json.load(read_file)
    
        return json_tasks

    def usage_exit(self):
        """Print a usage message and exit.
        """        
        print("\nUSAGE: python pdb_cli.py [--db_env [PROD|TEST]] <task> \n\tWhere <task> is one of:")
        for t in self.available_tasks:
            print("\t", t)
        print ("\nFor task parameter list, type 'python pdb_cli.py <task> -h'")
        sys.exit(0)
    
            
    def __init__(self, argv):
    
        from phenomedb.config import config

        #self.task_dir  = config['DATA']['task_directory']
        self.task_json = self.read_json_task_spec()

        self.available_tasks = [t for t in self.task_json.keys()]

        selected_task = None

        if len(argv)==1 or argv[1] == '-h':
            self.usage_exit()
        elif argv[1] not in self.task_json.keys():
            self.usage_exit()
        else:
            selected_task = argv[1]

        parser = argparse.ArgumentParser()
        parser.add_argument("--db_env", choices=["PROD", "TEST"], help="choose production or test database")
        # 'dest' value will store the task command used
        subparsers = parser.add_subparsers(dest="task_name")
        
        parsers = {}

        for t in self.available_tasks:
            # add a subparser for each task defined in the JSON file
            parsers[t] = subparsers.add_parser(t)

            task_def = self.task_json.get(t)
            # and add the parameters for each task
            for p in task_def.keys():
                d = task_def[p]
                try:
                    required = d["required"]
                except KeyError as e:
                    required = False

                if d['type'] in ['project','lambda','str','file_path_remote','file_upload','metadata_harmonised_field','json']:
                    type = str
                elif d['type'] in ['list','dropdown']:
                    type = list
                elif d['type'] == 'float':
                    type = float
                elif d['type'] in ['bool','boolean']:
                    type = bool
                else:
                    raise Exception("Unknown type %s" % d['type'])

                if required:
                    parsers[t].add_argument(p, type=type, help=d["label"], nargs="*")
                else:
                    parsers[t].add_argument("--" + p, type=type, help=d["label"], nargs="*")

        args = parser.parse_args()
        data = vars(args)
        self.data = {'db_env':data['db_env']}
        if selected_task:
            task_def = self.task_json[selected_task]
            for arg_name,arg_value in data.items():
                if arg_name in task_def.keys():
                    if task_def[arg_name]['type'] == 'str' and isinstance(arg_value,list) and len(arg_value) == 1:
                        data[arg_name] = arg_value[0]
                    elif task_def[arg_name]['type'] == 'list' and isinstance(arg_value,list) and len(arg_value) == 0:
                        data[arg_name] = None
                self.data[arg_name] = data[arg_name]

        print("The following will be executed: %s" % self.data)
       

    def get_task_module(self, mod_classes):
        """Get the task module by task_class_name.

        :param task_class_name: The task class name.
        :type task_class_name: str
        :return: The task module.
        :rtype: :class:`phenomed.tasks.*`
        """        

        """
        this is not very efficient at all
        basically loading all modules before
        knowing which is the right one
        """
        loaded_module = None
        
        #actual_task_modules = [os.path.basename(os.path.dirname(x)) + "." + os.path.basename(x)[:-3] for x in glob.glob(self.task_dir + "/**/*.py")]
        #print("matching module with class %s" % task_class_name)

        for mod_class in mod_classes:

            module, class_name = utils.get_module_and_class_name(mod_class)
            
            loaded_module = importlib.import_module("phenomedb." + module)

            class_members = isp.getmembers(loaded_module, isp.isclass)
        
            for name, cls in class_members:
                if name == class_name:
                    print("Found module %s" % loaded_module)
                    return loaded_module
                                       
        return loaded_module


    def execute(self):
        """Execute the task
        """        
       
        # separate the task name and the db env from the task parameter list
        args_dict = self.data
        mod_class = args_dict.pop("task_name")
        print("mod_class")
        print(mod_class)
        print("data")
        print(self.data)
        print(args_dict)

        module_name, class_name = utils.get_module_and_class_name(mod_class)

        #m = self.get_task_module(module)
        if module_name is not None:
            values_only_dict = {}

            # remove parameters with None values so as not 
            # to overwrite defaults
            values_only_dict = {k: v for k, v in args_dict.items() if v is not None}

            print(values_only_dict)

            module = importlib.import_module(module_name)
            class_ = getattr(module,class_name)

            task_instance = class_(**values_only_dict)
           
            task_instance.run()
        else:
            print("Unable to find module for task %s" % class_name)
       

if __name__ == "__main__":
    print(sys.argv)
    utility = CLI(sys.argv)
    utility.execute()