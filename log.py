#!/usr/bin/python3

from settings import log_file

from logging import (
	basicConfig as log_basicConfig,
	info as log_info,
	error as log_error,
	warning as log_warning,
	INFO as log_level_info
)

log_basicConfig(
	filename = log_file,
	filemode = "a",
	format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	level = log_level_info
)

def l_info(msg):
	log_info(msg)
	print(msg)

def l_error(msg):
	log_error(msg, exc_info = True)
	print(msg)

def l_warning(msg):
	log_warning(msg)
	print(msg)