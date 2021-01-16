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

**Note**: *evtx2splunk* converts the EVTX to JSON and stores them in a temporary place.   
Hence, up to the size of source EVTX can be created during the process. These files are removed at the end of the process, except if `keep_cache` is enabled. 

## Installation
**Usage of a *venv* is recommended to avoid conflicts.**
1. Clone the repo : `git clone https://github.com/whikernel/evtx2splunk.git && cd evtx2splunk`
2. Install the requirements: `pip3 instal -r ./requirements.txt`
3. Copy env configuration : `cp env.sample .env` and fill it with you Splunk configuration   
3. Run evtx2splunk :-)  

## Usage
Ingest a folder containing evtx files into `case_0001` index, using 8 threads and keeping json cache:
```
python3 evtx2splunk.py --folder /data/evtx/folder --index case_0001 --nb_process 8 --keep_cache 
```

## Options 
- `--input`: Folder containing EVTX files to parse or unitary file
- `--index`: Splunk index to push the evtx 
- `--nb_process`: Number of ingest processes to create. Default to number of cores
- `--keep_cache`: Keep JSON cache for future use - Might take a lot of space

## Improvements to come 
- Use the `evtx` python binding instead of the binaries 
- Add the possibility to dynamically add fields
- Add the possibility to dynamically change the computer name 
- Add the possibility to recreate an already-existing index 