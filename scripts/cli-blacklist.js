#!/usr/bin/env node

'use strict';

/*
 * cli-blacklist
 * Adds given users to blacklist.txt if they don't already exist there
 * Also removes the user from users.txt
 * USAGE: ./cli-blacklist.js user1 user2 ...
 */

const program = require('commander');
const chalk = require('chalk');

const readConfig = require('./lib/read-config');
const Twitter = require('./lib/twitter');
const Userlist = require('./lib/userlist');
const Blacklist = require('./lib/blacklist');

const config = readConfig().Twitter;
const twitter = new Twitter(config);
const userlist = new Userlist();
const blacklist = new Blacklist();

let usernames;

const error = msg => {
  console.error(chalk.red(`ERROR: ${msg}`));
};

const warn = msg => {
  console.error(chalk.yellow(msg));
};

const info = msg => {
  console.log(chalk.cyan(msg));
}

program
  .arguments('[username...]')
  .action( (names) => { usernames = names; } )
  .parse(process.argv);

if (!usernames || !usernames.length) {
  error('No usernames given');
  process.exit(1);
}

usernames.forEach( username => {
  twitter.getIDByScreenName(username)
    .then( id => {
      if (blacklist.isBlacklisted(id)) {
        warn(`'${username}' is already blacklisted`);
        return;
      }
      blacklist.blacklistUser(id);
      blacklist.save();
      userlist.removeUser(id);
      userlist.save();
      info(`'${username}' blacklisted`);
    })
    .catch( err => {
      error(err);
    });
});

