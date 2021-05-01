# evtx2splunk
Ingest EVTX files into a Splunk instance. 

This tool is based on the work of :
  - [Omer BenAmram](https://github.com/omerbenamram/)
  - [Blardy](https://github.com/blardy/evtx2elk)

*Thanks to [Ekto](https://github.com/Ektoplasma) for its contribution.*  


**Key features**
  - Splunk HEC support with token auto-creation
  - Splunk index auto-creation
  - Multiprocessing support
  - Caching for evtx reuse without reconverting
  - Windows and Linux compatibility  
  - Rely on the great and fast *evtx_dump* Rust tool of Omer 
  - **New** : Evtx message resolutions from database

**Note**: *evtx2splunk* converts the EVTX to JSON and stores them in a temporary place.   
Hence, up to the size of source EVTX can be created during the process. These files are removed at the end of the process, except if `keep_cache` is enabled. 

## Installation
**Usage of a *venv* is recommended to avoid conflicts. Please use Python 3.7 or later.**
1. Clone the repo : `git clone https://github.com/whikernel/evtx2splunk.git && cd evtx2splunk`
2. Install the requirements: `pip3 install -r ./requirements.txt`
3. Copy env configuration : `cp env.sample .env` and fill it with you Splunk configuration   
3. Run evtx2splunk :-)  

## Usage
Ingest a folder containing evtx files into `case_0001` index. 
```
# Default 
python3 evtx2splunk.py --folder /data/evtx/folder --index case_0001 

# Keep cache 
python3 evtx2splunk.py --folder /data/evtx/folder --index case_0001 --keep_cache 

# Reuse cache and keep it 
python3 evtx2splunk.py --folder /data/evtx/folder --index case_0001 --keep_cache --use_cache 

# Disable message resolution 
python3 evtx2splunk.py --folder /data/evtx/folder --index case_0001 --no_resolve

# Generates the JSON Evtx message file 
python3 build_resolver.py -d winevt-kb.db
```

## Options 
- `--input`: Folder containing EVTX files to parse or unitary file
- `--index`: Splunk index to push the evtx 
- `--nb_process`: Number of ingest processes to create. Default to number of cores
- `--keep_cache`: Keep JSON cache for future use - Might take a lot of space
- `--use_cache` : Use the cache saved previously. Add `--keep_cache` to avoid erase of the case at the end.
- `--test` : Enable test mode. Do not push the events into to Splunk to preserve license.  
- `--no_resolve` : Disable the messages resolution

## Improvements to come 
- ~~Use the `evtx` python binding instead of the binaries~~ : Huge loss of performance after testing 
- Add the possibility to dynamically add fields
- Add the possibility to dynamically change the computer name 
- Add the possibility to recreate an already-existing index 