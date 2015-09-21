# -*- coding: utf-8 -*-
import os
import sys
import re
import subprocess
import traceback
import xbmc
import xbmcvfs
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.audiobooks')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__media__ = xbmc.translatePath(os.path.join(__resource__, 'media').encode("utf-8")).decode("utf-8")

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join


# Generic class for handling m4b details
class M4BHandler():
    def __init__(self, audioBookFilePath, audioBookFileName):
        self.filePath = audioBookFilePath
        self.fileName = audioBookFileName
        self.coverImage = None
        self.title = None

    # Will load the basic details needed for simple listings
    def loadBasicDetails(self):
        log("M4BHandler: Loading audio book %s (%s)" % (self.filePath, self.fileName))

        # TODO: Add call to database to retrieve already processed audio books

        # Check to see if we already have an image available
        self.coverImage = self._getExistingCoverImage()

        # Check to see if ffmpeg is enabled
        ffmpeg = Settings.getFFmpegLocation()

        if ffmpeg not in [None, ""]:
            info = None
            try:
                # Use ffmpeg to read the audio book and extract all of the details
                startupinfo = None
                if sys.platform.lower() == 'win32':
                    # Need to stop the dialog appearing on windows
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                # The ffmpeg command will throw an error if the image file already exists
                # so check to see if we already have one
                coverTempName = os_path_join(Settings.getTempLocation(), 'maincover.jpg')
                # Remove the temporary name if it is already there
                if xbmcvfs.exists(coverTempName):
                    xbmcvfs.delete(coverTempName)

                # Generate the ffmpeg command
                ffmpegCmd = [ffmpeg, '-hide_banner', '-i', self.filePath, coverTempName]
                info = subprocess.check_output(ffmpegCmd, shell=False, startupinfo=startupinfo, stderr=subprocess.STDOUT)

                if self.coverImage in [None, ""]:
                    # Check if there is an image in the temporary location
                    if xbmcvfs.exists(coverTempName):
                        coverFileName, oldExt = os.path.splitext(self.fileName)
                        targetCoverName = "%s.jpg" % coverFileName
                        coverTargetName = os_path_join(Settings.getCoverCacheLocation(), targetCoverName)

                        # Now move the file to the covers cache directory
                        copy = xbmcvfs.copy(coverTempName, coverTargetName)
                        if copy:
                            log("M4BHandler: copy successful for %s" % coverTargetName)
                            self.coverImage = coverTargetName
                        else:
                            log("M4BHandler: copy failed from %s to %s" % (coverTempName, coverTargetName))
                        xbmcvfs.delete(coverTempName)
                else:
                    # Tidy up the image that we actually do not need
                    if xbmcvfs.exists(coverTempName):
                        xbmcvfs.delete(coverTempName)
            except:
                log("M4BHandler: Failed to get data using ffmpeg for file %s with error %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

            # The pattern to find chapter info
            chapter_pattern = re.compile('^Chapter #(\d+)\.(\d+): start (\d+\.\d+), end (\d+\.\d+)$')
            # The pattern that finds the title for a chapter
            title_pattern = re.compile('^\s*title\s*:\s*(.*)$')

            if info not in [None, ""]:
                log("M4BHandler: FFmpeg info for file %s is: %s" % (self.filePath, info))

                # Get the title from the output
                lines = info.split('\n')
                linenum = 0
                while linenum < len(lines):
                    line = lines[linenum]
                    line = line.strip()

                    # Check for the first title as that will be the main title
                    if self.title in [None, ""]:
                        main_title_match = title_pattern.match(line)
                        if main_title_match:
                            self.title = main_title_match.group(1)
                            log("M4BHandler: Found title in ffmpeg output: %s" % self.title)

                    # Note: The rest of this is the chapters, so will be moved!!!!!!!!!!!!!
                    # Chapters are listed in the following format
                    # ---
                    # Chapter #0:29: start 26100.000000, end 27000.000000
                    # Metadata:
                    #   title           : Part 30
                    # ---

                    chapter_match = chapter_pattern.match(line)
                    # If we found a chapter, skip ahead to the title and ignore the lines between them
                    if not chapter_match:
                        linenum += 1
                        continue
                    else:
                        title_match = title_pattern.match(lines[linenum + 2])
                        linenum += 3
                    chapter_num = chapter_match.group(1)
                    chapter_subnum = chapter_match.group(2)
                    start_time = chapter_match.group(3)
                    end_time = chapter_match.group(4)
                    duration = str(float(end_time) - float(start_time))

        if self.title in [None, ""]:
            log("M4BHandler: No title found for %s, using filename" % self.filePath)
            self.title = self.getFallbackTitle()

    def _getExistingCoverImage(self):
        # Check if there is a cached version, or a local one on the drive
        fullpathLocalImage, bookExt = os.path.splitext(self.filePath)
        fullpathLocalImage = "%s.jpg" % fullpathLocalImage

        if xbmcvfs.exists(fullpathLocalImage):
            log("M4BHandler: Found local cached image %s" % fullpathLocalImage)
            return fullpathLocalImage

        # Check for a cached cover
        return self._getCachedCover(self.fileName)

    def getTitle(self):
        return self.title

    def getCoverImage(self):
        return self.coverImage

    # Checks the cache to see if there is a cover for this audiobook
    def _getCachedCover(self, fileName):
        cachedCover = None
        # check if the directory exists before searching
        dirs, files = xbmcvfs.listdir(Settings.getCoverCacheLocation())
        for aFile in files:
            # Get the filename without extension
            coverSrc, ext = os.path.splitext(aFile)

            # Get the name that the cached cover will have been stored as
            targetSrc, bookExt = os.path.splitext(fileName)

            if targetSrc == coverSrc:
                cachedCover = os_path_join(Settings.getCoverCacheLocation(), aFile)
                log("M4BHandler: Cached cover found: %s" % cachedCover)

        return cachedCover

    def getChapterDetails(self):
        return []

    def getFallbackTitle(self):
        # Remove anything after the final dot
        sections = self.fileName.split('.')
        sections.pop()
        # Replace the dots with spaces
        return ' '.join(sections)