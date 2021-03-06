import os
import zipfile
import config as c
from os.path import normpath
from pathHelpers import *
from resolve import (mediaPool)
from clipTypes import ResolveClipTypes

# Clip Name: c.GetClipProperty('Clip Name') # GetName doesn't work for all types
# Clip Path: c.GetClipProperty('File Path')

class ResolveBinTree:
    BIN_PATH_SEPARATOR = "/"
    Instance = None
    
    def __init__(self, bin, parent = None) -> None:
        self.bin = bin
        self.parent = parent
        self.name = self.bin.GetName()
        self.childBins = []
        self.notAddedFiles = set()
        
        # get path
        currentBin = self
            
        path = ""
        
        while currentBin:
            path = self.BIN_PATH_SEPARATOR + currentBin.getName() + path
            currentBin = currentBin.getParent()
            
        # remove the first slash
        path = path[1:]
        
        self.path = path
        
        self.refresh()
        
    def __str__(self) -> str:
        return self.getPath()
    
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other: object) -> bool:
        if self is None or other is None:
            return False
        
        if not isinstance(other, ResolveBinTree):
            return False
        
        return self.getPath() == other.getPath() and len(self.getChildBins()) == len(other.getChildBins())
    
    def __hash__(self) -> int:
        return hash(self.getPath()) * len(self.getChildBins())
    
    def refresh(self):
        self.clips = self.bin.GetClipList()
        
        foundBinTrees = []
        noBinTreeFolders = []
        
        for folder in self.bin.GetSubFolderList():
            found = False
            for childBin in self.childBins:
                if self.isChildBinResolveFolder(childBin, folder):
                    found = True
                    foundBinTrees.append(childBin)
                    break
                
            if not found:
                noBinTreeFolders.append(folder)
        
        extraBinTrees = [bt for bt in self.childBins if bt not in foundBinTrees]
        
        for extraBinTree in extraBinTrees:
            self.childBins.remove(extraBinTree)
            
        for folder in noBinTreeFolders:
            self.childBins.append(ResolveBinTree(folder, self))
            
        for childBin in self.childBins:
            childBin.refresh()
            
    def get():
        if not ResolveBinTree.Instance:
            ResolveBinTree.Instance = ResolveBinTree(mediaPool.GetRootFolder())
        
        ResolveBinTree.Instance.refresh()
        return ResolveBinTree.Instance
    
    def getName(self):
        return self.name
    
    def getParent(self):
        return self.parent
    
    def getPath(self):
        return self.path
                   
    def getBinPathsRecursive(self):
        paths = []
        path = self.getPath()
        paths.append(path)
        
        for childBin in self.getChildBins():
            childBinPaths = childBin.getBinPathsRecursive()
            paths.extend(childBinPaths)
            
        return paths
    
    def findBinFromPath(self, path, default = None):
        if not isinstance(path, list):
            if not path:
                path = []
            else:
                path = path.split(self.BIN_PATH_SEPARATOR)
        
        if len(path) == 0:
            print(f"[{self.getName()}] Error finding bin: path is empty")
            return default
        
        if path[0] == self.getName():
            path.pop(0)
        
        if len(path) == 0:
            return self
        
        for childBin in self.getChildBins():
            pathInChildBin = childBin.findBinFromPath(path, default)
            if pathInChildBin != default:
                return pathInChildBin
            
        return default
            
    def hasClips(self):
        return not not self.clips
    
    def hasClip(self, clip):
        hasClip = False
                        
        for childClip in self.getBin().GetClipList():
            if childClip.GetMediaId() == clip.GetMediaId():
                hasClip = True
                break
            
        return hasClip
    
    def hasChildBins(self):
        return not not self.childBins
    
    def getBin(self):
        return self.bin
    
    def getClips(self, recursive = False):
        return self.clips
    
    def getChildBins(self, recursive = False):
        return self.childBins
    
    def isEmpty(self):
        if self.hasClips():
            return False
        
        if self.hasChildBins():
            for bin in self.getChildBins():
                if not bin.isEmpty():
                    return False
        
        return True
    
    # Check if child bin matches a resolve folder (because resolve folders don't have an ID :())
    def isChildBinResolveFolder(self, childBin, resolveFolder):
        if childBin not in self.getChildBins():
            return False
        
        if len(childBin.getChildBins()) != len(resolveFolder.GetSubFolderList()):
            return False
        
        if childBin.getPath() != self.getPath() + self.BIN_PATH_SEPARATOR + resolveFolder.GetName():
            return False
        
        return True
    
    def isIgnored(self):
        ignoredBinPaths = [b.getPath() for b in c.ignoredBins]
        
        if c.timelinesBin:
            ignoredBinPaths.append(c.timelinesBin.getPath())
        if c.compoundClipsBin:
            ignoredBinPaths.append(c.compoundClipsBin.getPath())
        if c.fusionCompsBin:
            ignoredBinPaths.append(c.fusionCompsBin.getPath())
        
        for ignoredBinPath in ignoredBinPaths:
            if ignoredBinPath in self.getPath() and len(self.getPath()) >= len(ignoredBinPath):
                return True
            
        return False
    
    def getTimelines(self, recursive = True, respectIgnore = True):
        timelines = []
        
        timelines.extend(self.getClipsByType(recursive, respectIgnore, ResolveClipTypes.Timeline))
        
        return timelines
    
    def getCompoundClips(self, recursive = True, respectIgnore = True):
        compoundClips = []
        
        compoundClips.extend(self.getClipsByType(recursive, respectIgnore, ResolveClipTypes.Compound))
        
        return compoundClips
    
    def getFusionComps(self, recursive = True, respectIgnore = True):
        comps = []
        
        comps.extend(self.getClipsByType(recursive, respectIgnore, ResolveClipTypes.Generator, ResolveClipTypes.Fusion))
        
        return comps
    
    def getClipsByType(self, recursive = True, respectIgnore = False, *clipTypes):
        clips = []
        
        if not respectIgnore or not self.isIgnored():
            for clip in self.getClips():
                if ResolveClipTypes.isAnyType(clip, *clipTypes):
                    clips.append(clip)
                    
            if recursive:
                for childBin in self.getChildBins():
                    clips.extend(childBin.getClipsByType(recursive, respectIgnore, *clipTypes)) 
        
        return clips
    
    def getMissingClips(self):
        files = []
        missingFiles = []
        
        files.extend(self.getClipsByType(True, True, *ResolveClipTypes.getImportedTypes()))
        
        for file in files:
            if not os.path.exists(normpath(file.GetClipProperty()['File Path'])):
                missingFiles.append(file)
                
        return missingFiles
    
    def getUnusedFiles(self):
        files = []
        unusedFiles = []
        
        files.extend(self.getClipsByType(True, True, *ResolveClipTypes.getImportedTypes()))
        
        for file in files:
            if int(file.GetClipProperty()['Usage']) == 0:
                unusedFiles.append(file)
                
        return unusedFiles
    
    def getEmptyChildBins(self, skipBins = [], recursive = True, delete = False):
        emptyBins = []
        
        for bin in self.getChildBins():
            if bin in skipBins or bin.isIgnored():
                continue
            
            if bin.isEmpty():
                emptyBins.append(bin)
                
                if delete:
                    self.deleteChildBins([bin])
                    
                continue
                
            elif recursive:
                emptyChildBins = bin.getEmptyChildBins(skipBins, recursive, False)
                emptyBins.extend(emptyChildBins)
                
                if delete:
                    bin.deleteChildBins(emptyChildBins)
                    
        return emptyBins
    
    def moveClipsToBin(self, clips, refresh = True):
        mediaPool.MoveClips(clips, self.getBin())
        
        if refresh:
            self.refresh()
    
    def deleteClips(self, files, deleteFiles = False, refresh = False):
        if not files:
            return
        
        action = "Deleting" if deleteFiles else "Removing"
        
        print(f"[{self.getName()}] {action} clips: " + str([file.GetClipProperty()['File Path'] for file in files]))
        
        if deleteFiles:
            for file in files:
                os.remove(normpath(file.GetClipProperty()['File Path']))
            
        mediaPool.DeleteClips(files)
        
        for file in files:
            if file in self.clips:
                self.clips.remove(file)
        
        if refresh:
            self.refresh()
        
    def deleteChildBins(self, bins):
        if not bins:
            return
        
        print(f"[{self.getName()}] Deleting bins: " + str(bins))
        
        for bin in bins:
            mediaPool.DeleteFolders(bin.getBin())
            self.childBins.remove(bin)
    
    def syncBinWithFolder(self, folder, recursive = True):
        ignoredFileExtensions = ['.' + x for x in c.ignoredFileExtensions.get().split(',') if x]
        importedFiles = []
        indexedChildBins = []
        
        if not folder:
            return
            
        for root, dirs, files in os.walk(folder):
            # add missing files
            for file in files:
                filePath = normpath(os.path.join(root, file))
                
                # handle archives
                if zipfile.is_zipfile(filePath):
                    # unzip archives
                    if c.unzipArchives.get():
                        zipPath = getPathWithoutFileExtension(filePath)
                        if not os.path.exists(zipPath):
                            print(f"[{self.getName()}] Unzipping archive {filePath}")
                            with zipfile.ZipFile(filePath,"r") as zip:
                                zip.extractall(zipPath)
                                dirs.append(getFolderNameFromPath(zipPath))
                            
                        if c.deleteUnzippedArchives.get():
                            print(f"[{self.getName()}] Deleting unzipped archive {filePath}")
                            os.remove(filePath)
                            
                    # no need to import zip files
                    continue
                
                if filePath in self.notAddedFiles:
                    continue
                
                # is the file ignored
                if getFileExtensionFromPath(filePath) in ignoredFileExtensions:
                    print(f"[{self.getName()}] Skipping ignored file (by extension) {filePath}")
                    self.notAddedFiles.add(filePath)
                    continue
                
                # is the file already imported
                importedFile = next((f for f in self.getClips() if f and normpath(f.GetClipProperty()['File Path']) == filePath), None)
                
                if not importedFile:
                    importedFilesList = mediaPool.ImportMedia(filePath)
                    print(f"[{self.getName()}] Adding File {filePath}")
                    
                    if not importedFilesList:
                        if(getFileNameFromPath(file).startswith(".")):
                            print(f"[{self.getName()}] Skipping file that starts with . {filePath} (Resolve can't import those)")
                        else:
                            print(f"[{self.getName()}] Failed Adding File {file}")
                        self.notAddedFiles.add(filePath)
                        continue
                    
                    importedFile = importedFilesList[0]
                    
                    if not self.hasClip(importedFile):
                        self.moveClipsToBin([importedFile], False)
                    
                    self.clips.append(importedFile)
                        
                importedFiles.append(importedFile.GetClipProperty()['File Path'])
                
            # add missing folders
            for dir in dirs:
                dirPath = os.path.join(root, dir)
                dirName = getFolderNameFromPath(dir)
                childBin = next((b for b in self.getChildBins() if b.getName() == dirName), None)
                
                if not childBin:
                    newBin = mediaPool.AddSubFolder(self.getBin(), dirName)
                    
                    if not newBin:
                        print(f"[{self.getName()}] Failed adding bin {dirName}")
                    
                    print(f"[{self.getName()}] Adding new bin {dirName}")
                    childBin = ResolveBinTree(newBin, self)
                    self.childBins.append(childBin)
                    
                indexedChildBins.append(childBin)
                    
                if recursive:
                    childBin.syncBinWithFolder(dirPath)
                    
            # we only want to process the current directory; let the bin tree handle the recursion
            break
        
        # bins that are not in the folder    
        extraBins = list(set(self.getChildBins()) - set(indexedChildBins))
        
        # iterate over the extra bins for the delete operations
        for extraBin in extraBins:
            extraBin.syncBinWithFolder(None)
        
        # remove files from Resolve that don't exist in the folder
        if c.removeExtraFiles.get() and not self.isIgnored():
            for clip in self.getClips():
                if(ResolveClipTypes.isImported(clip) and      # is a file type we can import
                    not clip.GetClipProperty()['File Path'] in importedFiles and             # is not already imported
                    int(clip.GetClipProperty("Usage")) == 0): # is not used
                        print(f"[{self.getName()}] Removing unused file {clip.GetClipProperty()['File Path']}")
                        self.deleteClips([clip], deleteFiles=False, refresh=False)
                
        # remove empty bins
        if c.removeEmptyBins.get() and not self.isIgnored():
            self.getEmptyChildBins(indexedChildBins, recursive=False, delete=True)