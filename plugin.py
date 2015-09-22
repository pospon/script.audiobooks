# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='script.audiobooks')
__addonid__ = __addon__.getAddonInfo('id')
__fanart__ = __addon__.getAddonInfo('fanart')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

from audiobook import M4BHandler
from bookplayer import BookPlayer


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

        self.tmpdestination = Settings.getTempLocation()
        self.coverCache = Settings.getCoverCacheLocation()

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # Show all the EBooks that are in the eBook directory
    def showAudiobooks(self, directory=None):
        # Get the setting for the audio book directory
        audioBookFolder = Settings.getAudioBookFolder()

        if audioBookFolder in [None, ""]:
            # Prompt the user to set the eBooks Folder
            audioBookFolder = xbmcgui.Dialog().browseSingle(0, __addon__.getLocalizedString(32005), 'files')

            # Check to make sure the directory is set now
            if audioBookFolder in [None, ""]:
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32001), __addon__.getLocalizedString(32006))
                return

            # Save the directory in settings for future use
            log("AudioBooksPlugin: Setting Audio Books folder to %s" % audioBookFolder)
            Settings.setAudioBookFolder(audioBookFolder)

        # We may be looking at a subdirectory
        if directory not in [None, ""]:
            audioBookFolder = directory

        dirs, files = xbmcvfs.listdir(audioBookFolder)

        # For each directory list allow the user to navigate into it
        for dir in dirs:
            if dir.startswith('.'):
                continue

            log("AudioBooksPlugin: Adding directory %s" % dir)

            nextDir = os_path_join(audioBookFolder, dir)
            displayName = "[%s]" % dir

            url = self._build_url({'mode': 'directory', 'directory': nextDir})
            li = xbmcgui.ListItem(displayName, iconImage='DefaultFolder.png')
            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems([], replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        # Now list all of the books
        for audioBookFile in files:
            log("AudioBooksPlugin: Processing file %s" % audioBookFile)
            # Check to ensure that this is an eBook
            if not audioBookFile.endswith('.m4b'):
                log("AudioBooksPlugin: Skipping non audiobook file: %s" % audioBookFile)
                continue

            fullpath = os_path_join(audioBookFolder, audioBookFile)

            m4bHandle = M4BHandler(fullpath)
            title = m4bHandle.getTitle()
            coverTargetName = m4bHandle.getCoverImage()
            del m4bHandle

            isRead = False

            displayString = title
            log("AudioBooksPlugin: Display title is %s for %s" % (displayString, fullpath))

            if isRead:
                displayString = '* %s' % displayString

            url = self._build_url({'mode': 'chapters', 'filename': fullpath, 'cover': coverTargetName})
            li = xbmcgui.ListItem(displayString, iconImage=coverTargetName)
            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems(self._getContextMenu(fullpath), replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def listChapters(self, fullpath, defaultImage):
        log("AudioBooksPlugin: Listing chapters for %s" % fullpath)

        m4bHandle = M4BHandler(fullpath)
        chapters = m4bHandle.getChapterDetails()

        # Add all the chapters to the display
        for chapter in chapters:
            url = self._build_url({'mode': 'play', 'filename': fullpath, 'startTime': chapter['startTime']})

            li = xbmcgui.ListItem(chapter['title'], iconImage=defaultImage)

            if chapter['duration'] > 0:
                li.setInfo('music', {'Duration': chapter['duration']})

            li.setProperty("Fanart_Image", __fanart__)
            li.addContextMenuItems(self._getContextMenu(fullpath), replaceItems=True)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def play(self, fullpath, startTime=0):
        log("AudioBooksPlugin: Playing %s" % fullpath)

        m4bHandle = M4BHandler(fullpath)

        bookPlayer = BookPlayer()
        bookPlayer.playAudioBook(m4bHandle, startTime)
        del bookPlayer

    # Construct the context menu
    def _getContextMenu(self, filepath, chapterLink="", previousChapterLink="", isLastChapter='false'):
        ctxtMenu = []

        # Check if this is the last chapter of a book, or if it is the book being marked
        # rather than just the chapter
#         readFlag = isLastChapter
#         if chapterLink in [None, ""]:
#             readFlag = 'true'
#
#         # Mark as Read
#         cmd = self._build_url({'mode': 'markReadStatus', 'filename': filepath, 'link': chapterLink, 'read': readFlag})
#         ctxtMenu.append((__addon__.getLocalizedString(32011), 'RunPlugin(%s)' % cmd))
#
#         # Mark as Not Read
#         # Note, marking a chapter as "Not Read" will result in the previous chapter being
#         # marked as the last chapter that was read
#         cmd = self._build_url({'mode': 'markReadStatus', 'filename': filepath, 'link': previousChapterLink, 'read': 'false'})
#         ctxtMenu.append((__addon__.getLocalizedString(32012), 'RunPlugin(%s)' % cmd))

        return ctxtMenu

#     def markReadStatus(self, fullpath, chapterLink, markRead):
#         # If there is no chapter link then we are clearing the read flag for the whole book
#         # If the request was just for a chapter, then we would have been given the previous
#         # chapter that would have been marked as read
#         bookDB = EbooksDB()
#         bookDB.setReadChapter(fullpath, chapterLink, markRead)
#         del bookDB
#
#         xbmc.executebuiltin("Container.Refresh")


################################
# Main of the eBooks Plugin
################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("AudioBooksPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("AudioBooksPlugin: Mode is NONE - showing root menu")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.showAudiobooks()
        del menuNav
    elif mode[0] == 'directory':
        log("AudioBooksPlugin: Mode is Directory")

        directory = args.get('directory', None)

        if (directory is not None) and (len(directory) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.showAudiobooks(directory[0])
            del menuNav

    elif mode[0] == 'chapters':
        log("AudioBooksPlugin: Mode is CHAPTERS")

        # Get the actual folder that was navigated to
        filename = args.get('filename', None)
        cover = args.get('cover', None)

        if (cover is not None) and (len(cover) > 0):
            cover = cover[0]
        else:
            cover = None

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.listChapters(filename[0], cover)
            del menuNav

    elif mode[0] == 'play':
        log("AudioBooksPlugin: Mode is PLAY")

        # Get the actual chapter that was navigated to
        filename = args.get('filename', None)
        startTime = args.get('startTime', None)

        startFrom = -1
        if (startTime is not None) and (len(startTime) > 0):
            startFrom = int(startTime[0])

        if (filename is not None) and (len(filename) > 0):
            menuNav = MenuNavigator(base_url, addon_handle)
            menuNav.play(filename[0], startFrom)
            del menuNav

#     elif mode[0] == 'markReadStatus':
#         log("EBooksPlugin: Mode is MARK READ STATUS")
#
#         filename = args.get('filename', None)
#         link = args.get('link', None)
#         readStatus = args.get('read', None)
#
#         if (link is not None) and (len(link) > 0):
#             link = link[0]
#         else:
#             link = ""
#
#         markRead = False
#         if (readStatus is not None) and (len(readStatus) > 0):
#             if readStatus[0] == 'true':
#                 markRead = True
#
#         if (filename is not None) and (len(filename) > 0):
#             menuNav = MenuNavigator(base_url, addon_handle)
#             menuNav.markReadStatus(filename[0], link, markRead)
#             del menuNav
