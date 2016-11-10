#!/bin/bash
#/Usage: git-history-migrate-branch.sh module-list.txt Source-repo Destination-repo
# module-list.txt is a list of odoo modules to be migrated from a project to
# another. Must be one line per module.
# instance-list.txt is a list of odoo projects which are affected by the
# migration of this modules. Must be one line per instance.
# token.txt must be located on $HOME_DIR
# To create TOKEN you must go to github.com / Settings / Personal Access Token
# and create a new one. Beware: TOKEN is like a password so it be kept safe.

# This could be helpful for rewriting history on project
# https://developer.atlassian.com/blog/2015/08/grafting-earlier-history-with-git/

# Scripted by:
# Humberto Arocha <hbto@vauxoo.com>

HOME_DIR=/root
ROOT_DIR=$HOME_DIR/branches
USR_DST=vauxoo-dev
USR_SRC=vauxoo
SRC=l10n-canada
DST=account-payment
DEV=osval
VER=9.0
# TOKEN=$(cat $HOME_DIR/token.txt)
# AUTH="\"""Authorization: token $TOKEN""\""

echo "Moving inside $HOME_DIR Folder"
cd $HOME_DIR

if [ ! -d "$ROOT_DIR" ]; then
    echo "Creating Folder $ROOT_DIR"
    mkdir -p $ROOT_DIR
fi

echo "Moving inside $ROOT_DIR Folder"
cd $ROOT_DIR

echo "Checking if Folder $SRC already exists"
if [ -d "$SRC" ]; then
    echo "Deleting Folder $SRC"
    rm -rf $SRC
fi
echo "Cloning $SRC Project"
git clone git@github.com:$USR_SRC/$SRC -b $VER
cd $SRC
echo "Adding remote development branch to $SRC"
git remote add vauxoo-dev git@github.com:vauxoo-dev/${SRC}.git
echo "Switching back to $ROOT_DIR"
cd $ROOT_DIR

echo "Checking if Folder $DST already exists"
if [ -d "$DST" ]; then
    echo "Deleting Folder $DST"
    rm -rf $DST
fi
echo "Cloning $DST Project"
git clone git@github.com:$USR_SRC/$DST -b $VER
cd $DST
echo "Adding remote development branch to $DST"
git remote add vauxoo-dev git@github.com:vauxoo-dev/${DST}.git
echo "Switching back to $ROOT_DIR"
cd $ROOT_DIR

while IFS='' read -r MODULE || [[ -n "$MODULE" ]]; do
    echo "Module: $MODULE"

    echo "Moving inside $ROOT_DIR Folder"
    cd $ROOT_DIR

    if [ -d "tmp-$SRC" ]; then
        echo "Deleting Folder tmp-$SRC"
        rm -rf tmp-$SRC
    fi

    echo "Duplicating $SRC Folder to tmp-$SRC Folder"
    cp -r $SRC/ tmp-$SRC

    echo "Moving inside tmp-$SRC to migrate $MODULE"
    cd tmp-$SRC

    echo "Checking out stable branch $VER on $SRC Branch"
    git checkout $VER
    git pull
    git fetch vauxoo-dev

    echo "Checking out to new branch $VER-tmp-$MODULE-$DEV"
    git checkout -b $VER-tmp-$MODULE-$DEV

    echo "Rewriting $SRC branch for $MODULE module"
    git filter-branch --subdirectory-filter $MODULE -- --all
    mkdir $MODULE
    git mv -k * $MODULE
    git commit -am "[GIT] $MODULE Git history"


    echo "Moving inside $ROOT_DIR Folder"
    cd $ROOT_DIR

    echo "Moving inside $DST to migrate $MODULE"
    cd $DST/

    echo "Checking out stable branch $VER on $DST Branch"
    git checkout $VER
    git pull
    git fetch vauxoo-dev

    echo "Adding local $SRC repo"
    git remote add $SRC ../tmp-$SRC

    echo "Fetching local $SRC repo"
    git fetch $SRC

    echo "Merging migrated module history $MODULE to $VER into $DST"
    git checkout -b $VER-migrate-$MODULE-from-$SRC-$DEV
    git merge $SRC/$VER-tmp-$MODULE-$DEV --commit --allow-unrelated-histories

    echo "Pushing history for $MODULE module to $DST project"
    git push vauxoo-dev $VER-migrate-$MODULE-from-$SRC-$DEV

    echo "Moving inside $ROOT_DIR Folder"
    cd $ROOT_DIR

    echo "Deleting  tmp-$SRC Because after being used is useless"
    rm -rf tmp-$SRC

    echo "Moving inside $SRC to delete $MODULE"
    cd $SRC

    echo "Checking out stable branch $VER on $SRC Branch"
    git checkout $VER

    echo "Removing $MODULE module from $SRC"
    git checkout -b  $VER-migrate-$MODULE-to-$DST-$DEV
    git rm -rf $MODULE
    git commit -am "[REM] $MODULE got moved to $DST"
    
    echo "Pushing $MODULE removal to $DST"
    git push vauxoo-dev $VER-migrate-$MODULE-to-$DST-$DEV

done < "$1"


