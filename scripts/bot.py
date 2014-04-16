#!/usr/bin/env python

# SL Bio Bot

import os
import sys
import re
import urllib
import twitter
import ConfigParser
from collections import namedtuple
from optparse import OptionParser
from random import randint

USER_LIST_FILE='users.txt'
BIOS_LIST_FILE='bios.txt'
CONFIG_FILE='configs.txt'
EXCLAMS=['Lookie!', 'Hey look!', 'Bang!', 'Wheee!', 'Whoa!', 'Holy moly!', 'Shaaa!']
MAX_REQ=100  # Maximum num of users to lookup in a single query. Max allowed is 100.

user_ids = []
bios = {}
shouldWrite = False

Change = namedtuple("Change", "user old new")

def getRandomExclam():
    return EXCLAMS[randint(0, len(EXCLAMS)-1)]

def loadUserList():
    global user_ids
    global bios

    if not os.path.exists(USER_LIST_FILE):
        sys.stderr.write("User file [%s] not found. Exiting...\n" % USER_LIST_FILE)
        sys.stderr.flush()
        sys.exit(1)

    try:
        fh = open(USER_LIST_FILE, 'r')
    except IOError, e:
        sys.stderr.write("User list file coud not be opened: %s\n" % e)
        sys.stderr.flush()
        sys.exit(1)

    # Read the user file and populate users
    while 1:
        user_id = fh.readline().strip()
        if not user_id: break

        if user_id in user_ids:
            sys.stderr.write("Duplicate detected: %s\n" % user_id)
            sys.stderr.flush()
            continue
        user_ids.append(user_id)

    fh.close()

def loadBioList():
    global bios
    if not os.path.exists(BIOS_LIST_FILE):
        sys.stderr.write("Bios file [%s] not found. Exiting...\n" % BIOS_LIST_FILE)
        sys.stderr.flush()
        sys.exit(1)

    try:
        fh = open(BIOS_LIST_FILE, 'r')
    except IOError, e:
        sys.stderr.write("Bios list file coud not be opened: %s\n" % e)
        sys.stderr.flush()
        sys.exit(1)

    # Read the bios file and populate bios
    while 1:
        user_id = fh.readline().strip()
        if not user_id:
            break
        bio = fh.readline().strip()

        if user_id not in user_ids:
            sys.stderr.write("User ID not in users file: %s\n" % user_id)
            sys.stderr.flush()
            continue

        bios[user_id] = bio


def writeBios():
    global user_ids
    global bios

    try:
        fh = open(BIOS_LIST_FILE, 'w')
    except IOError, e:
        sys.stderr.write("User file could not be opened for reading. %s\n" % e)
        sys.stderr.flush()
        sys.exit(1)

    user_ids.sort()

    for u in user_ids:
        fh.write("%s\n" % u)
        try:
            fh.write("%s\n" % bios[u])
        except KeyError:
            sys.stderr.write("No bio found for user %s\n" % u)
            sys.stderr.flush()
            continue

    fh.close()

# Main function that checks twitter for bio changes
def lookupUsers():
    global user_ids
    global bios
    global api
    global shouldWrite

    # Segment the users list to chunks of MAX_REQ. This should be <=100
    # Each user lookup call to Twitter API sends a chunk of MAX_REQ users
    tmp = user_ids
    segs = []
    while tmp:
        segs.append(tmp[:MAX_REQ])
        tmp = tmp[MAX_REQ:]

    changes = []

    for seg in segs:
        results = api.UsersLookup(user_id=seg)

        # Some names might be missing from the results
        # eg: some idiots change their screen names from time to time
        if len(seg) != len(results):
            sys.stderr.write("Missing names detected: %d vs %d\n"% (len(seg), len(results)))
            reslist = list(res.screen_name.lower() for res in results)
            # Get the list of names that we requested but was absent in the results
            missing = [x for x in seg if x not in reslist] # pissu hadenawa O_o
            sys.stderr.write("Missing   : %s\n" % str(missing))
            sys.stderr.flush()
            # This ain't fatal, so we can continue with the available results

        # Iterate the results from twitter
        for res in results:
            scname = res.screen_name.lower()
            uid = str(res.id)
            desc = res.description.encode('utf-8')
            desc = urllib.quote(desc)
            desc = re.sub('/', '%2F', desc) # encode forward slashes in urls

            # When adding new names to the list, their bios are set to -
            # Not considering these as changes, but should be written to file
            if uid not in bios.keys():
                print "New entry %s" % scname
                shouldWrite = True
                bios[uid] = desc

            # There's a change!
            elif bios[uid] != desc:
                print "Changed! %s" % scname
                shouldWrite = True

                old = bios[uid]
                if not old: old = '-' # Fix for blank URLs

                bios[uid] = desc  # Update dictionary
                if not desc: desc = '-' # Fix for blank URLs

                # Add to list of changes
                changes.append(Change(scname, old, desc))  # add name for changes instead of uid for tweeting
            else:
                pass

    return changes

def tweet(changes):
    global api

    for ch in changes:
        exclam = getRandomExclam()
        url = "http://slbiobot.herokuapp.com/d/%s/%s/%s" % (ch.user, ch.old, ch.new)
        tw = "%s @%s has changed the bio! %s" % (exclam, ch.user, url)
        api.PostUpdate(tw)

# __main__

### Parse command-line args ###
parser = OptionParser()
# -d option for dryrun. File will be updated, but nothing tweeted.
parser.add_option("-d", "--dryrun", action="store_true", dest="dry", default=False, help="If specified, output won't be tweeted")
# -f for full dryrun. File not updated, nothing tweeted.
parser.add_option("-f", "--fulldryrun", action="store_true", dest="fdry", default=False, help="If specified, output won't be written or tweeted")

(options, args) = parser.parse_args()

### Read configs ###
config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)
section = "Twitter"
configs=config.options(section)

keys = []
for cfg in configs:
    keys.append(config.get(section, cfg))

# Connect to twitter
api = twitter.Api(consumer_key=keys[0],
                consumer_secret=keys[1],
                access_token_key=keys[2],
                access_token_secret=keys[3])

# Load existing users, bios
loadUserList()
loadBioList()
# Check for changes
changes = lookupUsers()

# Take action!
if not options.fdry:
    if shouldWrite:
        writeBios()
        if not options.dry:
            tweet(changes)
        else:
            print "Not tweeting in dry run mode"
    else:
        print "Nothing to write or tweet"
else:
    print "Not writing or tweeting in full dry run mode"

