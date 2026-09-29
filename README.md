# webber

## Description
Text-Mode Web Reader

## Install
```
make clean install
```

## CLI Options
```
usage: main.py [-h] [-v] [-b] [-C {auto,always,never}] url

webber - command-line web reader

positional arguments:
  url                   URL

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -b, --batch           Run in plain text mode
  -C, --colors {auto,always,never}
                        Color output mode
  -l, --log {CRITICAL,ERROR,WARNING,INFO,DEBUG,TRACE}
                        Set the logging level
  -N, --line_numbers    Enable line numbers
  -r, --reset           Reset the application's history and configuration
```

## Operation
Webber can run in either plain CLI mode or as a full-screen app. if `-b|--batch` is specified in the command-line or if STDOUT is redirected, Webber will run in plain CLI mode, otherwise the full-screen mode will be selected.
In full-screen mode, the screen is divided into 4 regions: Title bar, main content area, prompt line (Edit mode only) and a status-bar.

### Viewing Help Information
In order to open the help page, either press `?` in view mode, or `h` in the prompt line when active.

### Following Hyper-Links
Links in an HTML page are prefixed with a dimmed `{nnn}`. Whenever you want to browse to a specific link, enter command-mode (`:`), and enter the link's ID prefixed with a `#` character (`#nnnn`).

### Text Search
To search for text in the content-area, enter command-mode (`:`), and enter `find <text1> <text2>...`. in order to search for text that includes spaces, enclose the searched text with double-quote (`"`) characters.
Once the `find` command is submitted, results can be iterated using the `n` and `N` keys for forward and backword iteration respectively. To cancel the search, use the `Escape` key.

### Saving the Current Page to a File
Enter the command-mode using the `:` key, and use the `w <filename>` command.

### Commands History
When in command-mode, use the `up` and `down` keys for scrolling the commands history.

## Appendix
### Key Bindings (View mode)

### Commands (Edit mode only)

### Themes
