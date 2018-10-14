import os, glob
import time
import tempfile
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0

import logging

oldPath=os.environ['PATH'] 
os.environ['PATH'] = "/home/artecker/gecko_0.22/:%s" % oldPath

print "PATH=%s" % os.environ['PATH']

_logger = logging.getLogger(__name__)

def get_pdf(html_file,tmpdirname):

    # configure Firefox
    opts = FirefoxOptions()
    opts.add_argument("--headless")
    downloaded_file=None
    fp = webdriver.FirefoxProfile()
    
    if tmpdirname=='':
        tmpdirname=tempfile.mkdtemp()

    fp.set_preference("browser.download.folderList",2)
    fp.set_preference("browser.download.manager.showWhenStarting",False)
    fp.set_preference("browser.download.dir", tmpdirname)
    fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    fp.set_preference( "browser.download.manager.showWhenStarting", False );
    fp.set_preference( "pdfjs.disabled", True );


    _logger.info('scrape mail %s' % html_file)
    try:
        ff = webdriver.Firefox(firefox_options=opts,firefox_profile=fp)
    except:
        _logger.warning('Could not load firefox driver! %s' % html_file)
    downloaded=False

    ff.get('file://'+ html_file)

    links=[]

    # get links
    for elm in ff.find_elements_by_xpath("//a[@href]"):
        if downloaded:
            break

        if not elm.get_attribute("href"):
            continue
        
        links.append(elm.get_attribute("href"))

    ulinks=[]
    _logger.debug('----- found %d links  html file %s' % (len(links),html_file))
    for j in links:
        if j not in ulinks:
                ulinks.append(j)

    # try out all links
    for href in ulinks:
        #while not downloaded:
        #    if i > 1:
        #        break
            if downloaded:
                break
            oldSize=0
            newSize=0
            time.sleep(2)
            _logger.debug('----- try link %s' % href)
            ff.get(href)
                    
            time.sleep(5)
            if len(glob.glob(tmpdirname + '/*.pdf')) > 0:
                    downloaded_file=glob.glob(tmpdirname + '/*.pdf')[0]
                    newSize=os.path.getsize(glob.glob(tmpdirname + '/*.pdf')[0]) 
                    #print "download started, size=%s" % newSize

            else:
                    #print "no pdf found"
                    continue

            for i in range(10):
                if newSize > 0 and newSize==oldSize:
                    _logger.info('--- downloaded with size %d' % newSize)
                    downloaded=True
                    break
                oldSize=newSize
                time.sleep(5) 

    ff.close();
    return downloaded_file

