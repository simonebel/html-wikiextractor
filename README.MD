# Html WikiExtractor

This repository aims to extract and cleans articles from a wikipedia HTML dump.

## Introduction

Since October 2023 Wikimedia has released a new category of [wikipedia dumps in HTML](https://dumps.wikimedia.org/other/enterprise_html/runs/). Unlike the XML dumps, the wikitext has already been transclude, making it easier to parse the dumps and making possible to extract infoboxes from a wiki.

## Getting Started

### Installation

### Usage

```
usage: Extract and write to disk table and infobox from a HTML wikipedia dumps
       [-h] [--include_table] [--include_list] [--json] [--html] [--stdout]
       [--dev DEV]
       input_file

positional arguments:
  input_file       The input HTML dump.

optional arguments:
  -h, --help       show this help message and exit

Output:
  Arguments related to output.

  --include_table  Whether to include the tables or not.
  --include_list   Whether to include the lists or not.
  --json           Whether to write the articles on disk in JSON
  --html           Whether to write the articles on disk in HTML
  --stdout         Whether to redirect the article to the stdout

Dev:
  Arguments related to debug this script

  --dev DEV        Whether to run this script in dev mode. This argument
                   expect an int which will be the size of the number of
                   articles to parse

```

## HTML dumps

### What are html dumps ?

HTML dumps are available to donwload [here](https://dumps.wikimedia.org/other/enterprise_html/runs/), two HTML dumps are added every months (at the start and the end of the month).

The dumps are available :

- For different languages
- For three differents namespace :
  - 0 : Main (Articles)
  - 6 : Files
  - 10 : Models
- For four differents domain (if exist in the trageted language) :
  - wiki
  - wikibooks
  - wikiquote
  - wiktionnary

### Download HTML dumps

You can either download from the [source page](https://dumps.wikimedia.org/other/enterprise_html/runs/) or using the command:

```

```

e.g `frwiki-NS0-20240120-ENTERPRISE-HTML.json.tar.gz` for the french dump of the wikipedia articles

<!-- Add typology of html dumps -->

## Advantages and Limitations

Beacause there is no need to collect the templates and transclude the wikitext from the HTML dumps

- The obtained text is less noisy
<!-- Include example -->
- It is possible to extract infoboxes from a wikipedia dump

But :

- The HTML dumps are larger than the XML dumps
<!-- Include list of size -->

<!-- ## Comparison with wikiextractor -->

## TODO

- Add rotating output writer
- Test and dev sets
- Install from pypi + source
