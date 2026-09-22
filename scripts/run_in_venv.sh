#!/usr/bin/env bash

function error() {
	echo "$@" >&2
	exit 1
}

function cleanup {
	deactivate
	[[ "$VENV_DIR" == ".venv" ]] || rm -rf $VENV_DIR
}

VENV_DIR=".venv"
PYTHON=${PYTHON:=python3}

cd $(dirname "$0")

# cd to root directory of the project
while [[ ! -d src ]]; do
	cd ..
done

# parse command line arguments
while [ -n "$1" ]; do
	case "$1" in
		--python)
			shift
			PYTHON="$1"
			;;
		--venv)
			shift
			VENV_DIR="$1"
			;;
		*)
			break
			;;
	esac
	shift
done

[ $# -gt 0 ] || error "Nothing to run"

if [ ! -d "${VENV_DIR}" ]; then
		${PYTHON} -m venv "${VENV_DIR}"
		. "${VENV_DIR}/bin/activate"
		pip install --upgrade pip
		[ -f requirements.txt ] && pip install -r requirements.txt
		pip install build
		deactivate
fi

. "${VENV_DIR}/bin/activate"
trap cleanup EXIT

$@
