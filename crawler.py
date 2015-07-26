from bs4 import BeautifulSoup
import urllib2 as ul2
import smtplib
import urllib
import ConfigParser
import json
import os.path
import pickle
import time, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Bolig(object):
    def __init__(self, title, m2, description, street, city, rent, creation_time, reserved, url, images):

        self.title = title
        self.m2 = m2
        self.description = description
        self.street = street
        self.city = city
        self.rent = rent
        self.creation_time = creation_time
        self.reserved = reserved
        self.images = images
        self.url = url

    def __str__(self):
        link = 'http://www.boligportal.dk{0}'.format(self.url)
        images = map((lambda x: '<img  src="http:' + str(x['thumb']) +'" />'), self.images)
        images = ''.join(images)
        return '<li><a style="color:#000;" href="' + link + '"><h2>{0}, {1}/mnd, {2} i {3}, {4}m2</h2></a><p>{5}</p>{6}</li>'.format(self.title, self.rent, self.street.encode('utf-8'), self.city.encode('utf-8'), self.m2, self.description.encode('utf-8'), images)
    
    


URL = 'http://www.boligportal.dk/api/soeg_leje_bolig.php'

HDR = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

# KBH = 4
area = 4
# In DKK
max_husleje = 12000

newest_bolig = 'newest_bolig'



def print_boliger(boliger):
    return ''.join(map(str, boliger))

        
class Crawler(object):
    def __init__(self, config, date_of_newest_bolig=0):
        self.date_of_newest_bolig = 0
        
        # Query
        self.interval = config.getint('Query', 'LookupIntervalSeconds')
        self.area = config.getint('Query', 'AreaCode')
        self.maxpay_dkk = config.getint('Query', 'MaxPayDKK')

        # Output
        self.receivers = config.get('Output', 'Emails').split(',')

        # Mailserver
        self.mailserver = config.get('MailServer', 'Url')
        self.mailusername = config.get('MailServer', 'Username')
        self.mailpassword = config.get('MailServer', 'Password')
        self.sender = config.get('MailServer', 'Sender')

        if os.path.exists(newest_bolig):
            f = open(newest_bolig)
            unix_date = pickle.load(f)

            self.date_of_newest_bolig = unix_date

            f.close()

    def run(self):
        error = False
        try:
          self.crawl()
        except ul2.URLError as urlError:
            error = False
        except Exception as e:
          print e
          error = True

        if error == False:
            threading.Timer(self.interval, self.run).start()

    def crawl(self):
        params = { 'serviceName': 'getProperties',
           'data': '{"amtId":"'+ str(self.area) +'","huslejeMin":"0","huslejeMax":"'+ str(self.maxpay_dkk) +'","stoerrelseMin":"0","stoerrelseMax":"0","postnrArr":[],"boligTypeArr":["0"],"lejeLaengdeArr":["4"],"page":"1","limit":"15","sortCol":"3","sortDesc":"1","visOnSiteBolig":0,"almen":-1,"billeder":-1,"husdyr":-1,"mobleret":-1,"delevenlig":-1,"fritekst":"","overtagdato":"","emailservice":"","kunNyeste":false,"muListeMuId":"","fremleje":-1}'
}
        req = ul2.Request(URL, urllib.urlencode(params), HDR)

        response = ul2.urlopen(req)

        boliger = json.load(response)['properties']

        date_fetch = self.date_of_newest_bolig
        new_boliger = []

        for bolig in boliger:
            title = bolig['jqt_headline'].encode('utf-8')
            m2 = bolig['jqt_size']['m2']
            description = bolig['jqt_adtext']
            street = bolig['jqt_location']['street']
            city = bolig['jqt_location']['city']
            rent = bolig['jqt_economy']['rent']
            creation_time = bolig['jqt_creationDate']
            reserved = bolig['jqt_reserved']
            url = bolig['jqt_adUrl']
            images = bolig['jqt_images']

            bolig_obj = Bolig(title, m2, description, street, city, rent, creation_time, reserved, url, images)

            if creation_time > self.date_of_newest_bolig:
                print str(type(creation_time)) + " : " + str(type(self.date_of_newest_bolig))
                new_boliger.append(bolig_obj)

                if creation_time > date_fetch:
                    date_fetch = creation_time

        self.update_newest_bolig(date_fetch)

        if len(new_boliger) > 0:
            
            for receiver in self.receivers:
                self.send_html_email(new_boliger, receiver)



    def send_html_email(self, boliger, to):
        html = '<html><head><meta http-equiv="content-type" content="text/html; charset=UTF-8"></head><ul style="list-style:none; padding-left: 0; font-family:\'Helvetica\'">{0}</ul></html>'.format(print_boliger(boliger))
        
        server = smtplib.SMTP(self.mailserver)
        server.ehlo()
        server.starttls()

        server.login(self.mailusername, self.mailpassword)

        msg = MIMEMultipart('alternative')
        
        if len(boliger) == 1:
            msg['Subject'] = "[BC] " + boliger[0].title
        else:
            msg['Subject'] = "[BC] " + str(len(boliger)) + " nye boliger"

                
        msg['From'] = self.sender
        msg['To'] = to

        msg.attach(MIMEText(html, 'html'))
    
        server.sendmail(self.sender, to, msg.as_string())

    def update_newest_bolig(self, time):
        self.date_of_newest_bolig = time
        f = open(newest_bolig, 'w')
        pickle.dump(time, f)
        f.close()

config = ConfigParser.ConfigParser()

config.read('src/config.ini')

c = Crawler(config)

c.run()
