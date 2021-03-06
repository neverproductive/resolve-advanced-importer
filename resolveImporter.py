import os
import threading
import config as c
from resolve import (mediaPool)
from time import sleep
from tkinter.messagebox import showerror

from resolveBinTree import ResolveBinTree

class ResolveImporter(threading.Thread):
    
    IMPORTED_MESSAGE_DURATION = 0.7
    
    importerThread = None
    
    def __init__(self, directory) -> None:
        super().__init__()
        
        self._stop = threading.Event()
        self.directory = directory
            
    def stop(self):
        self._stop.set()
        
    def stopped(self):
        return self._stop.isSet()
    
    def run(self):
        while True:
            sleepDuration = c.sleepBetweenChecks - self.IMPORTED_MESSAGE_DURATION
            if not self.updateMessage("Importing"): return
            sleep(sleepDuration/3)
            if not self.updateMessage("Importing."): return
            sleep(sleepDuration/3)
            if not self.updateMessage("Importing.."): return
            sleep(sleepDuration/3)
            if not self.updateMessage("Importing..."): return
            
            self.importDir()
            
            if c.timelinesBin or c.compoundClipsBin or c.fusionCompsBin:
                master = ResolveBinTree.get()
                
                if c.timelinesBin:
                    timelines = master.getTimelines()
                    
                    timelinesToMove = []
                    for timeline in timelines:
                        if not c.timelinesBin.hasClip(timeline):
                            timelinesToMove.append(timeline)
                            
                    if len(timelinesToMove) > 0:
                        c.timelinesBin.moveClipsToBin(timelinesToMove)
                        print(f"[Resolve Importer] Moved {[t.GetClipProperty('Clip Name') for t in timelinesToMove]} timelines to {c.timelinesBin.getPath()}")
                    
                if c.compoundClipsBin:
                    compoundClips = master.getCompoundClips()
                    
                    compoundClipsToMove = []
                    for clip in compoundClips:
                        if not c.compoundClipsBin.hasClip(clip):
                            compoundClipsToMove.append(clip)
                    
                    if len(compoundClipsToMove) > 0:
                        c.compoundClipsBin.moveClipsToBin(compoundClipsToMove)
                        print(f"[Resolve Importer] Moved {[c.GetClipProperty('Clip Name') for c in compoundClipsToMove]} compound clips to {c.compoundClipsBin.getPath()}")
                    
                if c.fusionCompsBin:
                    fusionComps = master.getFusionComps()
                    
                    fusionCompsToMove = []
                    for clip in fusionComps:
                        if not c.fusionCompsBin.hasClip(clip):
                            fusionCompsToMove.append(clip)
                    
                    if len(fusionCompsToMove) > 0:
                        c.fusionCompsBin.moveClipsToBin(fusionCompsToMove)
                        print(f"[Resolve Importer] Moved {[c.GetClipProperty('Clip Name') for c in fusionComps]} fusion comps to {c.fusionCompsBin.getPath()}")
                    
                master.refresh()
            
            if not self.updateMessage("Importing... Finished Import"): return
            sleep(self.IMPORTED_MESSAGE_DURATION)
            
    # returns false if stopped
    def updateMessage(self, message):
        if self.stopped():
            c.importedMessage.set("")
            return False
        
        c.importedMessage.set(message)
        return True
    
    def importDir(self):
        print(f"[Resolve Importer] Importing from {self.directory} to {c.importToBin.getPath()}")
        
        c.importToBin.refresh()
        
        c.importToBin.syncBinWithFolder(self.directory, recursive = True)
        
    def toggleImport():
        if(ResolveImporter.importerThread):
            print(f"[Resolve Importer] Stopping to Import from {c.folderPath.get()} to bin {c.importToBin.getPath()}")
            c.importing.set(False)
            ResolveImporter.importerThread.stop()
            ResolveImporter.importerThread = None
        else:
            if not ResolveImporter.validateImportPath():
                return
            
            c.saveCache()
            
            print(f"[Resolve Importer] Starting to Import from {c.folderPath.get()} to bin {c.importToBin.getPath()}")
            c.importing.set(True)
            c.importedMessage.set("Importing")
            ResolveImporter.importerThread = ResolveImporter(c.folderPath.get())
            ResolveImporter.importerThread.daemon = True
            ResolveImporter.importerThread.start()
            
    def validateImportPath():
        if not os.path.isdir(c.folderPath.get()):
            showerror(title="Error", message="Invalid import path. Please check your path config and try again.")
            return False
        return True