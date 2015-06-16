#!/bin/sh

DUMP=$1

DB_HOST=$(echo "postgres://postgres:postgres@$POSTGRES_PORT_5432_TCP_ADDR:$POSTGRES_PORT_5432_TCP_PORT/postgres")

echo "Dropping db..."
psql $DB_HOST -c "DROP DATABASE politikon;"

echo "Creating empty db..."
psql $DB_HOST -c "CREATE DATABASE politikon;"

echo "Restoring db dump..."
pg_restore --verbose --clean --no-acl --no-owner -d $DB_HOST $DUMP 

echo "Dump $DUMP restoration completed"

