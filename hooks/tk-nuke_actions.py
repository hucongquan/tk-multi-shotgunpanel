# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk
import os

HookBaseClass = sgtk.get_hook_baseclass()

class NukeActions(HookBaseClass):
    """
    Shotgun Panel Actions for Nuke
    """
    
    def generate_actions(self, sg_data, actions, ui_area):
        """
        Returns a list of action instances for a particular object.
        The data returned from this hook will be used to populate the 
        actions menu.
    
        The mapping between Shotgun objects and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the app
        has already established *which* actions are appropriate for this object.
        
        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.
        
        The ui_area parameter is a string and indicates where the item is to be shown. 
        
        - If it will be shown in the main browsing area, "main" is passed. 
        - If it will be shown in the details area, "details" is passed.
                
        :param sg_data: Shotgun data dictionary.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Shotgun Data: %s" % (ui_area, actions, sg_data))
        
        action_instances = []

        if "assign_task" in actions:
            action_instances.append( {"name": "assign_task", 
                                      "params": None,
                                      "caption": "Assign Task to yourself", 
                                      "description": "Assign this task to yourself."} )

        if "read_node" in actions:
            action_instances.append( {"name": "read_node", 
                                      "params": None,
                                      "caption": "Create Read Node", 
                                      "description": "This will add a read node to the current scene."} )

        if "script_import" in actions:        
            action_instances.append( {"name": "script_import",
                                      "params": None, 
                                      "caption": "Import Contents", 
                                      "description": "This will import all the nodes into the current scene."} )        
    
        return action_instances
                

    def execute_action(self, name, params, sg_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.
        
        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_data: Shotgun data dictionary
        :returns: No return value expected.
        """
        app = self.parent        
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Shotgun Data: %s" % (name, params, sg_data))
        
        if name == "assign_task":
            if app.context.user is None:
                raise Exception("Cannot establish current user!")
            
            data = app.shotgun.find_one("Task", [["id", "is", sg_data["id"]]], ["task_assignees"] )
            assignees = data["task_assignees"] or []
            assignees.append(app.context.user)
            app.shotgun.update("Task", sg_data["id"], {"task_assignees": assignees})
        
        if name == "read_node":
            # resolve path - forward slashes on all platforms in Nuke
            path = self.get_publish_path(sg_data).replace(os.path.sep, "/")
            self._create_read_node(path, sg_data)
        
        if name == "script_import":
            # resolve path - forward slashes on all platforms in Nuke
            path = self.get_publish_path(sg_data).replace(os.path.sep, "/")
            self._import_script(path, sg_data)
           
    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behavior of things
    
    def _import_script(self, path, sg_publish_data):
        """
        Import contents of the given file into the scene.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        import nuke
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)
        
        nuke.nodePaste(path)
                
    def _create_read_node(self, path, sg_publish_data):
        """
        Create a read node representing the publish.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.        
        """        
        import nuke
        
        (_, ext) = os.path.splitext(path)

        valid_extensions = [".png", 
                            ".jpg", 
                            ".jpeg", 
                            ".exr", 
                            ".cin", 
                            ".dpx", 
                            ".tiff", 
                            ".tif", 
                            ".mov", 
                            ".psd",
                            ".tga",
                            ".ari",
                            ".gif",
                            ".iff"]

        if ext.lower() not in valid_extensions:
            raise Exception("Unsupported file extension for '%s'!" % path)

        # find the sequence range if it has one:
        seq_range = self._find_sequence_range(path)
        
        # create the read node
        if seq_range:
            nuke.nodes.Read(file=path, first=seq_range[0], last=seq_range[1])
        else:
            nuke.nodes.Read(file=path)
                    

    def _find_sequence_range(self, path):
        """
        Helper method attempting to extract sequence information.
        
        Using the toolkit template system, the path will be probed to 
        check if it is a sequence, and if so, frame information is
        attempted to be extracted.
        
        :param path: Path to file on disk.
        :returns: None if no range could be determined, otherwise (min, max)
        """
        # find a template that matches the path:
        template = None
        try:
            template = self.parent.sgtk.template_from_path(path)
        except TankError:
            pass
        
        if not template:
            return None
            
        # get the fields and find all matching files:
        fields = template.get_fields(path)
        if not "SEQ" in fields:
            return None
        
        files = self.parent.sgtk.paths_from_template(template, fields, ["SEQ", "eye"])
        
        # find frame numbers from these files:
        frames = []
        for file in files:
            fields = template.get_fields(file)
            frame = fields.get("SEQ")
            if frame != None:
                frames.append(frame)
        if not frames:
            return None
        
        # return the range
        return (min(frames), max(frames))


